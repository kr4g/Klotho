from klotho.utils.algorithms.factors import to_factors
import math
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


# --- Cost guards on an equave reduction ---------------------------------
#
# ``_refuse_degenerate_equave`` above catches an equave of 1 or less, which
# never terminates at all. An equave a hair ABOVE 1 does terminate, in
# principle, and is useless in practice: reduction walks a degree into range
# one equave at a time, so the number of steps is (size of the degree)
# divided by (size of the equave).
#
# Two different things go wrong as that step count grows.
#
#   TIME. Each step is one arithmetic operation, so a million steps is a
#   visible pause and a billion is a frozen interpreter with no exception and
#   no output -- the same symptom the degenerate guard exists to prevent.
#
#   SIZE. In ratio mode the arithmetic is exact, so each division multiplies
#   the numerator and the denominator by the equave's own numerator and
#   denominator: the result grows by roughly one equave's worth of BITS per
#   step. Measured 2026-09-01: reducing 3/2 by 761963/761523 (one cent, a
#   20-bit numerator) takes 701 steps and lands on a Fraction whose numerator
#   is 13,699 bits -- 4,124 decimal digits. CPython refuses to render an
#   integer longer than ``sys.get_int_max_str_digits()`` (4300 digits by
#   default), so such an object is CONSTRUCTED successfully and then cannot
#   be printed: ``repr()`` raises "Exceeds the limit (4300 digits) for integer
#   string conversion". That is worse than a hang, because nothing looks wrong
#   until someone prints the scale.
#
# The size limit binds long before the time limit, so both are checked, and
# both are checked BEFORE any reduction runs. 14,000 bits is about 4,214
# decimal digits, which stays under CPython's 4,300-digit default with margin
# for the estimate being approximate (measured within 10% across two decades
# of equave sizes).
MAX_REDUCTION_STEPS = 100_000
MAX_REDUCTION_BITS = 14_000


def _size_in_cents(value) -> float:
  """Size of a positive ratio in cents, without ever calling ``float()`` on it.

  A Fraction produced by reduction can be far too large to survive
  ``float()``, so the logarithm is taken on the numerator and the denominator
  separately. Returns 0.0 for anything that is not a positive ratio; the
  zero/negative cases are refused by ``_refuse_non_positive`` at the point
  where they would actually spin.
  """
  if isinstance(value, Fraction):
    if value.numerator <= 0:
      return 0.0
    return 1200.0 * (math.log2(value.numerator) - math.log2(value.denominator))
  try:
    value = float(value)
  except (TypeError, ValueError, OverflowError):
    return 0.0
  if not (value > 0.0) or not math.isfinite(value):
    return 0.0
  return 1200.0 * math.log2(value)


def _refuse_costly_reduction(where: str, equave, steps: int, bits) -> ValueError:
  """Build the refusal for an equave so close to the unison that reducing by
  it would appear to hang, or would build a number too large to print."""
  detail = (
      f"about {steps:,} divisions per degree"
      if bits is None else
      f"about {steps:,} divisions per degree, ending on a number of roughly "
      f"{bits:,} bits ({int(bits * 0.30103):,} decimal digits)"
  )
  return ValueError(
      f"{where} cannot reduce by equave={equave!r}: it is too close to the "
      f"unison. Reduction walks each degree into range one equave at a time, "
      f"and this equave needs {detail}. Past that point the call stops "
      f"responding with no exception and no output, and in ratio mode the "
      f"result can exceed CPython's 4300-digit limit on printing an integer, "
      f"so the object is built and then raises when anyone prints it. Note "
      f"which reading applies: in ratios mode EVERY spelling of the equave is "
      f"a ratio -- 2, 2.0, Fraction(2, 1) and '2/1' are all the octave -- "
      f"while in cents mode the equave is a cents value, so 1200.0 is the "
      f"octave and 1901.955 the Bohlen-Pierce tritave."
  )


