from fractions import Fraction
from typing import TypeVar, cast
from ..pitch_collection import Pitch, PitchCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache

PC = TypeVar('PC', bound='Scale')

class AddressedScale(AddressedPitchCollection):
    pass

class Scale(PitchCollection[IntervalType]):
    def __invert__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._degrees]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._degrees]
        
        return Scale(sorted(inverted), self._equave)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()
        
    def __mul__(self, other: 'Pitch') -> 'AddressedScale':
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedScale(self, other)
        return _addressed_collection_cache[cache_key]
        
    def __rmul__(self, other: 'Pitch') -> 'AddressedScale':
        return self.__mul__(other) 