from typing import Union, TYPE_CHECKING
from fractions import Fraction
from functools import reduce as _reduce
from itertools import cycle
from math import lcm as _lcm
import copy
from .temporal import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree, Meas
from klotho.chronos.utils import beat_duration
from klotho.chronos.rhythm_trees.algorithms import (
    decompose as _rt_decompose,
    fuse as _rt_fuse,
    flatten as _rt_flatten,
    segment as _rt_segment,
    augment as _rt_augment,
    diminish as _rt_diminish,
    scale_tempus as _rt_scale_tempus,
    _fuse_parts,
)

if TYPE_CHECKING:
    from klotho.thetos.composition.compositional import CompositionalUnit


def _reanchor_contained_envelopes(original_uc, sub_uc, group):
    """Carry every control envelope living inside one tie group into the
    unit that group became.

    The explicit-prolatio arm hand-builds each unit instead of extracting
    a subtree, so it has to redo by hand what ``from_subtree`` does. An
    envelope whose resolved leaves all fall inside this group has exactly
    one home; re-anchoring it at the new unit's root with no leaf subset
    spreads it over the re-prolated leaves, the same cascade the head's
    pfields get. An envelope crossing several groups has no single home
    and is dropped -- the documented loss for spanning overlays.
    """
    descriptors = getattr(original_uc, '_control_envelopes', None)
    if not descriptors:
        return
    group_leaves = set(group)
    for desc in descriptors.values():
        env_leaves = set(original_uc._resolve_control_envelope_leaves(desc))
        if not env_leaves or not env_leaves.issubset(group_leaves):
            continue
        new_env_id = sub_uc._next_envelope_id
        sub_uc._next_envelope_id += 1
        sub_uc._control_envelopes[new_env_id] = {
            "envelope": desc["envelope"],
            "pfields": list(desc["pfields"]),
            "endpoint": desc["endpoint"],
            "anchor_node": sub_uc._rt.root,
            "leaf_subset": None,
        }


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


def _coerce_segment_factor(factor):
    """Lower a UT-level factor to the RT core's vocabulary.

    Adds one convenience the RT layer cannot have: the members of a list
    factor may be ``TemporalUnit``s, which is literally his fig. 4.73(b)-(c)
    workflow — decompose a composed unit, then use the resulting
    fundamental units as segmentation proportions. Their spans fold in.
    """
    if isinstance(factor, (list, tuple)):
        out = []
        for m in factor:
            if isinstance(m, TemporalUnit):
                value = (Fraction(m.tempus.numerator, m.tempus.denominator)
                         * Fraction(m.span))
                out.append(Meas(value.numerator, value.denominator))
            else:
                out.append(m)
        return out
    if isinstance(factor, TemporalUnit):
        value = (Fraction(factor.tempus.numerator, factor.tempus.denominator)
                 * Fraction(factor.span))
        return Meas(value.numerator, value.denominator)
    return factor


