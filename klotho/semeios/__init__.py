"""
Semeios: A specialized module for visualization, notation, and representation of music.

From the Greek "σημεῖον" (semeion) meaning "sign" or "mark," this module
provides tools for visualizing and notating musical structures.
"""
from .notelists import *

from . import visualization
from . import notelists

from .visualization import plots
from .visualization.plots import *

__all__ = []
