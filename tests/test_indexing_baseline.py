"""
Comprehensive baseline tests for PitchCollection indexing behavior.

This test suite captures the exact behavior of all pitch collection classes
across all mode combinations BEFORE any refactoring changes. It serves as
a verification baseline to ensure behavior is preserved after changes.

Mode dimensions:
- is_relative: True (from_degrees) / False (from Pitch objects)
- is_instanced: True (has reference_pitch) / False (no reference_pitch)
- interval_type: "ratios" (Fraction) / "cents" (float)
- equave_cyclic: True / False (implicit via equave)

Return type rules:
- relative + not instanced + ratios → Fraction
- relative + not instanced + cents → float
- relative + instanced → Pitch
- absolute (not relative) → Pitch
"""

import pytest
from fractions import Fraction
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from klotho.tonos.pitch import Pitch, PitchCollection, PitchCollectionBase
from klotho.tonos.scales import Scale
from klotho.tonos.chords import Chord, Voicing


class TestPitchCollectionRelativeRatiosNotCyclic:
    """PitchCollection: relative mode, ratios, not instanced, not cyclic"""
    
    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
            mode="ratios"
        )
    
    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1)
        
        result = collection[3]
        assert isinstance(result, Fraction)
        assert result == Fraction(4, 3)
    
    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, Fraction)
        assert result == Fraction(15, 8)
        
        result = collection[-3]
        assert isinstance(result, Fraction)
        assert result == Fraction(3, 2)
    
    def test_slice(self, collection):
        result = collection[1:4]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(9, 8)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(4, 3)
    
    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
    
    def test_sequence_with_negatives(self, collection):
        result = collection[[0, -1, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(15, 8)
        assert result[2] == Fraction(5, 4)


class TestPitchCollectionRelativeRatiosCyclic:
    """PitchCollection: relative mode, ratios, not instanced, cyclic"""
    
    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
            mode="ratios",
            equave="2/1"
        )
    
    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1)
        
        result = collection[3]
        assert isinstance(result, Fraction)
        assert result == Fraction(4, 3)
    
    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, Fraction)
        assert result == Fraction(15, 8) * Fraction(1, 2)
        
        result = collection[-7]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1) * Fraction(1, 2)
    
    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1) * Fraction(2, 1)
        
        result = collection[10]
        assert isinstance(result, Fraction)
        assert result == Fraction(4, 3) * Fraction(2, 1)
        
        result = collection[14]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1) * Fraction(4, 1)
    
    def test_out_of_bounds_negative(self, collection):
        result = collection[-8]
        assert isinstance(result, Fraction)
        assert result == Fraction(15, 8) * Fraction(1, 4)
    
    def test_sequence_with_out_of_bounds(self, collection):
        result = collection[[0, 7, 14, -7]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 4
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(1, 1) * Fraction(2, 1)
        assert result[2] == Fraction(1, 1) * Fraction(4, 1)
        assert result[3] == Fraction(1, 1) * Fraction(1, 2)


class TestPitchCollectionRelativeRatiosInstanced:
    """PitchCollection: relative mode, ratios, instanced, cyclic"""
    
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
        assert abs(result.freq - 261.6255653005986) < 0.001
        
        result = collection[3]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * (4/3)
        assert abs(result.freq - expected_freq) < 0.001
    
    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * 2
        assert abs(result.freq - expected_freq) < 0.001
    
    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert isinstance(result[0], Pitch)


class TestPitchCollectionRelativeCentsNotCyclic:
    """PitchCollection: relative mode, cents, not instanced, not cyclic"""
    
    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0],
            mode="cents"
        )
    
    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, float)
        assert abs(result - 0.0) < 0.000001
        
        result = collection[3]
        assert isinstance(result, float)
        assert abs(result - 500.0) < 0.000001
    
    def test_single_negative_index(self, collection):
        result = collection[-1]
        assert isinstance(result, float)
        assert abs(result - 1100.0) < 0.000001
    
    def test_sequence(self, collection):
        result = collection[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert abs(result[0] - 0.0) < 0.000001
        assert abs(result[1] - 400.0) < 0.000001
        assert abs(result[2] - 700.0) < 0.000001


class TestPitchCollectionRelativeCentsCyclic:
    """PitchCollection: relative mode, cents, not instanced, cyclic"""
    
    @pytest.fixture
    def collection(self):
        return PitchCollection.from_degrees(
            [0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0],
            mode="cents",
            equave=1200.0
        )
    
    def test_single_positive_index(self, collection):
        result = collection[0]
        assert isinstance(result, float)
        assert abs(result - 0.0) < 0.000001
    
    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, float)
        assert abs(result - 1200.0) < 0.000001
        
        result = collection[10]
        assert isinstance(result, float)
        assert abs(result - 1700.0) < 0.000001
    
    def test_out_of_bounds_negative(self, collection):
        result = collection[-1]
        assert isinstance(result, float)
        assert abs(result - (1100.0 - 1200.0)) < 0.000001
        
        result = collection[-7]
        assert isinstance(result, float)
        assert abs(result - (0.0 - 1200.0)) < 0.000001


