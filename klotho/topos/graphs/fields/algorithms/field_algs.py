from klotho.topos.graphs.fields import Field
import random

def find_navigation_path(field: Field, steps: int = 2000, seed: int = 42):
    """
    Generate a navigation path through the field.
    
    :param field: The Field object to navigate
    :param steps: Number of steps to take in the navigation
    :return: List of (point, value) tuples representing the path
    """
    random.seed(seed)
    start_point = random.choice(list(field.nodes.keys()))
    path = [(start_point, field[start_point])]
    visited = set([start_point])
    
    for _ in range(steps - 1):
        current_point = path[-1][0]
        neighbors = field.get_neighbors(current_point)
        unvisited_neighbors = [p for p in neighbors if p not in visited]
        
        if unvisited_neighbors:
            next_point = max(unvisited_neighbors, key=neighbors.get)
        elif neighbors:
            next_point = random.choice(list(neighbors.keys()))
        else:
            break
        
        path.append((next_point, field[next_point]))
        visited.add(next_point)
    
    return path