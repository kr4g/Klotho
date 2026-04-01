"""Regression tests for TemporalBlock (BT) notation layout."""

from fractions import Fraction
from collections import Counter

import pytest

from klotho.chronos import RhythmTree as RT, TemporalBlock, TemporalUnit, TemporalUnitSequence

from notation_pipeline.models import EngravingLeaf, NoteType
from notation_pipeline.pipeline import notate
from notation_pipeline.pipeline_bt import _event_abs_time_in_ut, notate_bt


def test_event_abs_time_uses_parent_ut_not_global_metric():
    ut0 = TemporalUnit(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120)
    ut1 = TemporalUnit(tempus="4/4", prolatio=((1, (1, 1)), 1, 1, 1), beat="1/4", bpm=120)
    z = EngravingLeaf(
        node_id=0,
        duration=Fraction(1, 4),
        onset=Fraction(0),
        note_type=NoteType.QUARTER,
    )
    assert _event_abs_time_in_ut(z, ut0) == pytest.approx(0.0)
    assert _event_abs_time_in_ut(z, ut1) == pytest.approx(ut1.offset)


def test_bt_uts_two_measures_distinct_x_and_chained_barlines():
    ut_a1 = TemporalUnit(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120)
    ut_a2 = TemporalUnit(
        tempus="4/4", prolatio=((1, (1, 1)), 1, 1, 1), beat="1/4", bpm=120
    )
    uts = TemporalUnitSequence([ut_a1, ut_a2])
    score = notate_bt(TemporalBlock([uts]))
    sys0 = score.rows[0]
    assert len(sys0.measures) == 2
    m0, m1 = sys0.measures
    assert m0.barline_x_positions and m1.barline_x_positions
    assert m1.barline_x_positions[0] == m0.barline_x_positions[-1]
    x0 = [e.x for e in m0.events]
    x1 = [e.x for e in m1.events]
    assert max(x0) < min(x1)


def test_measure_anchor_captured_for_bt_first_measure():
    ut = TemporalUnit(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120)
    score = notate_bt(TemporalBlock([ut]))
    m0 = score.rows[0].measures[0]
    assert len(m0.barline_x_positions) >= 2
    assert m0.barline_x_positions[0] == pytest.approx(44.0)


def test_bt_05_first_measures_share_two_second_end_time():
    ut_4_4_120 = TemporalUnit(tempus="4/4", prolatio=(1, 1, 1, 1), beat="1/4", bpm=120)
    ut_3_4_90 = TemporalUnit(tempus="3/4", prolatio=(1, 1, 1), beat="1/4", bpm=90)
    assert ut_4_4_120.duration == pytest.approx(2.0)
    assert ut_3_4_90.duration == pytest.approx(2.0)
    ut_5_8_90 = TemporalUnit(
        tempus="5/8", prolatio=(1, 1, 1, 1, 1), beat="1/8", bpm=90
    )
    assert ut_5_8_90.duration != pytest.approx(2.0)


def test_span2_tuplet_crossing_bar_never_split():
    rt = RT(
        span=2,
        meas="4/4",
        subdivisions=(1, 1, 1, 1, 1, 1, 1),
    )
    m = notate(rt, spacing_mode="hybrid")
    assert len(m.events) == 7
    counts = Counter(e.node_id for e in m.events)
    assert all(c == 1 for c in counts.values())


def test_span2_non_tuplet_crossing_bar_does_split():
    rt = RT(
        span=2,
        meas="4/4",
        subdivisions=(1, 1, 1, 1, 1, 1, 1, 1),
    )
    m = notate(rt, spacing_mode="hybrid")
    assert len(m.events) == 8
    counts = Counter(e.node_id for e in m.events)
    assert all(c == 1 for c in counts.values())


def test_span2_nested_tuplet_crossing_bar_never_split():
    rt = RT(
        span=2,
        meas="4/4",
        subdivisions=((1, (1, 1, 1, 1, 1)), 1, 1, 1, 1),
    )
    m = notate(rt, spacing_mode="hybrid")
    assert len(m.events) == 9
    counts = Counter(e.node_id for e in m.events)
    assert all(c == 1 for c in counts.values())


def test_barline_split_uses_om_decomposition():
    rt = RT(span=2, meas="4/4", subdivisions=(1, 5, 1, 1))
    m = notate(rt, spacing_mode="hybrid")
    assert len(m.events) == 5
    tied_fwd = [e for e in m.events if e.is_tied_forward]
    assert len(tied_fwd) == 1
    assert tied_fwd[0].duration == Fraction(3, 4)


def test_barline_split_5_3():
    rt = RT(span=2, meas="4/4", subdivisions=(5, 3))
    m = notate(rt, spacing_mode="hybrid")
    assert sum(e.duration for e in m.events) == Fraction(2, 1)
    assert any(e.is_tied_forward for e in m.events)


def test_barline_split_3_5():
    rt = RT(span=2, meas="4/4", subdivisions=(3, 5))
    m = notate(rt, spacing_mode="hybrid")
    assert sum(e.duration for e in m.events) == Fraction(2, 1)
    assert any(e.is_tied_forward for e in m.events)


def test_rest_decomposition_non_engravable():
    rt = RT(span=2, meas="4/4", subdivisions=(-5, 3))
    m = notate(rt, spacing_mode="hybrid")
    rests = [e for e in m.events if e.is_rest]
    assert len(rests) >= 2
    assert sum(e.duration for e in rests) == Fraction(5, 4)


def test_ternary_tuplet_denom_6_8():
    rt = RT(meas="6/8", subdivisions=(1, 1, 1, 1, 1))
    m = notate(rt, spacing_mode="hybrid")
    five_tuplets = [t for t in m.tuplets if t.actual == 5]
    assert len(five_tuplets) == 1
    assert five_tuplets[0].normal == 6
