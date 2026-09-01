// Behavioral probe for multichannel (speaker-array) routing.
//
// Loads the REAL scheduler_core.js / scheduler_score.js into a vm sandbox
// against a fake `sonic` that records every OSC message, then drives
// setupTracks() and _bundleNew()/_bundleSet() directly. Every assertion in
// tests/test_spatial_routing_js.py is therefore about messages the shipped
// sources actually send, not about their text.
//
// --src <dir> loads the two sources from somewhere else, which is how the
// A/B against a pre-change checkout is run: the same scenario, the same fake
// engine, two source trees, one comparison.
//
// Usage: node spatial_routing_probe.mjs <scenario> [--src <dir>]
//
//   nonspatial    a plain two-track score with an insert -- the transcript
//                 that must not move
//   lanes         one 8-speaker track: several lanes, two voices on the same
//                 speaker, two on different ones
//   chain         a 6-wide spatial track with two inserts, end to end
//   geometry      the /b_alloc -> /sync -> /b_setn fence and the decoder
//   ordering      node ids and add-actions of every array writer vs. the
//                 decoder
//   no_decoder    a labels-only array: no fold is possible
//   mixed         a spatial track and a stereo track in one score
//   main_only     the array declared on "main", so meta has no groups
//   slur          a /n_set on a spatial voice keeps its speaker
//   too_wide      a 40-speaker array must be refused, loudly
//   bad_width     non-integer / zero widths
//   missing_def   an off-family width whose SynthDef the page does not have
//   replay        two setupTracks calls on one scheduler: one buffer, one
//                 fence
//   payload       --payload <file>: a REAL lowered score, straight out of
//                 converters.py, driven end to end. This is the one scenario
//                 whose input nothing in this file invented.
//
// Prints one JSON object.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const scenario = argv[0];
const srcIx = argv.indexOf('--src');
const SS_DIR = srcIx !== -1
  ? argv[srcIx + 1]
  : join(HERE, '..', '..', 'klotho', 'utils', 'playback', 'supersonic');

const CORE_SRC = readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8');
const SCORE_SRC = readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8');

// Every OSC message, in order, direct sends and timestamped bundles alike.
const log = [];
let syncCount = 0;
const warnings = [];

const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(...args) { log.push({ k: 'send', msg: args }); },
  sendOSC(bundle) { log.push({ k: 'bundle', ...bundle }); },
  purge() {},
  async sync() { syncCount++; log.push({ k: 'sync', n: syncCount }); },
  getMetrics() { return {}; },
};

const sandbox = {
  performance: { timeOrigin: 0, now: () => 0 },
  setTimeout: (fn) => 1,
  clearTimeout: () => {},
  console: {
    log: () => {}, debug: () => {}, error: () => {},
    warn: (...a) => { warnings.push(a.join(' ')); },
  },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: {
    osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) },
  },
  // The boot stash: a generous bus budget, and the shared buffer-number
  // cursor the geometry upload draws from.
  __klothoSonic: {
    bootConfig: { scsynthOptions: { numAudioBusChannels: 1024 } },
    _nextBufnum: 7,
  },
  // The page's merged SynthDef registry. requireDef() consults this, so a
  // scenario that wants the "off-family width" refusal simply leaves the
  // name out.
  __klothoSynthdefAssets: {
    '__busRouter': 'x', '__busRouterMonitor': 'x', '__chainLimiter': 'x',
    '__klEnvCtrl': 'x', 'kl_tri': 'x', 'kl_saw': 'x', 'kl_reverb6': 'x',
    '__busRouter1': 'x', '__busRouter4': 'x', '__busRouter6': 'x',
    '__busRouter8': 'x', '__busRouter12': 'x', '__busRouter16': 'x',
    '__busRouter24': 'x', '__busRouter32': 'x',
    '__spatialDecode1': 'x', '__spatialDecode4': 'x', '__spatialDecode6': 'x',
    '__spatialDecode8': 'x', '__spatialDecode12': 'x', '__spatialDecode16': 'x',
    '__spatialDecode24': 'x', '__spatialDecode32': 'x', '__spatialDecode2': 'x',
  },
};
vm.createContext(sandbox);
vm.runInContext(CORE_SRC, sandbox);
vm.runInContext(SCORE_SRC, sandbox);

function newScheduler() {
  return new sandbox.BrowserScheduler({
    sonic,
    manifest: { kl_tri: { amp: 0.5, gate: 1 }, kl_saw: { amp: 0.5 } },
    ringTime: 0.1,
  });
}

