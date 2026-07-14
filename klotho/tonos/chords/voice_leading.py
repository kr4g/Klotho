"""
Register bounds and voice leading for relative pitch collections.

:func:`fold` octave-displaces each degree of a chord until its sounding
pitch lies within a register window; :func:`voice_lead` smooths a chord
sequence by choosing per-degree equave displacements that minimize
log-frequency movement between successive chords. Both work uniformly over
ratio- and cents-based collections (all comparison happens in Hz).
"""

import math
from fractions import Fraction
from typing import List, Optional, Union

from ..pitch import Pitch
from ..pitch.pitch_collections import RelativePitchCollection
from .chord import Voicing

__all__ = ['fold', 'voice_lead']

# Tolerance in equave-exponent space (~0.1 cents for an octave equave):
# Pitch frequencies are rounded, so boundary placements need slack.
_EPS = 1e-4


def _check_collection(collection, fn_name):
    from ..scales.scale import Scale
    if isinstance(collection, Scale):
        raise TypeError(
            f"{fn_name} does not accept a Scale (scale degrees are a gamut, "
            f"not a sonority); build a Chord or Voicing from its pitches first"
        )
    if not isinstance(collection, RelativePitchCollection):
        raise TypeError(
            f"{fn_name} requires a relative collection (Chord, Voicing, or "
            f"RelativePitchCollection); got {type(collection).__name__}"
        )


def _resolve_bound(bound, reference: Pitch, name: str) -> Optional[float]:
    """Resolve a register bound to Hz (relative bounds resolve against *reference*)."""
    from ..types import Frequency, Cent, Ratio
    if bound is None:
        return None
    if isinstance(bound, Pitch):
        return bound.freq
    if isinstance(bound, str):
        return Pitch(bound).freq
    if isinstance(bound, Frequency):
        return float(bound.magnitude)
    if isinstance(bound, Cent):
        return reference.freq * (2.0 ** (float(bound.magnitude) / 1200.0))
    if isinstance(bound, Ratio):
        return reference.freq * float(Fraction(bound.magnitude.item()))
    if isinstance(bound, (int, float)):
        raise TypeError(
            f"Bare number for '{name}' is ambiguous. Use a note name ('G3'), "
            f"a Pitch, frequency(hz), cent(c), or ratio('1/2')."
        )
    raise TypeError(f"Cannot interpret {name}={bound!r} as a register bound")


def _degree_hz(degree, mode: str, ref_hz: float) -> float:
    if mode == "cents":
        return ref_hz * (2.0 ** (float(degree) / 1200.0))
    return ref_hz * float(degree)


def _equave_factor(equave, mode: str) -> float:
    if mode == "cents":
        cents = equave if isinstance(equave, float) else 1200.0
        return 2.0 ** (cents / 1200.0)
    return float(equave)


def _displace(degree, k: int, equave, mode: str):
    if k == 0:
        return degree
    if mode == "cents":
        cents = equave if isinstance(equave, float) else 1200.0
        return float(degree) + k * cents
    ratio = equave if isinstance(equave, Fraction) else Fraction(2, 1)
    return degree * (ratio ** k)


def _clamp_k(hz: float, k: int, eq: float,
             lo: Optional[float], hi: Optional[float]) -> int:
    """Clamp a displacement so ``hz * eq**k`` lands inside ``[lo, hi]``.

    When the window is narrower than one equave and no placement fits, the
    nearest placement (smallest log-distance outside the window) wins.
    """
    log_eq = math.log(eq)
    k_lo = None if lo is None else math.ceil(math.log(lo / hz) / log_eq - _EPS)
    k_hi = None if hi is None else math.floor(math.log(hi / hz) / log_eq + _EPS)
    if k_lo is not None and k_hi is not None:
        if k_lo <= k_hi:
            return min(max(k, k_lo), k_hi)
        below = math.log(lo / (hz * eq ** k_hi))
        above = math.log((hz * eq ** k_lo) / hi)
        return k_hi if below <= above else k_lo
    if k_lo is not None:
        return max(k, k_lo)
    if k_hi is not None:
        return min(k, k_hi)
    return k


