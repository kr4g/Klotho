from typing import List, Callable, Optional
import networkx as nx
from networkx.algorithms.approximation import greedy_tsp

def minimum_cost_path(
    G: nx.Graph,
    traversal_func: Optional[Callable] = None,
    **kwargs
) -> List[int]:
    """
    Find a minimum cost path through a weighted graph using flexible traversal functions.
    
    Delegates to the specified traversal function, providing sensible defaults
    for missing required parameters. The default traversal function is greedy_tsp
    which solves the traveling salesman problem.

    Parameters
    ----------
    G : networkx.Graph
        Weighted graph with numeric edge weights representing costs.
    traversal_func : Callable, optional
        Function to use for graph traversal. Receives the graph as first
        argument and all other parameters via kwargs. Defaults to greedy_tsp
        from networkx.
    **kwargs
        All parameters for the traversal function. If using the default
        greedy_tsp and 'source' is not provided, defaults to the first node.

    Returns
    -------
    List[int]
        Ordered list of node indices representing the path found by the
        traversal function.

    Raises
    ------
    ValueError
        If required nodes are not in the graph or if no valid path exists.

    Examples
    --------
    Use default greedy TSP with automatic source:
    
    >>> import networkx as nx
    >>> G = nx.Graph()
    >>> G.add_weighted_edges_from([(0, 1, 1), (1, 2, 2), (0, 2, 4)])
    >>> path = minimum_cost_path(G)  # Uses first node as source
    
    Use default greedy TSP with specified source:
    
    >>> path = minimum_cost_path(G, source=0)
    
    Use custom traversal function:
    
    >>> def custom_dfs(graph, source, depth_limit=None):
    ...     return list(nx.dfs_preorder_nodes(graph, source, depth_limit=depth_limit))
    >>> path = minimum_cost_path(G, traversal_func=custom_dfs, source=0, depth_limit=2)

    Notes
    -----
    This function provides maximum flexibility by accepting any traversal function
    and passing all parameters via kwargs. When no traversal function is specified,
    it uses NetworkX's greedy_tsp algorithm which finds an approximate solution
    to the traveling salesman problem.
    """
    if traversal_func is None:
        return greedy_tsp(G, **kwargs)
    
    return traversal_func(G, **kwargs)

import random
from typing import List, Optional

def greedy_random_walk(G, source, steps: int = 10, weight: str = 'weight', 
                      target: Optional[int] = None, **kwargs) -> List[int]:
    """
    Perform a greedy walk choosing minimum weight edges with random tie-breaking.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to walk on
    source : node
        Starting node
    steps : int, optional
        Maximum number of steps to take (default: 10)
    weight : str, optional
        Edge attribute to use for decision making (default: 'weight')
    target : node, optional
        If provided, stop early when target is reached
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Path as list of nodes visited
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    path = [source]
    current = source
    
    for step in range(steps):
        # Get all neighbors and their edge weights
        neighbors = list(G.neighbors(current))
        
        if not neighbors:
            # Dead end - nowhere to go
            break
            
        # Get weights for edges to all neighbors
        neighbor_weights = []
        for neighbor in neighbors:
            try:
                edge_weight = G[current][neighbor].get(weight, 1.0)
                neighbor_weights.append((neighbor, edge_weight))
            except (KeyError, TypeError):
                # If weight attribute doesn't exist, use default weight of 1.0
                neighbor_weights.append((neighbor, 1.0))
        
        # Find minimum weight
        min_weight = min(neighbor_weights, key=lambda x: x[1])[1]
        
        # Get all neighbors with minimum weight (for tie-breaking)
        min_weight_neighbors = [neighbor for neighbor, w in neighbor_weights if w == min_weight]
        
        # Choose randomly among tied minimum weight options
        next_node = random.choice(min_weight_neighbors)
        path.append(next_node)
        current = next_node
        
        # Stop early if we reached target
        if target is not None and current == target:
            break
    
    return path


def probabilistic_random_walk(G, source, steps: int = 10, weight: str = 'weight',
                             target: Optional[int] = None, inverse_weights: bool = True, 
                             **kwargs) -> List[int]:
    """
    Perform a probabilistic walk where lower weights have higher probability.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to walk on
    source : node
        Starting node
    steps : int, optional
        Maximum number of steps to take (default: 10)
    weight : str, optional
        Edge attribute to use for decision making (default: 'weight')
    target : node, optional
        If provided, stop early when target is reached
    inverse_weights : bool, optional
        If True, lower weights get higher probability (default: True)
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Path as list of nodes visited
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    path = [source]
    current = source
    
    for step in range(steps):
        neighbors = list(G.neighbors(current))
        
        if not neighbors:
            break
            
        # Get weights and calculate probabilities
        weights = []
        for neighbor in neighbors:
            try:
                edge_weight = G[current][neighbor].get(weight, 1.0)
                weights.append(edge_weight)
            except (KeyError, TypeError):
                weights.append(1.0)
        
        # Convert weights to probabilities
        if inverse_weights:
            # Lower weights = higher probability
            # Use 1/weight, but handle zero weights
            inv_weights = [1.0 / max(w, 1e-10) for w in weights]
            total = sum(inv_weights)
            probabilities = [w / total for w in inv_weights]
        else:
            # Higher weights = higher probability
            total = sum(weights)
            probabilities = [w / total for w in weights] if total > 0 else [1.0/len(weights)] * len(weights)
        
        # Choose based on probabilities
        next_node = random.choices(neighbors, weights=probabilities)[0]
        path.append(next_node)
        current = next_node
        
        if target is not None and current == target:
            break
    
    return path


def deterministic_greedy_walk(G, source, steps: int = 10, weight: str = 'weight',
                             target: Optional[int] = None, **kwargs) -> List[int]:
    """
    Always choose the neighbor with minimum weight (deterministic, no randomness).
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to walk on
    source : node
        Starting node
    steps : int, optional
        Maximum number of steps to take (default: 10)
    weight : str, optional
        Edge attribute to use for decision making (default: 'weight')
    target : node, optional
        If provided, stop early when target is reached
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Path as list of nodes visited
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    path = [source]
    current = source
    visited = set([source])  # Avoid cycles
    
    for step in range(steps):
        neighbors = [n for n in G.neighbors(current) if n not in visited]
        
        if not neighbors:
            # Try all neighbors if we're stuck
            neighbors = list(G.neighbors(current))
            if not neighbors:
                break
        
        # Find neighbor with minimum weight
        min_neighbor = None
        min_weight = float('inf')
        
        for neighbor in neighbors:
            try:
                edge_weight = G[current][neighbor].get(weight, 1.0)
                if edge_weight < min_weight:
                    min_weight = edge_weight
                    min_neighbor = neighbor
            except (KeyError, TypeError):
                if 1.0 < min_weight:
                    min_weight = 1.0
                    min_neighbor = neighbor
        
        if min_neighbor is None:
            break
            
        path.append(min_neighbor)
        current = min_neighbor
        visited.add(current)
        
        if target is not None and current == target:
            break
    
    return path