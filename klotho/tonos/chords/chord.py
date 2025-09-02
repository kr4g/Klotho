from fractions import Fraction
from typing import TypeVar, cast, Optional, Union, List, Sequence
from ..pitch import PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
from ..utils.interval_normalization import equave_reduce
import numpy as np
from ...topos.graphs import Graph

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
    

    def _calculate_pitch(self, index: int) -> 'Pitch':
        interval = self._collection[index]
        
        if len(self._collection.degrees) == 0:
            return self._reference_pitch
        
        if self._collection.interval_type == float or (hasattr(self._collection, '_interval_type_mode') and self._collection._interval_type_mode == "cents"):
            freq_ratio = 2**(float(interval)/1200)
            return Pitch.from_freq(self._reference_pitch.freq * freq_ratio)
        else:
            freq_ratio = float(interval)
            return Pitch.from_freq(self._reference_pitch.freq * freq_ratio, partial=interval)

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
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1",
                 interval_type: str = "ratios"):
        super().__init__(degrees, equave, interval_type)
        self._graph = self._generate_graph()
    
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        """
        Process degrees for chord: equave reduce, remove duplicates, sort, but do NOT enforce unison.
        """
        if not degrees:
            return []
        
        converted = [self._convert_value(i) for i in degrees]
        
        if self._interval_type_mode == "cents":
            self._interval_type = float
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
            if not isinstance(self._equave, float):
                if self._equave == Fraction(2, 1):
                    self._equave = 1200.0
                else:
                    self._equave = float(self._equave)
            
            reduced_degrees = []
            for i in converted:
                while i >= self._equave:
                    i -= self._equave
                while i < 0:
                    i += self._equave
                reduced_degrees.append(i)
            
            unique_degrees = []
            for i in reduced_degrees:
                if not any(abs(i - j) < 1e-6 for j in unique_degrees):
                    unique_degrees.append(i)
            
            unique_degrees.sort()
        else:
            self._interval_type = Fraction
            converted = [i if isinstance(i, Fraction) else Fraction(i) for i in converted]
            if isinstance(self._equave, float):
                self._equave = Fraction.from_float(self._equave)
            
            reduced_degrees = [equave_reduce(i, self._equave) for i in converted]
            unique_degrees = sorted(list(set(reduced_degrees)))
        
        return cast(List[IntervalType], unique_degrees)
    
    def _generate_graph(self):
        """Generate a complete graph with chord degrees as nodes."""
        n_nodes = len(self._degrees)
        if n_nodes == 0:
            return Graph()
        
        G = Graph.complete_graph(n_nodes)
        for i, degree in enumerate(self._degrees):
            G.set_node_data(i, degree=degree, index=i)
        return G
    
    @property
    def graph(self):
        """A complete graph with chord degrees as nodes."""
        return self._graph
    

    
    def __invert__(self: PC) -> PC:
        if len(self._degrees) <= 1:
            return Chord(self._degrees.copy(), self._equave, self._interval_type_mode)
        
        if self._interval_type_mode == "cents":
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_difference = self._degrees[i] - self._degrees[i-1]
                new_degrees.append(new_degrees[-1] + interval_difference)
        else:
            new_degrees = [self._degrees[0]]
            for i in range(len(self._degrees) - 1, 0, -1):
                interval_ratio = self._degrees[i] / self._degrees[i-1]
                new_degrees.append(new_degrees[-1] * interval_ratio)
        
        return Chord(new_degrees, self._equave, self._interval_type_mode)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()
    
    def normalized(self: PC) -> PC:
        """
        Return a new chord where all intervals are shifted down so that the lowest is 1/1,
        preserving all proportional relationships.
        """
        if not self._degrees:
            return Chord([], self._equave, self._interval_type_mode)
        
        lowest = self._degrees[0]
        
        if self._interval_type_mode == "cents":
            normalized_degrees = [degree - lowest for degree in self._degrees]
        else:
            normalized_degrees = [degree / lowest for degree in self._degrees]
        
        return Chord(normalized_degrees, self._equave, self._interval_type_mode)
    
    @classmethod
    def from_collection(cls, collection: Union[PitchCollection, EquaveCyclicCollection, AddressedPitchCollection]) -> 'Chord':
        """
        Create a Chord from any pitch collection, automatically detecting interval type.
        
        Args:
            collection: Any PitchCollection, EquaveCyclicCollection, or AddressedPitchCollection
            
        Returns:
            New Chord with intervals from the collection
            
        Examples:
            >>> from klotho.tonos import Scale, Motive
            >>> scale = Scale.n_edo(24, 1200)
            >>> motive = Motive([0, 3, 6, 9])
            >>> collection = scale[motive]
            >>> chord = Chord.from_collection(collection)
        """
        if isinstance(collection, AddressedPitchCollection):
            underlying_collection = collection._collection
        else:
            underlying_collection = collection
        
        interval_type_mode = getattr(underlying_collection, '_interval_type_mode', 'ratios')
        equave = underlying_collection.equave
        degrees = underlying_collection.degrees
        
        return cls(degrees, equave, interval_type_mode)
    
    def root(self, other: Union[Pitch, str]) -> 'AddressedChord':
        if isinstance(other, str):
            other = Pitch(other)
            
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedChord(self, other)
        return _addressed_collection_cache[cache_key] 


