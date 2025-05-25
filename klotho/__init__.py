"""
Klotho: A graph-oriented Python package for computational composition.

This package provides tools for working with musical structures across multiple domains:
- Topos: Abstract structures and relationships
- Chronos: Time and rhythm
- Tonos: Pitch and harmony
- Aikous: Expression and parameters
- Skora: Visualization and notation
"""
from . import topos
from . import chronos
from . import tonos
from . import aikous
from . import skora

from .topos.collections import patterns, sequences, sets, Pattern, CombinationSet, PartitionSet
from .topos.graphs import trees, networks, fields, Tree, Network, Field, Graph

from .chronos import RhythmPair, RhythmTree, TemporalUnit, TemporalUnitSequence, TemporalBlock

from .tonos import Pitch, Scale, Chord, AddressedScale, AddressedChord

from .types import frequency, cent, midicent, midi, amplitude, decibel, onset, duration

__all__ = [
    'topos', 'chronos', 'tonos', 'aikous', 'skora',
    'Pitch', 'Scale', 'Chord', 
    'AddressedScale', 'AddressedChord',
    'frequency', 'cent', 'midicent', 'midi',
    'amplitude', 'decibel', 'onset', 'duration'
]

__version__ = '2.1.0'
