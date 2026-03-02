(function() {
  if (globalThis.BrowserScheduler) return;

  var MAX_EVENTS_PER_BATCH = 500;
  var BATCH_OVERLAP_RATIO = 0.8;
  var NTP_EPOCH_OFFSET = 2208988800;
  var STARTUP_DELAY = 0.1;
  var DEFAULT_RING_TIME = 5;

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
      this._groupId = null;

      this._playStartNTP = 0;
      this._playStartPerfMs = 0;
      this._batchTimeoutId = null;
      this._finishTimeoutId = null;
      this._loopTickId = null;
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
    }

    _freeGroupDeferred(groupId) {
      var sonic = this.sonic;
      var ringMs = this.ringTime * 1000;
      var tid = setTimeout(function() {
        try { sonic.send('/g_freeAll', groupId); } catch(e) {}
        try { sonic.send('/n_free', groupId); } catch(e) {}
      }, ringMs);
      this._deferredRings.push({ tid: tid, gid: groupId });
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

    _bundleNew(ev, ntp) {
      if (ev.defName === "__rest__") return;
      var defName = this._resolveDefName(ev.defName);
      var nodeId = this.sonic.nextNodeId();
      var target = this._groupId != null ? this._groupId : 0;
      var args = [defName, nodeId, 0, target];
      var pf = this._resolveDefPfields(defName, ev.pfields || {});
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
      this.sonic.sendOSC(bundle);
      this.nodeMap.set(ev.id, nodeId);
      this._defNames.set(ev.id, defName);
    }

    _bundleSet(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var args = [intId];
      var defName = this._defNames.get(ev.id);
      var pf = this._resolveDefPfields(defName, ev.pfields || {});
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
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

    _scheduleBatch(evts, startIdx, pieceDur, token, relOffset, suppressFinish, idPrefix) {
      if (token !== this.stopToken) return;

      var now = getNTP();
      var idx = startIdx;
      var batchStart = -1;
      var batchEnd = 0;
      var count = 0;
      var self = this;

      relOffset = relOffset || 0;
      suppressFinish = !!suppressFinish;

      while (idx < evts.length && count < MAX_EVENTS_PER_BATCH) {
        var ev = evts[idx];
        var evSched = ev;
        if (idPrefix != null) {
          evSched = {};
          for (var kCopy in ev) evSched[kCopy] = ev[kCopy];
          evSched.id = String(idPrefix) + ":" + ev.id;
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
          self._scheduleBatch(evts, idx, pieceDur, token, relOffset, suppressFinish, idPrefix);
        }, Math.max(1, delay));
      } else {
        if (!suppressFinish) {
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
    }

    async play(events, options) {
      options = options || {};
      this.stopToken++;
      var token = this.stopToken;

      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;

      if (options._skipStop && this._groupId != null) {
        this._freeGroupDeferred(this._groupId);
        this._groupId = null;
      } else {
        this._freeGroup();
      }

      this.nodeMap.clear();
      this._defNames.clear();
      this.drawScheduler.clear();

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
      if (!options._skipStop) {
        this._playStartNTP = now + STARTUP_DELAY;
        this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;
      } else {
        this._playStartNTP = now;
        this._playStartPerfMs = nowPerf;
      }

      this._createGroup();
      this.isPlaying = true;

      var pieceDur = this._computePieceDur(evts) + Math.max(0, options.tailPause || 0);
      var loopFinite = (typeof options.loop === "number" && Number.isFinite(options.loop) && options.loop > 1)
        ? Math.floor(options.loop)
        : 0;
      if (options.loop || loopFinite > 0) {
        this.playLoop(evts, {
          onEvent: this.onEvent,
          onFinish: this.onFinish,
          tailPause: options.tailPause != null ? options.tailPause : 0,
          finiteCycles: options.finiteCycles != null ? options.finiteCycles : (loopFinite > 0 ? loopFinite : null),
          lookaheadSec: options.lookaheadSec,
          tickMs: options.tickMs,
        });
        return;
      }

      this._scheduleBatch(evts, 0, pieceDur, token, 0, false, null);
    }

    playLoop(events, options) {
      options = options || {};
      this.stopToken++;
      var token = this.stopToken;

      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;

      this._freeGroup();
      this.nodeMap.clear();
      this._defNames.clear();
      this.drawScheduler.clear();

      if (token !== this.stopToken) return;

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;
      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      var basePieceDur = this._computePieceDur(evts);
      var tailPause = Math.max(0, options.tailPause || 0);
      var cycleDur = basePieceDur + tailPause;
      if (cycleDur <= 0) cycleDur = basePieceDur > 0 ? basePieceDur : 0.001;

      var lookaheadSec = options.lookaheadSec != null ? Math.max(0.1, options.lookaheadSec) : Math.max(0.8, Math.min(2.0, cycleDur));
      var tickMs = options.tickMs != null ? Math.max(10, options.tickMs) : 40;
      var finiteCycles = (typeof options.finiteCycles === "number" && Number.isFinite(options.finiteCycles) && options.finiteCycles > 0)
        ? Math.floor(options.finiteCycles)
        : 0;

      var now = getNTP();
      var nowPerf = performance.now();
      this._playStartNTP = now + STARTUP_DELAY;
      this._playStartPerfMs = nowPerf + STARTUP_DELAY * 1000;

      this._createGroup();
      this.isPlaying = true;

      if (finiteCycles > 0) {
        var endNTP = this._playStartNTP + (cycleDur * finiteCycles);
        var selfFinish = this;
        var finishToken = token;
        var finishRemaining = (endNTP - getNTP()) * 1000;
        this._finishTimeoutId = setTimeout(function() {
          if (finishToken !== selfFinish.stopToken) return;
          selfFinish.stopToken++;
          selfFinish.isPlaying = false;
          clearInterval(selfFinish._loopTickId);
          selfFinish._loopTickId = null;
          clearTimeout(selfFinish._batchTimeoutId);
          selfFinish._batchTimeoutId = null;
          if (selfFinish.onFinish) selfFinish.onFinish();
          if (selfFinish._groupId != null) {
            selfFinish._freeGroupDeferred(selfFinish._groupId);
            selfFinish._groupId = null;
          }
        }, Math.max(1, finishRemaining));
      }

      var self = this;
      var nextCycleIndex = 0;

      function enqueueReadyCycles() {
        if (token !== self.stopToken || !self.isPlaying) return;
        var nowRel = getNTP() - self._playStartNTP;
        var horizonRel = nowRel + lookaheadSec;
        while ((nextCycleIndex * cycleDur) <= horizonRel) {
          if (finiteCycles > 0 && nextCycleIndex >= finiteCycles) break;
          var relOffset = nextCycleIndex * cycleDur;
          self._scheduleBatch(
            evts,
            0,
            basePieceDur,
            token,
            relOffset,
            true,
            "loop" + nextCycleIndex
          );
          nextCycleIndex += 1;
        }
      }

      enqueueReadyCycles();
      this._loopTickId = setInterval(enqueueReadyCycles, tickMs);
    }

    async stop() {
      this.stopToken++;
      this.isPlaying = false;
      clearInterval(this._loopTickId);
      this._loopTickId = null;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;
      this._cancelAllDeferredRings();
      this._freeGroup();
      this.nodeMap.clear();
      this._defNames.clear();
      this.drawScheduler.clear();
    }
  };
})();
