from typing import Union, TYPE_CHECKING
from fractions import Fraction
from functools import reduce as _reduce
from itertools import cycle
from math import lcm as _lcm
import copy
from .temporal import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree, Meas
from klotho.chronos.utils import beat_duration
from klotho.chronos.rhythm_trees.algorithms import segment
from klotho.chronos.rhythm_trees.algorithms import (
    decompose as _rt_decompose,
    fuse as _rt_fuse,
    flatten as _rt_flatten,
    _fuse_parts,
)

if TYPE_CHECKING:
    from klotho.thetos.composition.compositional import CompositionalUnit


def _snip_slur_into_sub_uc(original_uc, sub_uc, depth_node, sounding_leaves):
    def _path_sig(tree, root, target):
        branch = list(tree.branch(target))
        root_idx = branch.index(root)
        sig = []
        for j in range(root_idx + 1, len(branch)):
            parent = branch[j - 1]
            current = branch[j]
            sig.append(list(tree.successors(parent)).index(current))
        return tuple(sig)

    def _node_from_sig(tree, root, sig):
        current = root
        for idx in sig:
            current = list(tree.successors(current))[idx]
        return current

    mapped = []
    for old_leaf in sounding_leaves:
        try:
            sig = _path_sig(original_uc._rt, depth_node, old_leaf)
            new_leaf = _node_from_sig(sub_uc._rt, sub_uc._rt.root, sig)
            mapped.append(new_leaf)
        except (ValueError, IndexError):
            continue
    if len(mapped) >= 2:
        try:
            sub_uc.apply_slur(node=mapped)
        except ValueError:
            pass


# def segment_ut(ut: TemporalUnit, ratio: Union[Fraction, float, str]) -> TemporalUnit:
#     """
#     Segments a temporal unit into a new unit with the given ratio. eg, a ratio of 1/3 means
#     the new unit will have a prolatio of (1, 2).
    
#     Args:
#     ut (TemporalUnit): The temporal unit to segment.
#     ratio (Union[Fraction, float, str]): The ratio to segment the unit by.
    
#     Returns:
#     TemporalUnit: A new temporal unit with the given ratio.
#     """
#     return TemporalUnit(span=ut.span, tempus=ut.tempus, prolatio=segment(ratio), beat=ut.beat, bpm=ut.bpm)

