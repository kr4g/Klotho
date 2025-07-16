from typing import List, Callable, Optional
import random
from ...topos.graphs import Graph

__all__ = [
    'minimum_cost_path',
    'greedy_random_walk',
    'probabilistic_random_walk',
    'deterministic_greedy_walk',
    'prim_order_traversal',
    'greedy_nearest_unvisited',
    'dijkstra_order_traversal',
    'weighted_dfs_traversal'
]

def greedy_tsp(G: Graph, source=None, **kwargs) -> List[int]:
    """
    Simple greedy TSP approximation algorithm.
    
    Parameters
    ----------
    G : Graph
        Weighted graph
    source : node, optional
        Starting node. If None, uses first node.
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Approximate TSP tour
    """
    if not G.nodes:
        return []
    
    if source is None:
        source = next(iter(G.nodes))
    
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    unvisited = set(G.nodes) - {source}
    tour = [source]
    current = source
    
    while unvisited:
        min_weight = float('inf')
        next_node = None
        
        for node in unvisited:
            if G.has_edge(current, node):
                try:
                    weight = G[current][node].get('weight', 1.0)
                    if weight < min_weight:
                        min_weight = weight
                        next_node = node
                except (KeyError, TypeError):
                    if 1.0 < min_weight:
                        min_weight = 1.0
                        next_node = node
        
        if next_node is None:
            # No direct edge, find nearest unvisited node
            next_node = unvisited.pop()
        else:
            unvisited.remove(next_node)
        
        tour.append(next_node)
        current = next_node
    
    return tour