class TestPitchCollectionRelativeCentsInstanced:
    """PitchCollection: relative mode, cents, instanced, cyclic"""
    
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
        assert abs(result.freq - 261.6255653005986) < 0.001
    
    def test_out_of_bounds_positive(self, collection):
        result = collection[7]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * 2
        assert abs(result.freq - expected_freq) < 0.001


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


class TestScaleRatiosNotInstanced:
    """Scale: ratios, not instanced (always cyclic)"""
    
    @pytest.fixture
    def scale(self):
        return Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
    
    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1)
        
        result = scale[3]
        assert isinstance(result, Fraction)
        assert result == Fraction(4, 3)
    
    def test_single_negative_index(self, scale):
        result = scale[-1]
        assert isinstance(result, Fraction)
        assert result == Fraction(15, 8) * Fraction(1, 2)
    
    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, Fraction)
        assert result == Fraction(2, 1)
        
        result = scale[14]
        assert isinstance(result, Fraction)
        assert result == Fraction(4, 1)
    
    def test_out_of_bounds_negative(self, scale):
        result = scale[-7]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 2)
        
        result = scale[-14]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 4)
    
    def test_sequence(self, scale):
        result = scale[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
    
    def test_sequence_with_out_of_bounds(self, scale):
        result = scale[[0, 7, 14, -7]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 4
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(2, 1)
        assert result[2] == Fraction(4, 1)
        assert result[3] == Fraction(1, 2)


class TestScaleRatiosInstanced:
    """Scale: ratios, instanced (always cyclic)"""
    
    @pytest.fixture
    def scale(self):
        return Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"]).root("C4")
    
    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001
    
    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * 2
        assert abs(result.freq - expected_freq) < 0.001
    
    def test_sequence(self, scale):
        result = scale[[0, 2, 4]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert isinstance(result[0], Pitch)


class TestScaleCentsNotInstanced:
    """Scale: cents, not instanced (always cyclic)"""
    
    @pytest.fixture
    def scale(self):
        return Scale([0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0], interval_type="cents")
    
    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, float)
        assert abs(result - 0.0) < 0.000001
    
    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, float)
        assert abs(result - 1200.0) < 0.000001
    
    def test_out_of_bounds_negative(self, scale):
        result = scale[-1]
        assert isinstance(result, float)
        assert abs(result - (1100.0 - 1200.0)) < 0.000001


class TestScaleCentsInstanced:
    """Scale: cents, instanced (always cyclic)"""
    
    @pytest.fixture
    def scale(self):
        return Scale([0.0, 200.0, 400.0, 500.0, 700.0, 900.0, 1100.0], interval_type="cents").root("C4")
    
    def test_single_positive_index(self, scale):
        result = scale[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001
    
    def test_out_of_bounds_positive(self, scale):
        result = scale[7]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * 2
        assert abs(result.freq - expected_freq) < 0.001


class TestChordRatiosNotInstanced:
    """Chord: ratios, not instanced (always cyclic)"""
    
    @pytest.fixture
    def chord(self):
        return Chord(["1/1", "5/4", "3/2"])
    
    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1)
        
        result = chord[1]
        assert isinstance(result, Fraction)
        assert result == Fraction(5, 4)
    
    def test_out_of_bounds_positive(self, chord):
        result = chord[3]
        assert isinstance(result, Fraction)
        assert result == Fraction(2, 1)
        
        result = chord[4]
        assert isinstance(result, Fraction)
        assert result == Fraction(5, 2)
    
    def test_out_of_bounds_negative(self, chord):
        result = chord[-1]
        assert isinstance(result, Fraction)
        assert result == Fraction(3, 4)
        
        result = chord[-3]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 2)


class TestChordRatiosInstanced:
    """Chord: ratios, instanced (always cyclic)"""
    
    @pytest.fixture
    def chord(self):
        return Chord(["1/1", "5/4", "3/2"]).root("C4")
    
    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001
    
    def test_out_of_bounds_positive(self, chord):
        result = chord[3]
        assert isinstance(result, Pitch)
        expected_freq = 261.6255653005986 * 2
        assert abs(result.freq - expected_freq) < 0.001


