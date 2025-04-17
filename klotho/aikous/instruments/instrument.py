from klotho.aikous.expression.dynamics import Dynamic, DynamicRange
from klotho.tonos.utils.pitch import Pitch
from utils.data_structures.dictionaries import SafeDict

class Instrument:
    
    def __init__(self, name, freq_range=None, dynamic_range=None, pfields=None):
        """
        Initialize an Instrument.
        
        Args:
            name (str): The name of the instrument
            freq_range (tuple): A tuple of (min, max) frequency values or Pitch instances
            dynamic_range: A DynamicRange instance or a tuple of (min, max) dB values
            pfields (dict or SafeDict): Parameter fields with default values
        """
        self._name = name
        
        if freq_range is None:
            freq_range = (20.0, 20000.0)
        self._freq_range = self._process_freq_range(freq_range)
        
        if dynamic_range is None:
            dynamic_range = (-60, 0)
        self._dynamic_range = self._process_dynamic_range(dynamic_range)
        
        if pfields is None:
            pfields = {}
        self._pfields = pfields if isinstance(pfields, SafeDict) else SafeDict(pfields)
    
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
    def name(self):
        return self._name
    
    @property
    def freq_range(self):
        return self._freq_range
    
    @property
    def dynamic_range(self):
        return self._dynamic_range
    
    @property
    def pfields(self):
        return self._pfields
    
    def __repr__(self):
        return f"Instrument(name='{self._name}', freq_range={self._freq_range}, dynamic_range={self._dynamic_range}, pfields={dict(self._pfields)})"
