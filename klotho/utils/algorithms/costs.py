from typing import List, Callable, TypeVar, Any, Tuple
import numpy as np

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


