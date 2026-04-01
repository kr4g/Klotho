"""Tests for duration classification."""

import pytest
from fractions import Fraction

from notation_pipeline.models import NoteType
from notation_pipeline.core.duration import (
    classify_duration,
    beam_count,
    largest_engravable_leq,
    ENGRAVABLE_DURATIONS,
)


class TestClassifyDuration:
    """Test classify_duration for all engravable durations."""

    # Undotted base durations
    @pytest.mark.parametrize("dur, expected_type", [
        (Fraction(1, 1),   NoteType.WHOLE),
        (Fraction(1, 2),   NoteType.HALF),
        (Fraction(1, 4),   NoteType.QUARTER),
        (Fraction(1, 8),   NoteType.EIGHTH),
        (Fraction(1, 16),  NoteType.N16TH),
        (Fraction(1, 32),  NoteType.N32ND),
        (Fraction(1, 64),  NoteType.N64TH),
        (Fraction(1, 128), NoteType.N128TH),
    ])
    def test_undotted(self, dur, expected_type):
        result = classify_duration(dur)
        assert result is not None
        note_type, dots = result
        assert note_type == expected_type
        assert dots == 0

    # Single-dotted durations
    @pytest.mark.parametrize("dur, expected_type", [
        (Fraction(3, 2),   NoteType.WHOLE),    # dotted whole
        (Fraction(3, 4),   NoteType.HALF),     # dotted half
        (Fraction(3, 8),   NoteType.QUARTER),  # dotted quarter
        (Fraction(3, 16),  NoteType.EIGHTH),   # dotted eighth
        (Fraction(3, 32),  NoteType.N16TH),    # dotted 16th
        (Fraction(3, 64),  NoteType.N32ND),    # dotted 32nd
        (Fraction(3, 128), NoteType.N64TH),    # dotted 64th
        (Fraction(3, 256), NoteType.N128TH),   # dotted 128th
    ])
    def test_single_dotted(self, dur, expected_type):
        result = classify_duration(dur)
        assert result is not None
        note_type, dots = result
        assert note_type == expected_type
        assert dots == 1

    # Double-dotted durations
    @pytest.mark.parametrize("dur, expected_type", [
        (Fraction(7, 4),   NoteType.WHOLE),
        (Fraction(7, 8),   NoteType.HALF),
        (Fraction(7, 16),  NoteType.QUARTER),
        (Fraction(7, 32),  NoteType.EIGHTH),
        (Fraction(7, 64),  NoteType.N16TH),
        (Fraction(7, 128), NoteType.N32ND),
        (Fraction(7, 256), NoteType.N64TH),
        (Fraction(7, 512), NoteType.N128TH),
    ])
    def test_double_dotted(self, dur, expected_type):
        result = classify_duration(dur)
        assert result is not None
        note_type, dots = result
        assert note_type == expected_type
        assert dots == 2

    # Non-engravable durations
    @pytest.mark.parametrize("dur", [
        Fraction(1, 6),    # triplet quarter
        Fraction(5, 16),   # not a standard duration
        Fraction(5, 8),    # five eighths (needs tie-split)
        Fraction(1, 3),    # third of a whole
        Fraction(2, 3),    # two thirds
        Fraction(1, 5),    # quintuplet
    ])
    def test_non_engravable(self, dur):
        assert classify_duration(dur) is None

    def test_zero_duration(self):
        assert classify_duration(Fraction(0)) is None

    def test_max_dots_zero(self):
        # Dotted quarter should fail if max_dots=0
        assert classify_duration(Fraction(3, 8), max_dots=0) is None
        # Undotted quarter should still work
        result = classify_duration(Fraction(1, 4), max_dots=0)
        assert result == (NoteType.QUARTER, 0)

    def test_max_dots_one(self):
        # Single dotted should work
        result = classify_duration(Fraction(3, 8), max_dots=1)
        assert result == (NoteType.QUARTER, 1)
        # Double dotted should fail
        assert classify_duration(Fraction(7, 16), max_dots=1) is None

    def test_tuplet_context(self):
        # 1/6 inside a 3:2 tuplet -> notated as 1/4 (quarter)
        # tuplet_scale = normal/actual = 2/3
        result = classify_duration(Fraction(1, 6), tuplet_scale=Fraction(2, 3))
        assert result == (NoteType.QUARTER, 0)

    def test_table_completeness(self):
        # Should have 8 * 3 = 24 entries
        assert len(ENGRAVABLE_DURATIONS) == 24


class TestBeamCount:
    @pytest.mark.parametrize("note_type, expected", [
        (NoteType.WHOLE, 0),
        (NoteType.HALF, 0),
        (NoteType.QUARTER, 0),
        (NoteType.EIGHTH, 1),
        (NoteType.N16TH, 2),
        (NoteType.N32ND, 3),
        (NoteType.N64TH, 4),
        (NoteType.N128TH, 5),
    ])
    def test_beam_counts(self, note_type, expected):
        assert beam_count(note_type) == expected


class TestLargestEngravableLeq:
    def test_exact_match(self):
        assert largest_engravable_leq(Fraction(1, 4)) == Fraction(1, 4)

    def test_between_values(self):
        # 5/16 is between 1/4 (=4/16) and 3/8 (=6/16)
        # Largest engravable <= 5/16 is 1/4
        assert largest_engravable_leq(Fraction(5, 16)) == Fraction(1, 4)

    def test_large_value(self):
        # Largest engravable <= 2 is 7/4 (double-dotted whole)
        assert largest_engravable_leq(Fraction(2)) == Fraction(7, 4)

    def test_very_small(self):
        # Smallest engravable is 7/512 (double-dotted 128th)
        assert largest_engravable_leq(Fraction(1, 128)) == Fraction(1, 128)
        # 1/200 is smaller than 7/512 (~0.0137), so nothing fits
        result = largest_engravable_leq(Fraction(1, 200))
        assert result is None

    def test_dotted_128th(self):
        # 3/256 (dotted 128th) should be found for values >= 3/256
        result = largest_engravable_leq(Fraction(3, 256))
        assert result == Fraction(3, 256)
