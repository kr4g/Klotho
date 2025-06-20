"""
Semeios: A specialized module for visualization, notation, and representation of music.

From the Greek "σημεῖον" (semeion) meaning "sign" or "mark," this module
provides tools for visualizing and notating musical structures.
"""
from .notelists import *

from . import animation
from . import notation
from . import visualization
from . import notelists
from . import midi
from . import maquettes

from .visualization import plots
from .visualization.plots import *

from .midi import midi as export_midi

__all__ = ['export_midi']
