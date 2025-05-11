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
    def __init__(self, intervals: IntervalList = ["9/8", "5/4", "4/3", "3/2", "5/3", "15/8", "2/1"], 
                 equave: Optional[Union[float, Fraction, int, str]] = None):
        self._intervals: List[IntervalType] = []
        
        if not intervals:
            equave_value = 2 if equave is None else equave
            self._equave = self._convert_value(equave_value)
            return
        
        converted = [self._convert_value(i) for i in intervals]
        
        self._interval_type = float if any(isinstance(i, float) for i in converted) else Fraction
        
        if self._interval_type == float:
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
            unique_intervals = []
            for i in converted:
                if not any(abs(i - j) < 1e-6 for j in unique_intervals):
                    unique_intervals.append(i)
            converted = sorted(unique_intervals)
            
            if abs(converted[0]) >= 1e-6:
                converted.insert(0, 0.0)
        else:
            converted = sorted(list(set(converted)))
            
            if converted[0] != Fraction(1, 1):
                converted.insert(0, Fraction(1, 1))
        
        self._equave = self._convert_value(intervals[-1] if equave is None else equave)
        
        if isinstance(converted[0], float) and not isinstance(self._equave, float):
            self._equave = float(self._equave)
        elif isinstance(converted[0], Fraction) and isinstance(self._equave, float):
            self._equave = Fraction.from_float(self._equave)
        
        if ((isinstance(converted[-1], float) and isinstance(self._equave, float) and 
             abs(converted[-1] - self._equave) < 1e-6) or
            (isinstance(converted[-1], Fraction) and isinstance(self._equave, Fraction) and 
             converted[-1] == self._equave)):
            converted.pop()
        
        self._intervals = cast(List[IntervalType], converted)
        
        self._calculate_value_cache = {}
        self._mode_cache = {}
    
    @property
    def intervals(self) -> List[IntervalType]:
        return self._intervals
        
    @property
    def equave(self) -> IntervalType:
        return cast(IntervalType, self._equave)
    
    @property
    def interval_type(self) -> type:
        if not self._intervals:
            return None
        return type(self._intervals[0])
    
    def _convert_value(self, value: Union[float, Fraction, int, str]) -> Union[float, Fraction]:
        match value:
            case float():
                return value
            case Fraction():
                return value
            case int():
                return Fraction(value, 1)
            case str() if '/' in value:
                return Fraction(value)
            case _:
                try:
                    return float(value)
                except ValueError:
                    raise ValueError(f"Cannot convert {value} to either a float or Fraction")
    
    def _get_octave_shift_and_index(self, index: int) -> tuple[int, int]:
        if not self._intervals:
            raise IndexError("Cannot index an empty collection")
            
        size = len(self._intervals)
        
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
            
        interval = self._intervals[wrapped_index]
        
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
        
        match (self.interval_type, other.interval_type):
            case (type1, type2) if type1 == type2:
                if type1 == float:
                    combined = list(self._intervals)
                    for interval in other._intervals:
                        if not any(abs(interval - existing) < 1e-6 for existing in combined):
                            combined.append(interval)
                    return self.__class__(sorted(combined), self._equave)
                else:
                    combined = sorted(list(set(self._intervals) | set(other._intervals)))
                    return self.__class__(combined, self._equave)
            case (float, _):
                converted = self._convert_to_other_type(other)
                return converted | other
            case (_, float):
                return other | self
    
    def __and__(self: PC, other: PC) -> PC:
        if not isinstance(other, self.__class__):
            return NotImplemented
        
        match (self.interval_type, other.interval_type):
            case (type1, type2) if type1 == type2:
                if type1 == float:
                    intersection = []
                    for interval1 in self._intervals:
                        if any(abs(interval1 - interval2) < 1e-6 for interval2 in other._intervals):
                            intersection.append(interval1)
                    return self.__class__(sorted(intersection), self._equave)
                else:
                    intersection = sorted(list(set(self._intervals) & set(other._intervals)))
                    return self.__class__(intersection, self._equave)
            case (float, _):
                converted = self._convert_to_other_type(other)
                return converted & other
            case (_, float):
                return other & self
    
    def __xor__(self: PC, other: PC) -> PC:
        if not isinstance(other, self.__class__):
            return NotImplemented
        
        match (self.interval_type, other.interval_type):
            case (type1, type2) if type1 == type2:
                if type1 == float:
                    difference = []
                    for interval1 in self._intervals:
                        if not any(abs(interval1 - interval2) < 1e-6 for interval2 in other._intervals):
                            difference.append(interval1)
                    for interval2 in other._intervals:
                        if not any(abs(interval2 - interval1) < 1e-6 for interval1 in self._intervals):
                            difference.append(interval2)
                    return self.__class__(sorted(difference), self._equave)
                else:
                    difference = sorted(list(set(self._intervals) ^ set(other._intervals)))
                    return self.__class__(difference, self._equave)
            case (float, _):
                converted = self._convert_to_other_type(other)
                return converted ^ other
            case (_, float):
                return other ^ self
    
    def _convert_to_other_type(self: PC, other: PC) -> PC:
        result = self.__class__.__new__(self.__class__)
        
        if self.interval_type == float and other.interval_type == float:
            converted = [1200 * np.log2(float(interval)) for interval in self._intervals]
            result._intervals = converted
            result._equave = 1200.0 if isinstance(other._equave, float) else other._equave
        else:
            converted = [Fraction.from_float(2 ** (interval / 1200)) for interval in self._intervals]
            result._intervals = converted
            result._equave = Fraction(2, 1) if isinstance(other._equave, Fraction) else other._equave
            
        return cast(PC, result)
    
    def mode(self: PC, mode_number: int) -> PC:
        if mode_number in self._mode_cache:
            return self._mode_cache[mode_number]
            
        if mode_number == 0:
            return self
            
        size = len(self._intervals)
        if size == 0:
            return self.__class__([], self._equave)
        
        start_index = mode_number % size
        if start_index < 0:
            start_index += size
        
        first_interval = self._intervals[start_index]
        modal_intervals = []
        
        if self.interval_type == float:
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    modal_intervals.append(0.0)
                else:
                    interval = self._intervals[current_idx] - first_interval
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200 * np.log2(float(self._equave))
                        interval += equave_value
                    modal_intervals.append(interval)
        else:
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    modal_intervals.append(Fraction(1, 1))
                else:
                    interval = self._intervals[current_idx] / first_interval
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, Fraction) else Fraction.from_float(2 ** (self._equave / 1200))
                        interval *= equave_value
                    modal_intervals.append(interval)
        
        result = self.__class__(modal_intervals, self._equave)
        self._mode_cache[mode_number] = result
        return result
    
    def __len__(self):
        return len(self._intervals)
    
    def __mul__(self, other: 'Pitch') -> 'AddressedPitchCollection':
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedPitchCollection(self, other)
        return _addressed_collection_cache[cache_key]
    
    def __rmul__(self, other: 'Pitch') -> 'AddressedPitchCollection':
        cache_key = (id(other), id(self))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedPitchCollection(self, other)
        return _addressed_collection_cache[cache_key]
    
    def __invert__(self: PC) -> PC:
        raise NotImplementedError("Subclasses must implement __invert__")
    
    def __neg__(self: PC) -> PC:
        raise NotImplementedError("Subclasses must implement __neg__")
    
    def __repr__(self):
        intervals_str = ', '.join(str(i) for i in self._intervals)
        return f"{self.__class__.__name__}([{intervals_str}], equave={self._equave})"

