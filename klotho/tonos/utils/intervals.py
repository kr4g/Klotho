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
    'fold_cents_symmetric',
    'split_partial',
    'harmonic_mean',
    'arithmetic_mean',
    'harmonic_distance',
    'logarithmic_distance',
    'interval_cost',
    'n_tet',
    'ratios_n_tet'
]

def ratio_to_cents(ratio: Union[int, float, Fraction, str], round_to: int = 4) -> float:
  """
  Convert a musical interval ratio to cents.

  Cents are a logarithmic unit where 1200 cents equals one octave (2/1).

  Parameters
  ----------
  ratio : int, float, Fraction, or str
      The interval ratio (e.g., ``'3/2'``, ``1.5``).
  round_to : int, optional
      Decimal places to round the result. Default is 4.

  Returns
  -------
  float
      The interval size in cents.

  Examples
  --------
  >>> ratio_to_cents('3/2')
  701.955
  """
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
  """
  Convert cents to a frequency ratio.

  Parameters
  ----------
  cents : float
      The interval in cents.

  Returns
  -------
  float
      The corresponding frequency ratio.

  Examples
  --------
  >>> cents_to_ratio(1200)
  2.0
  """
  return 2 ** (cents / 1200)

def cents_to_setclass(cent_value: float = 0.0, n_tet: int = 12, round_to: int = 2) -> float:
   """
   Convert a cent value to a pitch-class number in an equal-tempered system.

   Parameters
   ----------
   cent_value : float, optional
       Interval in cents. Default is 0.0.
   n_tet : int, optional
       Number of equal divisions per octave. Default is 12.
   round_to : int, optional
       Decimal places to round to. Default is 2.

   Returns
   -------
   float
       The pitch-class number.
   """
   return round((cent_value / 100)  % n_tet, round_to)

def fold_cents_symmetric(cents: float) -> float:
    """
    Fold a cents value into the range [0, 600].
    
    This implements interval class equivalence, treating intervals
    and their inversions as equivalent. A minor third (~316 cents)
    and a major sixth (~884 cents) both fold to ~316 cents.
    
    The folding works by:
    1. Taking the absolute value
    2. Reducing modulo 1200 (one octave)
    3. If > 600, reflecting: 1200 - value

    Parameters
    ----------
    cents : float
        Cents value to fold.

    Returns
    -------
    float
        Folded cents value in range [0, 600].

    Examples
    --------
    >>> fold_cents_symmetric(316.0)  # minor third
    316.0
    
    >>> fold_cents_symmetric(884.0)  # major sixth (inversion of m3)
    316.0
    
    >>> fold_cents_symmetric(702.0)  # fifth
    498.0
    
    >>> fold_cents_symmetric(-316.0)  # negative minor third
    316.0
    """
    c = abs(cents) % 1200.0
    return c if c <= 600.0 else 1200.0 - c

def ratio_to_setclass(ratio: Union[str, float], n_tet: int = 12, round_to: int = 2) -> float:
  """
  Convert a musical interval ratio to a pitch-class number.

  Parameters
  ----------
  ratio : str or float
      The interval ratio (e.g., ``'3/2'``).
  n_tet : int, optional
      Number of equal divisions per octave. Default is 12.
  round_to : int, optional
      Decimal places to round to. Default is 2.

  Returns
  -------
  float
      The pitch-class number.
  """
  return cents_to_setclass(ratio_to_cents(ratio), n_tet, round_to)

def split_partial(interval:Union[int, float, Fraction, str], n:int = 2):
    """
    Find the smallest harmonic subdivision of an interval into *n* equal steps.

    Returns a sequence of *n + 1* integers ``[a₀, a₁, …, aₙ]`` where each
    adjacent pair forms the same ratio and ``aₙ / a₀`` equals the target
    interval.

    Parameters
    ----------
    interval : int, float, Fraction, or str
        The target interval ratio to subdivide.
    n : int, optional
        Number of equal subdivisions. Default is 2.

    Returns
    -------
    namedtuple
        A named tuple with fields:

        - ``harmonics`` -- list of *n + 1* integers forming the subdivision.
        - ``k`` -- the smallest starting integer that yields a valid result.

    Examples
    --------
    >>> split_partial('3/2', 2)
    result(harmonics=[4, 5, 6], k=4)
    """
    result = namedtuple('result', ['harmonics', 'k'])

    multiplier = Fraction(interval)
    k = 1
    while True:
        d = ((multiplier-1) * k) / n
        if d.denominator == 1:
            harmonics = [k + i*int(d) for i in range(n+1)]
            if Fraction(harmonics[-1], harmonics[0]) == multiplier:
                return result(harmonics, k)
        k += 1

