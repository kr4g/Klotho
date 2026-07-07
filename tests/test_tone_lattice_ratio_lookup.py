"""Regression: equave-aware ratio lookup in ToneLattice.

With ``equave_reduce=True``, ``get_coordinates_for_ratio`` must resolve
ratios by equave-equivalence class: ``16/15`` and ``8/15`` are the same
pitch class under a 2/1 equave, so both must find the coordinate whose
represented ratio is ``8/15``. Two mechanisms are covered:

- the direct linear solve (augmented with an equave column so queries
  containing equave primes don't fail with "primes not in prime_basis")
- the exhaustive match index (keyed by canonical class representative,
  since the bipolar reduction window spans two equaves and is therefore
  not canonical)
"""
import warnings
from fractions import Fraction

import pytest

from klotho.tonos import ToneLattice
from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLatticeLookupWarning


@pytest.fixture
def tl_3x5():
    return ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=True)


class TestEquaveClassLookup:
    """Bipolar 3x5 lattice: ratios containing powers of 2 must resolve."""

    @pytest.mark.parametrize("ratio,expected", [
        ("16/15", (-1, -1)),
        ("8/15", (-1, -1)),
        ("8/5", (0, -1)),
        ("4/5", (0, -1)),
        ("3/2", (1, 0)),
        ("9/8", (2, 0)),
        ("1/1", (0, 0)),
        ("15/8", (1, 1)),
        ("5/4", (0, 1)),
    ])
    def test_resolves_without_warning(self, tl_3x5, ratio, expected):
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl_3x5.get_coordinates_for_ratio(ratio) == expected

    def test_lookup_all_mode(self, tl_3x5):
        result = tl_3x5.get_coordinates_for_ratio("16/15", lookup="all")
        assert result is not None
        assert (-1, -1) in result

    def test_lookup_unique_mode(self, tl_3x5):
        assert tl_3x5.get_coordinates_for_ratio("16/15", lookup="unique") == (-1, -1)

    def test_out_of_bounds_still_warns(self, tl_3x5):
        # 3^5 requires coordinate (5, 0), outside resolution=2.
        with pytest.warns(ToneLatticeLookupWarning):
            assert tl_3x5.get_coordinates_for_ratio(Fraction(243, 128)) is None

    def test_returned_coord_ratio_is_same_class(self, tl_3x5):
        coord = tl_3x5.get_coordinates_for_ratio("16/15")
        represented = tl_3x5.get_ratio(coord)
        # Same equave class: ratio quotient is a power of 2.
        q = Fraction("16/15") / represented
        while q > 1:
            q /= 2
        while q < 1:
            q *= 2
        assert q == 1


class TestNoEquaveReduceUnchanged:
    """Without equave reduction, matching stays exact."""

    def test_16_15_unresolved(self):
        tl = ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=False)
        with pytest.warns(ToneLatticeLookupWarning):
            assert tl.get_coordinates_for_ratio("16/15") is None

    def test_exact_ratio_resolves(self):
        tl = ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=False)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl.get_coordinates_for_ratio("15/1") == (1, 1)
            assert tl.get_coordinates_for_ratio("3/5") == (1, -1)


class TestUnipolar:
    def test_unipolar_class_lookup(self):
        tl = ToneLattice.from_generators((3, 5), resolution=2,
                                         equave_reduce=True, bipolar=False)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            # Unipolar lattice only has non-negative coordinates; 3/2 is at (1, 0).
            assert tl.get_coordinates_for_ratio("3/2") == (1, 0)
            # 6/4 == 3/2 (same value), 3/1 differs by an equave.
            assert tl.get_coordinates_for_ratio("3/1") == (1, 0)


class TestCustomEquave:
    def test_tritave_equave(self):
        tl = ToneLattice.from_generators((2, 5), resolution=2,
                                         equave_reduce=True, equave=3)
        assert tl.equave == Fraction(3)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl.get_coordinates_for_ratio("2/1") == (1, 0)
            # 6/5 = (2/1) * (1/5) * 3 -> coordinate (1, -1) modulo the tritave
            assert tl.get_coordinates_for_ratio("6/5") == (1, -1)

    def test_equave_representable_in_generators_falls_back(self):
        # Generators (3, '4/3') can represent 4 = 2^2, so the augmented
        # system with a 2/1 equave column is rank-deficient. The direct
        # solve must fail gracefully and the index lookup still works.
        tl = ToneLattice.from_generators((3, "4/3"), resolution=2,
                                         equave_reduce=True)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            coord = tl.get_coordinates_for_ratio("4/3")
            assert coord is not None
            assert tl._canonical_class(tl.get_ratio(coord)) == tl._canonical_class(Fraction(4, 3))


class TestEquaveProperty:
    def test_equave_property(self):
        tl = ToneLattice(2)
        assert tl.equave == Fraction(2)
        tl3 = ToneLattice.from_generators((2, 5), equave=3, resolution=1)
        assert tl3.equave == Fraction(3)
