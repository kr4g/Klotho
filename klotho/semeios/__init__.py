"""
Semeios: A specialized module for visualization, notation, and representation of music.

From the Greek "σημεῖον" (semeion) meaning "sign" or "mark," this module
provides tools for visualizing and notating musical structures.
"""
from . import visualization

from .visualization import plot

__all__ = ["plot"]
