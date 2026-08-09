// Finish-timing probe: a piece is over at its musical end PLUS the
// payload's trailing pause (V5). The V4 core computed
// ``pieceDur = basePieceDur + tailPause`` in play() and never used it —
// both finish arms armed at the base duration, so shape widgets (default
// pause 0.25) reset their visuals early by exactly the pause.
//
// Loads the real scheduler_core.js into a vm sandbox with a virtual
// clock, drives play() through onFinish, and reports when the finish arm
// actually fired. The mock engine implements the supersonic 0.71 reply
// surface used by the fast fence (`on('in')` delivering decoded
// [address, ...args] arrays), so the probe also exercises _fastSync and
// the teardown chain through onIdle.
//
// Usage: node finish_timing_probe.mjs <pause0|pause1|loop2-pause1>
// Prints JSON: { finishAtMs, idleFired, idleAfterFinish }

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const SS_DIR = join(HERE, '..', '..', 'klotho', 'utils', 'playback', 'supersonic');

// ---- virtual clock + timers -----------------------------------------------

let virtualMs = 0;
let nextTimerId = 1;
const timers = [];

function fakeSetTimeout(fn, delay) {
  const id = nextTimerId++;
  timers.push({ id, t: virtualMs + Math.max(0, delay || 0), fn });
  return id;
}

function fakeClearTimeout(id) {
  const i = timers.findIndex((t) => t.id === id);
  if (i >= 0) timers.splice(i, 1);
}

// ---- mock sonic ------------------------------------------------------------

const inListeners = new Set();
const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(addr, ...args) {
    if (addr === '/sync') {
      // Reply on a microtask, as the real transport does off the worklet
      // port; payload is the decoded flat array the 'in' event carries.
      queueMicrotask(() => {
        for (const cb of [...inListeners]) cb(['/synced', args[0]]);
      });
    }
  },
  on(evt, cb) {
    if (evt === 'in') inListeners.add(cb);
    return () => inListeners.delete(cb);
  },
  off(evt, cb) { inListeners.delete(cb); },
  async sync() {},
  purge() { return Promise.resolve(); },
  sendOSC() {},
  getMetrics() { return {}; },
};

// ---- sandbox ---------------------------------------------------------------

const sandbox = {
  performance: { timeOrigin: 0, now: () => virtualMs },
  setTimeout: fakeSetTimeout,
  clearTimeout: fakeClearTimeout,
  console: { log: () => {}, warn: () => {}, debug: () => {}, error: () => {} },
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: { osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) } },
};
vm.createContext(sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8'), sandbox);

// ---- run -------------------------------------------------------------------

const caseName = process.argv[2];
const tailPause = caseName === 'pause0' ? 0.0 : 1.0;
const loop = caseName === 'loop2-pause1' ? 2 : false;

// Two gated notes, base piece duration exactly 2.0 s.
const manifest = { gatedSynth: { gate: 1, amp: 0.5, freq: 440 } };
const events = [
  { type: 'new', id: 'e1', defName: 'gatedSynth', start: 0.0, dur: 1.0,
    releaseAfter: true, pfields: { amp: 0.5, freq: 440 } },
  { type: 'new', id: 'e2', defName: 'gatedSynth', start: 1.0, dur: 1.0,
    releaseAfter: true, pfields: { amp: 0.5, freq: 330 } },
];

const scheduler = new sandbox.BrowserScheduler({ sonic, manifest, ringTime: 0.1 });

let finishAtMs = null;
let idleFired = false;
let idleAfterFinish = false;
await scheduler.play(events, {
  tailPause,
  loop,
  onFinish: () => { finishAtMs = virtualMs; },
  onIdle: () => { idleFired = true; idleAfterFinish = finishAtMs != null; },
});

// Drain virtual timers, flushing microtasks between rounds so the async
// teardown chain (fast fence -> unregister -> purge -> onIdle) can
// progress and arm its own timers.
const RUNAWAY_MS = 60 * 1000;
for (let round = 0; round < 20; round++) {
  while (timers.length) {
    timers.sort((a, b) => a.t - b.t);
    const next = timers.shift();
    virtualMs = Math.max(virtualMs, next.t);
    if (virtualMs > RUNAWAY_MS) throw new Error('virtual clock runaway');
    next.fn();
  }
  await new Promise((r) => setImmediate(r));
}

process.stdout.write(JSON.stringify({ finishAtMs, idleFired, idleAfterFinish }));
