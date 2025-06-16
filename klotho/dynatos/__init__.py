"""
Dynatos: A specialized module for working with expression and dynamics in music.

From the Greek "δυνατός" (dynatos) meaning "powerful" or "capable," this module
deals with the expressive aspects of music that affect how we perceive sound.
"""

from . import expression

from .expression import Dynamic, DynamicRange
from .expression import dbamp, ampdb, freq_amp_scale
from .expression import line, arch, map_curve

__all__ = [
    'expression',
    'DynamicRange',
    'Dynamic',
    'dbamp', 
    'ampdb', 
    'freq_amp_scale',
    'line', 
    'arch', 
    'map_curve',
]
