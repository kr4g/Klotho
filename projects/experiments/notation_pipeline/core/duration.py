"""Duration classification: map Fraction durations to engravable note types."""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from ..models import NoteType, NOTE_TYPE_DURATIONS


# Dot multipliers: dots -> multiplier on base duration
DOT_MULTIPLIERS: dict[int, Fraction] = {
    0: Fraction(1, 1),     # undotted
    1: Fraction(3, 2),     # single dot: base * 3/2
    2: Fraction(7, 4),     # double dot: base * 7/4
}

# Build the full engravable duration table: Fraction -> (NoteType, dots)
ENGRAVABLE_DURATIONS: dict[Fraction, tuple[NoteType, int]] = {}

for note_type, base_dur in NOTE_TYPE_DURATIONS.items():
    for dots, multiplier in DOT_MULTIPLIERS.items():
        dur = base_dur * multiplier
        ENGRAVABLE_DURATIONS[dur] = (note_type, dots)

# Sorted from largest to smallest for greedy decomposition
ENGRAVABLE_SORTED: list[Fraction] = sorted(ENGRAVABLE_DURATIONS.keys(), reverse=True)


def classify_duration(
    dur: Fraction,
    max_dots: int = 2,
    tuplet_scale: Optional[Fraction] = None,
) -> Optional[tuple[NoteType, int]]:
    """Classify a duration as an engravable note type.

    Parameters
    ----------
    dur : Fraction
        Positive duration in whole notes.
    max_dots : int
        Maximum number of dots allowed (0, 1, or 2).
    tuplet_scale : Fraction, optional
        If inside a tuplet, the scaling factor (normal/actual).
        The "notated duration" is dur / tuplet_scale.

    Returns
    -------
    (NoteType, dots) if the duration is directly engravable, else None.
    """
    dur = abs(dur)
    if dur == 0:
        return None

    # Inside a tuplet, adjust to the notated duration
    if tuplet_scale is not None and tuplet_scale != 0:
        dur = dur / tuplet_scale

    result = ENGRAVABLE_DURATIONS.get(dur)
    if result is not None:
        note_type, dots = result
        if dots <= max_dots:
            return result
    return None


def beam_count(note_type: NoteType) -> int:
    """Return the number of beams/flags for a note type.

    0 for whole/half/quarter, 1 for eighth, 2 for 16th, etc.
    """
    beam_map = {
        NoteType.WHOLE:   0,
        NoteType.HALF:    0,
        NoteType.QUARTER: 0,
        NoteType.EIGHTH:  1,
        NoteType.N16TH:   2,
        NoteType.N32ND:   3,
        NoteType.N64TH:   4,
        NoteType.N128TH:  5,
    }
    return beam_map.get(note_type, 0)


def largest_engravable_leq(dur: Fraction, max_dots: int = 2) -> Optional[Fraction]:
    """Find the largest engravable duration <= dur.

    Used by the greedy tie-splitting algorithm.
    """
    dur = abs(dur)
    for candidate in ENGRAVABLE_SORTED:
        _, dots = ENGRAVABLE_DURATIONS[candidate]
        if dots <= max_dots and candidate <= dur:
            return candidate
    return None
