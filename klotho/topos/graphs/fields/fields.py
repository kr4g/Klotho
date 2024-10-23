from typing import Callable, Tuple, List, Dict
import numpy as np

class Field:
    def __init__(self, dimensionality: int, resolution: int, function: Callable[[np.ndarray], np.ndarray]):
        '''
        Initialize a Field.

        :param dimensionality: Number of dimensions for the field
        :param resolution: Number of points along each dimension
        :param function: Function to evaluate at each point
        '''
        self.dimensionality = dimensionality
        self.resolution = resolution
        self.nodes = {}
        self.edges = {}

        axes = [np.linspace(-1, 1, resolution) for _ in range(dimensionality)]
        grid = np.meshgrid(*axes)
        points = np.stack([ax.flatten() for ax in grid], axis=-1)

        if function is not None:
            values = function(points)
        else:
            values = np.zeros(resolution**dimensionality)
        # values = function(points)

        self.nodes = {tuple(point): float(value) for point, value in zip(points, values)}

        self._add_edges()

    def _add_edges(self):
        '''Add edges to form a grid with diagonals.'''
        points = list(self.nodes.keys())
        for i, point in enumerate(points):
            neighbors = self._get_neighbor_indices(i)
            for neighbor_idx in neighbors:
                if 0 <= neighbor_idx < len(points):
                    neighbor = points[neighbor_idx]
                    self.add_edge(point, neighbor)

    def _get_neighbor_indices(self, index: int) -> List[int]:
        '''Get the indices of neighboring points in n-dimensional space.'''
        coords = np.unravel_index(index, [self.resolution] * self.dimensionality)
        offsets = np.array(list(np.ndindex((3,) * self.dimensionality))) - 1
        neighbor_coords = np.array(coords) + offsets
        valid_coords = np.all((0 <= neighbor_coords) & (neighbor_coords < self.resolution), axis=1)
        return np.ravel_multi_index(neighbor_coords[valid_coords].T, [self.resolution] * self.dimensionality)

    def add_edge(self, point1: Tuple, point2: Tuple):
        '''Add an edge between two points.'''
        if point1 not in self.edges:
            self.edges[point1] = set()
        if point2 not in self.edges:
            self.edges[point2] = set()
        self.edges[point1].add(point2)
        self.edges[point2].add(point1)

    def get_field_value(self, point: Tuple) -> float:
        '''Get the field value at a specific point.'''
        return self.nodes[point]

    def get_neighbors(self, point: Tuple) -> Dict[Tuple, float]:
        '''Get the neighbors of a specific point.'''
        return {neighbor: self.nodes[neighbor] for neighbor in self.edges.get(point, set())}

    def __getitem__(self, point: Tuple) -> float:
        '''Allow field[point] access to field values.'''
        return self.get_field_value(point)

    def __setitem__(self, point: Tuple, value: float):
        '''Allow field[point] = value setting of field values.'''
        self.nodes[point] = value

    @classmethod
    def interact(cls, field1: 'Field', field2: 'Field', interaction_function: Callable[[float, float], float]) -> 'Field':
        '''
        Create a new field by interacting two existing fields.

        :param field1: First Field instance
        :param field2: Second Field instance
        :param interaction_function: Function that takes two field values and returns a new value
        :return: A new Field instance resulting from the interaction
        '''
        if field1.dimensionality != field2.dimensionality or field1.resolution != field2.resolution:
            raise ValueError("The two fields must have the same dimensionality and resolution")

        if set(field1.nodes.keys()) != set(field2.nodes.keys()):
            raise ValueError("The two fields must have the same space points")

        new_field = cls(field1.dimensionality, field1.resolution, None)
        
        # new_field.nodes = {
        #     point: interaction_function(field1[point], field2[point])
        #     for point in field1.nodes.keys()
        # }
        new_field.nodes = {
            point: interaction_function(field1, field2, point)
            for point in field1.nodes.keys()
        }

        new_field.edges = field1.edges.copy()

        return new_field

    def __str__(self) -> str:
        '''String representation of the field.'''
        return f"Field(dimensionality={self.dimensionality}, resolution={self.resolution}, nodes={len(self.nodes)}, edges={sum(len(e) for e in self.edges.values())//2})"

    def __repr__(self) -> str:
        return self.__str__()
    
import pickle

def save_field(field: Field, filename: str):
    """
    Save a Field instance to a file using pickle.
    
    Args:
    field (Field): The Field instance to save.
    filename (str): The name of the file to save the field to.
    """
    with open(filename, 'wb') as f:
        pickle.dump(field, f)
    print(f"Field saved to {filename}")

def load_field(filename: str) -> Field:
    """
    Load a Field instance from a file using pickle.
    
    Args:
    filename (str): The name of the file to load the field from.
    
    Returns:
    Field: The loaded Field instance.
    """
    with open(filename, 'rb') as f:
        field = pickle.load(f)
    print(f"Field loaded from {filename}")
    return field