"""Baseline regression tests for the notation pipeline.

Compares live pipeline output against stored JSON baselines at three levels:
  Level 1 (structural): exact match on event types, counts, durations, ties, tuplets, beams
  Level 2 (ordering):   x-position monotonicity, barline ordering, no collisions
  Level 3 (snapshot):   x-positions match baseline within tolerance

Run ``generate_baselines.py`` to create/update baselines from known-good output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[2]
if str(experiments_dir) not in sys.path:
    sys.path.insert(0, str(experiments_dir))

from klotho.chronos import RhythmTree as RT

from notation_pipeline.pipeline import notate
from notation_pipeline.pipeline_uts import notate_uts
from notation_pipeline.pipeline_bt import notate_bt

from notation_pipeline.render_examples import EXAMPLES as RT_EXAMPLES
from notation_pipeline.render_barline_splits import EXAMPLES as BARLINE_EXAMPLES
from notation_pipeline.render_span_edge_cases import EXAMPLES as SPAN_EXAMPLES
from notation_pipeline.render_containers import make_uts_examples, make_bt_examples

from .baseline_utils import (
    BASELINES_DIR,
    assert_ordering_invariants,
    assert_structural_match,
    assert_x_positions_match,
    load_baseline,
    serialize_measure,
    serialize_score,
    serialize_system,
)


def _rt_ids(examples):
    return [ex[0] for ex in examples]


def _notate_rt(example):
    name, meas_str, subdivisions = example[0], example[1], example[2]
    span = example[3] if len(example) > 3 else 1
    tempo_beat = example[4] if len(example) > 4 else None
    tempo_bpm = example[5] if len(example) > 5 else None
    rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
    return notate(rt, spacing_mode='hybrid', tempo_beat=tempo_beat, tempo_bpm=tempo_bpm)


_uts_examples = make_uts_examples()
_bt_examples = make_bt_examples()


def _has_baseline(category, name):
    return (BASELINES_DIR / category / f"{name}.json").exists()


# ═══════════════════════════════════════════════════════════════════════
# RT examples
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("example", RT_EXAMPLES, ids=_rt_ids(RT_EXAMPLES))
class TestRTBaselines:
    def test_structural(self, example):
        name = example[0]
        if not _has_baseline("rt", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("rt", name)
        assert_structural_match(actual, baseline, label=name)

    def test_ordering(self, example):
        actual = serialize_measure(_notate_rt(example))
        assert_ordering_invariants(actual, label=example[0])

    def test_x_positions(self, example):
        name = example[0]
        if not _has_baseline("rt", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("rt", name)
        assert_x_positions_match(actual, baseline, label=name)


# ═══════════════════════════════════════════════════════════════════════
# Barline split examples
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("example", BARLINE_EXAMPLES, ids=_rt_ids(BARLINE_EXAMPLES))
class TestBarlineSplitBaselines:
    def test_structural(self, example):
        name = example[0]
        if not _has_baseline("barline_splits", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("barline_splits", name)
        assert_structural_match(actual, baseline, label=name)

    def test_ordering(self, example):
        actual = serialize_measure(_notate_rt(example))
        assert_ordering_invariants(actual, label=example[0])

    def test_x_positions(self, example):
        name = example[0]
        if not _has_baseline("barline_splits", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("barline_splits", name)
        assert_x_positions_match(actual, baseline, label=name)


# ═══════════════════════════════════════════════════════════════════════
# Span edge case examples
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("example", SPAN_EXAMPLES, ids=_rt_ids(SPAN_EXAMPLES))
class TestSpanEdgeCaseBaselines:
    def test_structural(self, example):
        name = example[0]
        if not _has_baseline("span_edge_cases", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("span_edge_cases", name)
        assert_structural_match(actual, baseline, label=name)

    def test_ordering(self, example):
        actual = serialize_measure(_notate_rt(example))
        assert_ordering_invariants(actual, label=example[0])

    def test_x_positions(self, example):
        name = example[0]
        if not _has_baseline("span_edge_cases", name):
            pytest.skip("baseline not generated")
        actual = serialize_measure(_notate_rt(example))
        baseline = load_baseline("span_edge_cases", name)
        assert_x_positions_match(actual, baseline, label=name)


# ═══════════════════════════════════════════════════════════════════════
# UTS examples
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("name,uts", _uts_examples, ids=[n for n, _ in _uts_examples])
class TestUTSBaselines:
    def test_structural(self, name, uts):
        if not _has_baseline("uts", name):
            pytest.skip("baseline not generated")
        system = notate_uts(uts, spacing_mode='hybrid', barlines=True)
        actual = serialize_system(system)
        baseline = load_baseline("uts", name)
        assert actual["measure_count"] == baseline["measure_count"], (
            f"[{name}] measure count: {actual['measure_count']} != {baseline['measure_count']}"
        )
        for i, (am, bm) in enumerate(zip(actual["measures"], baseline["measures"])):
            assert_structural_match(am, bm, label=f"{name}/m{i}")

    def test_ordering(self, name, uts):
        system = notate_uts(uts, spacing_mode='hybrid', barlines=True)
        actual = serialize_system(system)
        for i, m in enumerate(actual["measures"]):
            assert_ordering_invariants(m, label=f"{name}/m{i}")

    def test_x_positions(self, name, uts):
        if not _has_baseline("uts", name):
            pytest.skip("baseline not generated")
        system = notate_uts(uts, spacing_mode='hybrid', barlines=True)
        actual = serialize_system(system)
        baseline = load_baseline("uts", name)
        for i, (am, bm) in enumerate(zip(actual["measures"], baseline["measures"])):
            assert_x_positions_match(am, bm, label=f"{name}/m{i}")


# ═══════════════════════════════════════════════════════════════════════
# BT examples
# ═══════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("name,bt", _bt_examples, ids=[n for n, _ in _bt_examples])
class TestBTBaselines:
    def test_structural(self, name, bt):
        if not _has_baseline("bt", name):
            pytest.skip("baseline not generated")
        score = notate_bt(bt, spacing_mode='hybrid', barlines=True)
        actual = serialize_score(score)
        baseline = load_baseline("bt", name)
        assert actual["row_count"] == baseline["row_count"], (
            f"[{name}] row count: {actual['row_count']} != {baseline['row_count']}"
        )
        for r, (ar, br) in enumerate(zip(actual["rows"], baseline["rows"])):
            assert ar["measure_count"] == br["measure_count"], (
                f"[{name}/row{r}] measure count mismatch"
            )
            for i, (am, bm) in enumerate(zip(ar["measures"], br["measures"])):
                assert_structural_match(am, bm, label=f"{name}/row{r}/m{i}")

    def test_ordering(self, name, bt):
        score = notate_bt(bt, spacing_mode='hybrid', barlines=True)
        actual = serialize_score(score)
        for r, row in enumerate(actual["rows"]):
            for i, m in enumerate(row["measures"]):
                assert_ordering_invariants(m, label=f"{name}/row{r}/m{i}")

    def test_x_positions(self, name, bt):
        if not _has_baseline("bt", name):
            pytest.skip("baseline not generated")
        score = notate_bt(bt, spacing_mode='hybrid', barlines=True)
        actual = serialize_score(score)
        baseline = load_baseline("bt", name)
        for r, (ar, br) in enumerate(zip(actual["rows"], baseline["rows"])):
            for i, (am, bm) in enumerate(zip(ar["measures"], br["measures"])):
                assert_x_positions_match(am, bm, label=f"{name}/row{r}/m{i}")