class AddressedSonority(AddressedPitchCollection):
    """
    A sonority bound to a specific root pitch.
    
    AddressedSonority provides access to the actual pitches of a sonority when rooted
    at a specific pitch, enabling work with concrete frequencies and pitch names
    rather than abstract intervals.
    
    Examples:
        >>> from klotho.tonos import Sonority
        >>> sonority = Sonority(["1/2", "1/1", "3/2", "5/2"])
        >>> c_sonority = sonority.root("C4")
        >>> c_sonority[0]
        C4-
        >>> c_sonority[3]
        C6+
    """
    pass


class Sonority(PitchCollection[IntervalType]):
    """
    A musical sonority with no equave reduction, allowing duplicates and cross-equave intervals.
    
    Sonority represents a "frozen" set of intervals that preserves exact pitch relationships
    without equave cycling. It does not reduce intervals to within an equave, allowing
    for chords that span multiple octaves with exact interval preservation.
    
    Args:
        degrees: List of intervals as ratios, decimals, or numbers
        equave: The interval of equivalence, defaults to "2/1" (octave)
        
    Examples:
        >>> sonority = Sonority(["1/2", "1/1", "3/2", "5/2"])
        >>> sonority.degrees
        [Fraction(1, 2), Fraction(1, 1), Fraction(3, 2), Fraction(5, 2)]
        
        >>> sonority.shift_equave(3, -1)  # Shift index 3 down one equave
        Sonority([Fraction(1, 2), Fraction(1, 1), Fraction(3, 2), Fraction(5, 4)])
    """
    
    def __init__(self, degrees: IntervalList = ["1/1", "5/4", "3/2"], 
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1",
                 interval_type: str = "ratios"):
        super().__init__(degrees, equave, interval_type)
        self._graph = self._generate_graph()
    
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        """
        Process degrees for sonority: do NOT equave reduce, do NOT remove duplicates, but sort.
        """
        if not degrees:
            return []
        
        converted = [self._convert_value(i) for i in degrees]
        
        if self._interval_type_mode == "cents":
            self._interval_type = float
            converted = [float(i) if isinstance(i, Fraction) else i for i in converted]
            if not isinstance(self._equave, float):
                if self._equave == Fraction(2, 1):
                    self._equave = 1200.0
                else:
                    self._equave = float(self._equave)
        else:
            self._interval_type = Fraction
            converted = [i if isinstance(i, Fraction) else Fraction(i) for i in converted]
            if isinstance(self._equave, float):
                self._equave = Fraction.from_float(self._equave)
        
        converted.sort()
        return cast(List[IntervalType], converted)
    
    def _generate_graph(self):
        """Generate a complete graph with sonority degrees as nodes."""
        n_nodes = len(self._degrees)
        if n_nodes == 0:
            return Graph()
        
        G = Graph.complete_graph(n_nodes)
        for i, degree in enumerate(self._degrees):
            G.set_node_data(i, degree=degree, index=i)
        return G
    
    @property
    def graph(self):
        """A complete graph with sonority degrees as nodes."""
        return self._graph
    
    def shift_equave(self, indices: Union[int, List[int], Sequence[int]], direction: int) -> 'Sonority':
        """
        Return a new sonority with specified intervals shifted by equave(s).
        
        Args:
            indices: Index or list of indices to shift
            direction: Number of equaves to shift (positive = up, negative = down)
            
        Returns:
            New Sonority with shifted intervals
            
        Examples:
            >>> sonority = Sonority(["1/2", "1/1", "3/2", "5/2"])
            >>> sonority.shift_equave(3, -1)  # Shift index 3 down one equave
            >>> sonority.shift_equave([1, 2], 1)  # Shift indices 1 and 2 up one equave
        """
        if isinstance(indices, int):
            indices = [indices]
        
        new_degrees = self._degrees.copy()
        
        for idx in indices:
            if 0 <= idx < len(new_degrees):
                if self._interval_type_mode == "cents":
                    equave_shift = direction * (self._equave if isinstance(self._equave, float) else 1200.0)
                    new_degrees[idx] = new_degrees[idx] + equave_shift
                else:
                    equave_ratio = self._equave if isinstance(self._equave, Fraction) else Fraction(2, 1)
                    new_degrees[idx] = new_degrees[idx] * (equave_ratio ** direction)
        
        return Sonority(new_degrees, self._equave, self._interval_type_mode)
    
    def remove_duplicates(self) -> 'Sonority':
        """Return a new sonority with all duplicate intervals removed."""
        if self._interval_type_mode == "cents":
            unique_degrees = []
            for degree in self._degrees:
                if not any(abs(degree - existing) < 1e-6 for existing in unique_degrees):
                    unique_degrees.append(degree)
        else:
            unique_degrees = sorted(list(set(self._degrees)))
        
        return Sonority(unique_degrees, self._equave, self._interval_type_mode)
    
    def add_interval(self, interval: Union[float, Fraction, int, str]) -> 'Sonority':
        """Return a new sonority with the interval added and sorted."""
        new_degrees = self._degrees.copy()
        new_interval = self._convert_value(interval)
        
        if self._interval_type_mode == "cents":
            new_interval = float(new_interval) if isinstance(new_interval, Fraction) else new_interval
        else:
            new_interval = new_interval if isinstance(new_interval, Fraction) else Fraction(new_interval)
        
        new_degrees.append(new_interval)
        return Sonority(new_degrees, self._equave, self._interval_type_mode)
    
    def remove_interval(self, interval: Union[float, Fraction, int, str]) -> 'Sonority':
        """Return a new sonority with the first occurrence of the interval removed."""
        target_interval = self._convert_value(interval)
        
        if self._interval_type_mode == "cents":
            target_interval = float(target_interval) if isinstance(target_interval, Fraction) else target_interval
        else:
            target_interval = target_interval if isinstance(target_interval, Fraction) else Fraction(target_interval)
        
        new_degrees = self._degrees.copy()
        
        if self._interval_type_mode == "cents":
            for i, degree in enumerate(new_degrees):
                if abs(degree - target_interval) < 1e-6:
                    new_degrees.pop(i)
                    break
        else:
            try:
                new_degrees.remove(target_interval)
            except ValueError:
                pass
        
        return Sonority(new_degrees, self._equave, self._interval_type_mode)
    
    @classmethod
    def from_collection(cls, collection: Union[PitchCollection, EquaveCyclicCollection, AddressedPitchCollection]) -> 'Sonority':
        """
        Create a Sonority from any pitch collection, automatically detecting interval type.
        
        Args:
            collection: Any PitchCollection, EquaveCyclicCollection, or AddressedPitchCollection
            
        Returns:
            New Sonority with intervals from the collection
            
        Examples:
            >>> from klotho.tonos import Scale, Motive
            >>> scale = Scale.n_edo(24, 1200)
            >>> motive = Motive([0, 3, 6, 9])
            >>> collection = scale[motive]
            >>> sonority = Sonority.from_collection(collection)
        """
        if isinstance(collection, AddressedPitchCollection):
            underlying_collection = collection._collection
        else:
            underlying_collection = collection
        
        interval_type_mode = getattr(underlying_collection, '_interval_type_mode', 'ratios')
        equave = underlying_collection.equave
        degrees = underlying_collection.degrees
        
        return cls(degrees, equave, interval_type_mode)
    
    def root(self, other: Union[Pitch, str]) -> 'AddressedSonority':
        """Create an addressed sonority with the given root pitch."""
        if isinstance(other, str):
            other = Pitch(other)
            
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedSonority(self, other)
        return _addressed_collection_cache[cache_key]


