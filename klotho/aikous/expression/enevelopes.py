# --------------------------------------------------
#  Klotho/klotho/aikous/envelopes.py
# --------------------------------------------------
'''
--------------------------------------------------------------------------------------
Envelopes for shaping the dynamics of a sequence of discrete values.
--------------------------------------------------------------------------------------
'''

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

def arch(start=0.0, end=1.0, steps=100, curve=0.0, axis=0):
    '''
    Generate a swelling curve that rises and falls, starting and ending at start value, peaking at end value.
    
    Args:
        start: Starting and ending value
        end: Peak value
        steps: Number of steps
        curve: Shape of the curve. Negative for exponential, positive for logarithmic, 0 for linear
        axis: Position of the peak (-1 to 1). 0 centers the peak, negative shifts earlier, positive shifts later
        
    Returns:
        numpy.ndarray: Array of values following a swell curve
    '''
    axis = np.clip(axis, -1, 1)
    split_point = int((0.5 + axis * 0.4) * steps)
    
    up = line(start, end, split_point, curve)
    down = line(end, start, steps - split_point, curve)
    
    return np.concatenate([up, down])

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
