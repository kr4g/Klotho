(function() {
  if (globalThis.BrowserScheduler) return;

  // The supersonic-scsynth engine holds at most SCHEDULER_SLOT_COUNT (512)
  // timestamped bundles; when that queue is full an arriving bundle is
  // silently dropped (scsynthSchedulerDropped metric). Every batch send must
  // therefore be budgeted in *bundles* (a gated note costs an /s_new plus a
  // late-bound /n_set gate release; control mappings add /n_map each) and
  // gated on the tracked in-flight load so total queue occupancy stays
  // under SAFE_QUEUE_LIMIT. The gap between SAFE_QUEUE_LIMIT and
  // SCHEDULER_QUEUE_SLOTS absorbs per-event cost overshoot (a batch stops
  // after the event that crosses the budget) plus non-Klotho traffic.
  var SCHEDULER_QUEUE_SLOTS = 512;
  var SAFE_QUEUE_LIMIT = 384;
  var MAX_BUNDLES_PER_BATCH = 200;
  var MIN_BATCH_BUNDLES = 25;
  var MAX_ITEMS_PER_BATCH = 500;
  var BATCH_OVERLAP_RATIO = 0.8;
  var BATCH_DEFER_MAX_MS = 250;
  var NTP_EPOCH_OFFSET = 2208988800;
  var STARTUP_DELAY = 0.1;
  var DEFAULT_RING_TIME = 5;
  var FIRST_PRIVATE_BUS = 16;
  var BUS_CHANNELS = 2;

  if (!globalThis.__klothoBusAlloc) {
    globalThis.__klothoBusAlloc = { nextAudio: FIRST_PRIVATE_BUS, nextControl: 0 };
  }

  function getNTP() {
    return (performance.timeOrigin + performance.now()) / 1000 + NTP_EPOCH_OFFSET;
  }

  // Shared in-flight load tracker: one due-NTP entry per timestamped bundle
  // any Klotho scheduler on the page has sent. All widgets share the single
  // scsynth instance (and its one 512-slot queue), so the tracker is global
  // like __klothoBusAlloc. Entries whose due time has passed are pruned
  // lazily; `dues` is a binary min-heap keyed on due NTP.
  function _schedLoad() {
    if (!globalThis.__klothoSchedLoad) {
      globalThis.__klothoSchedLoad = { dues: [], activePlayers: 0 };
    }
    return globalThis.__klothoSchedLoad;
  }

  function _schedLoadPush(due) {
    var h = _schedLoad().dues;
    h.push(due);
    var i = h.length - 1;
    while (i > 0) {
      var p = (i - 1) >> 1;
      if (h[p] <= h[i]) break;
      var t = h[p]; h[p] = h[i]; h[i] = t;
      i = p;
    }
  }

  function _schedLoadPop() {
    var h = _schedLoad().dues;
    var last = h.pop();
    if (h.length === 0) return;
    h[0] = last;
    var i = 0;
    for (;;) {
      var l = 2 * i + 1, r = l + 1, m = i;
      if (l < h.length && h[l] < h[m]) m = l;
      if (r < h.length && h[r] < h[m]) m = r;
      if (m === i) break;
      var t = h[m]; h[m] = h[i]; h[i] = t;
      i = m;
    }
  }

  // Drop expired entries; returns the current in-flight bundle count.
  function _schedLoadPrune(nowNTP) {
    var h = _schedLoad().dues;
    while (h.length && h[0] <= nowNTP) _schedLoadPop();
    return h.length;
  }

  function _schedLoadPeek() {
    var h = _schedLoad().dues;
    return h.length ? h[0] : null;
  }

  globalThis.BrowserScheduler = class {
    constructor(config) {
      this.sonic = config.sonic;
      this.manifest = config.manifest || { synths: {}, inserts: {} };
      this.ringTime = (config.ringTime != null) ? config.ringTime : DEFAULT_RING_TIME;

      this.isPlaying = false;
      this.stopToken = 0;
      this.nodeMap = new Map();
      this._defNames = new Map();

      this._scoreGroupId = null;
      this._groupId = null;
      this._trackMap = null;
      this._controlGroupId = null;
      this._controlBusMap = [];
      this._nextAudioBus = globalThis.__klothoBusAlloc.nextAudio;
      this._nextControlBus = globalThis.__klothoBusAlloc.nextControl;
      // Track the bus range allocated by THIS play, so it can be reclaimed
      // when the group is freed. Without this, ``__klothoBusAlloc`` only
      // grows monotonically and the user runs out of private audio buses
      // (default scsynth limit: 128 channels) after a few dozen plays.
      this._audioBusRangeStart = null;
      this._controlBusRangeStart = null;
      this._activeBuffers = [];

      this._playStartNTP = 0;
      this._playStartPerfMs = 0;
      this._batchTimeoutId = null;
      this._finishTimeoutId = null;
      this._deferredRings = [];
      this._batchBundleCount = 0;
      this._playerRegistered = false;
      this._metricsAtPlay = null;

      this.drawScheduler = new DrawScheduler();
      this.onEvent = null;
      this.onFinish = null;
    }

    _createGroup() {
      var gid = this.sonic.nextNodeId();
      this.sonic.send('/g_new', gid, 0, 0);
      this._groupId = gid;
    }

    _snapshotBusRangeStart() {
      this._audioBusRangeStart = globalThis.__klothoBusAlloc.nextAudio;
      this._controlBusRangeStart = globalThis.__klothoBusAlloc.nextControl;
    }

    // Reclaim a bus range back to the global allocator if no later play
    // has extended past it. The conditional check protects against
    // clobbering allocations made by a concurrent widget's scheduler.
    _reclaimBusRange(audioStart, audioEnd, controlStart, controlEnd) {
      var g = globalThis.__klothoBusAlloc;
      if (audioStart != null && audioEnd != null
          && g.nextAudio === audioEnd && audioStart < audioEnd) {
        g.nextAudio = audioStart;
      }
      if (controlStart != null && controlEnd != null
          && g.nextControl === controlEnd && controlStart < controlEnd) {
        g.nextControl = controlStart;
      }
    }

    _freeGroup() {
      if (this._groupId == null) return;
      try { this.sonic.send('/g_freeAll', this._groupId); } catch(e) {}
      try { this.sonic.send('/n_free', this._groupId); } catch(e) {}
      this._reclaimBusRange(
        this._audioBusRangeStart, globalThis.__klothoBusAlloc.nextAudio,
        this._controlBusRangeStart, globalThis.__klothoBusAlloc.nextControl
      );
      this._audioBusRangeStart = null;
      this._controlBusRangeStart = null;
      this._groupId = null;
      this._scoreGroupId = null;
    }

    _freeGroupDeferred(groupId) {
      var self = this;
      var sonic = this.sonic;
      var ringMs = this.ringTime * 1000;
      var bufs = this._activeBuffers.slice();
      // Snapshot this play's bus range; on ring-out, reclaim it so the
      // global allocator doesn't grow unboundedly.
      var audioStart = this._audioBusRangeStart;
      var audioEnd = globalThis.__klothoBusAlloc.nextAudio;
      var controlStart = this._controlBusRangeStart;
      var controlEnd = globalThis.__klothoBusAlloc.nextControl;
      var entry = {
        gid: groupId,
        bufs: bufs,
        audioStart: audioStart,
        audioEnd: audioEnd,
        controlStart: controlStart,
        controlEnd: controlEnd,
        tid: null,
      };
      entry.tid = setTimeout(function() {
        try { sonic.send('/g_freeAll', groupId); } catch(e) {}
        try { sonic.send('/n_free', groupId); } catch(e) {}
        for (var i = 0; i < bufs.length; i++) {
          try { sonic.send('/b_free', bufs[i]); } catch(e) {}
        }
        self._reclaimBusRange(audioStart, audioEnd, controlStart, controlEnd);
      }, ringMs);
      this._deferredRings.push(entry);
      this._activeBuffers = [];
      // Ownership of the range moves onto the deferred entry; clear so
      // the next play snapshots a fresh range starting from the (still
      // unreclaimed) global cursor.
      this._audioBusRangeStart = null;
      this._controlBusRangeStart = null;
    }

    _freeBuffers() {
      for (var i = 0; i < this._activeBuffers.length; i++) {
        try { this.sonic.send('/b_free', this._activeBuffers[i]); } catch(e) {}
      }
      this._activeBuffers = [];
    }

    _cancelAllDeferredRings() {
      for (var i = 0; i < this._deferredRings.length; i++) {
        var entry = this._deferredRings[i];
        clearTimeout(entry.tid);
        try { this.sonic.send('/g_freeAll', entry.gid); } catch(e) {}
        try { this.sonic.send('/n_free', entry.gid); } catch(e) {}
        if (entry.bufs) {
          for (var j = 0; j < entry.bufs.length; j++) {
            try { this.sonic.send('/b_free', entry.bufs[j]); } catch(e) {}
          }
        }
        this._reclaimBusRange(
          entry.audioStart, entry.audioEnd,
          entry.controlStart, entry.controlEnd
        );
      }
      this._deferredRings = [];
    }

    // Sole exit for timestamped bundles: registers the due time on the
    // shared load tracker (so every scheduler's occupancy gate sees it) and
    // counts it against the current batch budget.
    _sendScheduled(dueNTP, bundle) {
      _schedLoadPush(dueNTP);
      this._batchBundleCount++;
      this.sonic.sendOSC(bundle);
    }

    _registerPlayer() {
      if (this._playerRegistered) return;
      this._playerRegistered = true;
      _schedLoad().activePlayers++;
    }

    // When the last playing Klotho scheduler goes idle, flush the engine's
    // scheduled queue: stale bundles from a stopped play would otherwise
    // occupy slots until due (and fire /s_new into freed groups). Guarded by
    // the active-player count so a concurrent widget's playback survives.
    _unregisterPlayer() {
      if (!this._playerRegistered) return;
      this._playerRegistered = false;
      var g = _schedLoad();
      g.activePlayers--;
      if (g.activePlayers <= 0) {
        g.activePlayers = 0;
        g.dues.length = 0;
        try { this.sonic.send('/clearSched'); } catch(e) {}
      }
    }

    _snapshotMetrics() {
      try {
        if (typeof this.sonic.getMetrics === 'function') {
          return this.sonic.getMetrics();
        }
      } catch(e) {}
      return null;
    }

    // Diff the engine's loss counters against the play() snapshot and make
    // any message loss loud. Lateness is reported at debug level: it is the
    // intended degradation mode when the occupancy gate must defer sends.
    _reportLossMetrics() {
      var before = this._metricsAtPlay;
      if (!before) return;
      this._metricsAtPlay = null;
      var after = this._snapshotMetrics();
      if (!after) return;
      var LOSS_KEYS = {
        scsynthSchedulerDropped: 'engine scheduler queue overflowed',
        scsynthMessagesDropped: 'engine IN ring buffer overflowed',
        scsynthSequenceGaps: 'messages lost in transit to the engine',
        oscOutMessagesDropped: 'messages failed to send from the page'
      };
      for (var key in LOSS_KEYS) {
        var delta = (after[key] || 0) - (before[key] || 0);
        if (delta > 0) {
          console.warn('[Klotho] ' + delta + ' audio message(s) lost during '
            + 'playback (' + key + ': ' + LOSS_KEYS[key] + '). '
            + 'Audio gaps or stuck notes are likely.');
        }
      }
      var lates = (after.scsynthSchedulerLates || 0) - (before.scsynthSchedulerLates || 0);
      if (lates > 0) {
        console.debug('[Klotho] ' + lates + ' bundle(s) reached the engine '
          + 'after their scheduled time (played late, not dropped).');
      }
    }

    _finishPlayback() {
      this.isPlaying = false;
      this._unregisterPlayer();
      this._reportLossMetrics();
      if (this.onFinish) this.onFinish();
      if (this._groupId != null) {
        this._freeGroupDeferred(this._groupId);
        this._groupId = null;
      }
    }

    // Unified send stream: note events plus (when the score extension is
    // loaded) control-envelope synth items, merged by due time so an
    // envelope starting late in the piece ships with the batch covering
    // that stretch instead of being front-loaded at play start.
    _buildSendPlan(evts) {
      var items = new Array(evts.length);
      for (var i = 0; i < evts.length; i++) {
        items[i] = { kind: 'event', start: evts[i].start, ev: evts[i] };
      }
      var ctrl = (typeof this._controlStreamItems === 'function')
        ? this._controlStreamItems()
        : [];
      if (ctrl.length === 0) return items;
      var merged = items.concat(ctrl);
      merged.sort(function(a, b) { return a.start - b.start; });
      return merged;
    }

    _resolveDefPfields(defName, pfields) {
      var out = {};
      var sampleMap = (globalThis.__klothoSonic && globalThis.__klothoSonic.sampleMap) || {};
      for (var key in pfields) {
        if (!pfields.hasOwnProperty(key)) continue;
        var val = pfields[key];
        if (val === null || val === undefined) continue;
        if (typeof val === 'object') continue;
        if (typeof val === 'string') {
          // Symbolic sample name on a buf* pfield: substitute the bufnum
          // allocated by the widget's loadSamples. Drop unresolvable
          // strings so they never reach the OSC encoder.
          if (key.indexOf('buf') === 0 && sampleMap[val] != null) {
            out[key] = sampleMap[val];
          }
          continue;
        }
        out[key] = val;
      }
      return out;
    }

    _maybeScheduleAutoRelease(ev, intId, defName, ntp) {
      if (!ev || !ev.releaseAfter) return;
      var dur = (typeof ev.dur === 'number') ? ev.dur : null;
      if (dur === null || !(dur > 0)) return;
      var controls = (this.manifest || {})[defName];
      if (!controls || !('gate' in controls)) return;
      var releaseNtp = ntp + dur;
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(
        releaseNtp, '/n_set', [intId, 'gate', 0]);
      this._sendScheduled(releaseNtp, bundle);
    }

    _resolveDefName(name) {
      if (name === "__rest__") return "__rest__";
      if (!name || name === "sonic-pi-beep") return "kl_tri";
      return name;
    }

    _bundleNew(ev, ntp) {
      if (ev.defName === "__rest__") return;
      var defName = this._resolveDefName(ev.defName);
      var nodeId = this.sonic.nextNodeId();

      var target;
      var pf = this._resolveDefPfields(defName, ev.pfields || {});

      if (this._trackMap) {
        var group = ev.group || "default";
        var trackInfo = this._trackMap[group] || this._trackMap["default"] || this._trackMap["main"];
        target = trackInfo ? trackInfo.srcGroup : (this._scoreGroupId || this._groupId || 0);
        if (trackInfo) {
          pf.out = trackInfo.srcBus;
        }
      } else {
        target = this._groupId != null ? this._groupId : 0;
      }

      var args = [defName, nodeId, 0, target];
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        var v = pf[key];
        if (v === undefined || v === null || typeof v === 'object') continue;
        args.push(key, v);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
      this._sendScheduled(ntp, bundle);
      this.nodeMap.set(ev.id, nodeId);
      this._defNames.set(ev.id, defName);
      this._maybeScheduleAutoRelease(ev, nodeId, defName, ntp);

      if (typeof this._getControlMappingsForEvent === 'function') {
        var mappings = this._getControlMappingsForEvent(ev.id, ev.start);
        if (mappings) {
          for (var mi = 0; mi < mappings.length; mi++) {
            var mp = mappings[mi];
            var mapArgs = [nodeId, mp.param, mp.bus];
            var mapNtp = mp.deferred
              ? (this._playStartNTP + mp.startTime)
              : ntp;
            var mapBundle = globalThis.SuperSonic.osc.encodeSingleBundle(mapNtp, '/n_map', mapArgs);
            this._sendScheduled(mapNtp, mapBundle);
          }
        }
      }
    }

    _bundleSet(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var defName = this._defNames.get(ev.id);
      var pf = this._resolveDefPfields(defName, ev.pfields || {});
      // Mirror _bundleNew's track-aware out routing so slurred set events
      // don't accidentally re-route a running synth from the track's
      // srcBus back to the synth's baked default (typically out=0).
      if (this._trackMap) {
        var group = ev.group || "default";
        var trackInfo = this._trackMap[group] || this._trackMap["default"] || this._trackMap["main"];
        if (trackInfo) {
          pf.out = trackInfo.srcBus;
        }
      }
      var args = [intId];
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        var v = pf[key];
        if (v === undefined || v === null || typeof v === 'object') continue;
        args.push(key, v);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this._sendScheduled(ntp, bundle);
      this._maybeScheduleAutoRelease(ev, intId, defName, ntp);
    }

    _bundleRelease(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var defName = this._defNames.get(ev.id);
      var controls = (this.manifest || {})[defName];
      if (!controls || !('gate' in controls)) return;
      var args = [intId, 'gate', 0];
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this._sendScheduled(ntp, bundle);
    }

    _computePieceDur(evts) {
      var dur = 0;
      for (var i = 0; i < evts.length; i++) {
        var ev = evts[i];
        var evEnd = ev.start;
        if ((ev.type === "new" || ev.type === "set")
            && typeof ev.dur === 'number') {
          evEnd += ev.dur;
        }
        if (evEnd > dur) dur = evEnd;
      }
      return dur;
    }

    _scheduleBatch(plan, startIdx, pieceDur, token, relOffset, loopState) {
      if (token !== this.stopToken) return;

      var now = getNTP();
      var self = this;

      relOffset = relOffset || 0;
      var cycleIndex = (loopState && loopState.cycleIndex) || 0;
      var idPrefix = loopState ? "c" + cycleIndex : null;

      // Occupancy gate: never let the engine's scheduled-bundle queue exceed
      // SAFE_QUEUE_LIMIT. When headroom is too thin for a worthwhile batch,
      // defer until tracked bundles come due (bounded retry, so a genuinely
      // pinned queue degrades to late delivery rather than silent drops).
      if (startIdx < plan.length) {
        var load = _schedLoadPrune(now);
        var headroom = SAFE_QUEUE_LIMIT - load;
        if (headroom < MIN_BATCH_BUNDLES) {
          var earliest = _schedLoadPeek();
          var waitMs = (earliest != null)
            ? Math.min(BATCH_DEFER_MAX_MS, Math.max(20, (earliest - now) * 1000))
            : 100;
          this._batchTimeoutId = setTimeout(function() {
            self._scheduleBatch(plan, startIdx, pieceDur, token, relOffset, loopState);
          }, waitMs);
          return;
        }
      }

      var budget = Math.min(MAX_BUNDLES_PER_BATCH, SAFE_QUEUE_LIMIT - _schedLoad().dues.length);
      var idx = startIdx;
      var batchStart = -1;
      var batchEnd = 0;
      var itemCount = 0;
      this._batchBundleCount = 0;

      while (idx < plan.length
             && this._batchBundleCount < budget
             && itemCount < MAX_ITEMS_PER_BATCH) {
        var item = plan[idx];
        if (batchStart < 0) batchStart = item.start;
        batchEnd = item.start;

        var ntp = this._playStartNTP + relOffset + item.start;

        if (item.kind === "ctrl") {
          // Control-envelope synths are cycle-0 only: their /n_map targets
          // are keyed on unprefixed event ids, which later loop cycles
          // rewrite (pre-existing loop semantics, preserved).
          if (relOffset === 0 && typeof this._sendControlItem === 'function') {
            this._sendControlItem(item.cm, ntp);
          }
        } else {
          var ev = item.ev;
          var evSched = ev;
          if (idPrefix != null) {
            evSched = {};
            for (var kCopy in ev) evSched[kCopy] = ev[kCopy];
            evSched.id = idPrefix + ":" + ev.id;
          }

          if (evSched.type === "new") {
            this._bundleNew(evSched, ntp);
          } else if (evSched.type === "set") {
            this._bundleSet(evSched, ntp);
          } else if (evSched.type === "release") {
            this._bundleRelease(evSched, ntp);
          }

          if (ev.type === "new" && ev._stepIndex != null && this.onEvent) {
            (function(ds, cb, si, ms) {
              ds.schedule(function() { cb(si); }, ms);
            })(self.drawScheduler, self.onEvent, ev._stepIndex,
               self._playStartPerfMs + (relOffset + ev.start) * 1000);
          }
        }

        idx++;
        itemCount++;
      }

      if (idx < plan.length) {
        var batchDuration = batchEnd - batchStart;
        var overlapTime = batchDuration * BATCH_OVERLAP_RATIO;
        var nextBatchNTP = this._playStartNTP + relOffset + batchStart + overlapTime;
        var delay = (nextBatchNTP - now) * 1000;
        this._batchTimeoutId = setTimeout(function() {
          self._scheduleBatch(plan, idx, pieceDur, token, relOffset, loopState);
        }, Math.max(1, delay));
      } else if (loopState) {
        var nextCycle = cycleIndex + 1;
        if (loopState.finiteCycles > 0 && nextCycle >= loopState.finiteCycles) {
          var endNTP = this._playStartNTP + relOffset + pieceDur;
          var remaining = (endNTP - now) * 1000;
          this._finishTimeoutId = setTimeout(function() {
            if (token !== self.stopToken) return;
            self._finishPlayback();
          }, Math.max(1, remaining));
        } else {
          var cycleDur = pieceDur + (loopState.tailPause || 0);
          var nextRelOffset = relOffset + cycleDur;
          var nextLoopState = {
            cycleIndex: nextCycle,
            finiteCycles: loopState.finiteCycles,
            tailPause: loopState.tailPause
          };
          var nextCycleNTP = this._playStartNTP + nextRelOffset;
          var lookahead = Math.min(pieceDur * (1 - BATCH_OVERLAP_RATIO), 2.0);
          var scheduleAt = nextCycleNTP - lookahead;
          var delay2 = (scheduleAt - now) * 1000;
          this._batchTimeoutId = setTimeout(function() {
            self._scheduleBatch(plan, 0, pieceDur, token, nextRelOffset, nextLoopState);
          }, Math.max(1, delay2));
        }
      } else {
        var endNTP = this._playStartNTP + relOffset + pieceDur;
        var remaining = (endNTP - now) * 1000;
        this._finishTimeoutId = setTimeout(function() {
          if (token !== self.stopToken) return;
          self._finishPlayback();
        }, Math.max(1, remaining));
      }
    }

    async play(events, options) {
      options = options || {};
      this.stopToken++;
      var token = this.stopToken;

      this.isPlaying = false;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;

      // Restarting while a previous play is live: surface its loss metrics
      // and release its player registration (flushing the engine queue when
      // nothing else is playing) before the new burst goes out.
      this._reportLossMetrics();
      this._unregisterPlayer();

      this._cancelAllDeferredRings();
      this._freeGroup();
      this._freeBuffers();

      this.nodeMap.clear();
      this._defNames.clear();
      this.drawScheduler.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this._nextAudioBus = globalThis.__klothoBusAlloc.nextAudio;
      this._nextControlBus = globalThis.__klothoBusAlloc.nextControl;
      this._snapshotBusRangeStart();

      if (token !== this.stopToken) return;

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;

      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      var scoreMeta = options.meta || null;
      var scoreControlData = options.controlData || null;

      if (scoreMeta && (scoreMeta.groups || scoreMeta.inserts) && typeof this.setupTracks === 'function') {
        this._createScoreGroup();
        await this.setupTracks(scoreMeta, this._scoreGroupId);
      } else {
        this._createGroup();
      }

      // Control envelopes are independent of track/insert setup: they fire
      // for any payload carrying descriptors (bare UC/UTS/BT play included).
      if (scoreControlData && scoreControlData.bufferB64 && typeof this.setupControlEnvelopes === 'function') {
        var ctrlParent = (this._scoreGroupId != null) ? this._scoreGroupId : this._groupId;
        await this.setupControlEnvelopes(scoreControlData, ctrlParent);
      }

      // A stop() during the awaits above must win; without this recheck the
      // stale play would re-register and flip isPlaying back on.
      if (token !== this.stopToken) return;

      var plan = this._buildSendPlan(evts);
      this._registerPlayer();
      this._metricsAtPlay = this._snapshotMetrics();

      // Compute start time AFTER any async setup so the cushion isn't
      // eaten by /g_new + /s_new + /sync round-trips during setupTracks.
      // Otherwise the first batch of events lands with a past NTP and
      // scsynth processes them mid-block, clipping the first note's attack.
      var now = getNTP();
      var nowPerf = performance.now();
      this._playStartNTP = now + STARTUP_DELAY;
      this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;

      this.isPlaying = true;

      var basePieceDur = this._computePieceDur(evts);
      var tailPause = Math.max(0, options.tailPause || 0);
      var pieceDur = basePieceDur + tailPause;
      var loopFinite = (typeof options.loop === "number" && Number.isFinite(options.loop) && options.loop > 1)
        ? Math.floor(options.loop)
        : 0;

      var loopState = null;
      if (options.loop || loopFinite > 0) {
        loopState = {
          cycleIndex: 0,
          finiteCycles: loopFinite > 0 ? loopFinite : 0,
          tailPause: tailPause
        };
      }

      this._scheduleBatch(plan, 0, basePieceDur, token, 0, loopState);
    }

    async stop() {
      this.stopToken++;
      this.isPlaying = false;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;
      this._reportLossMetrics();
      this._cancelAllDeferredRings();
      this._freeGroup();
      this._freeBuffers();
      this._unregisterPlayer();
      this.nodeMap.clear();
      this._defNames.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this.drawScheduler.clear();
    }
  };
})();
