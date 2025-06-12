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
    'ratio_to_cents',
    'cents_to_ratio',
    'cents_to_setclass',
    'ratio_to_setclass',
    'split_interval',
    'harmonic_mean',
    'arithmetic_mean',
    'logarithmic_distance',
    'interval_cost',
    'n_tet',
    'ratios_n_tet'
]

def ratio_to_cents(ratio: Union[int, float, Fraction, str], round_to: int = 4) -> float:
  '''
  Convert a musical interval ratio to cents, a logarithmic unit of measure.
  
  Args:
    ratio: The musical interval ratio as a string (e.g., '3/2') or float.
    
  Returns:
    The interval in cents as a float.
  '''
  # bad...
  # if isinstance(ratio, str):
  #   numerator, denominator = map(float, ratio.split('/'))
  # else:  # assuming ratio is already a float
  #   numerator, denominator = ratio, 1.0
  if isinstance(ratio, str):
    ratio = Fraction(ratio)
    numerator, denominator = ratio.numerator, ratio.denominator
  else:  # assuming ratio is already a float/int
    ratio = Fraction(ratio)
    numerator, denominator = ratio.numerator, ratio.denominator
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

def split_interval(interval:Union[int, float, Fraction, str], n:int = 2):
    '''
    Find the smallest sequence of n+1 integers that form n equal subdivisions of a given interval ratio.
    
    For a given interval ratio r and number of divisions n, finds a sequence of integers [a₀, a₁, ..., aₙ]
    where each adjacent pair forms the same ratio, and aₙ/a₀ equals the target ratio r.
    
    Algorithm:
    1. Initialize k = 1
    2. Loop:
        a. Calculate step size d = (r-1)k/n where r is target ratio
        b. If d is an integer:
            - Generate sequence [k, k+d, k+2d, ..., k+nd]
            - If sequence[n]/sequence[0] equals target ratio:
                return sequence and k
        c. Increment k
    
    Args:
        interval: The target interval ratio to be subdivided
        n: Number of equal subdivisions (default: 2)
        
    Returns:
        A named tuple containing:
            - sequence: List of n+1 integers forming the subdivisions
            - k: The smallest starting value that produces valid subdivisions
            
    Example:
        split_interval('3/2', 2) returns sequence [4, 5, 6] and k=4
        because 5/4 = 6/5 = √(3/2)
    '''
    result = namedtuple('result', ['sequence', 'k'])

    multiplier = Fraction(interval)
    k = 1
    while True:
        d = ((multiplier-1) * k) / n
        if d.denominator == 1:
            sequence = [k + i*int(d) for i in range(n+1)]
            if Fraction(sequence[-1], sequence[0]) == multiplier:
                return result(sequence, k)
        k += 1

def harmonic_mean(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str]) -> Fraction:
    '''
    Calculate the harmonic mean between two values.
    
    The harmonic mean is defined as: 2 / (1/a + 1/b)
    
    Args:
        a: First value
        b: Second value
        
    Returns:
        The harmonic mean as a Fraction
    '''
    a, b = Fraction(a), Fraction(b)
    return 2 / (1/a + 1/b)

def arithmetic_mean(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str]) -> Fraction:
    '''
    Calculate the arithmetic mean between two values.
    
    The arithmetic mean is defined as: (a + b) / 2
    
    Args:
        a: First value
        b: Second value
        
    Returns:
        The arithmetic mean as a Fraction
    '''
    a, b = Fraction(a), Fraction(b)
    return (a + b) / 2

def logarithmic_distance(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str], 
                         equave: Union[int, float, Fraction, str] = 2) -> float:
    """
    Calculate the logarithmic distance between two musical intervals.
    
    Args:
        a: First interval
        b: Second interval
        equave: The equave to use for logarithmic scaling (default: 2 for octave)
        
    Returns:
        Logarithmic distance between the intervals
    """
    match a:
        case int() as i:
            r1 = Fraction(i, 1)
        case Fraction() as f:
            r1 = f
        case str() as s:
            r1 = Fraction(s)
        case _:
            raise TypeError("Unsupported type")

    match b:
        case int() as i:
            r2 = Fraction(i, 1)
        case Fraction() as f:
            r2 = f
        case str() as s:
            r2 = Fraction(s)
        case _:
            raise TypeError("Unsupported type")
            
    dist_interval = r2 / r1
    return abs(np.log(float(dist_interval)) / np.log(float(equave)))

def interval_cost(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str], diff_coeff: float = 1.0, prime_coeff: float = 1.0,
                  equave: Union[int, float, Fraction, str] = 2) -> float:
    match a:
        case int() as i:
            r1 = Fraction(i, 1)
        case Fraction() as f:
            r1 = f
        case str() as s:
            r1 = Fraction(s)
        case _:
            raise TypeError("Unsupported type")

    match b:
        case int() as i:
            r2 = Fraction(i, 1)
        case Fraction() as f:
            r2 = f
        case str() as s:
            r2 = Fraction(s)
        case _:
            raise TypeError("Unsupported type")

    log_dist = logarithmic_distance(r1, r2, equave)

    f1 = to_factors(r1)
    f2 = to_factors(r2)
    p_all = set(f1.keys()) | set(f2.keys())
    prime_diff = sum(abs(f1.get(p, 0) - f2.get(p, 0)) for p in p_all)

    return diff_coeff * log_dist + prime_coeff * prime_diff

def n_tet(divisions: int = 12, equave: Union[int, float, Fraction, str] = 2, nth_division: int = 1, symbolic: bool = False) -> Union[float, Rational]:
    '''
    Calculate the size of the nth division of an interval in equal temperament.
    
    Args:
        divisions: The number of equal divisions (default: 12)
        equave: The interval to divide (default: 2 for octave)
        nth_division: The nth division to calculate (default: 1)
        symbolic: If True, return symbolic expression instead of float (default: False)
    
    Returns:
        The frequency ratio either as a float or as a sympy expression
    '''
    ratio = root(Fraction(equave), Rational(divisions)) ** nth_division
    return ratio if symbolic else float(ratio)

def ratios_n_tet(divisions: int = 12, equave: Union[int, float, Fraction, str] = 2, symbolic: bool = False) -> List[Union[float, Rational]]:
  '''
  Calculate the ratios of the divisions of an interval in equal temperament.

  see:  https://en.wikipedia.org/wiki/Equal_temperament

  Args:
    divisions: The number of equal divisions
    equave: The interval to divide (default is 2 for an octave)
    symbolic: If True, return symbolic expression instead of float (default: False)
    
  Returns:
    A list of the frequency ratios of the divisions
  '''
  return [n_tet(divisions, equave, nth_division, symbolic) for nth_division in range(divisions)]
