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
