from .frequency_conversion import pitchclass_to_freq, freq_to_pitchclass
from fractions import Fraction
from typing import Tuple, Union

__all__ = [
    'partial_to_fundamental',
    'first_equave'
]

def partial_to_fundamental(pitchclass: str, octave: int = 4, partial: int = 1, cent_offset: float = 0.0) -> Tuple[str, float]:
    '''
    Calculate the fundamental frequency given a pitch class and its partial number.
    
    Args:
        pitchclass: The pitch class with octave (e.g., "A4", "C#3", "Bb2")
        partial: The partial number (integer, non-zero). Negative values indicate undertones.
        cent_offset: The cents offset from the pitch class, default is 0.0
        
    Returns:
        A tuple containing the fundamental's pitch class with octave and cents offset
    '''
    if partial == 0:
        raise ValueError("Partial number cannot be zero")

    freq = pitchclass_to_freq(pitchclass, octave, cent_offset)
    # For negative partials (undertones), multiply by |p| instead of dividing
    fundamental_freq = freq * abs(partial) if partial < 0 else freq / partial
    return freq_to_pitchclass(fundamental_freq)

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
