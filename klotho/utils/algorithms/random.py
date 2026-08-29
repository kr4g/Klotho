import random as _random
import numpy as np
from typing import Any, List, Optional, Sequence, Tuple, Union

__all__ = ['diverse_sample', 'sample_with_replacement']


def _coerce_rng(seed):
    """Return a random source for ``seed`` (mirrors the graph/lattice walks)."""
    if seed is None or seed is _random:
        return _random
    if isinstance(seed, _random.Random):
        return seed
    return _random.Random(seed)


def sample_with_replacement(pool: Sequence[Any],
                            n: int,
                            seed=None,
                            weights: Optional[List[float]] = None) -> List[Any]:
    """
    Draw *n* items from *pool* independently, with replacement.

    The seeded i.i.d. draw the library was missing. It uses the stdlib
    generator rather than numpy on purpose: ``pool`` holds arbitrary Python
    objects -- ``Pitch``, ``Fraction``, tuples -- and ``numpy.random.choice``
    coerces those into object arrays and mangles anything sequence-shaped.

    Parameters
    ----------
    pool : sequence
        Items to draw from. Any Python objects.
    n : int
        Number of draws. Must be non-negative.
    seed : int, random.Random, or None, optional
        Seed for reproducibility. A seed gets its own generator, so it does
        not disturb the caller's global ``random`` stream; None draws from
        that stream.
    weights : list of float, optional
        Relative weight per pool item. Must match ``pool`` in length, be
        non-negative, and sum to something positive. When omitted the draw is
        uniform.

    Returns
    -------
    list
        ``n`` items, each drawn independently.

    Raises
    ------
    ValueError
        If ``n`` is negative, ``pool`` is empty, or ``weights`` is invalid.

    Examples
    --------
    >>> sample_with_replacement([60, 64, 67], 4, seed=42)  # doctest: +SKIP
    [64, 60, 64, 67]
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    pool = list(pool)
    if not pool:
        raise ValueError("pool must be non-empty")
    if weights is not None:
        weights = list(weights)
        if len(weights) != len(pool):
            raise ValueError("Length of weights must match length of pool")
        if any(w < 0 for w in weights):
            raise ValueError("weights must be non-negative")
        if sum(weights) <= 0:
            raise ValueError("weights must sum to a positive value")
    return _coerce_rng(seed).choices(pool, weights=weights, k=n)


def diverse_sample(elements: List[Any], 
                   num_samples: int, 
                   subset_size: Union[int, Tuple[int, int]], 
                   seed=None,
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
    seed : int, numpy.random.Generator, or None, optional
        Seed for reproducibility (anything ``numpy.random.default_rng``
        accepts). When None (default), draws from the global numpy stream.
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
        If the optional ``diversipy`` dependency is not installed. It ships
        as the ``sampling`` extra: ``pip install klotho-cac[sampling]``.

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
        raise ImportError(
            "diverse_sample needs the optional 'diversipy' dependency, which "
            "ships as Klotho's 'sampling' extra. Install it with "
            "`pip install klotho-cac[sampling]` (or `pip install diversipy`). "
            "Nothing else in Klotho requires it."
        ) from None
    
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
    
    rng = np.random if seed is None else np.random.default_rng(seed)
    _randint = rng.randint if seed is None else rng.integers

    element_features = np.array([[i] for i in range(len(elements))])
    diverse_subsets = []
    selected_indices_history = []
    
    for i in range(num_samples):
        current_size = int(_randint(min_size, max_size + 1)) if min_size != max_size else min_size
        
        if i == 0:
            selected_indices = rng.choice(len(elements), current_size, replace=False)
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