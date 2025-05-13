from fractions import Fraction
from typing import TypeVar, cast
from ..pitch_collection import Pitch, PitchCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache

PC = TypeVar('PC', bound='Chord')

class AddressedChord(AddressedPitchCollection):
    pass

class Chord(PitchCollection[IntervalType]):
    def __neg__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._degrees]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._degrees]
        
        return Chord(sorted(inverted), self._equave)
    
    def __invert__(self: PC) -> PC:
        if len(self._degrees) <= 1:
            return Chord(self._degrees.copy(), self._equave)
        
        if self.interval_type == float:
            new_degrees = [0.0]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_difference = self._degrees[i] - self._degrees[i-1]
                new_degrees.append(new_degrees[-1] + interval_difference)
        else:
            new_degrees = [Fraction(1, 1)]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_ratio = self._degrees[i] / self._degrees[i-1]
                new_degrees.append(new_degrees[-1] * interval_ratio)
        
        return Chord(new_degrees, self._equave)
        
    def __mul__(self, other: 'Pitch') -> 'AddressedChord':
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedChord(self, other)
        return _addressed_collection_cache[cache_key]
        
    def __rmul__(self, other: 'Pitch') -> 'AddressedChord':
        return self.__mul__(other) 