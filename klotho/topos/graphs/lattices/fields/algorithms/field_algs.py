import random

# def find_navigation_path(field: Field, steps: int = 2000, seed: int = 42):
#     """
#     Generate a navigation path through the field.
    
#     :param field: The Field object to navigate
#     :param steps: Number of steps to take in the navigation
#     :return: List of (point, value) tuples representing the path
#     """
#     random.seed(seed)
#     start_point = random.choice(list(field.nodes.keys()))
#     path = [(start_point, field[start_point])]
#     visited = set([start_point])
    
#     for _ in range(steps - 1):
#         current_point = path[-1][0]
#         neighbors = list(field.neighbors(current_point))
#         unvisited_neighbors = [p for p in neighbors if p not in visited]
        
#         if unvisited_neighbors:
#             next_point = max(unvisited_neighbors, key=neighbors.get)
#             # next_point = random.choice(unvisited_neighbors)
#         elif neighbors:
#             next_point = random.choice(list(neighbors.keys()))
#         else:
#             break
        
#         path.append((next_point, field[next_point]))
#         visited.add(next_point)
    
#     return path

import numpy as np
from typing import List, Tuple

def find_navigation_path(field, steps: int = 2000, frequency: float = 0.05) -> List[Tuple]:
    """
    Generate a navigation path through the field.
    
    Args:
        field: The Field object to navigate
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
