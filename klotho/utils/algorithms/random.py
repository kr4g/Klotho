import numpy as np
from typing import List, Union, Tuple, Any, Optional

def diverse_sample(elements: List[Any], 
                   num_samples: int, 
                   subset_size: Union[int, Tuple[int, int]], 
                   **kwargs) -> List[List[Any]]:
    """
    Generate diverse subsets from a master list using greedy algorithms.
    
    Creates multiple subsets from a master list where each subset maximizes
    diversity relative to previously selected subsets. Uses diversipy's
    greedy maximin algorithm for optimal distribution.

    Parameters
    ----------
    elements : list
        Master list of elements to sample from.
    num_samples : int
        Number of diverse subsets to generate.
    subset_size : int or tuple of int
        Size of each subset. If tuple (min, max), randomly selects
        size within range for each subset.
    **kwargs
        Additional configuration parameters passed to subset generation.

    Returns
    -------
    list of list
        Collection of diverse subsets, each containing elements from
        the master list.

    Raises
    ------
    ValueError
        If num_samples or subset_size parameters are invalid.
    ImportError
        If diversipy library is not available.

    Examples
    --------
    Generate diverse subsets with fixed size:
    
    >>> elements = ['A', 'B', 'C', 'D', 'E', 'F']
    >>> subsets = diverse_sample(elements, 3, 2)
    >>> len(subsets)
    3
    
    Generate subsets with variable sizes:
    
    >>> subsets = diverse_sample(elements, 2, (2, 4))
    >>> all(2 <= len(subset) <= 4 for subset in subsets)
    True
    """
    try:
        from diversipy import subset
    except ImportError:
        raise ImportError("diversipy library is required. Install with: pip install diversipy")
    
    if num_samples <= 0:
        raise ValueError("num_samples must be positive")
    
    if isinstance(subset_size, tuple):
        if len(subset_size) != 2 or subset_size[0] > subset_size[1]:
            raise ValueError("subset_size tuple must be (min, max) with min <= max")
        min_size, max_size = subset_size
    else:
        if subset_size <= 0:
            raise ValueError("subset_size must be positive")
        min_size = max_size = subset_size
    
    if max_size > len(elements):
        raise ValueError("Maximum subset_size cannot exceed length of elements")
    
    element_features = np.array([[i] for i in range(len(elements))])
    diverse_subsets = []
    selected_indices_history = []
    
    for i in range(num_samples):
        current_size = np.random.randint(min_size, max_size + 1) if min_size != max_size else min_size
        
        if i == 0:
            selected_indices = np.random.choice(len(elements), current_size, replace=False)
        else:
            existing_points = np.vstack([element_features[idx] for indices in selected_indices_history 
                                       for idx in indices])
            
            selected_points = subset.select_greedy_maximin(
                element_features, 
                current_size,
                existing_points=existing_points
            )
            selected_indices = [int(point[0]) for point in selected_points]
        
        selected_elements = [elements[idx] for idx in selected_indices]
        diverse_subsets.append(selected_elements)
        selected_indices_history.append(selected_indices)
    
    return diverse_subsets 