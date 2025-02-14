# ------------------------------------------------------------------------------------
# Klotho/klotho/tonos/tonos.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
General functions for performing calculations and computations related to pitch and 
frequency.
--------------------------------------------------------------------------------------
'''
from typing import Union, List, Tuple, Dict, Set
from collections import namedtuple
from fractions import Fraction
import numpy as np
from sympy import Rational, root
import pandas as pd

A4_Hz   = 440.0
A4_MIDI = 69

from utils.data_structures.enums import DirectValueEnumMeta, Enum  

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
  
    class names:
      as_sharps = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
      as_flats  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


class Pitch:
    def __init__(self, pitchclass: str = 'A', octave: int = 4, cents_offset: float = 0.0, partial: int = 1):
        self._data = pd.DataFrame([{
            'pitchclass': pitchclass,
            'octave': octave,
            'cents_offset': cents_offset,
            'partial': partial,
            'freq': pitchclass_to_freq(pitchclass, octave, cents_offset)
        }]).set_index(pd.Index(['']))
    
    @property
    def pitchclass(self):
        return self._data['pitchclass'].iloc[0]
    
    @property
    def octave(self):
        return self._data['octave'].iloc[0]
    
    @property
    def cents_offset(self):
        return self._data['cents_offset'].iloc[0]
    
    @property
    def partial(self):
        return self._data['partial'].iloc[0]
    
    @property
    def freq(self):
        return self._data['freq'].iloc[0]
    
    @property
    def virtual_fundamental(self):
        return Pitch(*partial_to_fundamental(self.pitchclass, self.octave, self.partial, self.cents_offset))
    
    @cents_offset.setter
    def cents_offset(self, value):
        self._data.at['', 'cents_offset'] = value
        self._data.at['', 'freq'] = pitchclass_to_freq(self.pitchclass, self.octave, value)
    
    @partial.setter
    def partial(self, value):
        self._data.at['', 'partial'] = value
    
    def __str__(self):
        return f'{self.pitchclass}{self.octave}'
    
    def __repr__(self):
        display_df = self._data.copy()
        display_df['freq'] = display_df['freq'].round(2)
        display_df['cents_offset'] = display_df['cents_offset'].round(2)
        
        df_str = str(display_df)
        width = max(len(line) for line in df_str.split('\n'))
        border = '-' * width
        
        return f"{border}\n{df_str}\n{border}\n"


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
  return 100 * (12 * np.log2(frequency / A4_Hz) + A4_MIDI)

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
  return A4_Hz * (2 ** ((midicents - A4_MIDI * 100) / 1200.0))

def midicents_to_pitchclass(midicents: float) -> namedtuple:
  '''
  Convert MIDI cents to a pitch class with offset in cents.
  
  Args:
    midicents: The MIDI cent value to convert.
    
  Returns:
    A tuple containing the pitch class and the cents offset.
  '''
  result = namedtuple('result', ['pitchclass', 'octave', 'cents_offset'])
  PITCH_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
  midi = midicents / 100
  midi_round = round(midi)
  note_index = int(midi_round) % len(PITCH_LABELS)
  octave = int(midi_round // len(PITCH_LABELS)) - 1  # MIDI starts from C-1
  pitch_label = PITCH_LABELS[note_index]
  cents_diff = (midi - midi_round) * 100
  return result(pitch_label, octave, round(cents_diff, 4))
  # return Pitch(pitch_label, octave, round(cents_diff, 4))

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

def freq_to_pitchclass(freq: float, cent_round: int = 4) -> namedtuple:
    '''
    Converts a frequency to a pitch class with offset in cents.
    
    Args:
        freq: The frequency in Hertz to convert.
        cent_round: Number of decimal places to round cents to
    
    Returns:
        A tuple containing the pitch class and the cents offset.
    '''
    result = namedtuple('result', ['pitchclass', 'octave', 'cents_offset'])
    PITCH_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
    n_PITCH_LABELS = len(PITCH_LABELS)
    midi = A4_MIDI + n_PITCH_LABELS * np.log2(freq / A4_Hz)
    midi_round = round(midi)
    note_index = int(midi_round) % n_PITCH_LABELS
    octave = int(midi_round // n_PITCH_LABELS) - 1  # MIDI starts from C-1
    pitch_label = PITCH_LABELS[note_index]
    cents_diff = (midi - midi_round) * 100
    
    return result(pitch_label, octave, round(cents_diff, cent_round))

def pitchclass_to_freq(pitchclass: str, octave: int = 4, cent_offset: float = 0.0, hz_round: int = 4, A4_Hz=A4_Hz, A4_MIDI=A4_MIDI):
    '''
    Converts a pitch class with offset in cents to a frequency.
    
    Args:
        pitchclass: The pitch class (like "C4" or "F#-2") to convert.
        cent_offset: The cents offset, default is 0.0.
        A4_Hz: The frequency of A4, default is 440 Hz.
        A4_MIDI: The MIDI note number of A4, default is 69.
    
    Returns:
        The frequency in Hertz.
    '''
    # Try both sharp and flat notations
    SHARP_LABELS = PITCH_CLASSES.N_TET_12.names.as_sharps
    FLAT_LABELS = PITCH_CLASSES.N_TET_12.names.as_flats
    
    try:
        note_index = SHARP_LABELS.index(pitchclass)
    except ValueError:
        try:
            note_index = FLAT_LABELS.index(pitchclass)
        except ValueError:
            raise ValueError(f"Invalid pitch class: {pitchclass}")

    midi = note_index + (octave + 1) * 12
    midi = midi - A4_MIDI
    midi = midi + cent_offset / 100
    frequency = A4_Hz * (2 ** (midi / 12))
    return round(frequency, hz_round)

def partial_to_fundamental(pitchclass: str, octave: int = 4, partial: int = 1, cent_offset: float = 0.0) -> Tuple[str, float]:
    '''
    Calculate the fundamental frequency given a pitch class and its partial number.
    
    Args:
        pitchclass: The pitch class with octave (e.g., "A4", "C#3", "Bb2")
        partial: The partial number (integer >= 1)
        cent_offset: The cents offset from the pitch class, default is 0.0
        
    Returns:
        A tuple containing the fundamental's pitch class with octave and cents offset
    '''
    if partial < 1:
        raise ValueError("Partial number must be 1 or greater")

    freq = pitchclass_to_freq(pitchclass, octave, cent_offset)
    fundamental_freq = freq / partial
    return freq_to_pitchclass(fundamental_freq)

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

def first_equave(harmonic: Union[int, float, Fraction], equave: Union[int, float, Fraction, str] = 2, max_equave: Union[int, float, Fraction, str] = None):
  '''
  Returns the first equave in which a harmonic first appears.
  
  Args:
    harmonic: A harmonic.
    max_equave: The maximum equave to search, default is None.
    
  Returns:
    The first equave in which the harmonic first appears as an integer.
  '''
  equave = Fraction(equave)
  max_equave = Fraction(max_equave) if max_equave is not None else None
  n_equave = 0
  while max_equave is None or n_equave <= max_equave:
    if harmonic <= equave ** n_equave:
      return n_equave
    n_equave += 1
  return None

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
  while interval > equave**n_equaves:
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
  while interval > (equave**n_equaves):
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
    Fold a sequence of intervals where each interval is folded relative to the previous one.
    The first interval remains unchanged and serves as the initial reference.

    Args:
        sequence: List of intervals to be folded
        equave: The equave value, default is 2 (octave)

    Returns:
        List of folded intervals as Fractions
    '''
    if not sequence:
        return []
    
    result = [Fraction(sequence[0])]
    
    for i in range(1, len(sequence)):
        folded = reduce_interval_relative(sequence[i], result[i-1], equave)
        result.append(folded)
    
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

def fold_freq(freq: float, lower: float = 27.5, upper: float = 4186, equave: Union[int, float, Fraction, str] = 2) -> float:
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


