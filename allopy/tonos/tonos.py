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
from math import prod
import numpy as np
import itertools

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
  return 440.0 * (2 ** ((midicents - 6900) / 1200.0))

def ratio_to_cents(ratio: Union[str, float]) -> float:
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
  return 1200 * np.log2(numerator / denominator)

def cents_to_ratio(cents: float) -> str:
  '''
  Convert a musical interval in cents to a ratio.
  
  Args:
    cents: The interval in cents to convert.
    
  Returns:
    The interval ratio as a float.
  '''
  return 2 ** (cents / 1200)

def freq_to_pitchclass(freq: float, A4_Hz=440.0, A4_MIDI=69):
  '''
  Converts a frequency to a pitch class with offset in cents.
  
  Args:
    freq: The frequency in Hertz to convert.
    A4_Hz: The frequency of A4, default is 440 Hz.
    A4_MIDI: The MIDI note number of A4, default is 69.
  
  Returns:
    A tuple containing the pitch class and the cents offset.
  '''
  PITCH_LABELS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
  midi = A4_MIDI + 12 * np.log2(freq / A4_Hz)
  midi_round = round(midi)
  note_index = int(midi_round) % 12
  octave = int(midi_round // 12) - 1  # MIDI starts from C-1
  pitch_label = PITCH_LABELS[note_index]
  cents_diff = (midi - midi_round) * 100
  return f'{pitch_label}{octave}', cents_diff

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

def norgard(n = 0):
  '''
  Per Norgard "Infinity Series" (1972)
  '''
  pass