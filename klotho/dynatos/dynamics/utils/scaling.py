"""
Psychoacoustic frequency-amplitude scaling utilities.

This module provides functions for scaling amplitude based on frequency
and loudness according to psychoacoustic principles, accounting for
human perception of sound at different frequencies and levels.
"""

import numpy as np
from scipy import interpolate
from .amplitude import dbamp

__all__ = [
    'freq_amp_scale',
]

def freq_amp_scale(freq: float, db_level: float, min_db: float = -60) -> float:
    """
    Scale amplitude based on frequency and loudness according to psychoacoustic principles.
    
    Args:
        freq (float): The frequency in Hz
        db_level (float): The input level in dB
        min_db (float): The minimum dB level in the dynamic range (default -60)
        
    Returns:
        float: The perceptually scaled amplitude (linear scale)
    """
    range_db = abs(min_db)
    phon_level = 40 + ((db_level - min_db) / range_db) * 60
    
    frequencies = np.array([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000], dtype=float)
    
    if phon_level <= 40:
        scaling_curve = np.array([0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.0, 0.9, 0.7, 0.4], dtype=float)
    elif phon_level <= 70:
        scaling_curve = np.array([0.3, 0.45, 0.6, 0.8, 0.95, 1.0, 1.0, 0.95, 0.8, 0.5], dtype=float)
    else:
        scaling_curve = np.array([0.5, 0.6, 0.7, 0.85, 0.95, 1.0, 1.0, 0.95, 0.85, 0.6], dtype=float)
    
    spline = interpolate.CubicSpline(frequencies, scaling_curve, extrapolate=True)
    scaling_factor = max(0.01, float(spline(freq)))
    
    raw_amp = dbamp(db_level)
    return raw_amp * scaling_factor 