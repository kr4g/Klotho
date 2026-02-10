"""
Envelopes for shaping the dynamics of musical sequences.

This module provides the Envelope class for creating and manipulating
time-varying amplitude or parameter envelopes with support for various
curve shapes and normalization options.
"""

import numpy as np
from functools import lru_cache
from .utils import line

__all__ = [
    'Envelope',
]

class Envelope:
    """
    A flexible envelope generator for time-varying parameter control.
    
    The Envelope class creates smooth transitions between a series of values
    over specified time durations, with support for curve shaping, normalization,
    and scaling. 
    
    Args:
        values (list): List of values to interpolate between
        times (float or list): Duration(s) for each segment. If a single value,
            all segments use the same duration. If a list, must have one fewer
            element than values (default: 1.0)
        curve (float or list): Curve shape for each segment. 0 = linear,
            negative = exponential, positive = logarithmic. If a single value,
            all segments use the same curve (default: 0.0)
        normalize_values (bool): Whether to normalize values to 0-1 range (default: False)
        normalize_times (bool): Whether to normalize times to sum to 1 (default: False)
        value_scale (float): Scale factor applied to all values (default: 1.0)
        time_scale (float): Scale factor applied to all times (default: 1.0)
        resolution (int): Number of points to generate for the envelope (default: 1000)
        
    Example:
        >>> # Simple fade in/out envelope
        >>> env = Envelope([0, 1, 0.5, 0], times=[0.1, 0.8, 0.1])
        >>> len(env)
        1000
        >>> env.at_time(0.5)
        0.875
        
        >>> # Exponential decay
        >>> decay = Envelope([1, 0], times=2.0, curve=-3)
        >>> decay[0]  # Start value
        1.0
        >>> decay[-1]  # End value
        0.0
    """
    def __init__(self, values, times=1.0, curve=0.0, 
                 normalize_values=False, normalize_times=False, 
                 value_scale=1.0, time_scale=1.0, resolution=1000):
        self._original_values = list(values)
        self._original_times = times if isinstance(times, (list, tuple)) else [times] * (len(self._original_values) - 1)
        self._curve = curve if isinstance(curve, (list, tuple)) else [curve] * (len(self._original_values) - 1)
        self._resolution = resolution
        self._time_scale = time_scale
        self._normalize_times = normalize_times
        self._normalize_values = normalize_values
        self._value_scale = value_scale
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    def _apply_normalizations(self):
        values = list(self._original_values)
        times = list(self._original_times)
        
        if self._normalize_values and len(values) > 1:
            min_val = min(values)
            max_val = max(values)
            if max_val != min_val:
                values = [(v - min_val) / (max_val - min_val) for v in values]
        
        if self._value_scale != 1.0:
            values = [v * self._value_scale for v in values]
        
        if self._normalize_times and len(times) > 0:
            time_sum = sum(times)
            if time_sum != 0:
                times = [t / time_sum for t in times]
        
        return values, times
    
    def _generate_envelope(self):
        if hasattr(self, 'at_time'):
            self.at_time.cache_clear()
        
        if len(self._values) < 2:
            return np.array(self._values), np.array([0])
        
        segments = []
        time_segments = []
        current_time = 0
        scaled_times = [t * self._time_scale for t in self._times]
        
        for i in range(len(self._values) - 1):
            start_val = self._values[i]
            end_val = self._values[i + 1]
            duration = scaled_times[i]
            curve_val = self._curve[i]
            
            steps = max(2, int(self._resolution * duration / sum(scaled_times)))
            
            segment = line(start_val, end_val, steps, curve_val)
            time_segment = np.linspace(current_time, current_time + duration, steps)
            
            if i > 0:
                segment = segment[1:]
                time_segment = time_segment[1:]
            
            segments.append(segment)
            time_segments.append(time_segment)
            current_time += duration
        
        return np.concatenate(segments), np.concatenate(time_segments)
    
    def __iter__(self):
        return iter(self._data)
    
    def __getitem__(self, index):
        return self._data[index]
    
    def __len__(self):
        return len(self._data)
    
    @property
    def values(self):
        return self._values
    
    @property
    def times(self):
        return self._times
    
    @property
    def time_points(self):
        return self._time_points
    
    @property
    def resolution(self):
        return self._resolution
    
    @resolution.setter
    def resolution(self, value):
        self._resolution = value
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    @property
    def time_scale(self):
        return self._time_scale
    
    @time_scale.setter
    def time_scale(self, value):
        self._time_scale = value
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    @property
    def normalize_times(self):
        return self._normalize_times
    
    @normalize_times.setter
    def normalize_times(self, value):
        self._normalize_times = value
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    @property
    def normalize_values(self):
        return self._normalize_values
    
    @normalize_values.setter
    def normalize_values(self, value):
        self._normalize_values = value
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    @property
    def value_scale(self):
        return self._value_scale
    
    @value_scale.setter
    def value_scale(self, value):
        self._value_scale = value
        self._values, self._times = self._apply_normalizations()
        self._data, self._time_points = self._generate_envelope()
    
    @property
    def total_time(self):
        return sum(t * self._time_scale for t in self._times)
    
    @lru_cache(maxsize=128)
    def at_time(self, time):
        if time < 0 or time > self.total_time:
            raise ValueError(f"Time {time} is outside envelope duration [0, {self.total_time}]")
        
        if time == 0:
            return self._values[0]
        if time == self.total_time:
            return self._values[-1]
        
        scaled_times = [t * self._time_scale for t in self._times]
        current_time = 0
        
        for i in range(len(self._values) - 1):
            segment_duration = scaled_times[i]
            segment_end_time = current_time + segment_duration
            
            if time <= segment_end_time:
                segment_progress = (time - current_time) / segment_duration
                start_val = self._values[i]
                end_val = self._values[i + 1]
                curve_val = self._curve[i]
                
                if curve_val == 0:
                    return start_val + (end_val - start_val) * segment_progress
                else:
                    curved_progress = (np.exp(curve_val * segment_progress) - 1) / (np.exp(curve_val) - 1)
                    return start_val + (end_val - start_val) * curved_progress
            
            current_time = segment_end_time
        
        return self._values[-1]

    def __str__(self):
        def format_list(lst):
            if len(set(lst)) == 1:
                return lst[0]
            return lst
        
        effective_times = [t * self._time_scale for t in self._times]
        
        return f"Envelope(values={format_list(self._values)}, times={format_list(effective_times)}, curve={format_list(self._curve)})"

    def __repr__(self):
        return self.__str__() 