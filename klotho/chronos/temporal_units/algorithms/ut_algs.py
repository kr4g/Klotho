from typing import Union
from fractions import Fraction
from itertools import cycle
from ..ut import TemporalUnit, TemporalUnitSequence, TemporalUnitSequenceBlock, TemporalStructure, RhythmTree


def segment(ut: TemporalUnit, ratio: Union[Fraction, float, str]) -> TemporalStructure:
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

def decompose(structure: TemporalStructure, prolatio: Union[RhythmTree, tuple, str] = 'd') -> TemporalStructure:
    """Decomposes a temporal structure into its constituent parts based on the provided prolatio."""
    
    match structure:
        case TemporalUnit():
            if isinstance(prolatio, tuple):
                prolatio = [prolatio]
            elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
                prolatio = [structure.rtree.subdivisions]
                
            prolatio_cycle = cycle(prolatio)
            
            return TemporalUnitSequence([
                TemporalUnit(
                    span=ratio,
                    tempus=ratio,
                    prolatio=next(prolatio_cycle),
                    tempo=structure.tempo,
                    beat=structure.beat
                ) for ratio in structure.rtree.ratios
            ])
            
        case TemporalUnitSequence():
            raise NotImplementedError("Sequence decomposition not yet implemented")
            
        case TemporalUnitSequenceBlock():
            raise NotImplementedError("Block decomposition not yet implemented")
            
        case _:
            raise ValueError(f"Unknown temporal structure type: {type(structure)}")


def transform(structure: TemporalStructure) -> TemporalStructure:
    """Transforms a temporal structure into a higher-dimensional structure."""
    
    match structure:
        case TemporalUnit():
            return TemporalUnitSequenceBlock([TemporalUnitSequence([structure])])
            
        case TemporalUnitSequence():
            return TemporalUnitSequenceBlock([TemporalUnitSequence([ut]) for ut in structure.uts])
            
        case TemporalUnitSequenceBlock():
            raise NotImplementedError("Block transformation not yet implemented")
            
        case _:
            raise ValueError(f"Unknown temporal structure type: {type(structure)}")
