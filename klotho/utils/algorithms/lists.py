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
        their sum equals 1.0. An all-zero input is returned as zeros of the
        same collection type -- there is nothing to scale. (Note the list and
        tuple paths rebuild from Python ``int`` zeros, so a list of floats
        comes back as a list of ints; only the ndarray path preserves dtype.)

    Raises
    ------
    ValueError
        If the values sum to zero while at least one of them is nonzero.
        No scalar can make such a collection sum to 1, so there is no
        answer to give.
    TypeError
        If input is not a list, tuple, or numpy array.

    Notes
    -----
    **A negative total is REFUSED** (ruling, 2026-09-02). Scaling by
    ``1 / total`` is the only linear map that makes the sum 1, so a negative
    total reflects every value through zero: ``[-1, -2, -3]`` would normalize
    to ``[1/6, 1/3, 1/2]``. Every pairwise proportion survives that flip
    exactly, so the answer is arithmetically defensible -- and it was kept on
    that ground until the consequence was measured.

    The consequence is why it is now refused. This function's one live caller
    (``klotho/topos/collections/sequences.py``) hands the result to numpy as a
    PROBABILITY VECTOR, and the flipped result **sums to 1**, so numpy accepts
    it without complaint and the caller silently receives a distribution
    weighted in reverse. Every other invalid input to that caller is loud one
    frame later, because numpy rejects a vector that does not sum to 1. The
    sign flip was the single input that turned a caller error into a plausible
    wrong result.

    If the signs carry meaning for you, normalize the magnitudes and reapply
    the signs yourself.

    Examples
    --------
    Normalize a list of integers:

    >>> normalize_sum([1, 2, 3, 4])
    [0.1, 0.2, 0.3, 0.4]

    Normalize a tuple of floats:

    >>> normalize_sum((1.5, 2.5, 1.0))
    (0.3, 0.5, 0.2)

    An all-zero collection is returned as is:

    >>> normalize_sum([0, 0, 0])
    [0, 0, 0]

    A negative total is refused rather than silently reflected:

    >>> normalize_sum([-1, -1])
    Traceback (most recent call last):
        ...
    ValueError: cannot normalize a collection whose values sum to a negative number: [-1, -1] sums to -2. Scaling by 1/total would make them sum to 1 by REFLECTING every value through zero, turning negative weights into positive ones. If the signs are meaningful, normalize the magnitudes and reapply the signs yourself.
    """
    if isinstance(data, (list, tuple)):
        total = sum(data)
        if total == 0:
            if any(x != 0 for x in data):
                raise ValueError(
                    "cannot normalize a collection that sums to zero while "
                    f"holding nonzero values: {list(data)!r}. No scalar makes "
                    "these sum to 1."
                )
            return type(data)([0] * len(data))
        if total < 0:
            raise ValueError(
                f"cannot normalize a collection whose values sum to a "
                f"negative number: {list(data)!r} sums to {total}. Scaling by "
                f"1/total would make them sum to 1 by REFLECTING every value "
                f"through zero, turning negative weights into positive ones. "
                f"If the signs are meaningful, normalize the magnitudes and "
                f"reapply the signs yourself."
            )
        normalized = [x / total for x in data]
        return type(data)(normalized)
    elif isinstance(data, np.ndarray):
        total = np.sum(data)
        if total == 0:
            if np.any(data != 0):
                raise ValueError(
                    "cannot normalize an array that sums to zero while "
                    "holding nonzero values. No scalar makes these sum to 1."
                )
            return np.zeros_like(data)
        if total < 0:
            raise ValueError(
                f"cannot normalize an array whose values sum to a negative "
                f"number ({total}). Scaling by 1/total would make them sum to "
                f"1 by REFLECTING every value through zero. If the signs are "
                f"meaningful, normalize the magnitudes and reapply the signs."
            )
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


def tile(data, n):
    """
    Repeat a collection end to end n times.

    Parameters
    ----------
    data : list, tuple, or numpy.ndarray
        Collection to repeat.
    n : int
        Number of repetitions. Must be non-negative.

    Returns
    -------
    list, tuple, or numpy.ndarray
        Collection of the same type as the input, repeated n times.

    Raises
    ------
    ValueError
        If n is negative.
    TypeError
        If data is not a list, tuple, or numpy array.

    Notes
    -----
    The return type matters when the result feeds a ``Pattern``. A list is
    structure -- ``Pattern`` cycles through it one element per step -- while a
    tuple is a single value emitted whole on every step (Klotho's convention
    for a simultaneity). ``tile`` preserves the input type, so pass a list to
    get a cycling pattern and a tuple to get one longer chord.

    Examples
    --------
    >>> tile([1, 2, 3], 2)
    [1, 2, 3, 1, 2, 3]

    >>> tile((1, 2), 3)
    (1, 2, 1, 2, 1, 2)

    >>> tile([1, 2], 0)
    []
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    if isinstance(data, (list, tuple)):
        return type(data)(list(data) * n)
    elif isinstance(data, np.ndarray):
        return np.tile(data, n)
    else:
        raise TypeError("Input must be list, tuple, or numpy array")
