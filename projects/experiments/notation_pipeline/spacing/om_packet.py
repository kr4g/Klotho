"""OpenMusic-style horizontal spacing (scoretools.lisp).

Primary OM references (OpenMusic ``musicproject`` tree):

- ``scoretools.lisp`` ``space-packet`` (~2453-2467), ``space-size&offset`` (~2413-2446),
  ``ryhtm2pixels`` / ``*factor-spacing*`` (~2491-2494), ``get-chiffrage-space`` (~1511-1514).
- ``scoreeditors.lisp`` ``timebpf`` sentinel (~6706-6707) — mirrored by
  ``build_timebpf_with_sentinel``.

OM ``size`` is the staff reference pixel size (historically ~24); we default to 24.0
to match the notation_pipeline OM reference in NEXT_STEPS.md. SMuFL note bodies use
``compute_min_space`` from modes.py for the fourth column (notehead width analog).
"""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Any, Callable

from .modes import compute_min_space

OM_FACTOR_SPACING = 1.5

DEFAULT_OM_SIZE = 24.0

SENTINEL_TIME_EXTRA_S = 1.0
SENTINEL_X_EXTRA_PX = 20.0

DEFAULT_NEXTDUR_MS = 2000.0

OM_END_BARLINE_GAP = 14.0


def ryhtm2pixels(ms: float) -> float:
    """OM ``ryhtm2pixels`` (scoretools.lisp). ``ms`` = duration to next event in ms."""
    if ms <= 0:
        ms = DEFAULT_NEXTDUR_MS
    return max(0.25, OM_FACTOR_SPACING ** (math.log(ms / 1000.0, 2)))


def round_size_2(size: float) -> float:
    return round(size / 2.0)


def round_size_4(size: float) -> float:
    return round(size / 4.0)


def get_chiffrage_space_px(
    show_time_sig: bool,
    first_measure_of_voice: bool,
    metric_changed: bool,
    size: float,
) -> float:
    """OM ``get-chiffrage-space`` / ``mesure-space`` (scoretools.lisp ~1511-1514)."""
    if show_time_sig or first_measure_of_voice:
        return float(size)
    return float(size) if metric_changed else float(round(size / 1.5))


def space_size_offset_measure(
    *,
    first_of_group: bool,
    show_time_sig: bool,
    first_measure_of_voice: bool,
    metric_changed: bool,
    size: float,
) -> tuple[float, float, float, float]:
    """OM ``space-size&offset`` for grap-measure (scoretools.lisp ~2413-2414)."""
    barline_gap = 0.0 if first_of_group else round_size_2(size)
    ts_space = get_chiffrage_space_px(
        show_time_sig, first_measure_of_voice, metric_changed, size
    )
    body = round_size_2(size)
    return (barline_gap, ts_space, 0.0, body)


def space_size_offset_note(event: Any, size: float, body_fn: Callable[[Any], float]) -> tuple[float, float, float, float]:
    """OM ``space-size&offset`` for a note/rest (fourth column = body width)."""
    body = body_fn(event)
    return (0.0, 0.0, 0.0, float(body))


def space_packet(
    items: list[dict],
    count: float,
    nextdur_ms: float,
    size: float,
) -> tuple[float, dict[Any, float]]:
    """OM ``space-packet`` (scoretools.lisp ~2453-2467).

    Each item dict must have:
      - ``kind``: ``\"measure\"`` | ``\"note\"``
      - ``budget``: 4-tuple (barline, ts, grace, body)
      - ``id``: hashable key for output positions

    Returns (new_count, id -> x main-point for horizontal placement).
    """
    if not items:
        adv = max(round_size_4(size), size * ryhtm2pixels(nextdur_ms))
        return count + adv, {}

    measures_first = sorted(items, key=lambda it: (0 if it["kind"] == "measure" else 1))

    max_clef = max_m = max_grace = 0.0
    max_pixelsize = round_size_4(size)
    for it in measures_first:
        b = it["budget"]
        max_clef = max(max_clef, b[0])
        max_m = max(max_m, b[1])
        max_grace = max(max_grace, b[2])
        max_pixelsize = max(max_pixelsize, b[3])

    positions: dict[Any, float] = {}
    for it in measures_first:
        if it["kind"] == "measure":
            positions[it["id"]] = count + max_clef
        else:
            positions[it["id"]] = count + max_clef + max_m + max_grace

    advance = max(
        max_pixelsize,
        round_size_4(size),
        size * ryhtm2pixels(nextdur_ms),
    )
    new_count = count + max_clef + max_m + max_grace + advance
    return new_count, positions


def metric_onset_to_seconds(
    metric_onset: Fraction,
    bpm: float,
    beat_ratio: Fraction,
) -> float:
    from klotho.chronos.utils.beat import beat_duration

    return float(
        beat_duration(ratio=metric_onset, bpm=bpm, beat_ratio=beat_ratio)
    )


def build_timebpf_with_sentinel(
    time_x_pairs: list[tuple[float, float]],
) -> dict[float, float]:
    """OM-style BPF anchors plus sentinel (scoreeditors.lisp ~6706-6707).

    Pairs are (time_s, x); duplicate times keep the last x. Appends
    (last_t + SENTINEL_TIME_EXTRA_S, last_x + SENTINEL_X_EXTRA_PX).
    """
    if not time_x_pairs:
        return {}
    merged: dict[float, float] = {}
    for t, x in sorted(time_x_pairs, key=lambda p: p[0]):
        merged[round(t, 9)] = x
    times = sorted(merged.keys())
    if not times:
        return {}
    last_t, last_x = times[-1], merged[times[-1]]
    merged[round(last_t + SENTINEL_TIME_EXTRA_S, 9)] = last_x + SENTINEL_X_EXTRA_PX
    return merged


