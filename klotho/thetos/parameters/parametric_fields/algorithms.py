import random
import numpy as np
from typing import List, Tuple

def find_navigation_path(field, steps: int = 2000, frequency: float = 0.05) -> List[Tuple]:
    """
    Generate a navigation path through the field.
    
    Args:
        field: The ParametricField object to navigate
        steps: Number of steps to take in the navigation
        frequency: Frequency of oscillation for path generation
        
    Returns:
        List of (coordinate, value) tuples representing the path
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
