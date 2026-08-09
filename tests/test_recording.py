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
        install = CORE_SRC.index("if (globalThis.__klothoSchedCoreV5) return;")
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
        # V5 keys on its own name (pages with saved V4 outputs already set
        # V4, and their core fires finish before the trailing pause and
        # pads every teardown fence with the upstream sync() sleep)…
        assert "if (globalThis.__klothoSchedCoreV5) return;" in CORE_SRC
        assert "if (globalThis.BrowserScheduler) return;" not in CORE_SRC
        assert "globalThis.__klothoSchedCoreV5 = true;" in CORE_SRC
        # …but still claims every older marker so a stale core rendering
        # later can never downgrade the installed class.
        assert "globalThis.__klothoSchedCoreV2 = true;" in CORE_SRC
        assert "globalThis.__klothoSchedCoreV3 = true;" in CORE_SRC
        assert "globalThis.__klothoSchedCoreV4 = true;" in CORE_SRC
        assert "if (globalThis.__klothoSchedCoreV2) return;" not in CORE_SRC
        assert "if (globalThis.__klothoSchedCoreV3) return;" not in CORE_SRC
        assert "if (globalThis.__klothoSchedCoreV4) return;" not in CORE_SRC

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
    def test_versioned_guard_bumped_to_v4(self):
        assert '__klothoPlaybackBridgeV4 !== "undefined"' in BRIDGE_SRC
        assert '__klothoPlaybackBridgeV3 !== "undefined"' not in BRIDGE_SRC

    def test_v4_claims_all_versioned_names(self):
        """A stale 10.15/10.16 output rendered after a newer widget must
        not clobber the public name: V4 is a superset, so it owns every
        older name too."""
        assert "globalThis.__klothoPlaybackBridgeV2 = buildBridge" in BRIDGE_SRC
        assert "globalThis.__klothoPlaybackBridgeV3 = buildBridge" in BRIDGE_SRC
        assert "globalThis.__klothoPlaybackBridgeV4 = buildBridge" in BRIDGE_SRC

    def test_bridge_plumbs_on_idle_to_scheduler(self):
        """Controllers re-arm their play button at onIdle (finish +
        ring-out + teardown); the bridge must pass it through — and fire
        it on the no-events early return, or the icon sticks on stop."""
        assert "onIdle: onIdle," in BRIDGE_SRC
        assert "if (onIdle) onIdle();" in BRIDGE_SRC

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
