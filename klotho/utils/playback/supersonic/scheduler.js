(function() {
  if (globalThis.BrowserScheduler) return;
  globalThis.BrowserScheduler = class {
    constructor(config) {
      this.sonic = config.sonic;
      this.manifest = config.manifest || { synths: {}, inserts: {} };

      this.isPlaying = false;
      this.stopToken = 0;
      this._timers = [];
      this.nodeMap = new Map();
      this._synthNames = new Map();

      this.drawScheduler = new DrawScheduler();
      this.onEvent = null;
      this.onFinish = null;
    }

    _sendNew(ev) {
      if (ev.synthName === "__rest__") return;
      var nodeId = this.sonic.nextNodeId();
      var args = ['/s_new', ev.synthName, nodeId, 0, 0];
      var pf = ev.pfields || {};
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      this.sonic.send.apply(this.sonic, args);
      this.nodeMap.set(ev.id, nodeId);
      this._synthNames.set(ev.id, ev.synthName);
    }

    _sendSet(ev) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var args = ['/n_set', intId];
      var pf = ev.pfields || {};
      for (var key in pf) {
        if (!pf.hasOwnProperty(key)) continue;
        args.push(key, pf[key]);
      }
      this.sonic.send.apply(this.sonic, args);
    }

    _sendRelease(ev) {
      var intId = this.nodeMap.get(ev.id);
      if (intId == null) return;
      var synthName = this._synthNames.get(ev.id);
      var meta = (this.manifest.synths || {})[synthName];
      if (meta && meta.releaseMode === "free") {
        this.sonic.send('/n_free', intId);
      } else {
        this.sonic.send('/n_set', intId, (meta && meta.gateParam) || 'gate', 0);
      }
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

    play(events, options) {
      options = options || {};
      if (!options._skipStop) this.stop();
      else {
        for (var i = 0; i < this._timers.length; i++) clearTimeout(this._timers[i]);
        this._timers = [];
        this.nodeMap.clear();
        this._synthNames.clear();
      }

      var evts = events || [];
      this.onEvent = options.onEvent || null;
      this.onFinish = options.onFinish || null;

      if (evts.length === 0) {
        if (this.onFinish) this.onFinish();
        return;
      }

      this.isPlaying = true;
      var token = this.stopToken;
      var self = this;

      var pieceDur = this._computePieceDur(evts);

      for (var i = 0; i < evts.length; i++) {
        (function(ev) {
          var tid = setTimeout(function() {
            if (token !== self.stopToken) return;
            if (ev._stepIndex != null && self.onEvent) {
              self.onEvent(ev._stepIndex);
            }
            if (ev.type === "new") {
              self._sendNew(ev);
            } else if (ev.type === "set") {
              self._sendSet(ev);
            } else if (ev.type === "release") {
              self._sendRelease(ev);
            }
          }, ev.start * 1000);
          self._timers.push(tid);
        })(evts[i]);
      }

      var finishTid = setTimeout(function() {
        if (token !== self.stopToken) return;
        self.isPlaying = false;
        if (self.onFinish) self.onFinish();
      }, pieceDur * 1000);
      this._timers.push(finishTid);
    }

    stop() {
      this.stopToken++;
      this.isPlaying = false;
      for (var i = 0; i < this._timers.length; i++) clearTimeout(this._timers[i]);
      this._timers = [];
      this.nodeMap.clear();
      this._synthNames.clear();
      this.drawScheduler.clear();
      try { this.sonic.cancelAll(); } catch(e) {}
      try { this.sonic.send('/g_freeAll', 0); } catch(e) {}
    }
  };
})();
