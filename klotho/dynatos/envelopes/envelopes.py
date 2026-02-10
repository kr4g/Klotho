"""
Envelopes for shaping the dynamics of musical sequences.

This module provides the Envelope class for creating and manipulating
time-varying amplitude or parameter envelopes with support for various
curve shapes and normalization options.
"""

import numpy as np
from functools import lru_cache

__all__ = [
    'Envelope',
]

class Envelope:
    """
    A flexible envelope generator for time-varying parameter control.
    
    The Envelope class creates smooth transitions between a series of values
    over specified time durations, with support for curve shaping, normalization,
    and scaling. The envelope is immutable after construction.
    
    Parameters
    ----------
    values : list
        List of breakpoint values to interpolate between.
    times : float or list, optional
        Duration(s) for each segment. If a single value, all segments use 
        the same duration. If a list, must have one fewer element than values.
        Default is 1.0.
    curve : float or list, optional
        Curve shape for each segment. 0 = linear, negative = exponential, 
        positive = logarithmic. If a single value, all segments use the same 
        curve. Default is 0.0.
    normalize_values : bool, optional
        Whether to normalize values to 0-1 range at construction. Default is False.
    normalize_times : bool, optional
        Whether to normalize times to sum to 1 at construction. Default is False.
    value_scale : float, optional
        Scale factor applied to all values at construction. Default is 1.0.
    time_scale : float, optional
        Scale factor applied to all times when computing durations. Default is 1.0.
        
    Examples
    --------
    >>> env = Envelope([0, 1, 0.5, 0], times=[0.1, 0.8, 0.1])
    >>> env.at_time(0.5)
    0.875
    
    >>> decay = Envelope([1, 0], times=2.0, curve=-3)
    >>> decay.at_time(0)
    1.0
    >>> decay.at_time(2.0)
    0.0
    """
    def __init__(self, values, times=1.0, curve=0.0, 
                 normalize_values=False, normalize_times=False, 
                 value_scale=1.0, time_scale=1.0):
        values = list(values)
        times = times if isinstance(times, (list, tuple)) else [times] * (len(values) - 1)
        times = list(times)
        curve = curve if isinstance(curve, (list, tuple)) else [curve] * (len(values) - 1)
        curve = list(curve)
        
        if normalize_values and len(values) > 1:
            min_val = min(values)
            max_val = max(values)
            if max_val != min_val:
                values = [(v - min_val) / (max_val - min_val) for v in values]
        
        if value_scale != 1.0:
            values = [v * value_scale for v in values]
        
        if normalize_times and len(times) > 0:
            time_sum = sum(times)
            if time_sum != 0:
                times = [t / time_sum for t in times]
        
        self._values = values
        self._times = times
        self._curve = curve
        self._time_scale = time_scale
    
    @classmethod
    def perc(cls, attackTime=0.01, releaseTime=1.0, curve=-4.0, time_scale=1.0):
        """
        Create a percussive envelope: 0 -> 1 -> 0
        
        Parameters
        ----------
        attackTime : float, optional
            Duration of attack phase. Default is 0.01.
        releaseTime : float, optional
            Duration of release phase. Default is 1.0.
        curve : float, optional
            Curve shape for both segments. Default is -4.0.
        time_scale : float, optional
            Time scale factor. Default is 1.0.
            
        Returns
        -------
        Envelope
            A percussive envelope instance.
        """
        return cls(values=[0, 1, 0], times=[attackTime, releaseTime], curve=curve, time_scale=time_scale)
    
    @classmethod
    def adr(cls, attackTime=0.01, decayTime=0.3, decayLevel=0.5, releaseTime=1.0, curve=-4.0, time_scale=1.0):
        """
        Create an ADR envelope (3 segments): 0 -> 1 -> decayLevel -> 0
        
        Parameters
        ----------
        attackTime : float, optional
            Duration of attack phase. Default is 0.01.
        decayTime : float, optional
            Duration of decay phase. Default is 0.3.
        decayLevel : float, optional
            Level after decay. Default is 0.5.
        releaseTime : float, optional
            Duration of release phase. Default is 1.0.
        curve : float, optional
            Curve shape for all segments. Default is -4.0.
        time_scale : float, optional
            Time scale factor. Default is 1.0.
            
        Returns
        -------
        Envelope
            An ADR envelope instance.
        """
        return cls(values=[0, 1, decayLevel, 0], times=[attackTime, decayTime, releaseTime], curve=curve, time_scale=time_scale)
    
    @classmethod
    def adsr(cls, attackTime=0.01, decayTime=0.3, sustainTime=0.5, sustainLevel=0.5, releaseTime=1.0, curve=-4.0, time_scale=1.0):
        """
        Create an ADSR envelope (4 segments): 0 -> 1 -> sustainLevel (hold) -> 0
        
        Parameters
        ----------
        attackTime : float, optional
            Duration of attack phase. Default is 0.01.
        decayTime : float, optional
            Duration of decay phase. Default is 0.3.
        sustainTime : float, optional
            Duration of sustain phase. Default is 0.5.
        sustainLevel : float, optional
            Level during sustain. Default is 0.5.
        releaseTime : float, optional
            Duration of release phase. Default is 1.0.
        curve : float, optional
            Curve shape for all segments. Default is -4.0.
        time_scale : float, optional
            Time scale factor. Default is 1.0.
            
        Returns
        -------
        Envelope
            An ADSR envelope instance.
        """
        return cls(values=[0, 1, sustainLevel, sustainLevel, 0], times=[attackTime, decayTime, sustainTime, releaseTime], curve=curve, time_scale=time_scale)
    
    @classmethod
    def pairs(cls, pairs, curve=0.0, time_scale=1.0):
        """
        Create an envelope from (time, value) pairs.
        
        Parameters
        ----------
        pairs : list of tuples
            List of (time, value) pairs defining the envelope shape.
            Times should be absolute positions, not durations.
        curve : float, optional
            Curve shape for all segments. Default is 0.0 (linear).
        time_scale : float, optional
            Time scale factor. Default is 1.0.
            
        Returns
        -------
        Envelope
            An envelope instance defined by the given pairs.
            
        Examples
        --------
        >>> env = Envelope.pairs([(0, 0), (0.1, 1), (0.5, 0.5), (1.0, 0)])
        """
        sorted_pairs = sorted(pairs, key=lambda p: p[0])
        times_abs = [p[0] for p in sorted_pairs]
        values = [p[1] for p in sorted_pairs]
        durations = [times_abs[i+1] - times_abs[i] for i in range(len(times_abs)-1)]
        return cls(values=values, times=durations, curve=curve, time_scale=time_scale)
    
    @property
    def values(self):
        """List of breakpoint values."""
        return self._values
    
    @property
    def times(self):
        """List of segment durations."""
        return self._times
    
    @property
    def time_scale(self):
        """Time scale factor applied to segment durations."""
        return self._time_scale
    
    @property
    def total_time(self):
        """Total duration of the envelope."""
        return sum(t * self._time_scale for t in self._times)
    
    @property
    def breakpoint_times(self):
        """Cumulative time points for each breakpoint value."""
        result = [0.0]
        current_time = 0.0
        for t in self._times:
            current_time += t * self._time_scale
            result.append(current_time)
        return result
    
    @lru_cache(maxsize=128)
    def at_time(self, time):
        """
        Get the envelope value at a specific time.
        
        Parameters
        ----------
        time : float
            Time point to query (must be within [0, total_time]).
            
        Returns
        -------
        float
            Interpolated envelope value at the given time.
            
        Raises
        ------
        ValueError
            If time is outside the envelope duration.
        """
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
