"""Otonal chord-root analysis (klotho.tonos.chords.analysis)."""
from fractions import Fraction

import pytest

from klotho.tonos import root_index, chord_root


class TestRootIndex:

    @pytest.mark.parametrize("degrees,expected_root", [
        (['1', '5/4', '3/2'], '1'),            # major, root position
        (['1', '6/5', '8/5'], '8/5'),          # major, 1st inversion
        (['1', '4/3', '5/3'], '4/3'),          # major, 2nd inversion
        (['1', '5/4', '3/2', '7/4'], '1'),     # harmonic seventh
        (['1', '8/7', '10/7', '12/7'], '8/7'), # dom7 voiced over its 7th
        (['1', '3/2', '9/8', '27/16'], '1'),   # stack of fifths
    ])
    def test_otonal_roots(self, degrees, expected_root):
        assert chord_root(degrees) == Fraction(expected_root)

    def test_octave_displacement_ignored(self):
        # same chord, degrees spread across equaves: root unchanged
        assert chord_root(['1', '5/2', '3']) == 1
        assert chord_root(['2', '5/4', '3/2']) == 2

    def test_returns_index_into_input(self):
        degrees = ['1', '6/5', '8/5']
        assert root_index(degrees) == 2

    def test_utonal_pick_is_deterministic(self):
        # minor triads are utonal; the metric picks a stable representative
        assert chord_root(['1', '6/5', '3/2']) == chord_root(['1', '6/5', '3/2'])

    def test_equave_parameter(self):
        # Bohlen-Pierce-style tritave chord: factors of 3 stripped
        assert chord_root(['1', '5/3', '7/3'], equave=3) == 1

    def test_floats_rejected(self):
        with pytest.raises(TypeError):
            root_index([1.0, 1.25, 1.5])

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            root_index([])