def decompose(ut: Union[TemporalUnit, 'CompositionalUnit'], prolatio: Union[tuple, str, None] = None, depth: Union[int, None] = None) -> TemporalUnitSequence:
    """
    Decompose a temporal structure into its constituent parts.

    When *depth* is given, the units are the depth-*depth* frontier: every
    subtree rooted at that depth **plus** every leaf that terminates above
    it, in temporal (onset) order — so the resulting sequence always spans
    the same total duration as the source. ``depth=0`` yields one unit
    equal to the whole structure. Otherwise, each leaf becomes an
    independent unit with the specified *prolatio*.

    Rests are preserved in both branches: a rest leaf decomposes to a rest
    unit regardless of *prolatio*. For a CompositionalUnit without an
    explicit *prolatio*, per-leaf parameters, instruments, and contained
    overlays are preserved; slurs or envelopes spanning multiple resulting
    units cannot survive and are discarded. With an explicit *prolatio* on
    a CompositionalUnit, only the effective pfields and the governing
    instrument survive: authored mfields and contained control envelopes
    are dropped (that arm hand-builds each unit rather than extracting the
    subtree).

    Ties (07_TIES_CHARTER.md sect9): the leaf branch decomposes one unit
    per tie GROUP — a tied group is one sound, so it comes back as one
    fundamental unit whose tempus is the unreduced sum of the members'
    durations (16/21 + 32/35 = 176/105). The group's parameters are the
    head's. In the *depth* branch, ties internal to a frontier subtree
    ride along verbatim; a group crossing a frontier boundary is split
    and its continuation dangles (renders as an attack with a warning)
    until sequence-level resolution exists.

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The temporal structure to decompose.
    prolatio : tuple, str, or None, optional
        The subdivision specification for the resulting units. When None,
        defaults to ``'d'`` (duration). On a CompositionalUnit an explicit
        *prolatio* re-prolates each leaf, with the source leaf's effective
        pfields cascading from the new unit's root. Default is None.
    depth : int or None, optional
        If given, decompose at the specified frontier depth rather than at
        the leaf level. Must be within ``[0, tree depth]``. Cannot be
        combined with *prolatio* on a CompositionalUnit (re-prolating the
        subtrees would discard the per-leaf parameters the depth branch
        exists to preserve). Default is None.

    Returns
    -------
    TemporalUnitSequence
        A sequence of the resulting temporal units.

    Raises
    ------
    ValueError
        If *depth* is outside ``[0, tree depth]``, or if *prolatio* and
        *depth* are combined on a CompositionalUnit.
    """
    
    # Import here to avoid circular imports
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    # A falsy prolatio is an error, not a request for the default. '',
    # 0, False and [] are each rejected by the TemporalUnit constructor,
    # and () is a degenerate empty subdivision the grammar deliberately
    # round-trips; routed through here they used to be swallowed and
    # silently rebuilt as 'd'. Only None means "the default".
    if prolatio is not None and not prolatio:
        raise ValueError(
            f"prolatio must be a non-empty subdivision tuple or prolatio "
            f"string, got {prolatio!r}. Pass prolatio=None for the default "
            f"('d' at the leaf level, the source subdivisions at depth)."
        )

    prolatio_cycle = []

    if isinstance(prolatio, tuple):
        prolatio_cycle = [prolatio]
    elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
        prolatio_cycle = [ut._rt.subdivisions]
    elif prolatio is None:
        prolatio_cycle = ['d']
    else:
        prolatio_cycle = [prolatio]

    prolatio_cycle = cycle(prolatio_cycle)
    
    if depth is not None:
        max_depth = ut._rt.depth
        if not isinstance(depth, int) or isinstance(depth, bool) or not (0 <= depth <= max_depth):
            raise ValueError(
                f"depth must be an int in [0, {max_depth}] for this tree, got {depth!r}"
            )
        if isinstance(ut, CompositionalUnit) and prolatio is not None:
            raise ValueError(
                "prolatio cannot be combined with depth on a CompositionalUnit: "
                "re-prolating the subtrees would discard the per-leaf parameters "
                "the depth decomposition exists to preserve. Decompose without "
                "prolatio, or re-prolate the resulting units afterwards."
            )
        # The frontier: nodes at exactly `depth` plus every leaf that
        # terminates above it, in temporal order — otherwise shallow
        # branches silently vanish from the result.
        frontier = set(ut._rt.at_depth(depth))
        frontier.update(n for n in ut._rt.leaf_nodes if ut._rt.depth_of(n) < depth)
        nodes_at_depth = sorted(frontier, key=lambda n: ut._rt[n]['metric_onset'])
        leaf_set = set(ut._rt.leaf_nodes)
        units = []

        for node in nodes_at_depth:
            if isinstance(ut, CompositionalUnit):
                cu_subtree = ut.from_subtree(node)
                units.append(cu_subtree)
            else:
                metric_duration = ut._rt[node]['metric_duration']
                is_rest = ut._rt[node].get('proportion', 1) < 0
                if prolatio is None:
                    # The node's own subdivisions ride along verbatim,
                    # signs included -- but a bare leaf has no
                    # subdivisions, and group.S's (1,) wrapper fallback
                    # would turn a rest leaf into an attack.
                    node_prolatio = (
                        'r' if (is_rest and node in leaf_set)
                        else ut._rt.subtree(node).group.S
                    )
                else:
                    # Silence stays silence at every granularity: a rest
                    # GROUP -- an interior node with a negative proportion
                    # -- is as much a rest as a rest leaf, and re-prolating
                    # it would turn a whole unit of silence into audio.
                    node_prolatio = 'r' if is_rest else next(prolatio_cycle)
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = abs(metric_duration),
                    prolatio = node_prolatio,
                    beat     = ut._beat,
                    bpm      = ut._bpm
                )
                units.append(unit)

        if isinstance(ut, CompositionalUnit) and getattr(ut, '_slur_specs', None):
            depth_leaf_sets = {
                node: set(ut._rt.subtree_leaves(node))
                for node in nodes_at_depth
            }
            for slur_spec in ut._slur_specs.values():
                slur_leaves = list(slur_spec['leaf_nodes'])
                slur_leaf_set = set(slur_leaves)
                for i, depth_node in enumerate(nodes_at_depth):
                    local_leaves = depth_leaf_sets[depth_node]
                    if slur_leaf_set.issubset(local_leaves):
                        break
                    portion = [l for l in slur_leaves if l in local_leaves]
                    sounding = [
                        l for l in portion
                        if ut._rt[l].get('proportion', 1) >= 0
                    ]
                    if len(sounding) < 2:
                        continue
                    cu_sub = units[i]
                    _snip_slur_into_sub_uc(ut, cu_sub, depth_node, sounding)
        
        return TemporalUnitSequence(units)
    else:
        units = []
        # One product per tie GROUP (charter sect9): a tied group is one
        # sound, so it decomposes to one fundamental unit whose tempus is
        # the unreduced raw-int sum of the members' durations on their
        # common denominator (TEMPO-5's discipline). On a tie-free tree
        # every group is a single leaf and nothing changes.
        groups = ut._rt.tie_groups

        def _group_meas(group):
            if len(group) == 1:
                return Meas(abs(ut._rt[group[0]]['metric_duration']))
            mds = [ut._rt[n]['metric_duration'] for n in group]
            den = _reduce(_lcm, (m.denominator for m in mds), 1)
            num = sum(m.numerator * (den // m.denominator) for m in mds)
            return Meas(num, den)

        if isinstance(ut, CompositionalUnit):
            if prolatio is None:
                # from_subtree preserves the leaf's effective pfields,
                # governing instrument, and rest state. A tied group takes
                # the HEAD's subtree (the head governs, charter sect4) and
                # re-spells its tempus to the group sum at the source
                # tempo; a dangling leading tie is dropped by the subtree
                # extraction (the NEW-40 residue class).
                for group in groups:
                    head = group[0]
                    sub = ut.from_subtree(head)
                    if len(group) > 1:
                        grp = modulate_tempus(sub, 1, _group_meas(group))
                        grp._bpm = sub.bpm  # tempus rewrite at FIXED tempo:
                        # duration expands to the group span
                        grp._invalidate_timing_cache()
                        units.append(grp)
                    else:
                        units.append(sub)
            else:
                # An explicit prolatio reshapes each sounding event: the
                # head's effective pfields cascade from the new unit's
                # root. Rests stay rests regardless of the requested
                # prolatio. (ut[ordinal] is event-indexed, so it IS the
                # group's head event.)
                for ordinal, group in enumerate(groups):
                    head = group[0]
                    is_rest = ut._rt[head].get('proportion', 1) < 0
                    unit = CompositionalUnit(
                        span     = 1,
                        tempus   = _group_meas(group),
                        prolatio = 'r' if is_rest else next(prolatio_cycle),
                        beat     = ut._beat,
                        bpm      = ut._bpm,
                        pfields  = ut.pfields
                    )
                    if not is_rest:
                        unit.set_pfields(unit._rt.root, **ut[ordinal].pfields)
                    governing = ut._rt._resolve_governing_instrument_node(head)
                    if governing is not None and governing in ut._rt.node_instruments:
                        unit.set_instrument(unit._rt.root, ut._rt.node_instruments[governing])
                    units.append(unit)
        else:
            # Rest groups decompose to rest units -- the decomposed
            # sequence must sound identical to the source. A dangling
            # leading tie (head itself tied) keeps its marker under the
            # default prolatio, so a later sequence resolution can still
            # see it.
            rx = ut._rt._rx
            for group in groups:
                head_data = rx.get_node_data(group[0])
                is_rest = head_data.get('proportion', 1) < 0
                if is_rest:
                    prol = 'r'
                else:
                    prol = next(prolatio_cycle)
                    if prol == 'd' and head_data.get('tied', False):
                        prol = (1.0,)
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = _group_meas(group),
                    prolatio = prol,
                    beat     = ut._beat,
                    bpm      = ut._bpm
                )
                units.append(unit)

        return TemporalUnitSequence(units)

# def transform(structure: TemporalMeta) -> TemporalMeta:
    
#     match structure:
#         case TemporalUnit():
#             return TemporalBlock([ut for ut in decompose(structure).seq])
            
#         case TemporalUnitSequence():
#             return TemporalBlock([ut.copy() for ut in structure.seq])
            
#         case TemporalBlock():
#             raise NotImplementedError("Block transformation not yet implemented")
            
#         case _:
#             raise ValueError(f"Unknown temporal structure type: {type(structure)}")

def fuse(*operands, reference=None):
    """
    Fuse temporal material into ONE unit — Haddad's ‖, lifted (ruling R13).

    The symbolic core is :func:`klotho.chronos.rhythm_trees.algorithms.fuse`;
    this surface lifts each operand to its tree, reconciles mixed tempi by
    THE rule (LAYER-3), fuses symbolically, and re-temporalises at the
    reference. Closure per layer: all-RhythmTree operands return a
    RhythmTree; TemporalUnit operands return a TemporalUnit.

    **The reconciliation rule** (R13-B/C/D): when operands' (beat, bpm)
    differ, each is re-expressed at the FIRST temporalised operand's
    reference by sect4.4.4 (T' = T x (bpm_ref/bpm) x (beat_ref/beat)), in
    exact rational arithmetic with the tempus assembled unreduced
    (TEMPO-5) — every operand's real clock durations are retained and only
    metric spellings change. The result carries the reference, never a
    third value. ``reference=(beat, bpm)`` overrides; no operator ever
    defaults to a reference the operands don't carry.

    Nesting (R13-I — reconcile representation, refuse musical decisions):

    - a ``TemporalUnitSequence`` fuses depth-first into one part;
    - a bare ``RhythmTree`` among temporalised operands adopts the
      reference verbatim (his p. 97 convention: when fixed-time and
      mobile-time units combine, the relative units' relativity takes
      precedence and the absolute takes the shared reference);
    - a ``TemporalBlock`` REFUSES loudly — collapsing polyphony into one
      voice has no unique answer (fuse per row via BT-3's row-wise verb
      and choose explicitly);
    - a ``CompositionalUnit`` is the next staged surface (R13-E) and
      raises ``NotImplementedError`` until its parameter-state merge
      ships.

    Parameters
    ----------
    *operands : RhythmTree, TemporalUnit, or TemporalUnitSequence
        The material, in temporal order. A single list/tuple argument is
        unrolled.
    reference : tuple of (beat, bpm), optional
        Explicit reconciliation reference. Only legal when at least one
        operand is temporalised.

    Returns
    -------
    RhythmTree or TemporalUnit
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    ops = list(operands[0]) if (
        len(operands) == 1 and isinstance(operands[0], (list, tuple))
    ) else list(operands)
    if not ops:
        raise ValueError("fuse requires at least one operand")

    resolved = []
    for op in ops:
        if isinstance(op, TemporalBlock):
            raise ValueError(
                "a TemporalBlock cannot be fused: collapsing polyphony "
                "into one voice has no unique answer, and choosing one "
                "would choose music for the composer. Fuse each row to a "
                "uniform Tempus instead (the row-wise verb, docket BT-3), "
                "then decide what the rows become."
            )
        if isinstance(op, CompositionalUnit):
            raise NotImplementedError(
                "fuse for CompositionalUnits is the next staged surface "
                "(R13-E): the parameter/slur/envelope state must merge "
                "under the raw-copy discipline. Fuse `uc.rt` for the "
                "rhythm alone, or wait for the staged surface."
            )
        if isinstance(op, TemporalUnitSequence):
            resolved.append(fuse(*op.seq, reference=reference))
        elif isinstance(op, (TemporalUnit, RhythmTree)):
            resolved.append(op)
        else:
            raise TypeError(
                f"fuse takes RhythmTree, TemporalUnit, or "
                f"TemporalUnitSequence operands; got {type(op).__name__}"
            )

    units = [op for op in resolved if isinstance(op, TemporalUnit)]
    if not units:
        if reference is not None:
            raise ValueError(
                "symbolic operands carry no tempo to reconcile; a "
                "reference applies only when temporalised operands are "
                "present. Temporalise with TemporalUnit.from_rt, or drop "
                "reference=."
            )
        return _rt_fuse(resolved)

    if reference is not None:
        ref_beat, ref_bpm = Fraction(reference[0]), reference[1]
    else:
        ref_beat, ref_bpm = units[0].beat, units[0].bpm

    parts = []
    for op in resolved:
        if isinstance(op, TemporalUnit):
            factor = ((_exact_tempo_ratio(ref_bpm) / _exact_tempo_ratio(op.bpm))
                      * (ref_beat / op.beat) * Fraction(op.span))
            parts.append((op.tempus.numerator * factor.numerator,
                          op.tempus.denominator * factor.denominator,
                          op.prolationis))
        else:  # RhythmTree: untimed — adopts the reference verbatim
            parts.append((op.meas.numerator * op.span,
                          op.meas.denominator, op.subdivisions))
    total, den, s_out = _fuse_parts(parts)
    out = TemporalUnit(span=1, tempus=Meas(total, den), prolatio=s_out,
                       beat=ref_beat, bpm=ref_bpm)
    # Attribution (NEW-39's lift-rule wrinkle): the computed tempus is
    # attributed by definition; beat/bpm are attributed only if the caller
    # gave a reference or some operand attributed them — a fuse of
    # unattributed operands stays unattributed and keeps following the
    # future ambient dial.
    attributed = {'tempus'}
    if reference is not None:
        attributed |= {'beat', 'bpm'}
    else:
        for slot in ('beat', 'bpm'):
            if any(slot in u.attributed for u in units):
                attributed.add(slot)
    out._attributed = frozenset(attributed)
    return out


def flatten(obj):
    """
    Project temporal material onto its canonical one-level spelling —
    Haddad's *réduction* (ALG-4), lifted per ruling R13.

    The symbolic core is
    :func:`klotho.chronos.rhythm_trees.algorithms.flatten`. On a
    TemporalUnit the projection is unary and tempo is untouched: the
    result re-temporalises at the unit's own beat/bpm, so it sounds
    identical to the source (exact onsets and durations), with one term
    per sounding event and ``sum(|prolatio|) == meas.numerator``.
    Idempotent; a no-op exactly on already-canonical input.

    Parameters
    ----------
    obj : RhythmTree or TemporalUnit
        A CompositionalUnit raises ``NotImplementedError`` until its
        staged surface ships (R13-E); for a sequence, use :func:`fuse`.

    Returns
    -------
    RhythmTree or TemporalUnit
    """
    from klotho.thetos.composition.compositional import CompositionalUnit
    if isinstance(obj, CompositionalUnit):
        raise NotImplementedError(
            "flatten for CompositionalUnits is a staged surface (R13-E); "
            "flatten `uc.rt` for the rhythm alone."
        )
    if isinstance(obj, TemporalUnit):
        flat = _rt_flatten(obj._rt)
        out = TemporalUnit(span=1, tempus=flat.meas,
                           prolatio=flat.subdivisions,
                           beat=obj.beat, bpm=obj.bpm)
        out._attributed = frozenset(
            {'tempus'} | (obj.attributed & {'beat', 'bpm'}))
        return out
    if isinstance(obj, RhythmTree):
        return _rt_flatten(obj)
    raise TypeError(
        f"flatten is unary on a RhythmTree or TemporalUnit; got "
        f"{type(obj).__name__}. For a sequence, use fuse(...)."
    )


def _exact_tempo_ratio(value) -> Fraction:
    """Exact rational form of a tempo/beat quantity for reconciliation.

    Floats are snapped by ``limit_denominator(10**6)``, which recovers the
    intended rational for every musically plausible value (87.3 is exactly
    873/10) rather than the exact-but-monstrous binary expansion; exact
    types pass through untouched.
    """
    if isinstance(value, float):
        return Fraction(value).limit_denominator(10**6)
    return Fraction(value)


def modulate_tempo(ut: Union[TemporalUnit, 'CompositionalUnit'], beat: Union[Fraction, str, float], bpm: Union[int, float]) -> Union[TemporalUnit, 'CompositionalUnit']:
    """
    Create a new unit with specified beat/bpm, preserving the original duration.

    The tempus is adjusted so that the resulting unit has the same duration
    as *ut* under the new tempo parameters. This is Haddad's sect4.4.4
    correlation-by-modulation: T2 = T1 x (bpm2/bpm1) x (beat2/beat1).

    The new tempus is assembled from raw ints, UNREDUCED (TEMPO-5, ruling
    R13-D): modulating a unit to its own beat/bpm is a true no-op -- 6/20
    stays 6/20, never 3/10 -- because reducing a Tempus changes the unit's
    nature (Haddad sect4.4.2/4.4.5).

    Note the span collapse: the result always has ``span=1``, with the
    source's span folded into the tempus numerator (span 2 of 6/20 comes
    back as 12/20).

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The original temporal unit.
    beat : Fraction, str, or float
        The new beat value.
    bpm : int or float
        The new beats per minute. Floats are snapped to the intended
        rational by ``limit_denominator(10**6)`` for the tempus
        arithmetic; the value itself is stored as given.

    Returns
    -------
    TemporalUnit or CompositionalUnit
        A new unit with adjusted tempus and the specified beat/bpm.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    new_beat = Fraction(beat)
    # ratio x span as one exact Fraction, then applied to the tempus as
    # raw ints -- Fraction reduces ratio*span internally, but the tempus'
    # own numerator/denominator are never cancelled against each other
    factor = ((_exact_tempo_ratio(bpm) / _exact_tempo_ratio(ut.bpm))
              * (new_beat / ut.beat) * Fraction(ut.span))
    new_tempus = Meas(ut.tempus.numerator * factor.numerator,
                      ut.tempus.denominator * factor.denominator)

    if isinstance(ut, CompositionalUnit):
        new_cu = CompositionalUnit(
            span=1,
            tempus=new_tempus,
            prolatio=ut.prolationis,
            beat=beat,
            bpm=bpm,
            pfields=ut.pfields
        )
        new_cu._mirror_param_state(ut)
        new_cu._slur_specs = ut._copy_slur_specs()
        new_cu._next_slur_id = ut._next_slur_id
        new_cu._control_envelopes = ut._copy_control_envelopes()
        new_cu._next_envelope_id = ut._next_envelope_id
        return new_cu
    else:
        return TemporalUnit(
            span=1,
            tempus=new_tempus,
            prolatio=ut.prolationis,
            beat=beat,
            bpm=bpm
        )

