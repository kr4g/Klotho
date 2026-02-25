# ------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_trees/algorithms/subdivs.py
# ------------------------------------------------------------------------
"""
Rhythm tree algorithms.

Algorithms that operate on either the S part of a rhythmic tree or its
corresponding proportions.

Pseudocode for numbered algorithms by Karim Haddad unless otherwise noted.

    "Let us recall that the mentioned part corresponds to the S part of a
    rhythmic tree composed of (DS), that is its part constituting the
    proportions which can also encompass other tree structures."
    -- Karim Haddad
"""
from typing import Tuple
from fractions import Fraction
from math import gcd, lcm, prod
from functools import reduce
import numpy as np
from typing import Union

# Algorithm 1: MeasureRatios
def measure_ratios(subdivs:tuple[int]) -> Tuple[Fraction]:
    """
    Transform the subdivisions of a rhythm tree into fractional proportions.

    Algorithm 1 (MeasureRatios) from Karim Haddad. Recursively converts
    the S part of a rhythm tree ``(D S)`` into a flat sequence of
    :class:`~fractions.Fraction` values representing each leaf's proportion
    of the whole.

    Parameters
    ----------
    subdivs : tuple of int or tuple
        The subdivision part (S) of a rhythm tree. Elements may be plain
        integers or nested ``(D, S)`` tuples for sub-trees.

    Returns
    -------
    tuple of Fraction
        The fractional proportions for every leaf of the tree.

    Examples
    --------
    >>> measure_ratios((1, 1, 1))
    (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3))
    """
    # div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivs)
    div = sum_proportions(subdivs)
    result = []
    for s in subdivs:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(D, div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return tuple(result)

# Algorithm 2: ReducedDecomposition
def reduced_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
    """
    Reduce proportions relative to a time signature (Tempus).

    Algorithm 2 (ReducedDecomposition) from Karim Haddad. Scales each
    fraction by the Tempus to obtain proportions in the measure's
    coordinate system.

    Parameters
    ----------
    lst : tuple of Fraction
        The list of proportions (typically from :func:`measure_ratios`).
    meas : Fraction
        The Tempus (time signature as a fraction).

    Returns
    -------
    tuple of Fraction
        The reduced proportions.
    """
    return tuple(Fraction(f.numerator * meas.numerator, f.denominator * meas.denominator) for f in lst)

# Algorithm 3: StrictDecomposition
def strict_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
    """
    Decompose proportions into a common-denominator form.

    Algorithm 3 (StrictDecomposition) from Karim Haddad. Normalizes a list
    of proportions so that they share a common denominator, making them
    directly comparable as integer ratios.

    Parameters
    ----------
    lst : tuple of Fraction
        The list of proportions (typically from :func:`measure_ratios`).
    meas : Fraction
        The Tempus (time signature as a fraction).

    Returns
    -------
    tuple of Fraction
        Proportions with a common denominator.
    """
    pgcd = reduce(gcd, (ratio.numerator for ratio in lst))
    pgcd_denom = reduce(lcm, (ratio.denominator for ratio in lst))
    return tuple(Fraction((f / pgcd) * meas.numerator, pgcd_denom) for f in lst)

# ------------------------------------------------------------------------------------

def ratios_to_subdivs(ratios:tuple[Fraction]) -> tuple[int]:
    """
    Convert a sequence of fractional ratios to integer subdivisions.

    Finds a common denominator, scales all fractions to integers, and
    divides by the overall GCD to obtain the simplest integer proportions.

    Parameters
    ----------
    ratios : tuple of Fraction
        The fractional ratios to convert.

    Returns
    -------
    tuple of int
        The equivalent integer subdivisions in lowest terms.
    """
    common_denom = reduce(lcm, (abs(f.denominator) for f in ratios), 1)
    ints = [int(f * common_denom) for f in ratios]
    overall_gcd = reduce(gcd, ints)
    return tuple(x // overall_gcd for x in ints)

# ------------------------------------------------------------------------------------

def auto_subdiv(subdivs:tuple[int], n:int=1) -> tuple[tuple[int]]:
    """
    Automatically subdivide each element of S using a rotational scheme.

    Each element in the subdivision tuple is expanded into a nested
    ``(D, S)`` pair, where D is the original element and S is a uniform
    tuple whose length is determined by a rotationally offset element.

    Parameters
    ----------
    subdivs : tuple of int
        The subdivision part (S) of a rhythm tree.
    n : int, optional
        The rotation offset used to select the subdivision count for
        each element. Default is 1.

    Returns
    -------
    tuple of tuple
        Nested ``(D, S)`` pairs for each element.
    """
    def _recurse(idx:int) -> tuple:
        if idx == len(subdivs):
            return ()
        elt = subdivs[idx]
        next_elt = (elt, (1,) * subdivs[(idx + n) % len(subdivs)])
        return (next_elt,) + _recurse(idx + 1)
    return _recurse(0)

def auto_subdiv_matrix(matrix, rotation_offset=1):
    """
    Apply :func:`auto_subdiv` to every element in a matrix of tree specs.

    Each element of the matrix is a ``(D, S)`` pair. The function applies
    ``auto_subdiv`` to each element's subdivisions with a rotation offset
    that varies with the element's row and column position.

    Parameters
    ----------
    matrix : tuple of tuple
        A matrix where each element is a ``(D, S)`` pair.
    rotation_offset : int, optional
        Base offset for rotation calculations. Default is 1.

    Returns
    -------
    tuple of tuple
        A new matrix with ``auto_subdiv`` applied to each element.
    """
    result = []
    for i, row in enumerate(matrix):
        new_row = []
        for j, e in enumerate(row):
            offset = rotation_offset * i
            D, S = e[0], auto_subdiv(e[1], j - i + offset)
            new_row.append((D, S))
        result.append(tuple(new_row))
    return tuple(result)

def rhythm_pair(lst:Tuple, MM:bool=True) -> Tuple:
    """
    Generate a rhythmic sequence from the superimposition of pulse grids.

    Given a tuple of integers, this function creates evenly spaced pulse
    grids (one per element), merges them, and returns the inter-onset
    intervals. The ``MM`` flag controls whether grids are spaced by
    ``total_product // x`` (metric modulation mode) or by ``x`` directly.

    Parameters
    ----------
    lst : tuple of int
        The integers defining each pulse grid.
    MM : bool, optional
        If True, use metric modulation spacing. Default is True.

    Returns
    -------
    tuple of int
        The inter-onset intervals of the combined grid.
    """
    total_product = prod(lst)
    if MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(int(x) for x in deltas)

def segment(ratio: Union[Fraction, float, str]) -> tuple[int]:
    """
    Segment a ratio into a pair of complementary integers.

    Converts the ratio to a :class:`~fractions.Fraction` and returns
    ``(numerator, denominator - numerator)``. The ratio must be less
    than 1.

    Parameters
    ----------
    ratio : Fraction, float, or str
        The ratio to segment (must be < 1).

    Returns
    -------
    tuple of int
        A pair ``(numerator, denominator - numerator)``.

    Raises
    ------
    ValueError
        If the ratio is >= 1.
    """
    ratio = Fraction(ratio)
    if ratio >= 1:
        raise ValueError("Ratio must be less than 1")
    return (ratio.numerator, ratio.denominator - ratio.numerator)

# ------------------------------------------------------------------------------------

def sum_proportions(S:tuple) -> int:
    """
    Sum the absolute values of the top-level proportions of a subdivision.

    For nested ``(D, S)`` elements, only the absolute value of ``D`` is
    used. For plain integers, the absolute value is summed directly.

    Parameters
    ----------
    S : tuple
        The subdivision part of a rhythm tree.

    Returns
    -------
    int
        The sum of absolute top-level proportions.
    """
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in S)

def measure_complexity(subdivs:tuple) -> bool:
    """
    Determine whether a subdivision structure contains complex (non-binary) rhythms.

    Recursively traverses the tree. For any nested ``(D, S)`` element,
    if the sum of S is not a power of two and does not equal D, the
    rhythm is considered complex.

    Parameters
    ----------
    subdivs : tuple
        The subdivision part of a rhythm tree.

    Returns
    -------
    bool
        True if the tree contains complex (non-binary) rhythms.
    """
    for s in subdivs:
        if isinstance(s, tuple):
            D, S = s
            div = sum_proportions(S)
            # XXX - only works for binary meters!!!
            if bin(div).count("1") != 1 and div != D:
                return True
            else:
                return measure_complexity(S)
    return False

def clean_subdivs(subdivs:tuple) -> tuple:
    """
    Clean and normalize a subdivision tuple.

    .. note::
       Not yet implemented.

    Parameters
    ----------
    subdivs : tuple
        The subdivision part of a rhythm tree.

    Returns
    -------
    tuple
        The cleaned subdivision tuple.
    """
    pass

# def flatten(self):
#     return RhythmTree.from_ratios(self._ratios, self._span, self._decomp)

# def rotate(self, n:int = 1):
#     return RhythmTree.from_tree(rotate_tree(self, n), self._span, self._decomp)
