"""Tests for tie-splitting algorithms."""

import pytest
from fractions import Fraction

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from notation_pipeline.core.tie_split import (
    split_duration,
    split_proportion,
    split_proportion_fraction,
    compute_beat_boundaries,
    split_at_boundaries,
    measure_split_points_global,
    decompose_note_durations,
)


class TestSplitDuration:
    """Test greedy power-of-two decomposition."""

    def test_already_engravable(self):
        assert split_duration(Fraction(1, 4)) == [Fraction(1, 4)]

    def test_dotted_engravable(self):
        assert split_duration(Fraction(3, 8)) == [Fraction(3, 8)]

    def test_five_eighths(self):
        # 5/8 -> 1/2 + 1/8
        result = split_duration(Fraction(5, 8))
        assert sum(result) == Fraction(5, 8)
        assert all(r > 0 for r in result)
        assert result == [Fraction(1, 2), Fraction(1, 8)]

    def test_five_sixteenths(self):
        # 5/16 -> 1/4 + 1/16
        result = split_duration(Fraction(5, 16))
        assert sum(result) == Fraction(5, 16)
        assert result == [Fraction(1, 4), Fraction(1, 16)]

    def test_whole_plus_quarter(self):
        # 5/4 -> 1/1 + 1/4
        result = split_duration(Fraction(5, 4))
        assert sum(result) == Fraction(5, 4)
        assert result == [Fraction(1, 1), Fraction(1, 4)]

    def test_two_wholes(self):
        # 2/1 -> 7/4 + 1/4 (double-dotted whole + quarter)
        result = split_duration(Fraction(2, 1))
        assert sum(result) == Fraction(2, 1)

    def test_zero(self):
        assert split_duration(Fraction(0)) == [Fraction(0)]

    def test_no_dots(self):
        # 3/8 is dotted quarter; with max_dots=0 it needs splitting
        result = split_duration(Fraction(3, 8), max_dots=0)
        assert sum(result) == Fraction(3, 8)
        assert result == [Fraction(1, 4), Fraction(1, 8)]


class TestComputeBeatBoundaries:
    """Test beat boundary computation from time signatures."""

    def test_4_4(self):
        from klotho.chronos import Meas
        boundaries = compute_beat_boundaries(Meas(4, 4))
        assert boundaries == [Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)]

    def test_3_4(self):
        from klotho.chronos import Meas
        boundaries = compute_beat_boundaries(Meas(3, 4))
        assert boundaries == [Fraction(1, 4), Fraction(1, 2)]

    def test_6_8_compound(self):
        from klotho.chronos import Meas
        # 6/8 is compound: 2 beats of 3/8 each
        boundaries = compute_beat_boundaries(Meas(6, 8))
        assert boundaries == [Fraction(3, 8)]

    def test_9_8_compound(self):
        from klotho.chronos import Meas
        # 9/8: 3 beats of 3/8
        boundaries = compute_beat_boundaries(Meas(9, 8))
        assert boundaries == [Fraction(3, 8), Fraction(3, 4)]

    def test_2_4(self):
        from klotho.chronos import Meas
        boundaries = compute_beat_boundaries(Meas(2, 4))
        assert boundaries == [Fraction(1, 4)]

    def test_5_4(self):
        from klotho.chronos import Meas
        boundaries = compute_beat_boundaries(Meas(5, 4))
        assert boundaries == [
            Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1)
        ]


