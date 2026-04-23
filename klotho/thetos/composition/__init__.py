"""
Composition: A specialized module for working with compositional structures.

This module provides tools for creating and manipulating composite musical structures
that span multiple domains (temporal, tonal, parametric, etc.).
"""

from .compositional import CompositionalUnit, Parametron, DistributionContext, PFieldContext
from .score import Score, ScoreItem

__all__ = [
    'CompositionalUnit',
    'Parametron',
    'DistributionContext',
    'PFieldContext',
    'Score',
    'ScoreItem',
] 