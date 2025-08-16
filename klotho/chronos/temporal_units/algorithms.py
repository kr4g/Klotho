from typing import Union, TYPE_CHECKING
from fractions import Fraction
from itertools import cycle
from .temporal import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree, Meas
from klotho.chronos.utils import beat_duration
from klotho.chronos.rhythm_trees.algorithms import segment

if TYPE_CHECKING:
    from klotho.thetos.composition.compositional import CompositionalUnit


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
    """Decomposes a temporal structure into its constituent parts based on the provided prolatio."""
    
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
                # Create a CompositionalUnit from the subtree
                cu_subtree = ut.from_subtree(node)
                units.append(cu_subtree)
            else:
                # Create a regular TemporalUnit
                unit = TemporalUnit(
                    span     = 1,
                    tempus   = subtree[subtree.root]['metric_duration'],
                    prolatio = subtree.group.S if not prolatio else next(prolatio_cycle),
                    beat     = ut._beat,
                    bpm      = ut._bpm
                )
                units.append(unit)
        
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
                
                # Copy instrument information from the original CompositionalUnit
                # Look for the governing instrument node for the root
                governing_instrument_node = ut._pt.get_governing_subtree_node(ut._rt.root)
                if governing_instrument_node is not None and governing_instrument_node in ut._pt._node_instruments:
                    instrument = ut._pt._node_instruments[governing_instrument_node]
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
    Creates a new TemporalUnit or CompositionalUnit with the specified beat and bpm, 
    adjusting the tempus to maintain the same duration as the original unit.
    
    Args:
        ut (Union[TemporalUnit, CompositionalUnit]): The original temporal unit
        beat (Union[Fraction, str, float]): The new beat value
        bpm (Union[int, float]): The new beats per minute
        
    Returns:
        Union[TemporalUnit, CompositionalUnit]: A new temporal unit with adjusted tempus and the specified beat/bpm
    """
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    ratio = ut.duration / beat_duration(str(ut.tempus * ut.span), bpm, beat)
    new_tempus = Meas(ut.tempus * ut.span * ratio)
    
    if isinstance(ut, CompositionalUnit):
        # Create a new CompositionalUnit with the same ParameterTree structure
        new_cu = CompositionalUnit(
            span=1,
            tempus=new_tempus,
            prolatio=ut.prolationis,
            beat=beat,
            bpm=bpm,
            pfields=ut.pfields
        )
        # Copy the parameter tree data
        new_cu._pt = ut._pt.copy()
        # Copy envelopes
        new_cu._envelopes = ut._envelopes.copy()
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
    Creates a new TemporalUnit or CompositionalUnit with the specified tempus, 
    adjusting the beat/bpm to maintain the same duration as the original unit.
    
    Args:
        ut (Union[TemporalUnit, CompositionalUnit]): The original temporal unit
        span (int): The new span value
        tempus (Union[Meas, Fraction, float, str]): The new tempus value
        
    Returns:
        Union[TemporalUnit, CompositionalUnit]: A new temporal unit with the specified tempus and adjusted beat/bpm
    """
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if not isinstance(tempus, Meas):
        tempus = Meas(tempus)
    
    ratio = beat_duration(str(tempus * span), ut.bpm, ut.beat) / beat_duration(str(ut.tempus * ut.span), ut.bpm, ut.beat)

    if isinstance(ut, CompositionalUnit):
        # Create a new CompositionalUnit with the same ParameterTree structure
        new_cu = CompositionalUnit(
            span=span,
            tempus=tempus,
            prolatio=ut.prolationis,
            beat=ut.beat,
            bpm=ut.bpm * ratio,
            pfields=ut.pfields
        )
        # Copy the parameter tree data
        new_cu._pt = ut._pt.copy()
        # Copy envelopes
        new_cu._envelopes = ut._envelopes.copy()
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
