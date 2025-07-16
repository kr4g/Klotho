from typing import Tuple, List, Union
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
        
        lattice_graph = Graph.grid_graph(dims, periodic=periodic)
        
        # Create coordinate mapping for lattice nodes
        # RustworkX grid_graph creates integer indices, but we need coordinate tuples
        import itertools
        if self._bipolar:
            coord_ranges = [range(-res, res + 1) for res in self._resolution]
        else:
            coord_ranges = [range(0, res + 1) for res in self._resolution]
        
        # Generate all coordinate combinations
        all_coords = list(itertools.product(*coord_ranges))
        
        # Create a new Graph with coordinate tuples as nodes
        self._graph = lattice_graph._graph
        self._coord_to_index = {coord: i for i, coord in enumerate(all_coords)}
        self._index_to_coord = {i: coord for i, coord in enumerate(all_coords)}
        
        # Initialize Graph components
        self._meta = pd.DataFrame(index=[''])
        self._next_id = 0
    
    def _get_node_object(self, idx):
        """Override to return coordinate tuples instead of integer indices."""
        return self._index_to_coord.get(idx, idx)
    
    def _get_node_index(self, node):
        """Override to map coordinate tuples to integer indices."""
        if isinstance(node, tuple):
            return self._coord_to_index.get(node, node)
        return node
    
    @property
    def coords(self) -> List[Tuple[int, ...]]:
        """
        Get all coordinates in the lattice.
        
        Returns
        -------
        list of tuple of int
            List of all lattice coordinates.
        """
        return [self._get_node_object(idx) for idx in self._graph.node_indices()]
    
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
    
    def __str__(self) -> str:
        """String representation of the lattice."""
        return (f"Lattice(dimensionality={self._dimensionality}, "
                f"resolution={self._resolution}, "
                f"bipolar={self._bipolar}, "
                f"coordinates={len(self.coords)})")
    
    def __repr__(self) -> str:
        return self.__str__() 