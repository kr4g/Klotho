"""
Typed unit wrappers for amplitude and dynamics quantities.
"""

import numbers
import numpy as np

from ..topos.types import Unit
from .dynamics import ampdb, dbamp

__all__ = ['amplitude', 'decibel', 'velocity']


class Amplitude(Unit):
    """A linear amplitude / gain factor (1.0 = unity, symbol ``gain``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'amplitude', 'gain')

    @property
    def decibel(self):
        """Decibel : This amplitude converted to decibels via ``ampdb``."""
        return Decibel(ampdb(self.magnitude))


class Decibel(Unit):
    """A level in decibels relative to unity gain (symbol ``dB``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'decibel', 'dB')

    @property
    def amplitude(self):
        """Amplitude : This level converted to linear amplitude via ``dbamp``."""
        return Amplitude(dbamp(self.magnitude))


class Velocity(Unit):
    """A MIDI velocity value (0–127)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'velocity', '')


def amplitude(value):
    """Wrap a value as :class:`Amplitude` (linear gain)."""
    return Amplitude(value)


def decibel(value):
    """Wrap a value as :class:`Decibel` (dB)."""
    return Decibel(value)


def velocity(value):
    """Wrap a value as :class:`Velocity` (MIDI velocity)."""
    return Velocity(value)


numbers.Real.register(Amplitude)
numbers.Real.register(Decibel)
numbers.Real.register(Velocity)
