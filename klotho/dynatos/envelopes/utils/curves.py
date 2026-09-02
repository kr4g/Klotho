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

    Raises
    ------
    ValueError
        If ``curve`` is a sequence of any length other than 2.
    """
    if np.ndim(curve) > 0 and len(list(curve)) != 2:
        # Validated BEFORE the degenerate-steps return below, deliberately. The
        # other way round, a malformed curve was accepted in silence at exactly
        # steps <= 1 while raising at every other step count -- so the caller
        # who happened to exercise the one-sample case got no signal that their
        # argument was wrong.
        raise ValueError(
            f"curve must be a single number or a sequence of exactly 2 "
            f"(ascending, descending); got {len(list(curve))}: {curve}"
        )

    if steps <= 1:
        # No rise and no fall fit in one sample. An arch begins at its base,
        # so that is what a single sample of one shows -- `line` already
        # answers with its START for steps=1. This used to fall through to
        # `concatenate([up[:-1], down])` with an empty rise and return
        # [peak]: the one point an arch is definitely not at when it begins.
        # (steps <= 0 keeps its old empty result, and a negative steps still
        # raises the same message numpy has always given.)
        return np.linspace(base, base, steps)

    axis = np.clip(axis, -1, 1)
    split_point = int((0.5 + axis * 0.4) * steps)

    if np.ndim(curve) > 0:
        # A sequence used to fall through to the `else` and be multiplied
        # against the per-sample progress array inside `line`. When its length
        # happened to match the sample count that broadcast element-wise and
        # returned a per-SAMPLE curve -- plausible numbers, wrong shape, no
        # error; at any other length it died as
        # "operands could not be broadcast together", which names neither this
        # function nor the argument at fault.
        sides = list(curve)
        if len(sides) != 2:
            raise ValueError(
                f"curve must be a single number or a sequence of exactly 2 "
                f"(ascending, descending); got {len(sides)}: {curve}"
            )
        up_curve, down_curve = sides
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
        (start, end) for the input range. Either orientation is accepted:
        ``(0, 10)`` and ``(10, 0)`` are both valid and are mirror images of
        each other. Values outside the range are clamped to it. A zero-width
        range maps everything to ``out_range[0]``.
    out_range : tuple of float
        (start, end) for the output range. Either orientation is accepted.
    curve : float, optional
        Shape of the curve. Negative for exponential, positive for logarithmic,
        0 for linear (default is 0.0).

    Returns
    -------
    float
        Mapped value with curve applied.

    Examples
    --------
    A value halfway along the input range lands halfway along the output range:

    >>> float(map_curve(5, (0, 10), (0, 1)))
    0.5

    A DESCENDING ``in_range`` is a mirror image, not an error. Reading it
    backwards is the point: 0 is now the top of the sweep and 10 the bottom.

    >>> float(map_curve(0, (10, 0), (0, 1)))
    1.0
    >>> float(map_curve(10, (10, 0), (0, 1)))
    0.0

    The result is wrapped in ``float`` here only so the printed value is a
    plain number; the function itself returns a numpy scalar.
    """
    # Normalize explicitly rather than through np.interp. np.interp requires
    # an INCREASING `xp` and does not check it, so a descending in_range such
    # as (72, 60) used to return a silently wrong number: every probe past the
    # first collapsed onto out_range[1] instead of sweeping across it. The
    # arithmetic below is orientation-agnostic by construction.
    in_start, in_end = in_range
    in_span = in_end - in_start
    if in_span == 0:
        # No distance to travel: sit at the start of the sweep. This is the
        # limit of (value - in_start) / in_span as the span closes, and it is
        # what a player does with a one-note hairpin.
        normalized = np.zeros_like(np.asarray(value, dtype=float))
    else:
        normalized = np.clip((np.asarray(value, dtype=float) - in_start) / in_span, 0.0, 1.0)

    if curve != 0:
        normalized = np.exp(curve * normalized) - 1
        normalized = normalized / (np.exp(curve) - 1)

    out_start, out_end = out_range
    return out_start + normalized * (out_end - out_start) 