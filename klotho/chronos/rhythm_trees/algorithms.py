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
def strict_decomposition(lst:Tuple[Fraction], meas) -> tuple:
    """
    Decompose proportions into a duration-preserving common-denominator form.

    Algorithm 3 (StrictDecomposition) from Karim Haddad, per the rule his
    figs. 4.33/4.39 exhibit: each proportion ``p_i`` of a Tempus ``N/D``
    becomes ``(p_i * N) / (sum|p| * D)`` — so the parts share one common
    denominator and sum exactly to the Tempus. Strict decomposition exists
    FOR concatenation (his sect4.4.6.2.1: it "preserves the integrity of the
    Temporal Unit... and reserves it for other eventual operations such as
    concatenation"), which is why the spelling must survive: the result is
    a tuple of :class:`Meas`, never :class:`~fractions.Fraction`, because
    Fraction auto-reduces the common-denominator form out of existence.

    (The pre-2026-08-29 version divided by the numerator gcd and did not
    preserve duration — 3/4 (2 1 1 1) came back summing to 3/5. ALG-6.)

    Parameters
    ----------
    lst : tuple of Fraction
        The list of proportions (typically from :func:`measure_ratios`).
        Negative proportions (rests) keep their sign in the output.
    meas : Meas or Fraction
        The Tempus.

    Returns
    -------
    tuple of Meas
        One part per proportion, on a shared unreduced denominator.

    Examples
    --------
    >>> from klotho.chronos.rhythm_trees import Meas
    >>> strict_decomposition(measure_ratios((2, 1, 1, 1)), Meas('3/4'))
    (6/20, 3/20, 3/20, 3/20)
    """
    from .meas import Meas
    meas = Meas(meas)
    common = reduce(lcm, (abs(f.denominator) for f in lst), 1)
    den = common * meas.denominator
    return tuple(
        Meas(int(f * common) * meas.numerator, den) for f in lst
    )

# ------------------------------------------------------------------------------------
# The Chapter-4 symbolic core (ruling R13: the algebra lives here, on the
# untimed layer — exact Meas/Fraction arithmetic, no tempo in scope).
# UT/UC surfaces lift to these through the LAYER-3 reconciliation rule
# (temporal_units.algorithms).
# ------------------------------------------------------------------------------------

