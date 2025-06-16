"""
Klotho: A comprehensive toolkit for complex musical analysis, generation, and visualization.

From the Greek "Κλωθώ" (Klotho), one of the three Fates who spins the thread of life.
This library weaves together various aspects of musical computation.

Submodules:
- topos: Abstract mathematical and structural foundations
- chronos: Temporal structures and rhythm generation  
- tonos: Tonal systems, pitches, scales, and harmony
- thetos: Musical parameter trees and instrumentation
- dynatos: Expression, dynamics, and envelopes
- semeios: Visualization, notation, and representation
- utils: General utilities and helper functions
"""
from . import topos
from . import chronos
from . import tonos
from . import thetos
from . import dynatos
from . import semeios
from . import utils

from .topos.collections import patterns, sequences, sets, Pattern, CombinationSet, PartitionSet
from .topos.graphs import trees, networks, fields, Tree, Network, Field, Graph

from .chronos import RhythmPair, RhythmTree, TemporalUnit, TemporalUnitSequence, TemporalBlock

from .tonos import Pitch, Scale, Chord, AddressedScale, AddressedChord

from .semeios.visualization.plots import plot
from .semeios.notelists.scheduler import Scheduler
from .semeios.midi import midi as export_midi

from .thetos.types import frequency, cent, midicent, midi, amplitude, decibel, onset, duration

from .utils.playback.player import play, pause, stop, sync

__all__ = [
    'topos', 'chronos', 'tonos', 'thetos', 'dynatos', 'semeios', 'utils',
    'Pitch', 'Scale', 'Chord', 
    'AddressedScale', 'AddressedChord',
    'frequency', 'cent', 'midicent', 'midi',
    'amplitude', 'decibel', 'onset', 'duration',
    'RhythmTree', 'TemporalUnit',
    'plot', 'Scheduler',
    'play', 'pause', 'stop', 'sync', 'export_midi'
]

__version__ = '3.0.3'