def minimum_cost_path(
    G: Graph,
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
    G : Graph
        Weighted graph with numeric edge weights representing costs.
    traversal_func : Callable, optional
        Function to use for graph traversal. Receives the graph as first
        argument and all other parameters via kwargs. Defaults to greedy_tsp.
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
    
    >>> from klotho.topos.graphs import Graph
    >>> G = Graph.digraph()
    >>> G.add_edge(0, 1, weight=1)
    >>> G.add_edge(1, 2, weight=2) 
    >>> G.add_edge(0, 2, weight=4)
    >>> path = minimum_cost_path(G)  # Uses first node as source
    
    Use default greedy TSP with specified source:
    
    >>> path = minimum_cost_path(G, source=0)
    
    Use custom traversal function:
    
    >>> def custom_dfs(graph, source, depth_limit=None):
    ...     return list(graph.descendants(source))[:depth_limit]
    >>> path = minimum_cost_path(G, traversal_func=custom_dfs, source=0, depth_limit=2)

    Notes
    -----
    This function provides maximum flexibility by accepting any traversal function
    and passing all parameters via kwargs. When no traversal function is specified,
    it uses a greedy TSP algorithm which finds an approximate solution
    to the traveling salesman problem.
    """
    if traversal_func is None:
        return greedy_tsp(G, **kwargs)
    
    return traversal_func(G, **kwargs)

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
        neighbors = list(G.neighbors(current))
        
        if not neighbors:
            break
            
        neighbor_weights = []
        for neighbor in neighbors:
            try:
                edge_weight = G[current][neighbor].get(weight, 1.0)
                neighbor_weights.append((neighbor, edge_weight))
            except (KeyError, TypeError):
                neighbor_weights.append((neighbor, 1.0))
        
        min_weight = min(neighbor_weights, key=lambda x: x[1])[1]
        
        min_weight_neighbors = [neighbor for neighbor, w in neighbor_weights if w == min_weight]
        
        next_node = random.choice(min_weight_neighbors)
        path.append(next_node)
        current = next_node
        
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
            
        weights = []
        for neighbor in neighbors:
            try:
                edge_weight = G[current][neighbor].get(weight, 1.0)
                weights.append(edge_weight)
            except (KeyError, TypeError):
                weights.append(1.0)
        
        if inverse_weights:
            inv_weights = [1.0 / max(w, 1e-10) for w in weights]
            total = sum(inv_weights)
            probabilities = [w / total for w in inv_weights]
        else:
            total = sum(weights)
            probabilities = [w / total for w in weights] if total > 0 else [1.0/len(weights)] * len(weights)
        
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
    visited = set([source])
    
    for step in range(steps):
        neighbors = [n for n in G.neighbors(current) if n not in visited]
        
        if not neighbors:
            neighbors = list(G.neighbors(current))
            if not neighbors:
                break
        
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

def prim_order_traversal(G, source, weight: str = 'weight', **kwargs) -> List[int]:
    """
    Visit all nodes in the order they would be added by Prim's MST algorithm.
    
    This guarantees visiting every node while prioritizing edges with lower weights.
    Follows the minimum spanning tree construction order.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to traverse
    source : node
        Starting node for traversal
    weight : str, optional
        Edge attribute to use for weights (default: 'weight')
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Nodes visited in Prim's algorithm order
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    visited = set([source])
    path = [source]
    
    while len(visited) < G.number_of_nodes():
        min_edge = None
        min_weight = float('inf')
        next_node = None
        
        for node in visited:
            for neighbor in G.neighbors(node):
                if neighbor not in visited:
                    try:
                        edge_weight = G[node][neighbor].get(weight, 1.0)
                        if edge_weight < min_weight:
                            min_weight = edge_weight
                            min_edge = (node, neighbor)
                            next_node = neighbor
                    except (KeyError, TypeError):
                        if 1.0 < min_weight:
                            min_weight = 1.0
                            min_edge = (node, neighbor)
                            next_node = neighbor
        
        if next_node is None:
            break
            
        visited.add(next_node)
        path.append(next_node)
    
    return path


def greedy_nearest_unvisited(G, source, weight: str = 'weight', **kwargs) -> List[int]:
    """
    Visit all nodes by always moving to the nearest unvisited neighbor.
    
    At each step, chooses the unvisited neighbor with the minimum edge weight.
    If no unvisited neighbors exist, backtracks or jumps to nearest unvisited node.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to traverse
    source : node
        Starting node for traversal
    weight : str, optional
        Edge attribute to use for weights (default: 'weight')
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Nodes visited in greedy nearest order
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    visited = set([source])
    path = [source]
    current = source
    
    while len(visited) < G.number_of_nodes():
        min_neighbor = None
        min_weight = float('inf')
        
        for neighbor in G.neighbors(current):
            if neighbor not in visited:
                try:
                    edge_weight = G[current][neighbor].get(weight, 1.0)
                    if edge_weight < min_weight:
                        min_weight = edge_weight
                        min_neighbor = neighbor
                except (KeyError, TypeError):
                    if 1.0 < min_weight:
                        min_weight = 1.0
                        min_neighbor = neighbor
        
        if min_neighbor is not None:
            visited.add(min_neighbor)
            path.append(min_neighbor)
            current = min_neighbor
        else:
            unvisited = set(G.nodes()) - visited
            if not unvisited:
                break
                
            min_distance = float('inf')
            best_next = None
            best_path_node = None
            
            for visited_node in visited:
                for unvisited_node in unvisited:
                    if G.has_edge(visited_node, unvisited_node):
                        try:
                            edge_weight = G[visited_node][unvisited_node].get(weight, 1.0)
                            if edge_weight < min_distance:
                                min_distance = edge_weight
                                best_next = unvisited_node
                                best_path_node = visited_node
                        except (KeyError, TypeError):
                            if 1.0 < min_distance:
                                min_distance = 1.0
                                best_next = unvisited_node
                                best_path_node = visited_node
            
            if best_next is not None:
                current = best_path_node
                visited.add(best_next)
                path.append(best_next)
                current = best_next
            else:
                break
    
    return path


def dijkstra_order_traversal(G, source, weight: str = 'weight', **kwargs) -> List[int]:
    """
    Visit all nodes in order of their distance from source (Dijkstra-style).
    
    Visits nodes in order of increasing shortest path distance from the source,
    guaranteeing that all reachable nodes are visited.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to traverse
    source : node
        Starting node for traversal
    weight : str, optional
        Edge attribute to use for weights (default: 'weight')
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Nodes visited in order of distance from source
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    import heapq
    
    distances = {node: float('inf') for node in G.nodes()}
    distances[source] = 0
    visited = set()
    path = []
    heap = [(0, source)]
    
    while heap and len(visited) < G.number_of_nodes():
        current_dist, current_node = heapq.heappop(heap)
        
        if current_node in visited:
            continue
            
        visited.add(current_node)
        path.append(current_node)
        
        for neighbor in G.neighbors(current_node):
            if neighbor not in visited:
                try:
                    edge_weight = G[current_node][neighbor].get(weight, 1.0)
                    new_distance = current_dist + edge_weight
                    
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        heapq.heappush(heap, (new_distance, neighbor))
                except (KeyError, TypeError):
                    new_distance = current_dist + 1.0
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        heapq.heappush(heap, (new_distance, neighbor))
    
    return path


def weighted_dfs_traversal(G, source, weight: str = 'weight', **kwargs) -> List[int]:
    """
    Depth-first traversal that prioritizes edges with lower weights.
    
    At each node, explores neighbors in order of increasing edge weight,
    ensuring all reachable nodes are visited.
    
    Parameters
    ----------
    G : networkx.Graph
        The graph to traverse
    source : node
        Starting node for traversal
    weight : str, optional
        Edge attribute to use for weights (default: 'weight')
    **kwargs
        Additional parameters (ignored)
        
    Returns
    -------
    List[int]
        Nodes visited in weighted DFS order
    """
    if source not in G:
        raise ValueError(f"Source node {source} not in graph")
    
    visited = set()
    path = []
    
    def weighted_dfs_visit(node):
        if node in visited:
            return
            
        visited.add(node)
        path.append(node)
        
        neighbors_with_weights = []
        for neighbor in G.neighbors(node):
            if neighbor not in visited:
                try:
                    edge_weight = G[node][neighbor].get(weight, 1.0)
                    neighbors_with_weights.append((edge_weight, neighbor))
                except (KeyError, TypeError):
                    neighbors_with_weights.append((1.0, neighbor))
        
        neighbors_with_weights.sort(key=lambda x: x[0])
        
        for _, neighbor in neighbors_with_weights:
            weighted_dfs_visit(neighbor)
    
    weighted_dfs_visit(source)
    
    unvisited = set(G.nodes()) - visited
    for remaining_node in unvisited:
        weighted_dfs_visit(remaining_node)
    
    return path