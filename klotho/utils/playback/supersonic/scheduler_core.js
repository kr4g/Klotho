(function() {
  if (globalThis.BrowserScheduler) return;

  var MAX_EVENTS_PER_BATCH = 500;
  var BATCH_OVERLAP_RATIO = 0.8;
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
      this._activeBuffers = [];

      this._playStartNTP = 0;
      this._playStartPerfMs = 0;
      this._batchTimeoutId = null;
      this._finishTimeoutId = null;
      this._deferredRings = [];

      this.drawScheduler = new DrawScheduler();
      this.onEvent = null;
      this.onFinish = null;
    }

    _createGroup() {
      var gid = this.sonic.nextNodeId();
      this.sonic.send('/g_new', gid, 0, 0);
      this._groupId = gid;
    }

    _freeGroup() {
      if (this._groupId == null) return;
      try { this.sonic.send('/g_freeAll', this._groupId); } catch(e) {}
      try { this.sonic.send('/n_free', this._groupId); } catch(e) {}
      this._groupId = null;
      this._scoreGroupId = null;
    }

    _freeGroupDeferred(groupId) {
      var sonic = this.sonic;
      var ringMs = this.ringTime * 1000;
      var bufs = this._activeBuffers.slice();
      var tid = setTimeout(function() {
        try { sonic.send('/g_freeAll', groupId); } catch(e) {}
        try { sonic.send('/n_free', groupId); } catch(e) {}
        for (var i = 0; i < bufs.length; i++) {
          try { sonic.send('/b_free', bufs[i]); } catch(e) {}
        }
      }, ringMs);
      this._deferredRings.push({ tid: tid, gid: groupId });
      this._activeBuffers = [];
    }

    _freeBuffers() {
      for (var i = 0; i < this._activeBuffers.length; i++) {
        try { this.sonic.send('/b_free', this._activeBuffers[i]); } catch(e) {}
      }
      this._activeBuffers = [];
    }

    _cancelAllDeferredRings() {
      for (var i = 0; i < this._deferredRings.length; i++) {
        clearTimeout(this._deferredRings[i].tid);
        var gid = this._deferredRings[i].gid;
        try { this.sonic.send('/g_freeAll', gid); } catch(e) {}
        try { this.sonic.send('/n_free', gid); } catch(e) {}
      }
      this._deferredRings = [];
    }

    _getByPath(obj, path) {
      if (!obj || !path) return undefined;
      var parts = path.split('.');
      var cur = obj;
      for (var i = 0; i < parts.length; i++) {
        var key = parts[i];
        if (cur == null || typeof cur !== 'object' || !(key in cur)) return undefined;
        cur = cur[key];
      }
      return cur;
    }

    _resolveDefPfields(defName, pfields) {
      var out = {};
      for (var key in pfields) {
        if (!pfields.hasOwnProperty(key)) continue;
        var val = pfields[key];
        if (val === null || val === undefined) continue;
        if (typeof val === 'object') continue;
        out[key] = val;
      }
      var meta = (this.manifest.synths || {})[defName] || {};
      var paths = meta.paths || {};
      for (var srcPath in paths) {
        if (!paths.hasOwnProperty(srcPath)) continue;
        var dstKey = paths[srcPath];
        var mapped = this._getByPath(pfields, srcPath);
        if (mapped === undefined || mapped === null) continue;
        if (typeof mapped === 'object') continue;
        out[dstKey] = mapped;
      }
      return out;
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
      this.sonic.sendOSC(bundle);
      this.nodeMap.set(ev.id, nodeId);
      this._defNames.set(ev.id, defName);

      if (typeof this._getControlMappingsForEvent === 'function') {
        var mappings = this._getControlMappingsForEvent(ev.id);
        if (mappings) {
          for (var mi = 0; mi < mappings.length; mi++) {
            var mapArgs = [nodeId, mappings[mi].param, mappings[mi].bus];
            var mapBundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_map', mapArgs);
            this.sonic.sendOSC(mapBundle);
          }
        }
      }
    }

    _bundleSet(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var args = [intId];
      var defName = this._defNames.get(ev.id);
      var pf = this._resolveDefPfields(defName, ev.pfields || {});
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        var v = pf[key];
        if (v === undefined || v === null || typeof v === 'object') continue;
        args.push(key, v);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
    }

    _bundleRelease(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var defName = this._defNames.get(ev.id);
      var meta = (this.manifest.synths || {})[defName];
      if (meta && meta.releaseMode === "free") return;
      var gateParam = (meta && meta.gateParam) || 'gate';
      var args = [intId, gateParam, 0];
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
    }

    _computePieceDur(evts) {
      var dur = 0;
      for (var i = 0; i < evts.length; i++) {
        var ev = evts[i];
        var evEnd = ev.start;
        if (ev.type === "new") {
          var pf = ev.pfields || {};
          if (pf.dur != null) evEnd += pf.dur;
        }
        if (ev.type === "release") {
          evEnd = ev.start;
        }
        if (evEnd > dur) dur = evEnd;
      }
      return dur;
    }

    _scheduleBatch(evts, startIdx, pieceDur, token, relOffset, loopState) {
      if (token !== this.stopToken) return;

      var now = getNTP();
      var idx = startIdx;
      var batchStart = -1;
      var batchEnd = 0;
      var count = 0;
      var self = this;

      relOffset = relOffset || 0;
      var cycleIndex = (loopState && loopState.cycleIndex) || 0;
      var idPrefix = loopState ? "c" + cycleIndex : null;

      while (idx < evts.length && count < MAX_EVENTS_PER_BATCH) {
        var ev = evts[idx];
        var evSched = ev;
        if (idPrefix != null) {
          evSched = {};
          for (var kCopy in ev) evSched[kCopy] = ev[kCopy];
          evSched.id = idPrefix + ":" + ev.id;
        }
        if (batchStart < 0) batchStart = ev.start;
        batchEnd = ev.start;

        var ntp = this._playStartNTP + relOffset + ev.start;

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

        idx++;
        count++;
      }

      if (idx < evts.length) {
        var batchDuration = batchEnd - batchStart;
        var overlapTime = batchDuration * BATCH_OVERLAP_RATIO;
        var nextBatchNTP = this._playStartNTP + relOffset + batchStart + overlapTime;
        var delay = (nextBatchNTP - now) * 1000;
        this._batchTimeoutId = setTimeout(function() {
          self._scheduleBatch(evts, idx, pieceDur, token, relOffset, loopState);
        }, Math.max(1, delay));
      } else if (loopState) {
        var nextCycle = cycleIndex + 1;
        if (loopState.finiteCycles > 0 && nextCycle >= loopState.finiteCycles) {
          var endNTP = this._playStartNTP + relOffset + pieceDur;
          var remaining = (endNTP - now) * 1000;
          this._finishTimeoutId = setTimeout(function() {
            if (token !== self.stopToken) return;
            self.isPlaying = false;
            if (self.onFinish) self.onFinish();
            if (self._groupId != null) {
              self._freeGroupDeferred(self._groupId);
              self._groupId = null;
            }
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
            self._scheduleBatch(evts, 0, pieceDur, token, nextRelOffset, nextLoopState);
          }, Math.max(1, delay2));
        }
      } else {
        var endNTP = this._playStartNTP + relOffset + pieceDur;
        var remaining = (endNTP - now) * 1000;
        this._finishTimeoutId = setTimeout(function() {
          if (token !== self.stopToken) return;
          self.isPlaying = false;
          if (self.onFinish) self.onFinish();
          if (self._groupId != null) {
            self._freeGroupDeferred(self._groupId);
            self._groupId = null;
          }
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

      if (token !== this.stopToken) return;

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;

      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      var now = getNTP();
      var nowPerf = performance.now();
      this._playStartNTP = now + STARTUP_DELAY;
      this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;

      var scoreMeta = options.meta || null;
      var scoreControlData = options.controlData || null;

      if (scoreMeta && (scoreMeta.groups || scoreMeta.inserts) && typeof this.setupTracks === 'function') {
        this._createScoreGroup();
        await this.setupTracks(scoreMeta, this._scoreGroupId);
        if (scoreControlData && scoreControlData.bufferB64 && typeof this.setupControlEnvelopes === 'function') {
          await this.setupControlEnvelopes(scoreControlData, this._scoreGroupId);
        }
      } else {
        this._createGroup();
      }

      this.isPlaying = true;

      if (typeof this._scheduleControlSynths === 'function') {
        this._scheduleControlSynths(token);
      }

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

      this._scheduleBatch(evts, 0, basePieceDur, token, 0, loopState);
    }

    async stop() {
      this.stopToken++;
      this.isPlaying = false;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;
      this._cancelAllDeferredRings();
      this._freeGroup();
      this.nodeMap.clear();
      this._defNames.clear();
      this._trackMap = null;
      this._controlBusMap = [];
      this.drawScheduler.clear();
    }
  };
})();
