from ..utils.frequency_conversion import pitchclass_to_freq, freq_to_pitchclass, freq_to_midicents, midicents_to_freq, A4_Hz, A4_MIDI
from ..utils.harmonics import partial_to_fundamental
from fractions import Fraction
from typing import Union

import numpy as np

class Pitch:
    """
    A musical pitch with frequency, pitch class, octave, and partial information.

    Pitch represents a specific musical frequency with associated metadata including
    pitch class name, octave number, cents offset from equal temperament, and
    partial number for harmonic series calculations.

    Parameters
    ----------
    pitch_input : str or None, optional
        Pitch class name (e.g., ``"C"``, ``"F#"``) or pitch with octave
        (e.g., ``"C4"``, ``"Bb-1"``).
    octave : int, optional
        Octave number. Default is 4 (middle octave).
    cents_offset : float, optional
        Deviation from equal temperament in cents. Default is 0.0.
    partial : int, float, or Fraction, optional
        Partial number or frequency ratio. Default is 1 (fundamental).

    Examples
    --------
    >>> p = Pitch("C4")
    >>> p.freq
    261.6255653005986

    >>> p = Pitch("A", 4, 0.0)
    >>> p.freq
    440.0

    >>> p = Pitch("C", 4, 14.0)
    >>> p.cents_offset
    14.0

    >>> p = Pitch.from_freq(880.0)
    >>> str(p)
    'A5'
    """
    
    __slots__ = ('_pitchclass', '_octave', '_cents_offset', '_partial', '_freq')
    
    def __init__(self, pitch_input=None, octave=4, cents_offset=0.0, partial=1):
        if isinstance(pitch_input, str) and len(pitch_input) >= 1:
            pitchclass = ""
            octave_from_str = None
            
            for i, char in enumerate(pitch_input):
                if char.isdigit() or (char == '-' and i > 0):
                    octave_from_str = int(pitch_input[i:])
                    pitchclass = pitch_input[:i]
                    break
            
            if octave_from_str is None:
                pitchclass = pitch_input
            else:
                octave = octave_from_str
            
            self._pitchclass = pitchclass
            self._octave = octave
            self._cents_offset = cents_offset
            self._partial = partial
            self._freq = pitchclass_to_freq(pitchclass, octave, cents_offset)
        else:
            self._pitchclass = pitch_input or 'A'
            self._octave = octave
            self._cents_offset = cents_offset
            self._partial = partial
            self._freq = pitchclass_to_freq(pitch_input or 'A', octave, cents_offset)
    
    @classmethod
    def from_freq(cls, freq: float, partial: Union[int, float, Fraction] = 1):
        """
        Create a Pitch from a frequency in Hertz.

        Parameters
        ----------
        freq : float
            Frequency in Hertz.
        partial : int, float, or Fraction, optional
            Partial number or frequency ratio. Default is 1.

        Returns
        -------
        Pitch
            A new Pitch instance corresponding to the given frequency.
        """
        return cls(*freq_to_pitchclass(freq), partial=partial)
    
    @classmethod
    def from_midi(cls, midi_note: float, partial: Union[int, float, Fraction] = 1):
        """
        Create a Pitch from a MIDI note number.

        Parameters
        ----------
        midi_note : float
            MIDI note number (e.g., 60 for middle C, 69 for A4).
        partial : int, float, or Fraction, optional
            Partial number or frequency ratio. Default is 1.

        Returns
        -------
        Pitch
            A new Pitch instance corresponding to the MIDI note.
        """
        midicents = midi_note * 100
        return cls.from_midicent(midicents, partial)
    
    @classmethod
    def from_midicent(cls, midicent_value: float, partial: Union[int, float, Fraction] = 1):
        """
        Create a Pitch from a MIDI cent value.

        Parameters
        ----------
        midicent_value : float
            MIDI cent value (e.g., 6900 for A4).
        partial : int, float, or Fraction, optional
            Partial number or frequency ratio. Default is 1.

        Returns
        -------
        Pitch
            A new Pitch instance corresponding to the MIDI cent value.
        """
        freq = midicents_to_freq(midicent_value)
        return cls.from_freq(freq, partial)
    
    @property
    def pitchclass(self):
        """str : The pitch class name (e.g., ``'C'``, ``'F#'``)."""
        return self._pitchclass
    
    @property
    def octave(self):
        """int : The octave number."""
        return self._octave
    
    @property
    def cents_offset(self):
        """float : Deviation from equal temperament in cents."""
        return self._cents_offset
    
    @property
    def partial(self):
        """int, float, or Fraction : The partial number or frequency ratio."""
        return self._partial
    
    @property
    def freq(self):
        """float : The frequency in Hertz."""
        return self._freq
    
    @property
    def midicent(self):
        """float : The MIDI cent representation of this pitch."""
        return freq_to_midicents(self.freq)
    
    @property
    def midi(self):
        """float : The MIDI note number, rounded when cents offset is negligible."""
        midi_value = float(self.midicent / 100)
        if abs(self.cents_offset) < 0.01:
            return float(round(midi_value))
        return midi_value
    
    @property
    def virtual_fundamental(self):
        """Pitch : The implied fundamental derived from this pitch's partial number."""
        return Pitch(*partial_to_fundamental(self.pitchclass, self.octave, self.partial, self.cents_offset))
    
    def __eq__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return abs(self.freq - other.freq) < 1e-6
    
    def __lt__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return self.freq < other.freq
    
    def __le__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return self.freq <= other.freq or abs(self.freq - other.freq) < 1e-6
    
    def __gt__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return self.freq > other.freq
    
    def __ge__(self, other):
        if not isinstance(other, Pitch):
            return NotImplemented
        return self.freq >= other.freq or abs(self.freq - other.freq) < 1e-6
    
    def __hash__(self):
        return hash((self.pitchclass, self.octave, round(self.cents_offset, 1), self.partial))
    
    def is_same_note(self, other):
        """
        Check whether two pitches share the same pitch class and octave.

        Parameters
        ----------
        other : Pitch
            The pitch to compare against.

        Returns
        -------
        bool
            True if both pitch class and octave match.
        """
        if not isinstance(other, Pitch):
            return False
        return self.pitchclass == other.pitchclass and self.octave == other.octave
    
    def is_same_pitchclass(self, other):
        """
        Check whether two pitches share the same pitch class regardless of octave.

        Parameters
        ----------
        other : Pitch
            The pitch to compare against.

        Returns
        -------
        bool
            True if pitch classes match.
        """
        if not isinstance(other, Pitch):
            return False
        return self.pitchclass == other.pitchclass
    
    def cents_difference(self, other):
        """
        Calculate the interval between this pitch and another in cents.

        Parameters
        ----------
        other : Pitch
            The pitch to measure the interval to.

        Returns
        -------
        float
            Signed interval in cents (positive if self is higher).

        Raises
        ------
        TypeError
            If *other* is not a Pitch instance.
        """
        if not isinstance(other, Pitch):
            raise TypeError("Can only calculate cents difference with another Pitch")
        return 1200 * np.log2(self.freq / other.freq)
    
    def with_partial(self, partial: Union[int, float, Fraction]) -> 'Pitch':
        """
        Return a copy of this pitch with a different partial number.

        Parameters
        ----------
        partial : int, float, or Fraction
            The new partial number to assign.

        Returns
        -------
        Pitch
            A new Pitch sharing all attributes except the partial.
        """
        new_pitch = Pitch.__new__(Pitch)
        new_pitch._pitchclass = self._pitchclass
        new_pitch._octave = self._octave
        new_pitch._cents_offset = self._cents_offset
        new_pitch._partial = partial
        new_pitch._freq = self._freq
        return new_pitch
        
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        pitch_name = f"{self.pitchclass}{self.octave}"
        
        if abs(self.cents_offset) > 0.01:
            cents_str = f" ({self.cents_offset:+.2f}¢)"
        else:
            cents_str = ""
            
        freq_str = f"{self.freq:.2f} Hz"
        
        return f"Pitch({pitch_name}{cents_str}, {freq_str})" 