def layout_single_measure_events_om(
    events: list[Any],
    *,
    bpm: float,
    beat_ratio: Fraction,
    barlines: bool,
    show_time_sig: bool,
    first_of_group: bool,
    first_measure_of_voice: bool,
    metric_changed: bool,
    om_size: float,
    initial_count: float,
) -> tuple[list[Any], float]:
    """OM packet walk for one staff, one measure; metric onsets → seconds."""
    if not events and not barlines:
        return events, initial_count

    sec_times: list[float] = []
    for ev in events:
        sec_times.append(metric_onset_to_seconds(Fraction(ev.onset), bpm, beat_ratio))

    time_set = {round(t, 9) for t in sec_times}
    if barlines:
        time_set.add(0.0)
    sorted_t = sorted(time_set)

    by_t: dict[float, list[int]] = {}
    for i, st in enumerate(sec_times):
        k = round(st, 9)
        by_t.setdefault(k, []).append(i)

    from dataclasses import replace

    out = list(events)
    count = initial_count

    for i, t in enumerate(sorted_t):
        pack_items: list[dict] = []
        if barlines and abs(t - 0.0) < 1e-9:
            budget = space_size_offset_measure(
                first_of_group=first_of_group,
                show_time_sig=show_time_sig,
                first_measure_of_voice=first_measure_of_voice,
                metric_changed=metric_changed,
                size=om_size,
            )
            pack_items.append({"kind": "measure", "budget": budget, "id": ("meas",)})

        for ev_i in by_t.get(round(t, 9), []):
            b = space_size_offset_note(events[ev_i], om_size, compute_min_space)
            pack_items.append({"kind": "note", "budget": b, "id": ("n", ev_i)})

        if not pack_items:
            continue

        if i + 1 < len(sorted_t):
            nextdur_ms = max(1.0, (sorted_t[i + 1] - t) * 1000.0)
        else:
            nextdur_ms = DEFAULT_NEXTDUR_MS

        count, pos = space_packet(pack_items, count, nextdur_ms, om_size)
        for key, x in pos.items():
            if key[0] == "n":
                ev_i = key[1]
                out[ev_i] = replace(events[ev_i], x=x)

    return out, count


def space_with_barlines_om(
    events: list[Any],
    barline_onsets: list,
    meas: Any,
    *,
    bpm: float,
    beat_ratio: Fraction,
    om_size: float = DEFAULT_OM_SIZE,
) -> tuple[list[Any], list[float]]:
    """Multi-bar single staff: OM packet per measure; barlines after END_PAD."""
    from dataclasses import replace

    from .modes import BAR_X

    meas_dur = Fraction(meas.numerator, meas.denominator)
    n_measures = len(barline_onsets) + 1

    measure_groups: list[list[int]] = [[] for _ in range(n_measures)]
    for i, ev in enumerate(events):
        onset = Fraction(ev.onset)
        meas_idx = min(int(onset / meas_dur), n_measures - 1)
        measure_groups[meas_idx].append(i)

    result = list(events)
    barline_xs = [BAR_X]
    cursor = BAR_X

    for m in range(n_measures):
        indices = measure_groups[m]
        if not indices:
            cursor += float(meas_dur) * (16.0 * om_size / DEFAULT_OM_SIZE) + OM_END_BARLINE_GAP
            barline_xs.append(cursor)
            continue

        local_events = []
        for idx in indices:
            ev = events[idx]
            local_onset = Fraction(ev.onset) - meas_dur * m
            local_events.append(replace(ev, onset=local_onset))

        spaced, _ = layout_single_measure_events_om(
            local_events,
            bpm=bpm,
            beat_ratio=beat_ratio,
            barlines=True,
            show_time_sig=(m == 0),
            first_of_group=(m == 0),
            first_measure_of_voice=(m == 0),
            metric_changed=False,
            om_size=om_size,
            initial_count=cursor,
        )

        for k, idx in enumerate(indices):
            result[idx] = replace(events[idx], x=spaced[k].x)

        last_x = max(s.x for s in spaced) if spaced else cursor
        cursor = last_x + OM_END_BARLINE_GAP
        barline_xs.append(cursor)

    return result, barline_xs


def interp_timebpf(t: float, timebpf: dict[float, float]) -> float:
    from bisect import bisect_right

    times = sorted(timebpf.keys())
    if not times:
        return 0.0
    xs = [timebpf[tt] for tt in times]
    if t <= times[0]:
        return xs[0]
    if t >= times[-1]:
        t0, x0 = times[-1], xs[-1]
        if len(times) >= 2:
            t_prev, x_prev = times[-2], xs[-2]
            if t0 > t_prev:
                slope = (x0 - x_prev) / (t0 - t_prev)
            else:
                slope = DEFAULT_OM_SIZE
        else:
            slope = DEFAULT_OM_SIZE
        return x0 + (t - t0) * slope
    i = bisect_right(times, t) - 1
    if i >= len(times) - 1:
        return xs[-1]
    t0, t1 = times[i], times[i + 1]
    x0, x1 = xs[i], xs[i + 1]
    if t1 == t0:
        return x0
    return x0 + (t - t0) / (t1 - t0) * (x1 - x0)