def segment(obj, factor, tie: bool = False):
    """
    Divide a temporal unit in two — Haddad's segmentation operator (⊥).

    ``T ⊥ f => [T·f | T·(1−f)]``, returning a
    :class:`TemporalUnitSequence` of **exactly two units**. The symbolic
    core is :func:`klotho.chronos.rhythm_trees.algorithms.segment`
    (sect4.5.3.1, pp. 129–131, figs. 4.71–4.74). Span, beat and bpm carry
    over unchanged, so the two halves together sound for exactly as long
    as the source.

    TWO CALLING CONVENTIONS, and they are not interchangeable spellings:

        « La segmentation est l'operation qui divise une Unite Temporelle
        en deux par un facteur proportionnel pouvant etre une fraction
        quelconque entre 0 et 1, ou aussi, par un Tempus donne, relatif a
        celui de l'Unite Temporelle en question. »
        -- "Segmentation is the operation that divides a Temporal Unit in
        two by a proportional factor, which may be any fraction between 0
        and 1, *or else by a given Tempus, relative to that of the
        Temporal Unit in question*."

    ``segment(ut, '5/12')`` uses 5/12 as the factor. ``segment(ut,
    Meas('25/24'))`` reads 25/24 as a Tempus and converts it against the
    source's, ``25/24 x 2/5 = 5/12`` (fig. 4.73). A list is summed first,
    his n-th-unit form: ``(15/24 + 20/24) x 2/5 = 7/12`` (fig. 4.74), and
    its members may be ``TemporalUnit``s straight out of
    :func:`decompose`.

    Tempi are built raw (TEMPO-5): ``5/2 ⊥ 2/3`` gives ``10/6 | 5/6``
    where he prints ``5/3 | 5/6``. Same duration; he reduced.

    Only his variant (b) — « scinder » ("to split") — ships. The leaf the
    cut falls inside becomes two independent attacks; a group becomes a
    group on each side, so nesting survives. Variant (c) preserves the
    straddled prolatio « par une liaison rythmique » ("by a rhythmic
    tie") and needs a tie between the two RESULTING units, which is ties
    charter §7 (cross-container resolution) and is not implemented.

    Parameters
    ----------
    obj : TemporalUnit or RhythmTree
        A ``RhythmTree`` returns the symbolic pair (two trees) instead. A
        ``CompositionalUnit`` raises ``NotImplementedError``: splitting a
        leaf in two forces a decision about its parameter state, which is
        a staged surface (R13-E). Segmentation is unary on a unit — for a
        sequence or a block, segment the member.
    factor : Fraction, int, float, str, Meas, TemporalUnit, or list
        See above.
    tie : bool, optional
        Variant (c). Raises ``NotImplementedError``. Default False.

    Returns
    -------
    TemporalUnitSequence
        Exactly two units, in temporal order.

    Examples
    --------
    >>> ut = TemporalUnit(tempus='5/2', prolatio=(1,))
    >>> [str(u.tempus) for u in segment(ut, '1/8').seq]
    ['5/16', '35/16']
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    if isinstance(obj, CompositionalUnit):
        raise NotImplementedError(
            "segment for CompositionalUnits is a staged surface (R13-E): "
            "the cut splits a leaf in two, and what its pfields, "
            "envelopes and slurs become is a decision no default can "
            "make. Segment `uc.rt` for the rhythm alone."
        )
    if isinstance(obj, TemporalUnit):
        left, right = _rt_segment(obj._rt,
                                  _coerce_segment_factor(factor),
                                  tie=tie)
        units = []
        for part in (left, right):
            unit = TemporalUnit(span=part.span, tempus=part.meas,
                                prolatio=part.subdivisions,
                                beat=obj.beat, bpm=obj.bpm)
            unit._attributed = frozenset(
                {'tempus'} | (obj.attributed & {'beat', 'bpm'}))
            units.append(unit)
        return TemporalUnitSequence(units)
    if isinstance(obj, RhythmTree):
        return _rt_segment(obj, factor, tie=tie)
    raise TypeError(
        f"segment is unary on a TemporalUnit or a RhythmTree; got "
        f"{type(obj).__name__}. A TemporalUnitSequence or TemporalBlock "
        f"holds several units, and there is no single Tempus to divide -- "
        f"segment the member you mean."
    )

def decompose(ut: Union[TemporalUnit, 'CompositionalUnit'], prolatio: Union[tuple, str, None] = None, depth: Union[int, None] = None) -> TemporalUnitSequence:
    """
    Decompose a temporal structure into its constituent parts.

    When *depth* is given, the units are the depth-*depth* frontier: every
    subtree rooted at that depth **plus** every leaf that terminates above
    it, in temporal (onset) order — so the resulting sequence always spans
    the same total duration as the source. ``depth=0`` yields one unit
    equal to the whole structure. Otherwise, each leaf becomes an
    independent unit with the specified *prolatio*.

    Rests are preserved in both branches, at every granularity: a rest
    leaf decomposes to a rest unit regardless of *prolatio*, and in the
    depth branch a rest GROUP — an interior node with a negative
    proportion — becomes a whole rest unit rather than being re-prolated
    into sound. One rest does NOT survive: a rest child inside a
    *sounding* interior node is lost when an explicit *prolatio* replaces
    that node's subdivisions, which is inherent to re-prolation — the
    requested shape is the one that is built.

    For a CompositionalUnit without an explicit *prolatio*, per-leaf
    parameters, instruments, and contained overlays are preserved; an
    overlay spanning multiple resulting units cannot survive and is
    discarded. With an explicit *prolatio* on a CompositionalUnit, the
    effective pfields, the effective mfields, the governing instrument,
    and any control envelope contained in a single source event survive;
    slurs and spanning envelopes are dropped (each unit is one event, so
    a slur has nothing left to join).

    In the *depth* branch a slur spanning several frontier units is NOT
    discarded — it is snipped into per-unit partial slurs, one per unit
    that holds two or more of its sounding leaves.

    Ties (07_TIES_CHARTER.md sect9): the leaf branch decomposes one unit
    per tie GROUP — a tied group is one sound, so it comes back as one
    fundamental unit whose tempus is the unreduced sum of the members'
    durations (16/21 + 32/35 = 176/105). The group's parameters are the
    head's. A leading dangler (the head itself tied) keeps its ``(1.0,)``
    marker on a TemporalUnit but loses it on a CompositionalUnit, whose
    subtree extraction does not carry it — the NEW-40 residue class.

    In the *depth* branch, ties internal to a frontier subtree ride along
    verbatim. A group crossing a frontier boundary is split and its
    continuation dangles: at a cut ABOVE the tied leaf the dangler
    survives and renders as an attack with a warning, but when the
    frontier lands ON the tied leaf itself the marker is dropped
    silently, because a bare frontier leaf takes ``group.S``'s ``(1,)``
    wrapper fallback and the depth branch has no equivalent of the leaf
    branch's re-marking. Also NEW-40 residue.

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The temporal structure to decompose.
    prolatio : tuple, str, or None, optional
        The subdivision specification for the resulting units.

        - ``None`` (default) means the default shape: ``'d'`` in the leaf
          branch, and in the depth branch each node's own subdivisions,
          carried across verbatim.
        - A tuple is used as the subdivision of every resulting unit.
        - ``'s'`` means the SOURCE TREE'S ROOT subdivisions — the whole
          tree's ``S``, stamped onto every resulting unit at any depth,
          not the per-node subdivisions that ``None`` gives.
        - Any other string is passed to the TemporalUnit constructor.

        A falsy value that is not None (``''``, ``()``, ``0``, ``False``,
        ``[]``) raises: these used to be coerced to ``'d'``, masking an
        error the constructor would otherwise have raised.

        On a CompositionalUnit an explicit *prolatio* re-prolates each
        leaf, with the source leaf's effective pfields cascading from the
        new unit's root. Default is None.
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
    TypeError
        If *ut* is not a TemporalUnit (a CompositionalUnit is one).
    ValueError
        If *depth* is outside ``[0, tree depth]``, if *prolatio* is falsy
        but not None, or if *prolatio* and *depth* are combined on a
        CompositionalUnit.
    """

    # Import here to avoid circular imports
    from klotho.thetos.composition.compositional import CompositionalUnit

    if not isinstance(ut, TemporalUnit):
        raise TypeError(
            f"decompose is unary on a TemporalUnit or CompositionalUnit; "
            f"got {type(ut).__name__}. For a RhythmTree use "
            f"klotho.chronos.rhythm_trees.algorithms.decompose."
        )

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
                        pfields  = ut.pfields,
                        # mfield NAMES too, not just values: without the
                        # registry the schema is gone, and a later
                        # set_mfields on the new unit has nothing to write
                        # into. (ut.mfields is a sorted name list that
                        # always contains 'group' -- see the constructor.)
                        mfields  = ut.mfields
                    )
                    if not is_rest:
                        unit.set_pfields(unit._rt.root, **ut[ordinal].pfields)
                        unit.set_mfields(unit._rt.root, **ut[ordinal].mfields)
                        _reanchor_contained_envelopes(ut, unit, group)
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


# ------------------------------------------------------------------------------------
# The Tempus-FOLLOWING operator family, lifted (docket OPS-2/3/4).
#
# *Follows* means the Tempus is recomputed and **bpm is held**, so the
# real duration changes and the notation changes with it. Haddad has no
# tempo at all — for him the axis is two-valued (« prolationnelle
# stricte » / « relative », "strictly prolational" / "relative") — so the
# bpm-holding half of the policy is Klotho's, and it is the reading that
# makes his sentence true here: « le Tempus est la somme des prolationis
# une fois transformés » ("the Tempus is the sum of the prolationis once
# transformed") is a claim about notation, and only a held tempo lets the
# notation carry it.
# ------------------------------------------------------------------------------------


def _following_target(obj, verb):
    """Resolve what a following-family verb was called on.

    Returns ``'ut'`` or ``'rt'``. A ``CompositionalUnit`` is refused
    FIRST — it subclasses ``TemporalUnit``, so an isinstance chain that
    checked the base first would silently drop its parameter state.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    if isinstance(obj, CompositionalUnit):
        raise NotImplementedError(
            f"{verb} for CompositionalUnits is a staged surface (R13-E). "
            f"The whole following family rebuilds the tree from its "
            f"decomposition, and carrying the pfields, mfields, envelopes "
            f"and slurs across that rebuild is the staged work -- not an "
            f"impossibility: `RhythmTree._respell` already carries them "
            f"through a rebuild that destroys leaf identity, which is how "
            f"`CompositionalTree.extract` keeps its pfields. Apply it to "
            f"`uc.rt` for the rhythm alone."
        )
    if isinstance(obj, TemporalUnit):
        return 'ut'
    if isinstance(obj, RhythmTree):
        return 'rt'
    raise TypeError(
        f"{verb} is unary on a TemporalUnit or a RhythmTree; got "
        f"{type(obj).__name__}. A TemporalUnitSequence or TemporalBlock "
        f"holds several units and so several Tempi, and this family "
        f"recomputes exactly one -- apply it to the member you mean."
    )


