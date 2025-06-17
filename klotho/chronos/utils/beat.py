from typing import Union
from fractions import Fraction
from itertools import accumulate

__all__ = [
    'cycles_to_frequency',
    'beat_duration',
    'calc_onsets',
]

def cycles_to_frequency(cycles: Union[int, float], duration: float) -> float:
    '''
    Calculate the frequency (in Hz) needed to produce a specific number of cycles within a given duration.

    Args:
    cycles (Union[int, float]): The desired number of complete cycles
    duration (float): The time duration in seconds

    Returns:
    float: The frequency in Hertz (Hz) that will produce the specified number of cycles in the given duration

    Example:
    >>> cycles_to_frequency(4, 2)  # 4 cycles in 2 seconds = 2 Hz
    2.0
    '''
    return cycles / duration

def beat_duration(ratio:Union[int, float, Fraction, str], bpm:Union[int, float], beat_ratio:Union[int, float, Fraction, str] = '1/4') -> float:
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
  ratio_value  = float(Fraction(ratio))
  beat_ratio   = Fraction(beat_ratio)
  return tempo_factor * ratio_value * (beat_ratio.denominator / beat_ratio.numerator)

def calc_onsets(durations:tuple):
    return tuple(accumulate([0] + list(abs(r) for r in durations[:-1])))

