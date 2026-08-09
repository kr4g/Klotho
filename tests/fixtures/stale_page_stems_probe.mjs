// Regression probe for the 10.16 stems version-skew fix.
//
// Loads the real scheduler_core.js / scheduler_score.js into a vm sandbox
// and drives play() with Score meta + stemTaps in two page states:
//   fresh  — nothing installed (clean page)
//   stale  — a pre-10.16 BrowserScheduler (unversioned install guard, no
//            setupStemTaps, bus floor 16) was installed first, as happens
//            when a notebook with old saved outputs is opened.
// The versioned core install must replace the stale class so both states
// produce identical stem layouts and tap sends.
//
//   stale_1016dev — a 10.16-dev core (already claims __klothoSchedCoreV2,
//            has stems, but races frees against purge on stop) installed
//            first. The V3 core must key on its own marker and replace it;
//            deferring to V2 left the free-vs-purge race live and let a
//            late clearSched ack eat control-envelope synths.
//
// Usage: node stale_page_stems_probe.mjs <fresh|stale|stale_1016dev>
// Prints JSON: { stemLayout, tapSends, hasSetupStemTaps, busAllocNextAudio,
//                stopHasSyncDrain }

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const SS_DIR = join(HERE, '..', '..', 'klotho', 'utils', 'playback', 'supersonic');

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

if (process.argv[2] === 'stale') {
  // A minimal stand-in for the pre-10.16 build: same install guard
  // shape, old bus floor, no setupStemTaps / routerNode storage.
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

if (process.argv[2] === 'stale_1016dev') {
  // A minimal stand-in for the pre-fix 10.16-dev build: claims the V2
  // marker and the 10.16 bus floor, has stems plumbing, but its stop()
  // lacks the /sync drain (the free-vs-purge race). If the real core
  // defers to the V2 marker instead of installing, this class handles
  // play() and the probe's stem assertions fail.
  vm.runInContext(`
    globalThis.__klothoBusAlloc = { nextAudio: 48, nextControl: 0 };
    globalThis.__klothoSchedCoreV2 = true;
    globalThis.BrowserScheduler = class {
      constructor(cfg) { this.sonic = cfg.sonic; this.manifest = cfg.manifest || {};
        this.isPlaying = false; this.stopToken = 0; this.nodeMap = new Map();
        this._defNames = new Map(); this._trackMap = null; }
      async play() {} async stop() {}
      setupStemTaps() { return null; }
    };
    globalThis.BrowserScheduler.prototype.setupTracks = async function() { this._trackMap = {}; };
  `, sandbox);
}

vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8'), sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8'), sandbox);

const meta = { groups: ['drums', 'keys'], inserts: {} };
const events = [
  { type: 'new', id: 'e1', defName: 'percSynth', start: 0.0, dur: 0.5,
    releaseAfter: true, group: 'drums', pfields: { amp: 0.5 } },
  { type: 'new', id: 'e2', defName: 'percSynth', start: 0.5, dur: 0.5,
    releaseAfter: true, group: 'keys', pfields: { amp: 0.5 } },
];

const scheduler = new sandbox.BrowserScheduler({
  sonic, manifest: { percSynth: { amp: 0.5 } }, ringTime: 0.1,
});
await scheduler.play(events, { meta, stemTaps: true, onFinish: () => {} });

const taps = sends.filter((s) => s[0] === '/s_new' && s[1] === '__busRouter' && s[3] === 3);
process.stdout.write(JSON.stringify({
  stemLayout: scheduler._stemLayout ?? null,
  tapSends: taps.map((t) => ({ after: t[4], inBus: t[6], outBus: t[8] })),
  hasSetupStemTaps: typeof scheduler.setupStemTaps === 'function',
  busAllocNextAudio: sandbox.__klothoBusAlloc?.nextAudio,
  stopHasSyncDrain: /_engineLock/.test(
    sandbox.BrowserScheduler.prototype.stop.toString()),
}));
