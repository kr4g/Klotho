"""
Thetos: A specialized module for working with musical parameters and instruments.

From the Greek "θέτος" (thetos) meaning "placed" or "set," this module
deals with the placement and configuration of musical parameters and instruments.
"""

from . import instruments
from . import parameters

from .parameters import ParameterTree
from .instruments import Instrument
from .types import frequency, cent, midicent, midi, amplitude, decibel, onset, duration

__all__ = [
    'instruments',
    'parameters',
    'ParameterTree',
    'Instrument',
    'frequency', 
    'cent', 
    'midicent', 
    'midi',
    'amplitude', 
    'decibel', 
    'onset', 
    'duration',
] 