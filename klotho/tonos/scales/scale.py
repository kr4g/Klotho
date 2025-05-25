from fractions import Fraction
from typing import TypeVar, cast, Optional, Union
from ..pitch import EquaveCyclicPitchCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
import numpy as np
from ..utils.interval_normalization import equave_reduce

PC = TypeVar('PC', bound='Scale')

class AddressedScale(AddressedPitchCollection):
    pass

class Scale(EquaveCyclicPitchCollection[IntervalType]):
    def __init__(self, degrees: IntervalList = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1"):
        if degrees:
            converted = [EquaveCyclicPitchCollection._convert_value(i) for i in degrees]
            is_float = any(isinstance(i, float) for i in converted)
            equave_val = EquaveCyclicPitchCollection._convert_value(equave if equave is not None else "2/1")
            
            if is_float:
                converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
                
                unique_degrees = []
                for i in converted:
                    if not any(abs(i - j) < 1e-6 for j in unique_degrees):
                        unique_degrees.append(i)
                
                equave_cents = float(equave_val) if isinstance(equave_val, float) else 1200.0 * np.log2(float(equave_val))
                reduced_degrees = [float(equave_reduce(i, equave_cents)) for i in unique_degrees]
                reduced_degrees.sort()
                
                if reduced_degrees and abs(reduced_degrees[-1] - equave_cents) < 1e-6:
                    reduced_degrees.pop()
                    
                if not reduced_degrees or abs(reduced_degrees[0]) >= 1e-6:
                    reduced_degrees.insert(0, 0.0)
                    
                degrees = reduced_degrees
            else:
                converted = [i if isinstance(i, Fraction) else Fraction(i) for i in converted]
                unique_degrees = list(set(converted))
                reduced_degrees = [equave_reduce(i, equave_val) for i in unique_degrees]
                reduced_degrees.sort()
                
                if reduced_degrees and reduced_degrees[-1] == equave_val:
                    reduced_degrees.pop()
                    
                if not reduced_degrees or reduced_degrees[0] != Fraction(1, 1):
                    reduced_degrees.insert(0, Fraction(1, 1))
                    
                degrees = reduced_degrees
                
        super().__init__(degrees, equave)
        self._mode_cache = {}
        
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
    