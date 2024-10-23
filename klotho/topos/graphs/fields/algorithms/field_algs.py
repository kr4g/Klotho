from klotho.topos.graphs.fields import Field
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
#         neighbors = field.get_neighbors(current_point)
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

def find_navigation_path(field: Field, steps: int = 2000, frequency: float = 0.05) -> List[Tuple]:
    dimensions = field.dimensionality
    resolution = field.resolution
    path = []

    grid = np.meshgrid(*[np.arange(resolution) for _ in range(dimensions)])
    all_indices = np.stack([g.flatten() for g in grid], axis=-1)

    for t in range(steps):
        angle = frequency * t
        
        oscillating_point = np.zeros(dimensions)
        oscillating_point[0] = 0.5 * (1 + np.sin(angle) * np.cos(0.3 * angle)) * (resolution - 1)
        oscillating_point[1] = 0.5 * (1 + np.cos(1.5 * angle) * np.sin(0.4 * angle)) * (resolution - 1)
        
        for i in range(2, dimensions):
            oscillating_point[i] = 0.5 * (1 + 0.1 * np.sin(angle / (i + 1))) * (resolution - 1)

        distances = np.linalg.norm(all_indices - oscillating_point, axis=1)
        nearest_index = np.argmin(distances)
        nearest_point = tuple(all_indices[nearest_index])

        actual_point = tuple(field.nodes.keys())[nearest_index]
        path.append((actual_point, field[actual_point]))

    return path
