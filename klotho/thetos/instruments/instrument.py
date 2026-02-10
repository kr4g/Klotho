from klotho.dynatos.dynamics import Dynamic, DynamicRange
from klotho.tonos.pitch import Pitch
from klotho.utils.data_structures.dictionaries import SafeDict
from typing import List, Dict, TypeVar, Union

class Instrument():
    
    def __init__(self,
                 name          = 'default',
                 pfields       = None
        ):
        """
        Initialize an Instrument.
        
        Args:
            name (str): The name of the instrument
            pfields (dict or SafeDict): Parameter fields with default values
        """
        self._name = name
        
        if pfields is None:
            pfields = {}
        self._pfields = pfields if isinstance(pfields, SafeDict) else SafeDict(pfields)
    
    @property
    def name(self):
        return self._name
    
    @property
    def pfields(self):
        return self._pfields.copy()
    
    def keys(self):
        keys = ['synth_name']
        keys.extend(self._pfields.keys())
        return keys
    
    def __getitem__(self, key):
        if key == 'synth_name':
            return self._name
        return self._pfields[key]
    
    def __str__(self):
        return f"Instrument(name='{self._name}', pfields={dict(self._pfields)})"
    
    def __repr__(self):
        return self.__str__()


class SynthDefInstrument(Instrument):
    
    def __init__(self,
                 name          = 'default',
                 freq_range    = None,
                 dynamic_range = None,
                 env_type      = 'Sustained',
                 pfields       = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
        ):
        """
        Initialize a SynthDefInstrument.
        
        Args:
            name (str): The name of the instrument
            freq_range (tuple): A tuple of (min, max) frequency values or Pitch instances
            dynamic_range: A DynamicRange instance or a tuple of (min, max) dB values
            env_type (str): The envelope type for the instrument
            pfields (dict or SafeDict): Parameter fields with default values
        """
        if pfields is None:
            pfields = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
        
        super().__init__(name=name, pfields=pfields)
        
        if freq_range is None:
            self._freq_range = (Pitch.from_freq(27.5), Pitch.from_freq(4186.01))
        else:
            self._freq_range = self._process_freq_range(freq_range)
        
        if dynamic_range is None:
            self._dynamic_range = DynamicRange(min_dynamic=-60, max_dynamic=-3, curve=1.25)
        else:
            self._dynamic_range = self._process_dynamic_range(dynamic_range)
        
        self._env_type = env_type
    
    def _process_freq_range(self, freq_range):
        min_freq, max_freq = freq_range
        
        if not isinstance(min_freq, Pitch):
            min_freq = Pitch.from_freq(float(min_freq))
        
        if not isinstance(max_freq, Pitch):
            max_freq = Pitch.from_freq(float(max_freq))
            
        return (min_freq, max_freq)
    
    def _process_dynamic_range(self, dynamic_range):
        if isinstance(dynamic_range, DynamicRange):
            return dynamic_range
        
        min_dyn, max_dyn = dynamic_range
        
        if isinstance(min_dyn, Dynamic):
            min_dyn = min_dyn.db
            
        if isinstance(max_dyn, Dynamic):
            max_dyn = max_dyn.db
            
        return DynamicRange(min_dynamic=min_dyn, max_dynamic=max_dyn)
    
    @property
    def freq_range(self):
        return self._freq_range
    
    @property
    def dynamic_range(self):
        return self._dynamic_range
    
    @property
    def env_type(self):
        return self._env_type
    
    def __str__(self):
        return f"SynthDefInstrument(name='{self._name}', pfields={dict(self._pfields)})"


class MidiInstrument(Instrument):
    
    def __init__(self,
                 name          = 'default',
                 prgm          = 0,
                 is_Drum       = False,
                 pfields       = None
        ):
        """
        Initialize a MidiInstrument.
        
        Args:
            name (str): The name of the instrument
            prgm (int): General MIDI program number (ignored if is_Drum is True)
            is_Drum (bool): Whether this instrument uses the general MIDI percussion channel
            pfields (dict or SafeDict): Parameter fields with default values
        """
        if pfields is None:
            pfields = {'note': 60 if not is_Drum else 35, 'velocity': 100}
        
        super().__init__(name=name, pfields=pfields)
        
        self._prgm = prgm
        self._is_Drum = is_Drum
    
    @property
    def prgm(self):
        return self._prgm
    
    @property
    def is_Drum(self):
        return self._is_Drum
    
    def __str__(self):
        return f"MidiInstrument(name='{self._name}', prgm={self._prgm}, is_Drum={self._is_Drum}, pfields={dict(self._pfields)})"