def _following_result(obj, tree):
    """Re-temporalise a following-family result at the source's tempo.

    bpm and beat pass through untouched; the tempus is new by definition,
    so it is attributed, and beat/bpm keep whatever attribution the
    source carried (NEW-39's lift rule, as ``flatten`` and ``segment``
    already do it).
    """
    out = TemporalUnit(span=1, tempus=tree.meas, prolatio=tree.subdivisions,
                       beat=obj.beat, bpm=obj.bpm)
    out._attributed = frozenset(
        {'tempus'} | (obj.attributed & {'beat', 'bpm'}))
    return out


def diminish(obj, positions):
    """
    Delete prolationes and let the Tempus follow — Haddad's diminution (⊟).

    The symbolic core is
    :func:`klotho.chronos.rhythm_trees.algorithms.diminish` (sect4.5.2.2,
    p. 126, figs. 4.62–4.63):

        « Le tempus sera par conséquent recalculé à partir de la somme des
        prolationis restants. »
        -- "The tempus will consequently be recomputed from the sum of the
        remaining prolationis."

    On a ``TemporalUnit``, **beat and bpm are held** and the Tempus
    shrinks, so the unit really does get shorter — that is what
    distinguishes this from extraction (⊖), which holds the Tempus and
    dilates the survivors to fill the same bar. ``18/18 (4 2 3 6 3) ⊟ (0)``
    gives ``14/18 (2 3 6 3)``, 14/18ths of the source's duration.

    Tempi are built raw (TEMPO-5): he prints that 14/18 as ``7/9``. Same
    duration; he reduced.

    Positions index the DECOMPOSED sequence — one entry per tie group
    (ALG-2), not per leaf — 0-based, ``0`` the head.

    Parameters
    ----------
    obj : TemporalUnit or RhythmTree
        A ``RhythmTree`` returns a ``RhythmTree``. A ``CompositionalUnit``
        raises ``NotImplementedError`` (R13-E).
    positions : int or sequence of int

    Returns
    -------
    TemporalUnit or RhythmTree

    Examples
    --------
    >>> ut = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
    >>> str(diminish(ut, 0).tempus)
    '14/18'
    """
    if _following_target(obj, 'diminish') == 'rt':
        return _rt_diminish(obj, positions)
    return _following_result(obj, _rt_diminish(obj._rt, positions))


