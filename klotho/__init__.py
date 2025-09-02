"""
Klotho: A comprehensive toolkit for complex musical analysis, generation, and visualization.

From the Greek "Κλωθώ" (Klotho), one of the three Fates who spins the thread of life.
This library weaves together various aspects of musical computation.

Submodules:
- topos: Abstract mathematical and structural foundations
- chronos: Temporal and rhythm structures
- tonos: Tonal systems, pitches, scales, and harmony
- thetos: Compositional parameters and instrumentation
- dynatos: Expression, dynamics, and envelopes
- semeios: Visualization, notation, and representation
- utils: General utilities and helper functions
"""
from . import topos
from . import chronos
from . import tonos
from . import dynatos
from . import thetos
from . import semeios
from . import utils

from .topos.graphs import Graph, Tree, Lattice
from .topos.collections import Pattern, CombinationSet, PartitionSet

from .chronos import RhythmPair, RhythmTree, TemporalUnit, TemporalUnitSequence, TemporalBlock

from .tonos import Pitch, Scale, Chord, Sonority, ChordSequence, Motive

from .dynatos import Envelope, DynamicRange

from .thetos import ParameterTree, Instrument, SynthDefInstrument, MidiInstrument, CompositionalUnit, types
from .thetos.types import frequency, cent, midicent, midi, amplitude, decibel, real_onset, real_duration, metric_onset, metric_duration

from .semeios.visualization.plots import plot
from .semeios.notelists.supercollider import Scheduler
from .semeios.midi import midi as export_midi

from .utils.data_structures import Group
from .utils.playback.player import play, pause, stop, sync
from .utils.playback.midi_player import play_midi

__all__ = [
    'topos', 'chronos', 'tonos', 'dynatos', 'thetos', 'semeios', 'utils',
]

__version__ = '3.13.7'