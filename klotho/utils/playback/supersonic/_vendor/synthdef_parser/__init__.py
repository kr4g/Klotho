"""A parser for SuperCollider SynthDef binary files.

This module provides functionality to parse SynthDef files (.scsyndef) 
into Python dictionaries for inspection and manipulation.
"""

from .parser import parse_synthdef, parse_synthdef_file

__all__ = ['parse_synthdef', 'parse_synthdef_file']
__version__ = '0.1.0'
