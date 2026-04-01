"""Tie-splitting: decompose non-engravable durations into tied engravable components."""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from .duration import classify_duration, largest_engravable_leq, ENGRAVABLE_DURATIONS


# ---------------------------------------------------------------------------
# OM-style proportion decomposition (port of only-one-point / before&after-bin)
# ---------------------------------------------------------------------------

def _bracketing_powers(n: int) -> tuple[int, int]:
    """Return (lower, upper) powers of 2 that bracket *n*.

    Port of OM ``before&after-bin`` (rythtools.lisp:144).
    """
    exp = 0
    while n >= 2 ** exp:
        exp += 1
    return (2 ** (exp - 1), 2 ** exp)


_FAST_ENGRAVABLE = frozenset({0, 1, 2, 3, 4, 6, 8, 12, 16, 32})


def split_proportion(n: int) -> list[int]:
    """Decompose integer proportion *n* into engravable components.

    Port of OM ``only-one-point`` (rythtools.lisp:325).  Returns a list of
    positive integers that sum to *n*, each representable as a single
    notehead (power-of-2, dotted, or double-dotted).
    """
    if n <= 0:
        return [n] if n == 0 else []
    if n in _FAST_ENGRAVABLE:
        return [n]
    bef = _bracketing_powers(n)[0]
    if n == bef or n == bef * 3 // 2 or n == bef * 7 // 4:
        return [n]
    if n > bef * 3 // 2:
        head = bef + bef // 2
        return [head] + split_proportion(n - head)
    return [bef] + split_proportion(n - bef)


def split_proportion_fraction(dur: Fraction) -> list[Fraction]:
    """Apply :func:`split_proportion` to a :class:`Fraction` duration.

    Expresses *dur* as p/q, splits p, and maps back.
    """
    if dur <= 0:
        return [dur] if dur == 0 else []
    p, q = dur.numerator, dur.denominator
    return [Fraction(part, q) for part in split_proportion(p)]


def split_duration(dur: Fraction, max_dots: int = 2) -> list[Fraction]:
    """Greedy power-of-two decomposition of a duration.

    Splits a positive rational duration into a minimal list of engravable
    durations (each representable as a single note, possibly dotted).

    Parameters
    ----------
    dur : Fraction
        Positive duration in whole notes.
    max_dots : int
        Maximum dots allowed per note.

    Returns
    -------
    list[Fraction]
        Sequence of engravable durations that sum to dur.
    """
    if dur <= 0:
        return [dur] if dur == 0 else []

    result = []
    remaining = dur

    while remaining > 0:
        best = largest_engravable_leq(remaining, max_dots=max_dots)
        if best is None:
            # Duration is smaller than any engravable value — shouldn't happen
            # in well-formed input, but handle gracefully
            result.append(remaining)
            break
        result.append(best)
        remaining -= best

    return result


def compute_beat_boundaries(meas) -> list[Fraction]:
    """Compute beat boundary positions within a measure.

    Parameters
    ----------
    meas : Meas
        Time signature (e.g., Meas(4,4), Meas(6,8)).

    Returns
    -------
    list[Fraction]
        Sorted positions (in whole notes) of beat boundaries within the measure.
        Does not include 0 or the measure end.
    """
    num = meas.numerator
    denom = meas.denominator
    meas_dur = Fraction(num, denom)

    # Detect compound meters: numerator divisible by 3, >= 6
    if num >= 6 and num % 3 == 0:
        # Compound meter: beats are dotted groups
        # e.g., 6/8 -> 2 beats of 3/8 each; 9/8 -> 3 beats of 3/8
        beat_count = num // 3
        beat_dur = Fraction(3, denom)
    else:
        # Simple meter: one beat per numerator unit
        beat_count = num
        beat_dur = Fraction(1, denom)

    boundaries = []
    for i in range(1, beat_count):
        boundaries.append(beat_dur * i)

    return boundaries


