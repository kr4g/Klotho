from typing import Callable, Union, List, Tuple, Optional
import numpy as np
from ..lattices import Lattice


class Field(Lattice):
    """
    A field is a specialized lattice that represents a function evaluated over space.
    
    Fields are n-dimensional lattices with continuous-valued functions evaluated
    at discrete lattice points. They inherit all lattice functionality while
    providing field-specific methods and semantics.
    
    Args:
        dimensionality: Number of spatial dimensions
        resolution: Number of points along each dimension
        function: Function to evaluate at each lattice point
        ranges: Spatial range for each dimension, defaults to (-1, 1) per dimension
        bipolar: If True, coordinates range from -resolution to +resolution
    """
    
    def __init__(self, 
                 dimensionality: int, 
                 resolution: Union[int, List[int]], 
                 function: Callable[[np.ndarray], np.ndarray],
                 ranges: Optional[Union[Tuple[float, float], List[Tuple[float, float]]]] = None,
                 bipolar: bool = True):
        
        super().__init__(dimensionality, resolution, bipolar)
        
        if ranges is None:
            self._ranges = [(-1.0, 1.0)] * dimensionality
        elif isinstance(ranges, tuple) and len(ranges) == 2:
            self._ranges = [ranges] * dimensionality
        else:
            if len(ranges) != dimensionality:
                raise ValueError(f"Ranges list length {len(ranges)} must match dimensionality {dimensionality}")
            self._ranges = ranges
        
        self.apply_function(function)
    
    @property
    def ranges(self) -> List[Tuple[float, float]]:
        """Spatial ranges for each dimension."""
        return self._ranges.copy()
    
    def apply_function(self, function: Callable[[np.ndarray], np.ndarray]):
        """Apply a function to all lattice points, updating their values."""
        spatial_points = self._coordinates_to_spatial_points()
        values = function(spatial_points)
        
        for coord, value in zip(self.coords(), values):
            self.set_node_attributes(coord, {'value': float(value)})
    
    def _coordinates_to_spatial_points(self) -> np.ndarray:
        """Convert integer lattice coordinates to spatial points."""
        coordinates = self.coords()
        spatial_points = []
        
        for coord in coordinates:
            spatial_point = []
            for i, c in enumerate(coord):
                if self.bipolar:
                    coord_range = 2 * self.resolution[i]
                    spatial_val = self._ranges[i][0] + (c + self.resolution[i]) * (self._ranges[i][1] - self._ranges[i][0]) / coord_range
                else:
                    coord_range = self.resolution[i]
                    spatial_val = self._ranges[i][0] + c * (self._ranges[i][1] - self._ranges[i][0]) / coord_range
                spatial_point.append(spatial_val)
            spatial_points.append(spatial_point)
        
        return np.array(spatial_points)
    
    def get_field_value(self, coordinate: Tuple[int, ...]) -> float:
        """Get the field value at a specific coordinate."""
        return super().__getitem__(coordinate)['value']
    
    def set_field_value(self, coordinate: Tuple[int, ...], value: float):
        """Set the field value at a specific coordinate."""
        self.set_node_attributes(coordinate, {'value': float(value)})
    
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
        
        spatial_points = self._coordinates_to_spatial_points()
        field_values = np.array([self.get_field_value(coord) for coord in self.coords()])
        
        return griddata(spatial_points, field_values, points, method='linear', fill_value=0.0)
    
    def gradient(self, coordinate: Tuple[int, ...]) -> np.ndarray:
        """
        Compute the gradient at a lattice coordinate using finite differences.
        
        Parameters
        ----------
        coordinate : tuple of int
            The lattice coordinate to compute gradient at.
            
        Returns
        -------
        numpy.ndarray
            Gradient vector at the coordinate.
        """
        gradient = np.zeros(self.dimensionality)
        neighbors = self.get_neighbors(coordinate)
        center_value = self.get_field_value(coordinate)
        
        for neighbor_coord in neighbors:
            direction = np.array(neighbor_coord) - np.array(coordinate)
            distance = np.linalg.norm(direction)
            if distance > 0:
                direction = direction / distance
                value_diff = self.get_field_value(neighbor_coord) - center_value
                gradient += direction * value_diff / distance
        
        return gradient
    
    def laplacian(self, coordinate: Tuple[int, ...]) -> float:
        """
        Compute the Laplacian at a lattice coordinate using finite differences.
        
        Parameters
        ----------
        coordinate : tuple of int
            The lattice coordinate to compute Laplacian at.
            
        Returns
        -------
        float
            Laplacian value at the coordinate.
        """
        neighbors = self.get_neighbors(coordinate)
        center_value = self.get_field_value(coordinate)
        neighbor_sum = sum(self.get_field_value(neighbor) for neighbor in neighbors)
        
        return neighbor_sum - len(neighbors) * center_value
    
    def __getitem__(self, key):
        """Allow field[coordinate] access to values for tuples, otherwise delegate to Graph."""
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
        field._coord_to_node = lattice._coord_to_node.copy()
        field._node_to_coord = lattice._node_to_coord.copy()
        field._graph = lattice._graph.copy()
        field._meta = lattice._meta.copy()
        field._next_id = lattice._next_id
        
        if ranges is None:
            field._ranges = [(-1.0, 1.0)] * field._dimensionality
        elif isinstance(ranges, tuple) and len(ranges) == 2:
            field._ranges = [ranges] * field._dimensionality
        else:
            if len(ranges) != field._dimensionality:
                raise ValueError(f"Ranges list length {len(ranges)} must match dimensionality {field._dimensionality}")
            field._ranges = ranges
        
        field.apply_function(function)
        return field 