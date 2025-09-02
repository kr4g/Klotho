from fractions import Fraction
from typing import TypeVar, cast, Optional, Union, List
from ..pitch import EquaveCyclicCollection, AddressedPitchCollection, IntervalType, _addressed_collection_cache, IntervalList, Pitch
import numpy as np
from ..utils.interval_normalization import equave_reduce
from ...topos.graphs import Graph

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
                 equave: Optional[Union[float, Fraction, int, str]] = "2/1",
                 interval_type: str = "ratios"):
        super().__init__(degrees, equave, interval_type)
        self._mode_cache = {}
        self._graph = self._generate_graph()
        
    def _process_degrees(self, degrees: IntervalList) -> List[IntervalType]:
        processed = super()._process_degrees(degrees)
        
        if not processed:
            return processed
        
        if self._interval_type_mode == "cents":
            if not processed or abs(processed[0]) >= 1e-6:
                processed.insert(0, 0.0)
        else:
            if not processed or processed[0] != Fraction(1, 1):
                processed.insert(0, Fraction(1, 1))
        
        return processed
    
    def _generate_graph(self):
        """Generate a complete graph with scale degrees as nodes."""
        n_nodes = len(self._degrees)
        if n_nodes == 0:
            return Graph()
        
        G = Graph.complete_graph(n_nodes)
        for i, degree in enumerate(self._degrees):
            G.set_node_data(i, degree=degree, index=i)
        return G
    
    @property
    def graph(self):
        """A complete graph with scale degrees as nodes."""
        return self._graph
    
    @property
    def intervals(self) -> List[IntervalType]:
        """
        Returns the intervals between consecutive degrees plus final interval to equave.
        """
        base_intervals = super().intervals
        if self._degrees:
            if self._interval_type_mode == "cents":
                final_interval = self._equave - self._degrees[-1]
            else:
                final_interval = self._equave / self._degrees[-1]
            return base_intervals + [final_interval]
        return base_intervals
        
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
        
        if self._interval_type_mode == "cents":
            for i in range(size):
                current_idx = (start_index + i) % size
                
                if i == 0:
                    modal_degrees.append(0.0)
                else:
                    interval = self._degrees[current_idx] - first_degree
                    if current_idx < start_index:
                        equave_value = self._equave if isinstance(self._equave, float) else 1200.0
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
        
        result = Scale(modal_degrees, self._equave, self._interval_type_mode)
        self._mode_cache[mode_number] = result
        return result
        
    def __invert__(self: PC) -> PC:
        if self._interval_type_mode == "cents":
            inverted = [0.0 if abs(interval) < 1e-6 else self._equave - interval for interval in self._degrees]
        else:
            inverted = [Fraction(1, 1) if interval == Fraction(1, 1) else Fraction(interval.denominator * 2, interval.numerator) for interval in self._degrees]
        
        return Scale(sorted(inverted), self._equave, self._interval_type_mode)
    
    def __neg__(self: PC) -> PC:
        return self.__invert__()
        
    def root(self, other: Union[Pitch, str]) -> 'AddressedScale':
        if isinstance(other, str):
            other = Pitch(other)
            
        cache_key = (id(self), id(other))
        if cache_key not in _addressed_collection_cache:
            _addressed_collection_cache[cache_key] = AddressedScale(self, other)
        return _addressed_collection_cache[cache_key] 
    
    @classmethod
    def n_edo(cls, n: int = 12, equave: float = 1200.0) -> 'Scale':
        """
        Create an n-tone equal division of the equave (n-EDO).
        
        Args:
            n: Number of equal divisions
            equave: Size of the equave in cents (default 1200.0 for octave)
            
        Returns:
            Scale with n equal divisions
            
        Examples:
            >>> Scale.n_edo(12)  # 12-tone equal temperament
            >>> Scale.n_edo(24, 1200)  # Quarter-tone scale
            >>> Scale.n_edo(31, 1200)  # 31-EDO
        """
        step_size = equave / n
        degrees = [i * step_size for i in range(n)]
        return cls(degrees, equave, 'cents')
    
    @classmethod
    def ionian(cls) -> 'Scale':
        """Create the Ionian mode (major scale) in just intonation."""
        return cls(["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"])
    
    @classmethod
    def dorian(cls) -> 'Scale':
        """Create the Dorian mode in just intonation."""
        return cls.ionian().mode(1)
    
    @classmethod
    def phrygian(cls) -> 'Scale':
        """Create the Phrygian mode in just intonation."""
        return cls.ionian().mode(2)
    
    @classmethod
    def lydian(cls) -> 'Scale':
        """Create the Lydian mode in just intonation."""
        return cls.ionian().mode(3)
    
    @classmethod
    def mixolydian(cls) -> 'Scale':
        """Create the Mixolydian mode in just intonation."""
        return cls.ionian().mode(4)
    
    @classmethod
    def aeolian(cls) -> 'Scale':
        """Create the Aeolian mode (natural minor) in just intonation."""
        return cls.ionian().mode(5)
    
    @classmethod
    def locrian(cls) -> 'Scale':
        """Create the Locrian mode in just intonation."""
        return cls.ionian().mode(6)
    