def scale_tempus(obj, ratios, positions):
    """
    Scale prolationes and let the Tempus follow — Haddad's
    dilatation/contraction (⊠).

    The symbolic core is
    :func:`klotho.chronos.rhythm_trees.algorithms.scale_tempus`
    (sect4.5.2.3, pp. 127–128, figs. 4.66–4.69). ONE operator: the ratio's
    size decides the direction, which is why the verb is not ``dilate``.
    Its preserving sibling is ``RhythmTree.scale`` (⊗), which holds the
    Tempus and re-spells the contents against it.

    On a ``TemporalUnit``, **beat and bpm are held**, so the Tempus change
    is a real change of duration: ``18/18 (4 2 3 6 3) ⊠ ((3),(2))`` gives
    ``24/18``, 24/18ths of the source's duration, notated as a longer bar
    at the same tempo.

    Positions index the DECOMPOSED sequence — one entry per tie group
    (ALG-2) — 0-based, p. 127: "0 being the first prolatio".

    Parameters
    ----------
    obj : TemporalUnit or RhythmTree
        A ``RhythmTree`` returns a ``RhythmTree``. A ``CompositionalUnit``
        raises ``NotImplementedError`` (R13-E).
    ratios : rational or sequence of rational
        Positive. A ``Meas`` keeps its raw spelling; other rationals
        normalise.
    positions : int or sequence of int
        Parallel to *ratios*.

    Returns
    -------
    TemporalUnit or RhythmTree

    Examples
    --------
    >>> ut = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
    >>> str(scale_tempus(ut, 3, 2).tempus)
    '24/18'
    """
    if _following_target(obj, 'scale_tempus') == 'rt':
        return _rt_scale_tempus(obj, ratios, positions)
    return _following_result(
        obj, _rt_scale_tempus(obj._rt, ratios, positions))


