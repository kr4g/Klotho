# ------------------------------------------------------------------------------------
# Klotho/klotho/aikous/dynamics.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Classes and functions for working with musical dynamics.
--------------------------------------------------------------------------------------
'''

import numpy as np
from numpy.polynomial import Polynomial
from scipy import interpolate
from functools import lru_cache

__all__ = [
    'DynamicRange',
    'ampdb',
    'dbamp',
    # 'amp_freq_scale',
    'freq_amp_scale',
]

DYNAMIC_MARKINGS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')

class Dynamic:
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
  '''
  ----------------|---------|----------------
  Name            | Letters	| Level
  ----------------|---------|----------------
  fortississimo	  | fff	    | very very loud  
  fortissimo	    | ff	    | very loud
  forte	          | f	      | loud
  mezzo-forte	    | mf	    | moderately loud
  mezzo-piano	    | mp	    | moderately quiet
  piano	          | p	      | quiet
  pianissimo	    | pp	    | very quiet
  pianississimo	  | ppp	    | very very quiet
  ----------------|---------|----------------

  see https://en.wikipedia.org/wiki/Dynamics_(music)#
  '''
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

def ampdb(amp: float) -> float:
  '''
  Convert amplitude to decibels (dB).

  Args:
  amp (float): The amplitude to convert.

  Returns:
  float: The amplitude in decibels.
  '''
  return 20 * np.log10(amp)

def dbamp(db: float) -> float:
  '''
  Convert decibels (dB) to amplitude.

  Args:
  db (float): The decibels to convert.

  Returns:
  float: The amplitude.
  '''
  return 10 ** (db / 20)

# def amp_freq_scale(freq: float,
#     freqs: list = [20,  100, 250, 500, 1000, 2000, 3000, 4000, 6000, 10000, 20000],
#     amps: list  = [0.3, 0.5, 0.7, 0.8, 0.5,  0.6,  0.5,  0.6,  0.7,  0.5,   0.3],
#     deg: int = 4) -> float:
#   frequencies_sample = np.array(freqs, dtype=float)
#   loudness_sample    = np.array(amps, dtype=float)
#   p = Polynomial.fit(frequencies_sample, loudness_sample, deg=deg)
#   return p(freq)

def freq_amp_scale(freq: float, db_level: float, min_db: float = -60) -> float:
    """
    Scale amplitude based on frequency and loudness according to psychoacoustic principles.
    
    Args:
        freq (float): The frequency in Hz
        db_level (float): The input level in dB
        min_db (float): The minimum dB level in the dynamic range (default -60)
        
    Returns:
        float: The perceptually scaled amplitude (linear scale)
    """
    range_db = abs(min_db)
    phon_level = 40 + ((db_level - min_db) / range_db) * 60
    
    frequencies = np.array([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000], dtype=float)
    
    if phon_level <= 40:
        scaling_curve = np.array([0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.0, 0.9, 0.7, 0.4], dtype=float)
    elif phon_level <= 70:
        scaling_curve = np.array([0.3, 0.45, 0.6, 0.8, 0.95, 1.0, 1.0, 0.95, 0.8, 0.5], dtype=float)
    else:
        scaling_curve = np.array([0.5, 0.6, 0.7, 0.85, 0.95, 1.0, 1.0, 0.95, 0.85, 0.6], dtype=float)
    
    spline = interpolate.CubicSpline(frequencies, scaling_curve, extrapolate=True)
    scaling_factor = max(0.01, float(spline(freq)))
    
    raw_amp = dbamp(db_level)
    return raw_amp * scaling_factor
