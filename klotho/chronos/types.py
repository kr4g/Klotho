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
    """A duration or time point in seconds (symbol ``s``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'seconds', 's')


class RealOnset(Unit):
    """A real-time onset in seconds (symbol ``s``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_onset', 's')


class RealDuration(Unit):
    """A real-time duration in seconds (symbol ``s``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'real_duration', 's')


class MetricOnset(Unit):
    """A metric onset as a fraction of a whole note (symbol ``note``)."""

    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'metric_onset', 'note')

    @property
    def numerator(self):
        """int : Numerator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().numerator
        except ValueError:
            raise AttributeError("numerator only for scalar")

    @property
    def denominator(self):
        """int : Denominator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().denominator
        except ValueError:
            raise AttributeError("denominator only for scalar")


class MetricDuration(Unit):
    """A metric duration as a fraction of a whole note (symbol ``note``)."""

    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'metric_duration', 'note')

    @property
    def numerator(self):
        """int : Numerator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().numerator
        except ValueError:
            raise AttributeError("numerator only for scalar")

    @property
    def denominator(self):
        """int : Denominator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().denominator
        except ValueError:
            raise AttributeError("denominator only for scalar")


class Beat(Unit):
    """A beat value as a fraction of a whole note (e.g. ``1/4`` for a quarter note)."""

    def __init__(self, magnitude):
        magnitude = _to_fraction_array(magnitude)
        super().__init__(magnitude, 'beat', 'beat')

    @property
    def numerator(self):
        """int : Numerator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().numerator
        except ValueError:
            raise AttributeError("numerator only for scalar")

    @property
    def denominator(self):
        """int : Denominator of the scalar fraction (raises AttributeError for arrays)."""
        try:
            return self.magnitude.item().denominator
        except ValueError:
            raise AttributeError("denominator only for scalar")


class Bpm(Unit):
    """A tempo magnitude in beats per minute (symbol ``bpm``)."""

    def __init__(self, magnitude):
        super().__init__(magnitude, 'bpm', 'bpm')


class Tempo:
    """
    A tempo marking: a beat value paired with a beats-per-minute rate.

    Parameters
    ----------
    beat_val : Beat, Fraction, str, or float
        The beat receiving the pulse (e.g. ``'1/4'``).
    bpm_val : Bpm, int, or float
        Pulses per minute for that beat.
    """

    def __init__(self, beat_val, bpm_val):
        self.beat = Beat(beat_val) if not isinstance(beat_val, Beat) else beat_val
        self.bpm = Bpm(bpm_val) if not isinstance(bpm_val, Bpm) else bpm_val

    def __repr__(self):
        return f"tempo({self.beat} = {self.bpm})"


def seconds(value):
    """Wrap a value as :class:`Seconds`."""
    return Seconds(value)


def real_onset(value):
    """Wrap a value as :class:`RealOnset` (seconds)."""
    return RealOnset(value)


def real_duration(value):
    """Wrap a value as :class:`RealDuration` (seconds)."""
    return RealDuration(value)


def metric_onset(value):
    """Wrap a value as :class:`MetricOnset` (fraction of a whole note)."""
    return MetricOnset(value)


def metric_duration(value):
    """Wrap a value as :class:`MetricDuration` (fraction of a whole note)."""
    return MetricDuration(value)


def beat(value):
    """Wrap a value as :class:`Beat` (fraction of a whole note)."""
    return Beat(value)


def bpm(value):
    """Wrap a value as :class:`Bpm` (beats per minute)."""
    return Bpm(value)


def tempo(beat_val, bpm_val):
    """Build a :class:`Tempo` from a beat value and a BPM rate."""
    return Tempo(beat_val, bpm_val)


numbers.Real.register(Seconds)
numbers.Real.register(RealOnset)
numbers.Real.register(RealDuration)
numbers.Real.register(Bpm)
numbers.Rational.register(MetricOnset)
numbers.Rational.register(MetricDuration)
numbers.Rational.register(Beat)
