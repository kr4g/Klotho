from typing import List, Union, Dict, Tuple, Optional
from fractions import Fraction
import numpy as np
from sympy import prime as sympy_prime

from klotho.topos.graphs.lattices import Lattice
from klotho.utils.algorithms.factors import ratios_to_lattice_vectors, from_factors
from klotho.tonos.utils.interval_normalization import equave_reduce as equave_reduce_func


class ToneLattice(Lattice):
    """
    A lattice structure for representing musical intervals in prime number space.
    
    A ToneLattice extends the basic Lattice class by interpreting each coordinate
    dimension as an exponent of consecutive prime numbers starting from 2. This
    allows for geometric representation of musical intervals and harmonic relationships.
    
    Parameters
    ----------
    dimensionality : int
        Number of dimensions (prime numbers) to use.
    resolution : int or list of int
        Number of points along each dimension, or list of resolutions per dimension.
    bipolar : bool, optional
        If True, coordinates range from -resolution to +resolution. 
        If False, coordinates range from 0 to resolution (default is True).
    periodic : bool, optional
        Whether to use periodic boundary conditions (default is False).
    equave_reduce : bool, optional
        If True, ignore the 2-prime dimension for plotting and equave-reduce all ratios.
        If False, include all prime dimensions (default is True).
    """
    
    def __init__(self, 
                 dimensionality: int = 2, 
                 resolution: Union[int, List[int]] = 10, 
                 bipolar: bool = True,
                 periodic: bool = False,
                 equave_reduce: bool = True,
                 equave: Union[int, float, Fraction, str] = 2):
        
        self._equave_reduce = equave_reduce
        self._equave = Fraction(equave)
        
        super().__init__(
            dimensionality=dimensionality,
            resolution=resolution,
            bipolar=bipolar,
            periodic=periodic
        )
        
        if equave_reduce:
            self._primes = [sympy_prime(i) for i in range(2, dimensionality + 2)]
        else:
            self._primes = [sympy_prime(i) for i in range(1, dimensionality + 1)]
        
        self._populate_ratio_data()
    
    def _custom_equave_reduce(self, interval: Union[int, float, Fraction, str]) -> Fraction:
        """
        Reduce an interval to the range (1/2, 2) EXCLUSIVE on both ends.
        
        This differs from the standard equave_reduce which uses [1, 2).
        """
        interval = Fraction(interval)
        equave = self._equave
        
        # Bring interval into (1/2, 2) range - EXCLUSIVE on both ends
        while interval <= Fraction(1, 2):
            interval *= equave
        while interval >= equave:
            interval /= equave
        
        return interval
    

    
    def _populate_ratio_data(self):
        """Populate nodes with ratio data based on their coordinates."""
        if not self._is_lazy:
            # For non-lazy lattices, populate all nodes with ratio data
            for coord in self.coords:
                node_id = self._get_node_for_coord(coord)
                if node_id is not None:
                    ratio = self._coord_to_ratio(coord)
                    self[coord]['ratio'] = ratio
    
    def _coord_to_ratio(self, coord: Tuple[int, ...]) -> Fraction:
        """Convert lattice coordinates to musical ratio."""
        factors = {}
        
        for i, exp in enumerate(coord):
            if exp != 0 and i < len(self._primes):
                prime = self._primes[i]
                factors[prime] = exp
        
        ratio = from_factors(factors)
        
        if self._equave_reduce:
            ratio = self._custom_equave_reduce(ratio)
        
        return ratio
    
    def __getitem__(self, coord):
        """Get node data for a coordinate, ensuring ratio is included."""
        node_data = super().__getitem__(coord)
        
        # Ensure ratio is in the node data
        if 'ratio' not in node_data:
            ratio = self._coord_to_ratio(coord)
            node_data['ratio'] = ratio
        
        return node_data
    
    def get_ratio(self, coord: Tuple[int, ...]) -> Fraction:
        """
        Get the musical ratio for given coordinates.
        
        Parameters
        ----------
        coord : Tuple[int, ...]
            Lattice coordinates.
            
        Returns
        -------
        Fraction
            The musical ratio represented by these coordinates.
        """
        if coord not in self:
            raise KeyError(f"Coordinate {coord} not found in lattice")
        
        return self._coord_to_ratio(coord)
    
    def get_coordinates_for_ratio(self, ratio: Union[int, float, Fraction, str]) -> Optional[Tuple[int, ...]]:
        """
        Get lattice coordinates for a given musical ratio.
        
        Parameters
        ----------
        ratio : Union[int, float, Fraction, str]
            Musical ratio to find coordinates for.
            
        Returns
        -------
        Optional[Tuple[int, ...]]
            Lattice coordinates for the ratio, or None if not in lattice.
        """
        ratio = Fraction(ratio)
        
        if self._equave_reduce:
            ratio = self._custom_equave_reduce(ratio)
        
        vectors_dict = ratios_to_lattice_vectors([ratio])
        vector = list(vectors_dict.values())[0]
        
        if self._equave_reduce:
            coord = tuple(int(x) for x in vector[1:])
        else:
            coord = tuple(int(x) for x in vector)
        
        # Pad coordinate to match lattice dimensionality
        if len(coord) < self.dimensionality:
            coord = coord + (0,) * (self.dimensionality - len(coord))
        
        if coord in self:
            return coord
        return None
    

    
    @property
    def primes(self) -> List[int]:
        """List of prime numbers used in this lattice."""
        return self._primes.copy()
    
    @property
    def equave_reduce(self) -> bool:
        """Whether this lattice uses equave reduction."""
        return self._equave_reduce
    
    def __str__(self) -> str:
        """String representation of the tone lattice."""
        base_str = super().__str__()
        primes_str = ', '.join(str(p) for p in self._primes)
        equave_str = "equave-reduced" if self._equave_reduce else "full"
        
        return f"Tone{base_str[:-1]}, primes=[{primes_str}], {equave_str})"
