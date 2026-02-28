import pytest
import numpy as np
from fractions import Fraction
from klotho.tonos.pitch import Pitch, PitchCollection, PitchCollectionBase, RootedPitchCollection
from klotho.tonos.scales import Scale
from klotho.tonos.chords import Chord, Voicing, Sonority


class TestPitch:
    """Test the Pitch class functionality"""
    
    def test_pitch_default_construction(self):
        """Test pitch creation with default values"""
        p = Pitch()
        assert p.pitchclass == 'A'
        assert p.octave == 4
        assert p.cents_offset == 0.0
        assert p.partial == 1
        assert abs(p.freq - 440.0) < 1e-6
    
    def test_pitch_string_construction(self):
        """Test pitch creation from string notation"""
        p1 = Pitch("C4")
        assert p1.pitchclass == "C"
        assert p1.octave == 4
        assert abs(p1.freq - 261.6256) < 1e-4
        
        p2 = Pitch("F#5")
        assert p2.pitchclass == "F#"
        assert p2.octave == 5
        
        p3 = Pitch("Bb3")
        assert p3.pitchclass == "Bb"
        assert p3.octave == 3
        
        p4 = Pitch("C-1")
        assert p4.pitchclass == "C"
        assert p4.octave == -1
    
    def test_pitch_from_freq(self):
        """Test pitch creation from frequency"""
        p1 = Pitch.from_freq(440.0)
        assert p1.pitchclass == "A"
        assert p1.octave == 4
        assert abs(p1.cents_offset) < 1e-6
        
        p2 = Pitch.from_freq(261.6256)
        assert p2.pitchclass == "C"
        assert p2.octave == 4
    
    def test_pitch_comparison(self):
        """Test pitch comparison operators"""
        p1 = Pitch("C4")
        p2 = Pitch("C4")
        p3 = Pitch("D4")
        p4 = Pitch("C5")
        
        assert p1 == p2
        assert p1 != p3
        
        assert p1 < p3
        assert p1 < p4
        assert p3 > p1
        assert p1 <= p2
        assert p1 >= p2