class Scale(PitchCollection[IntervalType]):
    def __invert__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._intervals]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._intervals]
        
        return Scale(sorted(inverted), self._equave)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()

class Chord(PitchCollection[IntervalType]):
    def __neg__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._intervals]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._intervals]
        
        return Chord(sorted(inverted), self._equave)
    
    def __invert__(self: PC) -> PC:
        if len(self._intervals) <= 1:
            return Chord(self._intervals.copy(), self._equave)
        
        if self.interval_type == float:
            new_intervals = [0.0]
            for i in range(len(self._intervals) - 1, 0, -1):
                interval_difference = self._intervals[i] - self._intervals[i-1]
                new_intervals.append(new_intervals[-1] + interval_difference)
        else:
            new_intervals = [Fraction(1, 1)]
            for i in range(len(self._intervals) - 1, 0, -1):
                interval_ratio = self._intervals[i] / self._intervals[i-1]
                new_intervals.append(new_intervals[-1] * interval_ratio)
        
        return Chord(new_intervals, self._equave)

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
            if pitch.cents_offset != 0.0:
                pitches.append(f"{pitch.pitchclass}{pitch.octave} ({pitch.cents_offset:+.1f}¢)")
            else:
                pitches.append(f"{pitch.pitchclass}{pitch.octave}")
        
        pitches_str = ', '.join(pitches)
        collection_type = self.collection.__class__.__name__
        return f"Addressed{collection_type}([{pitches_str}])" 