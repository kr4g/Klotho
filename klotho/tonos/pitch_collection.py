from fractions import Fraction
import numpy as np
from typing import Union, List, Optional, Any, Sequence, TypeVar, cast, Callable, Generic, overload, Set, Dict, Type
from .pitch import Pitch
from functools import lru_cache

PC = TypeVar('PC', bound='PitchCollection')
IntervalType = TypeVar('IntervalType', float, Fraction)
IntervalList = Union[List[float], List[Fraction], List[int], List[str]]

_addressed_collection_cache = {}

class PitchCollection(Generic[IntervalType]):
    def __init__(self, degrees: IntervalList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1"):
        self._degrees: List[IntervalType] = []
        
        if not degrees:
            equave_value = 2 if equave is None else equave
            self._equave = self._convert_value(equave_value)
            return
        
        converted = [self._convert_value(i) for i in degrees]
        
        self._interval_type = float if any(isinstance(i, float) for i in converted) else Fraction
        
        if self._interval_type == float:
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
            unique_degrees = []
            for i in converted:
                if not any(abs(i - j) < 1e-6 for j in unique_degrees):
                    unique_degrees.append(i)
            converted = sorted(unique_degrees)
        else:
            converted = sorted(list(set(converted)))
        
        self._equave = self._convert_value(degrees[-1] if equave is None else equave)
        
        if isinstance(converted[0], float) and not isinstance(self._equave, float):
            self._equave = float(self._equave)
        elif isinstance(converted[0], Fraction) and isinstance(self._equave, float):
            self._equave = Fraction.from_float(self._equave)
        
        self._degrees = cast(List[IntervalType], converted)
        self._intervals = self._compute_intervals()
        
        self._calculate_value_cache = {}
            
    def _compute_intervals(self) -> List[IntervalType]:
        """Compute intervals between consecutive degrees"""
        if not self._degrees or len(self._degrees) <= 1:
            return []
            
        result = []
        if self.interval_type == float:
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] - self._degrees[i-1])
        else:
            for i in range(1, len(self._degrees)):
                result.append(self._degrees[i] / self._degrees[i-1])
                
        return result
    
    @property
    def degrees(self) -> List[IntervalType]:
        return self._degrees
    
    @property
    def intervals(self) -> List[IntervalType]:
        """Returns the intervals between consecutive degrees"""
        return self._intervals
        
    @property
    def equave(self) -> IntervalType:
        return cast(IntervalType, self._equave)
    
    @property
    def interval_type(self) -> type:
        if not self._degrees:
            return None
        return type(self._degrees[0])
    
    @staticmethod
    def _convert_value(value: Union[float, Fraction, int, str]) -> Union[float, Fraction]:
        if isinstance(value, float):
            return value
        elif isinstance(value, Fraction):
            return value
        elif isinstance(value, int):
            return Fraction(value, 1)
        elif isinstance(value, str) and '/' in value:
            return Fraction(value)
        else:
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"Cannot convert {value} to either a float or Fraction")
    
    def _get_octave_shift_and_index(self, index: int) -> tuple[int, int]:
        if not self._degrees:
            raise IndexError("Cannot index an empty collection")
            
        size = len(self._degrees)
        
        if index >= 0:
            octave_shift = index // size
            wrapped_index = index % size
        else:
            octave_shift = -((-index - 1) // size + 1)
            wrapped_index = size - 1 - ((-index - 1) % size)
            
        return octave_shift, wrapped_index
    
    def _calculate_value(self, octave_shift: int, wrapped_index: int) -> IntervalType:
        cache_key = (octave_shift, wrapped_index)
        if cache_key in self._calculate_value_cache:
            return self._calculate_value_cache[cache_key]
            
        interval = self._degrees[wrapped_index]
        
        if self.interval_type == float:
            if isinstance(self._equave, float):
                result = cast(IntervalType, interval + (octave_shift * self._equave))
            else:
                equave_cents = 1200 * np.log2(float(self._equave))
                result = cast(IntervalType, interval + (octave_shift * equave_cents))
        else:
            if isinstance(self._equave, float):
                equave_ratio = Fraction.from_float(2 ** (self._equave / 1200))
                result = cast(IntervalType, interval * (equave_ratio ** octave_shift))
            else:
                result = cast(IntervalType, interval * (self._equave ** octave_shift))
        
        self._calculate_value_cache[cache_key] = result
        return result
    
    def __getitem__(self, index: Union[int, Sequence[int], 'np.ndarray']) -> Union[IntervalType, List[IntervalType]]:
        if hasattr(index, '__iter__') and not isinstance(index, str):
            return [self[int(i) if not isinstance(i, int) else i] for i in index]
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer or a sequence of integers")
        
        octave_shift, wrapped_index = self._get_octave_shift_and_index(index)
        return self._calculate_value(octave_shift, wrapped_index)
    
    def __or__(self: PC, other: PC) -> PC:
        if not isinstance(other, self.__class__):
            return NotImplemented
        
        type1 = self.interval_type
        type2 = other.interval_type
        
        if type1 == type2:
            if type1 == float:
                combined = list(self._degrees)
                for interval in other._degrees:
                    if not any(abs(interval - existing) < 1e-6 for existing in combined):
                        combined.append(interval)
                return self.__class__(sorted(combined), self._equave)
            else:
                combined = sorted(list(set(self._degrees) | set(other._degrees)))
                return self.__class__(combined, self._equave)
        elif type1 == float:
            converted = self._convert_to_other_type(other)
            return converted | other
        else:
            return other | self
    
    def __and__(self: PC, other: PC) -> PC:
        if not isinstance(other, self.__class__):
            return NotImplemented
        
        type1 = self.interval_type
        type2 = other.interval_type
        
        if type1 == type2:
            if type1 == float:
                intersection = []
                for interval1 in self._degrees:
                    if any(abs(interval1 - interval2) < 1e-6 for interval2 in other._degrees):
                        intersection.append(interval1)
                return self.__class__(sorted(intersection), self._equave)
            else:
                intersection = sorted(list(set(self._degrees) & set(other._degrees)))
                return self.__class__(intersection, self._equave)
        elif type1 == float:
            converted = self._convert_to_other_type(other)
            return converted & other
        else:
            return other & self
    
    def __xor__(self: PC, other: PC) -> PC:
        if not isinstance(other, self.__class__):
            return NotImplemented
        
        type1 = self.interval_type
        type2 = other.interval_type
        
        if type1 == type2:
            if type1 == float:
                difference = []
                for interval1 in self._degrees:
                    if not any(abs(interval1 - interval2) < 1e-6 for interval2 in other._degrees):
                        difference.append(interval1)
                for interval2 in other._degrees:
                    if not any(abs(interval2 - interval1) < 1e-6 for interval1 in self._degrees):
                        difference.append(interval2)
                return self.__class__(sorted(difference), self._equave)
            else:
                difference = sorted(list(set(self._degrees) ^ set(other._degrees)))
                return self.__class__(difference, self._equave)
        elif type1 == float:
            converted = self._convert_to_other_type(other)
            return converted ^ other
        else:
            return other ^ self
    
    def _convert_to_other_type(self: PC, other: PC) -> PC:
        result = self.__class__.__new__(self.__class__)
        
        if self.interval_type == float and other.interval_type == float:
            converted = [1200 * np.log2(float(interval)) for interval in self._degrees]
            result._degrees = converted
            result._equave = 1200.0 if isinstance(other._equave, float) else other._equave
        else:
            converted = [Fraction.from_float(2 ** (interval / 1200)) for interval in self._degrees]
            result._degrees = converted
            result._equave = Fraction(2, 1) if isinstance(other._equave, Fraction) else other._equave
            
        result._intervals = []
        if hasattr(result, '_compute_intervals'):
            result._intervals = result._compute_intervals()
        result._calculate_value_cache = {}
            
        return cast(PC, result)
    
    def __len__(self):
        return len(self._degrees)
    
    def root(self, pitch: Union[Pitch, str]) -> 'AddressedPitchCollection':
        """Create an addressed pitch collection with the given root pitch"""
        if isinstance(pitch, str):
            pitch = Pitch(pitch)
            
        cache_key = (id(self), id(pitch))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedPitchCollection(self, pitch)
        return _addressed_collection_cache[cache_key]
    
    @classmethod
    def from_intervals(cls, intervals: IntervalList) -> PC:
        """Create a pitch collection from a list of intervals"""
        if not intervals:
            return cls()
            
        is_cents = any('.' in str(i) for i in intervals if isinstance(i, (str, float)))
        
        degrees = []
        if is_cents:
            current = 0.0
            degrees = [current]
            for interval in intervals:
                current += float(interval)
                degrees.append(current)
        else:
            current = Fraction(1, 1)
            degrees = [current]
            for interval in intervals:
                current *= Fraction(interval)
                degrees.append(current)
                
        return cls(degrees)
    
    def __invert__(self: PC) -> PC:
        raise NotImplementedError("Subclasses must implement __invert__")
    
    def __neg__(self: PC) -> PC:
        raise NotImplementedError("Subclasses must implement __neg__")
    
    def __repr__(self):
        degrees_str = ', '.join(str(i) for i in self._degrees)
        return f"{self.__class__.__name__}([{degrees_str}], equave={self._equave})"

class AddressedPitchCollection:
    def __init__(self, collection: PitchCollection, reference_pitch: 'Pitch'):
        self.collection = collection
        self.reference_pitch = reference_pitch
        self._get_pitch = lru_cache(maxsize=128)(self._calculate_pitch)
    
    def _calculate_pitch(self, index: int) -> 'Pitch':
        interval = self.collection[index]
        
        if self.collection.interval_type == float:
            return Pitch.from_freq(self.reference_pitch.freq * (2**(float(interval)/1200)))
        else:
            return Pitch.from_freq(self.reference_pitch.freq * float(interval), partial=interval)
    
    def __getitem__(self, index: Union[int, Sequence[int], 'np.ndarray']) -> Union['Pitch', List['Pitch']]:
        if hasattr(index, '__iter__') and not isinstance(index, str):
            return [self[int(i) if not isinstance(i, int) else i] for i in index]
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer or a sequence of integers")
        
        return self._get_pitch(index)
    
    def __call__(self, index: Union[int, Sequence[int]]) -> Union['Pitch', List['Pitch']]:
        return self[index]
    
    def __getattr__(self, name):
        return getattr(self.collection, name)
    
    def __repr__(self):
        size = len(self.collection)
        pitches = []
        for i in range(size):
            pitch = self[i]
            if abs(pitch.cents_offset) > 0.1:
                pitches.append(f"{pitch.pitchclass}{pitch.octave} ({pitch.cents_offset:+.1f}¢)")
            else:
                pitches.append(f"{pitch.pitchclass}{pitch.octave}")
        
        pitches_str = ', '.join(pitches)
        return f"{self.__class__.__name__}([{pitches_str}], equave={self.collection.equave})" 