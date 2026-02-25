"""
Typed unit wrappers for musical quantities.

This module provides lightweight wrapper classes for common musical units
(frequency, MIDI, midicent, amplitude, decibel, etc.) that carry unit metadata
and support NumPy array operations while preserving unit identity.
"""

import numpy as np
from fractions import Fraction

from ..tonos.utils.frequency_conversion import freq_to_midicents, midicents_to_freq
from ..dynatos.dynamics import ampdb, dbamp

__all__ = [
    'frequency', 'midi', 'midicent', 'cent', 'amplitude', 'decibel', 'real_onset', 'real_duration', 'metric_onset', 'metric_duration'
]

class Unit:
    """
    Base class for typed musical units with NumPy integration.
    
    Wraps a numeric magnitude with unit metadata, supporting transparent
    NumPy array operations via ``__array__`` and ``__array_ufunc__``.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        The numeric value(s) of the unit.
    unit_type : str
        Identifier for the unit type (e.g., 'frequency', 'amplitude').
    unit_symbol : str, optional
        Display symbol for the unit (default is ``""``).
    """
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
    """
    Unit wrapper for frequency values in Hertz.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Frequency value(s) in Hz.
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'frequency', 'Hz')
    
    @property
    def midicent(self):
        """Midicent : Frequency converted to midicents."""
        return Midicent(freq_to_midicents(self.magnitude))
    
    @property
    def midi(self):
        """Midi : Frequency converted to MIDI note number."""
        return Midi(self.midicent.magnitude / 100)

class Midi(Unit):
    """
    Unit wrapper for MIDI note numbers.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        MIDI note number(s) (e.g., 60 for middle C).
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'midi', 'MIDI')
    
    @property
    def frequency(self):
        """Frequency : MIDI note converted to frequency in Hz."""
        return Frequency(midicents_to_freq(self.magnitude * 100))
    
    @property
    def midicent(self):
        """Midicent : MIDI note converted to midicents."""
        return Midicent(self.magnitude * 100)

class Midicent(Unit):
    """
    Unit wrapper for midicent values (MIDI note number * 100).
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Midicent value(s) (e.g., 6000 for middle C).
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'midicent', 'm¢')
    
    @property
    def midi(self):
        """Midi : Midicent value converted to MIDI note number."""
        return Midi(self.magnitude / 100)
    
    @property
    def frequency(self):
        """Frequency : Midicent value converted to frequency in Hz."""
        return Frequency(midicents_to_freq(self.magnitude))

class Cent(Unit):
    """
    Unit wrapper for interval values in cents.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Interval value(s) in cents (1200 cents = one octave).
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'cent', '¢')
    
    @property
    def frequency_ratio(self):
        """float or numpy.ndarray : The frequency ratio equivalent of the cent value."""
        return 2.0 ** (self.magnitude / 1200.0)

class Amplitude(Unit):
    """
    Unit wrapper for linear amplitude (gain) values.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Linear amplitude value(s).
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'amplitude', 'gain')
    
    @property
    def decibel(self):
        """Decibel : Amplitude converted to decibels."""
        return Decibel(ampdb(self.magnitude))

class Decibel(Unit):
    """
    Unit wrapper for decibel values.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Decibel value(s).
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'decibel', 'dB')
    
    @property
    def amplitude(self):
        """Amplitude : Decibel value converted to linear amplitude."""
        return Amplitude(dbamp(self.magnitude))

class RealOnset(Unit):
    """
    Unit wrapper for real-time onset positions in seconds.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Onset time(s) in seconds.
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_onset', 's')

class RealDuration(Unit):
    """
    Unit wrapper for real-time durations in seconds.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Duration(s) in seconds.
    """
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_duration', 's')

class MetricOnset(Unit):
    """
    Unit wrapper for metric onset positions as fractions of a whole note.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Metric onset position(s), stored as ``Fraction`` values.
    """
    def __init__(self, magnitude):
        if isinstance(magnitude, (list, tuple, np.ndarray)):
            magnitude = [Fraction(x) for x in np.asarray(magnitude).flat]
            magnitude = np.array(magnitude).reshape(np.asarray(magnitude).shape)
        else:
            magnitude = Fraction(magnitude)
        super().__init__(magnitude, 'metric_onset', 'note')

class MetricDuration(Unit):
    """
    Unit wrapper for metric durations as fractions of a whole note.
    
    Parameters
    ----------
    magnitude : scalar or array-like
        Metric duration(s), stored as ``Fraction`` values.
    """
    def __init__(self, magnitude):
        if isinstance(magnitude, (list, tuple, np.ndarray)):
            magnitude = [Fraction(x) for x in np.asarray(magnitude).flat]
            magnitude = np.array(magnitude).reshape(np.asarray(magnitude).shape)
        else:
            magnitude = Fraction(magnitude)
        super().__init__(magnitude, 'metric_duration', 'note')

def frequency(value):
    """
    Create a Frequency unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Frequency value(s) in Hz.
        
    Returns
    -------
    Frequency
        Wrapped frequency value.
    """
    return Frequency(value)

def midi(value):
    """
    Create a Midi unit.
    
    Parameters
    ----------
    value : scalar or array-like
        MIDI note number(s).
        
    Returns
    -------
    Midi
        Wrapped MIDI value.
    """
    return Midi(value)

def midicent(value):
    """
    Create a Midicent unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Midicent value(s).
        
    Returns
    -------
    Midicent
        Wrapped midicent value.
    """
    return Midicent(value)

def cent(value):
    """
    Create a Cent unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Cent value(s).
        
    Returns
    -------
    Cent
        Wrapped cent value.
    """
    return Cent(value)

def amplitude(value):
    """
    Create an Amplitude unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Linear amplitude value(s).
        
    Returns
    -------
    Amplitude
        Wrapped amplitude value.
    """
    return Amplitude(value)

def decibel(value):
    """
    Create a Decibel unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Decibel value(s).
        
    Returns
    -------
    Decibel
        Wrapped decibel value.
    """
    return Decibel(value)

def real_onset(value):
    """
    Create a RealOnset unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Onset time(s) in seconds.
        
    Returns
    -------
    RealOnset
        Wrapped onset value.
    """
    return RealOnset(value)

def real_duration(value):
    """
    Create a RealDuration unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Duration(s) in seconds.
        
    Returns
    -------
    RealDuration
        Wrapped duration value.
    """
    return RealDuration(value)

def metric_onset(value):
    """
    Create a MetricOnset unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Metric onset position(s).
        
    Returns
    -------
    MetricOnset
        Wrapped metric onset value.
    """
    return MetricOnset(value)

def metric_duration(value):
    """
    Create a MetricDuration unit.
    
    Parameters
    ----------
    value : scalar or array-like
        Metric duration(s).
        
    Returns
    -------
    MetricDuration
        Wrapped metric duration value.
    """
    return MetricDuration(value)
