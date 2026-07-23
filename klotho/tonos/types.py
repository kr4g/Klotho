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
    """A frequency in hertz (symbol ``Hz``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'frequency', 'Hz')

    @property
    def midicent(self):
        """Midicent : This frequency converted to midicents."""
        return Midicent(freq_to_midicents(self.magnitude))

    @property
    def midi(self):
        """Midi : This frequency converted to a MIDI note number."""
        return Midi(self.midicent.magnitude / 100)


class Midi(Unit):
    """A MIDI note number (may be fractional for microtones)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'midi', 'MIDI')

    @property
    def frequency(self):
        """Frequency : This MIDI note number converted to hertz."""
        return Frequency(midicents_to_freq(self.magnitude * 100))

    @property
    def midicent(self):
        """Midicent : This MIDI note number converted to midicents."""
        return Midicent(self.magnitude * 100)


class Midicent(Unit):
    """A pitch in midicents — MIDI note number × 100 (symbol ``m¢``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'midicent', 'm¢')

    @property
    def midi(self):
        """Midi : These midicents converted to a MIDI note number."""
        return Midi(self.magnitude / 100)

    @property
    def frequency(self):
        """Frequency : These midicents converted to hertz."""
        return Frequency(midicents_to_freq(self.magnitude))


class Cent(Unit):
    """An interval in cents — 1/100 of an equal-tempered semitone (symbol ``¢``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'cent', '¢')

    @property
    def frequency_ratio(self):
        """float : The frequency ratio these cents represent (``2 ** (cents/1200)``)."""
        return 2.0 ** (self.magnitude / 1200.0)


class Ratio(Unit):
    """A frequency ratio as an exact fraction (e.g. ``3/2``)."""

    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'ratio', '')

    @property
    def numerator(self):
        """int : Numerator of the scalar ratio (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().numerator
        except ValueError:
            raise AttributeError("numerator only for scalar")

    @property
    def denominator(self):
        """int : Denominator of the scalar ratio (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().denominator
        except ValueError:
            raise AttributeError("denominator only for scalar")


class Partial(Unit):
    """A partial number — Fraction for harmonic partials, float for inharmonic ones."""

    def __init__(self, magnitude):
        magnitude = _to_partial_array(magnitude)
        super().__init__(magnitude, 'partial', '')


def frequency(value):
    """Wrap a value as :class:`Frequency` (Hz)."""
    return Frequency(value)


def midi(value):
    """Wrap a value as :class:`Midi` (MIDI note number)."""
    return Midi(value)


def midicent(value):
    """Wrap a value as :class:`Midicent` (MIDI × 100)."""
    return Midicent(value)


def cent(value):
    """Wrap a value as :class:`Cent` (1/100 semitone)."""
    return Cent(value)


def ratio(value):
    """Wrap a value as :class:`Ratio` (exact frequency ratio)."""
    return Ratio(value)


def partial(value):
    """Wrap a value as :class:`Partial` (harmonic or inharmonic partial number)."""
    return Partial(value)


numbers.Real.register(Frequency)
numbers.Real.register(Midi)
numbers.Real.register(Midicent)
numbers.Real.register(Cent)
numbers.Rational.register(Ratio)
