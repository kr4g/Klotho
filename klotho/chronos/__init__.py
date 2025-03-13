# Klotho/klotho/chronos/__init__.py
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
from .utils import *

__all__ = [
    'rhythm_pairs', 'rhythm_trees', 'temporal_units', 'utils'
]

__version__ = '2.0.0'