class TestPitchCollection:
    """Test the PitchCollection class with new unified architecture"""
    
    def test_pitch_collection_absolute_mode(self):
        """Test construction with pitch objects (absolute mode)"""
        pc = PitchCollection.from_pitch(["C4", "E4", "G4"])
        assert len(pc) == 3
        assert pc.is_relative == False
        assert pc[0].pitchclass == "C"
        assert pc[1].pitchclass == "E"
        assert pc[2].pitchclass == "G"
    
    def test_pitch_collection_from_degrees(self):
        """Test construction with degrees (relative mode)"""
        pc = PitchCollection.from_degrees(["1/1", "5/4", "3/2"])
        assert len(pc) == 3
        assert pc.is_relative == True
        assert pc[0] == Fraction(1, 1)
        assert pc[1] == Fraction(5, 4)
        assert pc[2] == Fraction(3, 2)
        assert pc.interval_type == Fraction
    
    def test_pitch_collection_from_degrees_cents(self):
        """Test construction with cents degrees"""
        pc = PitchCollection.from_degrees([0.0, 386.3, 702.0], mode="cents")
        assert pc.interval_type == float
        assert len(pc) == 3
        assert pc[0] == 0.0
        assert abs(pc[1] - 386.3) < 1e-6
        assert abs(pc[2] - 702.0) < 1e-6
        assert pc.equave == 1200.0
    
    def test_pitch_collection_intervals(self):
        """Test interval calculation between degrees"""
        pc1 = PitchCollection.from_degrees(["1/1", "5/4", "3/2"])
        intervals = pc1.intervals
        assert len(intervals) == 2
        assert intervals[0] == Fraction(5, 4)
        assert intervals[1] == Fraction(6, 5)
        
        pc2 = PitchCollection.from_degrees([0.0, 386.3, 702.0], mode="cents")
        intervals2 = pc2.intervals
        assert len(intervals2) == 2
        assert abs(intervals2[0] - 386.3) < 1e-6
        assert abs(intervals2[1] - 315.7) < 1e-6
    
    def test_pitch_collection_indexing(self):
        """Test various indexing methods"""
        pc = PitchCollection.from_degrees(["1/1", "5/4", "3/2", "2/1"])
        
        assert pc[0] == Fraction(1, 1)
        assert pc[1] == Fraction(5, 4)
        assert pc[-1] == Fraction(2, 1)
        
        subset = pc[1:3]
        assert isinstance(subset, PitchCollectionBase)
        assert len(subset) == 2
        assert subset[0] == Fraction(5, 4)
        
        selected = pc[[0, 2]]
        assert isinstance(selected, PitchCollectionBase)
        assert len(selected) == 2
        assert selected[0] == Fraction(1, 1)
        assert selected[1] == Fraction(3, 2)
    
    def test_pitch_collection_root_addressing(self):
        """Test creating instanced pitch collections"""
        pc = PitchCollection.from_degrees(["1/1", "5/4", "3/2"])
        
        instanced = pc.root("C4")
        assert isinstance(instanced, RootedPitchCollection)
        assert instanced.is_instanced == True
        assert instanced.reference_pitch.pitchclass == "C"
        assert instanced.reference_pitch.octave == 4
        
        p0 = instanced[0]
        assert isinstance(p0, Pitch)
        assert p0.pitchclass == "C"
        assert p0.octave == 4
        
        p1 = instanced[1]
        assert isinstance(p1, Pitch)
        
        subset = instanced[[0, 2]]
        assert isinstance(subset, RootedPitchCollection)
        assert subset.is_instanced == True
    
    def test_pitch_collection_from_setclass(self):
        """Test construction from setclass"""
        pc = PitchCollection.from_setclass([0, 4, 7], mod=12)
        assert pc.is_relative == True
        assert pc.equave == 1200.0
        assert pc[0] == 0.0
        assert pc[1] == 400.0
        assert pc[2] == 700.0
    
    def test_pitch_collection_from_intervals(self):
        """Test construction from intervals"""
        pc = PitchCollection.from_intervals(["9/8", "10/9", "16/15"])
        assert len(pc) == 4
        assert pc[0] == Fraction(1, 1)
        assert pc[1] == Fraction(9, 8)
        assert pc[2] == Fraction(5, 4)
        assert pc[3] == Fraction(4, 3)
    
    def test_pitch_collection_from_freqs(self):
        """Test construction from frequencies"""
        pc = PitchCollection.from_freq([261.63, 329.63, 392.0])
        assert len(pc) == 3
        assert pc.is_relative == False
        assert isinstance(pc[0], Pitch)

    def test_pitch_collection_float_ratios(self):
        pc = PitchCollection.from_degrees([1.0, 1.25, 1.5], mode="ratios")
        assert isinstance(pc.degrees[0], float)
        assert pc.interval_type == float


class TestPitchCollectionEquaveCyclic:
    """Test equave-cyclic behavior"""
    
    def test_equave_cyclic_indexing(self):
        """Test cyclic indexing when equave is specified"""
        pc = PitchCollection.from_degrees(["1/1", "5/4", "3/2"], equave="2/1")
        
        assert pc[0] == Fraction(1, 1)
        assert pc[1] == Fraction(5, 4)
        assert pc[2] == Fraction(3, 2)
        
        assert pc[3] == Fraction(2, 1)
        assert pc[4] == Fraction(5, 2)
        
        assert pc[-1] == Fraction(3, 4)
    
    def test_equave_cyclic_cents(self):
        """Test cyclic indexing with cents"""
        pc = PitchCollection.from_degrees([0.0, 400.0, 700.0], mode="cents", equave=1200.0)
        
        assert pc[3] == 1200.0
        assert pc[4] == 1600.0
        assert pc[-1] == -500.0


