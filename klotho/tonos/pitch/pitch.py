from ..utils.frequency_conversion import pitchclass_to_freq, freq_to_pitchclass, freq_to_midicents, midicents_to_freq, A4_Hz, A4_MIDI
from ..utils.harmonics import partial_to_fundamental

import pandas as pd
import numpy as np

class Pitch:
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