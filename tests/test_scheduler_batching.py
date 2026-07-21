"""Scheduler batching must never overflow the engine's 512-slot queue.

supersonic-scsynth holds at most 512 scheduled bundles (its
``SCHEDULER_SLOT_COUNT``); an arriving timestamped bundle is silently
dropped when the queue is full. The BrowserScheduler therefore budgets
batches in *bundles* (an event's /s_new plus its late-bound gate release
plus any /n_map mappings), tracks every in-flight bundle on a shared load
heap, and gates each batch on remaining headroom.

Static tests assert the source-level contract; behavioral tests run the
real JS under Node against a 512-slot engine model (see
``fixtures/scheduler_batching_harness.mjs``).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SS_DIR = Path(__file__).parent.parent / "klotho" / "utils" / "playback" / "supersonic"
CORE = (SS_DIR / "scheduler_core.js").read_text()
SCORE = (SS_DIR / "scheduler_score.js").read_text()
HARNESS = Path(__file__).parent / "fixtures" / "scheduler_batching_harness.mjs"

ENGINE_SLOTS = 512


def _const(src, name):
    m = re.search(rf"var {name} = (\d+);", src)
    assert m, f"{name} not declared in scheduler_core.js"
    return int(m.group(1))


# ---- static contract -------------------------------------------------------


class TestSourceContract:
    def test_constants_leave_engine_headroom(self):
        slots = _const(CORE, "SCHEDULER_QUEUE_SLOTS")
        safe = _const(CORE, "SAFE_QUEUE_LIMIT")
        max_bundles = _const(CORE, "MAX_BUNDLES_PER_BATCH")
        min_bundles = _const(CORE, "MIN_BATCH_BUNDLES")

        assert slots == ENGINE_SLOTS, "must match supersonic SCHEDULER_SLOT_COUNT"
        # Post-batch load is bounded by SAFE_QUEUE_LIMIT plus a per-event cost
        # overshoot; the gap to the hard capacity absorbs that overshoot.
        assert safe <= slots - 64
        assert max_bundles <= safe
        assert 0 < min_bundles < max_bundles

    def test_all_scheduled_sends_go_through_choke_point(self):
        # _sendScheduled is the sole sendOSC call site in core; the score
        # extension must route through it too.
        assert CORE.count(".sendOSC(") == 1
        assert re.search(
            r"_sendScheduled\(dueNTP, bundle\) \{[^}]*sendOSC", CORE, re.S
        ), "_sendScheduled must own the sendOSC call"
        assert ".sendOSC(" not in SCORE

    def test_control_synths_are_stream_items(self):
        assert "_controlStreamItems" in SCORE
        assert "_sendControlItem" in SCORE
        assert "_scheduleControlSynths" not in SCORE
        assert "_scheduleControlSynths" not in CORE
        assert "_buildSendPlan" in CORE

    def test_batching_is_bundle_budgeted(self):
        assert "MAX_EVENTS_PER_BATCH" not in CORE, (
            "event-count batching must be replaced by bundle budgeting"
        )
        assert "_batchBundleCount < budget" in CORE


# ---- behavioral simulation under Node --------------------------------------

node = shutil.which("node")

CASES = {
    # case name -> lateness allowed?
    "real-shape": False,
    "all-gated": False,
    "wall": True,  # 600 simultaneous gated events: late > dropped, by design
    "control-envelopes": False,
    "fx-automation": False,
}


def _run_case(name):
    proc = subprocess.run(
        [node, str(HARNESS), name],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, f"harness failed: {proc.stderr}"
    return json.loads(proc.stdout)


@pytest.mark.skipif(node is None, reason="node not installed")
class TestEngineQueueSimulation:
    @pytest.mark.parametrize("case", list(CASES))
    def test_no_bundles_dropped(self, case):
        result = _run_case(case)
        safe = _const(CORE, "SAFE_QUEUE_LIMIT")
        assert result["finished"], "piece must reach onFinish"
        assert result["dropped"] == 0, (
            f"{result['dropped']} bundles dropped by the 512-slot engine model"
        )
        # Small allowance over SAFE_QUEUE_LIMIT: a batch stops only after the
        # event whose bundles cross the budget.
        assert result["peak"] <= safe + 8, f"peak queue {result['peak']}"
        if not CASES[case]:
            assert result["lateSends"] == 0, (
                f"{result['lateSends']} bundles sent after their due time"
            )

    def test_fx_automation_maps_once_per_envelope(self):
        # Insert-FX control envelopes target 'set' events (the FX synth is
        # created in setupTracks); _bundleSet must wire exactly one /n_map
        # per envelope via the exact start-time match -- not one per
        # (event, envelope) pair, and not zero.
        result = _run_case("fx-automation")
        assert result["finished"]
        assert result["dropped"] == 0
        assert len(result["nMapTimesMs"]) == 12

    def test_control_synths_not_front_loaded(self):
        result = _run_case("control-envelopes")
        times = result["ctrlSendTimesMs"]
        assert len(times) == 300, "every control synth must be sent exactly once"
        # Envelopes are spread over 100 s of timeline; late ones must ship
        # with their stretch of the piece, not at play start.
        assert max(times) > 50_000
        assert min(times) < 5_000
