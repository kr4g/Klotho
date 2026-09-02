"""
Amplitude and decibel conversion utilities.

This module provides functions for converting between linear amplitude
values and logarithmic decibel representations.

Domain contract
---------------
``ampdb`` is defined on ``[0, inf)``. ``ampdb(0)`` is ``-inf`` exactly:
silence has a real representation in dB, it round-trips (``dbamp(-inf)`` is
``0.0``), and it is the convention every audio system uses -- so it is
returned quietly, without the ``divide by zero`` RuntimeWarning that the bare
``log10`` used to raise for a case that is not an accident.

A NEGATIVE amplitude is refused. It describes a phase inversion, not a level,
and ``20 * log10`` of it is NaN. NaN is the one value that must never leave
either converter: it compares false to everything, survives every arithmetic
operation it touches, and so turns a mistake at the call site into a plausible
wrong number several layers away. Both converters therefore refuse NaN on the
way in as well.
"""

import numpy as np

__all__ = [
    'ampdb',
    'dbamp',
]


def _as_float_array(value, name):
    """Coerce to a float ndarray and refuse NaN, which must never propagate."""
    array = np.asarray(value, dtype=float)
    if bool(np.any(np.isnan(array))):
        raise ValueError(f"{name} must be a real number; got {value!r} (NaN)")
    return array


def _unwrap(array):
    """Return a plain float for scalar input, the array for array input."""
    return float(array) if array.ndim == 0 else array


def ampdb(amp: float) -> float:
    """
    Convert amplitude to decibels (dB).

    Parameters
    ----------
    amp : float or array-like
        The linear amplitude value(s) to convert. Must be non-negative.

    Returns
    -------
    float
        The amplitude expressed in decibels. ``ampdb(0)`` is ``-inf``.

    Raises
    ------
    ValueError
        If any amplitude is negative (a phase inversion is not a level) or
        NaN. Both used to return NaN, which then propagated silently through
        ``Dynamic.amp`` and ``Amplitude.decibel``.
    """
    array = _as_float_array(amp, 'amplitude')
    if bool(np.any(array < 0)):
        raise ValueError(
            f"amplitude must be non-negative; got {amp!r}. A negative gain is "
            f"a phase inversion rather than a level, and its logarithm is NaN"
        )
    # amp == 0 is a defined case (-inf), not a numerical accident, so the
    # divide-by-zero warning log10 raises for it is noise.
    with np.errstate(divide='ignore'):
        return _unwrap(20.0 * np.log10(array))


def dbamp(db: float) -> float:
    """
    Convert decibels (dB) to amplitude.

    Parameters
    ----------
    db : float or array-like
        The decibel value(s) to convert. ``-inf`` is accepted and maps to
        ``0.0``.

    Returns
    -------
    float
        The linear amplitude value.

    Raises
    ------
    ValueError
        If any value is NaN, which would otherwise reach ``Dynamic.amp`` and
        every amplitude computed from it.
    """
    array = _as_float_array(db, 'decibel level')
    return _unwrap(10.0 ** (array / 20.0))
