from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple, Callable, Iterator
import math

class Field(ABC):
    def __init__(self, 
                 space_points: Dict[Any, Dict[str, Any]], 
                 field_function: Callable[[Any], Any],
                 edge_criteria: Callable[[Any, Any, Any, Any], bool] = None,
                 value_difference: Callable[[Any, Any], Any] = None,
                 interaction_mechanism: Callable[['Field', 'Field', Any], Any] = None):
        '''
        Initialize a generic Field.

        :param space_points: Dictionary of points in space with their attributes
        :param field_function: Function to evaluate at each point
        :param edge_criteria: Function to determine if an edge should exist between two points
        :param value_difference: Function to compute the difference between two field values
        :param interaction_mechanism: Function to define how this field interacts with other fields
        '''
        self.nodes = {}
        self.edges = {}
        self.field_function = field_function
        self.edge_criteria = edge_criteria or self._default_edge_criteria
        self.value_difference = value_difference or self._default_value_difference
        self.interaction_mechanism = interaction_mechanism or self._default_interaction_mechanism

        for point, attrs in space_points.items():
            self.add_point(point, attrs)

        self._add_edges()

    def _default_edge_criteria(self, point1: Any, value1: Any, point2: Any, value2: Any) -> bool:
        '''Default criteria for adding an edge between two points.'''
        return True

    def _default_value_difference(self, value1: Any, value2: Any) -> Any:
        '''Default function to compute the difference between two field values.'''
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return value2 - value1
        else:
            return None

    def _default_interaction_mechanism(self, other_field: 'Field', point: Any) -> Any:
        '''Default function for field interaction. Returns the sum of field values if numeric, else None.'''
        value1 = self.get_field_value(point)
        value2 = other_field.get_field_value(point)
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return value1 + value2
        else:
            return None

    def _add_edges(self):
        '''Add edges to the graph based on the edge criteria.'''
        points = list(self.nodes.keys())
        for i, point1 in enumerate(points):
            for point2 in points[i+1:]:
                if self.edge_criteria(point1, 
                                      self.nodes[point1]['field_value'],
                                      point2, 
                                      self.nodes[point2]['field_value']):
                    self.add_edge(point1, point2)

    def add_point(self, point: Any, attributes: Dict[str, Any]):
        '''Add a new point to the field.'''
        attributes['field_value'] = self.field_function(point)
        self.nodes[point] = attributes
        self._update_edges_for_point(point)

    def remove_point(self, point: Any):
        '''Remove a point from the field.'''
        del self.nodes[point]
        if point in self.edges:
            del self.edges[point]
        for other_point in self.edges:
            self.edges[other_point].pop(point, None)

    def add_edge(self, point1: Any, point2: Any, **attributes):
        '''Add an edge between two points.'''
        if point1 not in self.edges:
            self.edges[point1] = {}
        if point2 not in self.edges:
            self.edges[point2] = {}
        self.edges[point1][point2] = attributes
        self.edges[point2][point1] = attributes

    def remove_edge(self, point1: Any, point2: Any):
        '''Remove an edge between two points.'''
        self.edges[point1].pop(point2, None)
        self.edges[point2].pop(point1, None)

    def get_field_value(self, point: Any) -> Any:
        '''Get the field value at a specific point.'''
        return self.nodes[point]['field_value']

    def set_field_value(self, point: Any, value: Any):
        '''Set the field value at a specific point.'''
        self.nodes[point]['field_value'] = value

    def get_neighbors(self, point: Any) -> Dict[Any, Dict[str, Any]]:
        '''Get the neighbors of a specific point.'''
        return {neighbor: self.nodes[neighbor] for neighbor in self.edges.get(point, {})}

    def update_field_function(self, new_function: Callable[[Any], Any]):
        '''Update the field function and recalculate all field values.'''
        self.field_function = new_function
        for point in self.nodes:
            self.set_field_value(point, self.field_function(point))
        self.edges.clear()
        self._add_edges()

    def update_edge_criteria(self, new_criteria: Callable[[Any, Any, Any, Any], bool]):
        '''Update the edge criteria and recalculate all edges.'''
        self.edge_criteria = new_criteria
        self.edges.clear()
        self._add_edges()

    def get_gradient(self, point: Any) -> Dict[Any, Any]:
        '''Calculate the gradient at a specific point.'''
        gradient = {}
        point_value = self.get_field_value(point)
        for neighbor in self.get_neighbors(point):
            neighbor_value = self.get_field_value(neighbor)
            gradient[neighbor] = self.value_difference(point_value, neighbor_value)
        return gradient

    def get_subfield(self, points: List[Any]) -> 'Field':
        '''Get a subfield containing only the specified points.'''
        subfield_points = {p: self.nodes[p].copy() for p in points if p in self.nodes}
        return type(self)(subfield_points, self.field_function, self.edge_criteria, self.value_difference, self.interaction_mechanism)

    def apply_field_operation(self, operation: Callable[[Any], Any]):
        '''Apply an operation to all field values.'''
        for point in self.nodes:
            self.set_field_value(point, operation(self.get_field_value(point)))

    @abstractmethod
    def combine_fields(self, other_field: 'Field', combination_function: Callable[[Any, Any], Any], 
                       domain: Any = None, metadata_combination: Callable[[Dict, Dict], Dict] = None) -> 'Field':
        '''
        Combine this field with another field using a specified combination function.

        :param other_field: The field to combine with this field
        :param combination_function: Function that defines how to combine field values
        :param domain: Optional. The domain over which to combine the fields. If None, use the union of both fields' domains
        :param metadata_combination: Optional. Function to combine metadata of points from both fields
        :return: A new Field representing the combination of the two fields
        '''
        if domain is None:
            domain = set(self.nodes.keys()) | set(other_field.nodes.keys())
        
        combined_points = {}
        for point in domain:
            value1 = self.get_field_value(point) if point in self.nodes else None
            value2 = other_field.get_field_value(point) if point in other_field.nodes else None
            combined_value = combination_function(value1, value2)
            
            metadata1 = self.nodes.get(point, {}).copy()
            metadata2 = other_field.nodes.get(point, {}).copy()
            metadata1.pop('field_value', None)
            metadata2.pop('field_value', None)
            
            if metadata_combination:
                combined_metadata = metadata_combination(metadata1, metadata2)
            else:
                combined_metadata = {**metadata1, **metadata2}
            
            combined_points[point] = {'field_value': combined_value, **combined_metadata}
        
        def new_field_function(p):
            return combined_points[p]['field_value'] if p in combined_points else None
        
        return type(self)(combined_points, new_field_function, self.edge_criteria, self.value_difference)


    def interact(self, other_field: 'Field') -> 'Field':
        '''
        Create a new field resulting from the interaction of this field with another field.
        
        :param other_field: The field to interact with
        :return: A new Field representing the result of the interaction
        '''
        interaction_points = {}
        all_points = set(self.nodes.keys()) | set(other_field.nodes.keys())
        
        for point in all_points:
            interaction_value = self.interaction_mechanism(self, other_field, point)
            interaction_points[point] = {'field_value': interaction_value}
        
        return type(self)(interaction_points, lambda p: interaction_points[p]['field_value'], 
                          self.edge_criteria, self.value_difference, self.interaction_mechanism)

    def propagate_interaction(self, other_field: 'Field', steps: int = 1):
        '''
        Propagate the interaction with another field over multiple steps.
        
        :param other_field: The field to interact with
        :param steps: Number of propagation steps
        '''
        for _ in range(steps):
            interaction_field = self.interact(other_field)
            self.nodes = interaction_field.nodes
            other_field.nodes = interaction_field.nodes

    def set_interaction_mechanism(self, mechanism: Callable[['Field', 'Field', Any], Any]):
        '''
        Set a new interaction mechanism for the field.

        :param mechanism: A function that takes two Field objects and a point, and returns the interaction result
        '''
        self.interaction_mechanism = mechanism

    @abstractmethod
    def interpolate(self, point: Any) -> Any:
        '''Interpolate the field value at a given point (which may not be a node).'''
        # Simple nearest neighbor interpolation
        nearest_point = min(self.nodes.keys(), key=lambda p: self._distance(p, point))
        return self.get_field_value(nearest_point)

    def extrapolate(self, point: Any) -> Any:
        '''Extrapolate the field value at a given point outside the current field domain.'''
        # Simple nearest neighbor extrapolation
        nearest_point = min(self.nodes.keys(), key=lambda p: self._distance(p, point))
        return self.get_field_value(nearest_point)

    @abstractmethod
    def get_boundary(self) -> List[Any]:
        '''Get the boundary points of the field.'''
        pass

    @abstractmethod
    def get_interior(self) -> List[Any]:
        '''Get the interior points of the field.'''
        pass

    def apply_boundary_condition(self, condition: Callable[[Any], Any]):
        '''Apply a boundary condition to the field.'''
        for point in self.get_boundary():
            self.set_field_value(point, condition(point))

    @abstractmethod
    def get_divergence(self, point: Any) -> Any:
        '''Calculate the divergence of the field at a given point.'''
        pass

    @abstractmethod
    def get_curl(self, point: Any) -> Any:
        '''Calculate the curl of the field at a given point.'''
        pass

    def iterate_points(self) -> Iterator[Tuple[Any, Any]]:
        '''Iterate over all points and their field values.'''
        for point, data in self.nodes.items():
            yield point, data['field_value']

    @abstractmethod
    def normalize(self):
        '''Normalize the field values.'''
        pass

    @abstractmethod
    def get_energy(self) -> float:
        '''Calculate the total energy of the field.'''
        pass

    @abstractmethod
    def get_flux(self, surface: List[Any]) -> Any:
        '''Calculate the flux of the field through a given surface.'''
        pass

    def apply_differential_operator(self, operator: Callable[[Dict[Any, Any]], Any]) -> 'Field':
        '''Apply a differential operator to the field.'''
        result_points = {}
        for point in self.nodes:
            neighborhood = self.get_neighbors(point)
            neighborhood[point] = self.nodes[point]
            result_points[point] = {'field_value': operator(neighborhood)}
        return type(self)(result_points, lambda p: result_points[p]['field_value'], 
                          self.edge_criteria, self.value_difference, self.interaction_mechanism)

    # @abstractmethod
    # def to_continuous(self) -> Callable[[Any], Any]:
    #     '''Convert the discrete field to a continuous function.'''
    #     pass

    # @abstractmethod
    # def from_continuous(self, func: Callable[[Any], Any], domain: List[Any]):
    #     '''Create a discrete field from a continuous function over a given domain.'''
    #     pass
    
    def __getitem__(self, point: Any) -> Any:
        '''Allow field[point] access to field values.'''
        return self.get_field_value(point)

    def __setitem__(self, point: Any, value: Any):
        '''Allow field[point] = value setting of field values.'''
        self.set_field_value(point, value)

    def _distance(self, point1: Any, point2: Any) -> float:
        '''Calculate the distance between two points.'''
        # Assuming points are tuples of coordinates
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(point1, point2)))

    def __add__(self, other: 'Field') -> 'Field':
        '''Implement field addition.'''
        return self.combine_fields(other, lambda x, y: x + y)

    def __sub__(self, other: 'Field') -> 'Field':
        '''Implement field subtraction.'''
        return self.combine_fields(other, lambda x, y: x - y)

    def __mul__(self, other: 'Field') -> 'Field':
        '''Implement field multiplication.'''
        return self.combine_fields(other, lambda x, y: x * y)

    def __truediv__(self, other: 'Field') -> 'Field':
        '''Implement field division.'''
        return self.combine_fields(other, lambda x, y: x / y if y != 0 else float('inf'))

    def __pow__(self, power: float) -> 'Field':
        '''Implement field exponentiation.'''
        return self.apply_field_operation(lambda x: x ** power)

    def __str__(self) -> str:
        '''String representation of the field.'''
        return f"Field(nodes={len(self.nodes)}, edges={sum(len(e) for e in self.edges.values())//2})"

    def __repr__(self) -> str:
        return self.__str__()