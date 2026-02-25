from klotho.utils.data_structures.enums import DirectValueEnumMeta, Enum
from collections import namedtuple
import numpy as np
from enum import member

A4_Hz   = 440.0
A4_MIDI = 69

__all__ = [
    'PITCH_CLASSES',
    'freq_to_midicents',
    'midicents_to_freq',
    'midicents_to_pitchclass',
    'freq_to_pitchclass',
    'pitchclass_to_freq',
    'A4_Hz',
    'A4_MIDI'
]

class PITCH_CLASSES(Enum, metaclass=DirectValueEnumMeta):
  """Enumeration of pitch classes for 12-TET with both sharp and flat naming."""
  @member
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
  
    @member
    class names:
      as_sharps = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
      as_flats  = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def freq_to_midicents(frequency: float) -> float:
  """
  Convert a frequency in Hertz to MIDI cents notation.

  MIDI cents combine MIDI note numbers with cent offsets. A value of
  6900 corresponds to A4 (440 Hz). Each increment of 100 is one
  12-TET semitone; non-multiples of 100 indicate microtonal pitches.

  Parameters
  ----------
  frequency : float
      The frequency in Hertz.

  Returns
  -------
  float
      The MIDI cent value.

  Examples
  --------
  >>> freq_to_midicents(440.0)
  6900.0
  """
  return 100 * (12 * np.log2(frequency / A4_Hz) + A4_MIDI)

def midicents_to_freq(midicents: float) -> float:
  """
  Convert MIDI cents back to a frequency in Hertz.

  Parameters
  ----------
  midicents : float
      The MIDI cent value (e.g., 6900 for A4).

  Returns
  -------
  float
      The corresponding frequency in Hertz.

  Examples
  --------
  >>> midicents_to_freq(6900)
  440.0
  """
  return A4_Hz * (2 ** ((midicents - A4_MIDI * 100) / 1200.0))

def midicents_to_pitchclass(midicents: float) -> namedtuple:
  """
  Convert MIDI cents to a pitch class with octave and cents offset.

  Parameters
  ----------
  midicents : float
      The MIDI cent value.

  Returns
  -------
  namedtuple
      A named tuple with fields ``pitchclass``, ``octave``, and
      ``cents_offset``.
  """
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
  
def freq_to_pitchclass(freq: float, cent_round: int = 4) -> namedtuple:
    """
    Convert a frequency in Hertz to a pitch class with octave and cents offset.

    Parameters
    ----------
    freq : float
        The frequency in Hertz.
    cent_round : int, optional
        Decimal places for rounding the cents offset. Default is 4.

    Returns
    -------
    namedtuple
        A named tuple with fields ``pitchclass``, ``octave``, and
        ``cents_offset``.
    """
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
    """
    Convert a pitch class name to a frequency in Hertz.

    Parameters
    ----------
    pitchclass : str
        Pitch class name (e.g., ``"C"``, ``"F#"``, ``"Bb"``).
    octave : int, optional
        Octave number. Default is 4.
    cent_offset : float, optional
        Microtonal offset in cents. Default is 0.0.
    hz_round : int, optional
        Decimal places for rounding the result. Default is 4.
    A4_Hz : float, optional
        Reference frequency for A4. Default is 440.0.
    A4_MIDI : int, optional
        MIDI note number for A4. Default is 69.

    Returns
    -------
    float
        The frequency in Hertz.
    """
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
