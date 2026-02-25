from typing import Union, Tuple

__all__ = [
    'measure_partials',
]

def measure_partials(partials:Tuple[int], f:Union[int,float]=1):
    """
    Recursively compute absolute partial values from a nested partial specification.

    Supports both flat sequences of partials and nested ``(factor, sub_partials)``
    tuples for hierarchical harmonic structures.

    Parameters
    ----------
    partials : tuple
        Partial numbers. An element may be an ``int`` (or negative int for
        undertones) or a ``(factor, sub_partials)`` tuple for recursion.
    f : int or float, optional
        Cumulative multiplication factor from parent levels. Default is 1.

    Returns
    -------
    tuple
        Flat tuple of computed partial values.
    """
    result = []
    for s in partials:
        if isinstance(s, tuple):
            F, P = s
            result.extend(measure_partials(P, f * F))
        else:
            s = s if s > 0 else 1 / s
            result.append(f * s)
    return tuple(result)
