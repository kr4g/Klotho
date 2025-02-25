from typing import Union
from fractions import Fraction
from itertools import cycle
from ..ut import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock, RhythmTree


def segment(ut: TemporalUnit, ratio: Union[Fraction, float, str]) -> TemporalUnit:
    """
    Segments a temporal unit into a new unit with the given ratio. eg, a ratio of 1/3 means
    the new unit will have a prolatio of (1, 2).
    
    Args:
    ut (TemporalUnit): The temporal unit to segment.
    ratio (Union[Fraction, float, str]): The ratio to segment the unit by.
    
    Returns:
    TemporalUnit: A new temporal unit with the given ratio.
    """
    
    ratio = Fraction(ratio)
    prolatio = (ratio.numerator, ratio.denominator - ratio.numerator)
    return TemporalUnit(duration=ut.duration, tempus=ut.tempus, prolatio=prolatio, tempo=ut.tempo, beat=ut.beat)

def decompose(ut: TemporalUnit, prolatio: Union[tuple, str] = 'd') -> TemporalUnitSequence:
    """Decomposes a temporal structure into its constituent parts based on the provided prolatio."""
    
    if isinstance(prolatio, tuple):
        prolatio = [prolatio]
    elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
        prolatio = [ut._rt.subdivisions]
        
    prolatio_cycle = cycle(prolatio)
    
    return TemporalUnitSequence([
        TemporalUnit(
            span     = 1,
            tempus   = ratio,
            prolatio = next(prolatio_cycle),
            beat     = ut.beat,
            bpm      = ut.bpm
        ) for ratio in ut._rt._ratios
    ])

def transform(structure: TemporalMeta) -> TemporalMeta:
    
    match structure:
        case TemporalUnit():
            return TemporalBlock([TemporalUnitSequence([structure])])
            
        case TemporalUnitSequence():
            return TemporalBlock([TemporalUnitSequence([ut]) for ut in structure.uts])
            
        case TemporalBlock():
            raise NotImplementedError("Block transformation not yet implemented")
            
        case _:
            raise ValueError(f"Unknown temporal structure type: {type(structure)}")
