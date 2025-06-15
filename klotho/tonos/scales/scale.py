from fractions import Fraction
from typing import TypeVar, cast, Optional, Union, List
from ..pitch import EquaveCyclicCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
import numpy as np
from ..utils.interval_normalization import equave_reduce

PC = TypeVar('PC', bound='Scale')

class AddressedScale(AddressedPitchCollection):
    """
    A scale bound to a specific root pitch.
    
    AddressedScale provides access to the actual pitches of a scale when rooted
    at a specific pitch, enabling work with concrete frequencies and pitch names
    rather than abstract intervals.
    
    Examples:
        >>> from klotho.tonos import Scale
        >>> major = Scale(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
        >>> c_major = major.root("C4")
        >>> c_major[0]
        C4
        >>> c_major[2] 
        E4
    """
    pass

class Scale(EquaveCyclicCollection[IntervalType]):
    """
    A musical scale with automatic sorting, deduplication, and equave removal.
    
    Scale represents a collection of pitch intervals that form a musical scale.
    It automatically sorts degrees, removes duplicates, removes the equave interval,
    and ensures the unison (1/1) is present. Scales support infinite equave 
    displacement for accessing pitches in different octaves.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        equave: The interval of equivalence, defaults to "2/1" (octave)
        
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
        C4
    """
    def __init__(self, degrees: IntervalList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1"):
        super().__init__(degrees, equave)
        self._mode_cache = {}
        
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        processed = super()._process_degrees(degrees)
        
        if not processed:
            return processed
        
        if self._interval_type == float:
            if not processed or abs(processed[0]) >= 1e-6:
                processed.insert(0, 0.0)
        else:
            if not processed or processed[0] != Fraction(1, 1):
                processed.insert(0, Fraction(1, 1))
        
        return processed
        
    def mode(self, mode_number: int) -> 'Scale':
        if mode_number in self._mode_cache:
            return self._mode_cache[mode_number]
            
        if mode_number == 0:
            return self
            
        size = len(self._degrees)
        if size == 0:
            return Scale([], self._equave)
        
        start_index = mode_number % size
        if start_index < 0:
            start_index += size
        
        first_degree = self._degrees[start_index]
        modal_degrees = []
        
        if self.interval_type == float:
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    modal_degrees.append(0.0)
                else:
                    interval = self._degrees[current_idx] - first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200 * np.log2(float(self._equave))
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
        
        result = Scale(modal_degrees, self._equave)
        self._mode_cache[mode_number] = result
        return result
        
    def __invert__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._degrees]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._degrees]
        
        return Scale(sorted(inverted), self._equave)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()
        
    def root(self, other: Union[Pitch, str]) -> 'AddressedScale':
        if isinstance(other, str):
            other = Pitch(other)
            
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedScale(self, other)
        return _addressed_collection_cache[cache_key] 
    