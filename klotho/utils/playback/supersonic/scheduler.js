(function() {
  if (globalThis.BrowserScheduler) return;

  var MAX_EVENTS_PER_BATCH = 500;
  var BATCH_OVERLAP_RATIO = 0.8;
  var NTP_EPOCH_OFFSET = 2208988800;
  var STARTUP_DELAY = 0.1;

  function getNTP() {
    return (performance.timeOrigin + performance.now()) / 1000 + NTP_EPOCH_OFFSET;
  }

  globalThis.BrowserScheduler = class {
    constructor(config) {
      this.sonic = config.sonic;
      this.manifest = config.manifest || { synths: {}, inserts: {} };

      this.isPlaying = false;
      this.stopToken = 0;
      this.nodeMap = new Map();
      this._synthNames = new Map();
      this._groupId = null;

      this._playStartNTP = 0;
      this._playStartPerfMs = 0;
      this._batchTimeoutId = null;
      this._finishTimeoutId = null;

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

    _bundleNew(ev, ntp) {
      if (ev.synthName === "__rest__") return;
      var nodeId = this.sonic.nextNodeId();
      var target = this._groupId != null ? this._groupId : 0;
      var args = [ev.synthName, nodeId, 0, target];
      var pf = ev.pfields || {};
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/s_new', args);
      this.sonic.sendOSC(bundle);
      this.nodeMap.set(ev.id, nodeId);
      this._synthNames.set(ev.id, ev.synthName);
    }

    _bundleSet(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var args = [intId];
      var pf = ev.pfields || {};
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      var bundle = globalThis.SuperSonic.osc.encodeSingleBundle(ntp, '/n_set', args);
      this.sonic.sendOSC(bundle);
    }

    _bundleRelease(ev, ntp) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var synthName = this._synthNames.get(ev.id);
      var meta = (this.manifest.synths || {})[synthName];
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

    _scheduleBatch(evts, startIdx, pieceDur, token) {
      if (token !== this.stopToken) return;

      var now = getNTP();
      var idx = startIdx;
      var batchStart = -1;
      var batchEnd = 0;
      var count = 0;
      var self = this;

      while (idx < evts.length && count < MAX_EVENTS_PER_BATCH) {
        var ev = evts[idx];
        if (batchStart < 0) batchStart = ev.start;
        batchEnd = ev.start;

        var ntp = this._playStartNTP + ev.start;

        if (ev.type === "new") {
          this._bundleNew(ev, ntp);
        } else if (ev.type === "set") {
          this._bundleSet(ev, ntp);
        } else if (ev.type === "release") {
          this._bundleRelease(ev, ntp);
        }

        if (ev.type === "new" && ev._stepIndex != null && this.onEvent) {
          (function(ds, cb, si, ms) {
            ds.schedule(function() { cb(si); }, ms);
          })(self.drawScheduler, self.onEvent, ev._stepIndex,
             self._playStartPerfMs + ev.start * 1000);
        }

        idx++;
        count++;
      }

      if (idx < evts.length) {
        var batchDuration = batchEnd - batchStart;
        var overlapTime = batchDuration * BATCH_OVERLAP_RATIO;
        var nextBatchNTP = this._playStartNTP + batchStart + overlapTime;
        var delay = (nextBatchNTP - now) * 1000;
        this._batchTimeoutId = setTimeout(function() {
          self._scheduleBatch(evts, idx, pieceDur, token);
        }, Math.max(1, delay));
      } else {
        var endNTP = this._playStartNTP + pieceDur;
        var remaining = (endNTP - now) * 1000;
        this._finishTimeoutId = setTimeout(function() {
          if (token !== self.stopToken) return;
          self._freeGroup();
          self.isPlaying = false;
          if (self.onFinish) self.onFinish();
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

      await this.sonic.purge();
      this._freeGroup();
      this.nodeMap.clear();
      this._synthNames.clear();
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

      var pieceDur = this._computePieceDur(evts);
      this._scheduleBatch(evts, 0, pieceDur, token);
    }

    async stop() {
      this.stopToken++;
      this.isPlaying = false;
      clearTimeout(this._batchTimeoutId);
      this._batchTimeoutId = null;
      clearTimeout(this._finishTimeoutId);
      this._finishTimeoutId = null;
      await this.sonic.purge();
      this._freeGroup();
      this.nodeMap.clear();
      this._synthNames.clear();
      this.drawScheduler.clear();
    }
  };
})();
