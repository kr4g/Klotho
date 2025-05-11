from fractions import Fraction
from typing import TypeVar, cast
from ..pitch_collection import PitchCollection, IntervalType

PC = TypeVar('PC', bound='Scale')

class Scale(PitchCollection[IntervalType]):
    def __invert__(self: PC) -> PC:
        if self.interval_type == float:
            inverted = [0.0 if abs(interval) < 1e-6 else 1200.0 - interval for interval in self._intervals]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._intervals]
        
        return Scale(sorted(inverted), self._equave)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__() 