from typing import List, Callable, TypeVar, Any, Tuple
import numpy as np
import networkx as nx

T = TypeVar('T')

def cost_matrix(items: List[T], cost_function: Callable[[T, T], float], **kwargs: Any) -> Tuple[np.ndarray, List[T]]:
    """
    Generate a symmetric cost matrix for a collection of items.
    
    Create a numpy array representing pairwise costs between items using
    a provided cost function. The resulting matrix is symmetric with
    indices corresponding to item positions in the input list.

    Parameters
    ----------
    items : List[T]
        List of items to compute pairwise costs for. Items can be of any
        type that the cost function can handle.
    cost_function : Callable[[T, T], float]
        Function that takes two items and returns a numeric cost value.
        Should be symmetric (cost(a, b) == cost(b, a)) for best results.
    **kwargs : Any
        Additional keyword arguments to pass to the cost function.

    Returns
    -------
    Tuple[numpy.ndarray, List[T]]
        A tuple containing:
        - Symmetric cost matrix as numpy array where entry (i, j) 
          contains cost_function(items[i], items[j])
        - List of items in the same order as matrix indices

    Examples
    --------
    Create a distance matrix for 2D points:
    
    >>> import math
    >>> points = [(0, 0), (1, 1), (2, 0)]
    >>> def euclidean_distance(p1, p2):
    ...     return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    >>> matrix, item_list = cost_matrix(points, euclidean_distance)
    >>> print(matrix[0, 1])  # Distance from (0,0) to (1,1)
    1.4142135623730951
    """
    n = len(items)
    arr = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            arr[i, j] = cost_function(items[i], items[j], **kwargs)
    
    return arr, items

def cost_matrix_to_graph(cost_matrix: np.ndarray, items: List[T]) -> nx.Graph:
    """
    Convert a cost matrix numpy array to a weighted networkx graph.
    
    Transform a symmetric cost matrix into an undirected graph where
    edge weights represent the costs between nodes. Self-loops are
    excluded from the resulting graph.

    Parameters
    ----------
    cost_matrix : numpy.ndarray
        Symmetric cost matrix with numeric values. Should be square
        with dimensions matching the length of items.
    items : List[T]
        List of items corresponding to matrix indices. Used as node
        values in the resulting graph.

    Returns
    -------
    networkx.Graph
        Undirected graph with nodes corresponding to matrix indices
        and edge weights equal to the cost matrix values. Only edges
        with positive costs are included. Node attributes 'value' 
        contain the original items.

    Examples
    --------
    Convert a simple cost matrix to a graph:
    
    >>> import numpy as np
    >>> matrix = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
    >>> items = ['A', 'B', 'C']
    >>> graph = cost_matrix_to_graph(matrix, items)
    >>> list(graph.edges(data=True))
    [('A', 'B', {'weight': 1}), ('A', 'C', {'weight': 2}), ('B', 'C', {'weight': 3})]
    """
    G = nx.Graph()
    
    for i, item in enumerate(items):
        G.add_node(i, value=item)
    
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            cost = cost_matrix[i, j]
            if cost > 0:
                G.add_edge(i, j, weight=cost)
    
    return G
