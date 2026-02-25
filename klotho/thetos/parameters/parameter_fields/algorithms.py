"""
Navigation algorithms for traversing parameter fields.

This module provides path-generation utilities that trace oscillating
trajectories through a ``ParameterField``, producing sequences of
coordinate–value pairs.
"""

import random
import numpy as np
from typing import List, Tuple

def find_navigation_path(field, steps: int = 2000, frequency: float = 0.05) -> List[Tuple]:
    """
    Generate a navigation path through a parameter field.
    
    Traces a Lissajous-like oscillating trajectory through lattice space,
    snapping each point to its nearest lattice coordinate.
    
    Parameters
    ----------
    field : ParameterField
        The parameter field to navigate.
    steps : int, optional
        Number of steps to take in the navigation (default is 2000).
    frequency : float, optional
        Angular frequency of oscillation for path generation (default is 0.05).
        
    Returns
    -------
    list of tuple
        Each element is a ``(coordinate, value)`` pair representing one
        step along the path.
    """
    dimensions = field.dimensionality
    resolution = field.resolution
    path = []

    coordinates = field.coords()
    coord_array = np.array(coordinates)

    for t in range(steps):
        angle = frequency * t
        
        oscillating_point = np.zeros(dimensions)
        
        for i in range(dimensions):
            if field.bipolar:
                coord_range = 2 * resolution[i]
                center = 0
            else:
                coord_range = resolution[i]
                center = resolution[i] / 2
            
            if i == 0:
                oscillating_point[i] = center + 0.5 * coord_range * np.sin(angle) * np.cos(0.3 * angle)
            elif i == 1:
                oscillating_point[i] = center + 0.5 * coord_range * np.cos(1.5 * angle) * np.sin(0.4 * angle)
            else:
                oscillating_point[i] = center + 0.1 * coord_range * np.sin(angle / (i + 1))

        distances = np.linalg.norm(coord_array - oscillating_point, axis=1)
        nearest_index = np.argmin(distances)
        nearest_coordinate = coordinates[nearest_index]

        path.append((nearest_coordinate, field[nearest_coordinate]))

    return path
