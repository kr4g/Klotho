# ------------------------------------------------------------------------------------
# AlloPy/allopy/tonos/tonos.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------

The `tonos` base module provides general functions for performing calculations and
computations related to pitch and frequency in music.

--------------------------------------------------------------------------------------
'''
from typing import Union, List, Tuple, Dict, Set
# from math import prod
import numpy as np
# import itertools

A4_Hz   = 440.0
A4_MIDI = 69

from enum import Enum, EnumMeta
class DirectValueEnumMeta(EnumMeta):
    def __getattribute__(cls, name):
        member = super().__getattribute__(name)
        if isinstance(member, cls):
            return member.value
        return member
      
class PITCH_CLASSES(Enum, metaclass=DirectValueEnumMeta):
  class N_TET_12(Enum, metaclass=DirectValueEnumMeta):
    C  = 0
    Cs = 1
    Db = 1
    D  = 2
    Ds = 3
    Eb = 3
    E  = 4
    Es = 5
    Fb = 4
    F  = 5
    Fs = 6
    Gb = 6
    G  = 7
    Gs = 8
    Ab = 8
    A  = 9
    As = 10
    Bb = 10
    B  = 11
    Bs = 0

    # @classmethod
    # def names(cls):
    #     return ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    class names:
      as_sharps = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
      as_flats  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

def freq_to_midicents(frequency: float) -> float:
  '''
  Convert a frequency in Hertz to MIDI cents notation.
  
  MIDI cents are a logarithmic unit of measure used for musical intervals.
  The cent is equal to 1/100th of a semitone. There are 1200 cents in an octave.
  
  MIDI cents combines MIDI note numbers (denoting pitch with) with cents (denoting
  intervals).  The MIDI note number is the integer part of the value, and the cents
  are the fractional part.
  
  The MIDI note for A above middle C is 69, and the frequency is 440 Hz.  The MIDI
  cent value for A above middle C is 6900.  Adding or subtracting 100 to the MIDI
  cent value corresponds to a change of one semitone (one note number in the Western
  dodecaphonic equal-tempered "chromatic" scale).
  
  Values other than multiple of 100 indicate microtonal intervals.

  Args:
  frequency: The frequency in Hertz to convert.

  Returns:
  The MIDI cent value as a float.
  '''
  return 100 * (12 * np.log2(frequency / 440.0) + 69)

def midicents_to_freq(midicents: float) -> float:
  '''
  Convert MIDI cents back to a frequency in Hertz.
  
  MIDI cents are a logarithmic unit of measure used for musical intervals.
  The cent is equal to 1/100th of a semitone. There are 1200 cents in an octave.
  
  MIDI cents combines MIDI note numbers (denoting pitch with) with cents (denoting
  intervals).  The MIDI note number is the integer part of the value, and the cents
  are the fractional part.
  
  The MIDI note for A above middle C is 69, and the frequency is 440 Hz.  The MIDI
  cent value for A above middle C is 6900.  Adding or subtracting 100 to the MIDI
  cent value corresponds to a change of one semitone (one note number in the Western
  dodecaphonic equal-tempered "chromatic" scale).
  
  Values other than multiple of 100 indicate microtonal intervals.
  
  Args:
    midicents: The MIDI cent value to convert.
    
  Returns:
    The corresponding frequency in Hertz as a float.
  '''
  return 440.0 * (2 ** ((midicents - A4_MIDI * 100) / 1200.0))

def midicents_to_pitchclass(midicents: float) -> str:
  '''
  Convert MIDI cents to a pitch class with offset in cents.
  
  Args:
    midicents: The MIDI cent value to convert.
    
  Returns:
    A tuple containing the pitch class and the cents offset.
  '''
  PITCH_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
  midi = midicents / 100
  midi_round = round(midi)
  note_index = int(midi_round) % len(PITCH_LABELS)
  octave = int(midi_round // len(PITCH_LABELS)) - 1  # MIDI starts from C-1
  pitch_label = PITCH_LABELS[note_index]
  cents_diff = (midi - midi_round) * 100
  return f'{pitch_label}{octave}', round(cents_diff, 4)

def ratio_to_cents(ratio: Union[str, float], round_to: int = 4) -> float:
  '''
  Convert a musical interval ratio to cents, a logarithmic unit of measure.
  
  Args:
    ratio: The musical interval ratio as a string (e.g., '3/2') or float.
    
  Returns:
    The interval in cents as a float.
  '''
  if isinstance(ratio, str):
    numerator, denominator = map(float, ratio.split('/'))
  else:  # assuming ratio is already a float
    numerator, denominator = ratio, 1.0
  return round(1200 * np.log2(numerator / denominator), round_to)

def cents_to_ratio(cents: float) -> str:
  '''
  Convert a musical interval in cents to a ratio.
  
  Args:
    cents: The interval in cents to convert.
    
  Returns:
    The interval ratio as a float.
  '''
  return 2 ** (cents / 1200)

def cents_to_setclass(cent_value: float = 0.0, n_tet: int = 12, round_to: int = 2) -> float:
   return round((cent_value / 100)  % n_tet, round_to)

def ratio_to_setclass(ratio: Union[str, float], n_tet: int = 12, round_to: int = 2) -> float:
  '''
  Convert a musical interval ratio to a set class.
  
  Args:
    ratio: The musical interval ratio as a string (e.g., '3/2') or float.
    n_tet: The number of divisions in the octave, default is 12.
    round_to: The number of decimal places to round to, default is 2.
    
  Returns:
    The set class as a float.
  '''
  return cents_to_setclass(ratio_to_cents(ratio), n_tet, round_to)

def freq_to_pitchclass(freq: float):
  '''
  Converts a frequency to a pitch class with offset in cents.
  
  Args:
    freq: The frequency in Hertz to convert.
    A4_Hz: The frequency of A4, default is 440 Hz.
    A4_MIDI: The MIDI note number of A4, default is 69.
  
  Returns:
    A tuple containing the pitch class and the cents offset.
  '''
  PITCH_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
  n_PITCH_LABELS = len(PITCH_LABELS)
  midi = A4_MIDI + n_PITCH_LABELS * np.log2(freq / A4_Hz)
  midi_round = round(midi)
  note_index = int(midi_round) % n_PITCH_LABELS
  octave = int(midi_round // n_PITCH_LABELS) - 1  # MIDI starts from C-1
  pitch_label = PITCH_LABELS[note_index]
  cents_diff = (midi - midi_round) * 100
  return f'{pitch_label}{octave}', cents_diff

import numpy as np

def pitchclass_to_freq(pitchclass: str, cent_offset: float = 0.0, A4_Hz=A4_Hz, A4_MIDI=A4_MIDI):

  '''
  Converts a pitch class with offset in cents to a frequency.
  
  Args:
    pitchclass: The pitch class (like "C4") to convert.
    cent_offset: The cents offset, default is 0.0.
    A4_Hz: The frequency of A4, default is 440 Hz.
    A4_MIDI: The MIDI note number of A4, default is 69.
  
  Returns:
    The frequency in Hertz.
  '''
  PITCH_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
  if pitchclass[-1].isdigit():
        note = pitchclass[:-1]
        octave = int(pitchclass[-1])
  else:  # Default to octave 4 if no octave is provided
      note = pitchclass
      octave = 4
  note_index = PITCH_LABELS.index(note)
  midi = note_index + (octave + 1) * 12
  midi = midi - A4_MIDI
  midi = midi + cent_offset / 100
  frequency = A4_Hz * (2 ** (midi / 12))
  return frequency

def octave_reduce(interval: float, octave: int = 1) -> float:
  '''
  Reduce an interval to within the span of a specified octave.
  
  Args:
    interval: The musical interval to be octave-reduced.
    octave: The span of the octave for reduction, default is 1 octave.
    
  Returns:
    The octave-reduced interval as a float.
  '''
  while interval >= 2**octave:
    interval /= 2
  return interval

# def norgard(n = 0):
#   '''
#   Per Norgard "Infinity Series" (1972)
#   '''
#   pass
