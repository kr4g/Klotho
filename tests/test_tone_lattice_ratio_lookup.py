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


class TestNoEquaveReduceClassFallback:
    """Without equave reduction, exact representations win and
    equave-shifted queries fall back to class matching.

    Regression: chords built from lattice cells carry equave-displaced
    degrees (``Chord`` normalizes ``4/5`` to ``8/5``; voice-leading
    displaces further), and those degrees must still resolve to their
    cells on a non-reduced lattice.
    """

    @pytest.fixture
    def tl_plain(self):
        return ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=False)

    def test_16_15_resolves_by_class(self, tl_plain):
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            coord = tl_plain.get_coordinates_for_ratio("16/15")
        assert coord == (-1, -1)
        # the cell keeps its own representative: 1/15 == 16/15 / 2**4
        assert tl_plain.get_ratio(coord) == Fraction(1, 15)

    def test_exact_ratio_resolves(self, tl_plain):
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl_plain.get_coordinates_for_ratio("15/1") == (1, 1)
            assert tl_plain.get_coordinates_for_ratio("3/5") == (1, -1)

    def test_exact_match_beats_class_mate(self, tl_plain):
        # 3/1 is literally a cell; 3/2 is not, and resolves to 3/1's cell.
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl_plain.get_coordinates_for_ratio("3/1") == (1, 0)
            assert tl_plain.get_coordinates_for_ratio("3/2") == (1, 0)

    def test_foreign_primes_still_unresolved(self, tl_plain):
        with pytest.warns(ToneLatticeLookupWarning):
            assert tl_plain.get_coordinates_for_ratio("7/4") is None


class TestUnreducedChordShapeResolution:
    """Notebook regression: unreduced (6/5, 5/4) lattice; raw and
    voice-led ChordSequence degrees resolve through the plot shape path."""

    @pytest.fixture
    def tl_65_54(self):
        return ToneLattice.from_generators(('6/5', '5/4'), resolution=3,
                                           equave_reduce=False)

    def test_octave_shift_of_cell(self, tl_65_54):
        with warnings.catch_warnings():
            warnings.simplefilter("error", ToneLatticeLookupWarning)
            assert tl_65_54.get_coordinates_for_ratio("8/5") == (0, -1)
            assert tl_65_54.get_coordinates_for_ratio("4/5") == (0, -1)
            assert tl_65_54.get_coordinates_for_ratio("3/2") == (1, 1)

    def test_chord_shape_resolution_raw_and_voiced(self, tl_65_54):
        from klotho.semeios.visualization._dispatch.plot_lattice import (
            _resolve_chord_shape,
        )
        placements = [[(0, 0), (0, 1), (1, 0), (1, 1)],
                      [(0, -1), (1, -1), (1, 0), (2, 0)]]
        seq = tl_65_54.chord(placements)
        for s in (seq, seq.voice_led('C3', 'C5')):
            groups, freqs = _resolve_chord_shape(tl_65_54, s)
            assert len(groups) == len(placements)
            assert len(freqs) == len(placements)
            for ch, grp in zip(list(s), groups):
                for degree, node in zip(ch.degrees, grp):
                    represented = tl_65_54._coord_to_ratio(tuple(node))
                    assert (tl_65_54._canonical_class(represented)
                            == tl_65_54._canonical_class(Fraction(degree)))


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
