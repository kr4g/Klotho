from klotho.utils.algorithms.factors import to_factors
from typing import Union, List, Tuple, Dict, Set
from fractions import Fraction

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


def _refuse_non_positive(where: str, arg: str, value) -> ValueError:
  """Build the refusal for a value that no amount of reduction can move."""
  return ValueError(
      f"{where} cannot reduce {arg}={value!r}. Reduction multiplies by the "
      f"equave until the value reaches the bottom of the range, and no number "
      f"of multiplications carries zero or a negative number there -- the loop "
      f"would never end, and the process would hang with no exception and no "
      f"output. Ratios and frequencies are positive by definition; a 0 here is "
      f"usually an empty product, or a division that collapsed further "
      f"upstream. Correct the value where it is produced, or drop it before "
      f"reducing it."
  )


def _refuse_degenerate_equave(where: str, equave) -> ValueError:
  """Build the refusal for an equave that cannot walk a value into range."""
  return ValueError(
      f"{where} cannot reduce by equave={equave!r}. An interval of equivalence "
      f"must be greater than 1: reduction walks the value into range by "
      f"multiplying or dividing by the equave, and an equave of 1 never moves "
      f"it, while an equave of 0 or less never moves it consistently upward -- "
      f"the loop would never end, and the process would hang with no exception "
      f"and no output. Use 2 for the octave, 3 for the Bohlen-Pierce tritave, "
      f"or any ratio above 1."
  )


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

  Raises
  ------
  ValueError
      If *interval* is zero or negative, or if *equave* is 1 or less.
      Either case would spin the reduction loop forever.
  """
  interval = Fraction(interval)
  equave = Fraction(equave)
  if interval <= 0:
    raise _refuse_non_positive('equave_reduce()', 'interval', interval)
  if equave <= 1:
    raise _refuse_degenerate_equave('equave_reduce()', equave)
  if equave == 2:
    # The guard above already established interval > 0, which this fast path
    # requires; it used to test that itself and fall through into the
    # unguarded slow loop, which is where the hang lived.
    # octave fast path: the multiply/divide loops are single bit-shifts.
    # Semantics preserved exactly: <1 multiplies until first >=1 (lands
    # in [1/2..1)*2 = [1,2)); >=2^n divides until first <2^n (lands in
    # [2^(n-1), 2^n)); in-range inputs pass through untouched.
    p, q = interval.numerator, interval.denominator
    if p < q:
      k = q.bit_length() - p.bit_length()
      if (p << k) < q:
        k += 1
      return Fraction(p << k, q)
    if p >= (q << n_equaves):
      m = max(1, p.bit_length() - q.bit_length() - n_equaves)
      while p >= (q << (n_equaves + m)):
        m += 1
      return Fraction(p, q << m)
    return interval
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

  Raises
  ------
  ValueError
      If *interval* is zero or negative, or if *equave* is 1 or less.
      Either case would spin the folding loop forever.
  """
  interval = Fraction(interval)
  equave = Fraction(equave)
  if interval <= 0:
    raise _refuse_non_positive('reduce_interval()', 'interval', interval)
  if equave <= 1:
    raise _refuse_degenerate_equave('reduce_interval()', equave)
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

    Raises
    ------
    ValueError
        If *target* or *source* is zero or negative, or if *equave* is 1 or
        less. Any of these would spin the transposition loop forever.
    """
    target = Fraction(target)
    source = Fraction(source)
    equave = Fraction(equave)

    if target <= 0:
        raise _refuse_non_positive('reduce_interval_relative()', 'target', target)
    if source <= 0:
        raise _refuse_non_positive('reduce_interval_relative()', 'source', source)
    if equave <= 1:
        raise _refuse_degenerate_equave('reduce_interval_relative()', equave)

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

  Raises
  ------
  ValueError
      If *freq* is zero or negative, or if *equave* is 1 or less. Either
      case would spin the folding loop forever.
  """
  equave = Fraction(equave)
  if freq <= 0:
    raise _refuse_non_positive('reduce_freq()', 'freq', freq)
  if equave <= 1:
    raise _refuse_degenerate_equave('reduce_freq()', equave)
  while freq < lower:
      freq *= equave
  while freq > upper:
      freq /= equave  
  return float(freq)