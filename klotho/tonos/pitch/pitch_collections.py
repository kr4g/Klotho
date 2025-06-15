from fractions import Fraction
import numpy as np
from typing import Union, List, Optional, Any, Sequence, TypeVar, cast, Callable, Generic, overload, Set, Dict, Type
from .pitch import Pitch
from functools import lru_cache
from ..utils.interval_normalization import equave_reduce

PC = TypeVar('PC', bound='PitchCollection')
ECC = TypeVar('ECC', bound='EquaveCyclicCollection')
IntervalType = TypeVar('IntervalType', float, Fraction)
IntervalList = Union[List[float], List[Fraction], List[int], List[str]]

_addressed_collection_cache = {}

class PitchCollection(Generic[IntervalType]):
    """
    A collection of pitch intervals that preserves order and allows duplicates.
    
    PitchCollection is the base class for organizing musical intervals. It maintains
    the exact order and duplicates as provided, making it suitable for sequences
    where order matters and repetition is meaningful.
    
    Args:
        degrees: List of intervals as ratios (strings like "3/2"), decimals, or numbers
        equave: The interval of equivalence, defaults to "2/1" (octave)
        
    Examples:
        >>> pc = PitchCollection(["1/1", "5/4", "3/2"])
        >>> pc.degrees
        [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
        
        >>> pc = PitchCollection([0.0, 386.3, 702.0])  # cents
        >>> pc.interval_type
        <class 'float'>
    """
    
    def __init__(self, degrees: IntervalList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1"):
        self._equave = self._convert_value(equave if equave is not None else "2/1")
        self._degrees = self._process_degrees(degrees)
        self._intervals = self._compute_intervals()
            
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [self._convert_value(i) for i in degrees]
        self._interval_type = float if any(isinstance(i, float) for i in converted) else Fraction
        
        if self._interval_type == float:
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
        else:
            converted = [i if isinstance(i, Fraction) else Fraction(i) for i in converted]
        
        if converted and isinstance(converted[0], float) and not isinstance(self._equave, float):
            self._equave = float(self._equave)
        elif converted and isinstance(converted[0], Fraction) and isinstance(self._equave, float):
            self._equave = Fraction.from_float(self._equave)
        
        return cast(List[IntervalType], converted)
    
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
    
    def _get_wrapped_index(self, index: int) -> int:
        if not self._degrees:
            raise IndexError("Cannot index an empty collection")
        return index % len(self._degrees)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], 'np.ndarray']) -> Union[IntervalType, 'PitchCollection']:
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self._degrees))
            indices = list(range(start, stop, step))
            selected_degrees = [self._degrees[i] for i in indices]
            return PitchCollection(selected_degrees, self._equave)
            
        if hasattr(index, '__iter__') and not isinstance(index, str):
            selected_degrees = [self[int(i) if not isinstance(i, int) else i] for i in index]
            return PitchCollection(selected_degrees, self._equave)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        wrapped_index = self._get_wrapped_index(index)
        return self._degrees[wrapped_index]
    
    def __iter__(self):
        """Iterate over the base degrees only"""
        return iter(self._degrees)
    
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
            
        return cast(PC, result)
    
    def __len__(self):
        return len(self._degrees)
    
    def index(self, value: Union[float, Fraction, int, str], start: int = 0, stop: Optional[int] = None) -> int:
        if not self._degrees:
            raise ValueError("Cannot search in an empty collection")
        
        target_value = self._convert_value(value)
        
        if self.interval_type == float and not isinstance(target_value, float):
            target_value = float(target_value)
        elif self.interval_type == Fraction and isinstance(target_value, float):
            target_value = Fraction.from_float(target_value)
        
        if self.interval_type == float:
            for i, degree in enumerate(self._degrees):
                if abs(degree - target_value) < 1e-6:
                    if i >= start and (stop is None or i < stop):
                        return i
        else:
            try:
                base_index = self._degrees.index(target_value)
                if base_index >= start and (stop is None or base_index < stop):
                    return base_index
            except ValueError:
                pass
        
        raise ValueError(f"Interval {value} not found in collection")
    
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


