"""
Typed unit wrappers for temporal quantities.
"""

import numbers
import numpy as np

from ..topos.types import Unit, _to_fraction_array

__all__ = [
    'seconds', 'real_onset', 'real_duration',
    'metric_onset', 'metric_duration', 'beat', 'bpm', 'tempo',
]


class Seconds(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'seconds', 's')


class RealOnset(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_onset', 's')


class RealDuration(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_duration', 's')


class MetricOnset(Unit):
    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'metric_onset', 'note')

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


class MetricDuration(Unit):
    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'metric_duration', 'note')

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


class Beat(Unit):
    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'beat', 'beat')

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


class Bpm(Unit):
    def __init__(self, magnitude):
        super().__init__(magnitude, 'bpm', 'bpm')


class Tempo:
    def __init__(self, beat_val, bpm_val):
        self.beat = Beat(beat_val) if not isinstance(beat_val, Beat) else beat_val
        self.bpm = Bpm(bpm_val) if not isinstance(bpm_val, Bpm) else bpm_val

    def __repr__(self):
        return f"tempo({self.beat} = {self.bpm})"


def seconds(value):
    return Seconds(value)


def real_onset(value):
    return RealOnset(value)


def real_duration(value):
    return RealDuration(value)


def metric_onset(value):
    return MetricOnset(value)


def metric_duration(value):
    return MetricDuration(value)


def beat(value):
    return Beat(value)


def bpm(value):
    return Bpm(value)


def tempo(beat_val, bpm_val):
    return Tempo(beat_val, bpm_val)


numbers.Real.register(Seconds)
numbers.Real.register(RealOnset)
numbers.Real.register(RealDuration)
numbers.Real.register(Bpm)
numbers.Rational.register(MetricOnset)
numbers.Rational.register(MetricDuration)
numbers.Rational.register(Beat)
