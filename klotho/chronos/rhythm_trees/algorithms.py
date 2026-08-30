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
import numbers
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


def filtrage(rt, series):
    """
    Rest the leaves a series walks onto -- Haddad's *filtrage* ("filtering").

    Named ``filtrage`` (R13-G): his own term is accurate here -- this really
    does filter a subdivided surface through a series -- and ``filter``
    shadows the builtin, so the French is kept. Haddad sect2.3.4, thesis
    p. 279, figure 2.13:

        *"Nous filtrons le rythme subdivise (2.12) par la meme serie
        originelle (5 3 4 2 1 (5)) qui donnera par extension des silences
        aux positions (0 5 8 12 14 15 20) qui se trouvent etre la premiere
        note de chaque groupe d'irrationnel"*

        "We filter the subdivided rhythm (2.12) by the same original series
        (5 3 4 2 1 (5)) which will by extension give rests at positions
        (0 5 8 12 14 15 20), which happen to be the first note of each
        irrational group."

    His footnote 5 settles the indexing so we do not have to guess:
    *"0 etant la premiere position comme il est souvent l'usage dans les
    langages informatiques."* -- "0 being the first position, as is often
    the usage in computing languages." So the positions are ``[0]`` plus
    the inclusive prefix sums of the series, which for ``(5 3 4 2 1 5)``
    gives ``[0, 5, 8, 12, 14, 15, 20]`` -- character for character his
    printed list.

    Published example (RT-4). Filtering figure 2.12 by ``(5 3 4 2 1 5)``::

        (8 ((4 (1 1 1 1 1)) (2 (1 1 1)) (1 (1 1 1 1))
            (5 (1 1)) (5 (1)) (3 (1 1 1 1 1))))
        =>
        (8 ((4 (-1 1 1 1 1)) (2 (-1 1 1)) (1 (-1 1 1 1))
            (5 (-1 1)) (5 (-1)) (3 (-1 1 1 1 1))))

    **What is Haddad's and what is Klotho's** (DOC-3). The rule, the
    series, the position list and the 0-based convention are all his. Three
    decisions are ours, because his single worked example cannot settle
    them:

    - **Group 5 diverges, deliberately.** He prints ``(5 (-4 -1))`` where
      the mechanical filtering gives ``(5 (-1))``. Both are one 5-unit rest;
      his has an extra leaf, which he carries through figures 2.14 and 2.15
      so the *evide* has a tie to demonstrate there. It is a re-spelling
      applied after the filtering, not the filtering's output -- his own
      printed positions are the prefix sums of a TWENTY-leaf surface (a
      21-leaf tree would have to read ``... 15 16``), and his gloss "the
      first note of each irrational group" holds for six positions over six
      groups only on the 20-leaf reading. Klotho emits the 20-leaf form.
    - **Out-of-range positions are CLIPPED, not wrapped.** On his example
      the two are indistinguishable (``20 % 20 == 0``, and leaf 0 is
      already a target). The position list is a prefix-sum *walk* over the
      leaf surface, so running off the end means the series overshot.
    - **The trailing total is KEPT** -- ``[0] + accumulate(series)``, giving
      n+1 positions, not ``[0] + accumulate(series[:-1])`` giving n. They
      coincide only when ``sum(series) == len(leaf_nodes)``, which is his
      case; they differ on, say, a 30-leaf tree filtered by the same
      series. Keeping it is literally what he printed, and clipping
      degrades it to the other form in his case anyway.

    Rests are made through :meth:`RhythmTree.make_rest`, so a filtered leaf
    sheds any tie it carried (charter sect1: a tied rest is illegal) and a
    filtered branch rests everything under it.

    Parameters
    ----------
    rt : RhythmTree
        The tree to filter. Not modified; a copy is returned.
    series : sequence of int
        The step series. Every step must be a positive integer -- a zero or
        negative step makes the prefix-sum walk stall or run backwards,
        which is not a filtering of anything.

    Returns
    -------
    RhythmTree
        A new tree with the walked-onto leaves rested.

    Raises
    ------
    ValueError
        If ``series`` is empty or contains a non-positive step.
    """
    steps = tuple(series)
    if not steps:
        raise ValueError(
            "filtrage needs a non-empty series -- the series IS the filter"
        )
    for s in steps:
        if isinstance(s, bool) or not isinstance(s, numbers.Integral):
            raise TypeError(
                f"filtrage series takes integer steps; got {s!r}"
            )
        if s <= 0:
            raise ValueError(
                f"filtrage series steps must be positive; got {s!r}. A "
                f"zero step stalls the prefix-sum walk and a negative one "
                f"runs it backwards."
            )
    positions = [0]
    for s in steps:
        positions.append(positions[-1] + int(s))
    out = rt.copy()
    leaves = list(out.leaf_nodes)
    # dict.fromkeys de-duplicates while keeping order; make_rest is
    # idempotent anyway, this just avoids the redundant re-evaluations.
    for p in dict.fromkeys(positions):
        if p < len(leaves):          # CLIP (see above), never wrap
            out.make_rest(leaves[p])
    return out


