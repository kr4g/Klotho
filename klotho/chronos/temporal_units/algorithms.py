from typing import Union
from fractions import Fraction
from itertools import cycle
from .temporal import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree, Meas
from klotho.chronos.utils import beat_duration
from klotho.chronos.rhythm_trees.algorithms import segment


def segment_ut(ut: TemporalUnit, ratio: Union[Fraction, float, str]) -> TemporalUnit:
    """
    Segments a temporal unit into a new unit with the given ratio. eg, a ratio of 1/3 means
    the new unit will have a prolatio of (1, 2).
    
    Args:
    ut (TemporalUnit): The temporal unit to segment.
    ratio (Union[Fraction, float, str]): The ratio to segment the unit by.
    
    Returns:
    TemporalUnit: A new temporal unit with the given ratio.
    """
    return TemporalUnit(span=ut.span, tempus=ut.tempus, prolatio=segment(ratio), beat=ut.beat, bpm=ut.bpm)

def decompose(ut: TemporalUnit, prolatio: Union[tuple, str, None] = None, depth: Union[int, None] = None) -> TemporalUnitSequence:
    """Decomposes a temporal structure into its constituent parts based on the provided prolatio."""
    
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
        return TemporalUnitSequence([
            TemporalUnit(
                span     = 1,
                tempus   = subtree[subtree.root]['ratio'],
                prolatio = subtree.group.S if not prolatio else next(prolatio_cycle),
                beat     = ut._beat,
                bpm      = ut._bpm
            ) for subtree in [ut._rt.subtree(n) for n in ut._rt.at_depth(depth)]
        ])
    else:
        return TemporalUnitSequence([
           TemporalUnit(
               span     = 1,
               tempus   = abs(ratio),
               prolatio = next(prolatio_cycle),
               beat     = ut._beat,
               bpm      = ut._bpm
           ) for ratio in ut._rt._ratios
        ])

def transform(structure: TemporalMeta) -> TemporalMeta:
    
    match structure:
        case TemporalUnit():
            return TemporalBlock([ut for ut in decompose(structure).seq])
            
        case TemporalUnitSequence():
            return TemporalBlock([ut.copy() for ut in structure.seq])
            
        case TemporalBlock():
            raise NotImplementedError("Block transformation not yet implemented")
            
        case _:
            raise ValueError(f"Unknown temporal structure type: {type(structure)}")

def modulate_tempo(ut: TemporalUnit, beat: Union[Fraction, str, float], bpm: Union[int, float]) -> TemporalUnit:
    """
    Creates a new TemporalUnit with the specified beat and bpm, adjusting the tempus 
    to maintain the same duration as the original unit.
    
    Args:
        ut (TemporalUnit): The original temporal unit
        beat (Union[Fraction, str, float]): The new beat value
        bpm (Union[int, float]): The new beats per minute
        
    Returns:
        TemporalUnit: A new temporal unit with adjusted tempus and the specified beat/bpm
    """
    ratio = ut.duration / beat_duration(str(ut.tempus * ut.span), bpm, beat)
    new_tempus = Meas(ut.tempus * ut.span * ratio)
    
    return TemporalUnit(
        span=1,
        tempus=new_tempus,
        prolatio=ut.prolationis,
        beat=beat,
        bpm=bpm
    )

def modulate_tempus(ut: TemporalUnit, span: int, tempus: Union[Meas, Fraction, float, str]) -> TemporalUnit:
    """
    Creates a new TemporalUnit with the specified tempus, adjusting the beat/bpm 
    to maintain the same duration as the original unit.
    
    Args:
        ut (TemporalUnit): The original temporal unit
        tempus (Union[Meas, Fraction, float, str]): The new tempus value
        
    Returns:
        TemporalUnit: A new temporal unit with the specified tempus and adjusted beat/bpm
    """
    if not isinstance(tempus, Meas):
        tempus = Meas(tempus)
    
    ratio = beat_duration(str(tempus * span), ut.bpm, ut.beat) / beat_duration(str(ut.tempus * ut.span), ut.bpm, ut.beat)

    return TemporalUnit(
        span=span,
        tempus=tempus,
        prolatio=ut.prolationis,
        beat=ut.beat,
        bpm=ut.bpm * ratio
    )

def convolve(x: Union[TemporalUnit, TemporalUnitSequence], h: Union[TemporalUnit, TemporalUnitSequence], beat: Union[Fraction, str, float] = '1/4', bpm: Union[int, float] = 60) -> TemporalUnitSequence:
    beat = Fraction(beat)
    bpm = float(bpm)
    
    if isinstance(x, TemporalUnit):
        x = decompose(x)
    if isinstance(h, TemporalUnit):
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
