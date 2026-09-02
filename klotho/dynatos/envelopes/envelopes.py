"""
Envelopes for shaping the dynamics of musical sequences.

This module provides the Envelope class for creating and manipulating
time-varying amplitude or parameter envelopes with support for various
curve shapes and normalization options.
"""

from bisect import bisect_left

import numpy as np

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
        List of breakpoint values to interpolate between. At least two are
        required, since an envelope interpolates between breakpoints.
    times : float or list, optional
        Duration(s) for each segment, which must be non-negative. If a single
        value, all segments use the same duration. If a list, must have one
        fewer element than values. Default is 1.0.
    curve : float or list, optional
        Curve shape for each segment. 0 = linear, negative = exponential,
        positive = logarithmic. If a single value, all segments use the same
        curve; if a list, it must have one fewer element than values.
        Default is 0.0.
    warp : str, optional
        Interpolation domain for all segments: ``'lin'`` (default)
        interpolates values linearly; ``'exp'`` interpolates in the
        exponential (log) domain, i.e. a linexp mapping suited to
        perceptual parameters such as frequency. ``warp`` composes with
        ``curve``: the curve shapes the segment progress first, then the
        (possibly exponential) interpolation is applied. ``'exp'``
        requires every value to be strictly positive.
    normalize_values : bool, optional
        Whether to normalize values to 0-1 range at construction. Default is False.
    normalize_times : bool, optional
        Whether to normalize times to sum to 1 at construction. Default is False.
    value_scale : float, optional
        Scale factor applied to all values at construction. Default is 1.0.
    time_scale : float, optional
        Scale factor applied to all times when computing durations. Must be
        non-negative. Default is 1.0.

    Raises
    ------
    ValueError
        If fewer than two values are given; if a supplied ``times`` or
        ``curve`` list does not have exactly one entry per segment; if any
        segment time or ``time_scale`` is negative; if ``warp`` is neither
        ``'lin'`` nor ``'exp'``; or if ``warp='exp'`` and any value is not
        strictly positive after normalization and scaling.

    Examples
    --------
    >>> env = Envelope([0, 1, 0.5, 0], times=[0.1, 0.8, 0.1])
    >>> env.at_time(0.5)
    0.75
    
    >>> decay = Envelope([1, 0], times=2.0, curve=-3)
    >>> decay.at_time(0)
    1.0
    >>> decay.at_time(2.0)
    0.0
    """
    def __init__(self, values, times=1.0, curve=0.0, warp='lin',
                 normalize_values=False, normalize_times=False,
                 value_scale=1.0, time_scale=1.0):
        values = list(values)
        # An envelope interpolates BETWEEN breakpoints, so fewer than two of
        # them describes no segment. `Envelope([])` used to construct happily
        # and then raise IndexError on the first `at_time`, a page away from
        # the call that was actually wrong.
        n_segments = len(values) - 1
        if n_segments < 1:
            raise ValueError(
                f"values must have at least 2 breakpoints to define a "
                f"segment; got {len(values)}"
            )

        times_given_as_list = isinstance(times, (list, tuple))
        times = list(times) if times_given_as_list else [times] * n_segments
        curve_given_as_list = isinstance(curve, (list, tuple))
        curve = list(curve) if curve_given_as_list else [curve] * n_segments

        # A caller-supplied list has to match the segment count exactly. Too
        # many times silently LENGTHENED the envelope (total_time grew and the
        # surplus segments answered with the last value); too few silently
        # TRUNCATED it. A short curve list was the only loud one, and it was
        # loud late -- an IndexError from at_time, not from the constructor.
        if times_given_as_list and len(times) != n_segments:
            raise ValueError(
                f"times must have one entry per segment: got {len(times)} "
                f"times for {len(values)} values, which needs {n_segments}"
            )
        if curve_given_as_list and len(curve) != n_segments:
            raise ValueError(
                f"curve must have one entry per segment: got {len(curve)} "
                f"curve values for {len(values)} values, which needs "
                f"{n_segments}"
            )

        # Durations run forward. A negative one made the cumulative boundary
        # list non-monotonic, which both shortened total_time and left
        # bisect_left searching an unsorted sequence -- a wrong answer with no
        # error anywhere. `time_scale` is the same quantity through another
        # door: a negative scale built an envelope that refused every query,
        # including at_time(0). Zero is still allowed for both, because
        # apply_envelope reaches time_scale=0 for a zero-duration span.
        if any(t < 0 for t in times):
            raise ValueError(f"segment times must be non-negative; got {times}")
        if time_scale < 0:
            raise ValueError(
                f"time_scale must be non-negative; got {time_scale}"
            )

        values_as_given = list(values)

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
        
        if warp not in ('lin', 'exp'):
            raise ValueError(f"warp must be 'lin' or 'exp', got {warp!r}")
        if warp == 'exp' and any(v <= 0 for v in values):
            # Report what the caller typed. The check has to run AFTER
            # normalize_values/value_scale (a scale of -1 is exactly how a
            # positive list turns negative), but quoting only the rewritten
            # list named no number the caller had ever seen.
            detail = f"got {values_as_given}"
            if values != values_as_given:
                detail += (
                    f", which becomes {values} after normalization/scaling"
                )
            raise ValueError(
                "warp='exp' requires all envelope values to be strictly "
                f"positive; {detail}"
            )

        self._values = values
        self._times = times
        self._curve = curve
        self._warp = warp
        self._time_scale = time_scale
        self._at_time_cache: dict = {}
    
    @classmethod
    def perc(cls, attackTime=0.01, releaseTime=1.0, curve=-4.0, warp='lin', time_scale=1.0):
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
        return cls(values=[0, 1, 0], times=[attackTime, releaseTime], curve=curve, warp=warp, time_scale=time_scale)
    
    @classmethod
    def adr(cls, attackTime=0.01, decayTime=0.3, decayLevel=0.5, releaseTime=1.0, curve=-4.0, warp='lin', time_scale=1.0):
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
        return cls(values=[0, 1, decayLevel, 0], times=[attackTime, decayTime, releaseTime], curve=curve, warp=warp, time_scale=time_scale)
    
    @classmethod
    def adsr(cls, attackTime=0.01, decayTime=0.3, sustainTime=0.5, sustainLevel=0.5, releaseTime=1.0, curve=-4.0, warp='lin', time_scale=1.0):
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
        return cls(values=[0, 1, sustainLevel, sustainLevel, 0], times=[attackTime, decayTime, sustainTime, releaseTime], curve=curve, warp=warp, time_scale=time_scale)
    
    @classmethod
    def pairs(cls, pairs, curve=0.0, warp='lin', time_scale=1.0):
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
        return cls(values=values, times=durations, curve=curve, warp=warp, time_scale=time_scale)
    
    @property
    def values(self):
        """List of breakpoint values."""
        return self._values
    
    @property
    def times(self):
        """List of segment durations."""
        return self._times
    
    @property
    def curve(self):
        """List of per-segment curve factors (0 = linear)."""
        return self._curve

    @property
    def warp(self):
        """Interpolation domain: ``'lin'`` or ``'exp'``."""
        return self._warp

    @property
    def time_scale(self):
        """Time scale factor applied to segment durations."""
        return self._time_scale
    
    def _segment_state(self):
        """Precomputed (scaled_times, cumulative_boundaries, total).

        Envelopes are immutable after construction (values/times/scale are
        only written in ``__init__``), so this is computed once — at_time
        used to re-sum total_time twice and rebuild the scaled-times list
        on every call.
        """
        state = self.__dict__.get('_segment_state_cache')
        if state is None:
            scaled = [t * self._time_scale for t in self._times]
            boundaries = [0.0]
            current = 0.0
            for t in scaled:
                current += t
                boundaries.append(current)
            state = (scaled, boundaries, boundaries[-1] if scaled else 0.0)
            self.__dict__['_segment_state_cache'] = state
        return state

    @property
    def total_time(self):
        """Total duration of the envelope."""
        return self._segment_state()[2]
    
    @property
    def breakpoint_times(self):
        """Cumulative time points for each breakpoint value."""
        result = [0.0]
        current_time = 0.0
        for t in self._times:
            current_time += t * self._time_scale
            result.append(current_time)
        return result

    @property
    def normalized_times(self):
        """Cumulative breakpoint times normalized to the [0, 1] range."""
        total = self.total_time
        if total <= 0:
            return [0.0] * len(self._values)
        return [t / total for t in self.breakpoint_times]
    
    def at_time(self, time):
        """
        Get the envelope value at a specific time.

        Results are memoized on a per-instance cache keyed by the requested
        time, so repeated queries against the same envelope are O(1) after
        the first. The cache lifetime is bound to the envelope instance
        itself (unlike a module-level ``lru_cache``, which would keep every
        envelope alive for the life of the interpreter).

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
        cached = self._at_time_cache.get(time)
        if cached is not None:
            return cached
        result = self._at_time_uncached(time)
        if len(self._at_time_cache) >= 1024:
            # bound the memo: linspace-style sweeps never repeat a key and
            # used to grow this dict without limit
            self._at_time_cache.clear()
        self._at_time_cache[time] = result
        return result

    def _at_time_uncached(self, time):
        scaled_times, boundaries, total = self._segment_state()

        if time < 0 or time > total:
            raise ValueError(f"Time {time} is outside envelope duration [0, {total}]")
        if time == 0:
            value = self._values[0]
        elif time == total:
            value = self._values[-1]
        else:
            # First segment whose end boundary is >= time — identical to the
            # old linear scan's `time <= segment_end_time`, without rebuilding
            # the scaled-times list per call.
            #
            # The constructor now guarantees len(times) == len(values) - 1, so
            # `boundaries` has exactly len(values) entries and, for
            # 0 < time < total, `seg` can never reach len(values) - 1. The
            # `seg >= n_segments` fallback that used to sit here was only ever
            # reachable through an over-long `times` list, which is refused.
            seg = bisect_left(boundaries, time) - 1
            current_time = boundaries[seg]
            segment_duration = scaled_times[seg]
            segment_progress = (time - current_time) / segment_duration
            start_val = self._values[seg]
            end_val = self._values[seg + 1]
            curve_val = self._curve[seg]

            if curve_val == 0:
                progress = segment_progress
            else:
                progress = (np.exp(curve_val * segment_progress) - 1) / (np.exp(curve_val) - 1)

            if self._warp == 'exp':
                value = start_val * (end_val / start_val) ** progress
            else:
                value = start_val + (end_val - start_val) * progress

        # One coercion, at the return boundary, so every path answers in the
        # type the docstring promises. Before this the two endpoint branches
        # handed back whatever the caller put in `values` (an int stayed an
        # int) and the curved branch handed back a numpy scalar.
        return float(value)

    def sample(self, times):
        """
        Evaluate the envelope at each time in *times* (batch ``at_time``).

        Parameters
        ----------
        times : iterable of float
            Query times, each within ``[0, total_time]``.

        Returns
        -------
        list of float
            Envelope values, sample-for-sample identical to calling
            :meth:`at_time` per element (shared precomputed segment
            state; no per-call memoization traffic).

        Raises
        ------
        TypeError
            If *times* is not iterable. A scalar used to reach the list
            comprehension and surface as ``'float' object is not iterable``,
            which names neither the method nor the alternative.
        """
        if not hasattr(times, '__iter__'):
            raise TypeError(
                f"sample() expects an iterable of times, got "
                f"{type(times).__name__} ({times!r}); use at_time() for a "
                f"single time"
            )
        at = self._at_time_uncached
        return [at(float(t)) for t in times]

    def __str__(self):
        def format_list(lst):
            if len(set(lst)) == 1:
                return lst[0]
            return lst
        
        effective_times = [t * self._time_scale for t in self._times]

        warp_str = f", warp='{self._warp}'" if self._warp != 'lin' else ""
        return f"Envelope(values={format_list(self._values)}, times={format_list(effective_times)}, curve={format_list(self._curve)}{warp_str})"

    def __repr__(self):
        return self.__str__()