def evide(rt):
    """
    Interchange sounds and rests -- Haddad's *rythme evide*, after Boulez.

    Named ``evide`` (R13-G, an ASCII transliteration of *evide*): an English
    name wins only when Haddad's own term is WRONG for the operation --
    ``fuse`` because his "concatenation" is a fold, ``flatten`` because his
    *reduction* un-reduces. Here his term is accurate, so it is kept.
    ``hollow`` was the alternative and is a cheap rename if preferred.

    Haddad sect2.3.5, thesis p. 280, figure 2.14:

        *"Nous emprunterons a Pierre Boulez le principe du << rythme evide >>
        [...] comme on peut aussi representer comme un rythme << negatif >>
        d'un autre qui lui est pendant. Il s'agit d'intervertir les silences
        par des notes exprimees et vice et versa"*

        "We will borrow from Pierre Boulez the principle of the
        'hollowed-out rhythm' [...] which can also be represented as a
        'negative' rhythm of another that is its counterpart. It is a matter
        of interchanging the rests with expressed notes and vice versa."

    Boulez source as he cites it: Pierre Boulez and Paule Thevenin,
    *Releves d'apprenti* ("Apprentice's Notes"), Editions du Seuil, 1966.
    His footnote 7: *"Nous avons eu le privilege de montrer au compositeur
    ces exemples les illustrant par une piece breve."* -- "We had the
    privilege of showing the composer these examples, illustrating them with
    a short piece." Boulez himself saw these figures.

    Published example (RT-3). Hollowing out figure 2.13 gives figure 2.14
    character for character, his ``1.0`` tie markers included -- they are
    identical to Klotho's own storage convention::

        (8 ((4 (-1 1 1 1 1)) (2 (-1 1 1)) (1 (-1 1 1 1))
            (5 (-1 1)) (5 (-4 -1)) (3 (-1 1 1 1 1))))
        =>
        (8 ((4 (1 -1 -1 -1 -1)) (2 (1 -1 -1)) (1 (1 -1 -1 -1))
            (5 (1 -1)) (5 (4 1.0)) (3 (1.0 -1 -1 -1 -1))))

    **The re-tie rule is the charter's, not Haddad's** (07_TIES_CHARTER.md
    sect10): for each maximal run of newly-sounding leaves, the head keeps
    ``tied=False`` and the rest get ``tied=True``. Runs are computed AFTER
    the flip, which is what guarantees the charter's second condition -- a
    run head can never come out a dangling continuation of a preceding
    still-resting region. Sign flips clear ``tied`` (charter sect1), so the
    operation cannot manufacture a tied rest. Figure 2.14's own tie group
    crosses a branch boundary (the last leaf of group 5 and the first of
    group 6), which is exactly the case ``tie_groups`` derives by leaf
    ORDER rather than subtree containment.

    **Three behaviours are Klotho's, and are choices, not accidents**
    (DOC-3):

    - **Negative interior nodes are normalised to positive first.**
      ``_evaluate`` re-negates a positive child of a negative parent, so
      flipping a leaf sounding under a RESTING BRANCH is silently undone --
      ``(1, (-2 (1 1)), 1)`` would hollow out to ``(-1, (-2 (-1 -1)), -1)``,
      the group still a rest and nothing sounding at all. Normalising the
      branch first (top-down, so a nested one cannot re-negate under its
      own parent) gives ``(-1, (2 (1 1.0)), -1)``, which is the music the
      operation means. The alternative was refusing such trees loudly; the
      normalisation is chosen because a resting branch is a legal spelling
      of a resting region, and hollowing it out has an obvious answer.
    - **Every flip is written with an explicit ``tied=False``.** Writing an
      int ``proportion`` does NOT clear the flag: ``_evaluate`` reads
      ``isinstance(s, float) or data['tied']``, and only a NEGATIVE value
      forces it off. A silent flag would survive the flip and re-float the
      proportion, and charter sect10's run rule must be the only thing that
      sets a tie here.
    - **Input ties are destroyed, by design.** Every leaf flips, so every
      input tie clears. ``evide(evide(x))`` restores x's SIGN PATTERN
      exactly, but not its ties -- an involution on the signs only.

    Figure 2.15, his "optimised" spelling (successive rests merged within a
    group, ``(4 (1 -4))``), is deliberately NOT built. He presents it as an
    alternative spelling of the same structure, not as a further operation;
    it is close to a within-group :func:`flatten`, and it needs the form
    ``(5 (5))``, which ``_validate_s_form`` currently rejects.

    Parameters
    ----------
    rt : RhythmTree
        The tree to hollow out. Not modified; a copy is returned.

    Returns
    -------
    RhythmTree
        A new tree: every sound a rest, every rest a sound, re-tied per
        charter sect10.
    """
    out = rt.copy()

    # Pass 1 -- normalise resting BRANCHES to sounding, top-down.
    # ``descendants`` is depth-first pre-order, so a parent is always
    # positive by the time its children are reached; bottom-up would let a
    # still-negative parent re-negate a child that had just been flipped.
    for n in out.descendants(out.root):
        if out.out_degree(n) == 0:
            continue
        p = out[n]['proportion']
        if p < 0 or isinstance(p, float) or out[n].get('tied', False):
            out.set_node_data(n, proportion=int(abs(p)), tied=False)

    leaves = list(out.leaf_nodes)

    # Pass 2 -- interchange sounds and rests. ``tied=False`` is explicit on
    # every write (see the docstring: an int write does not clear it).
    for n in leaves:
        p = out[n]['proportion']
        flipped = -int(abs(p)) if p > 0 else int(abs(p))
        out.set_node_data(n, proportion=flipped, tied=False)

    # Pass 3 -- charter sect10: re-tie each maximal run of newly-sounding
    # leaves, head untied. Computed after the flip, so no head can be a
    # dangling continuation.
    previous_sounds = False
    for n in leaves:
        sounds = out[n]['proportion'] > 0
        if sounds and previous_sounds:
            out.set_node_data(n, tied=True)
        previous_sounds = sounds

    return out


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
