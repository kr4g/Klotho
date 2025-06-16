"""
Aikous: A specialized module for working with expression and parameters in music.

From the Greek "ακούω" (akoúō) meaning "to hear" or "to listen," this module
deals with the expressive aspects of music that affect how we perceive sound.
"""

from . import expression
from . import parameters
from . import instruments

from .expression import Dynamic, DynamicRange
from .parameters import ParameterTree
from .instruments import Instrument

from .expression import dbamp, ampdb, freq_amp_scale
from .expression import line, arch, map_curve

__all__ = [
    # Modules
    'expression',
    'parameters',
    'instruments',
    
    # Classes
    'DynamicRange',
    'Dynamic',
    'ParameterTree',
    'Instrument',
    
    # Expression functions
    'dbamp', 
    'ampdb', 
    'freq_amp_scale',
    'line', 
    'arch', 
    'map_curve',
]
