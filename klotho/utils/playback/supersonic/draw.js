(function() {
  if (globalThis.DrawScheduler) return;
  globalThis.DrawScheduler = class {
    constructor() {
      this._queue = [];
      this._running = false;
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

    _startLoop() {
      this._running = true;
      var self = this;
      function tick() {
        if (!self._running) return;
        var now = performance.now();
        while (self._queue.length && self._queue[0].time <= now) {
          var item = self._queue.shift();
          item.callback();
        }
        if (self._queue.length || self._running) {
          requestAnimationFrame(tick);
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