def modulate_tempus(ut: Union[TemporalUnit, 'CompositionalUnit'], span: int, tempus: Union[Meas, Fraction, float, str]) -> Union[TemporalUnit, 'CompositionalUnit']:
    """
    Create a new unit with specified tempus, preserving the original duration.

    The bpm is adjusted so that the resulting unit has the same duration
    as *ut* under the new tempus and span. Note the output bpm is computed
    through float division, so chained modulations park float noise in the
    bpm (e.g. 52.50000000000001) -- the tempus stays exactly as given.

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The original temporal unit.
    span : int
        The new span value.
    tempus : Meas, Fraction, float, or str
        The new time signature.

    Returns
    -------
    TemporalUnit or CompositionalUnit
        A new unit with the specified tempus and adjusted bpm.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if not isinstance(tempus, Meas):
        tempus = Meas(tempus)
    
    ratio = beat_duration((tempus * span).to_fraction(), ut.bpm, ut.beat) / beat_duration((ut.tempus * ut.span).to_fraction(), ut.bpm, ut.beat)

    if isinstance(ut, CompositionalUnit):
        new_cu = CompositionalUnit(
            span=span,
            tempus=tempus,
            prolatio=ut.prolationis,
            beat=ut.beat,
            bpm=ut.bpm * ratio,
            pfields=ut.pfields
        )
        new_cu._mirror_param_state(ut)
        new_cu._slur_specs = ut._copy_slur_specs()
        new_cu._next_slur_id = ut._next_slur_id
        new_cu._control_envelopes = ut._copy_control_envelopes()
        new_cu._next_envelope_id = ut._next_envelope_id
        return new_cu
    else:
        return TemporalUnit(
            span=span,
            tempus=tempus,
            prolatio=ut.prolationis,
            beat=ut.beat,
            bpm=ut.bpm * ratio
        )

def _is_rest_unit(ut) -> bool:
    """Whether a unit is silence throughout (every leaf a rest)."""
    rx = ut._rt._rx
    return all(rx.get_node_data(n).get('proportion', 1) < 0
               for n in ut._rt.leaf_nodes)


def convolve(x: Union[TemporalUnit, 'CompositionalUnit', TemporalUnitSequence], h: Union[TemporalUnit, 'CompositionalUnit', TemporalUnitSequence], reference=None) -> TemporalUnitSequence:
    """
    Convolve two temporal structures to produce a new sequence.

    Both inputs are first decomposed (if not already sequences) — the
    decomposition is sign-carrying and tie-aware, so rests contribute
    NEGATIVE terms (products carry the sign algebra, and negative outputs
    render as rests) and a tied group counts as one term. Terms are
    reconciled to one reference by sect4.4.4 modulation (real durations
    preserved; TEMPO-5's unreduced discipline, so a same-tempo
    reconciliation is a true no-op), then convolved in the
    signal-processing sense. Zero-valued outputs are deleted, per his
    stated algorithm.

    **The reference contract (R13-B, repealing the old hardcoded
    ``'1/4' @ 60``):** the reference defaults to the FIRST operand's own
    (beat, bpm); no reference the operands don't carry is ever chosen
    silently. Because convolution is bilinear in the operands' metric
    values, the choice of reference scales the metric results — which is
    why it must be the caller's, explicitly or through the first operand.

    Parameters
    ----------
    x : TemporalUnit, CompositionalUnit, or TemporalUnitSequence
        The first temporal structure (signal). Its (beat, bpm) — or its
        first unit's, for a sequence — is the default reference.
    h : TemporalUnit, CompositionalUnit, or TemporalUnitSequence
        The second temporal structure (kernel).
    reference : tuple of (beat, bpm), optional
        Explicit reconciliation reference.

    Returns
    -------
    TemporalUnitSequence
        At most ``len(x) + len(h) - 1`` units at the reference tempo
        (zero terms deleted); negative terms come back as rests.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    if isinstance(x, (TemporalUnit, CompositionalUnit)):
        x = decompose(x)
    if isinstance(h, (TemporalUnit, CompositionalUnit)):
        h = decompose(h)
    if not x.seq or not h.seq:
        raise ValueError("convolve requires non-empty operands")

    if reference is None:
        beat, bpm = x.seq[0].beat, x.seq[0].bpm
    else:
        beat, bpm = Fraction(reference[0]), reference[1]

    def _terms(seq):
        vals = []
        for u in seq.seq:
            value = modulate_tempo(u, beat, bpm).tempus.to_fraction()
            vals.append(-value if _is_rest_unit(u) else value)
        return vals

    xs, hs = _terms(x), _terms(h)
    y = []
    for n in range(len(xs) + len(hs) - 1):
        s = Fraction(0, 1)
        for k in range(len(xs)):
            m = n - k
            if 0 <= m < len(hs):
                s += xs[k] * hs[m]
        if s != 0:
            y.append(s)

    return TemporalUnitSequence([
        TemporalUnit(span=1, tempus=abs(r),
                     prolatio='d' if r > 0 else 'r',
                     beat=beat, bpm=bpm)
        for r in y
    ])
