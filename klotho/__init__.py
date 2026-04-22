"""
Klotho: A comprehensive toolkit for computational music.

From the Greek "Κλωθώ" (Klotho), one of the three Fates who spins the thread of life.
This library weaves together various aspects of musical computation.

Submodules:
- topos:   Abstract mathematical and structural foundations
- chronos: Temporal and rhythm structures
- tonos:   Tonal systems, pitches, scales, and harmony
- dynatos: Expression, dynamics, and envelopes
- thetos:  Compositional parameters and instrumentation
- semeios: Visualization, notation, and representation
- utils:   General utilities and helper functions
"""
from . import topos
from . import chronos
from . import tonos
from . import dynatos
from . import thetos
from . import semeios
from . import utils

from .topos.graphs import Graph, Tree, Lattice, Group

from .semeios.visualization import plot

from .utils.playback.player import play
from .utils.playback.midi_player import play_midi, create_midi
from .utils.playback._config import set_audio_engine, get_audio_engine

__all__ = [
    'topos', 'chronos', 'tonos', 'dynatos', 'thetos', 'semeios', 'utils',
    'plot', 'play', 'play_midi', 'create_midi', 'set_audio_engine', 'get_audio_engine',
    'Graph', 'Tree', 'Lattice', 'Group',
]

__version__ = '6.3.0'