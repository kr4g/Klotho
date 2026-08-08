from typing import Union
from fractions import Fraction
from itertools import accumulate

__all__ = [
    'cycles_to_frequency',
    'beat_duration',
    'calc_onsets',
]

def cycles_to_frequency(cycles: Union[int, float], duration: float) -> float:
    """
    Calculate the frequency needed to produce a number of cycles within a duration.

    Parameters
    ----------
    cycles : int or float
        The desired number of complete cycles.
    duration : float
        The time duration in seconds.

    Returns
    -------
    float
        The frequency in Hertz (Hz).

    Examples
    --------
    >>> cycles_to_frequency(4, 2)
    2.0
    """
    return cycles / duration

def beat_duration(ratio:Union[int, float, Fraction, str], bpm:Union[int, float], beat_ratio:Union[int, float, Fraction, str] = '1/4') -> float:
    """
    Calculate the duration in seconds of a musical beat given a ratio and tempo.

    The beat duration is determined by the ratio of the beat to a reference
    beat duration (``beat_ratio``), scaled by the tempo factor derived from
    beats per minute (BPM).

    Parameters
    ----------
    ratio : int, float, Fraction, or str
        The ratio of the desired beat duration to a whole note
        (e.g., ``'1/4'`` for a quarter note).
    bpm : int or float
        The tempo in beats per minute.
    beat_ratio : int, float, Fraction, or str, optional
        The reference beat duration ratio. Default is ``'1/4'``
        (quarter note).

    Returns
    -------
    float
        The beat duration in seconds.

    Examples
    --------
    >>> beat_duration('1/4', 120)
    0.5
    """
    tempo_factor = 60 / bpm
    if type(ratio) is Fraction:
        ratio_value = ratio.numerator / ratio.denominator
    else:
        ratio_value = _ratio_as_float(ratio)
    if type(beat_ratio) is not Fraction:
        beat_ratio = _parse_beat_ratio(beat_ratio)
    return tempo_factor * ratio_value * (beat_ratio.denominator / beat_ratio.numerator)


# Parse caches: beat_duration is called once per node per timing pass, but the
# distinct (ratio, beat_ratio) inputs per session are few — mostly repeated
# strings like '3/8'. Values are bounded by a hard cap so pathological streams
# of unique keys cannot grow memory without limit.
_RATIO_FLOAT_CACHE: dict = {}
_BEAT_RATIO_CACHE: dict = {}
_PARSE_CACHE_MAX = 4096


def _ratio_as_float(ratio) -> float:
    try:
        return _RATIO_FLOAT_CACHE[ratio]
    except KeyError:
        pass
    except TypeError:
        return float(Fraction(ratio))
    value = float(Fraction(ratio))
    if len(_RATIO_FLOAT_CACHE) >= _PARSE_CACHE_MAX:
        _RATIO_FLOAT_CACHE.clear()
    _RATIO_FLOAT_CACHE[ratio] = value
    return value


def _parse_beat_ratio(beat_ratio) -> Fraction:
    try:
        return _BEAT_RATIO_CACHE[beat_ratio]
    except KeyError:
        pass
    except TypeError:
        return Fraction(beat_ratio)
    value = Fraction(beat_ratio)
    if len(_BEAT_RATIO_CACHE) >= _PARSE_CACHE_MAX:
        _BEAT_RATIO_CACHE.clear()
    _BEAT_RATIO_CACHE[beat_ratio] = value
    return value

def calc_onsets(durations:tuple):
    """
    Calculate onset times from a sequence of durations.

    Each onset is the cumulative sum of the absolute values of all
    preceding durations, starting from zero.

    Parameters
    ----------
    durations : tuple
        A sequence of duration values (may include negative values for rests).

    Returns
    -------
    tuple
        The onset times corresponding to each duration.

    Examples
    --------
    >>> calc_onsets((Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)))
    (0, Fraction(1, 4), Fraction(1, 2))
    """
    return tuple(accumulate([0] + list(abs(r) for r in durations[:-1])))
