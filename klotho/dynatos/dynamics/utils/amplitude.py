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
    '''
    Convert amplitude to decibels (dB).

    Args:
    amp (float): The amplitude to convert.

    Returns:
    float: The amplitude in decibels.
    '''
    return 20 * np.log10(amp)

def dbamp(db: float) -> float:
    '''
    Convert decibels (dB) to amplitude.

    Args:
    db (float): The decibels to convert.

    Returns:
    float: The amplitude.
    '''
    return 10 ** (db / 20) 