from fractions import Fraction
from typing import Optional, Union, List, Sequence
from ..pitch import Pitch
from ..pitch.pitch_collections import (
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


class Scale(EquaveCyclicMixin, RelativePitchCollection):
    """
    A musical scale with automatic sorting, deduplication, and equave reduction.
    
    Scale represents a collection of pitch intervals that form a musical scale.
    It automatically sorts degrees, removes duplicates, equave-reduces intervals,
    and ensures the unison (1/1 or 0 cents) is present. Scales always use 
    equave-cyclic indexing for accessing pitches in different octaves.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        interval_type: "ratios" or "cents"
        equave: The interval of equivalence, defaults to "2/1" (octave)
        reference_pitch: If provided, the scale is instanced at this pitch
        
    Examples:
        >>> scale = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
        >>> scale.degrees
        [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4), Fraction(4, 3), Fraction(3, 2), Fraction(5, 3), Fraction(15, 8)]
        
        >>> scale[7]  # Next octave
        Fraction(2, 1)
        
        >>> scale.mode(1)  # Dorian mode
        Scale([Fraction(1, 1), Fraction(10, 9), ...], equave=2)
        
        >>> c_major = scale.root("C4")
        >>> c_major[0]
        Pitch(C4, 261.63 Hz)
        >>> type(c_major)
        <class 'Scale'>
    """
    
    def __init__(self, degrees: DegreeList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"],
                 interval_type: str = "ratios",
                 equave: Union[float, Fraction, int, str] = "2/1",
                 reference_pitch: Union[Pitch, str, None] = None):
        if interval_type not in ["ratios", "cents"]:
            raise ValueError("interval_type must be 'ratios' or 'cents'")
        
        parsed_equave = _parse_equave(equave)
        processed_degrees = self._process_scale_degrees(degrees, interval_type, parsed_equave)
        
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
        self._mode_cache = {}
        
        if reference_pitch is not None:
            self._reference_pitch = Pitch(reference_pitch) if isinstance(reference_pitch, str) else reference_pitch
        else:
            self._reference_pitch = None
        
        self._intervals = self._compute_scale_intervals()
    
    def _process_scale_degrees(self, degrees: DegreeList, interval_type: str, 
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
            
            if not unique or abs(unique[0]) >= 1e-6:
                unique.insert(0, 0.0)
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
                if not unique or abs(unique[0] - 1.0) >= 1e-9:
                    unique.insert(0, 1.0)
            else:
                equave_val = equave if isinstance(equave, Fraction) else Fraction(2, 1)
                reduced = [equave_reduce(d, equave_val) for d in converted]
                unique = sorted(list(set(reduced)))
                if not unique or unique[0] != Fraction(1, 1):
                    unique.insert(0, Fraction(1, 1))
        
        return unique
    
    def _compute_scale_intervals(self) -> List[IntervalType]:
        if not self._degrees or len(self._degrees) <= 1:
            return []
        
        result = []
        if self._interval_type_mode == "cents":
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
            final = self._equave - self._degrees[-1]
            result.append(final)
        else:
            for i in range(1, len(self._degrees)):
                prev = self._degrees[i-1]
                if prev == 0 or (isinstance(prev, Fraction) and prev.numerator == 0):
                    result.append(Fraction(0, 1))
                else:
                    result.append(self._degrees[i] / prev)
            final = self._equave / self._degrees[-1]
            result.append(final)
        
        return result
    
    @property
    def intervals(self) -> List[IntervalType]:
        return self._intervals

    @property
    def degrees(self) -> List[Union[Pitch, IntervalType]]:
        if self.is_instanced:
            return [self._calculate_pitch(i) for i in range(len(self._degrees))]
        return list(self._degrees)
    
    def relative(self) -> 'Scale':
        if not self.is_instanced:
            return self
        return Scale(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            None
        )
    
    def root(self, pitch: Union[Pitch, str]) -> 'Scale':
        return Scale(
            list(self._degrees),
            self._interval_type_mode,
            self._equave,
            pitch
        )
    
    def mode(self, mode_number: int) -> 'Scale':
        if mode_number in self._mode_cache:
            cached = self._mode_cache[mode_number]
            if self._reference_pitch:
                return cached.root(self._reference_pitch)
            return cached
        
        if mode_number == 0:
            return self
        
        size = len(self._degrees)
        if size == 0:
            return Scale([], self._interval_type_mode, self._equave, self._reference_pitch)
        
        start_index = mode_number % size
        if start_index < 0:
            start_index += size
        
        first_degree = self._degrees[start_index]
        modal_degrees = []
        
        if self._interval_type_mode == "cents":
            for i in range(size):
                current_idx = (start_index + i) % size
                if i == 0:
                    modal_degrees.append(0.0)
                else:
                    interval = self._degrees[current_idx] - first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200.0
                        interval += equave_value
                    modal_degrees.append(interval)
        else:
            for i in range(size):
                current_idx = (start_index + i) % size
                if i == 0:
                    modal_degrees.append(Fraction(1, 1))
                else:
                    interval = self._degrees[current_idx] / first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, Fraction) else Fraction.from_float(2 ** (self._equave / 1200))
                        interval *= equave_value
                    modal_degrees.append(interval)
        
        result = Scale(modal_degrees, self._interval_type_mode, self._equave, None)
        self._mode_cache[mode_number] = result
        
        if self._reference_pitch:
            return result.root(self._reference_pitch)
        return result
    
    def __invert__(self) -> 'Scale':
        if self._interval_type_mode == "cents":
            inverted = [0.0 if abs(d) < 1e-6 else self._equave - d for d in self._degrees]
        else:
            inverted = [Fraction(1, 1) if d == Fraction(1, 1) else Fraction(d.denominator * 2, d.numerator) for d in self._degrees]
        
        return Scale(sorted(inverted), self._interval_type_mode, self._equave, self._reference_pitch)
    
    def __neg__(self) -> 'Scale':
        return self.__invert__()
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], np.ndarray]) -> Union[Pitch, IntervalType, PitchCollectionBase]:
        if isinstance(index, slice):
            return self._getitem_slice_scale(index)
        
        if hasattr(index, '__iter__') and not isinstance(index, str):
            flat_indices = self._flatten_indices(index)
            return self._getitem_sequence_scale(flat_indices)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._getitem_single_scale(index)
    
    def _getitem_single_scale(self, index: int) -> Union[Pitch, IntervalType]:
        equave_shift, wrapped_index = self._get_cyclic_index(index)
        degree = self._calculate_degree_with_shift(equave_shift, wrapped_index)
        
        if self.is_instanced:
            return self._calculate_pitch(index)
        return degree
    
    def _getitem_slice_scale(self, index: slice) -> PitchCollectionBase:
        size = len(self._degrees)
        if size == 0:
            relative = RelativePitchCollection([], self._interval_type_mode, self._equave, self._reference_pitch)
            relative._equave_cyclic = False
            return relative
        
        start, stop, step = index.indices(size)
        use_cyclic = index.stop is not None and abs(index.stop) > size
        
        if use_cyclic:
            indices = list(range(index.start or 0, index.stop, step))
        else:
            indices = list(range(start, stop, step))
        
        selected_degrees = [
            self._calculate_degree_with_shift(*self._get_cyclic_index(i))
            if use_cyclic
            else self._degrees[i]
            for i in (indices if use_cyclic else range(start, stop, step))
        ]

        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted

        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
        relative._equave_cyclic = False
        return relative
    
    def _getitem_sequence_scale(self, indices: Sequence[int]) -> PitchCollectionBase:
        selected_degrees = []
        for i in indices:
            idx = int(i) if not isinstance(i, int) else i
            equave_shift, wrapped_index = self._get_cyclic_index(idx)
            degree = self._calculate_degree_with_shift(equave_shift, wrapped_index)
            selected_degrees.append(degree)
        if self.is_instanced:
            rooted = RootedPitchCollection(selected_degrees, self._interval_type_mode, self._equave, self._reference_pitch)
            rooted._equave_cyclic = False
            return rooted
        relative = RelativePitchCollection(selected_degrees, self._interval_type_mode, self._equave, None)
        relative._equave_cyclic = False
        return relative
    
    @classmethod
    def n_edo(cls, n: int = 12, equave: float = 1200.0, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        step_size = equave / n
        degrees = [i * step_size for i in range(n)]
        return cls(degrees, 'cents', equave, reference_pitch)
    
    @classmethod
    def ionian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], reference_pitch=reference_pitch)
    
    @classmethod
    def dorian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(1).root(reference_pitch) if reference_pitch else cls.ionian().mode(1)
    
    @classmethod
    def phrygian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(2).root(reference_pitch) if reference_pitch else cls.ionian().mode(2)
    
    @classmethod
    def lydian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(3).root(reference_pitch) if reference_pitch else cls.ionian().mode(3)
    
    @classmethod
    def mixolydian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(4).root(reference_pitch) if reference_pitch else cls.ionian().mode(4)
    
    @classmethod
    def aeolian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(5).root(reference_pitch) if reference_pitch else cls.ionian().mode(5)
    
    @classmethod
    def locrian(cls, reference_pitch: Union[Pitch, str, None] = None) -> 'Scale':
        return cls.ionian().mode(6).root(reference_pitch) if reference_pitch else cls.ionian().mode(6)


InstancedScale = Scale
