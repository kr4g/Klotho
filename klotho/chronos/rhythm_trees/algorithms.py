"""
Rhythm tree algorithms.

Algorithms that operate on either the S part of a rhythmic tree or its
corresponding proportions.

Pseudocode for numbered algorithms by Karim Haddad unless otherwise noted.

    "Let us recall that the mentioned part corresponds to the S part of a
    rhythmic tree composed of (DS), that is its part constituting the
    proportions which can also encompass other tree structures."
    -- Karim Haddad

Sources (docket DOC-1/DOC-2/DOC-7)
----------------------------------
The numbered algorithms and the figures cited throughout this module come
from Haddad, Karim, *L'Unite Temporelle : Une approche pour l'ecriture de
la duree et de sa quantification* ("The Temporal Unit: An approach to the
writing of duration and its quantification"), doctoral thesis, Sorbonne
Universite, 2020, HAL ``tel-03258984``. Algorithms 1-3 are here; 4
(``PermutList``) and 5 (``AutoRef``) are in
:mod:`klotho.topos.collections.patterns`.

For time-block material specifically -- ``tempus``, ``prolatio``, the
Temporal Unit itself -- the EARLIER and primary source is his 2008 chapter
"The Time-Block Concept in OpenMusic", twelve years before the thesis and
written in English. See :mod:`klotho.chronos.temporal_units.temporal` for
the full citations of all three sources.
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


# ------------------------------------------------------------------------------------
# The Tempus-FOLLOWING operator family (docket OPS-2/3/4, box half).
#
# Haddad states the axis outright, p. 128:
#
#     « Les prolationis qui en résultent sont identiques. C'est le Tempus
#     qui diffère. Dans le cas de la « prolation » stricte, le Tempus est
#     identique. Dans le deuxième cas, le Tempus est la somme des
#     prolationis une fois transformés. »
#     -- "The resulting prolationis are identical. It is the Tempus that
#     differs. In the case of strict 'prolation', the Tempus is identical.
#     In the second case, *the Tempus is the sum of the prolationis once
#     transformed*."
#
# That last clause is this family's implementation, literally. The
# Tempus-PRESERVING siblings (insertion, extraction, expansion/compression)
# hold the Tempus and rescale the contents instead.
#
# His own labels are « prolationnelle stricte » ("strictly prolational")
# for the preserved half and « relative » for this one; the English pair
# "Tempus-preserving"/"Tempus-following" is Klotho's coinage.
#
# Every one of them is decompose -> operate -> concatenate, sect4.5.2
# preamble, p. 124:
#
#     « Ces opérations utilisent l'ajout équivalent à l'addition, le
#     retrait à la soustraction, et la substitution (sous forme de
#     multiplication) après décomposition de l'Unité temporelle composée
#     suivi de la concaténation de l'ensemble des prolationis. »
#     -- "These operations use addition for adding, subtraction for
#     removal, and substitution (in the form of multiplication) -- after
#     decomposition of the composite Temporal Unit, followed by
#     concatenation of the whole set of prolationis."
#
# so all three are ``decompose`` + a list edit + ``fuse``, and the common
# denominator that makes an inserted or scaled operand commensurable with
# the survivors is ``_fuse_parts``' lcm fold.
# ------------------------------------------------------------------------------------


def _as_operand_tuple(value):
    """Broadcast a scalar operand to a one-element tuple.

    ``diminish(rt, 0)`` and ``diminish(rt, (0,))`` are the same call. A
    :class:`Meas`, a :class:`RhythmTree` and a ``Fraction`` are scalars
    here even though the first two are containers in other senses, so the
    test is on ``list``/``tuple`` alone.
    """
    return tuple(value) if isinstance(value, (list, tuple)) else (value,)


def _check_positions(positions, upper, verb, *, unique=False):
    """Validate 0-based positions into the decomposed sequence.

    His indexing convention, p. 125:

        « ...et position la position de l'ajout par rapport à l'ensemble
        de la séquence décomposée (0 étant la position de tête de
        séquence). »
        -- "...and position is the position of the addition relative to
        the whole decomposed sequence (0 being the head-of-sequence
        position)."

    p. 127 repeats it for the scaling operator ("0 being the first
    prolatio"). *upper* is inclusive: ``len(parts)`` for an insertion
    (appending past the tail is legal), ``len(parts) - 1`` for an edit of
    an existing prolatio.
    """
    out = []
    for p in positions:
        if isinstance(p, bool) or not isinstance(p, numbers.Integral):
            raise TypeError(
                f"{verb} positions are integer indices into the decomposed "
                f"sequence; got {p!r}"
            )
        p = int(p)
        if not 0 <= p <= upper:
            raise ValueError(
                f"{verb} position {p} is out of range: the decomposed "
                f"sequence admits 0..{upper} (0 is the head of sequence, "
                f"his « position de tête de séquence »)."
            )
        out.append(p)
    if unique and len(set(out)) != len(out):
        raise ValueError(
            f"{verb} was given the same position twice. Two ratios on one "
            f"prolatio has no defined answer -- compose them into a single "
            f"ratio, or apply the operator twice."
        )
    return tuple(out)


def _check_pairing(left, right, verb, left_name):
    """Refuse unequal parallel sequences.

    His notation is two parallel tuples -- ``⊠((1/3 1/9),(2 3))`` -- so a
    length mismatch is a mis-typed call, never a broadcast.
    """
    if len(left) != len(right):
        raise ValueError(
            f"{verb} takes parallel sequences: {len(left)} {left_name} "
            f"against {len(right)} positions. His notation pairs them one "
            f"to one."
        )


def diminish(rt, positions):
    """
    Delete prolationes and let the Tempus follow — Haddad's diminution (⊟).

    sect4.5.2.2, p. 126, figs. 4.62–4.63. The Tempus-FOLLOWING half of the
    remove pair; the preserving sibling is extraction (⊖), which keeps the
    Tempus and dilates the survivors to fill it.

        « Le tempus sera par conséquent recalculé à partir de la somme des
        prolationis restants. »
        -- "The tempus will consequently be recomputed from the sum of the
        remaining prolationis."

    So the bar shrinks: at held bpm the real duration drops by exactly the
    removed prolationes, and the notation changes.

    Published example (his running source ``B``, the *réduction* of
    ``1/1 ((2 (2 1)) 1 2 1)`` at fig. 4.62)::

        B = 18/18 (4 2 3 6 3)
        B ⊟ (0)    =>  14/18 (2 3 6 3)
        B ⊟ (4)    =>  15/18 (4 2 3 6)
        B ⊟ (1 3)  =>  10/18 (4 3 3)

    **His printed Tempi are inconsistent, and Klotho does not chase them**
    (TEMPO-5). He prints 14/18 as ``7/9`` and 10/18 as ``5/9`` but leaves
    15/18 alone — the reductions are editorial, not rule-generated. Same
    durations either way, and the duration is the claim.

    Positions index the DECOMPOSED sequence, which is one entry per tie
    GROUP (ALG-2), not one per leaf. Like :func:`flatten`, whose machinery
    this is, the result carries one term per sounding event and no ties.

    Parameters
    ----------
    rt : RhythmTree
        The tree to remove prolationes from. Not modified.
    positions : int or sequence of int
        0-based indices into the decomposed sequence. Repeats are
        harmless (a prolatio can only be removed once).

    Returns
    -------
    RhythmTree
        A new tree whose ``meas`` is the sum of the survivors.

    Raises
    ------
    ValueError
        If *positions* is empty, names an index out of range, or would
        remove every prolatio — an empty Temporal Unit is not a rest, it
        is nothing, and it has no Tempus to compute.
    """
    from .rhythm_tree import RhythmTree
    if not isinstance(rt, RhythmTree):
        raise TypeError(
            f"diminish at RT level takes a RhythmTree; got "
            f"{type(rt).__name__}. For TemporalUnits use "
            f"klotho.chronos.temporal_units.algorithms.diminish."
        )
    parts = list(decompose(rt))
    idx = _as_operand_tuple(positions)
    if not idx:
        raise ValueError(
            "diminish needs at least one position -- removing nothing is "
            "not a diminution. For the canonical re-spelling alone, use "
            "flatten."
        )
    drop = set(_check_positions(idx, len(parts) - 1, 'diminish'))
    survivors = [p for i, p in enumerate(parts) if i not in drop]
    if not survivors:
        raise ValueError(
            f"diminish would remove all {len(parts)} prolationes, leaving "
            f"no Tempus to recompute from -- his rule is « recalculé à "
            f"partir de la somme des prolationis restants » (\"recomputed "
            f"from the sum of the remaining prolationis\"), and an empty "
            f"sum is not a Temporal Unit."
        )
    return fuse(survivors)


def _as_prolatio(value, verb):
    """Lift an augmentation operand to a :class:`RhythmTree`.

    His §4.5.2 preamble makes the operand a PROLATIO, not merely a number
    — the operation is « la concaténation de l'ensemble des prolationis »
    ("the concatenation of the whole set of prolationis") — so a
    ``RhythmTree`` passes through with its internal structure intact and
    a bare rational becomes a fundamental one.

    A ``Meas`` keeps its raw spelling (TEMPO-5), and the spelling matters
    here: 6/20 and 3/10 are the same duration but refine the shared grid
    differently, which is exactly the distinction of nature his §4.4.2 and
    §4.4.5 insist on. Other rationals go through ``Fraction`` and
    normalise. A NEGATIVE operand inserts a rest — the sign convention
    ``decompose`` already uses, so a silence is insertable without a
    second verb.
    """
    from .rhythm_tree import RhythmTree
    from .meas import Meas
    if isinstance(value, RhythmTree):
        return value
    if isinstance(value, Meas):
        num, den = value.numerator, value.denominator
    else:
        try:
            f = _exact_ratio(value)
        except (TypeError, ValueError):
            raise TypeError(
                f"{verb} operands are prolationes: a RhythmTree, a Meas, "
                f"or any rational; got {type(value).__name__}."
            ) from None
        num, den = f.numerator, f.denominator
    if num == 0:
        raise ValueError(
            f"{verb} cannot add a zero-length prolatio -- it would occupy "
            f"no time, and the rhythm tree grammar rejects a zero "
            f"proportion. To add a silence, pass a NEGATIVE value."
        )
    negative = (num < 0) != (den < 0)
    return RhythmTree(span=1, meas=Meas(abs(num), abs(den)),
                      subdivisions=(-1,) if negative else (1,))


def augment(rt, additions, positions):
    """
    Add prolationes and let the Tempus follow — Haddad's augmentation (⊞).

    sect4.5.2.1, pp. 125–126, figs. 4.58–4.60. The Tempus-FOLLOWING half
    of the add pair; the preserving sibling is insertion (⊕), which holds
    the Tempus and re-spells the whole bar as a longer tuplet.

    The Tempus grows by exactly what was added — p. 128, on this family:
    « le Tempus est la somme des prolationis une fois transformés » ("the
    Tempus is the sum of the prolationis once transformed") — so at held
    bpm the bar really gets longer.

    Published examples::

        2/2 (2 1 2) ⊞ (3/10, 2)                     =>  13/10 (4 2 3 4)
        4/3 (4 3 2 1) ⊞ {(1/4,0) ‖ (3/10,2) ‖ (1/2,3)}
                                    =>  143/60 (15 32 24 18 16 30 8)

    **Figures 4.58 and 4.60 print the source subscript as ``(2 1 1)``.**
    It is ``(2 1 2)``, proven three ways: his prose says « trois
    prolationis de (2 1 2) » ("three prolationis of (2 1 2)"), the
    engraving is a 5:4 tuplet (5 = 2+1+2), and only ``(2 1 2)`` yields his
    own printed ``(4 2 3 4)``.

    **This is the refinement case.** An added prolatio is generally not
    commensurable with the existing ones — in fig. 4.58 the source lives
    on 5ths and the operand on 10ths — and the whole result is the grid on
    which they all become integers. That grid is ``_fuse_parts``' lcm
    fold, so the arithmetic is the shipped one and no new rule is
    introduced here.

    Positions index the DECOMPOSED sequence and are **insert-before**,
    0-based (p. 125: « 0 étant la position de tête de séquence » — "0
    being the head-of-sequence position"). ``len(parts)`` appends past the
    tail. Indices name the ORIGINAL sequence, so several insertions do not
    shift one another; two operands at one position go in the order given.
    One entry per tie GROUP (ALG-2), and, like :func:`flatten`, the result
    carries no ties.

    Parameters
    ----------
    rt : RhythmTree
        The tree to augment. Not modified.
    additions : RhythmTree, Meas, rational, or sequence of them
        The prolationes to add. A ``RhythmTree`` keeps its internal
        structure and nests; a negative rational inserts a rest. A scalar
        broadcasts to a one-element tuple.
    positions : int or sequence of int
        Parallel to *additions*, in ``0..len(decomposed)``.

    Returns
    -------
    RhythmTree
        A new tree whose ``meas`` is the sum of everything, source and
        additions alike, on their common grid.

    Raises
    ------
    ValueError
        On an empty call, a length mismatch, an out-of-range position, or
        a zero-length operand.
    """
    from .rhythm_tree import RhythmTree
    if not isinstance(rt, RhythmTree):
        raise TypeError(
            f"augment at RT level takes a RhythmTree; got "
            f"{type(rt).__name__}. For TemporalUnits use "
            f"klotho.chronos.temporal_units.algorithms.augment."
        )
    adds = _as_operand_tuple(additions)
    ps = _as_operand_tuple(positions)
    if not adds and not ps:
        raise ValueError(
            "augment needs at least one (prolatio, position) pair -- "
            "adding nothing is not an augmentation. For the canonical "
            "re-spelling alone, use flatten."
        )
    _check_pairing(adds, ps, 'augment', 'additions')
    parts = list(decompose(rt))
    # upper bound is len(parts), not len(parts) - 1: inserting BEFORE the
    # one-past-the-end index is how the tail is appended.
    idx = _check_positions(ps, len(parts), 'augment')

    pending = {}
    for value, p in zip(adds, idx):
        pending.setdefault(p, []).append(_as_prolatio(value, 'augment'))

    out = []
    for i in range(len(parts) + 1):
        out.extend(pending.get(i, ()))
        if i < len(parts):
            out.append(parts[i])
    return fuse(out)


def _scaling_ratio(value, verb):
    """Exact positive rational form of a scaling ratio.

    A :class:`Meas` is read RAW (TEMPO-5) — its spelling is a Tempus and
    survives into the result's grid. Everything else goes through
    ``Fraction``, which normalises; that is Fraction's contract, not a
    policy of the verb. Pass a ``Meas`` when the spelling matters.
    """
    from .meas import Meas
    if isinstance(value, Meas):
        num, den = value.numerator, value.denominator
    else:
        f = _exact_ratio(value)
        num, den = f.numerator, f.denominator
    if num == 0:
        raise ValueError(
            f"{verb} ratios must be positive; 0 would delete the prolatio, "
            f"which is diminution's job (⊟), not this operator's."
        )
    if (num < 0) != (den < 0):
        raise ValueError(
            f"{verb} ratios must be positive; got {value!r}. A prolatio's "
            f"SIGN says whether it sounds or rests and belongs to the "
            f"prolatio, never to the ratio -- a negative ratio would make "
            f"a rest out of a scaling, which is not what the operator "
            f"means. Use make_rest for that."
        )
    return abs(num), abs(den)


def scale_tempus(rt, ratios, positions):
    """
    Scale prolationes and let the Tempus follow — Haddad's
    dilatation/contraction (⊠).

    sect4.5.2.3, pp. 127–128, figs. 4.66–4.69. The Tempus-FOLLOWING half
    of the scale pair; the preserving sibling is expansion/compression
    (⊗), which holds the Tempus and re-spells everything against it.

    **One operator, not two.** His §4.5.3 heading reads
    « Dilatation/Contraction (⊠), Expansion/Compression (⊗) »: each policy
    is a single operator whose ratio decides the direction — above 1 it
    dilates, below 1 it contracts. That is why the verb is ``scale_tempus``
    and not ``dilate``, which would be accurate above 1 and actively
    misleading below it. Both members of the pair are named for the
    POLICY (``scale_tempus`` / ``scale``), which is the point of the axis.

    Published examples on his running source ``B = 18/18 (4 2 3 6 3)``::

        B ⊠ ((3), (2))          =>  24/18 (4 2 9 6 3)      fig. 4.66
        B ⊠ ((1/3 1/9), (2 3))  =>  32/54 (12 6 3 2 9)     fig. 4.69

    **Figures 4.68 and 4.69 are corrupt and must not be copied.** Both
    reprint the preceding *expansion* result ``(4 2 9 6 3)`` as the
    contraction's prolationis. Fig. 4.69's Tempus ``16/27`` is right, and
    it forces the true answer; ``32/54`` is its raw spelling on the grid
    the contraction refines to.

    Positions index the DECOMPOSED sequence — one entry per tie GROUP
    (ALG-2), 0-based, p. 127: "0 being the first prolatio". Like
    :func:`flatten`, whose machinery this is, the result carries one term
    per sounding event and no ties.

    Parameters
    ----------
    rt : RhythmTree
        The tree to scale. Not modified.
    ratios : rational or sequence of rational
        One positive ratio per position. A ``Meas`` keeps its raw
        spelling; a ``Fraction``/``str``/``int`` normalises. A scalar
        broadcasts to a one-element tuple.
    positions : int or sequence of int
        Parallel to *ratios*, as his own ``⊠((1/3 1/9),(2 3))`` notation
        pairs them.

    Returns
    -------
    RhythmTree
        A new tree whose ``meas`` is the sum of the transformed
        prolationes.

    Raises
    ------
    ValueError
        On an empty call, a length mismatch, a repeated position (two
        ratios on one prolatio has no defined answer), a non-positive
        ratio, or an out-of-range position.
    """
    from .rhythm_tree import RhythmTree
    from .meas import Meas
    if not isinstance(rt, RhythmTree):
        raise TypeError(
            f"scale_tempus at RT level takes a RhythmTree; got "
            f"{type(rt).__name__}. For TemporalUnits use "
            f"klotho.chronos.temporal_units.algorithms.scale_tempus."
        )
    rs = _as_operand_tuple(ratios)
    ps = _as_operand_tuple(positions)
    if not rs and not ps:
        raise ValueError(
            "scale_tempus needs at least one (ratio, position) pair -- "
            "scaling nothing is not a dilatation. For the canonical "
            "re-spelling alone, use flatten."
        )
    _check_pairing(rs, ps, 'scale_tempus', 'ratios')
    parts = list(decompose(rt))
    idx = _check_positions(ps, len(parts) - 1, 'scale_tempus', unique=True)

    for ratio, p in zip(rs, idx):
        num, den = _scaling_ratio(ratio, 'scale_tempus')
        part = parts[p]
        # Raw ints, folded as ONE factor (TEMPO-5): Meas.__mul__ would
        # gcd-reduce and destroy the spelling even at the identity, and
        # applying the two factors separately can cancel against the
        # part's own terms. Decomposed parts always have span 1, so
        # there is no span left to fold in here.
        parts[p] = RhythmTree(
            span=1,
            meas=Meas(part.meas.numerator * num,
                      part.meas.denominator * den),
            subdivisions=part.subdivisions)
    return fuse(parts)


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

    Notes
    -----
    **Haddad's, and verified against him** (docket DOC-7). This reproduces
    his figure 2.12 exactly and said so nowhere until 2026-08-29 -- one of
    the inverted-attribution cases, where the faithful reproductions went
    uncited while borrowed vocabulary went unmarked. It belongs with
    :func:`~klotho.topos.collections.patterns.autoref` in section 2.3 of
    the thesis, not with the numbered algorithms above.

    The default ``n=1`` is what fig. 2.12 shows: each element takes its
    successor's value as its subdivision count, wrapping at the end.
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

def _exact_ratio(value) -> Fraction:
    """Exact rational form of a user-supplied ratio.

    Floats are snapped by ``limit_denominator(10**6)``. Without it
    ``Fraction(1/3)`` is ``6004799503160661/18014398509481984`` and every
    downstream proportion is astronomical — the documented float path was
    unusable.
    """
    if isinstance(value, float):
        return Fraction(value).limit_denominator(10 ** 6)
    return Fraction(value)


def segment_proportions(ratio: Union[Fraction, float, str]) -> tuple[int]:
    """
    Segment a ratio into a pair of complementary integers.

    Converts the ratio to a :class:`~fractions.Fraction` and returns
    ``(numerator, denominator - numerator)`` — the two-term subdivision
    that realises the ratio. ``2/5 => (2, 3)``.

    Renamed from ``segment`` (2026-08-29, docket OPS-5): Haddad's
    segmentation operator ⊥ took that name, because the operator is what
    he defines and this is its proportion arithmetic, not the operation.
    See :func:`segment`.

    Parameters
    ----------
    ratio : Fraction, float, or str
        The ratio to segment. Must lie strictly between 0 and 1. Floats
        are snapped to their intended rational.

    Returns
    -------
    tuple of int
        A pair ``(numerator, denominator - numerator)``.

    Raises
    ------
    ValueError
        If the ratio is not strictly between 0 and 1.
    """
    ratio = _exact_ratio(ratio)
    if ratio <= 0:
        raise ValueError(
            "ratio must be greater than 0; a zero or negative ratio has "
            "no proportion pair, and 0 would yield the pair (0, 1) whose "
            "leading zero the rhythm tree grammar rejects."
        )
    if ratio >= 1:
        raise ValueError("Ratio must be less than 1")
    return (ratio.numerator, ratio.denominator - ratio.numerator)


def _S_to_split_nodes(S):
    """Lower a subdivision tuple into the mutable form the splitter uses.

    ``['group', signed magnitude, children]`` or
    ``['leaf', signed magnitude, tied]``. A tie is carried as the flag it
    is rather than as the float spelling, so magnitude arithmetic stays
    exact and the float is re-emitted only at the end.
    """
    out = []
    for e in S:
        if isinstance(e, tuple):
            out.append(['group', Fraction(e[0]), _S_to_split_nodes(e[1])])
        else:
            out.append(['leaf', Fraction(e), isinstance(e, float)])
    return out


def _split_nodes(nodes, t):
    """Split *nodes* at proportion position *t*, descending into groups.

    Everything ending at or before *t* goes left, everything starting at
    or after it goes right, and the one element the cut falls inside is
    divided — recursively, so a group straddling the cut becomes a group
    on each side rather than being flattened. This is Haddad's variant
    (b), « scinder » ("to split"): the two pieces of a divided leaf are
    independent attacks, so only the left piece inherits the leaf's tie.
    """
    left, right = [], []
    acc = Fraction(0)
    for nd in nodes:
        mag = abs(nd[1])
        sign = -1 if nd[1] < 0 else 1
        if acc + mag <= t:
            left.append(nd)
        elif acc >= t:
            right.append(nd)
        else:
            head = t - acc
            tail = mag - head
            if nd[0] == 'group':
                sub_total = sum(abs(c[1]) for c in nd[2])
                sub_left, sub_right = _split_nodes(nd[2],
                                                   head / mag * sub_total)
                left.append(['group', sign * head, sub_left])
                right.append(['group', sign * tail, sub_right])
            else:
                left.append(['leaf', sign * head, nd[2]])
                right.append(['leaf', sign * tail, False])
        acc += mag
    return left, right


def _integerise_nodes(nodes):
    """Scale each subdivision level by the lcm of its denominators.

    A cut at an arbitrary factor lands between the grid points, so the
    split produces fractional proportions. Each level is scaled
    independently: a group's proportions are relative to its own sum, so
    multiplying one level by a positive integer changes no duration.
    """
    out = []
    for nd in nodes:
        if nd[0] == 'group':
            out.append(['group', nd[1], _integerise_nodes(nd[2])])
        else:
            out.append(list(nd))
    den = reduce(lcm, (abs(nd[1]).denominator for nd in out), 1)
    for nd in out:
        nd[1] = nd[1] * den
    return out


def _split_nodes_to_S(nodes):
    """Raise the splitter's form back to a subdivision tuple.

    A tied leaf is re-spelled as a whole-valued float, the encoding the
    grammar uses. Group Ds stay ``int``: a float D on an interior node is
    refused (it has no tie meaning in OpenMusic either), and groups carry
    no ties.
    """
    out = []
    for nd in nodes:
        if nd[0] == 'group':
            out.append((int(nd[1]), _split_nodes_to_S(nd[2])))
        else:
            value = int(nd[1])
            out.append(float(value) if nd[2] else value)
    return tuple(out)


def _resolve_segment_factor(meas, factor) -> Fraction:
    """Resolve either of Haddad's two segmentation conventions to a factor.

    A rational (``Fraction``, ``int``, ``float``, ``str``) is the factor
    itself. A :class:`Meas` is a *Tempus read relative to the source's*,
    his second convention (sect4.5.3.1 p. 129): fig. 4.73 converts it by
    multiplying by the inverse of the source Tempus, ``25/24 x 2/5 =
    5/12``. A list of ``Meas`` is summed first — fig. 4.74's n-th-unit
    form, ``(15/24 + 20/24) x 2/5 = 7/12``.
    """
    from .meas import Meas

    def _value(m):
        return Fraction(m.numerator, m.denominator)

    if isinstance(factor, Meas):
        f = _value(factor) / _value(meas)
    elif isinstance(factor, (list, tuple)):
        if not factor:
            raise ValueError(
                "an empty list of tempi gives no segmentation factor"
            )
        for m in factor:
            if not isinstance(m, Meas):
                raise TypeError(
                    f"a list factor is his fig. 4.74 form and holds Meas "
                    f"tempi to be summed; got {type(m).__name__}."
                )
        f = sum(_value(m) for m in factor) / _value(meas)
    else:
        f = _exact_ratio(factor)

    if not 0 < f < 1:
        raise ValueError(
            f"the segmentation factor must lie strictly between 0 and 1; "
            f"got {f}. Haddad: « un facteur proportionnel pouvant etre "
            f"une fraction quelconque entre 0 et 1 » -- \"a proportional "
            f"factor, which may be any fraction between 0 and 1\"."
        )
    return f


def segment(rt, factor, tie: bool = False) -> tuple:
    """
    Divide a rhythm tree in two — Haddad's segmentation operator (⊥).

    ``T ⊥ f => [T·f | T·(1−f)]``. The RT-level sibling of
    :func:`klotho.chronos.temporal_units.algorithms.segment` (sect4.5.3.1,
    pp. 129–131, figs. 4.71–4.74), on the untimed layer.

    Both his calling conventions are accepted, and they are NOT
    interchangeable spellings of the same text:

        « La segmentation est l'operation qui divise une Unite Temporelle
        en deux par un facteur proportionnel pouvant etre une fraction
        quelconque entre 0 et 1, ou aussi, par un Tempus donne, relatif a
        celui de l'Unite Temporelle en question. »
        -- "Segmentation is the operation that divides a Temporal Unit in
        two by a proportional factor, which may be any fraction between 0
        and 1, *or else by a given Tempus, relative to that of the
        Temporal Unit in question*."

    So ``'5/12'`` is the factor itself, while ``Meas('5/12')`` is a
    Tempus and gets multiplied by the inverse of the source's.

    The two Tempi are built raw (TEMPO-5): ``5/2 ⊥ 2/3`` gives
    ``10/6 | 5/6`` where he prints ``5/3 | 5/6``. Same duration, his
    reduction, not a divergence.

    Only Haddad's variant (b) — « scinder » ("to split") — ships. A leaf
    the cut falls inside becomes two independent attacks; a group becomes
    a group on each side. Variant (c), which preserves the straddled
    prolatio « par une liaison rythmique » ("by a rhythmic tie"), needs a
    tie ACROSS the two results, which is ties charter §7 (cross-container
    resolution) and is not implemented — ties today are unit-local. A tie
    group already in the source that straddles the cut therefore becomes
    two unit-local groups, the second one headed by a dangling tie.

    Parameters
    ----------
    rt : RhythmTree
        The tree to divide.
    factor : Fraction, int, float, str, Meas, or list of Meas
        See above. A rational must lie strictly between 0 and 1.
    tie : bool, optional
        Variant (c). Raises ``NotImplementedError``. Default False.

    Returns
    -------
    tuple of RhythmTree
        Exactly two trees, in temporal order.
    """
    from .rhythm_tree import RhythmTree
    from .meas import Meas

    if tie:
        raise NotImplementedError(
            "the tie variant of segmentation (his variant (c), preserving "
            "the straddled prolatio « par une liaison rythmique » -- \"by "
            "a rhythmic tie\") needs a tie ACROSS the two results. That is "
            "ties charter §7, cross-container resolution, which is not "
            "implemented: ties resolve unit-locally only. Use the shipped "
            "split variant (tie=False)."
        )
    if not isinstance(rt, RhythmTree):
        raise TypeError(
            f"segment at RT level takes a RhythmTree; got "
            f"{type(rt).__name__}. For TemporalUnits use "
            f"klotho.chronos.temporal_units.algorithms.segment, which "
            f"returns a two-unit TemporalUnitSequence."
        )

    f = _resolve_segment_factor(rt.meas, factor)
    g = 1 - f

    S = rt.subdivisions
    nodes = _S_to_split_nodes(S)
    total = sum(abs(nd[1]) for nd in nodes)
    left_nodes, right_nodes = _split_nodes(nodes, f * total)

    num, den = rt.meas.numerator, rt.meas.denominator
    return (
        RhythmTree(span=rt.span,
                   meas=Meas(num * f.numerator, den * f.denominator),
                   subdivisions=_split_nodes_to_S(
                       _integerise_nodes(left_nodes))),
        RhythmTree(span=rt.span,
                   meas=Meas(num * g.numerator, den * g.denominator),
                   subdivisions=_split_nodes_to_S(
                       _integerise_nodes(right_nodes))),
    )

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
