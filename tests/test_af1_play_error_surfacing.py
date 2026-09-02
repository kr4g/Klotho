"""A refused ``play()`` must reach the person who pressed play (AUD-12, AUD-4).

The whole refusal architecture of the multichannel layer is built on "refuse
here, where you can see it" -- a dozen docstrings in ``scheduler_score.js`` say
so, and every one of those messages is a paragraph written for a composer.  All
of them were being thrown into a promise nobody was listening to.

``scheduler_core.js``'s ``async play()`` awaited ``setupTracks`` /
``setupControlEnvelopes`` outside any try/catch, and ``_animation_bridge.js``
called ``play()`` with no ``await`` and no ``.catch``.  A refusal was therefore
an **unhandled promise rejection**: the message landed in the browser devtools
console and nowhere a composer in Jupyter or Colab would ever look.  Because
``onFinish``/``onIdle`` never fired, the widget's button stayed on its stop
icon -- and pressing that stop icon re-ran the failed play, because the
controller's stop branch is gated on ``isPlaying || ringing``, both false.
``record()`` waited forever for a finish that could not come.  The partial
score group stayed allocated, so its bus run was never reclaimed either.

Six code paths reject ``play()``, all of them reachable from the public API:

1. ``_spatialPlan``'s four refusals (bad width, more than 32 speakers,
   geometry stride mismatch, coefficient-length mismatch);
2. ``requireDef`` for an array width off the precompiled family;
3. ``_allocAudioBusN`` "out of private audio buses" -- immediate on a legacy
   128-bus page with one 24-wide array (48 + 4x24 = 144 > 128), and reachable
   by accumulation everywhere else;
4. ``_allocAudioBusN``'s width validation;
5. ``preloadControlBuffer``'s ``atob`` on a corrupted saved output;
6. an awaited control-buffer fill promise that rejected.

These are BEHAVIORAL tests.  The probe below loads the REAL
``_animation_bridge.js``, ``scheduler_core.js`` and ``scheduler_score.js`` into
a Node ``vm`` sandbox against a fake engine, installs
``process.on('unhandledRejection')``, and calls ``bridge.play()``
fire-and-forget exactly the way ``_engine_widget.js`` does -- because a silent
failure and a success are indistinguishable from Python, and asserting on
source text would only pin the words.  Modelled on the harness in
``tests/test_spatial_routing_js.py``.

**Where the expected values come from.**  Not from running the fixed code.
:class:`TestPreFixBehaviourWasSilent` runs the same probe against the sources
as they stood in :data:`PRE_FIX_COMMIT` -- one ``git show`` away -- and pins the
old behaviour: the rejection unhandled, both callbacks unfired, the group
leaked, ``record()`` hung.  :meth:`TestRefusedPlayIsSurfaced
.test_the_caller_gets_the_message_the_console_used_to_swallow` then asserts
that the message the fixed build hands to ``onError`` is *byte-identical to the
one the old build leaked*, so the expectation is captured from pre-change
behaviour rather than from the thing under test.

The probe JS is embedded here rather than living in ``tests/fixtures/`` so this
file is self-contained; it is written to a temp directory per session.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
_SS_DIR = _ROOT / "klotho" / "utils" / "playback" / "supersonic"
_PB_DIR = _ROOT / "klotho" / "utils" / "playback"

#: The last commit before this fix: 10.18.0 plus the branch's spatial work,
#: with ``play()``'s awaits still outside any try/catch and the bridge still
#: calling ``play()`` bare.  Used only to fetch three source files for the A/B;
#: if the object is gone the A/B skips and the forward assertions still stand.
PRE_FIX_COMMIT = "269cc32"

requires_node = pytest.mark.skipif(shutil.which("node") is None,
                                   reason="node not available")


# ---------------------------------------------------------------------------
# The probe.  One JSON object on stdout per run.
# ---------------------------------------------------------------------------
PROBE_JS = r'''
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const HERE = dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const scenario = argv[0];
const ROOT = argv[argv.indexOf('--root') + 1];
const srcIx = argv.indexOf('--src');
const SS_DIR = srcIx !== -1 ? argv[srcIx + 1]
  : join(ROOT, 'klotho', 'utils', 'playback', 'supersonic');
const bridgeIx = argv.indexOf('--bridge');
const BRIDGE_FILE = bridgeIx !== -1 ? argv[bridgeIx + 1]
  : join(ROOT, 'klotho', 'utils', 'playback', '_animation_bridge.js');

// The whole question is what a BROWSER would do with the rejection, so this
// is the instrument: anything that lands here reached no handler at all.
const unhandled = [];
process.on('unhandledRejection', (r) => {
  unhandled.push(String((r && r.message) || r));
});

const log = [];
const consoleErrors = [];
const warnings = [];

const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send(...args) { log.push({ k: 'send', msg: args }); },
  sendOSC(bundle) { log.push({ k: 'bundle', ...bundle }); },
  purge() {},
  async sync() {},
  getMetrics() { return {}; },
  audioContext: { state: 'running', resume: async () => {} },
};

function makeSandbox(busChannels) {
  const sandbox = {
    performance: { timeOrigin: 0, now: () => 0 },
    // Timers never fire: this probe is about the synchronous + microtask
    // behaviour of a REFUSED play, and a live timer would only add flake.
    // The one place real time is needed -- does record() hang? -- is timed
    // from the host, outside the sandbox.
    setTimeout: () => 1,
    clearTimeout: () => {},
    console: {
      log: () => {}, debug: () => {},
      error: (...a) => { consoleErrors.push(a.join(' ')); },
      warn: (...a) => { warnings.push(a.join(' ')); },
    },
    atob: (s) => Buffer.from(s, 'base64').toString('binary'),
    DrawScheduler: class { schedule() {} clear() {} },
    SuperSonic: {
      osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) },
    },
    __klothoSonic: {
      bootConfig: { scsynthOptions: { numAudioBusChannels: busChannels } },
      _nextBufnum: 7,
      instance: sonic,
    },
    __ensureSuperSonic: async () => sonic,
    // The page's merged SynthDef registry.  Width 5 is deliberately absent:
    // that is how the "off-family width" refusal is reached.
    __klothoSynthdefAssets: {
      '__busRouter': 'x', '__busRouterMonitor': 'x', '__chainLimiter': 'x',
      '__klEnvCtrl': 'x', 'kl_tri': 'x', 'kl_saw': 'x',
      '__busRouter1': 'x', '__busRouter2': 'x', '__busRouter4': 'x',
      '__busRouter6': 'x', '__busRouter8': 'x', '__busRouter12': 'x',
      '__busRouter16': 'x', '__busRouter24': 'x', '__busRouter32': 'x',
      '__spatialDecode1': 'x', '__spatialDecode2': 'x', '__spatialDecode4': 'x',
      '__spatialDecode6': 'x', '__spatialDecode8': 'x', '__spatialDecode12': 'x',
      '__spatialDecode16': 'x', '__spatialDecode24': 'x', '__spatialDecode32': 'x',
    },
    Blob: class { constructor(parts) { this.parts = parts; } },
  };
  vm.createContext(sandbox);
  vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8'), sandbox);
  vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8'), sandbox);
  vm.runInContext(readFileSync(BRIDGE_FILE, 'utf8'), sandbox);
  return sandbox;
}

function arrayMeta(name, width) {
  const labels = [];
  for (let i = 0; i < width; i++) labels.push('S' + (i + 1));
  return { name, labels, width,
    positions: null, units: null, speedOfSound: null, decoder: null };
}

const events = () => ([{
  id: 1, type: 'new', defName: 'kl_tri', start: 0, dur: 1, group: 'a',
  pfields: { freq: 220, amp: 0.3 },
}]);

const spatialMeta = (width) => ({
  groups: ['a'],
  spatial: {
    arrays: { arr: arrayMeta('arr', width) },
    tracks: { a: { array: 'arr', width } },
  },
});

const tick = (ms) => new Promise((r) => setTimeout(r, ms));

const groupsCreated = () => log
  .filter((m) => m.k === 'send' && m.msg[0] === '/g_new').map((m) => m.msg[1]);
const groupsFreed = () => log
  .filter((m) => m.k === 'send' && m.msg[0] === '/n_free').map((m) => m.msg[1]);
const groupsCleared = () => log
  .filter((m) => m.k === 'send' && m.msg[0] === '/g_freeAll').map((m) => m.msg[1]);

// Scenario -> [private audio bus channels the page booted with, array width].
// too_wide     the decoder family stops at 32
// missing_def  width 5 is off the precompiled family
// no_buses     48 + 4 * 24 = 144 > 128 on a legacy page, first try
// ok           nothing refuses this one
const CASES = {
  too_wide: [1024, 40],
  missing_def: [1024, 5],
  no_buses: [128, 24],
  ok: [1024, 8],
};

const out = { scenario };

async function run() {
  if (Object.prototype.hasOwnProperty.call(CASES, scenario)) {
    const [busChannels, width] = CASES[scenario];
    const sandbox = makeSandbox(busChannels);
    const bridge = sandbox.KlothoPlaybackBridge({
      audioPayload: { events: events() },
      ringTime: 0.1,
      meta: spatialMeta(width),
      manifest: { kl_tri: { amp: 0.5, gate: 1 } },
    });
    out.ready = await bridge.ensureReady();

    let onFinishFired = false, onIdleFired = false, onErrorMsg = null;
    // Fire-and-forget: exactly how _engine_widget.js's doPlay() calls it.
    bridge.play(null, {
      onFinish: function () { onFinishFired = true; },
      onIdle: function () { onIdleFired = true; },
      onError: function (m) { onErrorMsg = String(m); },
    });
    await tick(80);

    out.unhandledRejections = unhandled;
    out.onFinishFired = onFinishFired;
    out.onIdleFired = onIdleFired;
    out.onErrorMsg = onErrorMsg;
    out.consoleErrors = consoleErrors;
    out.groupsCreated = groupsCreated();
    out.groupsFreed = groupsFreed();
    out.groupsCleared = groupsCleared();
    out.isPlaying = bridge.isPlaying();

  } else if (scenario === 'record') {
    const sandbox = makeSandbox(1024);
    let aborted = false;
    sandbox.KlothoRecorder = {
      async start() {
        return { startedPerfMs: 0,
                 abort() { aborted = true; },
                 async stop() { return null; } };
      },
      defaultBaseName: () => 'take',
      encodeWav24: () => new Uint8Array(0),
      zipStore: () => new Uint8Array(0),
      deliver: () => {},
    };
    const bridge = sandbox.KlothoPlaybackBridge({
      audioPayload: { events: events() },
      ringTime: 0.1,
      meta: spatialMeta(40),
      manifest: { kl_tri: { amp: 0.5, gate: 1 } },
    });
    await bridge.ensureReady();
    let onErrorMsg = null;
    const HUNG = Symbol('hung');
    const settled = await Promise.race([
      bridge.record(null, { onError: function (m) { onErrorMsg = String(m); } }),
      tick(400).then(() => HUNG),
    ]);
    out.recordSettled = settled !== HUNG;
    out.recordValue = settled === HUNG ? 'HUNG' : settled;
    out.recorderAborted = aborted;
    out.recordOnErrorMsg = onErrorMsg;
    out.unhandledRejections = unhandled;
    out.consoleErrors = consoleErrors;

  } else {
    throw new Error('unknown scenario: ' + scenario);
  }
}

await run();
process.stdout.write(JSON.stringify(out));
'''

#: Every scenario whose play() the schedulers must refuse.
REFUSAL_SCENARIOS = ["too_wide", "missing_def", "no_buses"]


@pytest.fixture(scope="module")
def probe_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("af1_play_error") / "play_error_probe.mjs"
    p.write_text(PROBE_JS)
    return p


def _run(probe, scenario, src=None, bridge=None):
    argv = ["node", str(probe), scenario, "--root", str(_ROOT)]
    if src is not None:
        argv += ["--src", str(src)]
    if bridge is not None:
        argv += ["--bridge", str(bridge)]
    r = subprocess.run(argv, capture_output=True, text=True, cwd=str(_ROOT))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _pre_fix_tree(tmp):
    """The three sources as of :data:`PRE_FIX_COMMIT`, or ``None``.

    All three come from the same commit so the "before" side is internally
    consistent even while other lanes edit the working tree.
    """
    files = {
        "scheduler_core.js": f"{PRE_FIX_COMMIT}:klotho/utils/playback/supersonic/scheduler_core.js",
        "scheduler_score.js": f"{PRE_FIX_COMMIT}:klotho/utils/playback/supersonic/scheduler_score.js",
        "_animation_bridge.js": f"{PRE_FIX_COMMIT}:klotho/utils/playback/_animation_bridge.js",
    }
    try:
        for name, spec in files.items():
            text = subprocess.run(["git", "show", spec], capture_output=True,
                                  text=True, cwd=str(_ROOT), check=True).stdout
            (Path(tmp) / name).write_text(text)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return Path(tmp)


@requires_node
class TestPreFixBehaviourWasSilent:
    """The red proof, run against the sources one ``git show`` back.

    Nothing here asserts what the fix *should* do; it pins what the bug *did*,
    so the forward assertions in the rest of this file have an origin outside
    the code they check.
    """

    def test_the_refusal_reached_nobody(self, probe_path):
        with tempfile.TemporaryDirectory() as tmp:
            src = _pre_fix_tree(tmp)
            if src is None:
                pytest.skip(f"{PRE_FIX_COMMIT} not reachable from this checkout")
            before = _run(probe_path, "too_wide", src=src,
                          bridge=src / "_animation_bridge.js")
        # The refusal message ended up in the isolate's unhandled-rejection
        # channel -- i.e. the browser devtools console, and nothing else.
        assert len(before["unhandledRejections"]) == 1
        assert "declares 40 speakers" in before["unhandledRejections"][0]
        # Nothing was written where a caller could see it.
        assert before["consoleErrors"] == []
        assert before["onErrorMsg"] is None
        # So the transport never re-armed: the icon stayed on "stop", and the
        # controller's stop branch (isPlaying || ringing) was false on both
        # counts -- the next press RE-RAN the failed play.
        assert before["onFinishFired"] is False
        assert before["onIdleFired"] is False
        # And the group created a moment before the refusal was never freed,
        # so its bus run was never reclaimed either.
        assert before["groupsCreated"] == [1000]
        assert before["groupsFreed"] == []

    def test_record_hung_forever(self, probe_path):
        with tempfile.TemporaryDirectory() as tmp:
            src = _pre_fix_tree(tmp)
            if src is None:
                pytest.skip(f"{PRE_FIX_COMMIT} not reachable from this checkout")
            before = _run(probe_path, "record", src=src,
                          bridge=src / "_animation_bridge.js")
        # record() settles from its play's onFinish, which a refused play
        # never reaches: 400 ms later the promise was still pending.
        assert before["recordSettled"] is False
        assert before["recordValue"] == "HUNG"
        assert before["recorderAborted"] is False


@requires_node
class TestRefusedPlayIsSurfaced:
    """Every refusing path now reaches the caller instead of the void."""

    @pytest.mark.parametrize("scenario", REFUSAL_SCENARIOS)
    def test_no_unhandled_rejection(self, probe_path, scenario):
        r = _run(probe_path, scenario)
        assert r["unhandledRejections"] == []

    @pytest.mark.parametrize("scenario", REFUSAL_SCENARIOS)
    def test_the_reason_reaches_the_caller_and_the_console(self, probe_path,
                                                           scenario):
        r = _run(probe_path, scenario)
        assert isinstance(r["onErrorMsg"], str) and r["onErrorMsg"]
        # Reported once, not once per layer.
        assert len(r["consoleErrors"]) == 1
        assert r["consoleErrors"][0].startswith(
            "[Klotho] playback could not start: ")

    @pytest.mark.parametrize("scenario", REFUSAL_SCENARIOS)
    def test_the_transport_re_arms(self, probe_path, scenario):
        """``onIdle`` is where every controller puts its play icon back; a
        refusal that skips it leaves a stop icon whose next press retries."""
        r = _run(probe_path, scenario)
        assert r["onFinishFired"] is True
        assert r["onIdleFired"] is True
        assert r["isPlaying"] is False

    @pytest.mark.parametrize("scenario", REFUSAL_SCENARIOS)
    def test_the_partial_score_group_is_freed(self, probe_path, scenario):
        """``_createScoreGroup`` runs before ``setupTracks`` can refuse, so a
        refusal leaves a live group -- and with it an unreclaimed bus run,
        which is how a page walks itself into "out of private audio buses"."""
        r = _run(probe_path, scenario)
        score_group = r["groupsCreated"][0]
        assert score_group in r["groupsFreed"]
        assert score_group in r["groupsCleared"]

    def test_the_caller_gets_the_message_the_console_used_to_swallow(
            self, probe_path):
        """The expectation with an independent origin: whatever text the
        PRE-FIX build leaked as an unhandled rejection is exactly what the
        fixed build now hands to ``onError``."""
        with tempfile.TemporaryDirectory() as tmp:
            src = _pre_fix_tree(tmp)
            if src is None:
                pytest.skip(f"{PRE_FIX_COMMIT} not reachable from this checkout")
            before = _run(probe_path, "too_wide", src=src,
                          bridge=src / "_animation_bridge.js")
            after = _run(probe_path, "too_wide")
        assert after["onErrorMsg"] == before["unhandledRejections"][0]


@requires_node
class TestRecordSettles:
    """``record()`` must resolve ``null``, not wait for a finish that a
    refused play can never produce."""

    def test_record_resolves_null_instead_of_hanging(self, probe_path):
        r = _run(probe_path, "record")
        assert r["recordSettled"] is True
        assert r["recordValue"] is None

    def test_the_capture_is_abandoned(self, probe_path):
        """A live capture worklet left running is a memory leak and a file
        of silence; ``stop()`` mid-record aborts, and so must this."""
        r = _run(probe_path, "record")
        assert r["recorderAborted"] is True

    def test_record_surfaces_the_reason_too(self, probe_path):
        r = _run(probe_path, "record")
        assert isinstance(r["recordOnErrorMsg"], str)
        assert "declares 40 speakers" in r["recordOnErrorMsg"]
        assert r["unhandledRejections"] == []


@requires_node
class TestSuccessfulPlayIsUntouched:
    """The catch must not swallow a play that nothing refuses.

    A try/catch around the setup section is exactly the shape of change that
    can turn a working play into a silent no-op, so this is the control: an
    8-speaker array on a 1024-bus page is refused by nothing.
    """

    def test_a_good_payload_still_starts(self, probe_path):
        r = _run(probe_path, "ok")
        assert r["unhandledRejections"] == []
        assert r["onErrorMsg"] is None
        assert r["consoleErrors"] == []
        assert r["isPlaying"] is True

    def test_the_end_of_play_callbacks_do_not_fire_early(self, probe_path):
        """``onFinish``/``onIdle`` are now routed through once-only wrappers.
        Once-only must not mean once-at-the-start: with the sandbox's timers
        stubbed out the piece never reaches its finish, so neither may fire."""
        r = _run(probe_path, "ok")
        assert r["onFinishFired"] is False
        assert r["onIdleFired"] is False

    def test_the_groups_stay_alive(self, probe_path):
        r = _run(probe_path, "ok")
        assert r["groupsCreated"]
        assert r["groupsFreed"] == []


class TestTheSeamsStayInPlace:
    """Cheap source fences, so a later edit cannot quietly reopen the hole.

    Behavioral tests above are the real argument; these only pin the two
    seams, because their absence is invisible -- an unhandled rejection looks
    exactly like a success from every side except the devtools console.
    """

    def test_scheduler_play_guards_its_awaited_setup(self):
        src = (_SS_DIR / "scheduler_core.js").read_text()
        body = src[src.index("async play(events, options)"):]
        body = body[:body.index("this._buildSendPlan(evts)")]
        assert "try {" in body
        assert "this._abortPlaySetup(err)" in body

    def test_the_abort_helper_frees_and_runs_the_callbacks(self):
        src = (_SS_DIR / "scheduler_core.js").read_text()
        body = src[src.index("_abortPlaySetup(err)"):]
        body = body[:body.index("async play(events, options)")]
        assert "this._freeGroup()" in body
        assert "this.onFinish()" in body
        assert "this.onIdle()" in body

    def test_the_bridge_handles_the_rejection_it_never_awaits(self):
        src = (_PB_DIR / "_animation_bridge.js").read_text()
        body = src[src.index("async function play(events, options)"):]
        body = body[:body.index("// ------")]
        # Still fire-and-forget (a press must not block its click handler),
        # which is precisely why the promise needs a handler of its own.
        assert "var pending = _ssScheduler.play(evts, {" in body
        assert "pending.then(null, function(err)" in body
