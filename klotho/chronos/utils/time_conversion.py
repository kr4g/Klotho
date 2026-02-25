from typing import Union
import numpy as np
from fractions import Fraction
from itertools import accumulate
from klotho.utils.data_structures.enums import MinMaxEnum

__all__ = [
    'seconds_to_hmsms',
    'hmsms_to_seconds',
    'seconds_to_hmsf',
    'hmsf_to_seconds',
]

def seconds_to_hmsms(seconds: float, as_string=True) -> Union[str, tuple[int, int, int, int]]:
    """
    Convert a duration from seconds to hours, minutes, seconds, and milliseconds.

    Parameters
    ----------
    seconds : float
        The duration in seconds.
    as_string : bool, optional
        Whether to return the result as a formatted string or a tuple.
        Default is True.

    Returns
    -------
    str or tuple of int
        If ``as_string`` is True, a formatted string like ``'1h:01m:01s:500ms'``
        showing non-zero units. If False, a tuple of
        ``(hours, minutes, seconds, milliseconds)``.

    Examples
    --------
    >>> seconds_to_hmsms(3661.5)
    '1h:01m:01s:500ms'
    >>> seconds_to_hmsms(3661.5, as_string=False)
    (1, 1, 1, 500)
    """
    h = int(seconds // 3600)
    seconds %= 3600
    m = int(seconds // 60)
    seconds %= 60
    s = int(seconds)
    ms = int((seconds - s) * 1000)
    
    if not as_string:
        return (h, m, s, ms)
    
    parts = []
    if h > 0:
        parts.append(f'{h}h')
    if h > 0 or m > 0:
        parts.append(f'{m:02}m')
    parts.append(f'{s:02}s')
    parts.append(f'{ms:03}ms')
    
    return ':'.join(parts)
  
def hmsms_to_seconds(h:int = 0, m:int = 0, s:int = 0, ms:int = 0) -> float:
    """
    Convert hours, minutes, seconds, and milliseconds to total seconds.

    Parameters
    ----------
    h : int, optional
        Hours. Default is 0.
    m : int, optional
        Minutes. Default is 0.
    s : int, optional
        Seconds. Default is 0.
    ms : int, optional
        Milliseconds. Default is 0.

    Returns
    -------
    float
        Total duration in seconds.

    Examples
    --------
    >>> hmsms_to_seconds(h=1, m=30, s=45, ms=500)
    5445.5
    """
    return h * 3600 + m * 60 + s + ms / 1000

def seconds_to_hmsf(seconds: float, fps: int = 30, as_string: bool = True) -> Union[str, tuple[int, int, int, int]]:
    """
    Convert a duration from seconds to hours, minutes, seconds, and frames.

    Parameters
    ----------
    seconds : float
        The duration in seconds.
    fps : int, optional
        Frames per second. Default is 30.
    as_string : bool, optional
        Whether to return the result as a formatted string or a tuple.
        Default is True.

    Returns
    -------
    str or tuple of int
        If ``as_string`` is True, a formatted string like ``'1h:01m:01s:15f'``.
        If False, a tuple of ``(hours, minutes, seconds, frames)``.

    Examples
    --------
    >>> seconds_to_hmsf(3661.5, fps=30)
    '1h:01m:01s:15f'
    >>> seconds_to_hmsf(3661.5, fps=30, as_string=False)
    (1, 1, 1, 15)
    """
    h = int(seconds // 3600)
    seconds %= 3600
    m = int(seconds // 60)
    seconds %= 60
    s = int(seconds)
    f = int((seconds - s) * fps)
    
    if not as_string:
        return (h, m, s, f)
    
    parts = []
    if h > 0:
        parts.append(f'{h}h')
    if h > 0 or m > 0:
        parts.append(f'{m:02}m')
    parts.append(f'{s:02}s')
    parts.append(f'{f:02}f')
    
    return ':'.join(parts)
  
def hmsf_to_seconds(h:int = 0, m:int = 0, s:int = 0, f:int = 0, fps: int = 30) -> float:
    """
    Convert hours, minutes, seconds, and frames to total seconds.

    Parameters
    ----------
    h : int, optional
        Hours. Default is 0.
    m : int, optional
        Minutes. Default is 0.
    s : int, optional
        Seconds. Default is 0.
    f : int, optional
        Frames. Default is 0.
    fps : int, optional
        Frames per second. Default is 30.

    Returns
    -------
    float
        Total duration in seconds.

    Examples
    --------
    >>> hmsf_to_seconds(h=1, m=30, s=45, f=15, fps=30)
    5445.5
    """
    return h * 3600 + m * 60 + s + f / fps