class TestSplitAtBoundaries:
    """Test beat-boundary-aware splitting."""

    def test_no_crossing(self):
        from klotho.chronos import Meas
        # Quarter note starting at beat 1 in 4/4 — no boundary crossed
        result = split_at_boundaries(Fraction(1, 4), Fraction(0), Meas(4, 4))
        assert result == [Fraction(1, 4)]

    def test_half_note_crossing_midbar(self):
        from klotho.chronos import Meas
        # Half note starting at beat 2 (onset 1/4) in 4/4
        # Crosses the half-bar boundary at 1/2
        result = split_at_boundaries(Fraction(1, 2), Fraction(1, 4), Meas(4, 4))
        assert sum(result) == Fraction(1, 2)
        # Should split at 1/2: [1/4, 1/4]
        assert result == [Fraction(1, 4), Fraction(1, 4)]

    def test_half_note_on_beat(self):
        from klotho.chronos import Meas
        # Half note starting at beat 1 — crosses beat 2 boundary at 1/4
        result = split_at_boundaries(Fraction(1, 2), Fraction(0), Meas(4, 4))
        # Crosses boundary at 1/4 -> [1/4, 1/4]
        assert sum(result) == Fraction(1, 2)

    def test_zero_duration(self):
        from klotho.chronos import Meas
        result = split_at_boundaries(Fraction(0), Fraction(0), Meas(4, 4))
        assert result == [Fraction(0)]

    def test_compound_meter(self):
        from klotho.chronos import Meas
        # In 6/8, dotted quarter (3/8) starting at 0 — no boundary (fills first beat group)
        result = split_at_boundaries(Fraction(3, 8), Fraction(0), Meas(6, 8))
        assert result == [Fraction(3, 8)]

    def test_compound_crossing(self):
        from klotho.chronos import Meas
        # Quarter note (1/4) starting at 1/8 in 6/8 — crosses boundary at 3/8
        result = split_at_boundaries(Fraction(1, 4), Fraction(1, 4), Meas(6, 8))
        # onset=1/4, end=1/2, boundary at 3/8 -> [1/8, 1/8]
        assert sum(result) == Fraction(1, 4)
        assert result == [Fraction(1, 8), Fraction(1, 8)]


class TestMeasureBoundarySplit:
    def test_measure_split_points_two_measures(self):
        from klotho.chronos import Meas
        md = Fraction(Meas(4, 4).numerator, Meas(4, 4).denominator)
        assert md == Fraction(1, 1)
        pts = measure_split_points_global(Fraction(0), Fraction(2, 1), md)
        assert pts == [Fraction(1, 1)]

    def test_global_onset_split_at_boundaries(self):
        from klotho.chronos import Meas
        result = split_at_boundaries(Fraction(1, 2), Fraction(5, 4), Meas(4, 4))
        assert sum(result) == Fraction(1, 2)
        assert result == [Fraction(1, 4), Fraction(1, 4)]

    def test_decompose_cross_measure_whole(self):
        from klotho.chronos import Meas
        durs = decompose_note_durations(
            Fraction(0), Fraction(2, 1), Meas(4, 4), split_measures=True,
        )
        assert sum(durs) == Fraction(2, 1)
        assert len(durs) >= 2


class TestSplitProportion:
    """Tests for OM-style proportion decomposition (port of only-one-point)."""

    def test_power_of_two(self):
        assert split_proportion(1) == [1]
        assert split_proportion(2) == [2]
        assert split_proportion(4) == [4]
        assert split_proportion(8) == [8]
        assert split_proportion(16) == [16]
        assert split_proportion(32) == [32]

    def test_dotted(self):
        assert split_proportion(3) == [3]
        assert split_proportion(6) == [6]
        assert split_proportion(12) == [12]

    def test_five(self):
        assert split_proportion(5) == [4, 1]

    def test_seven(self):
        result = split_proportion(7)
        assert sum(result) == 7
        assert result == [7]

    def test_nine(self):
        result = split_proportion(9)
        assert sum(result) == 9

    def test_ten(self):
        result = split_proportion(10)
        assert sum(result) == 10

    def test_eleven(self):
        result = split_proportion(11)
        assert sum(result) == 11

    def test_zero(self):
        assert split_proportion(0) == [0]

    def test_fraction_helper(self):
        result = split_proportion_fraction(Fraction(5, 4))
        assert sum(result) == Fraction(5, 4)
        assert result == [Fraction(4, 4), Fraction(1, 4)]

    def test_fraction_engravable_passthrough(self):
        result = split_proportion_fraction(Fraction(3, 8))
        assert result == [Fraction(3, 8)]
