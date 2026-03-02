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

    When *depth* is given, subtrees at that depth become the new units.
    Otherwise, each leaf duration becomes an independent unit with the
    specified *prolatio*.

    Parameters
    ----------
    ut : TemporalUnit or CompositionalUnit
        The temporal structure to decompose.
    prolatio : tuple, str, or None, optional
        The subdivision specification for the resulting units. When None,
        defaults to ``'d'`` (duration). Default is None.
    depth : int or None, optional
        If given, decompose at the specified tree depth rather than at
        the leaf level. Default is None.

    Returns
    -------
    TemporalUnitSequence
        A sequence of the resulting temporal units.
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
    
    if depth:
        nodes_at_depth = ut._rt.at_depth(depth)
        units = []
        
        for node in nodes_at_depth:
            subtree = ut._rt.subtree(node)
            
            if isinstance(ut, CompositionalUnit):
                cu_subtree = ut.from_subtree(node)
                units.append(cu_subtree)
            else:
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = subtree[subtree.root]['metric_duration'],
                    prolatio = subtree.group.S if not prolatio else next(prolatio_cycle),
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
        
        # Create units based on leaf node durations/ratios
        for ratio in ut._rt.durations:
            if isinstance(ut, CompositionalUnit):
                # For CompositionalUnit, create new CompositionalUnit instances 
                # with the same parameter structure but duration-based timing
                unit = CompositionalUnit(
                    span     = 1,
                    tempus   = abs(ratio),
                    prolatio = next(prolatio_cycle),
                    beat     = ut._beat,
                    bpm      = ut._bpm,
                    pfields  = ut.pfields
                )
                
                instrument = ut.get_instrument(ut._rt.root)
                if instrument is not None:
                    unit.set_instrument(unit._pt.root, instrument)
            else:
                # Original behavior for TemporalUnit
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = abs(ratio),
                    prolatio = next(prolatio_cycle),
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
    
    ratio = ut.duration / beat_duration(str(ut.tempus * ut.span), bpm, beat)
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
        new_cu._pt = ut._pt.copy()
        new_cu._slur_specs = copy.deepcopy(ut._slur_specs)
        new_cu._next_slur_id = ut._next_slur_id
        new_cu._control_envelopes = copy.deepcopy(ut._control_envelopes)
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
    
    ratio = beat_duration(str(tempus * span), ut.bpm, ut.beat) / beat_duration(str(ut.tempus * ut.span), ut.bpm, ut.beat)

    if isinstance(ut, CompositionalUnit):
        new_cu = CompositionalUnit(
            span=span,
            tempus=tempus,
            prolatio=ut.prolationis,
            beat=ut.beat,
            bpm=ut.bpm * ratio,
            pfields=ut.pfields
        )
        new_cu._pt = ut._pt.copy()
        new_cu._slur_specs = copy.deepcopy(ut._slur_specs)
        new_cu._next_slur_id = ut._next_slur_id
        new_cu._control_envelopes = copy.deepcopy(ut._control_envelopes)
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
