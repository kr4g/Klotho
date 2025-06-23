from typing import Tuple, List, Union
import networkx as nx
import pandas as pd
from ..graphs import Graph


class Lattice(Graph):
    """
    A generic n-dimensional lattice structure.
    
    A lattice provides a discrete sampling of n-dimensional space with integer
    coordinates. This can be used for various applications such as spatial fields,
    microtonal tone lattices, or any discrete grid-based structure.
    
    Parameters
    ----------
    dimensionality : int
        Number of dimensions.
    resolution : int or list of int
        Number of points along each dimension, or list of resolutions per dimension.
    bipolar : bool, optional
        If True, coordinates range from -resolution to +resolution. 
        If False, coordinates range from 0 to resolution (default is True).
    """
    
    def __init__(self, 
                 dimensionality : int                   = 2, 
                 resolution     : Union[int, List[int]] = 10, 
                 bipolar        : bool                  = True,
                 periodic       : bool                  = False,
        ):
        
        self._dimensionality = dimensionality
        self._bipolar = bipolar
        
        if isinstance(resolution, int):
            self._resolution = [resolution] * dimensionality
        else:
            if len(resolution) != dimensionality:
                raise ValueError(f"Resolution list length {len(resolution)} must match dimensionality {dimensionality}")
            self._resolution = resolution
        
        if self._bipolar:
            dims = [range(-res, res + 1) for res in self._resolution]
        else:
            dims = [range(0, res + 1) for res in self._resolution]
        
        lattice_graph = nx.grid_graph(dims, periodic=periodic)
        
        # Initialize Graph components manually since coordinate tuples aren't integers
        self._graph = lattice_graph
        self._meta = pd.DataFrame(index=[''])
        self._next_id = 0  # Not used since we use coordinate tuples as node IDs
    
    @property
    def dimensionality(self) -> int:
        """
        Number of dimensions in the lattice.
        
        Returns
        -------
        int
            The dimensionality of the lattice.
        """
        return self._dimensionality
    
    @property
    def resolution(self) -> List[int]:
        """
        Resolution along each dimension.
        
        Returns
        -------
        list of int
            Copy of the resolution list to prevent external modification.
        """
        return self._resolution.copy()
    
    @property
    def bipolar(self) -> bool:
        """
        Whether the lattice uses bipolar coordinates.
        
        Returns
        -------
        bool
            True if coordinates range from -resolution to +resolution,
            False if coordinates range from 0 to resolution.
        """
        return self._bipolar  
    
    def get_neighbors(self, coordinate: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        """
        Get the neighboring coordinates of a given coordinate.
        
        Parameters
        ----------
        coordinate : tuple of int
            The lattice coordinate.
            
        Returns
        -------
        list of tuple of int
            List of neighboring coordinates.
            
        Raises
        ------
        KeyError
            If coordinate is not in lattice.
        """
        if coordinate not in self.nodes:
            raise KeyError(f"Coordinate {coordinate} not in lattice")
        return list(self.graph.neighbors(coordinate))
    
    def coords(self) -> List[Tuple[int, ...]]:
        """
        Get all coordinates in the lattice.
        
        Returns
        -------
        list of tuple of int
            List of all lattice coordinates.
        """
        return list(self.nodes)    
    
    def __str__(self) -> str:
        """String representation of the lattice."""
        return (f"Lattice(dimensionality={self._dimensionality}, "
                f"resolution={self._resolution}, "
                f"bipolar={self._bipolar}, "
                f"coordinates={len(self.nodes)})")
    
    def __repr__(self) -> str:
        return self.__str__() 