"""
Notelists: A module for creating and managing musical note sequences.

This module provides tools for creating, manipulating, and scheduling
sequences of musical notes and events.
"""

from .allolib import *
from .supercollider import Scheduler

__all__ = [
    'Scheduler', 'make_notelist', 'play', 'make_score_df', 
    'synthSeq_to_df', 'df_to_synthSeq', 'notelist_to_synthSeq',
    'get_pfields', 'set_score_path', 'extract_pfields'
] 