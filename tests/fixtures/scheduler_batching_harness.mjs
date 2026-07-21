// Behavioral harness for the BrowserScheduler batching policy.
//
// Loads the real scheduler_core.js / scheduler_score.js sources into a vm
// sandbox with a virtual clock and virtual timers, drives play() to
// completion, and models the supersonic-scsynth engine as a 512-slot
// due-time queue that silently drops on overflow (the real engine's
// behavior, see supersonic-scsynth memory_profile.h SCHEDULER_SLOT_COUNT).
//
// Usage: node scheduler_batching_harness.mjs <case>
//   case: real-shape | all-gated | wall | control-envelopes | fx-automation
// Prints a JSON result on stdout:
//   { sent, dropped, peak, lateSends, finished, ctrlSendTimesMs, logs }

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const SS_DIR = join(HERE, '..', '..', 'klotho', 'utils', 'playback', 'supersonic');

const ENGINE_SLOTS = 512;
const NTP_EPOCH_OFFSET = 2208988800;

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

function nowNTP() {
  return virtualMs / 1000 + NTP_EPOCH_OFFSET;
}

// ---- engine model + mock sonic --------------------------------------------

const engine = { dues: [], dropped: 0, peak: 0, lateSends: 0, sent: 0 };
const ctrlSendTimesMs = [];
const nMapTimesMs = [];
const logs = [];

const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(addr) {
    if (addr === '/clearSched') engine.dues = [];
  },
  async sync() {},
  sendOSC(bundle) {
    engine.sent += 1;
    const now = nowNTP();
    if (bundle.ntp < now - 1e-6) engine.lateSends += 1;
    engine.dues = engine.dues.filter((d) => d > now);
    if (engine.dues.length >= ENGINE_SLOTS) {
      engine.dropped += 1;
      return;
    }
    engine.dues.push(bundle.ntp);
    if (engine.dues.length > engine.peak) engine.peak = engine.dues.length;
    if (bundle.args && bundle.args[0] === '__klEnvCtrl') {
      ctrlSendTimesMs.push(virtualMs);
    }
    if (bundle.addr === '/n_map') {
      nMapTimesMs.push(virtualMs);
    }
  },
  getMetrics() { return {}; },
};

// ---- sandbox ---------------------------------------------------------------

const sandbox = {
  performance: { timeOrigin: 0, now: () => virtualMs },
  setTimeout: fakeSetTimeout,
  clearTimeout: fakeClearTimeout,
  console: {
    log: (...a) => logs.push(a.join(' ')),
    warn: (...a) => logs.push(a.join(' ')),
    debug: (...a) => logs.push(a.join(' ')),
    error: (...a) => logs.push(a.join(' ')),
  },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: {
    osc: {
      encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }),
    },
  },
};
vm.createContext(sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8'), sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8'), sandbox);

// ---- payloads --------------------------------------------------------------

const manifest = {
  gatedSynth: { gate: 1, amp: 0.5, freq: 440 },
  percSynth: { amp: 0.5, freq: 440 },
};

function ev(i, start, dur, gated) {
  return {
    type: 'new',
    id: 'e' + i,
    defName: gated ? 'gatedSynth' : 'percSynth',
    start,
    dur,
    releaseAfter: true,
    pfields: { amp: 0.5, freq: 440 },
  };
}

function buildCase(name) {
  const events = [];
  let controlData = null;
  let meta = null;

  if (name === 'real-shape') {
    // The Aphex notebook shape: sparse 56 s intro, dense 34 s tail;
    // ~25% gated, a sprinkling of long-sustain pads.
    for (let i = 0; i < 300; i++) {
      const gated = i % 4 === 0;
      events.push(ev(i, (i * 56) / 300, i % 20 === 0 ? 5 : 0.2, gated));
    }
    for (let i = 300; i < 835; i++) {
      const gated = i % 4 === 0;
      events.push(ev(i, 56 + ((i - 300) * 34) / 535, 0.2, gated));
    }
  } else if (name === 'all-gated') {
    for (let i = 0; i < 1000; i++) {
      events.push(ev(i, (i * 60) / 1000, 2, true));
    }
  } else if (name === 'wall') {
    // 600 gated events at the same instant: 1200 bundles due in a burst.
    // The occupancy gate must degrade to late delivery, never drops.
    for (let i = 0; i < 600; i++) {
      events.push(ev(i, 5.0, 1, true));
    }
  } else if (name === 'control-envelopes') {
    for (let i = 0; i < 500; i++) {
      events.push(ev(i, (i * 100) / 500, 0.2, false));
    }
    const nDesc = 300;
    const blockSize = 4;
    const descriptors = [];
    for (let i = 0; i < nDesc; i++) {
      descriptors.push({
        blockIndex: i,
        start: (i * 100) / nDesc,
        dur: 1,
        pfields: ['amp'],
        targets: [],
      });
    }
    controlData = {
      bufferB64: Buffer.alloc(nDesc * blockSize * 4).toString('base64'),
      numFrames: nDesc * blockSize,
      blockSize,
      descriptors,
    };
  } else if (name === 'fx-automation') {
    // Insert-FX automation: per-section 'set' events all sharing the FX's
    // uid, one control envelope per section targeting that uid. The
    // scheduler must wire exactly one /n_map per envelope (exact
    // start-time match in _bundleSet), never one per (event, envelope).
    const S = 12;
    const blockSize = 4;
    const descriptors = [];
    for (let k = 0; k < S; k++) {
      const t = k * 5;
      events.push({ type: 'set', id: 'fx1', defName: null, start: t,
                    pfields: { mix: 0.1 + k * 0.05 } });
      descriptors.push({ blockIndex: k, start: t, dur: 5, pfields: ['mix'],
                         targets: [{ id: 'fx1', startTime: t }] });
    }
    for (let i = 0; i < 50; i++) {
      events.push(ev(i, i * 1.2, 0.2, false));
    }
    controlData = {
      bufferB64: Buffer.alloc(S * blockSize * 4).toString('base64'),
      numFrames: S * blockSize,
      blockSize,
      descriptors,
    };
    meta = { groups: ['t'], inserts: { t: [{ defName: 'fxDef', uid: 'fx1', args: {} }] } };
  } else {
    throw new Error('unknown case: ' + name);
  }

  events.sort((a, b) => a.start - b.start);
  return { events, controlData, meta };
}

// ---- run -------------------------------------------------------------------

const caseName = process.argv[2];
const { events, controlData, meta } = buildCase(caseName);

const scheduler = new sandbox.BrowserScheduler({
  sonic,
  manifest,
  ringTime: 0.1,
});

let finished = false;
await scheduler.play(events, {
  controlData,
  meta,
  onFinish: () => { finished = true; },
});

// Drain the virtual timer queue, advancing the clock to each firing.
const RUNAWAY_MS = 6 * 3600 * 1000;
while (timers.length) {
  timers.sort((a, b) => a.t - b.t);
  const next = timers.shift();
  virtualMs = Math.max(virtualMs, next.t);
  if (virtualMs > RUNAWAY_MS) throw new Error('virtual clock runaway — scheduler never finished');
  next.fn();
}

process.stdout.write(JSON.stringify({
  sent: engine.sent,
  dropped: engine.dropped,
  peak: engine.peak,
  lateSends: engine.lateSends,
  finished,
  ctrlSendTimesMs,
  nMapTimesMs,
  logs,
}));
