from typing import Union, TYPE_CHECKING
from fractions import Fraction
from itertools import cycle
import copy
from .temporal import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree, Meas
from klotho.chronos.utils import beat_duration
from klotho.chronos.rhythm_trees.algorithms import segment

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
    unit regardless of *prolatio*. For a CompositionalUnit, per-leaf
    parameters, instruments, and contained overlays are preserved; slurs or
    envelopes spanning multiple resulting units cannot survive and are
    discarded.

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
    
    prolatio_cycle = []
    
    if isinstance(prolatio, tuple):
        prolatio_cycle = [prolatio]
    elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
        prolatio_cycle = [ut._rt.subdivisions]
    elif not prolatio:
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
            subtree = ut._rt.subtree(node)

            if isinstance(ut, CompositionalUnit):
                cu_subtree = ut.from_subtree(node)
                units.append(cu_subtree)
            else:
                metric_duration = ut._rt[node]['metric_duration']
                is_rest_leaf = (node in leaf_set
                                and ut._rt[node].get('proportion', 1) < 0)
                if is_rest_leaf:
                    node_prolatio = 'r'
                elif not prolatio:
                    node_prolatio = subtree.group.S
                else:
                    node_prolatio = next(prolatio_cycle)
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

        if isinstance(ut, CompositionalUnit):
            if prolatio is None:
                # from_subtree preserves the leaf's effective pfields,
                # governing instrument, and rest state.
                for leaf in ut._rt.leaf_nodes:
                    units.append(ut.from_subtree(leaf))
            else:
                # An explicit prolatio reshapes each leaf: the source leaf's
                # effective pfields cascade from the new unit's root. Rest
                # leaves stay rests regardless of the requested prolatio.
                for ordinal, leaf in enumerate(ut._rt.leaf_nodes):
                    metric_duration = ut._rt[leaf]['metric_duration']
                    is_rest = ut._rt[leaf].get('proportion', 1) < 0
                    unit = CompositionalUnit(
                        span     = 1,
                        tempus   = abs(metric_duration),
                        prolatio = 'r' if is_rest else next(prolatio_cycle),
                        beat     = ut._beat,
                        bpm      = ut._bpm,
                        pfields  = ut.pfields
                    )
                    if not is_rest:
                        unit.set_pfields(unit._rt.root, **ut[ordinal].pfields)
                    governing = ut._rt._resolve_governing_instrument_node(leaf)
                    if governing is not None and governing in ut._rt.node_instruments:
                        unit.set_instrument(unit._rt.root, ut._rt.node_instruments[governing])
                    units.append(unit)
        else:
            # Rest leaves (negative ratios) decompose to rest units — the
            # decomposed sequence must sound identical to the source.
            for ratio in ut._rt.durations:
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = abs(ratio),
                    prolatio = 'r' if ratio < 0 else next(prolatio_cycle),
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

def modulate_tempo(ut: Union[TemporalUnit, 'CompositionalUnit'], beat: Union[Fraction, str, float], bpm: Union[int, float]) -> Union[TemporalUnit, 'CompositionalUnit']:
    """
    Create a new unit with specified beat/bpm, preserving the original duration.

    The tempus is adjusted so that the resulting unit has the same duration
    as *ut* under the new tempo parameters.

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The original temporal unit.
    beat : Fraction, str, or float
        The new beat value.
    bpm : int or float
        The new beats per minute.

    Returns
    -------
    TemporalUnit or CompositionalUnit
        A new unit with adjusted tempus and the specified beat/bpm.
    """
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    ratio = ut.duration / beat_duration((ut.tempus * ut.span).to_fraction(), bpm, beat)
    new_tempus = Meas(ut.tempus * ut.span * ratio)
    
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
    as *ut* under the new tempus and span.

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

def convolve(x: Union[TemporalUnit, 'CompositionalUnit', TemporalUnitSequence], h: Union[TemporalUnit, 'CompositionalUnit', TemporalUnitSequence], beat: Union[Fraction, str, float] = '1/4', bpm: Union[int, float] = 60) -> TemporalUnitSequence:
    """
    Convolve two temporal structures to produce a new sequence.

    Both inputs are first decomposed (if not already sequences), then
    their tempus values are convolved in the signal-processing sense to
    produce a sequence of ``y_len = len(x) + len(h) - 1`` units.

    Parameters
    ----------
    x : TemporalUnit, CompositionalUnit, or TemporalUnitSequence
        The first temporal structure (signal).
    h : TemporalUnit, CompositionalUnit, or TemporalUnitSequence
        The second temporal structure (kernel).
    beat : Fraction, str, or float, optional
        Beat reference for the output units. Default is ``'1/4'``.
    bpm : int or float, optional
        Beats per minute for the output units. Default is 60.

    Returns
    -------
    TemporalUnitSequence
        The convolved sequence.
    """
    beat = Fraction(beat)
    bpm = float(bpm)
    
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if isinstance(x, (TemporalUnit, CompositionalUnit)):
        x = decompose(x)
    if isinstance(h, (TemporalUnit, CompositionalUnit)):
        h = decompose(h)
        
    y_len = len(x) + len(h) - 1
    y = []
    for n in range(y_len):
        s = Fraction(0, 1)
        for k in range(len(x)):
            m = n - k
            if 0 <= m < len(h):
                s += modulate_tempo(x.seq[k], beat, bpm).tempus.to_fraction() * modulate_tempo(h.seq[m], beat, bpm).tempus.to_fraction()
        y.append(s)
        
    return TemporalUnitSequence([TemporalUnit(span=1, tempus=r, prolatio='d' if r > 0 else 'r', beat=beat, bpm=bpm) for r in y])
