"""
Typed unit wrappers for pitch and frequency quantities.
"""

import numbers
import numpy as np
from fractions import Fraction

from ..topos.types import Unit, _to_fraction_array
from .utils.frequency_conversion import freq_to_midicents, midicents_to_freq

__all__ = ['frequency', 'midi', 'midicent', 'cent', 'ratio', 'partial']


def _to_partial_array(value):
    """
    Convert to partial(s): int, Fraction, str -> Fraction; float -> float (inharmonic).
    Preserves shape. Returns ndarray with dtype=object.
    """
    def _convert(x):
        if isinstance(x, (float, np.floating)):
            return float(x)
        return Fraction(x)

    def _map_flat(seq, f):
        if isinstance(seq, (list, tuple)):
            return [_map_flat(x, f) if isinstance(x, (list, tuple)) else f(x) for x in seq]
        return f(seq)

    if isinstance(value, (list, tuple)):
        mapped = _map_flat(value, _convert)
        return np.array(mapped, dtype=object)
    if isinstance(value, np.ndarray):
        out = np.array([_convert(x) for x in value.flat], dtype=object)
        return out.reshape(value.shape)
    return np.array(_convert(value), dtype=object)


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


class Ratio(Unit):
    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'ratio', '')

    @property
    def numerator(self):
        try:
            return self.magnitude.item().numerator
        except ValueError:
            raise AttributeError("numerator only for scalar")

    @property
    def denominator(self):
        try:
            return self.magnitude.item().denominator
        except ValueError:
            raise AttributeError("denominator only for scalar")


class Partial(Unit):
    def __init__(self, magnitude):
        magnitude = _to_partial_array(magnitude)
        super().__init__(magnitude, 'partial', '')


def frequency(value):
    return Frequency(value)


def midi(value):
    return Midi(value)


def midicent(value):
    return Midicent(value)


def cent(value):
    return Cent(value)


def ratio(value):
    return Ratio(value)


def partial(value):
    return Partial(value)


numbers.Real.register(Frequency)
numbers.Real.register(Midi)
numbers.Real.register(Midicent)
numbers.Real.register(Cent)
numbers.Rational.register(Ratio)
