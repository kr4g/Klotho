"""
Curve generation and mapping utilities for envelopes.

This module provides functions for generating various types of curves
including linear and exponential lines, arch/swell shapes, and value
mapping with curve transformations.
"""

import numpy as np

__all__ = [
    'line',
    'arch',
    'map_curve',
]

def line(start=0.0, end=1.0, steps=100, curve=0.0):
    """
    Generate a curved line from start to end value over n steps.
    
    Parameters
    ----------
    start : float, optional
        Starting value (default is 0.0).
    end : float, optional
        Ending value (default is 1.0).
    steps : int, optional
        Number of steps (default is 100).
    curve : float, optional
        Shape of the curve. Negative for exponential, positive for logarithmic,
        0 for linear (default is 0.0).
        
    Returns
    -------
    numpy.ndarray
        Array of values following the specified curve.
    """
    if curve == 0:
        return np.linspace(start, end, steps)
    
    t = np.linspace(0, 1, steps)
    curved_t = np.exp(curve * t) - 1
    curved_t = curved_t / (np.exp(curve) - 1)
    
    return start + (end - start) * curved_t

def arch(base=0.0, peak=1.0, steps=100, curve=0.0, axis=0):
    """
    Generate a swelling curve that rises and falls.
    
    Starts and ends at the base value, peaking at the peak value.
    
    Parameters
    ----------
    base : float, optional
        Starting and ending value (default is 0.0).
    peak : float, optional
        Peak value (default is 1.0).
    steps : int, optional
        Number of steps (default is 100).
    curve : float or list of float, optional
        Shape of the curve. A single number applies the same curve to both
        sides (negative for exponential, positive for logarithmic). A list
        of two values sets ascending and descending curves independently
        (default is 0.0).
    axis : float, optional
        Position of the peak (-1 to 1). 0 centers the peak, negative shifts
        earlier, positive shifts later (default is 0).
        
    Returns
    -------
    numpy.ndarray
        Array of values following a swell curve.
    """
    axis = np.clip(axis, -1, 1)
    split_point = int((0.5 + axis * 0.4) * steps)
    
    if isinstance(curve, (list, tuple)) and len(curve) == 2:
        up_curve, down_curve = curve
    else:
        up_curve = down_curve = curve
    
    up = line(base, peak, split_point + 1, up_curve)
    down = line(peak, base, steps - split_point, down_curve)
    
    return np.concatenate([up[:-1], down])

def map_curve(value, in_range, out_range, curve=0.0):
    """
    Map a value from an input range to an output range with optional curve shaping.
    
    Parameters
    ----------
    value : float
        Input value to map.
    in_range : tuple of float
        (min, max) for the input range.
    out_range : tuple of float
        (min, max) for the output range.
    curve : float, optional
        Shape of the curve. Negative for exponential, positive for logarithmic,
        0 for linear (default is 0.0).
        
    Returns
    -------
    float
        Mapped value with curve applied.
    """
    normalized = np.interp(value, in_range, (0, 1))
    
    if curve != 0:
        normalized = np.exp(curve * normalized) - 1
        normalized = normalized / (np.exp(curve) - 1)
    
    return np.interp(normalized, (0, 1), out_range) 