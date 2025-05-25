from fractions import Fraction
from typing import TypeVar, cast, Optional, Union
from ..pitch import EquaveCyclicPitchCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
import numpy as np

PC = TypeVar('PC', bound='Chord')

class AddressedChord(AddressedPitchCollection):
    """
    A chord bound to a specific root pitch.
    
    AddressedChord provides access to the actual pitches of a chord when rooted
    at a specific pitch, enabling work with concrete frequencies and pitch names
    rather than abstract intervals.
    
    Examples:
        >>> from klotho.tonos import Chord
        >>> major_triad = Chord(["1/1", "5/4", "3/2"])
        >>> c_major = major_triad.root("C4")
        >>> c_major[0]
        C4
        >>> c_major[2]
        G4
    """
    pass

class Chord(EquaveCyclicPitchCollection[IntervalType]):
    """
    A musical chord with automatic sorting and deduplication, preserving equave.
    
    Chord represents a collection of pitch intervals that form a musical chord.
    It automatically sorts degrees and removes duplicates, but unlike Scale,
    it preserves the equave interval when present. Chords support infinite 
    equave displacement for accessing chord tones in different octaves.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        equave: The interval of equivalence, defaults to "2/1" (octave)
        
    Examples:
        >>> chord = Chord(["1/1", "5/4", "3/2"])  # Major triad
        >>> chord.degrees
        [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]
        
        >>> chord[3]  # Next octave
        Fraction(2, 1)
        
        >>> chord.inversion(1)  # First inversion
        Chord([Fraction(5, 4), Fraction(3, 2), Fraction(2, 1)], equave=2)
        
        >>> c_major = chord.root("C4")
        >>> c_major[0]
        C4
    """
    
    def __init__(self, degrees: IntervalList = ["1/1", "5/4", "3/2"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1"):
        super().__init__(degrees, equave, remove_equave=False)
        self._inversion_cache = {}
    
    def inversion(self, inversion_number: int) -> 'Chord':
        """Create a chord inversion by moving the bottom notes to the top.
        
        Args:
            inversion_number: The inversion number (0 = root position, 1 = first inversion, etc.)
            
        Returns:
            A new chord with the specified inversion
        """
        if inversion_number in self._inversion_cache:
            return self._inversion_cache[inversion_number]
            
        if inversion_number == 0:
            return self
            
        size = len(self._degrees)
        if size == 0:
            return Chord([], self._equave)
        
        start_index = inversion_number % size
        if start_index < 0:
            start_index += size
        
        first_degree = self._degrees[start_index]
        inverted_degrees = []
        
        if self.interval_type == float:
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    inverted_degrees.append(self._degrees[current_idx])
                else:
                    interval = self._degrees[current_idx] - first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200 * np.log2(float(self._equave))
                        interval += equave_value
                    inverted_degrees.append(first_degree + interval)
        else:
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    inverted_degrees.append(self._degrees[current_idx])
                else:
                    interval = self._degrees[current_idx] / first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, Fraction) else Fraction.from_float(2 ** (self._equave / 1200))
                        interval *= equave_value
                    inverted_degrees.append(first_degree * interval)
        
        result = Chord(inverted_degrees, self._equave)
        self._inversion_cache[inversion_number] = result
        return result
    
    def __invert__(self: PC) -> PC:
        if len(self._degrees) <= 1:
            return Chord(self._degrees.copy(), self._equave)
        
        if self.interval_type == float:
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_difference = self._degrees[i] - self._degrees[i-1]
                new_degrees.append(new_degrees[-1] + interval_difference)
        else:
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_ratio = self._degrees[i] / self._degrees[i-1]
                new_degrees.append(new_degrees[-1] * interval_ratio)
        
        return Chord(new_degrees, self._equave)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()
        
    def root(self, other: Union[Pitch, str]) -> 'AddressedChord':
        if isinstance(other, str):
            other = Pitch(other)
            
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedChord(self, other)
        return _addressed_collection_cache[cache_key] 
    