SC = TypeVar('SC', bound='ChordSequence')

class ChordSequence:
    """
    A sequence of Chord or Sonority objects.
    
    ChordSequence provides a container for organizing multiple chord or sonority
    objects in sequence, enabling operations on chord progressions or harmonic
    sequences.
    
    Args:
        chords: List of Chord and/or Sonority objects
        
    Examples:
        >>> from klotho.tonos import Chord, Sonority
        >>> chord1 = Chord(["1/1", "5/4", "3/2"])
        >>> chord2 = Chord(["1/1", "6/5", "3/2"])
        >>> sequence = ChordSequence([chord1, chord2])
        >>> len(sequence)
        2
    """
    
    def __init__(self, chords: List[Union[Chord, Sonority]] = None):
        self._chords = chords if chords is not None else []
    
    @property
    def chords(self) -> List[Union[Chord, Sonority]]:
        """Return the list of chords/sonorities in the sequence."""
        return self._chords.copy()
    
    def __len__(self) -> int:
        return len(self._chords)
    
    def __getitem__(self, index: Union[int, slice]) -> Union[Chord, Sonority, 'ChordSequence']:
        if isinstance(index, slice):
            return ChordSequence(self._chords[index])
        return self._chords[index]
    
    def __iter__(self):
        return iter(self._chords)
    
    def __repr__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"
    
    def __str__(self) -> str:
        return f"ChordSequence({len(self._chords)} chords)"
    