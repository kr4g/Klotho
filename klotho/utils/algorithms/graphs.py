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