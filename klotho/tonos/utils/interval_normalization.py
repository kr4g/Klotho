from klotho.utils.algorithms.factors import to_factors
from typing import Union, List, Tuple, Dict, Set
from collections import namedtuple
from fractions import Fraction
import numpy as np
from sympy import Rational, root
import pandas as pd

A4_Hz   = 440.0
A4_MIDI = 69

from klotho.utils.data_structures.enums import DirectValueEnumMeta, Enum  

__all__ = [
    'equave_reduce',
    'reduce_interval',
    'reduce_interval_relative',
    'reduce_sequence_relative',
    'fold_interval',
    'reduce_freq'
]

def equave_reduce(interval:Union[int, float, Fraction, str], equave:Union[Fraction, int, str, float] = 2, n_equaves:int = 1) -> Union[int, float, Fraction]:
  """
  Reduce an interval into the range ``[1, equave^n_equaves)``.

  Repeatedly multiplies or divides by *equave* until the interval
  falls within the target range.

  Parameters
  ----------
  interval : int, float, Fraction, or str
      The interval to reduce.
  equave : Fraction, int, str, or float, optional
      Interval of equivalence. Default is 2 (octave).
  n_equaves : int, optional
      Number of equaves for the reduction window. Default is 1.

  Returns
  -------
  Fraction
      The equave-reduced interval.
  """
  interval = Fraction(interval)
  equave = Fraction(equave)
  while interval < 1:
    interval *= equave
  while interval >= equave**n_equaves:
    interval /= equave
  return interval

def reduce_interval(interval:Union[Fraction, int, float, str], equave:Union[Fraction, int, float, str] = 2, n_equaves:int = 1) -> Fraction: 
  """
  Fold an interval into the bipolar range ``[1/equave^n, equave^n)``.

  Unlike ``equave_reduce``, the lower bound extends below unison,
  allowing sub-fundamental intervals to be represented.

  Parameters
  ----------
  interval : Fraction, int, float, or str
      The interval to fold.
  equave : Fraction, int, float, or str, optional
      Interval of equivalence. Default is 2.
  n_equaves : int, optional
      Number of equaves for the range. Default is 1.

  Returns
  -------
  Fraction
      The folded interval.
  """
  interval = Fraction(interval)
  equave = Fraction(equave)  
  while interval < 1/(equave**n_equaves):
    interval *= equave
  while interval >= (equave**n_equaves):
    interval /= equave
  return interval

def reduce_interval_relative(target: Union[Fraction, int, float, str], source: Union[Fraction, int, float, str], equave: Union[Fraction, int, float, str] = 2) -> Fraction:
    """
    Fold *target* to the equave transposition closest to *source*.

    Searches upward and downward by equave until the minimum absolute
    distance from *source* is found.

    Parameters
    ----------
    target : Fraction, int, float, or str
        The interval to fold.
    source : Fraction, int, float, or str
        The reference interval.
    equave : Fraction, int, float, or str, optional
        Interval of equivalence. Default is 2.

    Returns
    -------
    Fraction
        The transposition of *target* that minimizes ``|source - target|``.
    """
    target = Fraction(target)
    source = Fraction(source)
    equave = Fraction(equave)
    
    while target < 1:
        target *= equave
    while source < 1:
        source *= equave
        
    best_target = target
    min_distance = abs(source - target)
    
    test_up = target
    test_down = target
    while True:
        test_up *= equave
        test_down /= equave
        
        up_dist = abs(source - test_up)
        down_dist = abs(source - test_down)
        
        if up_dist < min_distance:
            min_distance = up_dist
            best_target = test_up
        elif down_dist < min_distance:
            min_distance = down_dist
            best_target = test_down
        else:
            break
            
    return best_target

def reduce_sequence_relative(sequence: List[Union[Fraction, int, float, str]], equave: Union[Fraction, int, float, str] = 2) -> List[Fraction]:
    """
    Fold a sequence of intervals to minimise octave jumps between neighbours.

    The first and last intervals are kept as anchors. Interior intervals are
    folded forward then backward to minimise adjacent displacement.

    Parameters
    ----------
    sequence : list of Fraction, int, float, or str
        Intervals to fold.
    equave : Fraction, int, float, or str, optional
        Interval of equivalence. Default is 2.

    Returns
    -------
    list of Fraction
        Folded intervals preserving the original start and end values.
    """
    if len(sequence) <= 2:
        return [Fraction(x) for x in sequence]
    
    result = [Fraction(x) for x in sequence]
    
    for i in range(1, len(sequence)-1):
        result[i] = reduce_interval_relative(result[i], result[i-1], equave)
    
    for i in range(len(sequence)-2, 0, -1):
        result[i] = reduce_interval_relative(result[i], result[i+1], equave)
    
    return result
  
def fold_interval(interval: Union[Fraction, int, float, str], lower_thresh: Union[Fraction, int, float, str], upper_thresh: Union[Fraction, int, float, str]) -> Fraction:
    """
    Reflect an interval back inside explicit threshold boundaries.

    If the interval exceeds the upper threshold, it is reflected
    downward by the overshoot distance; if below the lower threshold,
    it is reflected upward.

    Parameters
    ----------
    interval : Fraction, int, float, or str
        The interval to fold.
    lower_thresh : Fraction, int, float, or str
        Lower boundary.
    upper_thresh : Fraction, int, float, or str
        Upper boundary.

    Returns
    -------
    Fraction
        The folded interval.
    """
    interval = Fraction(interval)
    lower_thresh = Fraction(lower_thresh)
    upper_thresh = Fraction(upper_thresh)
    
    if interval > upper_thresh:
        distance = interval / upper_thresh
        return upper_thresh / distance
    elif interval < lower_thresh:
        distance = lower_thresh / interval
        return lower_thresh * distance
    
    return interval

def reduce_freq(freq: float, lower: float = 27.5, upper: float = 4186, equave: Union[int, float, Fraction, str] = 2) -> float:
  """
  Fold a frequency into a bounded range by equave transposition.

  Parameters
  ----------
  freq : float
      The frequency to fold.
  lower : float, optional
      Lower bound in Hertz. Default is 27.5 (A0).
  upper : float, optional
      Upper bound in Hertz. Default is 4186 (C8).
  equave : int, float, Fraction, or str, optional
      Interval of equivalence. Default is 2.

  Returns
  -------
  float
      The frequency folded into ``[lower, upper]``.
  """
  equave = Fraction(equave)
  while freq < lower:
      freq *= equave
  while freq > upper:
      freq /= equave  
  return float(freq)