class TestScale:
    """Test the Scale class"""
    
    def test_scale_defaults(self):
        """Test default scale construction"""
        scale = Scale()
        assert len(scale) == 7
        assert scale[0] == Fraction(1, 1)
        assert scale.equave_cyclic == True
    
    def test_scale_custom_construction(self):
        """Test scale with custom degrees"""
        scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2"])
        assert len(scale) == 5
        assert scale[0] == Fraction(1, 1)
        assert scale[4] == Fraction(3, 2)
    
    def test_scale_unison_insertion(self):
        """Test that unison is automatically inserted"""
        scale = Scale(["9/8", "5/4", "4/3"])
        assert scale[0] == Fraction(1, 1)
        assert len(scale) == 4
    
    def test_scale_equave_removal(self):
        """Test that equave is removed from degrees"""
        scale = Scale(["1/1", "9/8", "5/4", "2/1"])
        degrees = list(scale._degrees)
        assert Fraction(2, 1) not in degrees
    
    def test_scale_basic_indexing(self):
        """Test scale indexing (equave-cyclic)"""
        scale = Scale(["1/1", "9/8", "5/4"])
        
        assert scale[0] == Fraction(1, 1)
        assert scale[1] == Fraction(9, 8)
        assert scale[2] == Fraction(5, 4)
        
        assert scale[3] == Fraction(2, 1)
        assert scale[4] == Fraction(9, 4)
        
        assert scale[-1] == Fraction(5, 8)
    
    def test_scale_mode_generation(self):
        """Test mode generation"""
        scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2"])
        
        mode0 = scale.mode(0)
        assert mode0[0] == Fraction(1, 1)
        
        mode1 = scale.mode(1)
        assert mode1[0] == Fraction(1, 1)
        assert isinstance(mode1, Scale)
    
    def test_scale_instanced_creation(self):
        """Test instanced scale creation"""
        scale = Scale(["1/1", "9/8", "5/4"])
        
        c_scale = scale.root("C4")
        assert isinstance(c_scale, Scale)
        assert c_scale.is_instanced == True
        
        p0 = c_scale[0]
        assert isinstance(p0, Pitch)
        assert p0.pitchclass == "C"
        assert p0.octave == 4
    
    def test_scale_relative_property(self):
        """Test .relative property"""
        scale = Scale(["1/1", "9/8", "5/4"])
        c_scale = scale.root("C4")
        
        relative = c_scale.relative()
        assert isinstance(relative, Scale)
        assert relative.is_instanced == False
        assert relative[0] == Fraction(1, 1)


class TestChord:
    """Test the Chord class"""
    
    def test_chord_defaults(self):
        """Test default chord construction"""
        chord = Chord()
        assert len(chord) == 3
        assert chord[0] == Fraction(1, 1)
        assert chord.equave_cyclic == True
    
    def test_chord_custom_construction(self):
        """Test chord with custom degrees"""
        chord = Chord(["1/1", "5/4", "3/2"])
        assert len(chord) == 3
        assert chord[0] == Fraction(1, 1)
        assert chord[1] == Fraction(5, 4)
        assert chord[2] == Fraction(3, 2)
    
    def test_chord_equave_behavior(self):
        """Test chord equave-cyclic indexing"""
        chord = Chord(["1/1", "5/4", "3/2"])
        
        assert chord[3] == Fraction(2, 1)
        assert chord[4] == Fraction(5, 2)
    
    def test_chord_basic_indexing(self):
        """Test chord basic indexing"""
        chord = Chord(["1/1", "5/4", "3/2"])
        
        assert chord[0] == Fraction(1, 1)
        assert chord[1] == Fraction(5, 4)
        assert chord[2] == Fraction(3, 2)
    
    def test_chord_inversion_operations(self):
        """Test chord inversion"""
        chord = Chord(["1/1", "5/4", "3/2"])
        inverted = ~chord
        assert isinstance(inverted, Chord)
    
    def test_chord_instanced_creation(self):
        """Test instanced chord creation"""
        chord = Chord(["1/1", "5/4", "3/2"])
        
        c_chord = chord.root("C4")
        assert isinstance(c_chord, Chord)
        assert c_chord.is_instanced == True
        
        p0 = c_chord[0]
        assert isinstance(p0, Pitch)
        assert p0.pitchclass == "C"
    
    def test_chord_voicing(self):
        """Test chord voicing method"""
        chord = Chord(["1/1", "5/4", "3/2"])
        from klotho.tonos.chords import Voicing
        
        voicing = chord.voicing([0, 1, 2, 3])
        assert isinstance(voicing, Voicing)

    def test_chord_from_collection_rejects_absolute(self):
        pc = PitchCollection.from_pitch(["C4", "E4", "G4"])
        with pytest.raises(ValueError):
            Chord.from_collection(pc)

    def test_chord_from_collection_equave_override(self):
        pc = PitchCollection.from_degrees(["1/1", "5/4", "3/2"], mode="ratios", equave="3/1")
        chord = Chord.from_collection(pc, equave="2/1")
        assert chord.equave == Fraction(2, 1)