class EquaveCyclicCollection(PitchCollection[IntervalType]):
    """
    A pitch collection with infinite equave-displacement indexing and automatic sorting.
    
    This class extends PitchCollection to support indexing beyond the collection bounds,
    where out-of-bounds indices wrap around the equave. It automatically sorts degrees
    and removes duplicates, making it suitable for scales and chords that represent
    pitch classes within an equave.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        equave: The interval of equivalence, defaults to "2/1" (octave)
        remove_equave: Whether to remove the equave from degrees (True for scales, False for chords)
        
    Examples:
        >>> ecc = EquaveCyclicCollection(["5/4", "1/1", "3/2"])
        >>> ecc.degrees  # Automatically sorted
        [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
        
        >>> ecc[3]  # Equave displacement
        Fraction(2, 1)
        
        >>> ecc[-1]  # Negative indexing
        Fraction(3, 4)
    """
    
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        if not degrees:
            return []
        
        converted = [self._convert_value(i) for i in degrees]
        is_float = any(isinstance(i, float) for i in converted)
        
        if is_float:
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
            self._interval_type = float
            
            reduced_degrees = [float(equave_reduce(i, self._equave)) for i in converted]
            
            unique_degrees = []
            for i in reduced_degrees:
                if not any(abs(i - j) < 1e-6 for j in unique_degrees):
                    unique_degrees.append(i)
            
            unique_degrees.sort()
        else:
            converted = [i if isinstance(i, Fraction) else Fraction(i) for i in converted]
            self._interval_type = Fraction
            
            reduced_degrees = [equave_reduce(i, self._equave) for i in converted]
            unique_degrees = sorted(list(set(reduced_degrees)))
        
        if converted and isinstance(converted[0], float) and not isinstance(self._equave, float):
            self._equave = float(self._equave)
        elif converted and isinstance(converted[0], Fraction) and isinstance(self._equave, float):
            self._equave = Fraction.from_float(self._equave)
        
        return cast(List[IntervalType], unique_degrees)
    
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
        
        return result
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], 'np.ndarray']) -> Union[IntervalType, 'PitchCollection']:
        if isinstance(index, slice):
            size = len(self._degrees)
            if size == 0:
                return PitchCollection([], self._equave)
                
            start, stop, step = index.indices(size)
            
            if index.stop is None or (index.stop is not None and abs(index.stop) <= size):
                indices = list(range(start, stop, step))
                selected_degrees = [self._degrees[i] for i in indices]
                return PitchCollection(selected_degrees, self._equave)
            else:
                indices = list(range(index.start or 0, index.stop, step))
                selected_degrees = [self[i] for i in indices]
                return PitchCollection(selected_degrees, self._equave)
            
        if hasattr(index, '__iter__') and not isinstance(index, str):
            selected_degrees = [self[int(i) if not isinstance(i, int) else i] for i in index]
            return PitchCollection(selected_degrees, self._equave)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        octave_shift, wrapped_index = self._get_octave_shift_and_index(index)
        return self._calculate_value(octave_shift, wrapped_index)
    
    def index(self, value: Union[float, Fraction, int, str], start: int = 0, stop: Optional[int] = None) -> int:
        if not self._degrees:
            raise ValueError("Cannot search in an empty collection")
        
        target_value = self._convert_value(value)
        
        if self.interval_type == float and not isinstance(target_value, float):
            target_value = float(target_value)
        elif self.interval_type == Fraction and isinstance(target_value, float):
            target_value = Fraction.from_float(target_value)
        
        size = len(self._degrees)
        
        if self.interval_type == float:
            for i, degree in enumerate(self._degrees):
                if abs(degree - target_value) < 1e-6:
                    base_index = i
                    if base_index >= start and (stop is None or base_index < stop):
                        return base_index
        else:
            try:
                base_index = self._degrees.index(target_value)
                if base_index >= start and (stop is None or base_index < stop):
                    return base_index
            except ValueError:
                pass
        
        if self.interval_type == float:
            equave_cents = 1200.0 if isinstance(self._equave, float) else 1200 * np.log2(float(self._equave))
            reduced_value = target_value % equave_cents
            octave_shift = int(target_value // equave_cents)
            
            for i, degree in enumerate(self._degrees):
                if abs(degree - reduced_value) < 1e-6:
                    calculated_index = octave_shift * size + i
                    if (start <= 0 or calculated_index >= start) and (stop is None or calculated_index < stop):
                        return calculated_index
        else:
            if isinstance(self._equave, float):
                equave_ratio = Fraction.from_float(2 ** (self._equave / 1200))
            else:
                equave_ratio = self._equave
            
            octave_shift = 0
            reduced_value = target_value
            
            while reduced_value >= equave_ratio:
                reduced_value /= equave_ratio
                octave_shift += 1
            
            while reduced_value < Fraction(1, 1):
                reduced_value *= equave_ratio
                octave_shift -= 1
            
            try:
                base_index = self._degrees.index(reduced_value)
                calculated_index = octave_shift * size + base_index
                if (start <= 0 or calculated_index >= start) and (stop is None or calculated_index < stop):
                    return calculated_index
            except ValueError:
                pass
        
        raise ValueError(f"Interval {value} not found in collection")


class AddressedPitchCollection:
    """
    A pitch collection bound to a specific reference pitch.
    
    AddressedPitchCollection wraps any PitchCollection with a reference pitch,
    allowing access to actual Pitch objects rather than abstract intervals.
    This enables working with concrete frequencies and pitch names.
    
    Args:
        collection: The underlying PitchCollection
        reference_pitch: The pitch that corresponds to the collection's reference interval
        
    Examples:
        >>> from klotho.tonos import Scale, Pitch
        >>> scale = Scale(["1/1", "9/8", "5/4"])
        >>> addressed = scale.root("C4")
        >>> addressed[0]
        C4
        >>> addressed[1] 
        D4
        
        >>> addressed[[0, 1, 2]]  # Returns AddressedPitchCollection
        AddressedPitchCollection([C4, D4, E4], equave=2)
    """
    
    def __init__(self, collection: PitchCollection, reference_pitch: 'Pitch'):
        self._collection = collection
        self._reference_pitch = reference_pitch
        self._get_pitch = lru_cache(maxsize=128)(self._calculate_pitch)
    
    @property
    def reference_pitch(self) -> 'Pitch':
        """The reference pitch for this addressed collection"""
        return self._reference_pitch
    
    @property
    def degrees(self) -> List['Pitch']:
        """Returns the degrees as Pitch instances"""
        return [self[i] for i in range(len(self._collection))]
    
    def _calculate_pitch(self, index: int) -> 'Pitch':
        interval = self._collection[index]
        
        if self._collection.interval_type == float:
            return Pitch.from_freq(self._reference_pitch.freq * (2**(float(interval)/1200)))
        else:
            return Pitch.from_freq(self._reference_pitch.freq * float(interval), partial=interval)
    
    def __getitem__(self, index: Union[int, slice, Sequence[int], 'np.ndarray']) -> Union['Pitch', 'AddressedPitchCollection']:
        if isinstance(index, slice):
            interval_collection = self._collection[index]
            return AddressedPitchCollection(interval_collection, self._reference_pitch)
            
        if hasattr(index, '__iter__') and not isinstance(index, str):
            selected_pitches = [self[int(i) if not isinstance(i, int) else i] for i in index]
            selected_intervals = []
            for pitch in selected_pitches:
                if self._collection.interval_type == float:
                    interval = 1200 * np.log2(pitch.freq / self._reference_pitch.freq)
                else:
                    interval = Fraction(pitch.freq / self._reference_pitch.freq)
                selected_intervals.append(interval)
            
            new_collection = PitchCollection(selected_intervals, self._collection.equave)
            return AddressedPitchCollection(new_collection, self._reference_pitch)
        
        if not isinstance(index, int):
            raise TypeError("Index must be an integer, slice, or sequence of integers")
        
        return self._get_pitch(index)
    
    def __call__(self, index: Union[int, Sequence[int]]) -> Union['Pitch', 'AddressedPitchCollection']:
        return self[index]
    
    def __len__(self):
        return len(self._collection)
    
    def __iter__(self):
        """Iterate over the base degrees as Pitch instances"""
        for i in range(len(self._collection)):
            yield self[i]
    
    def __getattr__(self, name):
        return getattr(self._collection, name)
    
    def __repr__(self):
        size = len(self._collection)
        pitches = []
        for i in range(size):
            pitch = self[i]
            if abs(pitch.cents_offset) > 0.01:
                pitches.append(f"{pitch.pitchclass}{pitch.octave} ({pitch.cents_offset:+.1f}¢)")
            else:
                pitches.append(f"{pitch.pitchclass}{pitch.octave}")
        
        pitches_str = ', '.join(pitches)
        return f"{self.__class__.__name__}([{pitches_str}], equave={self._collection.equave})"
