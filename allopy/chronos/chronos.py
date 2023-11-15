# ------------------------------------------------------------------------------------
# AlloPy/allopy/chronos/chronos.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------

The `chronos` base module provides general functions for performing calculations and
computations related to time and rhythm in music.

--------------------------------------------------------------------------------------
'''

from fractions import Fraction

def seconds_to_hmsms(seconds: float, as_string=True) -> str:
    '''
    Convert a duration from seconds to a formatted string in hours, minutes, seconds, and milliseconds.

    Args:
    seconds (float): The duration in seconds.
    as_string (bool, optional): Whether to return the result as a string or as a tuple of integers. 
    Defaults to True.

    Returns:
    str: The formatted duration string in the form 'hours:minutes:seconds:milliseconds'.
    tuple: The formatted duration as a tuple of integers in the form (hours, minutes, seconds, milliseconds).
    '''
    
    h = int(seconds // 3600)
    seconds %= 3600
    m = int(seconds // 60)
    seconds %= 60
    s = int(seconds)
    ms = int((seconds - s) * 1000)    
    
    return f'{h}:{m:02}:{s:02}:{ms:03}' if as_string else (h, m, s, ms)

def beat_duration(ratio: str, bpm: float, beat_ratio: str = '1/4') -> float:
  '''
  Calculate the duration in seconds of a musical beat given a ratio and tempo.

  The beat duration is determined by the ratio of the beat to a reference beat duration (beat_ratio),
  multiplied by the tempo factor derived from the beats per minute (BPM).

  Args:
  ratio (str): The ratio of the desired beat duration to a whole note (e.g., '1/4' for a quarter note).
  bpm (float): The tempo in beats per minute.
  beat_ratio (str, optional): The reference beat duration ratio, defaults to a quarter note '1/4'.

  Returns:
  float: The beat duration in seconds.
  '''
  
  tempo_factor = 60 / bpm
  if isinstance(ratio, str):
    ratio_numerator, ratio_denominator = map(int, ratio.split('/'))
    ratio_value = ratio_numerator / ratio_denominator
  else:
    ratio_value = float(ratio)
  # ratio_value = Fraction(ratio)
  beat_numerator, beat_denominator = map(int, beat_ratio.split('/'))
  return tempo_factor * ratio_value * (beat_denominator / beat_numerator)

def duration_beat(duration: float, bpm: float, beat_ratio: str = '1/4', max_denominator: float = 16) -> Fraction:
  '''
  Finds the closest beat ratio for a given duration at a certain tempo.
  
  Args:
  duration (float): The duration in seconds.
  bpm (float): The tempo in beats per minute.
  beat_ratio (str, optional): The reference beat duration ratio, defaults to a quarter note '1/4'.
  
  Returns:
  str: The closest beat ratio as a string in the form 'numerator/denominator'.
  '''
  
  approximate_ratio = lambda x: Fraction(x).limit_denominator(max_denominator)
  
  beat_numerator, beat_denominator = map(int, beat_ratio.split('/'))
  reference_beat_duration = 60 / bpm * (beat_denominator / beat_numerator)
  beat_count = duration / reference_beat_duration
  return approximate_ratio(beat_count)

def metric_modulation(current_tempo: float, current_beat_value: float, new_beat_value: float) -> float:
  '''
  Determine the new tempo (in BPM) for a metric modulation from one metric value to another.

  Metric modulation is calculated by maintaining the duration of a beat constant while changing
  the note value that represents the beat, effectively changing the tempo.
  
  see:  https://en.wikipedia.org/wiki/Metric_modulation

  Args:
  current_tempo (float): The original tempo in beats per minute.
  current_beat_value (float): The note value (as a fraction of a whole note) representing one beat before modulation.
  new_beat_value (float): The note value (as a fraction of a whole note) representing one beat after modulation.

  Returns:
  float: The new tempo in beats per minute after the metric modulation.
  '''
  current_duration = 60 / current_tempo * current_beat_value
  new_tempo = 60 / current_duration * new_beat_value
  return new_tempo
