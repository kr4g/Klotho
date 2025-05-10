from .frequency_conversion import pitchclass_to_freq, freq_to_pitchclass
from .harmonics import partial_to_fundamental

import pandas as pd

class Pitch:
    def __init__(self, pitch_input=None, octave=4, cents_offset=0.0, partial=1):
        if isinstance(pitch_input, str) and len(pitch_input) >= 1:
            # Handle string input like "C4", "F#5", "Bb3"
            pitchclass = ""
            octave_from_str = None
            
            # Extract octave number if present
            for i, char in enumerate(pitch_input):
                if char.isdigit() or (char == '-' and i > 0):
                    octave_from_str = int(pitch_input[i:])
                    pitchclass = pitch_input[:i]
                    break
            
            # If no octave in string, use the provided octave parameter
            if octave_from_str is None:
                pitchclass = pitch_input
            else:
                octave = octave_from_str
            
            # Initialize with extracted values
            self._data = pd.DataFrame([{
                'pitchclass': pitchclass,
                'octave': octave,
                'cents_offset': cents_offset,
                'partial': partial,
                'freq': pitchclass_to_freq(pitchclass, octave, cents_offset)
            }]).set_index(pd.Index(['']))
        else:
            # Original initialization
            self._data = pd.DataFrame([{
                'pitchclass': pitch_input or 'A',  # Default to 'A' if None
                'octave': octave,
                'cents_offset': cents_offset,
                'partial': partial,
                'freq': pitchclass_to_freq(pitch_input or 'A', octave, cents_offset)
            }]).set_index(pd.Index(['']))
    
    @classmethod
    def from_freq(cls, freq: float, partial: int = 1):
        return cls(*freq_to_pitchclass(freq), partial=partial)
    
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
