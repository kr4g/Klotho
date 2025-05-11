'''
--------------------------------------------------------------------------------------
General psychoacoustic tools for working with music synthesis.

`Aikous` is a specialized module for working with psychoacoustics in the context of music.

see: https://en.wikipedia.org/wiki/Psychoacoustics

The word "aikous" is a portmanteau derived from Ancient Greek, blending the elements of 
"αἰσθάνομαι" (aisthanomai), meaning "to perceive" or "to feel," and "ἀκούω" (akouo), 
meaning "to hear."

The `aikous` module contains tools for translating physics phenomena, as perceived by
humans, into algebraic musical representations.
--------------------------------------------------------------------------------------
'''
from .dynamics import Dynamic, DynamicRange, dbamp, ampdb, freq_amp_scale
from .enevelopes import line, arch, map_curve

__all__ = [
    'Dynamic',
    'DynamicRange',
    'dbamp',
    'ampdb',
    'freq_amp_scale',
    'line',
    'arch',
    'map_curve'
]