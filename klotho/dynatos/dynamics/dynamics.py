"""
Dynamics classes and utilities for musical expression.

This module provides classes for working with musical dynamics, including
individual dynamic markings and dynamic ranges.
"""

import numpy as np
from functools import lru_cache
from .utils import dbamp

__all__ = [
    'Dynamic',
    'DynamicRange',
]

DYNAMIC_MARKINGS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')

class Dynamic:
    """
    Represents a musical dynamic marking with both symbolic and numeric representations.
    
    A Dynamic object encapsulates both the traditional musical marking (e.g., 'f', 'pp')
    and its corresponding decibel value, providing seamless conversion between symbolic
    and numeric representations of dynamics.
    
    Args:
        marking (str): The symbolic dynamic marking (e.g., 'f', 'pp', 'mf')
        db_value (float): The decibel value corresponding to this dynamic level
        
    Example:
        >>> dyn = Dynamic('f', -12)
        >>> dyn.marking
        'f'
        >>> dyn.db
        -12
        >>> dyn.amp
        0.25118864315095825
    """
    def __init__(self, marking, db_value):
        self._marking = marking
        self._db_value = db_value
    
    @property
    def marking(self):
        return self._marking
    
    @property
    def db(self):
        return self._db_value
        
    @property
    def amp(self):
        return dbamp(self._db_value)
    
    def __float__(self):
        return float(self._db_value)
    
    def __repr__(self):
        return f"Dynamic(marking='{self._marking}', db={self._db_value:.2f}, amp={self.amp:.4f})"


class DynamicRange:
    """
    Manages a range of musical dynamics with customizable curve mapping.
    
    DynamicRange creates a mapping between traditional dynamic markings and their
    corresponding decibel values, with optional curve shaping for non-linear
    dynamic progressions.
    
    +------------------+---------+------------------+
    | Name             | Letters | Level            |
    +==================+=========+==================+
    | fortississimo    | fff     | very very loud   |
    +------------------+---------+------------------+
    | fortissimo       | ff      | very loud        |
    +------------------+---------+------------------+
    | forte            | f       | loud             |
    +------------------+---------+------------------+
    | mezzo-forte      | mf      | moderately loud  |
    +------------------+---------+------------------+
    | mezzo-piano      | mp      | moderately quiet |
    +------------------+---------+------------------+
    | piano            | p       | quiet            |
    +------------------+---------+------------------+
    | pianissimo       | pp      | very quiet       |
    +------------------+---------+------------------+
    | pianississimo    | ppp     | very very quiet  |
    +------------------+---------+------------------+
    
    Args:
        min_dynamic (float): Minimum decibel value for the quietest dynamic (default: -60)
        max_dynamic (float): Maximum decibel value for the loudest dynamic (default: -3)
        curve (float): Curve shaping factor. 0 = linear, positive = logarithmic, negative = exponential (default: 0)
        dynamics (tuple): Tuple of dynamic markings to use (default: standard 8-level dynamics)
        
    Example:
        >>> dr = DynamicRange()
        >>> dr['f'].db
        -12.857142857142858
        >>> dr.at(0.5).marking
        'mp'
        
    See Also:
        https://en.wikipedia.org/wiki/Dynamics_(music)
    """
    def __init__(self, min_dynamic=-60, max_dynamic=-3, curve=0, dynamics=DYNAMIC_MARKINGS):
        self._min_db = min_dynamic
        self._max_db = max_dynamic
        self._curve = curve
        self._dynamics = dynamics
        self._range = self._calculate_range()

    @property
    def min_dynamic(self):
        return self._range[self._dynamics[0]]
    
    @property
    def max_dynamic(self):
        return self._range[self._dynamics[-1]]
    
    @property
    def curve(self):
        return self._curve
    
    @property
    def ranges(self):
        return self._range

    def _calculate_range(self):
        min_db = float(self._min_db)
        max_db = float(self._max_db)
        num_dynamics = len(self._dynamics)
        
        result = {}
        for i, dyn in enumerate(self._dynamics):
            normalized_pos = i / (num_dynamics - 1)
            
            if self._curve == 0:
                curved_pos = normalized_pos
            else:
                curved_pos = (np.exp(self._curve * normalized_pos) - 1) / (np.exp(self._curve) - 1)
                
            db_value = min_db + curved_pos * (max_db - min_db)
            result[dyn] = Dynamic(dyn, db_value)
            
        return result

    def __getitem__(self, dynamic):
        return self._range[dynamic]

    @lru_cache(maxsize=128)
    def at(self, position):
        if position < 0 or position > 1:
            raise ValueError(f"Position {position} must be between 0 and 1")
        
        if position == 0:
            return self._range[self._dynamics[0]]
        if position == 1:
            return self._range[self._dynamics[-1]]
        
        num_dynamics = len(self._dynamics)
        dynamic_positions = np.linspace(0, 1, num_dynamics)
        
        zone_index = 0
        for i in range(num_dynamics - 1):
            if position < dynamic_positions[i + 1]:
                zone_index = i
                break
        else:
            zone_index = num_dynamics - 1
        
        marking = self._dynamics[zone_index]
        
        min_db = float(self._min_db)
        max_db = float(self._max_db)
        
        if self._curve == 0:
            curved_pos = position
        else:
            curved_pos = (np.exp(self._curve * position) - 1) / (np.exp(self._curve) - 1)
            
        db_value = min_db + curved_pos * (max_db - min_db)
        
        return Dynamic(marking, db_value) 