def _fuse_parts(parts):
    """Fold ``(numerator, denominator, S)`` parts into one ``(total, den,
    S_out)`` on the lcm denominator, raw ints throughout (TEMPO-5: no gcd
    reduction anywhere). A fundamental part (single plain leaf) contributes
    a bare proportion — negative when it is a rest, float when its leaf is
    tied (a leading tie rides into the fused S, where it finally has a
    predecessor); a composed part nests as ``(w, S)``."""
    den = reduce(lcm, (d for _, d, _ in parts), 1)
    total = 0
    s_out = []
    for n, d, s in parts:
        w = n * (den // d)
        total += abs(w)
        if len(s) == 1 and not isinstance(s[0], tuple):
            first = s[0]
            if isinstance(first, float):
                s_out.append(float(w))
            elif first < 0:
                s_out.append(-w)
            else:
                s_out.append(w)
        elif len(s) == 0:
            s_out.append(w)
        else:
            s_out.append((w, tuple(s)))
    return total, den, tuple(s_out)


def decompose(rt) -> tuple:
    """
    Decompose a rhythm tree into fundamental trees, one per sounding event.

    The RT-level sibling of :func:`klotho.chronos.temporal_units.algorithms.decompose`
    (LAYER-2) — Haddad's decomposition on the untimed layer, where his
    sect4.5.1 puts it. Sign-carrying (ALG-1: a rest leaf comes back as a
    positive tempus with a rest-encoded S ``(-1,)``) and tie-aware (ALG-2,
    charter sect9: one fundamental unit per tie GROUP, its tempus the
    unreduced raw-int sum of the members' durations on their common
    denominator — ``16/21 + 32/35 = 176/105``, which is why Haddad's
    ``[x]`` is 10 units, not 11).

    Parameters
    ----------
    rt : RhythmTree
        The tree to decompose.

    Returns
    -------
    tuple of RhythmTree
        One fundamental tree per tie group (span 1; ``S = (1,)`` for a
        sound, ``(-1,)`` for a rest). Singleton parts keep the reduced
        per-leaf spelling (his fig. 4.108 form); only group sums stay
        unreduced, because only there is a spelling being *constructed*.
    """
    from .rhythm_tree import RhythmTree
    from .meas import Meas
    parts = []
    rx = rt._rx
    for group in rt.tie_groups:
        if len(group) == 1:
            md = rx.get_node_data(group[0])['metric_duration']
            s = (-1,) if md < 0 else (1,)
            parts.append(RhythmTree(span=1, meas=Meas(abs(md)),
                                    subdivisions=s))
        else:
            mds = [rx.get_node_data(n)['metric_duration'] for n in group]
            den = reduce(lcm, (m.denominator for m in mds), 1)
            num = sum(m.numerator * (den // m.denominator) for m in mds)
            parts.append(RhythmTree(span=1, meas=Meas(num, den),
                                    subdivisions=(1,)))
    return tuple(parts)


def fuse(rts) -> 'object':
    """
    Fuse rhythm trees into ONE tree — Haddad's ‖ ("concatenation").

    Named ``fuse`` (R13-G): his ‖ folds a sequence of units into one unit
    with a unified Tempus — that is a fold, not a concatenation, and
    append/prepend already own that word. The inverse of decomposition:
    ``fuse(6/20, 3/20, 3/20, 3/20) => 15/20 (6 3 3 3)``, unreduced
    spelling kept (TEMPO-5).

    A common denominator is NOT required (his sect4.4.6.5: same-denominator
    parts guarantee a *simple* composed unit; variable denominators
    produce a *complex* one — both legal, and he sometimes prefers keeping
    the complex spelling). Fundamental operands contribute bare
    proportions (sign-carrying for rests, tie-marking floats preserved);
    composed operands nest as ``(D, S)`` pairs. Spans fold into the
    contribution.

    Parameters
    ----------
    rts : iterable of RhythmTree
        The operands, in temporal order.

    Returns
    -------
    RhythmTree
        One tree; ``meas`` is the unreduced sum on the lcm denominator.
    """
    from .rhythm_tree import RhythmTree
    from .meas import Meas
    rts = list(rts)
    if not rts:
        raise ValueError("fuse requires at least one operand")
    for r in rts:
        if not isinstance(r, RhythmTree):
            raise TypeError(
                f"fuse at RT level takes RhythmTrees; got "
                f"{type(r).__name__}. For TemporalUnits use "
                f"klotho.chronos.temporal_units.algorithms.fuse, which "
                f"lifts, reconciles tempo, and re-temporalises."
            )
    parts = [(r.meas.numerator * r.span, r.meas.denominator, r.subdivisions)
             for r in rts]
    total, den, s_out = _fuse_parts(parts)
    return RhythmTree(span=1, meas=Meas(total, den), subdivisions=s_out)


def flatten(rt) -> 'object':
    """
    Project a rhythm tree onto its canonical one-level spelling —
    Haddad's *réduction* (the overline), decompose-then-fuse in one step.

    Named ``flatten`` (R13-G): ``reduce`` collides with gcd-reduction —
    the exact thing this operation does NOT do (it un-reduces toward the
    leaf grid) — and with ``functools.reduce``, whose fold shape belongs
    to :func:`fuse`. A projection, not an identity: the result sounds
    identical (exact Fraction onsets and durations), carries one term per
    sounding event with ``sum(|prolatio|) == meas.numerator``, is
    idempotent, and is a no-op exactly on already-canonical input.
    ``3/4 (2 1 1 1) => 15/20 (6 3 3 3)``.

    Parameters
    ----------
    rt : RhythmTree

    Returns
    -------
    RhythmTree
    """
    return fuse(decompose(rt))


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

    Each element of the matrix is a ``(D, S)`` pair. For the element at row
    *i*, column *j*, ``auto_subdiv`` is applied to its subdivisions with an
    effective rotation offset of ``j - i + rotation_offset * i``.

    At the default ``rotation_offset=1`` that reduces to ``j``: the row index
    cancels, the offset depends on the column alone, and identical input rows
    produce identical output rows. Pass a ``rotation_offset`` other than 1 for
    the offset to vary by row as well as by column.

    Parameters
    ----------
    matrix : tuple of tuple
        A matrix where each element is a ``(D, S)`` pair.
    rotation_offset : int, optional
        Per-row multiplier in the effective offset ``j - i +
        rotation_offset * i``. Default is 1, at which the row term cancels.

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