def _refuse_ratio_equave_in_cents_mode(where: str, equave) -> ValueError:
  """Build the refusal for a ratio written where cents are meant.

  A fraction -- a ``Fraction`` instance, or a string in fraction format like
  ``'3/1'`` -- is unambiguously a ratio everywhere else in Klotho. Written in
  a field that means cents it is a category error, not an ambiguity, so it is
  refused rather than guessed at in either direction.
  """
  try:
    as_ratio = Fraction(equave)
    ratio_cents = 1200.0 * (math.log2(as_ratio.numerator)
                            - math.log2(as_ratio.denominator))
    ratio_reading = (f"the interval {as_ratio.numerator}/{as_ratio.denominator}"
                     f", which is {ratio_cents:.4f} cents")
    ratio_fix = f"pass equave={ratio_cents:.4f}"
  except (ValueError, ZeroDivisionError, TypeError):
    ratio_reading = "an interval ratio"
    ratio_fix = "pass its size in cents"
  return ValueError(
      f"{where} was given interval_type='cents' with equave={equave!r}, which "
      f"is written as a RATIO. In cents mode the equave is a CENTS value, so "
      f"the two readings disagree and neither is guessed. Both readings, and "
      f"how to spell each: (1) you meant {ratio_reading} -- {ratio_fix}, or "
      f"keep equave={equave!r} and use interval_type='ratios'; (2) you meant "
      f"that many cents -- write it as a plain number, e.g. equave=1200.0 for "
      f"the octave or equave=1901.955 for the Bohlen-Pierce tritave. In "
      f"ratios mode no such refusal applies: 2, 2.0, Fraction(2, 1) and '2/1' "
      f"are all the octave."
  )


def check_reduction_cost(where: str, equave, degrees, interval_type: str = 'ratios') -> None:
  """Refuse an unaffordable equave reduction before any of it runs.

  Parameters
  ----------
  where : str
      Name of the caller, used in the refusal message.
  equave : Fraction or float
      The equave already resolved to the form *interval_type* works in: a
      ``Fraction`` ratio for ``"ratios"``, a cents ``float`` for ``"cents"``.
  degrees : iterable
      The converted degrees, in the same units as *equave*.
  interval_type : str, optional
      ``"ratios"`` or ``"cents"``. Default ``"ratios"``.
  """
  degrees = [d for d in degrees]
  if not degrees:
    return

  if interval_type == 'cents':
    equave_cents = float(equave)
    if not (equave_cents > 0.0) or not math.isfinite(equave_cents):
      raise _refuse_degenerate_equave(where, equave)
    widest = max((abs(float(d)) for d in degrees), default=0.0)
    steps = int(widest / equave_cents)
    if steps > MAX_REDUCTION_STEPS:
      raise _refuse_costly_reduction(where, equave, steps, None)
    return

  equave = Fraction(equave)
  if equave <= 1:
    raise _refuse_degenerate_equave(where, equave)
  equave_cents = 1200.0 * (math.log2(equave.numerator)
                           - math.log2(equave.denominator))
  # Bits added per division: measured against actual reductions across
  # equaves from 1 to 20 cents and denominators from 10**3 to 2**52, the
  # result's bit length came to 0.90-1.00 times this estimate.
  equave_bits = max(equave.numerator.bit_length(),
                    equave.denominator.bit_length())
  widest = max((abs(_size_in_cents(d)) for d in degrees), default=0.0)
  if equave_cents <= 0.0:
    # An exact Fraction strictly greater than 1 whose numerator and
    # denominator are within one float ulp of each other in log2 -- e.g.
    # Fraction(2**53 + 1, 2**53) -- measures as exactly 0.0 cents wide.
    # The equave is real, so the `equave <= 1` guard above does not fire,
    # but no finite number of divisions by it reduces anything, and
    # dividing by that width to price the work raises ZeroDivisionError
    # rather than the ValueError this function exists to produce.
    raise _refuse_costly_reduction(where, equave, MAX_REDUCTION_STEPS + 1, None)
  steps = int(widest / equave_cents)
  if steps > MAX_REDUCTION_STEPS:
    raise _refuse_costly_reduction(where, equave, steps, steps * equave_bits)
  if steps * equave_bits > MAX_REDUCTION_BITS:
    raise _refuse_costly_reduction(where, equave, steps, steps * equave_bits)


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