"""
Aikous: A specialized module for working with expression and parameters in music.

From the Greek "ακούω" (akoúō) meaning "to hear" or "to listen," this module
deals with the expressive aspects of music that affect how we perceive sound.
"""

from . import expression
from . import parameters
from . import instruments

from .expression import DynamicRange, dbamp, ampdb, freq_amp_scale
from .parameters import ParameterTree
from .instruments import Instrument

__all__ = []

__version__ = '2.0.0'