class TestBasicIntegration:
    """Test integration between different classes"""
    
    def test_pitch_collection_set_operations_fractions(self):
        """Test set operations with fractions"""
        pc1 = PitchCollection.from_degrees(["1/1", "5/4", "3/2"])
        pc2 = PitchCollection.from_degrees(["1/1", "6/5", "3/2"])
        
        assert pc1[0] == pc2[0]
        assert pc1[2] == pc2[2]
    
    def test_real_world_musical_scenarios(self):
        """Test realistic musical operations"""
        scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
        
        c_scale = scale.root("C4")
        assert c_scale.is_instanced == True
        
        c4 = c_scale[0]
        assert isinstance(c4, Pitch)
        assert c4.pitchclass == "C"
        assert c4.octave == 4
        
        mode2 = scale.mode(2)
        assert isinstance(mode2, Scale)
    
    def test_type_preservation(self):
        """Test that .root() preserves type"""
        scale = Scale(["1/1", "9/8", "5/4"])
        chord = Chord(["1/1", "5/4", "3/2"])
        
        c_scale = scale.root("C4")
        c_chord = chord.root("C4")
        
        assert type(c_scale).__name__ == "Scale"
        assert type(c_chord).__name__ == "Chord"

    def test_sonority_from_collection_rejects_absolute(self):
        pc = PitchCollection.from_pitch(["C4", "E4", "G4"])
        with pytest.raises(ValueError):
            Voicing.from_collection(pc)

    def test_absolute_sonority_wraps_absolute_collection(self):
        pc = PitchCollection.from_pitch(["C4", "E4", "G4"])
        sonority = Sonority(pc.pitches)
        assert len(sonority) == 3


class TestCentsAndMixedOperations:
    """Test cents mode and mixed operations"""
    
    def test_cents_scales_now_work(self):
        """Test that cents-based scales work"""
        scale = Scale([0.0, 200.0, 400.0, 500.0, 700.0], interval_type="cents")
        assert len(scale) == 5
        assert scale[0] == 0.0
        assert scale.equave == 1200.0
    
    def test_cents_chords_now_work(self):
        """Test that cents-based chords work"""
        chord = Chord([0.0, 400.0, 700.0], interval_type="cents")
        assert len(chord) == 3
        assert chord[0] == 0.0
    
    def test_mixed_type_operations_work(self):
        """Test mixed type operations"""
        pc_ratio = PitchCollection.from_degrees(["1/1", "5/4", "3/2"])
        pc_cents = PitchCollection.from_degrees([0.0, 386.3, 702.0], mode="cents")
        
        assert len(pc_ratio) == len(pc_cents)
        
        c_ratio = pc_ratio.root("C4")
        c_cents = pc_cents.root("C4")
        
        assert c_ratio.is_instanced == True
        assert c_cents.is_instanced == True
    
    def test_from_intervals_with_interval_type(self):
        """Test from_intervals with different interval types"""
        pc_ratio = PitchCollection.from_intervals(["9/8", "10/9"])
        assert pc_ratio[0] == Fraction(1, 1)
        
        pc_cents = PitchCollection.from_intervals([200.0, 200.0], mode="cents")
        assert pc_cents[0] == 0.0
        assert abs(pc_cents[1] - 200.0) < 1e-6
        assert abs(pc_cents[2] - 400.0) < 1e-6