// A plausible geometry table: six fields per lane, all inside the ranges
// klotho.thetos.spatial guarantees (delays 0..0.33 s, gains 0..1, shadow
// cutoffs above 0). The exact numbers do not matter; their ORDER does, and
// they are distinct per lane so a misread is visible.
function coefficients(width) {
  const flat = [];
  for (let lane = 0; lane < width; lane++) {
    flat.push(
      0.001 * lane,            // delay_l
      0.002 * lane,            // delay_r
      1 - 0.01 * lane,         // gain_l
      0.9 - 0.01 * lane,       // gain_r
      18000 - 100 * lane,      // shadow_l_hz
      17000 - 100 * lane,      // shadow_r_hz
    );
  }
  return flat;
}

function arrayMeta(name, width, { geometry = true } = {}) {
  const labels = [];
  for (let i = 0; i < width; i++) labels.push('S' + (i + 1));
  const entry = {
    name, labels, width,
    positions: null, units: null, speedOfSound: null, decoder: null,
  };
  if (geometry) {
    entry.positions = labels.map((_, i) => [i, 0]);
    entry.units = 'meters';
    entry.speedOfSound = 343.0;
    entry.decoder = {
      kind: 'binaural', listener: [0, 0], facing: 0.0, headHalf: 0.09,
      fields: ['delay_l', 'delay_r', 'gain_l', 'gain_r',
        'shadow_l_hz', 'shadow_r_hz'],
      stride: 6, maxDelay: 0.33, coefficients: coefficients(width),
    };
  }
  return entry;
}

function ev(id, group, lane, extra) {
  const e = {
    id, type: 'new', defName: 'kl_tri', start: 0, dur: 1, group,
    pfields: { freq: 220 + id, amp: 0.3 },
  };
  if (lane != null) { e.speakerLane = lane; e.speaker = 'S' + (lane + 1); }
  return Object.assign(e, extra || {});
}

// Only the messages a routing question is about.
const sNews = () => log.filter((m) => m.k === 'send' && m.msg[0] === '/s_new')
  .map((m) => m.msg);
const newBundles = () => log.filter((m) => m.k === 'bundle' && m.addr === '/s_new')
  .map((m) => m.args);
const setBundles = () => log.filter((m) => m.k === 'bundle' && m.addr === '/n_set')
  .map((m) => m.args);

// out= as it actually reaches scsynth, per event id.
function outsByEvent(args) {
  const ix = args.indexOf('out');
  return ix === -1 ? null : args[ix + 1];
}

const out = { scenario, srcDir: SS_DIR };

