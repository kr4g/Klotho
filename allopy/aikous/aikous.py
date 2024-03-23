# ------------------------------------------------------------------------------------
# AlloPy/allopy/aikous/aikous.py
# ------------------------------------------------------------------------------------
'''
The `aikous` base module.
'''

import numpy as np
from numpy.polynomial import Polynomial
import pandas as pd
import matplotlib.pyplot as plt
from enum import Enum, EnumMeta

class DirectValueEnumMeta(EnumMeta):
  def __getattribute__(cls, name):
    member = super().__getattribute__(name)
    if isinstance(member, cls):
      return member.value
    return member

class MinMaxEnum(Enum):
    @property
    def min(self):
        return self.value[0]

    @property
    def max(self):
        return self.value[1]
    
    def __repr__(self):
        return repr(self.value)
    
    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return (self.min * other, self.max * other)
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __call__(self):
        return np.random.uniform(self.min, self.max)

class DYNAMICS(MinMaxEnum):
  '''
  Enum for musical dynamics mapped to decibels.
  
  Decibel values are approximate and can be adjusted as needed.  Note, however, that the
  decibel level for the loudest dynamic (ffff) must be 0 dB as this translates to an
  amplitude of 1.0.
  
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
  
  Example use:
  `>>> Dynamics.fff`
  '''
  # values in amps
  ffff = (0.9448, 1.0)    
  fff  = (0.7079, 0.9447) 
  ff   = (0.5012, 0.7078) 
  f    = (0.3548, 0.5011) 
  mf   = (0.2512, 0.3547) 
  mp   = (0.1778, 0.2511) 
  p    = (0.1259, 0.1777) 
  pp   = (0.0891, 0.1258) 
  ppp  = (0.0631, 0.0890) 
  pppp = (0.0447, 0.0630) 

class ArticulationEnum(Enum):
  @property
  def attk(self):
      return self.value[0]

  @property
  def dur(self):
      return self.value[1]
  
  @property
  def sus(self):
      return self.value[2]
  
  @property
  def rel(self):
      return self.value[3]
  
  def __repr__(self):
      return repr(self.value)

class ARTICULATION(ArticulationEnum):
  '''
  Enum for musical articulation styles, each represented by a tuple of values.
  These values modify the attack time, decay, and sustain level of a note.

  The first value in the tuple is the scalar for attack time, the second for decay,
  and the third is the sustain level.

  Example use:
  `>>> Articulation.Staccato`
  '''
  Legato    = (0.9, 1.0, 0.9, 0.0)   # Longer attack, full decay, high sustain
  Staccato  = (0.1, 0.5, 0.3, 0.0)   # Quick attack, shortened decay, low sustain
  Marcato   = (0.2, 0.7, 0.6, 0.0)   # Quick attack, moderate decay, medium sustain
  Tenuto    = (0.9, 1.1, 0.9, 0.0)   # Longer attack, extended decay, high sustain
  Spiccato  = (0.05, 0.4, 0.2, 0.0)  # Very quick attack, short decay, very low sustain
  Portato   = (0.3, 0.9, 0.7, 0.0)   # Moderate attack, full decay, medium-high sustain
  Accent    = (0.2, 0.8, 0.4, 0.0)   # Quick attack, slightly shortened decay, medium-low sustain
  Sforzando = (0.2, 1.0, 0.5, 0.0)   # Very quick attack, full decay, medium sustain

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

def amp_freq_scale(freq: float,
                   freqs: list = [20, 100, 500, 1000, 3000, 4000, 6000, 10000, 20000],
                   amps: list = [0.2, 0.4, 0.8, 0.9, 1.0, 0.9, 0.8, 0.6, 0.4],
                   deg: int = 4) -> float:
  frequencies_sample = np.array(freqs, dtype=float)
  loudness_sample    = np.array(amps, dtype=float)
  p = Polynomial.fit(frequencies_sample, loudness_sample, deg=deg)
  return p(freq)
