"""
Maquettes: Interactive timeline visualization for musical sketches.

This module provides tools for creating and manipulating musical maquettes (sketches)
through interactive timeline visualizations with OSC communication support.
"""

from .clip import Clip
from .timeline import Timeline

__all__ = ['Clip', 'Timeline'] 