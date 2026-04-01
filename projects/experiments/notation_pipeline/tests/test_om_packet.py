"""Tests for OM packet spacing (spacing/om_packet.py)."""

import pytest
from fractions import Fraction

from notation_pipeline.models import NoteType, EngravingLeaf
from notation_pipeline.spacing.om_packet import (
    OM_FACTOR_SPACING,
    ryhtm2pixels,
    space_packet,
    space_size_offset_measure,
    get_chiffrage_space_px,
    build_timebpf_with_sentinel,
    interp_timebpf,
    metric_onset_to_seconds,
)


def test_ryhtm2pixels_quarter_reference():
    assert ryhtm2pixels(1000.0) == pytest.approx(1.0)
    assert ryhtm2pixels(500.0) == pytest.approx(OM_FACTOR_SPACING ** -1)
    assert ryhtm2pixels(2000.0) == pytest.approx(OM_FACTOR_SPACING**1)


def test_ryhtm2pixels_minimum():
    assert ryhtm2pixels(1e9) >= 0.25


def test_space_packet_two_notes_same_time_align():
    size = 24.0
    m1 = {"kind": "note", "budget": (0, 0, 0, 14.0), "id": "a"}
    m2 = {"kind": "note", "budget": (0, 0, 0, 20.0), "id": "b"}
    count, pos = space_packet([m1, m2], 44.0, 1000.0, size)
    assert pos["a"] == pos["b"]
    assert count > 44.0


def test_space_packet_measure_before_note_sort():
    size = 24.0
    note = {"kind": "note", "budget": (0, 0, 0, 14.0), "id": "n"}
    meas = {
        "kind": "measure",
        "budget": space_size_offset_measure(
            first_of_group=True,
            show_time_sig=True,
            first_measure_of_voice=True,
            metric_changed=False,
            size=size,
        ),
        "id": "m",
    }
    count0 = 44.0
    _, pos = space_packet([note, meas], count0, 1000.0, size)
    assert pos["m"] == count0
    assert pos["n"] > pos["m"]


def test_get_chiffrage_space_metric_unchanged():
    s = 24.0
    assert get_chiffrage_space_px(False, False, False, s) == round(s / 1.5)
    assert get_chiffrage_space_px(False, False, True, s) == s


def test_metric_onset_to_seconds():
    t = metric_onset_to_seconds(Fraction(1, 4), 60.0, Fraction(1, 4))
    assert t == pytest.approx(1.0)


def _leaf(onset, dur="1/4"):
    return EngravingLeaf(
        node_id=0,
        duration=Fraction(dur),
        onset=Fraction(onset),
        note_type=NoteType.QUARTER,
        dots=0,
        is_rest=False,
    )


def test_build_timebpf_sentinel():
    bpf = build_timebpf_with_sentinel([(0.0, 100.0), (1.0, 200.0)])
    assert max(bpf.keys()) > 1.0
    assert bpf[max(bpf.keys())] == 200.0 + 20.0


def test_interp_timebpf_extrapolate_beyond_sentinel():
    bpf = build_timebpf_with_sentinel([(0.0, 0.0), (1.0, 100.0)])
    x2 = interp_timebpf(2.0, bpf)
    assert x2 > 100.0
