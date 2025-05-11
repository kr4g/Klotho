from fractions import Fraction
from typing import TypeVar, cast
from ..pitch_collection import PitchCollection, IntervalType

PC = TypeVar('PC', bound='Chord')

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