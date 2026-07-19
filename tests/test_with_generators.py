"""ToneLattice.with_generators: same board, new generator basis."""
from fractions import Fraction

import pytest

from klotho.tonos import ToneLattice


@pytest.fixture
def tl_3x5():
    return ToneLattice.from_generators((3, 5), resolution=3).root('A4')


class TestWithGenerators:

    def test_board_preserved(self, tl_3x5):
        new = tl_3x5.with_generators((3, 7))
        assert new.resolution == tl_3x5.resolution
        assert new.bipolar == tl_3x5.bipolar
        assert new.equave == tl_3x5.equave
        assert new.equave_reduce == tl_3x5.equave_reduce
        assert new.dimensionality == tl_3x5.dimensionality
        assert set(new.coords) == set(tl_3x5.coords)

    def test_ratios_change(self, tl_3x5):
        new = tl_3x5.with_generators((3, 7))
        assert tl_3x5.get_ratio((0, 1)) == Fraction(5, 4)
        assert new.get_ratio((0, 1)) == Fraction(7, 4)
        assert new.get_ratio((1, 0)) == tl_3x5.get_ratio((1, 0)) == Fraction(3, 2)

    def test_fraction_generators(self, tl_3x5):
        new = tl_3x5.with_generators(('3/2', '7/4'))
        assert new.get_ratio((1, 0)) == Fraction(3, 2)
        assert new.get_ratio((0, 1)) == Fraction(7, 4)

    def test_reference_pitch_carried(self, tl_3x5):
        new = tl_3x5.with_generators((3, 7))
        assert new.reference_pitch == tl_3x5.reference_pitch

    def test_coordinate_groups_carry_over(self, tl_3x5):
        groups = [[(0, 0), (1, 0), (0, 1), (1, 1)], [(-1, -1), (-1, 0), (0, 0), (1, 0)]]
        new = tl_3x5.with_generators((3, 7))
        seq_old = tl_3x5.chord(groups)
        seq_new = new.chord(groups)
        assert len(seq_old.chords) == len(seq_new.chords) == 2

    def test_dimensionality_change_raises(self, tl_3x5):
        # generator 2 equals the equave and is dropped under equave_reduce,
        # leaving a 1D basis on a 2D board
        with pytest.raises(ValueError):
            tl_3x5.with_generators((2, 3))
