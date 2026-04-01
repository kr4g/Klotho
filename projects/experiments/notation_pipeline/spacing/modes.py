"""Spacing algorithms: proportional, traditional, and hybrid."""

from __future__ import annotations

import math
from fractions import Fraction
from dataclasses import replace

from ..models import EngravingLeaf, NoteType


# Minimum glyph widths in abstract units
NOTEHEAD_WIDTH = 14.0
DOT_WIDTH = 6.0
INTER_NOTE_PADDING = 6.0
STEM_WIDTH = 2.0
REST_WIDTH = 12.0

# Multi-bar barline layout constants
BAR_X = 44.0         # Must match svg_renderer.BAR_X
DEFAULT_BUFFER = 18.0  # Buffer between barline and adjacent note (= NOTE_X0 - BAR_X)


def compute_min_space(event: EngravingLeaf) -> float:
    """Compute minimum horizontal space needed for an event's glyphs."""
    if event.is_rest:
        base = REST_WIDTH
    else:
        base = NOTEHEAD_WIDTH
    if event.dots > 0:
        base += DOT_WIDTH * event.dots
    base += INTER_NOTE_PADDING
    return base


def space_proportional(
    events: list[EngravingLeaf],
    scale: float = 400.0,
    left_margin: float = 60.0,
) -> list[EngravingLeaf]:
    """Proportional spacing: x position directly proportional to onset.

    Parameters
    ----------
    events : list[EngravingLeaf]
        Events to space (must be sorted by onset).
    scale : float
        Abstract units per whole note.
    left_margin : float
        Space reserved for clef/time signature.

    Returns
    -------
    list[EngravingLeaf]
        New events with x positions assigned.
    """
    if not events:
        return []

    result = [
        replace(event, x=left_margin + float(event.onset) * scale)
        for event in events
    ]

    # Enforce minimum distances to prevent glyph collisions
    for i in range(1, len(result)):
        min_x = result[i - 1].x + compute_min_space(result[i - 1])
        if result[i].x < min_x:
            result[i] = replace(result[i], x=min_x)

    return result


def space_traditional(
    events: list[EngravingLeaf],
    base_width: float = 40.0,
    left_margin: float = 60.0,
) -> list[EngravingLeaf]:
    """Traditional spacing: logarithmic compression of durations.

    Spacing follows conventional engraving rules where shorter notes
    get proportionally more space than pure proportional spacing.

    Parameters
    ----------
    events : list[EngravingLeaf]
        Events to space (sorted by onset).
    base_width : float
        Base spacing unit.
    left_margin : float
        Space reserved for clef/time signature.
    """
    if not events:
        return []

    # Find the minimum non-zero duration for log scaling
    non_zero_durs = [float(abs(e.duration)) for e in events if e.duration > 0]
    min_dur = min(non_zero_durs) if non_zero_durs else 0.25

    result = []
    x = left_margin

    for i, event in enumerate(events):
        result.append(replace(event, x=x))

        # Compute space after this event
        dur = float(abs(event.duration))
        if dur > 0:
            # Logarithmic: space = base * (1 + log2(dur / min_dur))
            ratio = dur / min_dur
            space = base_width * (1.0 + max(0, math.log2(ratio)))
        else:
            space = base_width * 0.3  # grace note / zero-duration

        # Enforce minimum
        space = max(space, compute_min_space(event))
        x += space

    return result


def space_hybrid(
    events: list[EngravingLeaf],
    scale: float = 400.0,
    left_margin: float = 60.0,
    min_spacing_factor: float = 1.0,
) -> list[EngravingLeaf]:
    """Legacy hybrid: proportional base plus minimum-distance sweep.

    For engraved output, ``pipeline.notate`` uses ``spacing.om_packet`` when
    ``spacing_mode`` is ``hybrid`` or ``om`` (OpenMusic ``space-packet``).
    This function remains for ``spacing_mode='hybrid'`` in contexts that do
    not go through ``notate`` (tests, comparisons) and for barline-free
    measures where OM packet layout is skipped.

    Parameters
    ----------
    events : list[EngravingLeaf]
        Events to space (sorted by onset).
    scale : float
        Abstract units per whole note (proportional base).
    left_margin : float
        Space reserved for clef/time signature.
    min_spacing_factor : float
        Multiplier on minimum glyph spacing.
    """
    if not events:
        return []

    # Pass 1: proportional placement
    result = [
        replace(event, x=left_margin + float(event.onset) * scale)
        for event in events
    ]

    # Pass 2: enforce minimum distances (left-to-right sweep)
    for i in range(1, len(result)):
        min_x = result[i - 1].x + compute_min_space(result[i - 1]) * min_spacing_factor
        if result[i].x < min_x:
            result[i] = replace(result[i], x=min_x)

    return result


def space_with_barlines(
    events: list[EngravingLeaf],
    barline_onsets: list,
    meas,
    spacing_mode: str = 'hybrid',
    scale: float = 400.0,
    left_margin: float = 62.0,
) -> tuple[list[EngravingLeaf], list[float]]:
    """Per-measure spacing for span > 1 (OM-style).

    Each measure gets independent spacing.  Barlines are placed at a
    fixed small distance after the last note's glyph (following OM's
    approach where the barline sits at the right edge of the last
    note's bounding rectangle), NOT at the proportional end of the
    measure.  A consistent left pad (barline → first note) matches
    the opening barline gap.

    Returns
    -------
    (spaced_events, barline_x_positions)
        barline_x_positions includes start, internal, and end barlines.
    """
    LEFT_PAD = left_margin - BAR_X  # 18 px — barline → first note
    END_PAD = 14.0                  # Fixed gap: last note glyph → barline

    meas_dur = Fraction(meas.numerator, meas.denominator)
    n_measures = len(barline_onsets) + 1

    # Group events by measure (using metric onsets & meas multiples)
    measure_groups: list[list[int]] = [[] for _ in range(n_measures)]
    for i, ev in enumerate(events):
        onset = Fraction(ev.onset)
        meas_idx = min(int(onset / meas_dur), n_measures - 1)
        measure_groups[meas_idx].append(i)

    result = list(events)
    barline_xs = [BAR_X]  # start barline
    cursor = BAR_X        # tracks current barline x

    for m in range(n_measures):
        indices = measure_groups[m]
        note_start = cursor + LEFT_PAD

        if not indices:
            # Empty measure — use proportional width as fallback
            cursor = note_start + float(meas_dur) * scale + END_PAD
            barline_xs.append(cursor)
            continue

        # Create temporary events with measure-local onsets
        local_events = []
        for idx in indices:
            ev = events[idx]
            local_onset = Fraction(ev.onset) - meas_dur * m
            local_events.append(replace(ev, onset=local_onset))

        # Apply per-measure spacing
        if spacing_mode == 'proportional':
            spaced = space_proportional(local_events, scale=scale,
                                        left_margin=note_start)
        elif spacing_mode == 'traditional':
            spaced = space_traditional(local_events, left_margin=note_start)
        else:  # hybrid
            spaced = space_hybrid(local_events, scale=scale,
                                  left_margin=note_start)

        # Transfer x positions back (preserving original onsets)
        for k, idx in enumerate(indices):
            result[idx] = replace(events[idx], x=spaced[k].x)

        # Barline sits right after the last note's glyph (OM convention)
        last_x = max(s.x for s in spaced)
        cursor = last_x + END_PAD
        barline_xs.append(cursor)

    return result, barline_xs
