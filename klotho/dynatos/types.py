"""
Typed unit wrappers for amplitude and dynamics quantities.
"""

import numbers
import numpy as np

from ..topos.types import Unit
from .dynamics import ampdb, dbamp

__all__ = ['amplitude', 'decibel', 'velocity']


class Amplitude(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'amplitude', 'gain')

    @property
    def decibel(self):
        return Decibel(ampdb(self.magnitude))


class Decibel(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'decibel', 'dB')

    @property
    def amplitude(self):
        return Amplitude(dbamp(self.magnitude))


class Velocity(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'velocity', '')


def amplitude(value):
    return Amplitude(value)


def decibel(value):
    return Decibel(value)


def velocity(value):
    return Velocity(value)


numbers.Real.register(Amplitude)
numbers.Real.register(Decibel)
numbers.Real.register(Velocity)
