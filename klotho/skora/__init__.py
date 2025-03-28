"""
Skora: A specialized module for visualization, notation, and representation of music.

From the Greek "σκορ" (skor) related to "score" or "notation," this module
provides tools for visualizing and notating musical structures.
"""
from .skora import *

from . import animation
from . import notation
from . import visualization

from .visualization import plots
from .visualization.plots import plot_graph, plot_tree, plot_rt, plot_ratios, plot_curve

__all__ = []
