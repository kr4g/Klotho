// Behavioral probe for the shared private-audio-bus allocator.
//
// Loads the REAL scheduler_core.js / scheduler_score.js into a vm sandbox and
// drives _allocAudioBus() / _allocAudioBusN(width) directly, so the assertions
// are about what the shipped sources actually hand out — not about their text.
//
// The property that matters: both entry points step ONE page-global cursor
// (globalThis.__klothoBusAlloc), so a stereo allocation and a 24-wide spatial
// allocation can never overlap. An overlap is two unrelated voices silently
// summing into each other.
//
// Usage: node spatial_bus_alloc_probe.mjs <scenario> [capacity]
//
//   stereo_only   pure _allocAudioBus() sequence (pre-change behavior)
//   mixed         interleaved _allocAudioBus() / _allocAudioBusN(N)
//   two_includes  the sources included TWICE, with a second scheduler after
//   stale_floor   a stale pre-10.16 page (cursor 16) loaded first
//   exhaust       allocate until the budget refuses
//   bad_width     every rejected width shape
//   setup_tracks  the real setupTracks(), reporting its bus assignments
//
// Prints one JSON object per scenario; every assertion lives in
// tests/test_spatial_bus_allocation.py.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const SS_DIR = join(HERE, '..', '..', 'klotho', 'utils', 'playback', 'supersonic');
const CORE_SRC = readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8');
const SCORE_SRC = readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8');

const scenario = process.argv[2];
const capacity = process.argv[3] ? Number(process.argv[3]) : null;

let virtualMs = 0;
const sends = [];
const sandbox = {
  performance: { timeOrigin: 0, now: () => virtualMs },
  setTimeout: () => 1,
  clearTimeout: () => {},
  console: { log: () => {}, warn: () => {}, debug: () => {}, error: () => {} },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: { osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) } },
};
const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(...args) { sends.push(args); },
  purge() {},
  async sync() {},
  sendOSC() {},
  getMetrics() { return {}; },
};
vm.createContext(sandbox);

// The ss_init boot stash the allocator reads its budget from. Omitted
// entirely when no capacity is given, which is the stale-page state (no
// bootConfig) — the allocator must then fall back on its own.
if (capacity != null) {
  sandbox.__klothoSonic = { bootConfig: { scsynthOptions: { numAudioBusChannels: capacity } } };
}

if (scenario === 'stale_floor') {
  // A pre-10.16 page: old bus floor (16) and a scheduler with no
  // setupTracks/_allocAudioBusN. The core's floor guard must lift the shared
  // cursor to 48 before anything is handed out.
  vm.runInContext(`
    globalThis.__klothoBusAlloc = { nextAudio: 16, nextControl: 0 };
    globalThis.BrowserScheduler = class {
      constructor(cfg) { this.sonic = cfg.sonic; this.manifest = cfg.manifest || {};
        this.isPlaying = false; this.stopToken = 0; this.nodeMap = new Map();
        this._defNames = new Map(); this._trackMap = null; }
      async play() {} async stop() {}
    };
    globalThis.BrowserScheduler.prototype.setupTracks = async function() { this._trackMap = {}; };
  `, sandbox);
}

function loadSources() {
  vm.runInContext(CORE_SRC, sandbox);
  vm.runInContext(SCORE_SRC, sandbox);
}

function newScheduler() {
  return new sandbox.BrowserScheduler({
    sonic, manifest: { percSynth: { amp: 0.5 } }, ringTime: 0.1,
  });
}

// One allocation record: what was asked for, where it landed, and where the
// two cursors stood afterwards. Python turns these into ranges.
function alloc(sched, width, tag) {
  const start = (width === 2 && tag === 'stereo')
    ? sched._allocAudioBus()
    : sched._allocAudioBusN(width);
  return {
    via: tag,
    width,
    start,
    localCursor: sched._nextAudioBus,
    globalCursor: sandbox.__klothoBusAlloc.nextAudio,
  };
}

