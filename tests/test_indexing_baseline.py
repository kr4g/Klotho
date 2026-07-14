"""
Comprehensive baseline tests for PitchCollection indexing behavior.

This suite captures the exact behavior of all pitch collection classes
under the always-rooted (relative/absolute) model.

Mode dimensions:
- is_relative: True (from_degrees) / False (from Pitch objects)
- degree_dtype: Fraction ("ratios") / float ("cents")
- equave_cyclic: True / False (implicit via equave)
- reference_pitch: always present on relative collections (default C4)

Return type rules:
- indexing (single) → Pitch, realized against the reference pitch
- indexing (slice/sequence) → PitchCollectionBase subset carrying the root
- .degrees → raw interval values (Fraction ratios or float cents), never Pitch
- .pitches / .freqs → concrete realization
"""

import pytest
from fractions import Fraction
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from klotho.tonos.pitch import Pitch, PitchCollection, PitchCollectionBase
from klotho.tonos.scales import Scale
from klotho.tonos.chords import Chord, Voicing

C4 = 261.6255653005986


def cents_freq(cents, root=C4):
    return root * 2 ** (cents / 1200)


class TestPitchCollectionRelativeRatiosNotCyclic:
    """PitchCollection: relative mode, ratios, default C4 root, not cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
            mode="ratios"
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

        result = collection[3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 4 / 3)

    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 15 / 8)

        result = collection[-3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 3 / 2)

    def test_degrees_are_raw(self, collection):
        assert collection.degrees == [
            Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3),
            Fraction(3, 2), Fraction(5, 3), Fraction(15, 8)
        ]

    def test_slice(self, collection):
        result = collection[1:4]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result.degrees == [Fraction(9, 8), Fraction(5, 4), Fraction(4, 3)]
        assert result.reference_pitch.pitchclass == "C"

    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    def test_sequence_with_negatives(self, collection):
        result = collection[[0, -1, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result.degrees == [Fraction(1, 1), Fraction(15, 8), Fraction(5, 4)]


class TestPitchCollectionRelativeRatiosCyclic:
    """PitchCollection: relative mode, ratios, cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
            mode="ratios",
            equave="2/1"
        )

    def test_single_positive_index(self, collection):
        assert collection[0].freq == pytest.approx(C4)
        assert collection[3].freq == pytest.approx(C4 * 4 / 3)

    def test_single_negative_index(self, collection):
        assert collection[-1].freq == pytest.approx(C4 * 15 / 16)
        assert collection[-7].freq == pytest.approx(C4 / 2)

    def test_out_of_bounds_positive(self, collection):
        assert collection[7].freq == pytest.approx(C4 * 2)
        assert collection[10].freq == pytest.approx(C4 * 8 / 3)
        assert collection[14].freq == pytest.approx(C4 * 4)

    def test_out_of_bounds_negative(self, collection):
        assert collection[-8].freq == pytest.approx(C4 * 15 / 32)

    def test_sequence_with_out_of_bounds(self, collection):
        result = collection[[0, 7, 14, -7]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(2, 1), Fraction(4, 1), Fraction(1, 2)
        ]


class TestPitchCollectionRelativeRatiosRooted:
    """PitchCollection: relative mode, ratios, explicitly rooted, cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
            mode="ratios",
            equave="2/1",
            reference_pitch="C4"
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

        result = collection[3]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 4 / 3) < 0.001

    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 2) < 0.001

    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert isinstance(result[0], Pitch)
        assert result.reference_pitch.pitchclass == "C"


class TestPitchCollectionRelativeCentsNotCyclic:
    """PitchCollection: relative mode, cents, default root, not cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0],
            mode="cents"
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

        result = collection[3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(cents_freq(500.0))

    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(cents_freq(1100.0))

    def test_degrees_are_raw(self, collection):
        assert collection.degrees == pytest.approx(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0]
        )

    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == pytest.approx([0.0, 400.0, 700.0])


class TestPitchCollectionRelativeCentsCyclic:
    """PitchCollection: relative mode, cents, cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0],
            mode="cents",
            equave=1200.0
        )

    def test_single_positive_index(self, collection):
        assert collection[0].freq == pytest.approx(C4)

    def test_out_of_bounds_positive(self, collection):
        assert collection[7].freq == pytest.approx(cents_freq(1200.0))
        assert collection[10].freq == pytest.approx(cents_freq(1700.0))

    def test_out_of_bounds_negative(self, collection):
        assert collection[-1].freq == pytest.approx(cents_freq(-100.0))
        assert collection[-7].freq == pytest.approx(cents_freq(-1200.0))


class TestPitchCollectionRelativeCentsRooted:
    """PitchCollection: relative mode, cents, explicitly rooted, cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0],
            mode="cents",
            equave=1200.0,
            reference_pitch="C4"
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 2) < 0.001


