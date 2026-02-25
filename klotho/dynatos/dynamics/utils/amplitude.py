"""
Amplitude and decibel conversion utilities.

This module provides functions for converting between linear amplitude
values and logarithmic decibel representations.
"""

import numpy as np

__all__ = [
    'ampdb',
    'dbamp',
]

def ampdb(amp: float) -> float:
    """
    Convert amplitude to decibels (dB).

    Parameters
    ----------
    amp : float
        The linear amplitude value to convert.

    Returns
    -------
    float
        The amplitude expressed in decibels.
    """
    return 20 * np.log10(amp)

def dbamp(db: float) -> float:
    """
    Convert decibels (dB) to amplitude.

    Parameters
    ----------
    db : float
        The decibel value to convert.

    Returns
    -------
    float
        The linear amplitude value.
    """
    return 10 ** (db / 20) 