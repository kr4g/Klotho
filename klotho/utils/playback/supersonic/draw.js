(function() {
  if (globalThis.DrawScheduler) return;
  globalThis.DrawScheduler = class {
    constructor() {
      this._queue = [];
      this._running = false;
      // Bumped by each _startLoop so a tick from a superseded loop can
      // retire instead of re-arming beside the new one.
      this._epoch = 0;
    }

    schedule(callback, timeMs) {
      var lo = 0, hi = this._queue.length;
      while (lo < hi) {
        var mid = (lo + hi) >>> 1;
        if (this._queue[mid].time <= timeMs) lo = mid + 1;
        else hi = mid;
      }
      this._queue.splice(lo, 0, { time: timeMs, callback: callback });
      if (!this._running) this._startLoop();
    }

    // AUD-180: the loop must STOP when the queue drains.
    //
    // The re-arm condition used to be `queue.length || _running`, and
    // `_running` is only ever cleared by clear() -- so once a widget had
    // played, an empty-queue no-op callback ran on every single frame for
    // as long as the page stayed open, on every widget in the notebook.
    // The queue being empty is the whole signal: schedule() re-arms the
    // loop, so idling loses nothing.
    _startLoop() {
      this._running = true;
      var self = this;
      var epoch = ++this._epoch;
      function tick() {
        if (!self._running || self._epoch !== epoch) return;
        var now = performance.now();
        while (self._queue.length && self._queue[0].time <= now) {
          var item = self._queue.shift();
          try { item.callback(); } catch(e) {}
        }
        // A callback above may have called clear() and/or schedule(), which
        // starts a fresh loop; that bumps _epoch, and this one retires.
        if (!self._running || self._epoch !== epoch) return;
        if (self._queue.length) {
          requestAnimationFrame(tick);
        } else {
          self._running = false;
        }
      }
      requestAnimationFrame(tick);
    }

    clear() {
      this._queue = [];
      this._running = false;
    }
  };
})();
