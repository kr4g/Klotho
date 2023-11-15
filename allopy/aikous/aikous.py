# ------------------------------------------------------------------------------------
# AlloPy/allopy/aikous/aikous.py
# ------------------------------------------------------------------------------------
'''
The `aikous` base module.
'''

import numpy as np
from enum import Enum, EnumMeta

class DirectValueEnumMeta(EnumMeta):
  def __getattribute__(cls, name):
    member = super().__getattribute__(name)
    if isinstance(member, cls):
      return member.value
    return member

class Tempo(Enum, metaclass=DirectValueEnumMeta):
  '''
  Enum for musical tempo markings mapped to beats per minute (bpm).

  Each tempo marking is associated with a range of beats per minute. 
  This enumeration returns a tuple representing the minimum and maximum bpm for each tempo.

  ----------------|----------------------|----------------
  Name            | Tempo Marking        | BPM Range
  ----------------|----------------------|----------------
  Larghissimo     | extremely slow       | (12 - 24 bpm)
  Adagissimo_Grave | very slow, solemn   | (24 - 40 bpm)
  Largo           | slow and broad       | (40 - 66 bpm)
  Larghetto       | rather slow and broad| (44 - 66 bpm)
  Adagio          | slow and expressive  | (44 - 68 bpm)
  Adagietto       | slower than andante  | (46 - 80 bpm)
  Lento           | slow                 | (52 - 108 bpm)
  Andante         | walking pace         | (56 - 108 bpm)
  Andantino       | slightly faster than andante | (80 - 108 bpm)
  Marcia_Moderato | moderate march       | (66 - 80 bpm)
  Andante_Moderato | between andante and moderato | (80 - 108 bpm)
  Moderato        | moderate speed       | (108 - 120 bpm)
  Allegretto      | moderately fast      | (112 - 120 bpm)
  Allegro_Moderato | slightly less than allegro | (116 - 120 bpm)
  Allegro         | fast, bright         | (120 - 156 bpm)
  Molto_Allegro_Allegro_Vivace | slightly faster than allegro | (124 - 156 bpm)
  Vivace          | lively, fast         | (156 - 176 bpm)
  Vivacissimo_Allegrissimo | very fast, bright | (172 - 176 bpm)
  Presto          | very fast            | (168 - 200 bpm)
  Prestissimo     | extremely fast       | (200 - 300 bpm)
  ----------------|----------------------|----------------

  Example use:
  `>>> Tempo.Adagio`
  '''
  Larghissimo                  = (12, 24)
  Adagissimo_Grave             = (24, 40)
  Largo                        = (40, 66)
  Larghetto                    = (44, 66)
  Adagio                       = (44, 68)
  Adagietto                    = (46, 80)
  Lento                        = (52, 108)
  Andante                      = (56, 108)
  Andantino                    = (80, 108)
  Marcia_Moderato              = (66, 80)
  Andante_Moderato             = (80, 108)
  Moderato                     = (108, 120)
  Allegretto                   = (112, 120)
  Allegro_Moderato             = (116, 120)
  Allegro                      = (120, 156)
  Molto_Allegro_Allegro_Vivace = (124, 156)
  Vivace                       = (156, 176)
  Vivacissimo_Allegrissimo     = (172, 176)
  Presto                       = (168, 200)
  Prestissimo                  = (200, 305)

class Dynamics(Enum, metaclass=DirectValueEnumMeta):
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
  ffff = 1
  fff  = 0.7079 
  ff   = 0.5012 
  f    = 0.3548 
  mf   = 0.2512
  mp   = 0.1778
  p    = 0.1259
  pp   = 0.0891
  ppp  = 0.0631
  pppp = 0.0447

class Articulation(Enum, metaclass=DirectValueEnumMeta):
  '''
  Enum for musical articulation styles, each represented by a tuple of values.
  These values modify the attack time, decay, and sustain level of a note.

  The first value in the tuple is the scalar for attack time, the second for decay,
  and the third is the sustain level.

  Example use:
  `>>> Articulation.Staccato`
  '''

  Legato    = (0.9, 1.0, 0.9)  # Longer attack, full decay, high sustain
  Staccato  = (0.1, 0.5, 0.3)  # Quick attack, shortened decay, low sustain
  Marcato   = (0.2, 0.7, 0.6)  # Quick attack, moderate decay, medium sustain
  Tenuto    = (0.9, 1.1, 0.9)  # Longer attack, extended decay, high sustain
  Spiccato  = (0.05, 0.4, 0.2)  # Very quick attack, short decay, very low sustain
  Portato   = (0.3, 0.9, 0.7)  # Moderate attack, full decay, medium-high sustain
  Accent    = (0.2, 0.8, 0.4)  # Quick attack, slightly shortened decay, medium-low sustain
  Sforzando = (0.2, 1.0, 0.5)  # Very quick attack, full decay, medium sustain

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

def percieved_tempo(durations: list) -> float:
  '''
  Given a list of durations, returns the percieved tempo.
  '''
  pass
