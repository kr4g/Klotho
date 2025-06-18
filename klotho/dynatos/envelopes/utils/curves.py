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
    '''
    Generate a curved line from start to end value over n steps.
    
    Args:
        start: Starting value
        end: Ending value
        steps: Number of steps
        curve: Shape of the curve. Negative for exponential, positive for logarithmic, 0 for linear
        
    Returns:
        numpy.ndarray: Array of values following the specified curve
    '''
    if curve == 0:
        return np.linspace(start, end, steps)
    
    t = np.linspace(0, 1, steps)
    curved_t = np.exp(curve * t) - 1
    curved_t = curved_t / (np.exp(curve) - 1)
    
    return start + (end - start) * curved_t

def arch(base=0.0, peak=1.0, steps=100, curve=0.0, axis=0):
    '''
    Generate a swelling curve that rises and falls, starting and ending at base value, peaking at peak value.
    
    Args:
        base: Starting and ending value
        peak: Peak value
        steps: Number of steps
        curve: Shape of the curve. Can be:
               - A single number: Same curve applied to both sides (negative for exponential, positive for logarithmic)
               - A tuple/list of two values: First value for ascending curve, second for descending
        axis: Position of the peak (-1 to 1). 0 centers the peak, negative shifts earlier, positive shifts later
        
    Returns:
        numpy.ndarray: Array of values following a swell curve
    '''
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
    '''
    Map a value from an input range to an output range with optional curve shaping.
    
    Args:
        value: Input value to map
        in_range: Tuple of (min, max) for input range
        out_range: Tuple of (min, max) for output range
        curve: Shape of the curve. Negative for exponential, positive for logarithmic, 0 for linear
        
    Returns:
        float: Mapped value with curve applied
    '''
    normalized = np.interp(value, in_range, (0, 1))
    
    if curve != 0:
        normalized = np.exp(curve * normalized) - 1
        normalized = normalized / (np.exp(curve) - 1)
    
    return np.interp(normalized, (0, 1), out_range) 