async function run() {
  if (scenario === 'nonspatial') {
    // The transcript that must not move. Two tracks, one insert chain, four
    // voices, one of them slurred -- every code path the change touches,
    // with no speaker array anywhere in sight.
    const s = newScheduler();
    const meta = {
      groups: ['drums', 'keys'],
      inserts: { keys: [{ defName: 'kl_reverb', uid: 'fx1', args: { mix: 0.3 } }] },
    };
    await s.setupTracks(meta, 900);
    const evts = [
      ev(1, 'drums'), ev(2, 'keys'), ev(3, 'default'), ev(4, 'nosuchtrack'),
    ];
    evts.forEach((e, i) => s._bundleNew(e, 100 + i));
    s._bundleSet(Object.assign(ev(1, 'drums'), { type: 'set' }), 110);
    out.log = log;
    out.warnings = warnings;

  } else if (scenario === 'lanes') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { pavilion: arrayMeta('pavilion', 8) },
        tracks: { array: { array: 'pavilion', width: 8 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.srcBus = s._trackMap.array.srcBus;
    out.width = s._trackMap.array.width;
    // Lane 7 is the LAST speaker of an 8-wide array: legal only for a
    // 1-channel point source, since a 2-channel instrument occupies the
    // speaker it names and the one above it. converters.py enforces that;
    // here it is simply the top of the run, which is the offset worth
    // checking because it is the one an off-by-one walks off the end of.
    const lanes = [0, 1, 3, 7, 3, 0];
    lanes.forEach((lane, i) => s._bundleNew(ev(10 + i, 'array', lane), 200 + i));
    // A voice with NO speaker on the same (spatial) track: lane 0.
    s._bundleNew(ev(99, 'array'), 300);
    out.outs = newBundles().map(outsByEvent);
    out.lanes = lanes;

  } else if (scenario === 'chain') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      inserts: {
        array: [
          { defName: 'kl_reverb6', uid: 'fx1', args: {} },
          { defName: 'kl_reverb6', uid: 'fx2', args: {} },
        ],
      },
      spatial: {
        arrays: { ring: arrayMeta('ring', 6) },
        tracks: { array: { array: 'ring', width: 6 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.trackBuses = {
      array: { srcBus: s._trackMap.array.srcBus, fxBus: s._trackMap.array.fxBus },
      main: { srcBus: s._trackMap.main.srcBus, fxBus: s._trackMap.main.fxBus },
    };
    out.widths = { array: s._trackMap.array.width, main: s._trackMap.main.width };
    out.sNews = sNews();
    out.globalCursor = sandbox.__klothoBusAlloc.nextAudio;

  } else if (scenario === 'geometry' || scenario === 'ordering') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { hall: arrayMeta('hall', 4) },
        tracks: { array: { array: 'hall', width: 4 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.log = log;
    out.expectedCoefficients = coefficients(4);
    out.mainFxBus = s._trackMap.main.fxBus;
    out.mainParentGroup = s._trackMap.main.parentGroup;
    out.decoderNode = s._trackMap.main.decoderNode;
    out.bufnum = s._geomPreload ? s._geomPreload.bufnum : null;

  } else if (scenario === 'no_decoder') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { labelsOnly: arrayMeta('labelsOnly', 4, { geometry: false }) },
        tracks: { array: { array: 'labelsOnly', width: 4 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.sNews = sNews();
    out.warnings = warnings;
    out.mainWidth = s._trackMap.main.width;
    out.decoderNode = s._trackMap.main.decoderNode || null;
    out.allocs = log.filter((m) => m.k === 'send' && m.msg[0] === '/b_alloc');

  } else if (scenario === 'mixed') {
    const s = newScheduler();
    const meta = {
      groups: ['array', 'stereo'],
      spatial: {
        arrays: { hall: arrayMeta('hall', 8) },
        tracks: { array: { array: 'hall', width: 8 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.widths = {
      array: s._trackMap.array.width,
      stereo: s._trackMap.stereo.width,
      main: s._trackMap.main.width,
    };
    out.buses = {
      array: [s._trackMap.array.srcBus, s._trackMap.array.fxBus],
      stereo: [s._trackMap.stereo.srcBus, s._trackMap.stereo.fxBus],
      main: [s._trackMap.main.srcBus, s._trackMap.main.fxBus],
    };
    out.sNews = sNews();
    out.warnings = warnings;
    s._bundleNew(ev(1, 'stereo'), 100);
    s._bundleNew(ev(2, 'array', 5), 101);
    out.outs = newBundles().map(outsByEvent);

  } else if (scenario === 'main_only') {
    const s = newScheduler();
    const meta = {
      spatial: {
        arrays: { hall: arrayMeta('hall', 4) },
        tracks: { main: { array: 'hall', width: 4 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.hasTrackMap = !!s._trackMap;
    out.mainWidth = s._trackMap ? s._trackMap.main.width : null;
    out.defaultIsMain = s._trackMap
      ? s._trackMap['default'] === s._trackMap.main : null;
    s._bundleNew(ev(1, 'default', 2), 100);
    out.outs = newBundles().map(outsByEvent);
    out.srcBus = s._trackMap ? s._trackMap.main.srcBus : null;
    out.sNews = sNews();

  } else if (scenario === 'slur') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { hall: arrayMeta('hall', 8) },
        tracks: { array: { array: 'hall', width: 8 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.srcBus = s._trackMap.array.srcBus;
    s._bundleNew(ev(1, 'array', 6), 100);
    s._bundleSet(Object.assign(ev(1, 'array', 6), { type: 'set' }), 101);
    out.newOuts = newBundles().map(outsByEvent);
    out.setOuts = setBundles().map(outsByEvent);

  } else if (scenario === 'too_wide') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { huge: arrayMeta('huge', 40, { geometry: false }) },
        tracks: { array: { array: 'huge', width: 40 } },
      },
    };
    out.threw = false;
    try { await s.setupTracks(meta, 900); }
    catch (e) { out.threw = true; out.message = String(e && e.message); }
    out.sends = log.length;
    out.trackMap = s._trackMap;

  } else if (scenario === 'bad_width') {
    out.cases = [];
    for (const [name, w] of [['zero', 0], ['fractional', 2.5],
      ['string', '8'], ['nan', NaN], ['null', null], ['negative', -4]]) {
      const s = newScheduler();
      const meta = {
        groups: ['array'],
        spatial: {
          arrays: { a: arrayMeta('a', 4, { geometry: false }) },
          tracks: { array: { array: 'a', width: w } },
        },
      };
      let threw = false, message = null;
      try { await s.setupTracks(meta, 900); }
      catch (e) { threw = true; message = String(e && e.message); }
      out.cases.push({ name, threw, message });
    }

  } else if (scenario === 'missing_def') {
    // Width 5 is off the precompiled family, so the page's registry has no
    // __busRouter5 and no __spatialDecode5.
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { odd: arrayMeta('odd', 5) },
        tracks: { array: { array: 'odd', width: 5 } },
      },
    };
    out.threw = false;
    try { await s.setupTracks(meta, 900); }
    catch (e) { out.threw = true; out.message = String(e && e.message); }
    out.sends = log.length;

  } else if (scenario === 'replay') {
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      spatial: {
        arrays: { hall: arrayMeta('hall', 4) },
        tracks: { array: { array: 'hall', width: 4 } },
      },
    };
    await s.setupTracks(meta, 900);
    const firstBufnum = s._geomPreload.bufnum;
    const allocsAfterFirst = log.filter(
      (m) => m.k === 'send' && m.msg[0] === '/b_alloc').length;
    await s.setupTracks(meta, 901);
    out.firstBufnum = firstBufnum;
    out.secondBufnum = s._geomPreload.bufnum;
    out.allocsAfterFirst = allocsAfterFirst;
    out.allocsAfterSecond = log.filter(
      (m) => m.k === 'send' && m.msg[0] === '/b_alloc').length;
    out.syncCount = syncCount;
    out.decoderNodes = sNews()
      .filter((m) => String(m[1]).indexOf('__spatialDecode') === 0)
      .map((m) => ({ def: m[1], bufnum: m[m.indexOf('bufnum') + 1] }));
    s.releaseControlPreload();
    out.frees = log.filter((m) => m.k === 'send' && m.msg[0] === '/b_free')
      .map((m) => m.msg);
    out.geomAfterRelease = s._geomPreload;

  } else if (scenario === 'narrow_master') {
    // Master inserts on a main that a spatial track widened. Score.track()
    // only checks insert widths for a track that DECLARES speakers, so
    // these were accepted as stereo and would silence every lane above the
    // first pair.
    const s = newScheduler();
    const meta = {
      groups: ['array'],
      inserts: { main: [{ defName: 'kl_reverb', uid: 'fx1', args: {} }] },
      spatial: {
        arrays: { hall: arrayMeta('hall', 8) },
        tracks: { array: { array: 'hall', width: 8 } },
      },
    };
    await s.setupTracks(meta, 900);
    out.warnings = warnings;
    out.mainWidth = s._trackMap.main.width;

  } else if (scenario === 'play_gate') {
    // The gate in play() that decides between the score path (track map,
    // array bus, per-lane routing) and the bare single-group path. A score
    // whose only speaker array is declared on "main" has no `groups` and
    // need have no `inserts`, so a gate reading only those two takes the
    // bare path and drops the whole declaration in silence.
    const s = newScheduler();
    const meta = {
      spatial: {
        arrays: { hall: arrayMeta('hall', 4) },
        tracks: { main: { array: 'hall', width: 4 } },
      },
    };
    const evts = [ev(1, 'main', 2)];
    evts[0].start = 0;
    await s.play(evts, { meta });
    out.hasTrackMap = !!s._trackMap;
    out.mainWidth = s._trackMap ? s._trackMap.main.width : null;
    out.outs = newBundles().map(outsByEvent);
    out.decoders = sNews()
      .filter((m) => String(m[1]).indexOf('__spatialDecode') === 0)
      .map((m) => m[1]);
    await s.stop();

  } else if (scenario === 'payload') {
    // A real lowered score: nothing about the meta or the events was written
    // here, so this is the contract as converters.py actually emits it.
    const ix = argv.indexOf('--payload');
    if (ix === -1) throw new Error('payload scenario needs --payload <file>');
    const payload = JSON.parse(readFileSync(argv[ix + 1], 'utf8'));
    const s = newScheduler();
    await s.setupTracks(payload.meta, 900);
    // __rest__ produces no synth at all, so it would break the
    // event-index -> bundle-index correspondence below.
    const news = (payload.events || [])
      .filter((e) => e.type === 'new' && e.defName !== '__rest__');
    news.forEach((e, i) => s._bundleNew(e, 500 + i));
    out.trackMap = {};
    for (const name of Object.keys(s._trackMap)) {
      const t = s._trackMap[name];
      out.trackMap[name] = {
        srcBus: t.srcBus, fxBus: t.fxBus, width: t.width,
        decoderNode: t.decoderNode || null,
      };
    }
    out.events = news.map((e, i) => ({
      id: e.id, group: e.group, speaker: e.speaker,
      speakerLane: e.speakerLane == null ? null : e.speakerLane,
      out: outsByEvent(newBundles()[i]),
    }));
    out.sNews = sNews();
    out.allocs = log.filter((m) => m.k === 'send' && m.msg[0] === '/b_alloc')
      .map((m) => m.msg);
    out.setnFloats = log
      .filter((m) => m.k === 'send' && m.msg[0] === '/b_setn')
      .reduce((acc, m) => acc.concat(m.msg.slice(4)), []);
    out.warnings = warnings;

  } else {
    throw new Error('unknown scenario: ' + scenario);
  }
}

await run();
process.stdout.write(JSON.stringify(out));