def harmonic_mean(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str]) -> Fraction:
    """
    Calculate the harmonic mean of two values: ``2 / (1/a + 1/b)``.

    In music, the harmonic mean of two intervals produces the
    interval that divides the span *harmonically* (unequal division
    weighted toward the smaller value).

    Parameters
    ----------
    a : int, float, Fraction, or str
        First value.
    b : int, float, Fraction, or str
        Second value.

    Returns
    -------
    Fraction
        The harmonic mean.
    """
    a, b = Fraction(a), Fraction(b)
    return 2 / (1/a + 1/b)

def arithmetic_mean(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str]) -> Fraction:
    """
    Calculate the arithmetic mean of two values: ``(a + b) / 2``.

    In music, the arithmetic mean of two intervals produces the
    interval that divides the span *arithmetically* (equal division
    by frequency difference).

    Parameters
    ----------
    a : int, float, Fraction, or str
        First value.
    b : int, float, Fraction, or str
        Second value.

    Returns
    -------
    Fraction
        The arithmetic mean.
    """
    a, b = Fraction(a), Fraction(b)
    return (a + b) / 2

def harmonic_distance(ratio: Union[int, float, Fraction, str]) -> float:
    """
    Compute the Tenney height (harmonic distance) of a ratio.

    For a ratio p/q in lowest terms the Tenney height is defined as
    log2(p * q).  Simpler ratios (small numerator and denominator)
    yield lower values; more complex ratios yield higher values.

    Parameters
    ----------
    ratio : int, float, Fraction, or str
        The ratio to measure.  Strings like ``'3/2'`` are accepted.

    Returns
    -------
    float
        The Tenney height (base-2 logarithm of numerator * denominator).

    Examples
    --------
    >>> harmonic_distance('3/2')
    2.584962500721156

    >>> harmonic_distance('5/4')
    4.321928094887363

    >>> harmonic_distance(Fraction(9, 8))
    6.169925001442312
    """
    r = Fraction(ratio)
    p, q = abs(r.numerator), abs(r.denominator)
    return float(np.log2(p * q))


def logarithmic_distance(a: Union[int, float, Fraction, str], b: Union[int, float, Fraction, str], 
                         equave: Union[int, float, Fraction, str] = 2) -> float:
    """
    Calculate the logarithmic distance between two musical intervals.

    Parameters
    ----------
    a : int, float, Fraction, or str
        First interval.
    b : int, float, Fraction, or str
        Second interval.
    equave : int, float, Fraction, or str, optional
        Base for logarithmic scaling. Default is 2 (octave).

    Returns
    -------
    float
        The absolute logarithmic distance.
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
    """
    Compute a weighted cost of moving between two intervals.

    Combines logarithmic distance with prime-factorization distance.

    Parameters
    ----------
    a : int, float, Fraction, or str
        First interval.
    b : int, float, Fraction, or str
        Second interval.
    diff_coeff : float, optional
        Weight for logarithmic distance. Default is 1.0.
    prime_coeff : float, optional
        Weight for prime-exponent difference. Default is 1.0.
    equave : int, float, Fraction, or str, optional
        Base for logarithmic scaling. Default is 2.

    Returns
    -------
    float
        The weighted cost.
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

    log_dist = logarithmic_distance(r1, r2, equave)

    f1 = to_factors(r1)
    f2 = to_factors(r2)
    p_all = set(f1.keys()) | set(f2.keys())
    prime_diff = sum(abs(f1.get(p, 0) - f2.get(p, 0)) for p in p_all)

    return diff_coeff * log_dist + prime_coeff * prime_diff

def n_tet(divisions: int = 12, equave: Union[int, float, Fraction, str] = 2, nth_division: int = 1, symbolic: bool = False) -> Union[float, Rational]:
    """
    Calculate the frequency ratio of the *nth* step in an equal temperament.

    Parameters
    ----------
    divisions : int, optional
        Number of equal divisions of the equave. Default is 12.
    equave : int, float, Fraction, or str, optional
        The interval to divide. Default is 2 (octave).
    nth_division : int, optional
        Which step to compute. Default is 1.
    symbolic : bool, optional
        If True, return a sympy expression instead of a float.
        Default is False.

    Returns
    -------
    float or sympy.Rational
        The frequency ratio.
    """
    ratio = root(Fraction(equave), Rational(divisions)) ** nth_division
    return ratio if symbolic else float(ratio)

def ratios_n_tet(divisions: int = 12, equave: Union[int, float, Fraction, str] = 2, symbolic: bool = False) -> List[Union[float, Rational]]:
  """
  Return all step ratios for an equal temperament.

  Parameters
  ----------
  divisions : int, optional
      Number of equal divisions. Default is 12.
  equave : int, float, Fraction, or str, optional
      The interval to divide. Default is 2 (octave).
  symbolic : bool, optional
      If True, return sympy expressions. Default is False.

  Returns
  -------
  list of float or sympy.Rational
      Frequency ratios for steps 0 through ``divisions - 1``.

  References
  ----------
  .. [1] https://en.wikipedia.org/wiki/Equal_temperament
  """
  return [n_tet(divisions, equave, nth_division, symbolic) for nth_division in range(divisions)]
