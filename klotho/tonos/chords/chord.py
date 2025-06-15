from fractions import Fraction
from typing import TypeVar, cast, Optional, Union
from ..pitch import EquaveCyclicCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
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
    def _calculate_pitch(self, index: int) -> 'Pitch':
        interval = self._collection[index]
        
        if len(self._collection.degrees) == 0:
            return self._reference_pitch
        
        lowest_interval = self._collection.degrees[0]
        
        if self._collection.interval_type == float:
            freq_ratio = 2**((interval - lowest_interval)/1200)
            return Pitch.from_freq(self._reference_pitch.freq * freq_ratio)
        else:
            freq_ratio = interval / lowest_interval
            return Pitch.from_freq(self._reference_pitch.freq * float(freq_ratio))

class Chord(EquaveCyclicCollection[IntervalType]):
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
        super().__init__(degrees, equave)
    
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
    