def _fold_degrees(collection, lo_hz, hi_hz):
    mode = collection._interval_type_mode
    ref_hz = collection.reference_pitch.freq
    eq = _equave_factor(collection.equave, mode)
    out = []
    for degree in collection._degrees:
        hz = _degree_hz(degree, mode, ref_hz)
        k = _clamp_k(hz, 0, eq, lo_hz, hi_hz)
        out.append(_displace(degree, k, collection.equave, mode))
    return out


def fold(collection, lo=None, hi=None) -> Voicing:
    """
    Octave-displace each degree until its pitch lies within ``[lo, hi]``.

    Displacement is by whole equaves of the collection. If the window is
    narrower than one equave and a degree cannot fit, the placement nearest
    the window is used.

    Parameters
    ----------
    collection : Chord, Voicing, or RelativePitchCollection
        The sonority to fold. ``Scale`` and absolute collections are
        rejected.
    lo, hi : optional
        Register bounds; either may be omitted. Each may be a note name
        (``'G3'``), a :class:`Pitch`, ``frequency(hz)`` (absolute), or
        ``cent(c)`` / ``ratio('1/2')`` (relative to the collection's
        reference pitch). Bare numbers are rejected as ambiguous.

    Returns
    -------
    Voicing
        The folded sonority (out-of-equave degrees are legal in a Voicing).

    Examples
    --------
    >>> fold(Chord(['1/1', '5/4', '3/2'], reference_pitch='C5'), lo='G3', hi='G4')
    """
    _check_collection(collection, 'fold')
    ref = collection.reference_pitch
    lo_hz = _resolve_bound(lo, ref, 'lo')
    hi_hz = _resolve_bound(hi, ref, 'hi')
    if lo_hz is not None and hi_hz is not None and lo_hz > hi_hz:
        raise ValueError(f"lo bound ({lo_hz:.2f} Hz) is above hi bound ({hi_hz:.2f} Hz)")
    degrees = _fold_degrees(collection, lo_hz, hi_hz)
    return Voicing(degrees, collection._interval_type_mode,
                   collection.equave, ref)


def voice_lead(chords, lo=None, hi=None) -> List[Voicing]:
    """
    Voice-lead a chord sequence with minimal per-voice movement.

    The first chord keeps its own voicing (folded into bounds if given).
    Each subsequent chord's degrees are equave-displaced to sit as close as
    possible (in log-frequency) to the previous sounded voicing — voices
    are matched by sorted order, greedily when cardinalities differ — and
    then folded into the bounds.

    Mixed ratio- and cents-based sequences work uniformly: comparison
    happens in Hz and displacement happens on each chord's own degrees.

    Parameters
    ----------
    chords : iterable of Chord, Voicing, or RelativePitchCollection
        The progression (a :class:`ChordSequence` works directly).
    lo, hi : optional
        Register bounds, as in :func:`fold`.

    Returns
    -------
    list of Voicing
    """
    chords = list(chords)
    if not chords:
        return []

    result = [fold(chords[0], lo, hi)]
    prev_hz = sorted(p.freq for p in result[0].pitches)

    for collection in chords[1:]:
        _check_collection(collection, 'voice_lead')
        ref = collection.reference_pitch
        lo_hz = _resolve_bound(lo, ref, 'lo')
        hi_hz = _resolve_bound(hi, ref, 'hi')
        mode = collection._interval_type_mode
        ref_hz = ref.freq
        eq = _equave_factor(collection.equave, mode)
        log_eq = math.log(eq)

        new_degrees = []
        for degree in collection._degrees:
            hz = _degree_hz(degree, mode, ref_hz)
            best_k, best_dist = 0, None
            for target in prev_hz:
                base = round(math.log(target / hz) / log_eq)
                for k in (base - 1, base, base + 1):
                    dist = abs(math.log((hz * eq ** k) / target))
                    if best_dist is None or dist < best_dist:
                        best_k, best_dist = k, dist
            k = _clamp_k(hz, best_k, eq, lo_hz, hi_hz)
            new_degrees.append(_displace(degree, k, collection.equave, mode))

        voicing = Voicing(new_degrees, mode, collection.equave, ref)
        result.append(voicing)
        sounded = sorted(p.freq for p in voicing.pitches)
        if sounded:
            prev_hz = sounded

    return result
