__all__ = [
    'Group',
    'factor_children',
    'refactor_children',
    'get_signs',
    'get_abs',
    'rotate_children',
    'format_subdivisions',
]

def factor_children(subdivs:tuple) -> tuple:
    """Flatten a nested subdivision tuple into a flat tuple of leaf values.

    Recursively traverses *subdivs* and collects every non-tuple element
    in depth-first order.

    Parameters
    ----------
    subdivs : tuple
        Arbitrarily nested tuple of numeric leaf values.

    Returns
    -------
    tuple
        Flat tuple containing all leaf values in traversal order.

    Examples
    --------
    >>> factor_children((3, (2, 1), 4))
    (3, 2, 1, 4)
    """
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor_children(subdivs:tuple, factors:tuple) -> tuple:
    """Re-nest flat *factors* into the nested structure of *subdivs*.

    Walks *subdivs* depth-first and replaces each leaf position with the
    next value from *factors*, preserving the original nesting topology.

    Parameters
    ----------
    subdivs : tuple
        Nested tuple whose structure (but not leaf values) is preserved.
    factors : tuple
        Flat sequence of replacement leaf values.  Must contain exactly as
        many elements as there are leaves in *subdivs*.

    Returns
    -------
    tuple
        A new nested tuple with the same shape as *subdivs* but with leaf
        values taken sequentially from *factors*.

    Examples
    --------
    >>> refactor_children((3, (2, 1), 4), (10, 20, 30, 40))
    (10, (20, 30), 40)
    """
    def _refactor(subdivs, index):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                nested_result, index = _refactor(element, index)
                result.append(nested_result)
            else:
                result.append(factors[index])
                index += 1
        return tuple(result), index
    return _refactor(subdivs, 0)[0]

def get_signs(subdivs):
    """Extract the sign of each leaf value in a nested subdivision tuple.

    Parameters
    ----------
    subdivs : tuple
        Arbitrarily nested tuple of numeric values.

    Returns
    -------
    list of int
        Flat list of ``+1`` or ``-1`` for each leaf, in depth-first order.

    Examples
    --------
    >>> get_signs((3, (-2, 1), -4))
    [1, -1, 1, -1]
    """
    signs = []
    for element in subdivs:
        if isinstance(element, tuple):
            signs.extend(get_signs(element))
        else:
            signs.append(1 if element >= 0 else -1)
    return signs
    
def get_abs(subdivs):
    """Get the absolute values of all leaves in a nested subdivision tuple.

    Parameters
    ----------
    subdivs : tuple
        Arbitrarily nested tuple of numeric values.

    Returns
    -------
    list of int or float
        Flat list of absolute leaf values in depth-first order.

    Examples
    --------
    >>> get_abs((3, (-2, 1), -4))
    [3, 2, 1, 4]
    """
    result = []
    for element in subdivs:
        if isinstance(element, tuple):
            result.extend(get_abs(element))
        else:
            result.append(abs(element))
    return result

def rotate_children(subdivs: tuple, n: int = 1, preserve_signs: bool = False) -> tuple:
    """Rotate the leaf values of a nested subdivision tuple.

    Flattens the leaves, performs a left-rotation by *n* positions, and
    re-nests them into the original structure.  When *preserve_signs* is
    ``True``, only the absolute values are rotated while the original sign
    at each leaf position is retained.

    Parameters
    ----------
    subdivs : tuple
        Arbitrarily nested tuple of numeric values.
    n : int, optional
        Number of positions to rotate left (default is 1).
    preserve_signs : bool, optional
        If ``True``, rotate absolute values only and reapply the original
        signs at each position (default is ``False``).

    Returns
    -------
    tuple
        A new nested tuple with the same shape as *subdivs* and rotated
        leaf values.

    Examples
    --------
    >>> rotate_children((1, (2, 3), 4))
    (2, (3, 4), 1)

    >>> rotate_children((1, (-2, 3), -4), preserve_signs=True)
    (2, (-3, 4), -1)
    """
    if not preserve_signs:
        factors = factor_children(subdivs)
        n = n % len(factors)
        factors = factors[n:] + factors[:n]
        return refactor_children(subdivs, factors)
    
    signs = get_signs(subdivs)
    abs_values = get_abs(subdivs)
    
    n = n % len(abs_values)
    rotated_values = abs_values[n:] + abs_values[:n]
    
    signed_values = [val * sign for val, sign in zip(rotated_values, signs)]
    
    return refactor_children(subdivs, tuple(signed_values))

def format_subdivisions(subdivs):
    """Format a nested subdivision tuple as a human-readable string.

    Produces a parenthesised, space-separated representation (no commas)
    suitable for display.

    Parameters
    ----------
    subdivs : tuple or list or scalar
        Arbitrarily nested structure of numeric values.

    Returns
    -------
    str
        String representation, e.g. ``"(3 (2 1) 4)"``.

    Examples
    --------
    >>> format_subdivisions((3, (2, 1), 4))
    '(3 (2 1) 4)'
    """
    if isinstance(subdivs, (tuple, list)):
        inner = ' '.join(str(format_subdivisions(x)) for x in subdivs)
        return f"({inner})"
    return str(subdivs)


class Group(tuple):
    """Immutable ``(D, S)`` pair representing a rhythmic subdivision group.

    *D* is the top-level duration/divisor and *S* is a (possibly nested)
    tuple of subdivisions.  Nested tuples within *S* are recursively
    converted to ``Group`` instances, so the entire tree is typed
    throughout.

    Parameters
    ----------
    G : tuple
        A two-element tuple ``(D, S)`` where *D* is a numeric duration and
        *S* is a subdivision value or nested tuple of subdivisions.

    Examples
    --------
    >>> g = Group((4, (1, 2, 1)))
    >>> g.D
    4
    >>> g.S
    (1, 2, 1)
    """

    def __new__(cls, G):
        if isinstance(G, tuple):
            D = G[0]
            S = G[1]
            
            if isinstance(S, tuple):
                processed_S = []
                for item in S:
                    if isinstance(item, tuple):
                        processed_S.append(Group(item))
                    else:
                        processed_S.append(item)
                S = tuple(processed_S)
            
            G = (D, S)
        
        return super(Group, cls).__new__(cls, G)
    
    @property
    def D(self):
        return self[0]
    
    @property
    def S(self):
        return self[1]
    
    def __str__(self) -> str:
        return f"Group(({self.D} {format_subdivisions(self.S)}))"
    
    def __repr__(self) -> str:
        return self.__str__()
