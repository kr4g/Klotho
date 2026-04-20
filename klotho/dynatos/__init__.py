"""
Dynatos: A specialized module for working with expression and dynamics in music.

From the Greek "δυνατός" (dynatos) meaning "powerful" or "capable," this module
deals with the expressive aspects of music that affect how we perceive sound.
"""

from . import dynamics
from . import types as _types
from .types import *
from . import envelopes

from .dynamics import Dynamic, DynamicRange, ampdb, dbamp, freq_amp_scale
from .envelopes import Envelope, line, arch, map_curve

__all__ = [
    'dynamics',
    'envelopes',
    'Dynamic',
    'DynamicRange',
    'ampdb', 
    'dbamp', 
    'freq_amp_scale',
    'Envelope',
    'line', 
    'arch', 
    'map_curve',
] + getattr(_types, '__all__', [])
