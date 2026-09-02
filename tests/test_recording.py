"""Recording feature: source contracts and widget script sanity.

Static contracts over the JS sources (the browser behavior itself is
click-tested manually in Jupyter/Colab), in the style of
``test_scheduler_batching.TestSourceContract``.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_PLAYBACK_DIR = Path(__file__).parent.parent / "klotho" / "utils" / "playback"
_SS_DIR = _PLAYBACK_DIR / "supersonic"

CORE_SRC = (_SS_DIR / "scheduler_core.js").read_text()
SCORE_SRC = (_SS_DIR / "scheduler_score.js").read_text()
BRIDGE_SRC = (_PLAYBACK_DIR / "_animation_bridge.js").read_text()
RECORDER_SRC = (_PLAYBACK_DIR / "_recorder.js").read_text()


def _const(src, name):
    m = re.search(rf"var {name} = (\d+);", src)
    assert m, f"{name} not found"
    return int(m.group(1))


def _newest_core_marker():
    """The highest ``__klothoSchedCoreVn`` the core claims on its way out."""
    ns = [int(n) for n in
          re.findall(r"globalThis\.__klothoSchedCoreV(\d+) = true;", CORE_SRC)]
    assert ns, "the core claims no version marker at all"
    return max(ns)


def _newest_bridge_marker(src=None):
    """The highest ``__klothoPlaybackBridgeVn`` the bridge claims on its way
    out."""
    ns = [int(n) for n in
          re.findall(r"globalThis\.__klothoPlaybackBridgeV(\d+) = buildBridge;",
                     BRIDGE_SRC if src is None else src)]
    assert ns, "the bridge claims no version marker at all"
    return max(ns)


class TestBusFloorContract:
    def test_first_private_bus_matches_across_files(self):
        assert _const(CORE_SRC, "FIRST_PRIVATE_BUS") == \
            _const(SCORE_SRC, "FIRST_PRIVATE_BUS")

    def test_first_private_bus_clears_hardware_span(self):
        """Output + input buses must never overlap track routing buses."""
        from klotho.utils.playback.supersonic.cdn import supersonic_config
        opts = supersonic_config()["scsynthOptions"]
        num_out = opts["numOutputBusChannels"]
        num_in = opts.get("numInputBusChannels", 2)  # SuperSonic default
        assert _const(CORE_SRC, "FIRST_PRIVATE_BUS") >= num_out + num_in

    def test_output_channels_within_web_audio_cap(self):
        from klotho.utils.playback.supersonic.cdn import supersonic_config
        assert supersonic_config()["scsynthOptions"]["numOutputBusChannels"] <= 32

    def test_stale_page_floor_guard_precedes_install_guard(self):
        """The floor guard must run on EVERY inclusion — before the
        versioned early-return — so it also repairs pages where a
        stale pre-10.16 scheduler was installed first."""
        guard = CORE_SRC.index("__klothoBusAlloc.nextAudio < 48")
        install = CORE_SRC.index(
            f"if (globalThis.__klothoSchedCoreV{_newest_core_marker()}) return;")
        assert guard < install

    def test_cdn_version_pinned(self):
        from klotho.utils.playback.supersonic.cdn import SUPERSONIC_VERSION
        assert SUPERSONIC_VERSION != "latest"
        assert re.fullmatch(r"\d+\.\d+\.\d+", SUPERSONIC_VERSION)


class TestSchedulerVersionSkew:
    """The 10.16 stems bug: a stale pre-10.16 scheduler installed by old
    saved outputs must be replaced, not deferred to (it lacks
    setupStemTaps, so stems ZIPs silently contained only main.wav)."""

    def test_core_install_guard_is_versioned(self):
        """The discipline, not one literal: whatever the newest marker N is,
        the install guard keys on N alone, every marker from V2 to N is
        claimed on the way out, and no older marker is used as a guard.

        Written generically because it is edited on every behavioural fix to
        the core (V6 = the per-play bus-run ledger), and a test that has to
        be hand-edited to say a new number is a test that gets edited
        without being read.
        """
        newest = _newest_core_marker()
        assert newest >= 6, newest
        assert f"if (globalThis.__klothoSchedCoreV{newest}) return;" in CORE_SRC
        assert "if (globalThis.BrowserScheduler) return;" not in CORE_SRC
        # Every marker up to the newest is claimed, so a stale core
        # rendering later can never downgrade the installed class…
        for n in range(2, newest + 1):
            assert f"globalThis.__klothoSchedCoreV{n} = true;" in CORE_SRC, n
        # …and none of the older ones is what the install guard keys on.
        for n in range(2, newest):
            assert f"if (globalThis.__klothoSchedCoreV{n}) return;" not in CORE_SRC, n

    def test_boot_stashes_config_for_capacity_checks(self):
        from klotho.utils.playback.supersonic._js_fragments import ss_init_js
        assert "bootConfig = config" in ss_init_js()

    def test_bridge_degrades_stems_with_reload_hint(self):
        assert "stemCapacity" in BRIDGE_SRC
        assert "Reload the notebook page" in BRIDGE_SRC

    @pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
    @pytest.mark.parametrize("page_state", ["fresh", "stale", "stale_1016dev"])
    def test_stems_taps_survive_page_state(self, page_state):
        """Behavioral: the real scheduler sources must produce identical
        stem layouts whether or not a stale scheduler ran first."""
        probe = Path(__file__).parent / "fixtures" / "stale_page_stems_probe.mjs"
        proc = subprocess.run(["node", str(probe), page_state],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        result = json.loads(proc.stdout)
        assert result["hasSetupStemTaps"] is True
        assert result["stemLayout"] == [
            {"name": "drums", "ch": [2, 3]},
            {"name": "keys", "ch": [4, 5]},
        ]
        assert [t["outBus"] for t in result["tapSends"]] == [2, 4]
        # bus floor must hold even when the stale page installed 16
        assert result["busAllocNextAudio"] >= 48
        # the installed class must be the V3 build (sync-drained stop) —
        # a 10.16-dev core claiming the V2 marker must not win the page
        assert result["stopHasSyncDrain"] is True


class TestTeardownFenceContract:
    def test_teardown_fences_use_fast_sync(self):
        """stop(), play()'s restart drain and the idle-holdoff chain fence
        frees via the direct /synced round-trip; the upstream sync() pads
        every call with ~2x snapshotIntervalMs (~300 ms) of settling sleep
        in postMessage mode."""
        assert "_fastSync(" in CORE_SRC
        assert "this.sonic.sync()" not in CORE_SRC

    def test_buffer_fill_fence_keeps_upstream_sync(self):
        """preloadControlBuffer's /b_alloc rides supersonic's async
        buffer-command chain (the /b_alloc family is not written straight
        to the out-ring), and only the full sonic.sync() awaits that
        chain. A raw /sync round-trip can overtake the alloc, landing the
        /b_setn fills on an unallocated buffer — the control-envelope
        silence bug. Do not convert this site to _fastSync."""
        assert "await sonic.sync();" in SCORE_SRC
        assert "_fastSync" not in SCORE_SRC


class TestSchedulerRecordingContract:
    def test_no_blocked_clearsched_command(self):
        """SuperSonic blocks /clearSched client-side (it throws); the
        idle-flush must use purge()."""
        assert "send('/clearSched')" not in CORE_SRC
        assert 'send("/clearSched")' not in CORE_SRC
        assert "this.sonic.purge()" in CORE_SRC

    def test_stem_taps_placed_after_stored_router(self):
        # router ids are stored so taps can be /s_new'd addAction 3 (after)
        assert "routerNode = routerId" in SCORE_SRC
        assert re.search(
            r"'/s_new', '__busRouter', tapId, 3, track\.routerNode", SCORE_SRC)

    def test_stem_taps_use_output_pairs_from_channel_2(self):
        assert "var STEM_OUT_BASE = 2;" in SCORE_SRC
        assert "var MAX_STEMS = 15;" in SCORE_SRC

    def test_play_hooks_stem_taps_behind_option(self):
        assert "options.stemTaps" in CORE_SRC
        assert "this.setupStemTaps" in CORE_SRC

    def test_unresolvable_buf_names_warn(self):
        assert "__klothoBufWarned" in CORE_SRC


class TestBridgeRecordContract:
    def test_bridge_install_guard_is_versioned(self):
        """The same discipline the core is held to, and for the same reason:
        whatever the newest marker N is, the install guard keys on N alone,
        every marker from V2 to N is claimed on the way out, and no older
        marker is used as a guard.

        Written generically rather than naming a literal, because it is
        edited on every behavioural fix to the bridge — and the previous
        version of this test *was* named ``test_versioned_guard_bumped_to_v4``,
        which is exactly the shape that gets read as "V4 is correct" instead
        of "bump me".  A test that has to be hand-edited to say a new number
        is a test that gets edited without being read.
        """
        newest = _newest_bridge_marker()
        assert newest >= 5, newest
        assert (f'if (typeof globalThis.__klothoPlaybackBridgeV{newest} '
                f'!== "undefined") return;') in BRIDGE_SRC
        # Every marker up to the newest is claimed, so a stale bridge
        # rendering later can never clobber the public name with an older
        # build…
        for n in range(2, newest + 1):
            assert (f"globalThis.__klothoPlaybackBridgeV{n} = buildBridge"
                    in BRIDGE_SRC), n
        # …and none of the older ones is what the install guard keys on,
        # or a page that cached that older build would skip this one.
        for n in range(2, newest):
            assert (f'__klothoPlaybackBridgeV{n} !== "undefined"'
                    not in BRIDGE_SRC), n

    def test_bridge_still_claims_every_shipped_marker(self):
        """The three names klotho-cac **10.18.0** assigns on its way out.

        Not derived from the current source: read off the released build with
        ``git show 9c1646c:klotho/utils/playback/_animation_bridge.js``
        (``RELEASED_COMMIT``; it was ``origin/main`` until that stopped
        naming the published release on 2026-09-01).
        A newer bridge that stopped claiming one of them would let a stale
        saved output from that release win the public name on a shared page.
        """
        for n in (2, 3, 4):
            assert (f"globalThis.__klothoPlaybackBridgeV{n} = buildBridge"
                    in BRIDGE_SRC), n

    def test_bridge_plumbs_on_idle_to_scheduler(self):
        """Controllers re-arm their play button at onIdle (finish +
        ring-out + teardown); the bridge must pass it through — and fire
        it on the no-events early return, or the icon sticks on stop."""
        assert "onIdle: onIdle," in BRIDGE_SRC
        assert "if (onIdle) onIdle();" in BRIDGE_SRC

    def test_bridge_stop_is_not_gated_on_is_playing(self):
        """During the ring-out isPlaying is already false, but a stop
        press must still cut the ringing tails — an isPlaying gate here
        silently no-ops the cut (stop means STOP)."""
        assert "if (_ssScheduler) await _ssScheduler.stop();" in BRIDGE_SRC
        assert "_ssScheduler.isPlaying) await _ssScheduler.stop()" not in BRIDGE_SRC


class TestRingOutTransportContract:
    """The stop-means-stop rule: while tails ring (icon still 'stop'),
    a press cuts them and re-arms — it must NEVER start a new playback.
    Restart during ring-out is stop then play, two fast presses."""

    _CONTROLLERS = {
        "playback": (Path(__file__).parent.parent / "klotho" / "semeios"
                     / "visualization" / "_animation" / "_playback.js"),
        "shape": (Path(__file__).parent.parent / "klotho" / "semeios"
                  / "visualization" / "_animation" / "_shape_playback.js"),
        "engine_widget": _SS_DIR / "_engine_widget.js",
    }

    @pytest.mark.parametrize("name", sorted(_CONTROLLERS))
    def test_controller_routes_ring_press_to_stop(self, name):
        src = self._CONTROLLERS[name].read_text()
        assert "var ringing = false;" in src
        assert "ringing = true" in src   # armed at onFinish
        assert "|| ringing" in src       # stop branch covers the ring window

    @pytest.mark.parametrize("name", ["playback", "shape"])
    def test_controller_ring_flags_track_idle(self, name):
        src = self._CONTROLLERS[name].read_text()
        assert "onFinish: function() { ringing = true;" in src
        assert "onIdle: function() { ringing = false;" in src

    def test_record_forces_loop_off_and_waits_for_ring(self):
        m = re.search(r"async function record\(.*?\n    }\n", BRIDGE_SRC, re.S)
        assert m, "record() not found"
        body = m.group(0)
        assert "loop: false" in body
        assert "ringTime" in body

    def test_stop_cancels_recording(self):
        assert "_recCancel" in BRIDGE_SRC


class TestRecorderModule:
    def test_recorder_installs_versioned_global(self):
        assert "__klothoRecorderV1" in RECORDER_SRC
        assert "globalThis.KlothoRecorder = KlothoRecorder" in RECORDER_SRC

    def test_wav_encoder_is_24_bit(self):
        # bits-per-sample field written as 24; int scaling to 2^23 - 1
        assert "dv.setUint16(34, 24, true)" in RECORDER_SRC
        assert "8388607" in RECORDER_SRC

    def test_zip_writer_is_store_only(self):
        # method 0 (STORE) in both local and central headers
        assert "0x04034b50" in RECORDER_SRC
        assert "0x02014b50" in RECORDER_SRC
        assert "0x06054b50" in RECORDER_SRC

    def test_delivery_leaves_persistent_link(self):
        # Colab can block programmatic clicks; a visible link must remain
        assert "createElement" in RECORDER_SRC
        assert "download" in RECORDER_SRC


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
class TestGeneratedScriptsParse:
    def _check_blocks(self, html, tmp_path):
        blocks = re.findall(r'<script type="module">(.*?)</script>', html, re.S)
        assert blocks
        for i, block in enumerate(blocks):
            p = tmp_path / f"block{i}.mjs"
            p.write_text(block)
            proc = subprocess.run(["node", "--check", str(p)],
                                  capture_output=True, text=True)
            assert proc.returncode == 0, proc.stderr

    def test_record_widget_scripts_parse(self, tmp_path):
        from klotho.thetos.composition.score import Score
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )
        s = Score()
        s.track('drums')
        s.new(start=0.0, dur=0.5, inst=SynthDefInstrument.sampler('bb_kick'),
              track='drums', amp=0.7)
        payload = convert_score_to_sc_events(s)
        eng = SuperSonicEngine(payload["events"], meta=payload.get("meta"),
                               control_data=payload.get("control_data"),
                               record=True)
        self._check_blocks(eng._generate_html(), tmp_path)

    def test_recorder_js_parses_standalone(self, tmp_path):
        p = tmp_path / "recorder.mjs"
        p.write_text(RECORDER_SRC)
        proc = subprocess.run(["node", "--check", str(p)],
                              capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr


class TestPlayKwargPlumbing:
    def test_play_accepts_record_kwarg_everywhere(self):
        import inspect
        # smoke: the kwarg is popped before converters see it, so building
        # the widget through play()'s branches must not raise. We can't
        # display in tests, so go through the engine directly per branch —
        # the pop sites are asserted textually.
        src = inspect.getsource(
            __import__("klotho.utils.playback.player",
                       fromlist=["play"]).play)
        assert src.count("kwargs.pop('record', False)") >= 2

    def test_playback_kwargs_include_record(self):
        from klotho.semeios.visualization._dispatch._klotho_plot import (
            _PLAYBACK_KWARGS,
        )
        from klotho.semeios.visualization._dispatch.plot_score import (
            _PASSTHROUGH_KWARGS,
        )
        assert "record" in _PLAYBACK_KWARGS
        assert "record" in _PASSTHROUGH_KWARGS


# ===========================================================================
# Install-guard behaviour: does a page that already cached the SHIPPED
# bridge actually get a behaviourally-changed one?
#
# The static contracts above pin the *shape* of the guard.  They cannot see
# the failure this section exists for, which is that the shape stayed
# perfectly correct while the NUMBER went stale: a fix landed in the bridge
# and the marker it is guarded by did not move, so on every page holding a
# cached copy of the previous release the fix does not install at all.  That
# is a recorded lesson in this project, from the stop/purge race -- "a
# behavioural fix inside a shipped guard version => bump the marker".
#
# So these are behavioural: the REAL bridge source is executed in a Node
# ``vm`` against a page that has already been primed, and the question asked
# is the browser's question -- which build ends up under the public name.
# Modelled on the harness in ``tests/test_spatial_routing_js.py`` and
# ``tests/test_af1_play_error_surfacing.py``.
# ===========================================================================

_ROOT = Path(__file__).parent.parent

#: The commit whose build is on PyPI as **klotho-cac 10.18.0**.
#:
#: This used to be spelled ``origin/main``, which was correct only while
#: ``origin/main`` happened to equal the published release.  That accident
#: ENDED on 2026-09-01 when the Haddad block merged: ``origin/main`` became
#: ``f37fd51`` (version 11.0.0, unpublished), so "the released bridge" and
#: "the bridge on main" stopped being the same file and the A/B below started
#: comparing a build against itself.  Its own sanity assertion caught that --
#: the test went red rather than vacuous, which is why this pin exists.
#:
#: **Move this when a RELEASE is published, not when ``main`` moves.**
RELEASED_COMMIT = "9c1646c"

#: The markers a cached **klotho-cac 10.18.0** page has already defined.
#: Read off the released build, not off the source under test:
#: ``git show 9c1646c:klotho/utils/playback/_animation_bridge.js``
#: assigns exactly V2, V3 and V4 on its way out (verified 2026-09-01).
SHIPPED_MARKERS_1018 = [
    "__klothoPlaybackBridgeV2",
    "__klothoPlaybackBridgeV3",
    "__klothoPlaybackBridgeV4",
]

#: A width the precompiled decoder family cannot serve, so ``play()`` is
#: refused inside the scheduler's setup.  32 is the top of the family --
#: ``scheduler_score.js`` builds the message as ``' declares ' + w +
#: ' speakers and the decoder family stops at '`` -- so 40 refuses.
_REFUSED_WIDTH = 40
_REFUSAL_PHRASE = "decoder family stops at"


STALE_BRIDGE_PROBE_JS = r'''
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import vm from 'node:vm';

const argv = process.argv.slice(2);
const ROOT = argv[argv.indexOf('--root') + 1];
const seedIx = argv.indexOf('--seed');
const SEED = (seedIx !== -1 && argv[seedIx + 1])
  ? argv[seedIx + 1].split(',').filter(Boolean) : [];
const staleIx = argv.indexOf('--stale-bridge');
const STALE_BRIDGE = staleIx !== -1 ? argv[staleIx + 1] : null;
const widthIx = argv.indexOf('--width');
const WIDTH = widthIx !== -1 ? Number(argv[widthIx + 1]) : 40;

const SS_DIR = join(ROOT, 'klotho', 'utils', 'playback', 'supersonic');
const BRIDGE_FILE = join(ROOT, 'klotho', 'utils', 'playback',
                         '_animation_bridge.js');

// The browser's own verdict on an unhandled rejection.  Anything landing
// here reached no handler -- i.e. the devtools console and nowhere else.
const unhandled = [];
process.on('unhandledRejection', (r) => {
  unhandled.push(String((r && r.message) || r));
});

const consoleErrors = [];
const sonic = {
  _id: 1000,
  nextNodeId() { return this._id++; },
  send() {},
  sendOSC() {},
  purge() {},
  async sync() {},
  getMetrics() { return {}; },
  audioContext: { state: 'running', resume: async () => {} },
};

const sandbox = {
  performance: { timeOrigin: 0, now: () => 0 },
  setTimeout: () => 1,
  clearTimeout: () => {},
  console: {
    log: () => {}, debug: () => {}, warn: () => {},
    error: (...a) => { consoleErrors.push(a.join(' ')); },
  },
  atob: (s) => Buffer.from(s, 'base64').toString('binary'),
  DrawScheduler: class { schedule() {} clear() {} },
  SuperSonic: {
    osc: { encodeSingleBundle: (ntp, addr, args) => ({ ntp, addr, args }) },
  },
  __klothoSonic: {
    bootConfig: { scsynthOptions: { numAudioBusChannels: 1024 } },
    _nextBufnum: 7,
    instance: sonic,
  },
  __ensureSuperSonic: async () => sonic,
  __klothoSynthdefAssets: {
    '__busRouter': 'x', '__busRouterMonitor': 'x', '__chainLimiter': 'x',
    '__klEnvCtrl': 'x', 'kl_tri': 'x',
    '__busRouter1': 'x', '__busRouter2': 'x', '__busRouter4': 'x',
    '__busRouter8': 'x', '__busRouter16': 'x', '__busRouter32': 'x',
    '__spatialDecode1': 'x', '__spatialDecode2': 'x', '__spatialDecode4': 'x',
    '__spatialDecode8': 'x', '__spatialDecode16': 'x', '__spatialDecode32': 'x',
  },
  Blob: class { constructor(parts) { this.parts = parts; } },
};
vm.createContext(sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_core.js'), 'utf8'), sandbox);
vm.runInContext(readFileSync(join(SS_DIR, 'scheduler_score.js'), 'utf8'), sandbox);

// ---- prime the page, exactly as a cached saved output would -------------
const out = {};
if (STALE_BRIDGE) {
  // The genuine article: a previously released bridge, run first, claiming
  // its own marker names and the public name.
  vm.runInContext(readFileSync(STALE_BRIDGE, 'utf8'), sandbox);
  out.primedWith = 'real-source';
} else {
  // Marker-only priming: no old build needed to ask the guard's question.
  const STALE = function stalePlaceholder() { throw new Error('stale ran'); };
  sandbox.KlothoPlaybackBridge = STALE;
  for (const name of SEED) sandbox[name] = STALE;
  out.primedWith = 'markers';
}
out.seeded = SEED;
const before = sandbox.KlothoPlaybackBridge;

// ---- now render a fresh widget on that same page ------------------------
vm.runInContext(readFileSync(BRIDGE_FILE, 'utf8'), sandbox);
out.publicReplaced = sandbox.KlothoPlaybackBridge !== before;

// ---- and ask whether the CURRENT behaviour is what actually runs --------
// The discriminator is the AF-1 refusal surfacing: the shipped 10.18.0
// bridge calls play() with neither await nor .catch, so a refused play is an
// unhandled rejection and no onError exists at all.  If the fixed build
// installed, onError carries the message and nothing goes unhandled.
const arrayMeta = (w) => {
  const labels = [];
  for (let i = 0; i < w; i++) labels.push('S' + (i + 1));
  return { name: 'arr', labels, width: w,
           positions: null, units: null, speedOfSound: null, decoder: null };
};
const tick = (ms) => new Promise((r) => setTimeout(r, ms));

// Only meaningful when a real build won the public name.  In the
// marker-primed short-circuit case the placeholder is still installed and
// calling it would abort the probe, turning a clean verdict into a crash --
// so report the verdict and stop.
out.ready = null;
out.onErrorMsg = null;
out.onIdleFired = null;
if (out.publicReplaced) {
  const bridge = sandbox.KlothoPlaybackBridge({
    audioPayload: { events: [{
      id: 1, type: 'new', defName: 'kl_tri', start: 0, dur: 1, group: 'a',
      pfields: { freq: 220, amp: 0.3 },
    }] },
    ringTime: 0.1,
    meta: { groups: ['a'], spatial: {
      arrays: { arr: arrayMeta(WIDTH) },
      tracks: { a: { array: 'arr', width: WIDTH } },
    } },
    manifest: { kl_tri: { amp: 0.5, gate: 1 } },
  });
  out.ready = await bridge.ensureReady();

  let onErrorMsg = null, onIdleFired = false;
  // Fire-and-forget, exactly how _engine_widget.js's doPlay() calls it.
  bridge.play(null, {
    onIdle: function () { onIdleFired = true; },
    onError: function (m) { onErrorMsg = String(m); },
  });
  await tick(80);
  out.onErrorMsg = onErrorMsg;
  out.onIdleFired = onIdleFired;
}

out.unhandledRejections = unhandled;
out.consoleErrors = consoleErrors;
process.stdout.write(JSON.stringify(out));
'''


@pytest.fixture(scope="module")
def stale_bridge_probe(tmp_path_factory):
    p = tmp_path_factory.mktemp("bridge_guard") / "stale_bridge_probe.mjs"
    p.write_text(STALE_BRIDGE_PROBE_JS)
    return p


def _run_stale_probe(probe, seed=(), stale_bridge=None, width=_REFUSED_WIDTH):
    cmd = ["node", str(probe), "--root", str(_ROOT),
           "--seed", ",".join(seed), "--width", str(width)]
    if stale_bridge is not None:
        cmd += ["--stale-bridge", str(stale_bridge)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
class TestBridgeInstallsOverACachedPage:
    """A page holding the previous release's marker must still get this build.

    ``_animation_bridge.js``'s marker is a **shipped** one -- unlike
    ``scheduler_core.js``'s, which was bumped to V6 on this branch and so was
    never released under its current behaviour.  Every marker in
    :data:`SHIPPED_MARKERS_1018` is already defined in a notebook page that
    rendered a 10.18.0 widget, so the guard sees them on real users' pages.
    """

    def test_shipped_marker_set_does_not_block_this_build(
            self, stale_bridge_probe):
        """The whole finding, in one assertion.

        With V2/V3/V4 already defined -- which is the state of every cached
        10.18.0 page -- the current bridge must still install, and the fix it
        carries must be the behaviour that actually runs.
        """
        r = _run_stale_probe(stale_bridge_probe, seed=SHIPPED_MARKERS_1018)
        assert r["publicReplaced"] is True, (
            "the bridge short-circuited on a marker the last RELEASE already "
            "defines, so this build never installs on a cached page")
        assert r["ready"] is True
        # …and the behaviour that runs is this build's, not a placeholder's.
        assert r["onErrorMsg"] is not None
        assert _REFUSAL_PHRASE in r["onErrorMsg"]
        assert r["unhandledRejections"] == []

    def test_this_builds_own_marker_set_still_short_circuits(
            self, stale_bridge_probe):
        """The guard is bumped, not deleted.

        Re-including the same build (two widgets in one notebook) must be a
        no-op; otherwise every extra widget would rebuild the bridge and a
        genuinely stale copy rendering later could still win the public name.
        """
        newest = _newest_bridge_marker()
        seed = [f"__klothoPlaybackBridgeV{n}" for n in range(2, newest + 1)]
        r = _run_stale_probe(stale_bridge_probe, seed=seed)
        assert r["publicReplaced"] is False, (
            f"seeding every marker up to V{newest} did not short-circuit the "
            "install -- the guard no longer guards")

    def test_the_real_released_bridge_is_replaced(self, stale_bridge_probe,
                                                  tmp_path):
        """The same question, with no placeholder: run the genuine released
        bridge first, then render a new widget on that page.

        The expectation does not come from the new code.  The released build
        is the one whose ``play()`` has neither ``await`` nor ``.catch`` --
        that is why a refusal was an unhandled rejection, pinned independently
        in ``tests/test_af1_play_error_surfacing.py``.  So if the released
        build is still the one under the public name, ``onError`` cannot fire
        (it does not exist there) and the refusal must show up unhandled.
        """
        try:
            text = subprocess.run(
                ["git", "show",
                 f"{RELEASED_COMMIT}:klotho/utils/playback"
                 "/_animation_bridge.js"],
                capture_output=True, text=True, cwd=str(_ROOT),
                check=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip(f"{RELEASED_COMMIT} not reachable from this checkout")
        released = tmp_path / "released_animation_bridge.js"
        released.write_text(text)
        # Sanity on the fixture itself: it must be an OLDER build, or this
        # test proves nothing.  If this fires, RELEASED_COMMIT is stale --
        # do NOT relax it to a skip, which would disable the test silently.
        assert _newest_bridge_marker(text) < _newest_bridge_marker(), (
            f"RELEASED_COMMIT ({RELEASED_COMMIT}) no longer names an OLDER "
            f"bridge than the source under test, so this A/B would compare a "
            f"build against itself and prove nothing")

        r = _run_stale_probe(stale_bridge_probe, stale_bridge=released)
        assert r["publicReplaced"] is True
        assert r["onErrorMsg"] is not None and _REFUSAL_PHRASE in r["onErrorMsg"]
        assert r["unhandledRejections"] == []


class TestGuardMarkersMoveWithBehaviour:
    """A behavioural change to a version-guarded module must move its marker.

    The rule this file exists to enforce, stated once and checked against the
    last release rather than against a literal: **if the module's source
    differs from the published build, its newest install-guard marker must be
    greater than the published one.**  The published build is
    ``RELEASED_COMMIT``, so the check stays live until a RELEASE goes out and
    goes vacuous only for a module nobody has touched since.

    **It used to read ``origin/main``, and that was the same thing only by
    accident.**  When the Haddad block merged on 2026-09-01, ``origin/main``
    became HEAD, every side matched, and all three parametrizations plus the
    score-extension case went silently VACUOUS -- green, and guarding nothing.
    Nothing failed, which is why this is written down: the sibling A/B below
    had a sanity assertion and went RED instead, and that red is the only
    reason the vacuum here was noticed.

    ``scheduler_score.js`` is the one exception, and deliberately so: its
    guard is a *prototype* flag on ``BrowserScheduler``, so a core bump
    installs a fresh class whose prototype has no flag and the extension
    re-installs.  Its marker therefore moves with the core's.
    """

    _MODULES = {
        "_animation_bridge.js": (
            "klotho/utils/playback/_animation_bridge.js",
            r"globalThis\.__klothoPlaybackBridgeV(\d+) = buildBridge;"),
        "scheduler_core.js": (
            "klotho/utils/playback/supersonic/scheduler_core.js",
            r"globalThis\.__klothoSchedCoreV(\d+) = true;"),
        "_recorder.js": (
            "klotho/utils/playback/_recorder.js",
            r"__klothoRecorderV(\d+)"),
    }

    @staticmethod
    def _released(rel_path):
        try:
            return subprocess.run(
                ["git", "show", f"{RELEASED_COMMIT}:{rel_path}"],
                capture_output=True, text=True,
                cwd=str(_ROOT), check=True).stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

    @staticmethod
    def _newest(pattern, text):
        ns = [int(n) for n in re.findall(pattern, text)]
        assert ns, "no version marker found"
        return max(ns)

    def test_released_commit_pin_is_not_stale(self):
        """The sentinel for every other check in this class.

        Each check below returns early when ``old == new``, so a STALE
        ``RELEASED_COMMIT`` does not make them fail -- it makes them go
        quiet.  Measured on 2026-09-01 by pointing the pin at ``HEAD``: the
        A/B in the sibling class went red, and all four checks here passed
        while guarding nothing.  This test is the one that goes red instead.

        The bridge is the probe because it is the module that has moved most
        recently; if a future release makes this vacuous too, that is the
        signal to pick a different probe, not to delete the test.
        """
        old = self._released(self._MODULES["_animation_bridge.js"][0])
        if old is None:
            pytest.skip(f"{RELEASED_COMMIT} not reachable from this checkout")
        assert _newest_bridge_marker(old) < _newest_bridge_marker(), (
            f"RELEASED_COMMIT ({RELEASED_COMMIT}) no longer names a build "
            f"OLDER than the tree, so every changed-module check in this "
            f"class is silently vacuous. Repoint it at the commit whose "
            f"build is on PyPI -- it moves on a RELEASE, not when main moves")

    @pytest.mark.parametrize("name", sorted(_MODULES))
    def test_changed_module_has_a_bumped_marker(self, name):
        rel, pattern = self._MODULES[name]
        old = self._released(rel)
        if old is None:
            pytest.skip(f"{RELEASED_COMMIT} not reachable from this checkout")
        new = (_ROOT / rel).read_text()
        if old == new:
            return  # unchanged since the release; nothing to bump
        assert self._newest(pattern, new) > self._newest(pattern, old), (
            f"{name} changed since the last release but its install guard "
            f"marker did not move: every page that cached the released build "
            f"will short-circuit the install and keep running the old one")

    def test_changed_score_extension_rides_a_core_bump(self):
        """The prototype-flag exception, checked rather than assumed."""
        rel = "klotho/utils/playback/supersonic/scheduler_score.js"
        old = self._released(rel)
        if old is None:
            pytest.skip(f"{RELEASED_COMMIT} not reachable from this checkout")
        new = (_ROOT / rel).read_text()
        if old == new:
            return
        pat = r"__klothoScoreExtV(\d+)"
        core_rel, core_pat = self._MODULES["scheduler_core.js"]
        old_core = self._released(core_rel)
        assert (self._newest(pat, new) > self._newest(pat, old)
                or self._newest(core_pat, CORE_SRC)
                > self._newest(core_pat, old_core)), (
            "scheduler_score.js changed since the last release, but neither "
            "its own prototype marker nor the core's global marker moved -- "
            "a cached page keeps the released extension methods")