class TestPitchCollectionAbsoluteNotCyclic:
    """PitchCollection: absolute mode (from Pitch objects), not cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_pitch(
            ["C4", "E4", "G4", "B4"]
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert result.pitchclass == "C"
        assert result.octave == 4

    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, Pitch)
        assert result.pitchclass == "B"
        assert result.octave == 4

    def test_sequence(self, collection):
        result = collection[[0, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 2
        assert result[0].pitchclass == "C"
        assert result[1].pitchclass == "G"

    def test_degrees_are_cents_from_first(self, collection):
        degs = collection.degrees
        assert degs[0] == pytest.approx(0.0)
        assert degs[1] == pytest.approx(400.0)


class TestPitchCollectionAbsoluteCyclic:
    """PitchCollection: absolute mode (from Pitch objects), cyclic"""

    @pytest.fixture
    def collection(self):
        return PitchCollection.from_pitch(
            ["C4", "E4", "G4", "B4"],
            equave="2/1"
        )

    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Pitch)
        assert result.pitchclass == "C"

    def test_out_of_bounds_positive(self, collection):
        result = collection[4]
        assert isinstance(result, Pitch)
        assert result.pitchclass == "C"

        result = collection[5]
        assert isinstance(result, Pitch)
        assert result.pitchclass == "E"


class TestScaleRatiosDefaultRoot:
    """Scale: ratios, default C4 root (always cyclic)"""

    @pytest.fixture
    def scale(self):
        return Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])

    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

        result = scale[3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 4 / 3)

    def test_single_negative_index(self, scale):
        assert scale[-1].freq == pytest.approx(C4 * 15 / 16)

    def test_out_of_bounds_positive(self, scale):
        assert scale[7].freq == pytest.approx(C4 * 2)
        assert scale[14].freq == pytest.approx(C4 * 4)

    def test_out_of_bounds_negative(self, scale):
        assert scale[-7].freq == pytest.approx(C4 / 2)
        assert scale[-14].freq == pytest.approx(C4 / 4)

    def test_sequence(self, scale):
        result = scale[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    def test_sequence_with_out_of_bounds(self, scale):
        result = scale[[0, 7, 14, -7]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(2, 1), Fraction(4, 1), Fraction(1, 2)
        ]


class TestScaleRatiosRooted:
    """Scale: ratios, explicitly rooted (always cyclic)"""

    @pytest.fixture
    def scale(self):
        return Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"]).root("C4")

    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 2) < 0.001

    def test_sequence(self, scale):
        result = scale[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert isinstance(result[0], Pitch)


class TestScaleCentsDefaultRoot:
    """Scale: cents, default C4 root (always cyclic)"""

    @pytest.fixture
    def scale(self):
        return Scale([0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0], interval_type="cents")

    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

    def test_out_of_bounds_positive(self, scale):
        assert scale[7].freq == pytest.approx(cents_freq(1200.0))

    def test_out_of_bounds_negative(self, scale):
        assert scale[-1].freq == pytest.approx(cents_freq(-100.0))


class TestScaleCentsRooted:
    """Scale: cents, explicitly rooted (always cyclic)"""

    @pytest.fixture
    def scale(self):
        return Scale([0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0], interval_type="cents").root("C4")

    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 2) < 0.001


class TestChordRatiosDefaultRoot:
    """Chord: ratios, default C4 root (always cyclic)"""

    @pytest.fixture
    def chord(self):
        return Chord(["1/1", "5/4", "3/2"])

    def test_single_positive_index(self, chord):
        assert chord[0].freq == pytest.approx(C4)
        assert chord[1].freq == pytest.approx(C4 * 5 / 4)

    def test_out_of_bounds_positive(self, chord):
        assert chord[3].freq == pytest.approx(C4 * 2)
        assert chord[4].freq == pytest.approx(C4 * 5 / 2)

    def test_out_of_bounds_negative(self, chord):
        assert chord[-1].freq == pytest.approx(C4 * 3 / 4)
        assert chord[-3].freq == pytest.approx(C4 / 2)


class TestChordRatiosRooted:
    """Chord: ratios, explicitly rooted (always cyclic)"""

    @pytest.fixture
    def chord(self):
        return Chord(["1/1", "5/4", "3/2"]).root("C4")

    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

    def test_out_of_bounds_positive(self, chord):
        result = chord[3]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4 * 2) < 0.001


class TestChordCentsDefaultRoot:
    """Chord: cents, default C4 root (always cyclic)"""

    @pytest.fixture
    def chord(self):
        return Chord([0.0, 400.0, 700.0], interval_type="cents")

    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

    def test_out_of_bounds_positive(self, chord):
        assert chord[3].freq == pytest.approx(cents_freq(1200.0))


class TestChordCentsRooted:
    """Chord: cents, explicitly rooted (always cyclic)"""

    @pytest.fixture
    def chord(self):
        return Chord([0.0, 400.0, 700.0], interval_type="cents").root("C4")

    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001


class TestVoicingRatiosDefaultRoot:
    """Voicing: ratios, default C4 root (never cyclic)"""

    @pytest.fixture
    def sonority(self):
        return Voicing(["1/1", "5/4", "3/2", "2/1"])

    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

        result = sonority[3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 2)

    def test_single_negative_index(self, sonority):
        result = sonority[-1]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4 * 2)

    def test_degrees_are_raw(self, sonority):
        assert sonority.degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2), Fraction(2, 1)
        ]

    def test_sequence(self, sonority):
        result = sonority[[0, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [Fraction(1, 1), Fraction(3, 2)]


class TestVoicingRatiosRooted:
    """Voicing: ratios, explicitly rooted (never cyclic)"""

    @pytest.fixture
    def sonority(self):
        return Voicing(["1/1", "5/4", "3/2", "2/1"]).root("C4")

    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001

    def test_sequence(self, sonority):
        result = sonority[[0, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 2
        assert isinstance(result[0], Pitch)


class TestVoicingCentsDefaultRoot:
    """Voicing: cents, default C4 root (never cyclic)"""

    @pytest.fixture
    def sonority(self):
        return Voicing([0.0, 400.0, 700.0, 1200.0], interval_type="cents")

    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(C4)

        result = sonority[3]
        assert isinstance(result, Pitch)
        assert result.freq == pytest.approx(cents_freq(1200.0))


class TestVoicingCentsRooted:
    """Voicing: cents, explicitly rooted (never cyclic)"""

    @pytest.fixture
    def sonority(self):
        return Voicing([0.0, 400.0, 700.0, 1200.0], interval_type="cents").root("C4")

    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - C4) < 0.001


class TestContour:
    """Test the Contour class"""

    def test_contour_creation(self):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2, 4, 7])
        assert len(c) == 4
        assert c[0] == 0
        assert c[3] == 7

    def test_contour_concat(self):
        from klotho.tonos.pitch import Contour
        c1 = Contour([0, 2, 4])
        c2 = Contour([1, 3, 5])
        result = Contour.concat([c1, c2])
        assert len(result) == 6
        assert result.values == [0, 2, 4, 1, 3, 5]

    def test_contour_concat_multiple(self):
        from klotho.tonos.pitch import Contour
        c1 = Contour([0, 1])
        c2 = Contour([2])
        c3 = Contour([3, 4, 5])
        result = Contour.concat([c1, c2, c3])
        assert len(result) == 6
        assert result.values == [0, 1, 2, 3, 4, 5]

    def test_contour_indexes_into_scale(self):
        from klotho.tonos.pitch import Contour
        scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
        contour = Contour([0, 2, 4])
        result = scale[contour]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    def test_contour_retrograde(self):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2, 4, 7])
        r = c.retrograde()
        assert r.values == [7, 4, 2, 0]

    def test_contour_invert(self):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2, 4])
        i = c.invert(0)
        assert i.values == [0, -2, -4]

    def test_contour_transpose(self):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2, 4])
        t = c + 5
        assert t.values == [5, 7, 9]

    def test_contour_musical_mod(self):
        from klotho.tonos.pitch import Contour
        c = Contour([13, -13, -1, -12, 0])
        result = c % 12
        assert result.values == [1, -1, -1, 0, 0]

    def test_contour_zeroed(self):
        from klotho.tonos.pitch import Contour
        c = Contour([5, 3, 7, 4])
        assert c.zeroed().values == [0, -2, 2, -1]
        assert c.zeroed(1).values == [1, -1, 3, 0]

    def test_contour_normalized(self):
        from klotho.tonos.pitch import Contour
        c = Contour([5, 3, 7, 4])
        assert c.normalized().values == [2, 0, 4, 1]
        assert c.normalized(1).values == [3, 1, 5, 2]


class TestNestedIndexFlattening:
    """Test that nested indices are flattened automatically"""

    @pytest.fixture
    def scale(self):
        return Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])

    @pytest.fixture
    def chord(self):
        return Chord(["1/1", "5/4", "3/2"])

    def test_nested_list_indexes_scale(self, scale):
        result = scale[[[0, 1], [2, 3]]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3)
        ]

    def test_nested_list_indexes_chord(self, chord):
        result = chord[[[0, 1], [2]]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    def test_list_of_contours_indexes_scale(self, scale):
        from klotho.tonos.pitch import Contour
        c1 = Contour([0, 2, 4])
        c2 = Contour([1, 3, 5])
        result = scale[[c1, c2]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2),
            Fraction(9, 8), Fraction(4, 3), Fraction(5, 3)
        ]

    def test_deeply_nested_flattens(self, scale):
        result = scale[[[[0], [1]], [[2, 3]]]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3)
        ]

    def test_mixed_contours_and_lists(self, scale):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2])
        result = scale[[c, [4, 6]]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2), Fraction(15, 8)
        ]

    def test_voicing_nested_indexing(self):
        voicing = Voicing(["1/1", "5/4", "3/2", "2/1"])
        result = voicing[[[0, 1], [2]]]
        assert isinstance(result, PitchCollectionBase)
        assert result.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]


class TestContourImports:
    """Test that Contour can be imported from various paths"""

    def test_contour_from_pitch_module(self):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 1, 2])
        assert len(c) == 3

    def test_contour_from_tonos(self):
        from klotho.tonos import Contour
        c = Contour([0, 1, 2])
        assert len(c) == 3

    def test_contour_from_klotho(self):
        from klotho.tonos import Contour
        c = Contour([0, 1, 2])
        assert len(c) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
