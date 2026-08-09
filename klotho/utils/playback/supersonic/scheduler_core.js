(function() {
  // Bus-floor guard, re-asserted on EVERY inclusion (deliberately before the
  // install guard below): output buses 2..31 are stem-tap pairs under the
  // 10.16 boot config, so the shared private-bus cursor must never sit
  // inside the hardware span. This also repairs pages where a stale
  // pre-10.16 scheduler (floor 16) was installed first — the stale code
  // still allocates from this shared cursor, so raising it is sufficient.
  // Keep the literal in sync with FIRST_PRIVATE_BUS below.
  if (globalThis.__klothoBusAlloc && globalThis.__klothoBusAlloc.nextAudio < 48) {
    globalThis.__klothoBusAlloc.nextAudio = 48;
  }

  // Version-skew guard, same pattern as the playback bridge: saved
  // notebook outputs from klotho <= 10.15 install an older scheduler
  // under BrowserScheduler (first-wins) that lacks setupStemTaps and the
  // 10.16 bus floor. Widgets rendered after those stale outputs must get
  // THIS build, so the install guard keys on the versioned name and the
  // public class is overwritten unconditionally; stale code can never
  // downgrade it back (its own guard sees BrowserScheduler defined).
  // Old scheduler instances constructed before the overwrite keep their
  // old prototype and behave as before.
  // V3 (sync-drained stop/play, purge-ack fencing): pages carrying saved
  // 10.16-dev outputs already set the V2 marker, and their stale core has
  // the free-vs-purge race — so V3 must key on its own name to install
  // over them. Old instances keep the old prototype; new widgets get V3.
  // V4 (ring-out purge holdoff): the V3 core purged the engine queue at
  // the finish INSTANT — the exact due time of the piece's final gate
  // releases — so the last notes' releases could be wiped before they
  // fired (stuck final chord, hard-cut by the deferred ring free). V4
  // defers the idle purge past the ring-out; same marker discipline.
  // V5 (finish honors the trailing pause + fast fences + teardown handoff):
  // the V4 core armed both finish arms at the piece's musical end, ignoring
  // the payload's tail pause (shape widgets reset their visuals early on
  // every play), and paid supersonic sync()'s ~300 ms postMessage settling
  // sleep on every teardown fence; same marker discipline.
  if (globalThis.__klothoSchedCoreV5) return;

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
  // Idle purge waits ring-out + this margin after natural finish, so the
  // final gate releases (due exactly at pieceDur) and the deferred ring
  // frees (due at pieceDur + ringTime, riding the unordered OSC out-ring)
  // are consumed before purge()'s clearSched can wipe the queue. Also the
  // whole guard when ringTime is 0.
  var PURGE_HOLDOFF_MS = 250;
  // Must stay >= the engine's hardware bus span (numOutputBusChannels +
  // numInputBusChannels from supersonic_config(), currently 32 + 2): output
  // buses 2..31 are stem-tap pairs for recording, and track/FX routing must
  // never allocate into them. Keep in sync with scheduler_score.js.
  var FIRST_PRIVATE_BUS = 48;
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
      this._purgeHoldoffId = null;
      this._deferredRings = [];
      this._batchBundleCount = 0;
      this._playerRegistered = false;
      this._metricsAtPlay = null;
      this._tailPause = 0;

      this.drawScheduler = new DrawScheduler();
      this.onEvent = null;
      this.onFinish = null;
      // Fired when the piece is DONE done: finish + ring-out + teardown
      // (incl. any purge ack) — the earliest instant the fast play path
      // is guaranteed again. Transports re-arm their play button here,
      // not at onFinish.
      this.onIdle = null;
    }

    // "Now" on the clock scsynth actually fires bundles against: the
    // engine's drift-corrected NTP (superClock) when available, the page
    // wall clock otherwise. Stamping from the page clock desyncs whenever
    // the engine's drift correction moves — worst right after
    // audioContext.resume(), whose correction jump can instantly make a
    // queued first batch late (fired mid-block = clipped attacks).
    _engineNow() {
      try {
        var sc = this.sonic && this.sonic.superClock;
        if (sc && typeof sc.now === 'function') {
          var t = sc.now();
          if (typeof t === 'number' && isFinite(t) && t > 0) return t;
        }
      } catch (e) {}
      return getNTP();
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
        // Done entries leave the list so an idle replay reads as clean
        // (play()'s dirty check) and doesn't re-free dead nodes.
        var ix = self._deferredRings.indexOf(entry);
        if (ix !== -1) self._deferredRings.splice(ix, 1);
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
    // Must be purge(): /clearSched is a blocked command in SuperSonic (it
    // throws), and only purge() clears the JS pre-scheduler as well.
    _unregisterPlayer() {
      if (!this._playerRegistered) return;
      this._playerRegistered = false;
      var g = _schedLoad();
      g.activePlayers--;
      if (g.activePlayers <= 0) {
        g.activePlayers = 0;
        g.dues.length = 0;
        // The flush is async: clearSched rides the worklet port and is
        // acked later. Record the in-flight promise on the shared state —
        // the next play() (on ANY widget sharing this engine) must await
        // it before scheduling, or the late ack wipes that play's own
        // freshly queued bundles: eaten n_maps / __klEnvCtrl spawns show
        // up as frozen control envelopes, eaten gate releases and frees
        // as stuck notes. Which slice dies depends on timing, which is
        // why the failures looked intermittent.
        try {
          if (typeof this.sonic.purge === 'function') {
            var p = this.sonic.purge();
            g.purgePromise = p;
            var clearP = function() { if (g.purgePromise === p) g.purgePromise = null; };
            if (p && typeof p.then === 'function') p.then(clearP, clearP);
          }
        } catch(e) {}
      }
    }

    // Await a promise, but never longer than ms. sync()/purge() acks can
    // be lost when the engine is mid-reload or the reply channel is
    // wedged; an unbounded await here hangs stop() (stuck UI, poisoned
    // queue for every later play) or play() (piece never starts).
    async _awaitBounded(promise, ms) {
      if (!promise || typeof promise.then !== 'function') return;
      var timeout = new Promise(function(res) { setTimeout(res, ms); });
      try { await Promise.race([promise, timeout]); } catch(e) {}
    }

    // Direct /sync round-trip: resolves on scsynth's matching /synced
    // reply — the command-stream ordering guarantee the teardown fences
    // need. The upstream sonic.sync() adds ~2x snapshotIntervalMs
    // (~300 ms) of settling sleep in postMessage mode so its main-thread
    // state mirrors catch up, and also fences its internal async
    // buffer-command chain (the /b_alloc family is dispatched off a
    // promise chain, not written straight to the out-ring). Neither
    // matters here: these fences only order the /synced reply behind
    // /g_freeAll, /n_free and /b_free, which are direct out-ring sends.
    // scheduler_score.js's preloadControlBuffer MUST keep the full
    // sonic.sync(): its /b_alloc rides that async chain, and a raw /sync
    // can overtake it (b_setn fills would land on an unallocated buffer
    // — the control-envelope silence bug).
    // The 'in' event delivers each incoming OSC message as a decoded
    // flat array: [address, ...args] (supersonic-scsynth 0.71.0).
    // Self-bounded: resolves after timeoutMs even on a lost reply, and
    // always unhooks its listener. Engines without the emitter fall back
    // to the padded upstream sync().
    _fastSync(timeoutMs) {
      var sonic = this.sonic;
      if (!sonic || typeof sonic.on !== 'function'
          || typeof sonic.send !== 'function') {
        try {
          if (sonic && typeof sonic.sync === 'function') {
            return this._awaitBounded(sonic.sync(), timeoutMs);
          }
        } catch (e) {}
        return Promise.resolve();
      }
      var id = (Math.floor(Math.random() * 0x3fffffff) | 1);
      return new Promise(function(resolve) {
        var off = null;
        var done = function() {
          if (off) { try { off(); } catch (e) {} off = null; }
          resolve();
        };
        try {
          off = sonic.on('in', function(msg) {
            if (msg && msg[0] === '/synced' && msg[1] === id) done();
          });
          sonic.send('/sync', id);
        } catch (e) {
          done();
          return;
        }
        setTimeout(done, timeoutMs);
      });
    }

    // Record an in-flight teardown on the shared state: drain the frees
    // just sent (fast fence), then release the player registration —
    // which records any triggered purge on purgePromise BEFORE this
    // promise resolves, so an awaiter that then awaits purgePromise
    // observes the flush. play() on ANY widget sharing the engine awaits
    // the recorded teardown before scheduling; this closes the race
    // where a quick play lands while a stop()'s drain is mid-flight and
    // its purge is not yet recorded (the old unconditional sync masked
    // it by accident). Recorded when the teardown ACTIONS start — never
    // when the idle holdoff is merely armed, which would stall fresh
    // plays on other widgets for the whole ring-out.
    // ``superseded`` (optional) aborts the unregister when a newer
    // play/stop on this instance has taken over its registration.
    _beginTeardown(superseded) {
      var self = this;
      var g = _schedLoad();
      var p = (async function() {
        try { await self._fastSync(750); } catch (e) {}
        if (superseded && superseded()) return;
        self._unregisterPlayer();
      })();
      g.teardownPromise = p;
      var clear = function() { if (g.teardownPromise === p) g.teardownPromise = null; };
      p.then(clear, clear);
      return p;
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
      this._reportLossMetrics();
      if (this.onFinish) this.onFinish();
      if (this._groupId != null) {
        this._freeGroupDeferred(this._groupId);
        this._groupId = null;
      }
      this._deferUnregister();
    }

    // Natural finish fires at pieceDur — the exact due time of the last
    // gate releases — and unregistering the final player purges the
    // engine's scheduled queue. Purging at that instant races the very
    // bundles that end the piece (eaten releases = the last chord stuck
    // at full sustain until the ring free hard-cuts it). Hold the
    // unregister until the ring-out has passed, then sync-drain so the
    // deferred /g_freeAll (which rides the unordered OSC out-ring at
    // ringTime) is consumed before purge()'s clearSched can wipe it.
    // stop() and play()'s restart path keep their immediate unregister:
    // both already sync-drain first, and there the flush is the point.
    _deferUnregister() {
      var self = this;
      var token = this.stopToken;
      var delayMs = Math.max(0, this.ringTime || 0) * 1000 + PURGE_HOLDOFF_MS;
      this._purgeHoldoffId = setTimeout(function() {
        self._purgeHoldoffId = null;
        if (token !== self.stopToken) return;
        var teardown = self._beginTeardown(function() {
          return token !== self.stopToken;
        });
        // Transport re-arm: only after the teardown AND its recorded
        // purge ack settle is the fast play path guaranteed. Superseded
        // chains (a newer play/stop bumped the token) never fire — the
        // newer lifecycle owns the button.
        teardown.then(function() {
          return self._awaitBounded(_schedLoad().purgePromise, 1250);
        }).then(function() {
          if (token !== self.stopToken) return;
          if (self.onIdle) { try { self.onIdle(); } catch (e) {} }
        });
      }, delayMs);
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
          // allocated by the widget's loadSamples. Unresolvable strings
          // must never reach the OSC encoder — but dropping one means the
          // synth plays buffer 0 (silence or the wrong sample), so say so.
          if (key.indexOf('buf') === 0 && sampleMap[val] != null) {
            out[key] = sampleMap[val];
          } else if (key.indexOf('buf') === 0) {
            var warned = globalThis.__klothoBufWarned || (globalThis.__klothoBufWarned = {});
            if (!warned[val]) {
              warned[val] = true;
              console.warn('[Klotho] sample ' + JSON.stringify(val)
                + ' is not loaded on this page; events using it will be '
                + 'silent or play the wrong buffer.');
            }
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

      // Control mappings for set-event targets (insert-FX automation: the
      // FX synth is created in setupTracks, so its envelope wiring can't
      // ride an /s_new). Only attach mappings whose envelope starts exactly
      // at this event: every automation event on the same FX shares one
      // uid across all of that knob's descriptors, and the exact-time match
      // is what keeps each envelope wired once, in its own batch, instead
      // of re-mapping every earlier bus per section. Sent after the /n_set
      // above, so at equal timestamps the mapping wins.
      if (typeof this._getControlMappingsForEvent === 'function') {
        var mappings = this._getControlMappingsForEvent(ev.id, ev.start);
        if (mappings) {
          for (var mi = 0; mi < mappings.length; mi++) {
            var mp = mappings[mi];
            if (Math.abs(mp.startTime - ev.start) > 1e-6) continue;
            var mapBundle = globalThis.SuperSonic.osc.encodeSingleBundle(
              ntp, '/n_map', [intId, mp.param, mp.bus]);
            this._sendScheduled(ntp, mapBundle);
          }
        }
      }
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

      var now = this._engineNow();
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
          // Last finite cycle ends at its musical end PLUS the trailing
          // pause (between-cycle spacing already honors it via cycleDur).
          var endNTP = this._playStartNTP + relOffset + pieceDur
            + (loopState.tailPause || 0);
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
        // Non-loop finish: musical end plus the trailing pause.
        var endNTP = this._playStartNTP + relOffset + pieceDur + this._tailPause;
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
      clearTimeout(this._purgeHoldoffId);
      this._purgeHoldoffId = null;

      // Restarting while a previous play is live: free its nodes, then
      // release its player registration (flushing the engine queue when
      // nothing else is playing) before the new burst goes out. The frees
      // MUST be drained ahead of the flush: /g_freeAll rides the OSC
      // out-ring while purge() signals clearSched over the worklet port —
      // an unordered channel that can wipe the ring before it drains,
      // eating the frees and leaving the old notes sounding forever. The
      // /synced round-trip guarantees the frees are consumed first.
      // Liveness is captured BEFORE the frees reset it: a fresh or fully
      // idle widget has nothing in flight to drain, so it skips the
      // fence and press-to-sound stays at ~STARTUP_DELAY.
      this._reportLossMetrics();
      var wasLive = (this._groupId != null)
        || this._activeBuffers.length > 0
        || this._deferredRings.length > 0;
      this._cancelAllDeferredRings();
      this._freeGroup();
      this._freeBuffers();
      if (wasLive) {
        await this._beginTeardown();
      } else {
        this._unregisterPlayer();
      }
      // A teardown started elsewhere — a stop() or idle holdoff on any
      // widget sharing this engine — may be mid-flight with its purge
      // not yet recorded: await it, THEN the recorded purge. A late
      // clearSched ack would otherwise eat a random slice of the new
      // batch (n_maps, control synths, releases).
      await this._awaitBounded(_schedLoad().teardownPromise, 750);
      await this._awaitBounded(_schedLoad().purgePromise, 750);

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
      this.onIdle = options.onIdle || null;

      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        if (this.onIdle) { try { this.onIdle(); } catch (e) {} }
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

      // Stems recording: tap each track's post-FX bus onto its own
      // hardware output pair for the widget's capture node.
      this._stemLayout = null;
      if (options.stemTaps && this._trackMap
          && typeof this.setupStemTaps === 'function') {
        this._stemLayout = this.setupStemTaps();
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

      // Compute the start time AFTER any async setup, ON THE ENGINE'S
      // CLOCK. First settle the drift correction: the widget resumes the
      // AudioContext right before play(), and the resume-sized correction
      // jump must land before the start stamp is derived, not after —
      // otherwise the first batch of events is instantly late on the
      // engine clock and scsynth processes it mid-block, clipping the
      // first notes' attacks (audible as soft pops at play start).
      try {
        var sclk = this.sonic && this.sonic.superClock;
        if (sclk && typeof sclk.updateDriftOffset === 'function') {
          sclk.updateDriftOffset();
        }
      } catch (e) {}
      var now = this._engineNow();
      var nowPerf = performance.now();
      this._playStartNTP = now + STARTUP_DELAY;
      this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;

      this.isPlaying = true;

      var basePieceDur = this._computePieceDur(evts);
      // The trailing pause is part of the piece: the finish arms in
      // _scheduleBatch add it (via this._tailPause / loopState.tailPause)
      // so the visual reset and teardown chain don't fire early, while
      // batching lookahead math stays on the base duration.
      var tailPause = Math.max(0, options.tailPause || 0);
      this._tailPause = tailPause;
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
      clearTimeout(this._purgeHoldoffId);
      this._purgeHoldoffId = null;
      this._reportLossMetrics();
      this._cancelAllDeferredRings();
      this._freeGroup();
      this._freeBuffers();
      // Same free-vs-purge ordering hazard as play()'s restart path: the
      // frees ride the OSC out-ring, purge()'s clearSched rides the
      // worklet port, and the port message can win — wiping the ring
      // before the frees are consumed. Stop must actually silence the
      // synths, so drain via the fast /synced fence before flushing the
      // queue (bounded inside _beginTeardown: a lost reply degrades to a
      // best-effort flush, never a hung stop() with a poisoned queue).
      await this._beginTeardown();
      this.nodeMap.clear();
      this._defNames.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this.drawScheduler.clear();
    }
  };
  globalThis.__klothoSchedCoreV2 = true;
  globalThis.__klothoSchedCoreV3 = true;
  globalThis.__klothoSchedCoreV4 = true;
  globalThis.__klothoSchedCoreV5 = true;
})();
