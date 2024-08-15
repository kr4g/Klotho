# ------------------------------------------------------------------------------------
# AlloPy/allopy/aikous/dynamics.py
# ------------------------------------------------------------------------------------
'''
'''

import numpy as np
from numpy.polynomial import Polynomial
# from utils.data_structures.enums import MinMaxEnum, Enum

DYNAMIC_MARKINGS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')

class DynamicRange:
  def __init__(self, min_db=-60, max_db=0, dynamics=DYNAMIC_MARKINGS):
    self.min_db = min_db
    self.max_db = max_db
    self.dynamics = dynamics
    self.range = self._calculate_range()
    
  @property
  def ranges(self):
    return self.range

  def _calculate_range(self):
    step_size = (self.max_db - self.min_db) / (len(self.dynamics) - 1)
    return {
      dyn: self.min_db + i * step_size
      for i, dyn in enumerate(self.dynamics)
    }

  def __getitem__(self, dynamic):
    return self.range[dynamic]


class DYNAMICS:
  '''
  Enum for musical dynamics mapped to decibels.

  Note: the decibel level for the loudest 
  dynamic (ffff) is 0 dB as this translates 
  to an amplitude of 1.0.

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
  _registry = {}

  @classmethod
  def register(cls, instrument_name, min_db, max_db):
      cls._registry[instrument_name] = DynamicRange(min_db, max_db)

  @classmethod
  def get(cls, instrument_name):
      return cls._registry.get(instrument_name, None)

  def __getitem__(self, instrument_name):
      return self.get(instrument_name)
    

def amp_db(amp: float) -> float:
  '''
  Convert amplitude to decibels (dB).

  Args:
  amp (float): The amplitude to convert.

  Returns:
  float: The amplitude in decibels.
  '''
  return 20 * np.log10(amp)

def db_amp(db: float) -> float:
  '''
  Convert decibels (dB) to amplitude.

  Args:
  db (float): The decibels to convert.

  Returns:
  float: The amplitude.
  '''
  return 10 ** (db / 20)

def amp_freq_scale(freq: float, freqs: list = [20,  100, 500, 1000, 3000, 4000, 6000, 10000, 20000],
                   amps: list               = [0.2, 0.4, 0.8, 0.9,  1.0,  0.9,  0.8,  0.6,   0.4],
                   deg: int = 4) -> float:
  frequencies_sample = np.array(freqs, dtype=float)
  loudness_sample    = np.array(amps, dtype=float)
  p = Polynomial.fit(frequencies_sample, loudness_sample, deg=deg)
  return p(freq)