def _coerce_addition(value, ref_beat, ref_bpm):
    """Lower one augmentation operand to the RT core's vocabulary.

    A temporalised operand carries its own (beat, bpm), so before it can
    be concatenated it is re-expressed at the HOST's reference by
    sect4.4.4 — the same reconciliation rule ``fuse`` uses (R13-B/C/D),
    with the ratio and the span folded into ONE exact ``Fraction`` and
    applied to the tempus as raw ints, so no spelling is cancelled away
    (TEMPO-5). Without this an inserted unit would silently change how
    long it sounds.

    Everything else (a ``RhythmTree``, a ``Meas``, a bare rational) is
    untimed and passes through to be read at the host's reference — his
    p. 97 convention, the one ``fuse`` already follows.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit

    if isinstance(value, CompositionalUnit):
        raise NotImplementedError(
            "a CompositionalUnit cannot be inserted by augment: its "
            "pfields, envelopes and slurs would have to merge into the "
            "host, which is the staged parameter-state surface (R13-E). "
            "Insert `uc.rt` for the rhythm alone."
        )
    if isinstance(value, TemporalUnitSequence):
        raise TypeError(
            "augment adds ONE prolatio per position; a "
            "TemporalUnitSequence is several. Fuse it into a single unit "
            "first (fuse(seq)) and insert that, so the reconciliation is "
            "yours to see rather than implied."
        )
    if isinstance(value, TemporalBlock):
        raise TypeError(
            "a TemporalBlock cannot be inserted: a polyphonic stack is "
            "not a prolatio, and flattening it into one voice has no "
            "unique answer."
        )
    if isinstance(value, TemporalUnit):
        factor = ((_exact_tempo_ratio(ref_bpm) / _exact_tempo_ratio(value.bpm))
                  * (ref_beat / value.beat) * Fraction(value.span))
        return RhythmTree(span=1,
                          meas=Meas(value.tempus.numerator * factor.numerator,
                                    value.tempus.denominator * factor.denominator),
                          subdivisions=value.prolationis)
    return value


def augment(obj, additions, positions):
    """
    Add prolationes and let the Tempus follow — Haddad's augmentation (⊞).

    The symbolic core is
    :func:`klotho.chronos.rhythm_trees.algorithms.augment` (sect4.5.2.1,
    pp. 125–126, figs. 4.58–4.60). Its preserving sibling is
    ``RhythmTree.insert`` (⊕), which holds the Tempus and re-spells the
    bar as a longer tuplet — "add a note without changing the bar's
    duration". This verb does the opposite: **beat and bpm are held**, the
    Tempus grows by exactly what was added, and the bar gets longer.

    ``2/2 (2 1 2) ⊞ (3/10, 2)`` gives ``13/10 (4 2 3 4)``, and that
    re-spelling of the source from 5ths onto 10ths is the operation's real
    content — the added prolatio is not commensurable with the existing
    ones until the grid is refined.

    A ``TemporalUnit`` operand is RECONCILED before it is concatenated:
    re-expressed at this unit's (beat, bpm) by sect4.4.4, exactly as
    :func:`fuse` does, so the inserted material keeps its real duration
    rather than silently adopting the host's tempo. An untimed operand (a
    ``RhythmTree``, a ``Meas``, a rational) is read at the host's
    reference, his p. 97 convention.

    Positions are insert-before, 0-based, into the DECOMPOSED sequence,
    and name the ORIGINAL sequence, so several insertions do not shift
    one another. ``len(decomposed)`` appends past the tail.

    Parameters
    ----------
    obj : TemporalUnit or RhythmTree
        A ``RhythmTree`` returns a ``RhythmTree``. A ``CompositionalUnit``
        raises ``NotImplementedError`` (R13-E).
    additions : TemporalUnit, RhythmTree, Meas, rational, or sequence
        A ``TemporalUnitSequence`` is refused — fuse it first, so the
        reconciliation is visible rather than implied.
    positions : int or sequence of int

    Returns
    -------
    TemporalUnit or RhythmTree

    Examples
    --------
    >>> ut = TemporalUnit(tempus='2/2', prolatio=(2, 1, 2))
    >>> str(augment(ut, '3/10', 2).tempus)
    '13/10'
    """
    if _following_target(obj, 'augment') == 'rt':
        return _rt_augment(obj, additions, positions)
    adds = additions if isinstance(additions, (list, tuple)) else [additions]
    coerced = [_coerce_addition(a, obj.beat, obj.bpm) for a in adds]
    if not isinstance(additions, (list, tuple)):
        coerced = coerced[0]
    return _following_result(obj, _rt_augment(obj._rt, coerced, positions))


def _interleave_operand(obj, position):
    """Normalise one ``interleave`` operand to a list of whole units.

    Refuses a ``TemporalBlock`` in the same three-part shape ``fuse``
    uses: what cannot happen, why it has no unique answer, and the named
    alternative.
    """
    if isinstance(obj, TemporalBlock):
        raise ValueError(
            "a TemporalBlock cannot be interleaved: zipping a polyphonic "
            "stack into one voice has no unique answer, and choosing one "
            "would choose music for the composer. The block-shaped "
            "sibling is `weave` -- the vertical rotation-weave of his "
            "fig. 7.10 (docket WL-28) -- which is not built yet. "
            "Interleave the block's rows as sequences instead."
        )
    if isinstance(obj, TemporalUnitSequence):
        return list(obj.seq)
    if isinstance(obj, TemporalUnit):
        return [obj]
    if isinstance(obj, (list, tuple)):
        out = []
        for member in obj:
            out.extend(_interleave_operand(member, position))
        return out
    raise TypeError(
        f"interleave takes a TemporalUnit, a TemporalUnitSequence, or a "
        f"list of them; operand {position} is {type(obj).__name__}."
    )


def interleave(a, b):
    """
    Zip a sequence against another's retrograde -- Haddad's *tuilage*
    (docket OPS-8).

    ``C = [i || j]`` for ``i`` in *a* and ``j`` in ``reverse(b)``: a
    strict alternating zip of WHOLE units. Nothing is merged, scaled or
    re-metered -- every unit passes through untouched (as a copy),
    keeping its own tempus, prolationis, beat and bpm -- so the result is
    one single-voice :class:`TemporalUnitSequence` whose duration is
    exactly ``a.duration + b.duration``. No arithmetic crosses an operand
    boundary, so there is no tempo to reconcile.

    Source: sect4.6.2 pp. 133-134, figs. 4.80-4.83 (2008 English original
    pp. 30-32). Haddad glosses his own term on p. 133 --
    « un tuilage (« interlocking ») », "a *tuilage* ('interlocking')" --
    and says on p. 134 why it interests him:

        « l'engendrement par son contraire utilisant le procede de
        diminution genere une fausse symetrie qui nous parait
        interessante »
        -- "generation by its opposite, using the diminution process,
        produces a *false symmetry* that seems interesting to us."

    The English name wins over *tuilage*: the French word means tiling,
    overlapping entries, and this operation has **no overlap at all** --
    one voice, units end to end. (Same call as ``fuse`` over
    "concatenation".)

    Source-inclusion is a property of the OPERANDS, not of this verb.
    In his own example each iteration sequence begins with the unit it
    was diminished from, which is why fig. 4.81 has ten bars where fig.
    4.82's
    formalism suggests eight. ``interleave`` stays a pure zip and takes
    no ``include_source`` flag -- such a flag would double-count when
    both operands already carry their seed. It lives on the generator
    instead: :func:`iterate`, where it defaults ``True``.

    UNEQUAL LENGTHS -- append-tail, and it is not symmetric. The zip runs
    to ``min(len(a), len(b))``; the longer operand's remaining units are
    then appended **in their own traversal order**. *a*'s tail is
    appended forward, *b*'s tail in ``reverse(b)`` order, so
    ``interleave(x, y)`` and ``interleave(y, x)`` are not reverses of
    each other. Both are lossless.

    Parameters
    ----------
    a : TemporalUnit, TemporalUnitSequence, or list of them
        Traversed forward. A ``CompositionalUnit`` is an ordinary member:
        unlike ``fuse``, this verb merges no parameter state, so there is
        nothing to reconcile.
    b : TemporalUnit, TemporalUnitSequence, or list of them
        Traversed in retrograde.

    Returns
    -------
    TemporalUnitSequence
        One single-voice sequence, ``len(a) + len(b)`` units long.

    Raises
    ------
    ValueError
        If either operand is a ``TemporalBlock``; the block-shaped
        sibling is ``weave`` (WL-28), not built.

    Examples
    --------
    >>> a = TemporalUnitSequence([TemporalUnit(tempus='1/4', prolatio=(1,)),
    ...                           TemporalUnit(tempus='2/4', prolatio=(1,))])
    >>> b = TemporalUnitSequence([TemporalUnit(tempus='3/4', prolatio=(1,)),
    ...                           TemporalUnit(tempus='5/4', prolatio=(1,))])
    >>> [str(u.tempus) for u in interleave(a, b).seq]
    ['1/4', '5/4', '2/4', '3/4']
    """
    forward = _interleave_operand(a, 'a')
    retrograde = list(reversed(_interleave_operand(b, 'b')))

    n = min(len(forward), len(retrograde))
    out = []
    for i in range(n):
        out.append(forward[i])
        out.append(retrograde[i])
    out.extend(forward[n:])
    out.extend(retrograde[n:])

    # The constructor copies every member, which is what keeps the
    # output's units independent of the operands'.
    return TemporalUnitSequence(out)


def _prolatio_count(unit):
    """Size of the surface the operator family takes its positions in.

    One entry per tie GROUP (ALG-2), not one per leaf -- the decomposed
    sequence is what ``diminish``, ``augment`` and ``scale_tempus`` all
    index into, so it is what the stopping condition has to count.
    """
    return len(_rt_decompose(unit._rt))


def _iterate_position(index, mode):
    """Resolve ``iterate``'s position selector to a callable of the counter.

    ``None`` is mode-sensitive on purpose, because the two modes have
    different published idioms and neither default is usable in the
    other's mode:

    * ``'recursive'`` -> ``0``. His sequence A deletes the head over and
      over; the surface shrinks under it, so a constant is a moving
      target and does real work.
    * ``'simple'`` -> the counter itself. His (a) is iteration "sur tout
      ou partie des elements" ("over all or part of the elements"), and
      the source never shrinks, so a constant would return the same unit
      every step.
    """
    if index is None:
        return (lambda i: 0) if mode == 'recursive' else (lambda i: i)
    if callable(index):
        return index
    if isinstance(index, int) and not isinstance(index, bool):
        return lambda i, _fixed=index: _fixed
    raise TypeError(
        f"iterate's index selects the position operated on at each step: "
        f"an int for a fixed position, or a callable of the iteration "
        f"counter for a moving one (his sequence B is `4 - i`). Got "
        f"{type(index).__name__}."
    )


def iterate(ut, op, start=0, stop=None, *, mode='recursive',
            include_source=True, index=None) -> TemporalUnitSequence:
    """
    Build a whole form by repeated application of one operator --
    Haddad's iteration (docket OPS-7).

    Source: sect4.6, p. 131, figs. 4.76-4.82. He names two kinds, and
    both ship here as one verb under ``mode``:

        a) « Iteration simple sur tout ou partie des elements. »
           -- "Simple iteration over all or part of the elements."

        b) « Iteration recursive cumulative sur tout ou partie des
           elements, le resultat etant l'accumulation des resultats de la
           recursion. »
           -- "Cumulative recursive iteration over all or part of the
           elements, the result being the accumulation of the results of
           the recursion."

    Three of his operator glosses fix the shape of what comes back:

        « p := » -- "at each iteration the operation is performed on the
                    result of the previous one"  (``mode='recursive'``)
        « & »    -- "create a sequence from all the iteration results"
                    (hence a ``TemporalUnitSequence``)
        « || »   -- "concatenation of all results" (that is :func:`fuse`,
                    already shipped -- the OTHER thing his notation
                    offers, and the reason this verb does not fold)

    NAMING. "Erosion" was the docket's coinage and is **not Haddad's**.
    His own two terms -- *iteration simple* ("simple iteration") and
    *iteration recursive cumulative* ("cumulative recursive iteration") --
    are accurate, so the English name follows them and "erosion" is kept
    out of the code entirely.

    His worked case is ``p := (p |-|(i)) &`` on ``1/1 (4 3 2 1)`` with
    ``i = 0, 2`` (figs. 4.78-4.79), which gives three bars of
    ``3/5 (3 2 1) | 3/10 (2 1) | 1/10 (1)``.

    NOT ``autoref``. :func:`klotho.topos.collections.patterns.autoref` is
    self-referential SUBDIVISION and GROWS a tree -- ``autoref((2, 3))``
    is ``((2, (3, 2)), (3, (2, 3)))``, and ``depth=n`` gives
    ``len ** (depth + 1)`` leaves. Iteration here runs the other way: each
    step deletes a prolatio and lets the Tempus follow, so the units get
    shorter, and the return is a sequence of units rather than one tree.

    THE OPERATOR IS A PARAMETER. ``diminish`` is his example, not the
    definition, so ``op`` is called as ``op(unit, position)`` and any
    unary member of the family fits. An operator that needs more operands
    is bound first::

        from functools import partial
        iterate(ut, partial(lambda r, u, p: scale_tempus(u, r, p), 2), 0, 3)

    STOPPING. ``start`` and ``stop`` are his ``i = d, f`` -- an INCLUSIVE
    counter range, and ``start`` shifts only the value handed to *index*.
    On top of that there is a STRUCTURAL FLOOR: iteration halts once one
    prolatio is left, because there is nothing further to remove and his
    published A and B both stop there. An over-long ``stop`` therefore
    truncates rather than raising. ``stop=None`` means "run to that
    floor" in recursive mode, and "one pass over the source's surface" in
    simple mode. A recursive ``stop=None`` under an operator that does
    NOT shrink the surface would never terminate, so that raises and asks
    for an explicit ``stop``.

    ``include_source`` -- **read this before comparing against the
    book.** Fig. 4.82's condensed formalism gives FOUR units per
    sequence; the engravings of fig. 4.80 show FIVE, because each
    sequence begins with the unit it was diminished from, and the tuilage of
    fig. 4.81 accordingly has TEN bars rather than eight. The default is
    ``True`` on the strength of the engravings, and because a diminution
    development states its theme first. The head passes through
    UNFLATTENED -- it is his bar 1, nesting and all, not the surface the
    operator indexes into. This flag lives here and not on
    :func:`interleave`, which stays a pure zip: source-inclusion is a
    property of the operands.

    Parameters
    ----------
    ut : TemporalUnit
        The seed. Not modified. A ``CompositionalUnit`` is not screened
        here -- ``iterate`` delegates, so *op*'s own refusal fires (R13-E
        for the following family) rather than a second, possibly
        contradictory check.
    op : callable
        ``op(unit, position) -> TemporalUnit``.
    start, stop : int
        His ``i = d, f``, inclusive. ``stop=None`` is described above.
        ``stop < start`` is zero iterations, not an error.
    mode : {'recursive', 'simple'}
        ``'recursive'`` is his ``p :=`` -- operate on the previous
        result. ``'simple'`` operates on the SOURCE every step, so
        nothing accumulates.
    include_source : bool
        Prepend the seed. Default ``True``; see above.
    index : int, callable, or None
        The position operated on at step ``i``. A callable receives the
        counter, which is how his sequence B's ``4 - i`` is expressed --
        an int cannot say it. ``None`` is ``0`` in recursive mode and the
        counter in simple mode.

    Returns
    -------
    TemporalUnitSequence
        His ``&``. To get his ``||`` instead, pass the result to
        :func:`fuse`.

    Raises
    ------
    ValueError
        Unknown *mode*; or a recursive ``stop=None`` under an operator
        that does not shrink the surface.
    TypeError
        *ut* is not a ``TemporalUnit`` (a sequence or a block holds
        several, and this verb iterates exactly one); *op* is not
        callable; *index* is neither an int nor a callable.

    Examples
    --------
    >>> src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
    >>> [str(u.tempus) for u in
    ...  iterate(src, diminish, 0, 2, include_source=False).seq]
    ['6/10', '3/10', '1/10']
    """
    if mode not in ('recursive', 'simple'):
        raise ValueError(
            f"iterate's mode is 'recursive' (his `p :=`, operate on the "
            f"previous result) or 'simple' (operate on the source every "
            f"step); got {mode!r}."
        )
    if not isinstance(ut, TemporalUnit):
        raise TypeError(
            f"iterate seeds from one TemporalUnit; got "
            f"{type(ut).__name__}. A TemporalUnitSequence or a "
            f"TemporalBlock already holds several units, and this verb "
            f"MAKES a sequence out of one -- iterate the member you mean."
        )
    if not callable(op):
        raise TypeError(
            f"iterate's op is the operator applied at each step, called "
            f"as op(unit, position); got {type(op).__name__}. Bind any "
            f"extra operands first (functools.partial)."
        )
    position_of = _iterate_position(index, mode)

    surface = _prolatio_count(ut)
    if mode == 'simple' and stop is None:
        # His (a), "over all the elements": one application per prolatio.
        stop = start + surface - 1

    results = []
    current = ut
    i = start
    while stop is None or i <= stop:
        if surface <= 1:
            break  # the structural floor: nothing left to remove
        step = op(current if mode == 'recursive' else ut, position_of(i))
        if mode == 'recursive':
            new_surface = _prolatio_count(step)
            if stop is None and new_surface >= surface:
                raise ValueError(
                    f"iterate was given no stop, so it runs to the "
                    f"structural floor of one prolatio -- but this "
                    f"operator left the surface at {new_surface} prolationes "
                    f"from {surface}, so the floor is never reached and "
                    f"the iteration would not terminate. Pass an "
                    f"explicit stop."
                )
            surface = new_surface
            current = step
        results.append(step)
        i += 1

    # The constructor copies every member, so the seed and the caller's
    # unit stay independent of the output.
    return TemporalUnitSequence(([ut] if include_source else []) + results)


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
