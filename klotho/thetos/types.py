import numpy as np
from fractions import Fraction

from ..tonos.utils.frequency_conversion import freq_to_midicents, midicents_to_freq
from ..dynatos.dynamics import ampdb, dbamp

__all__ = [
    'frequency', 'midi', 'midicent', 'cent', 'amplitude', 'decibel', 'real_onset', 'real_duration', 'metric_onset', 'metric_duration'
]

class Unit:
    def __init__(self, magnitude, unit_type, unit_symbol=""):
        self.magnitude = np.asarray(magnitude)
        self.unit_type = unit_type
        self.unit_symbol = unit_symbol
    
    def __array__(self):
        return self.magnitude
    
    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        magnitudes = []
        for input_ in inputs:
            if hasattr(input_, 'magnitude'):
                magnitudes.append(input_.magnitude)
            else:
                magnitudes.append(input_)
        
        result_magnitude = ufunc(*magnitudes, **kwargs)
        return type(self)(result_magnitude)
    
    def __float__(self):
        return float(self.magnitude)
    
    def __int__(self):
        return int(self.magnitude)
    
    def __repr__(self):
        return self.__str__()
    
    def __str__(self):
        return f"{self.magnitude} {self.unit_symbol}"
    
    def __getitem__(self, key):
        return type(self)(self.magnitude[key])

class Frequency(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'frequency', 'Hz')
    
    @property
    def midicent(self):
        return Midicent(freq_to_midicents(self.magnitude))
    
    @property
    def midi(self):
        return Midi(self.midicent.magnitude / 100)

class Midi(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'midi', 'MIDI')
    
    @property
    def frequency(self):
        return Frequency(midicents_to_freq(self.magnitude * 100))
    
    @property
    def midicent(self):
        return Midicent(self.magnitude * 100)

class Midicent(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'midicent', 'm¢')
    
    @property
    def midi(self):
        return Midi(self.magnitude / 100)
    
    @property
    def frequency(self):
        return Frequency(midicents_to_freq(self.magnitude))

class Cent(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'cent', '¢')
    
    @property
    def frequency_ratio(self):
        return 2.0 ** (self.magnitude / 1200.0)

class Amplitude(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'amplitude', 'lin')
    
    @property
    def decibel(self):
        return Decibel(ampdb(self.magnitude))

class Decibel(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'decibel', 'dB')
    
    @property
    def amplitude(self):
        return Amplitude(dbamp(self.magnitude))

class RealOnset(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_onset', 's')

class RealDuration(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_duration', 's')

class MetricOnset(Unit):
    def __init__(self, magnitude):
        if isinstance(magnitude, (list, tuple, np.ndarray)):
            magnitude = [Fraction(x) for x in np.asarray(magnitude).flat]
            magnitude = np.array(magnitude).reshape(np.asarray(magnitude).shape)
        else:
            magnitude = Fraction(magnitude)
        super().__init__(magnitude, 'metric_onset', 'beats')

class MetricDuration(Unit):
    def __init__(self, magnitude):
        if isinstance(magnitude, (list, tuple, np.ndarray)):
            magnitude = [Fraction(x) for x in np.asarray(magnitude).flat]
            magnitude = np.array(magnitude).reshape(np.asarray(magnitude).shape)
        else:
            magnitude = Fraction(magnitude)
        super().__init__(magnitude, 'metric_duration', 'beats')

def frequency(value):
    return Frequency(value)

def midi(value):
    return Midi(value)

def midicent(value):
    return Midicent(value)

def cent(value):
    return Cent(value)

def amplitude(value):
    return Amplitude(value)

def decibel(value):
    return Decibel(value)

def real_onset(value):
    return RealOnset(value)

def real_duration(value):
    return RealDuration(value)

def metric_onset(value):
    return MetricOnset(value)

def metric_duration(value):
    return MetricDuration(value)
