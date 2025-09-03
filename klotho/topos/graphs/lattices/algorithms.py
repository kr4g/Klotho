from typing import List, Tuple, Optional
import random
import rustworkx as rx
from .lattices import Lattice


def random_walk(lattice: Lattice, start_coord: Tuple[int, ...], num_steps: int, 
                max_repeats: Optional[int] = None, seed: Optional[int] = None,
                avoid_backtrack: bool = False) -> List[Tuple[int, ...]]:
    """
    Perform a random walk on a lattice starting from a given coordinate.
    
    Parameters
    ----------
    lattice : Lattice
        The lattice to perform the random walk on.
    start_coord : Tuple[int, ...]
        Starting coordinate for the random walk.
    num_steps : int
        Number of steps to take in the random walk.
    max_repeats : Optional[int]
        Maximum number of times any coordinate can be visited. If None, no limit.
    seed : Optional[int]
        Random seed for reproducible walks.
    avoid_backtrack : bool
        If True, avoid immediately returning to the previous coordinate when possible.
        
    Returns
    -------
    List[Tuple[int, ...]]
        List of coordinates representing the random walk path.
        
    Raises
    ------
    KeyError
        If start_coord is not valid in the lattice.
    ValueError
        If num_steps is negative.
    """
    if num_steps < 0:
        raise ValueError("num_steps must be non-negative")
    
    if start_coord not in lattice:
        raise KeyError(f"Start coordinate {start_coord} not found in lattice")
    
    if seed is not None:
        random.seed(seed)
    
    path = [start_coord]
    current_coord = start_coord
    visit_counts = {start_coord: 1}
    previous_coord = None
    
    for step in range(num_steps):
        neighbors = lattice.neighbors(current_coord)
        
        if not neighbors:
            break
        
        valid_neighbors = []
        for neighbor in neighbors:
            if max_repeats is not None:
                neighbor_visits = visit_counts.get(neighbor, 0)
                if neighbor_visits > max_repeats:
                    continue
            
            if avoid_backtrack and neighbor == previous_coord and len(neighbors) > 1:
                continue
                
            valid_neighbors.append(neighbor)
        
        if not valid_neighbors:
            if max_repeats is not None:
                valid_neighbors = [n for n in neighbors 
                                 if visit_counts.get(n, 0) <= max_repeats]
            
            if not valid_neighbors:
                break
        
        next_coord = random.choice(valid_neighbors)
        
        visit_counts[next_coord] = visit_counts.get(next_coord, 0) + 1
        path.append(next_coord)
        previous_coord = current_coord
        current_coord = next_coord
    
    return path


def directed_walk(lattice: Lattice, start_coord: Tuple[int, ...], direction_weights: List[float],
                  num_steps: int, max_repeats: Optional[int] = None, 
                  seed: Optional[int] = None) -> List[Tuple[int, ...]]:
    """
    Perform a biased random walk with directional preferences.
    
    Parameters
    ----------
    lattice : Lattice
        The lattice to perform the walk on.
    start_coord : Tuple[int, ...]
        Starting coordinate for the walk.
    direction_weights : List[float]
        Weights for each dimension direction. Length should be 2 * dimensionality,
        where indices [0, 1] are weights for dimension 0 [-1, +1], etc.
    num_steps : int
        Number of steps to take.
    max_repeats : Optional[int]
        Maximum visits per coordinate.
    seed : Optional[int]
        Random seed for reproducibility.
        
    Returns
    -------
    List[Tuple[int, ...]]
        List of coordinates representing the walk path.
    """
    if len(direction_weights) != 2 * lattice.dimensionality:
        raise ValueError(f"direction_weights length {len(direction_weights)} must be "
                        f"2 * dimensionality ({2 * lattice.dimensionality})")
    
    if start_coord not in lattice:
        raise KeyError(f"Start coordinate {start_coord} not found in lattice")
    
    if seed is not None:
        random.seed(seed)
    
    path = [start_coord]
    current_coord = start_coord
    visit_counts = {start_coord: 1}
    
    for step in range(num_steps):
        neighbors = lattice.neighbors(current_coord)
        
        if not neighbors:
            break
        
        neighbor_weights = []
        valid_neighbors = []
        
        for neighbor in neighbors:
            if max_repeats is not None:
                neighbor_visits = visit_counts.get(neighbor, 0)
                if neighbor_visits > max_repeats:
                    continue
            
            coord_diff = tuple(n - c for n, c in zip(neighbor, current_coord))
            
            weight = 1.0
            for dim_idx, diff in enumerate(coord_diff):
                if diff == 1:
                    weight *= direction_weights[dim_idx * 2 + 1]
                elif diff == -1:
                    weight *= direction_weights[dim_idx * 2]
            
            valid_neighbors.append(neighbor)
            neighbor_weights.append(weight)
        
        if not valid_neighbors:
            break
        
        if sum(neighbor_weights) == 0:
            next_coord = random.choice(valid_neighbors)
        else:
            next_coord = random.choices(valid_neighbors, weights=neighbor_weights)[0]
        
        visit_counts[next_coord] = visit_counts.get(next_coord, 0) + 1
        path.append(next_coord)
        current_coord = next_coord
    
    return path


def boundary_walk(lattice: Lattice, start_coord: Tuple[int, ...], num_steps: int,
                  boundary_preference: float = 0.7, seed: Optional[int] = None) -> List[Tuple[int, ...]]:
    """
    Perform a random walk with preference for boundary coordinates.
    
    Parameters
    ----------
    lattice : Lattice
        The lattice to perform the walk on.
    start_coord : Tuple[int, ...]
        Starting coordinate for the walk.
    num_steps : int
        Number of steps to take.
    boundary_preference : float
        Probability of choosing a boundary neighbor when available (0.0-1.0).
    seed : Optional[int]
        Random seed for reproducibility.
        
    Returns
    -------
    List[Tuple[int, ...]]
        List of coordinates representing the walk path.
    """
    if not 0.0 <= boundary_preference <= 1.0:
        raise ValueError("boundary_preference must be between 0.0 and 1.0")
    
    if start_coord not in lattice:
        raise KeyError(f"Start coordinate {start_coord} not found in lattice")
    
    if seed is not None:
        random.seed(seed)
    
    def is_boundary_coord(coord):
        """Check if a coordinate is on the lattice boundary."""
        for i, val in enumerate(coord):
            dim_range = lattice._dims[i]
            if val == min(dim_range) or val == max(dim_range):
                return True
        return False
    
    path = [start_coord]
    current_coord = start_coord
    
    for step in range(num_steps):
        neighbors = lattice.neighbors(current_coord)
        
        if not neighbors:
            break
        
        boundary_neighbors = [n for n in neighbors if is_boundary_coord(n)]
        interior_neighbors = [n for n in neighbors if not is_boundary_coord(n)]
        
        if boundary_neighbors and random.random() < boundary_preference:
            next_coord = random.choice(boundary_neighbors)
        elif interior_neighbors:
            next_coord = random.choice(interior_neighbors)
        else:
            next_coord = random.choice(neighbors)
        
        path.append(next_coord)
        current_coord = next_coord
    
    return path
