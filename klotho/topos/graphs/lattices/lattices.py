from typing import Tuple, List, Union
import pandas as pd
from ..graphs import Graph


class Lattice(Graph):
    """
    A generic n-dimensional lattice structure.
    
    A lattice provides a discrete sampling of n-dimensional space with integer
    coordinates. Nodes are accessed via coordinate tuples but stored internally
    as integer node IDs in the underlying RustworkX graph.
    
    Parameters
    ----------
    dimensionality : int
        Number of dimensions.
    resolution : int or list of int
        Number of points along each dimension, or list of resolutions per dimension.
    bipolar : bool, optional
        If True, coordinates range from -resolution to +resolution. 
        If False, coordinates range from 0 to resolution (default is True).
    periodic : bool, optional
        Whether to use periodic boundary conditions (default is False).
    """
    
    def __init__(self, 
                 dimensionality : int                   = 2, 
                 resolution     : Union[int, List[int]] = 10, 
                 bipolar        : bool                  = True,
                 periodic       : bool                  = False,
        ):
        
        self._dimensionality = dimensionality
        self._bipolar = bipolar
        self._periodic = periodic
        
        if isinstance(resolution, int):
            self._resolution = [resolution] * dimensionality
        else:
            if len(resolution) != dimensionality:
                raise ValueError(f"Resolution list length {len(resolution)} must match dimensionality {dimensionality}")
            self._resolution = resolution
        
        if self._bipolar:
            self._dims = [range(-res, res + 1) for res in self._resolution]
        else:
            self._dims = [range(0, res + 1) for res in self._resolution]
        
        self._coord_to_node = {}
        self._node_to_coord = {}
        self._materialized_coords = set()
        
        self._estimate_size()

        lattice_graph = Graph.grid_graph(self._dims, periodic=periodic)
        super().__init__()
        self._graph = lattice_graph._graph.copy()
        self._is_lazy = False
        self._build_coordinate_mapping()
        self._materialized_coords = set(self._coord_to_node.keys())
        
        self._meta = pd.DataFrame(index=[''])
    
    def _estimate_size(self):
        """Estimate total lattice size."""
        self._estimated_size = 1
        for res in self._resolution:
            size = (2 * res + 1) if self._bipolar else (res + 1)
            self._estimated_size *= size
            if self._estimated_size > 100_000:
                self._estimated_size = float('inf')
                break
    
    def _should_use_lazy(self):
        """Determine if lazy loading should be used."""
        return False
    
    def _seed_initial_coords(self):
        """Create initial coordinates for lazy lattice."""
        return
    
    def _build_coordinate_mapping(self):
        """Build coordinate mapping for non-lazy lattice."""
        import itertools
        
        for node_id in self._graph.node_indices():
            coord_data = self._graph.get_node_data(node_id)
            if coord_data and 'coord' in coord_data:
                coord = coord_data['coord']
                self._coord_to_node[coord] = node_id
                self._node_to_coord[node_id] = coord
    
    def _is_valid_coord(self, coord):
        """Check if a coordinate is valid for this lattice."""
        if not isinstance(coord, tuple) or len(coord) != self._dimensionality:
            return False
        
        for i, val in enumerate(coord):
            if val not in self._dims[i]:
                return False
        return True
    
    def _materialize_coord(self, coord):
        """Materialize a coordinate and its neighbors in lazy lattice."""
        if coord in self._materialized_coords:
            return
        if self._is_valid_coord(coord) and coord in self._coord_to_node:
            self._materialized_coords.add(coord)
    
    def _get_node_for_coord(self, coord):
        """Get node ID for coordinate, materializing if needed."""
        return self._coord_to_node.get(coord)
    
    def __getitem__(self, coord):
        """Get node data for a coordinate tuple."""
        node_id = self._get_node_for_coord(coord)
        if node_id is None:
            raise KeyError(f"Coordinate {coord} not found in lattice")
        return super().__getitem__(node_id)
    
    def __contains__(self, coord):
        """Check if a coordinate exists in the lattice."""
        if not self._is_valid_coord(coord):
            return False
        return coord in self._coord_to_node
    
    def get_coordinates(self, node_id):
        """Get coordinates for a given node ID."""
        if node_id in self._node_to_coord:
            return self._node_to_coord[node_id]
        else:
            raise KeyError(f"Node {node_id} not found in lattice")
    
    def get_node(self, coord):
        """Get node ID for given coordinates."""
        return self._get_node_for_coord(coord)
    
    @property
    def coords(self) -> List[Tuple[int, ...]]:
        """
        Get coordinates in the lattice.
        
        Returns
        -------
        list of tuple of int
            List of lattice coordinates.
        """
        return list(self._coord_to_node.keys())
    
    def _get_plot_coords(self, max_resolution: int) -> List[Tuple[int, ...]]:
        """
        Get coordinates for plotting, limited by max resolution from origin.
        
        Args:
            max_resolution: Maximum distance from origin in any dimension
            
        Returns:
            List of coordinate tuples within the resolution limit
        """
        import itertools
        
        if self._bipolar:
            plot_ranges = [range(-max_resolution, max_resolution + 1) for _ in range(self._dimensionality)]
        else:
            plot_ranges = [range(0, max_resolution + 1) for _ in range(self._dimensionality)]
        
        limited_ranges = []
        for plot_range, lattice_range in zip(plot_ranges, self._dims):
            limited_range = [val for val in plot_range if val in lattice_range]
            limited_ranges.append(limited_range)
        
        plot_coords = list(itertools.product(*limited_ranges))
        
        return plot_coords
    
    @property
    def edges(self):
        """Return a view of the edges with coordinate tuples."""
        return LatticeEdgeView(self)
    
    @property
    def dimensionality(self) -> int:
        """Number of dimensions in the lattice."""
        return self._dimensionality
    
    @property
    def resolution(self) -> List[int]:
        """Resolution along each dimension."""
        return self._resolution.copy()
    
    @property
    def bipolar(self) -> bool:
        """Whether the lattice uses bipolar coordinates."""
        return self._bipolar
    
    def number_of_nodes(self):
        """Return total number of nodes in lattice."""
        return super().number_of_nodes()
    
    def number_of_edges(self):
        """Return total number of edges in lattice."""
        return super().number_of_edges()
    
    def neighbors(self, coord):
        """Get neighbor coordinates of a coordinate."""
        node_id = self._get_node_for_coord(coord)
        if node_id is None:
            return []
        
        neighbor_nodes = super().neighbors(node_id)
        return [self._node_to_coord[n] for n in neighbor_nodes if n in self._node_to_coord]
    
    def add_edge(self, u, v, **attr):
        """Add edge between two coordinates."""
        u_node = self._get_node_for_coord(u)
        v_node = self._get_node_for_coord(v)
        
        if u_node is None or v_node is None:
            raise KeyError("One or both coordinates not found in lattice")
        
        super().add_edge(u_node, v_node, **attr)
    
    def has_edge(self, u, v):
        """Check if edge exists between two coordinates."""
        u_node = self._get_node_for_coord(u)
        v_node = self._get_node_for_coord(v)
        
        if u_node is None or v_node is None:
            return False
        
        return super().has_edge(u_node, v_node)
    
    def __str__(self) -> str:
        """String representation of the lattice."""
        coord_count = str(len(self.coords))
        
        return (f"Lattice(dimensionality={self._dimensionality}, "
                f"resolution={self._resolution}, "
                f"bipolar={self._bipolar}, "
                f"coordinates={coord_count})")
    
    def __repr__(self) -> str:
        return self.__str__()


class LatticeEdgeView:
    """View of lattice edges that returns coordinate tuples."""
    
    def __init__(self, lattice):
        self._lattice = lattice
    
    def __iter__(self):
        """Iterate over edges as coordinate tuple pairs."""
        for src_node, tgt_node in self._lattice._graph.edge_list():
            src_coord = self._lattice._node_to_coord.get(src_node)
            tgt_coord = self._lattice._node_to_coord.get(tgt_node)
            if src_coord is not None and tgt_coord is not None:
                yield (src_coord, tgt_coord)
    
    def __len__(self):
        """Return number of edges."""
        return self._lattice.number_of_edges()
    
    def __call__(self, data=False):
        """Return edges with optional data."""
        if data:
            for src_node, tgt_node in self._lattice._graph.edge_list():
                src_coord = self._lattice._node_to_coord.get(src_node)
                tgt_coord = self._lattice._node_to_coord.get(tgt_node)
                if src_coord is not None and tgt_coord is not None:
                    edge_data = self._lattice._graph.get_edge_data(src_node, tgt_node)
                    yield (src_coord, tgt_coord, edge_data if isinstance(edge_data, dict) else {})
        else:
            for src_coord, tgt_coord in self:
                yield (src_coord, tgt_coord)
