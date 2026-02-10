from fractions import Fraction
from typing import Optional, Union, List, Sequence
from ..pitch import Pitch
from ..pitch.pitch_collections import (
    AbsolutePitchCollection,
    EquaveCyclicMixin,
    IntervalType,
    DegreeList,
    RelativePitchCollection,
    RootedPitchCollection,
    PitchCollectionBase,
    _parse_equave,
    _convert_degree,
)
from ..utils.interval_normalization import equave_reduce
import numpy as np


class Chord(EquaveCyclicMixin, RelativePitchCollection):
    """
    A musical chord with automatic sorting and deduplication.
    
    Chord represents a collection of pitch intervals that form a musical chord.
    It automatically sorts degrees, removes duplicates, and equave-reduces intervals,
    but unlike Scale, it does NOT enforce the presence of unison. Chords always use 
    equave-cyclic indexing for accessing chord tones in different octaves.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        interval_type: "ratios" or "cents"
        equave: The interval of equivalence, defaults to "2/1" (octave)
        reference_pitch: If provided, the chord is instanced at this pitch
        
    Examples:
        >>> chord = Chord(["1/1", "5/4", "3/2"])  # Major triad
        >>> chord.degrees
        [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
        
        >>> chord[3]  # Next octave
        Fraction(2, 1)
        
        >>> c_major = chord.root("C4")
        >>> c_major[0]
        Pitch(C4, 261.63 Hz)
        >>> type(c_major)
        <class 'Chord'>
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "5/4", "3/2"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str] = "2/1",
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")
        
        parsed_equave = _parse_equave(equave)
        processed_degrees = self._process_chord_degrees(degrees, interval_type, parsed_equave)
        
        if interval_type == "cents":
            if isinstance(parsed_equave, Fraction):
                parsed_equave = 1200.0 if parsed_equave == Fraction(2, 1) else float(parsed_equave)
        else:
            if isinstance(parsed_equave, float):
                parsed_equave = Fraction.from_float(2 ** (parsed_equave / 1200))
        
        self._equave = parsed_equave
        self._equave_cyclic = True
        self._degrees = processed_degrees
        self._interval_type_mode = interval_type
        self._pitches = None
        
        if reference_pitch is not None:
            self._reference_pitch = Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch
        else:
            self._reference_pitch = None
        
        self._intervals = self._compute_chord_intervals()
    
    def _process_chord_degrees(self, degrees: DegreeList, interval_type: str,
                                equave: Union[float, Fraction]) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [_convert_degree(d) for d in degrees]
        
        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else d for d in converted]
            equave_val = equave if isinstance(equave, float) else 1200.0
            
            reduced = []
            for d in converted:
                while d >= equave_val:
                    d -= equave_val
                while d < 0:
                    d += equave_val
                reduced.append(d)
            
            unique = []
            for d in reduced:
                if not any(abs(d - existing) < 1e-6 for existing in unique):
                    unique.append(d)
            unique.sort()
        else:
            converted = [d if isinstance(d, Fraction) else Fraction(d) if isinstance(d, int) else d for d in converted]
            has_float = any(isinstance(d, float) for d in converted)
            if has_float:
                equave_val = float(equave) if not isinstance(equave, float) else equave
                reduced = []
                for d in converted:
                    val = float(d)
                    while val < 1:
                        val *= equave_val
                    while val >= equave_val:
                        val /= equave_val
                    reduced.append(val)
                unique = []
                for d in reduced:
                    if not any(abs(d - existing) < 1e-9 for existing in unique):
                        unique.append(d)
                unique.sort()
            else:
                equave_val = equave if isinstance(equave, Fraction) else Fraction(2, 1)
                reduced = [equave_reduce(d, equave_val) for d in converted]
                unique = sorted(list(set(reduced)))
        
        return unique
    
    def _compute_chord_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        return self._intervals

    @property
    def degrees(self) -> List[Union[Pitch, IntervalType]]:
        if self.is_instanced:
            return [self._calculate_pitch(i) for i in range(len(self._degrees))]
        return list(self._degrees)
    
    def relative(self) -> 'Chord':
        if not self.is_instanced:
            return self
        return Chord(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            None
        )
    
    def root(self, pitch: Union[Pitch, str]) -> 'Chord':
        return Chord(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )
    
    def normalized(self) -> 'Chord':
        if not self._degrees:
            return Chord([], self._interval_type_mode, self._equave, self._reference_pitch)
        
        lowest = self._degrees[0]
        
        if self._interval_type_mode == "cents":
            normalized_degrees = [d - lowest for d in self._degrees]
        else:
            normalized_degrees = [d / lowest for d in self._degrees]
        
        return Chord(normalized_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
    
    def voicing(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> 'Voicing':
        if isinstance(index, slice):
            size = len(self._degrees)
            if size == 0:
                return Voicing([], self._interval_type_mode, self._equave, self._reference_pitch)
            
            start, stop, step = index.indices(size)
            use_cyclic = index.stop is not None and abs(index.stop) > size
            
            if use_cyclic:
                indices = list(range(index.start or 0, index.stop, step))
                selected = [self._get_degree_cyclic(i) for i in indices]
            else:
                selected = [self._degrees[i] for i in range(start, stop, step)]
            
            return Voicing(selected, self._interval_type_mode, self._equave, self._reference_pitch)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            selected = [self._get_degree_cyclic(int(i) if not isinstance(i, int) else i) for i in index]
            return Voicing(selected, self._interval_type_mode, self._equave, self._reference_pitch)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        degree = self._get_degree_cyclic(index)
        return Voicing([degree], self._interval_type_mode, self._equave, self._reference_pitch)
    
    def _get_degree_cyclic(self, index: int) -> IntervalType:
        equave_shift, wrapped_index = self._get_cyclic_index(index)
        return self._calculate_degree_with_shift(equave_shift, wrapped_index)
    
    def __invert__(self) -> 'Chord':
        if len(self._degrees) <= 1:
            return Chord(list(self._degrees), self._interval_type_mode, self._equave, self._reference_pitch)
        
        if self._interval_type_mode == "cents":
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_diff = self._degrees[i] - self._degrees[i-1]
                new_degrees.append(new_degrees[-1] + interval_diff)
        else:
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_ratio = self._degrees[i] / self._degrees[i-1]
                new_degrees.append(new_degrees[-1] * interval_ratio)
        
        return Chord(new_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
    
    def __neg__(self) -> 'Chord':
        return self.__invert__()
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_chord(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_chord(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_chord(index)
    
    def _getitem_single_chord(self, index: int) -> Union[Pitch, IntervalType]:
        equave_shift, wrapped_index = self._get_cyclic_index(index)
        degree = self._calculate_degree_with_shift(equave_shift, wrapped_index)
        
        if self.is_instanced:
            return self._calculate_pitch(index)
        return degree
    
    def _getitem_slice_chord(self, index: slice) -> PitchCollectionBase:
        size = len(self._degrees)
        if size == 0:
            relative = RelativePitchCollection([], self._interval_type_mode, self._equave, self._reference_pitch)
            relative._equave_cyclic = False
            return relative
        
        start, stop, step = index.indices(size)
        use_cyclic = index.stop is not None and abs(index.stop) > size
        
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
            selected_degrees = [self._get_degree_cyclic(i) for i in indices]
        else:
            selected_degrees = [self._degrees[i] for i in range(start, stop, step)]
        
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted

        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        relative._equave_cyclic = False
        return relative
    
    def _getitem_sequence_chord(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = [self._get_degree_cyclic(int(i) if not isinstance(i, int) else i) for i in indices]
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted
        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, None)
        relative._equave_cyclic = False
        return relative
    
    @classmethod
    def from_collection(cls, collection: PitchCollectionBase, equave: Union[float, Fraction, int, str, None] = None) -> 'Chord':
        if not collection.is_relative:
            raise ValueError("Cannot create Chord from absolute collection")
        target_equave = equave if equave is not None else (collection.equave if collection.equave is not None else Fraction(2, 1))
        return cls(
            list(collection._degrees),
            collection._interval_type_mode,
            target_equave,
            collection._reference_pitch
        )


class Voicing(RelativePitchCollection):
    """
    A musical sonority with no equave reduction, removing only exact duplicates.
    
    Sonority represents a "frozen" set of intervals that preserves exact pitch relationships
    without equave cycling. It does not reduce intervals to within an equave, allowing
    for chords that span multiple octaves with exact interval preservation. Exact duplicates
    are removed, but the same pitch-class in different octaves is allowed.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        interval_type: "ratios" or "cents"
        equave: The interval of equivalence, defaults to "2/1" (octave)
        reference_pitch: If provided, the sonority is instanced at this pitch
        
    Examples:
        >>> voicing = Voicing(["1/2", "1/1", "3/2", "5/2"])
        >>> voicing.degrees
        [Fraction(1, 2), Fraction(1, 1), Fraction(3, 2), Fraction(5, 2)]
        
        >>> voicing = Voicing(["1/1", "1/1", "3/2"])  # Exact duplicate removed
        >>> voicing.degrees
        [Fraction(1, 1), Fraction(3, 2)]
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "5/4", "3/2"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str] = "2/1",
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")
        
        parsed_equave = _parse_equave(equave)
        processed_degrees = self._process_sonority_degrees(degrees, interval_type, parsed_equave)
        
        if interval_type == "cents":
            if isinstance(parsed_equave, Fraction):
                parsed_equave = 1200.0 if parsed_equave == Fraction(2, 1) else float(parsed_equave)
        else:
            if isinstance(parsed_equave, float):
                parsed_equave = Fraction.from_float(2 ** (parsed_equave / 1200))
        
        self._equave = parsed_equave
        self._equave_cyclic = False
        self._degrees = processed_degrees
        self._interval_type_mode = interval_type
        self._pitches = None
        
        if reference_pitch is not None:
            self._reference_pitch = Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch
        else:
            self._reference_pitch = None
        
        self._intervals = self._compute_sonority_intervals()
    
    def _process_sonority_degrees(self, degrees: DegreeList, interval_type: str,
                                   equave: Union[float, Fraction]) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [_convert_degree(d) for d in degrees]
        
        if interval_type == "cents":
            converted = [float(d) if isinstance(d, Fraction) else d for d in converted]
            
            unique = []
            for d in converted:
                if not any(abs(d - existing) < 1e-6 for existing in unique):
                    unique.append(d)
            unique.sort()
        else:
            converted = [d if isinstance(d, Fraction) else Fraction(d) if isinstance(d, int) else d for d in converted]
            has_float = any(isinstance(d, float) for d in converted)
            if has_float:
                converted = [float(d) for d in converted]
                unique = []
                for d in converted:
                    if not any(abs(d - existing) < 1e-9 for existing in unique):
                        unique.append(d)
                unique.sort()
            else:
                unique = sorted(list(set(converted)))
        
        return unique
    
    def _compute_sonority_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        return self._intervals

    @property
    def degrees(self) -> List[Union[Pitch, IntervalType]]:
        if self.is_instanced:
            return [self._getitem_single_sonority(i) for i in range(len(self._degrees))]
        return list(self._degrees)
    
    def relative(self) -> 'Voicing':
        if not self.is_instanced:
            return self
        return Voicing(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            None
        )
    
    def root(self, pitch: Union[Pitch, str]) -> 'Voicing':
        return Voicing(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_sonority(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_sonority(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_sonority(index)
    
    def _getitem_single_sonority(self, index: int) -> Union[Pitch, IntervalType]:
        degree = self._degrees[index]
        
        if self.is_instanced:
            if self._interval_type_mode == "cents":
                freq = self._reference_pitch.freq * (2 ** (float(degree) / 1200))
                partial = 2 ** (float(degree) / 1200)
            else:
                freq = self._reference_pitch.freq * float(degree)
                partial = degree
            return Pitch.from_freq(freq, partial)
        return degree
    
    def _getitem_slice_sonority(self, index: slice) -> PitchCollectionBase:
        selected_degrees = self._degrees[index]
        
        if self.is_instanced:
            rooted = RootedPitchCollection(list(selected_degrees), self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted

        relative = RelativePitchCollection(list(selected_degrees), self._interval_type_mode, self._equave, None)
        relative._equave_cyclic = False
        return relative
    
    def _getitem_sequence_sonority(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = [self._degrees[int(i) if not isinstance(i, int) else i] for i in indices]
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted
        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, None)
        relative._equave_cyclic = False
        return relative
    
    @classmethod
    def from_collection(cls, collection: PitchCollectionBase, equave: Union[float, Fraction, int, str, None] = None) -> 'Voicing':
        if not collection.is_relative:
            raise ValueError("Cannot create Voicing from absolute collection")
        target_equave = equave if equave is not None else (collection.equave if collection.equave is not None else Fraction(2, 1))
        return cls(
            list(collection._degrees),
            collection._interval_type_mode,
            target_equave,
            collection._reference_pitch
        )


class Sonority(AbsolutePitchCollection):
    """
    A sonority of absolute Pitch objects without interval structure.
    
    Sonority stores Pitch objects directly without deriving them from
    intervals and a reference pitch. Unlike PitchCollection which can be
    used sequentially, Sonority represents simultaneous pitches (a chord).
    
    Args:
        pitches: List of Pitch objects or pitch strings (e.g., "C4", "D#5")
        
    Examples:
        >>> asnty = Sonority(["C4", "E4", "G4"])
        >>> asnty[0]
        Pitch(C4, 261.63 Hz)
    """
    
    def __init__(self, pitches: Union[List[Pitch], List[str]],
                 equave: Union[float, Fraction, int, str, None] = None,
                 reference_pitch: Union[Pitch, str, None] = None):
        super().__init__(pitches, equave, reference_pitch)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, 'Sonority']:
        result = super().__getitem__(index)
        if isinstance(result, PitchCollectionBase) and not isinstance(result, Sonority):
            sonority = Sonority(result.pitches, result.equave, result.reference_pitch)
            sonority._equave_cyclic = result.equave_cyclic
            return sonority
        return result


FreeSonority = Sonority


class ChordSequence:
    """
    A sequence of Chord, Voicing, or Sonority objects.
    
    ChordSequence provides a container for organizing multiple chord or sonority
    objects in sequence, enabling operations on chord progressions or harmonic
    sequences. Accepts both relative (Chord, Voicing) and absolute (Sonority)
    chord types.
    
    Args:
        chords: List of Chord, Voicing, and/or Sonority objects
        
    Examples:
        >>> chord1 = Chord(["1/1", "5/4", "3/2"])
        >>> chord2 = Chord(["1/1", "6/5", "3/2"])
        >>> sequence = ChordSequence([chord1, chord2])
        >>> len(sequence)
        2
    """
    
    def __init__(self, chords: List[Union[Chord, Voicing, Sonority]] = None):
        self._chords = chords if chords is not None else []
    
    @property
    def chords(self) -> List[Union[Chord, Voicing, Sonority]]:
        return self._chords.copy()
    
    def __len__(self) -> int:
        return len(self._chords)
    
    def __getitem__(self, index: Union[int, slice]) -> Union[Chord, Voicing, Sonority, 'ChordSequence']:
        if isinstance(index, slice):
            return ChordSequence(self._chords[index])
        return self._chords[index]
    
    def __iter__(self):
        return iter(self._chords)
    
    def __repr__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"
    
    def __str__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"


InstancedChord = Chord
InstancedVoicing = Voicing
