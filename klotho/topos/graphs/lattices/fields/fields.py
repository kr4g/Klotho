from typing import Callable, Union, List, Tuple, Optional
import numpy as np
import pandas as pd
from ..lattices import Lattice


class Field(Lattice):
    """
    A field is a lattice with a function evaluated at each coordinate.
    
    Fields inherit all lattice functionality while providing field-specific
    methods for function evaluation and field manipulation. The function is
    evaluated lazily as coordinates are materialized in the lattice.
    
    Parameters
    ----------
    dimensionality : int
        Number of dimensions.
    resolution : int or list of int
        Number of points along each dimension, or list of resolutions per dimension.
    function : callable
        Function to evaluate at each coordinate. Should accept an array of shape
        (n_points, dimensionality) and return an array of shape (n_points,).
    ranges : tuple or list of tuple, optional
        Spatial range for each dimension. If tuple, applies to all dimensions.
        If list, must match dimensionality. Defaults to (-1, 1) per dimension.
    bipolar : bool, optional
        If True, coordinates range from -resolution to +resolution. 
        If False, coordinates range from 0 to resolution (default is True).
    periodic : bool, optional
        Whether to use periodic boundary conditions (default is False).
    """
    
    def __init__(self, 
                 dimensionality: int = 2, 
                 resolution: Union[int, List[int]] = 10, 
                 function: Callable[[np.ndarray], np.ndarray] = None,
                 ranges: Optional[Union[Tuple[float, float], List[Tuple[float, float]]]] = None,
                 bipolar: bool = True,
                 periodic: bool = False):
        
        if function is None:
            function = lambda x: np.zeros(x.shape[0])
        
        self._function = function
        
        if ranges is None:
            self._ranges = [(-1.0, 1.0)] * dimensionality
        elif isinstance(ranges, tuple) and len(ranges) == 2:
            self._ranges = [ranges] * dimensionality
        else:
            if len(ranges) != dimensionality:
                raise ValueError(f"Ranges list length {len(ranges)} must match dimensionality {dimensionality}")
            self._ranges = ranges
        
        super().__init__(dimensionality, resolution, bipolar, periodic)
        
        if not self._is_lazy:
            self._evaluate_all_coordinates()
    
    @property
    def function(self) -> Callable[[np.ndarray], np.ndarray]:
        """The function evaluated at each coordinate."""
        return self._function
    
    @property
    def ranges(self) -> List[Tuple[float, float]]:
        """Spatial ranges for each dimension."""
        return self._ranges.copy()
    
    def _coordinate_to_spatial_point(self, coord: Tuple[int, ...]) -> np.ndarray:
        """Convert a single integer lattice coordinate to spatial point."""
        spatial_point = []
        for i, c in enumerate(coord):
            if self._bipolar:
                coord_range = 2 * self._resolution[i]
                spatial_val = self._ranges[i][0] + (c + self._resolution[i]) * (self._ranges[i][1] - self._ranges[i][0]) / coord_range
            else:
                coord_range = self._resolution[i]
                spatial_val = self._ranges[i][0] + c * (self._ranges[i][1] - self._ranges[i][0]) / coord_range
            spatial_point.append(spatial_val)
        
        return np.array(spatial_point)
    
    def _coordinates_to_spatial_points(self, coords: List[Tuple[int, ...]]) -> np.ndarray:
        """Convert integer lattice coordinates to spatial points."""
        spatial_points = []
        
        for coord in coords:
            spatial_point = self._coordinate_to_spatial_point(coord)
            spatial_points.append(spatial_point)
        
        return np.array(spatial_points) if spatial_points else np.empty((0, self._dimensionality))
    
    def _evaluate_coordinates(self, coords: List[Tuple[int, ...]]):
        """Evaluate function at given coordinates and store values."""
        if not coords:
            return
        
        spatial_points = self._coordinates_to_spatial_points(coords)
        values = self._function(spatial_points)
        
        if np.isscalar(values):
            values = np.array([values])
        elif values.ndim == 0:
            values = np.array([values])
        
        for coord, value in zip(coords, values):
            node_id = self._coord_to_node[coord]
            current_data = self._graph.get_node_data(node_id) or {}
            current_data['field_value'] = float(value)
            self._graph[node_id] = current_data
    
    def _evaluate_all_coordinates(self):
        """Evaluate function at all existing coordinates."""
        coords = list(self._coord_to_node.keys())
        self._evaluate_coordinates(coords)
    
    def _materialize_coord(self, coord):
        """Override to evaluate function when materializing coordinates."""
        if not self._is_lazy or coord in self._materialized_coords:
            return
        
        coords_before = set(self._materialized_coords)
        super()._materialize_coord(coord)
        coords_after = set(self._materialized_coords)
        
        new_coords = list(coords_after - coords_before)
        if new_coords:
            self._evaluate_coordinates(new_coords)
    
    def get_field_value(self, coord: Tuple[int, ...]) -> float:
        """
        Get the field value at a specific coordinate.
        
        Parameters
        ----------
        coord : tuple of int
            The lattice coordinate.
            
        Returns
        -------
        float
            The field value at the coordinate.
        """
        node_id = self._get_node_for_coord(coord)
        if node_id is None:
            raise KeyError(f"Coordinate {coord} not found in field")
        
        node_data = self._graph.get_node_data(node_id) or {}
        return node_data.get('field_value', 0.0)
    
    def set_field_value(self, coord: Tuple[int, ...], value: float):
        """
        Set the field value at a specific coordinate.
        
        Parameters
        ----------
        coord : tuple of int
            The lattice coordinate.
        value : float
            The value to set.
        """
        node_id = self._get_node_for_coord(coord)
        if node_id is None:
            raise KeyError(f"Coordinate {coord} not found in field")
        
        current_data = self._graph.get_node_data(node_id) or {}
        current_data['field_value'] = float(value)
        self._graph[node_id] = current_data
    
    def apply_function(self, function: Callable[[np.ndarray], np.ndarray]):
        """
        Apply a new function to all lattice points, updating their values.
        
        Parameters
        ----------
        function : callable
            Function to evaluate at each coordinate. Should accept an array of shape
            (n_points, dimensionality) and return an array of shape (n_points,).
        """
        self._function = function
        
        if self._is_lazy:
            coords = list(self._materialized_coords)
        else:
            coords = list(self._coord_to_node.keys())
        
        self._evaluate_coordinates(coords)
    
    def sample_field(self, points: np.ndarray) -> np.ndarray:
        """
        Sample the field at arbitrary spatial points using interpolation.
        
        Parameters
        ----------
        points : numpy.ndarray
            Array of spatial points to sample, shape (n_points, dimensionality).
            
        Returns
        -------
        numpy.ndarray
            Array of interpolated field values.
        """
        from scipy.interpolate import griddata
        
        if self._is_lazy:
            coords = list(self._materialized_coords)
        else:
            coords = list(self._coord_to_node.keys())
        
        if not coords:
            return np.zeros(points.shape[0])
        
        spatial_points = self._coordinates_to_spatial_points(coords)
        field_values = np.array([self.get_field_value(coord) for coord in coords])
        
        return griddata(spatial_points, field_values, points, method='linear', fill_value=0.0)
    
    def gradient(self, coord: Tuple[int, ...]) -> np.ndarray:
        """
        Compute the gradient at a lattice coordinate using finite differences.
        
        Parameters
        ----------
        coord : tuple of int
            The lattice coordinate to compute gradient at.
            
        Returns
        -------
        numpy.ndarray
            Gradient vector at the coordinate.
        """
        gradient = np.zeros(self._dimensionality)
        neighbors = list(self.neighbors(coord))
        center_value = self.get_field_value(coord)
        
        for neighbor_coord in neighbors:
            direction = np.array(neighbor_coord) - np.array(coord)
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance
                value_diff = self.get_field_value(neighbor_coord) - center_value
                gradient += direction * value_diff / distance
        
        return gradient
    
    def laplacian(self, coord: Tuple[int, ...]) -> float:
        """
        Compute the Laplacian at a lattice coordinate using finite differences.
        
        Parameters
        ----------
        coord : tuple of int
            The lattice coordinate to compute Laplacian at.
            
        Returns
        -------
        float
            Laplacian value at the coordinate.
        """
        neighbors = list(self.neighbors(coord))
        center_value = self.get_field_value(coord)
        neighbor_sum = sum(self.get_field_value(neighbor) for neighbor in neighbors)
        
        return neighbor_sum - len(neighbors) * center_value
    
    def get_field_values(self) -> List[float]:
        """
        Get all field values in the same order as coords.
        
        Returns
        -------
        list of float
            List of field values.
        """
        coords = self.coords
        return [self.get_field_value(coord) for coord in coords]
    
    def __getitem__(self, key):
        """Allow field[coordinate] access to values for tuples, otherwise delegate to parent."""
        if isinstance(key, tuple):
            return self.get_field_value(key)
        return super().__getitem__(key)
    
    def __setitem__(self, key, value):
        """Allow field[coordinate] = value setting for tuples."""
        if isinstance(key, tuple):
            self.set_field_value(key, value)
        else:
            raise TypeError("Only tuple keys are supported for field coordinate access")
    
    @classmethod
    def from_lattice(cls, lattice: Lattice, 
                     function: Callable[[np.ndarray], np.ndarray],
                     ranges: Optional[Union[Tuple[float, float], List[Tuple[float, float]]]] = None) -> 'Field':
        """
        Create a Field from an existing Lattice.
        
        Parameters
        ----------
        lattice : Lattice
            The lattice to convert to a field.
        function : callable
            Function to evaluate at each lattice point.
        ranges : tuple or list of tuple, optional
            Spatial ranges for the field.
            
        Returns
        -------
        Field
            A new Field instance with the same structure.
        """
        field = cls.__new__(cls)
        
        field._dimensionality = lattice._dimensionality
        field._resolution = lattice._resolution.copy()
        field._bipolar = lattice._bipolar
        field._periodic = lattice._periodic
        field._dims = lattice._dims.copy()
        field._coord_to_node = lattice._coord_to_node.copy()
        field._node_to_coord = lattice._node_to_coord.copy()
        field._materialized_coords = lattice._materialized_coords.copy()
        field._estimated_size = lattice._estimated_size
        field._is_lazy = lattice._is_lazy
        field._function = function
        
        field._graph = lattice._graph.copy()
        field._meta = lattice._meta.copy() if hasattr(lattice, '_meta') else pd.DataFrame(index=[''])
        
        if ranges is None:
            field._ranges = [(-1.0, 1.0)] * field._dimensionality
        elif isinstance(ranges, tuple) and len(ranges) == 2:
            field._ranges = [ranges] * field._dimensionality
        else:
            if len(ranges) != field._dimensionality:
                raise ValueError(f"Ranges list length {len(ranges)} must match dimensionality {field._dimensionality}")
            field._ranges = ranges
        
        if field._is_lazy:
            coords = list(field._materialized_coords)
        else:
            coords = list(field._coord_to_node.keys())
        
        field._evaluate_coordinates(coords)
        
        return field
    
    def __str__(self) -> str:
        """String representation of the field."""
        if self._is_lazy:
            coord_count = f"{len(self._materialized_coords)} materialized"
        else:
            coord_count = str(len(self.coords))
        
        return (f"Field(dimensionality={self._dimensionality}, "
                f"resolution={self._resolution}, "
                f"bipolar={self._bipolar}, "
                f"coordinates={coord_count})")
    
    def __repr__(self) -> str:
        return self.__str__()