def measure_split_points_global(
    onset: Fraction,
    dur: Fraction,
    meas_dur: Fraction,
) -> list[Fraction]:
    if dur <= 0 or meas_dur <= 0:
        return []
    end = onset + dur
    pts: list[Fraction] = []
    pt = (onset // meas_dur + 1) * meas_dur
    while pt < end:
        pts.append(pt)
        pt += meas_dur
    return pts


def global_beat_split_points(
    onset: Fraction,
    dur: Fraction,
    meas,
    meas_dur: Fraction,
) -> list[Fraction]:
    if dur <= 0:
        return []
    end = onset + dur
    local_b = compute_beat_boundaries(meas)
    pts: list[Fraction] = []
    m = onset // meas_dur
    while m * meas_dur < end:
        base = m * meas_dur
        for b in local_b:
            g = base + b
            if onset < g < end:
                pts.append(g)
        m += 1
    return pts


def _merged_interior_split_points(
    onset: Fraction,
    dur: Fraction,
    meas,
    meas_dur: Fraction,
) -> list[Fraction]:
    end = onset + dur
    s: set[Fraction] = set()
    for p in measure_split_points_global(onset, dur, meas_dur):
        s.add(p)
    for p in global_beat_split_points(onset, dur, meas, meas_dur):
        s.add(p)
    return sorted(x for x in s if onset < x < end)


def _segments_from_points(
    onset: Fraction,
    dur: Fraction,
    points_sorted: list[Fraction],
) -> list[tuple[Fraction, Fraction]]:
    end = onset + dur
    if not points_sorted:
        return [(onset, dur)]
    out: list[tuple[Fraction, Fraction]] = []
    cur = onset
    for p in points_sorted:
        if cur < p:
            out.append((cur, p - cur))
        cur = p
    if cur < end:
        out.append((cur, end - cur))
    return out


def decompose_note_durations(
    onset: Fraction,
    dur: Fraction,
    meas,
    max_dots: int = 2,
    *,
    split_measures: bool = False,
) -> list[Fraction]:
    if dur <= 0:
        return [dur] if dur == 0 else []

    meas_dur = Fraction(meas.numerator, meas.denominator)
    onset_m = onset % meas_dur
    if not split_measures and onset_m + dur > meas_dur:
        split_measures = True
    if not split_measures:
        return split_at_boundaries(dur, onset_m, meas, max_dots=max_dots)

    pts = _merged_interior_split_points(onset, dur, meas, meas_dur)
    segs = _segments_from_points(onset, dur, pts)
    result: list[Fraction] = []
    for s0, sd in segs:
        loc = s0 % meas_dur
        result.extend(split_at_boundaries(sd, loc, meas, max_dots=max_dots))
    return result


def measure_segments_only(
    onset: Fraction,
    dur: Fraction,
    meas_dur: Fraction,
) -> list[tuple[Fraction, Fraction]]:
    pts = measure_split_points_global(onset, dur, meas_dur)
    return _segments_from_points(onset, dur, pts)


def split_at_boundaries(
    dur: Fraction,
    onset: Fraction,
    meas,
    max_dots: int = 2,
) -> list[Fraction]:
    """Split a duration at beat boundaries, then decompose each segment.

    Parameters
    ----------
    dur : Fraction
        Positive duration in whole notes.
    onset : Fraction
        Metric onset in whole notes (global across span or local to one measure).
    meas : Meas
        Time signature.
    max_dots : int
        Maximum dots allowed.

    Returns
    -------
    list[Fraction]
        Sequence of engravable durations that sum to dur.
    """
    if dur <= 0:
        return [dur] if dur == 0 else []

    meas_dur = Fraction(meas.numerator, meas.denominator)
    onset_m = onset % meas_dur
    if onset_m + dur > meas_dur:
        return decompose_note_durations(
            onset, dur, meas, max_dots=max_dots, split_measures=True,
        )

    boundaries = compute_beat_boundaries(meas)
    note_end = onset_m + dur

    split_points = [b for b in boundaries if onset_m < b < note_end]

    if not split_points:
        return split_duration(dur, max_dots=max_dots)

    segments = []
    current_start = onset_m
    for boundary in split_points:
        seg_dur = boundary - current_start
        if seg_dur > 0:
            segments.append(seg_dur)
        current_start = boundary
    final = note_end - current_start
    if final > 0:
        segments.append(final)

    result = []
    for seg in segments:
        result.extend(split_duration(seg, max_dots=max_dots))

    return result
