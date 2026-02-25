from .frequency_conversion import pitchclass_to_freq, freq_to_pitchclass
from fractions import Fraction
from typing import Tuple, Union

__all__ = [
    'partial_to_fundamental',
    'first_equave'
]

def partial_to_fundamental(pitchclass: str, octave: int = 4, partial: int = 1, cent_offset: float = 0.0) -> Tuple[str, float]:
    """
    Calculate the fundamental from a pitch and its partial number.

    Given a pitch that represents a specific partial of an unknown
    fundamental, this function back-calculates the fundamental frequency
    and returns its pitch-class information.

    Parameters
    ----------
    pitchclass : str
        Pitch class name (e.g., ``"A"``, ``"C#"``).
    octave : int, optional
        Octave number. Default is 4.
    partial : int, optional
        Partial number (non-zero). Negative values indicate undertones.
        Default is 1.
    cent_offset : float, optional
        Microtonal offset in cents. Default is 0.0.

    Returns
    -------
    namedtuple
        A named tuple with fields ``pitchclass``, ``octave``, and
        ``cents_offset`` for the fundamental.

    Raises
    ------
    ValueError
        If *partial* is zero.
    """
    if partial == 0:
        raise ValueError("Partial number cannot be zero")

    freq = pitchclass_to_freq(pitchclass, octave, cent_offset)
    # For negative partials (undertones), multiply by |p| instead of dividing
    fundamental_freq = freq * abs(partial) if partial < 0 else freq / partial
    return freq_to_pitchclass(fundamental_freq)

def first_equave(harmonic: Union[int, float, Fraction], equave: Union[int, float, Fraction, str] = 2, max_equave: Union[int, float, Fraction, str] = None):
  """
  Return the first equave register in which a harmonic number appears.

  For example, harmonics 2 and 3 first appear in equave 1 (range 2--4),
  harmonic 5 first appears in equave 2 (range 4--8), etc.

  Parameters
  ----------
  harmonic : int, float, or Fraction
      The harmonic number.
  equave : int, float, Fraction, or str, optional
      Interval of equivalence. Default is 2 (octave).
  max_equave : int, float, Fraction, str, or None, optional
      Maximum equave register to search. None means unbounded.

  Returns
  -------
  int or None
      The equave register number, or None if not found within
      *max_equave*.
  """
  equave = Fraction(equave)
  max_equave = Fraction(max_equave) if max_equave is not None else None
  n_equave = 0
  while max_equave is None or n_equave <= max_equave:
    if harmonic <= equave ** n_equave:
      return n_equave
    n_equave += 1
  return None
