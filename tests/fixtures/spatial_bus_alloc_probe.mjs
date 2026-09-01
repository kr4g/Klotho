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
//   two_widgets   two schedulers ALIVE AT ONCE, one ringing out under the
//                 other — the interleaving a pairwise-disjointness check on
//                 one scheduler's allocations cannot see
//   ring_out_reclaims  one widget alone: the reclaim must still happen
//   stale_floor   a stale pre-10.16 page (cursor 16) loaded first
//   exhaust       allocate until the budget refuses (even width, 24)
//   exhaust_odd   the same, at an ODD width, where rounding decides the edge
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
// Deferred ring-outs are the whole point of the two-widget scenarios, so
// timers are queued rather than dropped and fired on demand.
const timers = new Map();
let nextTimerId = 1;
function runTimers() {
  const due = [...timers.entries()];
  timers.clear();
  for (const [, fn] of due) fn();
  return due.length;
}
const sandbox = {
  performance: { timeOrigin: 0, now: () => virtualMs },
  setTimeout: (fn) => { const id = nextTimerId++; timers.set(id, fn); return id; },
  clearTimeout: (id) => { timers.delete(id); },
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

} else if (scenario === 'two_widgets') {
  // TWO WIDGETS ALIVE AT ONCE on one page, which is the case a per-widget
  // disjointness check cannot reach: A is still ringing out when B starts.
  //
  //   A plays a stereo pair (+ control buses)
  //   B plays a 24-wide spatial run (+ control buses) while A rings
  //   A allocates AGAIN, still mid-play, after B has moved the cursor
  //   A's ring-out timer fires -- A frees
  //   C (the next play on the page) allocates
  //
  // Nothing A or C is handed may land inside B's live run. Both cursors are
  // driven, because _allocControlBus has the same shape as the audio one.
  // Every allocation is reported individually, so Python can compare every
  // pair rather than trusting a range.
  const A = newScheduler();
  A._beginBusRuns();
  const aAudio = [alloc(A, 2, 'stereo'), alloc(A, 2, 'stereo')];
  const aCtrl = [A._allocControlBus(), A._allocControlBus()];

  const B = newScheduler();
  B._beginBusRuns();
  const bAudio = [alloc(B, 24, 'wide')];
  const bCtrl = [B._allocControlBus(), B._allocControlBus(), B._allocControlBus()];

  // A is STILL PLAYING and allocates again. Its own cursor is stale by 24
  // channels now, so drawing from it would land inside B's live run.
  aAudio.push(alloc(A, 2, 'stereo'));
  aCtrl.push(A._allocControlBus());

  out.aAllocations = aAudio;
  out.bAllocations = bAudio;
  out.aControlBuses = aCtrl;
  out.bControlBuses = bCtrl;
  out.aAudio = [aAudio[0].start, aAudio[aAudio.length - 1].localCursor];
  out.bAudio = [bAudio[0].start, bAudio[bAudio.length - 1].localCursor];
  out.aControl = [aCtrl[0], aCtrl[aCtrl.length - 1] + 1];
  out.bControl = [bCtrl[0], bCtrl[bCtrl.length - 1] + 1];
  out.globalBeforeRingOut = {
    audio: sandbox.__klothoBusAlloc.nextAudio,
    control: sandbox.__klothoBusAlloc.nextControl,
  };

  // A finishes and rings out. B is still sounding.
  A._groupId = 999;
  A._freeGroupDeferred(999);
  out.timersPending = timers.size;
  out.timersFired = runTimers();
  out.globalAfterRingOut = {
    audio: sandbox.__klothoBusAlloc.nextAudio,
    control: sandbox.__klothoBusAlloc.nextControl,
  };

  const C = newScheduler();
  C._beginBusRuns();
  const cAudio = [alloc(C, 24, 'wide')];
  const cCtrl = [C._allocControlBus(), C._allocControlBus()];
  out.cAllocations = cAudio;
  out.cControlBuses = cCtrl;
  out.cAudio = [cAudio[0].start, cAudio[cAudio.length - 1].localCursor];
  out.cControl = [cCtrl[0], cCtrl[cCtrl.length - 1] + 1];

} else if (scenario === 'ring_out_reclaims') {
  // The other half of the trade: one widget alone must still get its buses
  // back, or the page runs out after a few dozen plays. A ring-out with
  // nothing allocated above it is the reclaimable case.
  const s = newScheduler();
  s._beginBusRuns();
  out.first = [alloc(s, 2, 'stereo'), alloc(s, 24, 'wide')];
  out.firstControl = [s._allocControlBus(), s._allocControlBus()];
  out.globalBeforeRingOut = {
    audio: sandbox.__klothoBusAlloc.nextAudio,
    control: sandbox.__klothoBusAlloc.nextControl,
  };
  s._groupId = 777;
  s._freeGroupDeferred(777);
  out.timersFired = runTimers();
  out.globalAfterRingOut = {
    audio: sandbox.__klothoBusAlloc.nextAudio,
    control: sandbox.__klothoBusAlloc.nextControl,
  };
  s._beginBusRuns();
  out.second = [alloc(s, 2, 'stereo')];
  out.secondControl = [s._allocControlBus()];
  // A second free with nothing above it must also give everything back.
  s._groupId = 778;
  s._freeGroupDeferred(778);
  runTimers();
  out.globalAfterSecondRingOut = {
    audio: sandbox.__klothoBusAlloc.nextAudio,
    control: sandbox.__klothoBusAlloc.nextControl,
  };

} else if (scenario === 'stop_paths') {
  // The other two ways a range comes back: the immediate _freeGroup() a
  // stop() does, and _cancelAllDeferredRings() cancelling a ring that has
  // not fired. Both read the same ledger, and a stop that threw would be a
  // stuck transport rather than a quiet overlap.
  const s = newScheduler();
  s._beginBusRuns();
  out.beforeAll = sandbox.__klothoBusAlloc.nextAudio;

  s._groupId = 1;
  out.immediate = [alloc(s, 24, 'wide'), alloc(s, 2, 'stereo')];
  s._freeGroup();
  out.afterFreeGroup = sandbox.__klothoBusAlloc.nextAudio;

  s._beginBusRuns();
  s._groupId = 2;
  out.deferred = [alloc(s, 16, 'wide')];
  s._freeGroupDeferred(2);
  out.ringsPending = s._deferredRings.length;
  s._cancelAllDeferredRings();          // stop() before the ring fired
  out.afterCancel = sandbox.__klothoBusAlloc.nextAudio;
  out.ringsAfterCancel = s._deferredRings.length;
  out.timersLeft = timers.size;

} else if (scenario === 'double_reclaim') {
  // Defence in depth: no path frees one play's ledger twice today, so this
  // drives _reclaimBusRuns directly. A second reclaim of a ledger that has
  // already been given back must be a no-op even when the cursor happens to
  // have returned to the same number -- by then those channels belong to
  // somebody else.
  const s = newScheduler();
  s._beginBusRuns();
  out.mine = [alloc(s, 2, 'stereo'), alloc(s, 2, 'stereo')];
  const stale = s._audioBusRuns;          // the reference a ring entry holds
  const staleCtrl = s._controlBusRuns;
  s._reclaimBusRuns(stale, staleCtrl);
  out.afterFirstReclaim = sandbox.__klothoBusAlloc.nextAudio;

  const other = newScheduler();
  other._beginBusRuns();
  out.other = [alloc(other, 2, 'stereo'), alloc(other, 2, 'stereo')];
  out.afterOther = sandbox.__klothoBusAlloc.nextAudio;

  s._reclaimBusRuns(stale, staleCtrl);    // stray second free
  out.afterSecondReclaim = sandbox.__klothoBusAlloc.nextAudio;

} else if (scenario === 'stale_floor') {
  const s = newScheduler();
  out.staleCursorBefore = 16;
  out.allocations = [
    alloc(s, 2, 'stereo'), alloc(s, 24, 'wide'), alloc(s, 2, 'stereo'),
  ];

} else if (scenario === 'exhaust' || scenario === 'exhaust_odd') {
  // Even width divides the budget cleanly; an ODD one does not, and the
  // round-up-to-even means the last run that fits is decided by the
  // RESERVED width, not the asked-for one. That boundary is its own case.
  // 25 divides 125 - 48 = 77 into three runs of ASKED-for width but only
  // two of RESERVED width, so a budget check written against the asked-for
  // width lets the last one reserve past the end.
  const runWidth = scenario === 'exhaust_odd' ? 25 : 24;
  const s = newScheduler();
  out.runWidth = runWidth;
  out.allocations = [];
  out.threw = false;
  out.message = null;
  for (let i = 0; i < 500; i++) {
    try {
      out.allocations.push(alloc(s, runWidth, 'wide'));
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
