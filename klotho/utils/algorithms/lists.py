import numpy as np

def normalize_sum(data):
    """
    Normalize values in a collection so their sum equals 1.
    
    Scale all values proportionally so that their sum equals 1.0 while
    preserving their relative proportions and original data type.

    Parameters
    ----------
    data : list, tuple, or numpy.ndarray
        Collection of numeric values to normalize. Can contain integers,
        floats, Fractions, Decimals, or other numeric types.

    Returns
    -------
    list, tuple, or numpy.ndarray
        Collection of the same type as input with values scaled so that
        their sum equals 1.0. If input sum is zero, returns collection
        of zeros with same shape and type.

    Raises
    ------
    TypeError
        If input is not a list, tuple, or numpy array.

    Examples
    --------
    Normalize a list of integers:
    
    >>> normalize_sum([1, 2, 3, 4])
    [0.1, 0.2, 0.3, 0.4]
    
    Normalize a tuple of floats:
    
    >>> normalize_sum((1.5, 2.5, 1.0))
    (0.3, 0.5, 0.2)
    
    Handle zero sum case:
    
    >>> normalize_sum([0, 0, 0])
    [0, 0, 0]
    """
    if isinstance(data, (list, tuple)):
        total = sum(data)
        if total == 0:
            return type(data)([0] * len(data))
        normalized = [x / total for x in data]
        return type(data)(normalized)
    elif isinstance(data, np.ndarray):
        total = np.sum(data)
        if total == 0:
            return np.zeros_like(data)
        return data / total
    else:
        raise TypeError("Input must be list, tuple, or numpy array")

def invert(data):
    """
    Invert the proportional ordering of values in a collection.
    
    Reorder values so that the largest becomes the smallest, the smallest
    becomes the largest, etc., while preserving positions and exact types.
    The ranking is inverted but all original values are preserved.

    Parameters
    ----------
    data : list, tuple, or numpy.ndarray
        Collection of numeric values to invert. Values can be any
        comparable numeric type (int, float, Fraction, etc.).

    Returns
    -------
    list, tuple, or numpy.ndarray
        Collection of the same type as input with values reordered so that
        proportional relationships are inverted. Original value types are
        preserved exactly.

    Raises
    ------
    TypeError
        If input is not a list, tuple, or numpy array.

    Examples
    --------
    Basic inversion example:
    
    >>> invert([5, 1, 3])
    [1, 5, 3]
    
    Four element example:
    
    >>> invert([0, 5, 1, 4])
    [5, 0, 4, 1]
    
    Handle duplicate values:
    
    >>> invert([1, 3, 1, 2, 3])
    [3, 1, 3, 2, 1]
    
    Single element remains unchanged:
    
    >>> invert([42])
    [42]
    """
    if isinstance(data, (list, tuple)):
        unique_values = sorted(set(data))
        inversion_map = dict(zip(unique_values, reversed(unique_values)))
        return type(data)([inversion_map[x] for x in data])
    elif isinstance(data, np.ndarray):
        unique_values = np.sort(np.unique(data))
        indices = np.searchsorted(unique_values, data)
        return unique_values[::-1][indices]
    else:
        raise TypeError("Input must be list, tuple, or numpy array")
