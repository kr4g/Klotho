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
  '''
  Reduce an interval to within the span of a specified octave.
  
  Args:
    interval: The musical interval to be octave-reduced.
    equave: The span of the octave for reduction, default is 2.
    n_equaves: The number of equaves, default is 1.
    
  Returns:
    The equave-reduced interval as a float.
  '''
  interval = Fraction(interval)
  equave = Fraction(equave)
  while interval < 1:
    interval *= equave
  while interval >= equave**n_equaves:
    interval /= equave
  return interval

def reduce_interval(interval:Union[Fraction, int, float, str], equave:Union[Fraction, int, float, str] = 2, n_equaves:int = 1) -> Fraction: 
  '''
  Fold an interval to within a specified range.

  Args:
    interval: The interval to be wrapped.
    equave: The equave value, default is 2.
    n_equaves: The number of equaves, default is 1.

  Returns:
    The folded interval as a float.
  '''
  interval = Fraction(interval)
  equave = Fraction(equave)  
  while interval < 1/(equave**n_equaves):
    interval *= equave
  while interval >= (equave**n_equaves):
    interval /= equave
  return interval

def reduce_interval_relative(target: Union[Fraction, int, float, str], source: Union[Fraction, int, float, str], equave: Union[Fraction, int, float, str] = 2) -> Fraction:
    '''
    Fold a target interval to minimize its distance from a source interval through octave reduction.

    Args:
        target: The interval to be folded
        source: The reference interval to fold relative to
        equave: The equave value, default is 2 (octave)

    Returns:
        The folded interval as a Fraction that minimizes distance from source
    '''
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
    '''
    Fold a sequence of intervals where each interval is folded relative to its neighbors.
    The first and last intervals remain unchanged, serving as anchors.
    Intermediate intervals are folded to minimize octave displacement between adjacent pairs.

    Args:
        sequence: List of intervals to be folded
        equave: The equave value, default is 2 (octave)

    Returns:
        List of folded intervals as Fractions, preserving original start and end values
    '''
    if len(sequence) <= 2:
        return [Fraction(x) for x in sequence]
    
    result = [Fraction(x) for x in sequence]
    
    for i in range(1, len(sequence)-1):
        result[i] = reduce_interval_relative(result[i], result[i-1], equave)
    
    for i in range(len(sequence)-2, 0, -1):
        result[i] = reduce_interval_relative(result[i], result[i+1], equave)
    
    return result
  
def fold_interval(interval: Union[Fraction, int, float, str], lower_thresh: Union[Fraction, int, float, str], upper_thresh: Union[Fraction, int, float, str]) -> Fraction:
    '''
    Fold an interval by reflecting it relative to explicit threshold boundaries.
    If interval exceeds upper threshold, measure how far above it is and move that 
    same distance down FROM the upper threshold.
    If interval is below lower threshold, measure how far below it is and move that
    same distance up FROM the lower threshold.

    Args:
        interval: The interval to be folded
        lower_thresh: The lower threshold interval
        upper_thresh: The upper threshold interval

    Returns:
        The folded interval as a Fraction
    '''
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
  '''
  Fold a frequency value to within a specified range.
  
  Args:
    freq: The frequency to be wrapped.
    lower: The lower bound of the range.
    upper: The upper bound of the range.
    
  Returns:
    The folded frequency as a float.
  '''
  equave = Fraction(equave)
  while freq < lower:
      freq *= equave
  while freq > upper:
      freq /= equave  
  return float(freq)