class TestChordCentsNotInstanced:
    """Chord: cents, not instanced (always cyclic)"""
    
    @pytest.fixture
    def chord(self):
        return Chord([0.0, 400.0, 700.0], interval_type="cents")
    
    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, float)
        assert abs(result - 0.0) < 0.000001
    
    def test_out_of_bounds_positive(self, chord):
        result = chord[3]
        assert isinstance(result, float)
        assert abs(result - 1200.0) < 0.000001


class TestChordCentsInstanced:
    """Chord: cents, instanced (always cyclic)"""
    
    @pytest.fixture
    def chord(self):
        return Chord([0.0, 400.0, 700.0], interval_type="cents").root("C4")
    
    def test_single_positive_index(self, chord):
        result = chord[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001


class TestVoicingRatiosNotInstanced:
    """Voicing: ratios, not instanced (never cyclic)"""
    
    @pytest.fixture
    def sonority(self):
        return Voicing(["1/1", "5/4", "3/2", "2/1"])
    
    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Fraction)
        assert result == Fraction(1, 1)
        
        result = sonority[3]
        assert isinstance(result, Fraction)
        assert result == Fraction(2, 1)
    
    def test_single_negative_index(self, sonority):
        result = sonority[-1]
        assert isinstance(result, Fraction)
        assert result == Fraction(2, 1)
    
    def test_sequence(self, sonority):
        result = sonority[[0, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 2
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(3, 2)


class TestVoicingRatiosInstanced:
    """Voicing: ratios, instanced (never cyclic)"""
    
    @pytest.fixture
    def sonority(self):
        return Voicing(["1/1", "5/4", "3/2", "2/1"]).root("C4")
    
    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001
    
    def test_sequence(self, sonority):
        result = sonority[[0, 2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 2
        assert isinstance(result[0], Pitch)


class TestVoicingCentsNotInstanced:
    """Voicing: cents, not instanced (never cyclic)"""
    
    @pytest.fixture
    def sonority(self):
        return Voicing([0.0, 400.0, 700.0, 1200.0], interval_type="cents")
    
    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, float)
        assert abs(result - 0.0) < 0.000001
        
        result = sonority[3]
        assert isinstance(result, float)
        assert abs(result - 1200.0) < 0.000001


class TestVoicingCentsInstanced:
    """Voicing: cents, instanced (never cyclic)"""
    
    @pytest.fixture
    def sonority(self):
        return Voicing([0.0, 400.0, 700.0, 1200.0], interval_type="cents").root("C4")
    
    def test_single_positive_index(self, sonority):
        result = sonority[0]
        assert isinstance(result, Pitch)
        assert abs(result.freq - 261.6255653005986) < 0.001


class TestContour:
    """Test the new Contour class"""
    
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
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
    
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
        assert len(result) == 4
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(9, 8)
        assert result[2] == Fraction(5, 4)
        assert result[3] == Fraction(4, 3)
    
    def test_nested_list_indexes_chord(self, chord):
        result = chord[[[0, 1], [2]]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
    
    def test_list_of_contours_indexes_scale(self, scale):
        from klotho.tonos.pitch import Contour
        c1 = Contour([0, 2, 4])
        c2 = Contour([1, 3, 5])
        result = scale[[c1, c2]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 6
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
        assert result[3] == Fraction(9, 8)
        assert result[4] == Fraction(4, 3)
        assert result[5] == Fraction(5, 3)
    
    def test_deeply_nested_flattens(self, scale):
        result = scale[[[[0], [1]], [[2, 3]]]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 4
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(9, 8)
        assert result[2] == Fraction(5, 4)
        assert result[3] == Fraction(4, 3)
    
    def test_mixed_contours_and_lists(self, scale):
        from klotho.tonos.pitch import Contour
        c = Contour([0, 2])
        result = scale[[c, [4, 6]]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 4
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)
        assert result[3] == Fraction(15, 8)
    
    def test_voicing_nested_indexing(self):
        voicing = Voicing(["1/1", "5/4", "3/2", "2/1"])
        result = voicing[[[0, 1], [2]]]
        assert isinstance(result, PitchCollectionBase)
        assert len(result) == 3
        assert result[0] == Fraction(1, 1)
        assert result[1] == Fraction(5, 4)
        assert result[2] == Fraction(3, 2)


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
        from klotho import Contour
        c = Contour([0, 1, 2])
        assert len(c) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
