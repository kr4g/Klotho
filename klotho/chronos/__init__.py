"""
Chronos: A specialized module for working with time and rhythm in music.

The word "chronos" originates from Ancient Greek and is deeply rooted in both language 
and mythology. In Greek, "χρόνος" (chronos) means "time".

In Greek mythology, Chronos (not to be confused with Cronus, the Titan) is personified as 
the god of time. His representation often symbolizes the endless passage of time and the 
cycles of creation and destruction within the universe.
"""
from . import rhythm_pairs
from . import rhythm_trees
from . import temporal_units
from . import utils

from .rhythm_pairs import RhythmPair
from .rhythm_trees import RhythmTree, Meas
from .temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock

from .utils.beat import *
from .utils.tempo import *
from .utils.time_conversion import *
from .utils.beat import __all__ as beat_all
from .utils.tempo import __all__ as tempo_all
from .utils.time_conversion import __all__ as time_conversion_all

__all__ = [
    # Modules
    'rhythm_pairs', 
    'rhythm_trees', 
    'temporal_units', 
    'utils',
    
    # Classes
    'RhythmPair',
    'RhythmTree',
    'Meas',
    'TemporalUnit',
    'TemporalUnitSequence',
    'TemporalBlock',
]

__all__.extend(beat_all)
__all__.extend(tempo_all)
__all__.extend(time_conversion_all)