loadSources();
const out = { scenario, capacity, firstPrivateBus: 48 };

if (scenario === 'stereo_only') {
  const s = newScheduler();
  out.allocations = [];
  for (let i = 0; i < 8; i++) out.allocations.push(alloc(s, 2, 'stereo'));

} else if (scenario === 'mixed') {
  const s = newScheduler();
  // Deliberately interleaved, and deliberately including an ODD width so the
  // rounding decision is exercised rather than assumed.
  const plan = [
    ['stereo', 2], ['wide', 24], ['stereo', 2], ['wide', 1],
    ['stereo', 2], ['wide', 24], ['wide', 3], ['stereo', 2],
    ['wide', 2], ['stereo', 2], ['wide', 16],
  ];
  out.allocations = plan.map(([tag, w]) => alloc(s, w, tag));

} else if (scenario === 'two_includes') {
  const a = newScheduler();
  out.first = [alloc(a, 2, 'stereo'), alloc(a, 24, 'wide'), alloc(a, 2, 'stereo')];
  // A second widget's <script> tags run the same sources again. The install
  // guards no-op, and a NEW scheduler must continue the page-global cursor.
  loadSources();
  out.reinstalled = a.constructor === sandbox.BrowserScheduler;
  const b = newScheduler();
  out.second = [alloc(b, 24, 'wide'), alloc(b, 2, 'stereo'), alloc(b, 7, 'wide')];

} else if (scenario === 'stale_floor') {
  const s = newScheduler();
  out.staleCursorBefore = 16;
  out.allocations = [
    alloc(s, 2, 'stereo'), alloc(s, 24, 'wide'), alloc(s, 2, 'stereo'),
  ];

} else if (scenario === 'exhaust') {
  const s = newScheduler();
  out.allocations = [];
  out.threw = false;
  out.message = null;
  for (let i = 0; i < 500; i++) {
    try {
      out.allocations.push(alloc(s, 24, 'wide'));
    } catch (e) {
      out.threw = true;
      out.message = String(e && e.message);
      out.localCursorAfterThrow = s._nextAudioBus;
      out.globalCursorAfterThrow = sandbox.__klothoBusAlloc.nextAudio;
      break;
    }
  }
  out.reportedCapacity = s._audioBusCapacity();

} else if (scenario === 'bad_width') {
  const s = newScheduler();
  const cursorBefore = s._nextAudioBus;
  const cases = [
    ['zero', 0], ['negative', -2], ['fractional', 2.5], ['string', '24'],
    ['nan', NaN], ['infinity', Infinity], ['absurd', 1000000],
    ['null', null], ['undefined', undefined],
  ];
  out.cases = cases.map(([name, w]) => {
    let threw = false, message = null, returned = null;
    try { returned = s._allocAudioBusN(w); } catch (e) { threw = true; message = String(e && e.message); }
    return { name, threw, message, returned };
  });
  out.cursorBefore = cursorBefore;
  out.cursorAfter = s._nextAudioBus;
  out.globalCursorAfter = sandbox.__klothoBusAlloc.nextAudio;

} else if (scenario === 'setup_tracks') {
  const s = newScheduler();
  const meta = { groups: ['drums', 'keys'], inserts: { keys: [{ defName: 'kl_reverb', uid: 'fx1', args: {} }] } };
  await s.setupTracks(meta, 900);
  out.trackBuses = {};
  for (const name of ['drums', 'keys', 'main']) {
    const t = s._trackMap[name];
    out.trackBuses[name] = { srcBus: t.srcBus, fxBus: t.fxBus };
  }
  out.globalCursor = sandbox.__klothoBusAlloc.nextAudio;
  out.routerSends = sends
    .filter((m) => m[0] === '/s_new' && m[1] === '__busRouter')
    .map((m) => ({ inBus: m[6], outBus: m[8] }));

} else {
  throw new Error('unknown scenario: ' + scenario);
}

process.stdout.write(JSON.stringify(out));
