"""Tests for spacing algorithms."""

import pytest
from fractions import Fraction

from notation_pipeline.models import NoteType, EngravingLeaf
from notation_pipeline.spacing.modes import (
    space_proportional,
    space_traditional,
    space_hybrid,
    compute_min_space,
)


def _make_event(onset, duration, note_type=NoteType.QUARTER, dots=0, is_rest=False):
    return EngravingLeaf(
        node_id=0,
        duration=Fraction(duration),
        onset=Fraction(onset),
        note_type=note_type,
        dots=dots,
        is_rest=is_rest,
    )


class TestComputeMinSpace:
    def test_plain_note(self):
        evt = _make_event(0, '1/4')
        space = compute_min_space(evt)
        assert space > 0

    def test_dotted_wider(self):
        plain = _make_event(0, '1/4')
        dotted = _make_event(0, '3/8', dots=1)
        assert compute_min_space(dotted) > compute_min_space(plain)

    def test_rest_has_width(self):
        rest = _make_event(0, '1/4', is_rest=True)
        assert compute_min_space(rest) > 0


class TestProportionalSpacing:
    def test_monotonic(self):
        events = [
            _make_event('0', '1/4'),
            _make_event('1/4', '1/4'),
            _make_event('1/2', '1/4'),
            _make_event('3/4', '1/4'),
        ]
        spaced = space_proportional(events)
        xs = [e.x for e in spaced]
        assert all(xs[i] < xs[i+1] for i in range(len(xs)-1))

    def test_equal_spacing(self):
        events = [
            _make_event('0', '1/4'),
            _make_event('1/4', '1/4'),
            _make_event('1/2', '1/4'),
        ]
        spaced = space_proportional(events, scale=400)
        # Equal durations -> equal spacing
        d1 = spaced[1].x - spaced[0].x
        d2 = spaced[2].x - spaced[1].x
        assert abs(d1 - d2) < 0.001

    def test_proportional_relationship(self):
        events = [
            _make_event('0', '1/2'),
            _make_event('1/2', '1/4'),
            _make_event('3/4', '1/4'),
        ]
        spaced = space_proportional(events, scale=400)
        # Half note onset gap = 1/2 of whole = 200 units
        # Quarter onset gap = 1/4 of whole = 100 units
        gap1 = spaced[1].x - spaced[0].x
        gap2 = spaced[2].x - spaced[1].x
        assert abs(gap1 - 2 * gap2) < 0.001


class TestTraditionalSpacing:
    def test_monotonic(self):
        events = [
            _make_event('0', '1/4'),
            _make_event('1/4', '1/4'),
            _make_event('1/2', '1/8', note_type=NoteType.EIGHTH),
            _make_event('5/8', '1/8', note_type=NoteType.EIGHTH),
        ]
        spaced = space_traditional(events)
        xs = [e.x for e in spaced]
        assert all(xs[i] < xs[i+1] for i in range(len(xs)-1))

    def test_empty(self):
        assert space_traditional([]) == []


class TestHybridSpacing:
    def test_monotonic(self):
        events = [
            _make_event('0', '1/4'),
            _make_event('1/4', '1/4'),
            _make_event('1/2', '1/4'),
        ]
        spaced = space_hybrid(events)
        xs = [e.x for e in spaced]
        assert all(xs[i] < xs[i+1] for i in range(len(xs)-1))

    def test_no_overlap(self):
        # Dense events that would overlap with pure proportional
        events = [
            _make_event('0', '1/32', note_type=NoteType.N32ND),
            _make_event('1/32', '1/32', note_type=NoteType.N32ND),
            _make_event('1/16', '1/32', note_type=NoteType.N32ND),
            _make_event('3/32', '1/32', note_type=NoteType.N32ND),
        ]
        spaced = space_hybrid(events, scale=400)
        for i in range(1, len(spaced)):
            gap = spaced[i].x - spaced[i-1].x
            min_gap = compute_min_space(spaced[i-1])
            assert gap >= min_gap - 0.001  # Allow tiny float imprecision

    def test_empty(self):
        assert space_hybrid([]) == []
