from ..utils.frequency_conversion import pitchclass_to_freq, freq_to_pitchclass, freq_to_midicents, midicents_to_freq, A4_Hz, A4_MIDI
from ..utils.harmonics import partial_to_fundamental

import pandas as pd
import numpy as np

class Pitch:
    """
    A musical pitch with frequency, pitch class, octave, and partial information.
    
    Pitch represents a specific musical frequency with associated metadata including
    pitch class name, octave number, cents offset from equal temperament, and 
    partial number for harmonic series calculations.
    
    Args:
        pitch_input: Pitch class name (e.g., "C", "F#") or pitch with octave (e.g., "C4", "Bb-1")
        octave: Octave number (default 4 for middle octave)
        cents_offset: Deviation from equal temperament in cents (default 0.0)
        partial: Partial number for harmonic series (default 1 for fundamental)
        
    Examples:
        >>> p = Pitch("C4")
        >>> p.freq
        261.6255653005986
        
        >>> p = Pitch("A", 4, 0.0)  # A4 = 440 Hz
        >>> p.freq
        440.0
        
        >>> p = Pitch("C", 4, 14.0)  # C4 + 14 cents
        >>> p.cents_offset
        14.0
        
        >>> p = Pitch.from_freq(880.0)  # Create from frequency
        >>> str(p)
        'A5'
    """
    
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
            
            self._data = pd.DataFrame([{
                'pitchclass': pitchclass,
                'octave': octave,
                'cents_offset': cents_offset,
                'partial': partial,
                'freq': pitchclass_to_freq(pitchclass, octave, cents_offset)
            }]).set_index(pd.Index(['']))
        else:
            self._data = pd.DataFrame([{
                'pitchclass': pitch_input or 'A',
                'octave': octave,
                'cents_offset': cents_offset,
                'partial': partial,
                'freq': pitchclass_to_freq(pitch_input or 'A', octave, cents_offset)
            }]).set_index(pd.Index(['']))
    
    @classmethod
    def from_freq(cls, freq: float, partial: int = 1):
        return cls(*freq_to_pitchclass(freq), partial=partial)
    
    @classmethod
    def from_midi(cls, midi_note: float, partial: int = 1):
        midicents = midi_note * 100
        return cls.from_midicent(midicents, partial)
    
    @classmethod
    def from_midicent(cls, midicent_value: float, partial: int = 1):
        freq = midicents_to_freq(midicent_value)
        return cls.from_freq(freq, partial)
    
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
    def midicent(self):
        return freq_to_midicents(self.freq)
    
    @property
    def midi(self):
        return self.midicent / 100
    
    @property
    def virtual_fundamental(self):
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
        if not isinstance(other, Pitch):
            return False
        return self.pitchclass == other.pitchclass and self.octave == other.octave
    
    def is_same_pitchclass(self, other):
        if not isinstance(other, Pitch):
            return False
        return self.pitchclass == other.pitchclass
    
    def cents_difference(self, other):
        if not isinstance(other, Pitch):
            raise TypeError("Can only calculate cents difference with another Pitch")
        return 1200 * np.log2(self.freq / other.freq)
        
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