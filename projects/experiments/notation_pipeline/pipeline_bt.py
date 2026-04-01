"""BT pipeline: TemporalBlock → NotatedScore → SVG.

Multi-staff horizontal layout uses OpenMusic ``space-packet`` (scoretools.lisp)
with a global time-ordered walk in absolute seconds (Klotho real onsets).
A post-layout time→x BPF with OM-style sentinel supports barline interpolation
(``get-x-pos`` analog). See ``spacing/om_packet.py``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace as dc_replace
from fractions import Fraction

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock

from .models import NotatedMeasure, NotatedSystem, NotatedScore
from .pipeline import notate
from .pipeline_uts import notate_uts, should_show_time_sig
from .spacing.modes import compute_min_space
from .spacing.om_packet import (
    DEFAULT_NEXTDUR_MS,
    DEFAULT_OM_SIZE,
    build_timebpf_with_sentinel,
    interp_timebpf,
    space_packet,
    space_size_offset_measure,
    space_size_offset_note,
)


BAR_X = 44.0


def notate_bt(
    bt: TemporalBlock,
    spacing_mode: str = 'hybrid',
    max_dots: int = 2,
    scale: float = 400.0,
    left_margin: float = 62.0,
    barlines: bool = True,
    time_scale: float = 80.0,
    min_event_dx: float = 20.0,
    om_size: float = DEFAULT_OM_SIZE,
) -> NotatedScore:
    """Convert a TemporalBlock into a multi-staff NotatedScore.

    Horizontal positions for simultaneous events follow OM ``space-packet``
    (column maxima across all staves). Per-row ``spacing_mode`` only affects
    discarded pre-layout pass; final x is always OM packet-based for BT.

    Parameters
    ----------
    time_scale, min_event_dx
        Retained for API compatibility; BT layout uses ``om_size`` and OM
        ``ryhtm2pixels`` instead.
    """
    row_systems: list[NotatedSystem] = []
    for row in bt.rows:
        if isinstance(row, TemporalUnitSequence):
            system = notate_uts(
                row, spacing_mode=spacing_mode, max_dots=max_dots,
                scale=scale, left_margin=left_margin, barlines=barlines,
            )
            row_systems.append(system)
        elif isinstance(row, TemporalUnit):
            m = notate(
                row.rt, spacing_mode=spacing_mode, max_dots=max_dots,
                scale=scale, left_margin=left_margin, barlines=barlines,
                tempo_beat=row.beat, tempo_bpm=row.bpm,
            )
            row_systems.append(NotatedSystem(measures=[m]))
        else:
            raise NotImplementedError(
                f"Nested TemporalBlocks not yet supported (got {type(row).__name__})"
            )

    all_times = _collect_all_times(bt)
    if not all_times:
        return NotatedScore(rows=row_systems)

    measure_left_x = _apply_om_packet_layout_bt(bt, row_systems, om_size=om_size)

    timebpf = _build_event_timebpf(bt, row_systems)

    for row_idx, (row, system) in enumerate(zip(bt.rows, row_systems)):
        _recompute_barlines(row_idx, row, system, timebpf, measure_left_x)

    _align_shared_barlines(bt, row_systems)
    _chain_adjacent_measure_barlines(row_systems)

    return NotatedScore(rows=row_systems)


def _time_key(t: float) -> float:
    return round(t, 9)


def _apply_om_packet_layout_bt(
    bt: TemporalBlock,
    row_systems: list[NotatedSystem],
    om_size: float,
) -> dict[tuple[int, int], float]:
    measure_left_x: dict[tuple[int, int], float] = {}
    all_times: set[float] = set()
    for row_idx, row in enumerate(bt.rows):
        ut_list = _row_to_ut_list(row)
        system = row_systems[row_idx]
        for meas_idx, ut in enumerate(ut_list):
            if meas_idx < len(system.measures):
                all_times.add(_time_key(ut.offset))
        for meas_idx, meas in enumerate(system.measures):
            if meas_idx >= len(ut_list):
                continue
            ut = ut_list[meas_idx]
            for ev in meas.events:
                at = _event_abs_time_in_ut(ev, ut)
                if at is not None:
                    all_times.add(_time_key(at))

    sorted_times = sorted(all_times)
    if not sorted_times:
        return measure_left_x

    count = BAR_X

    for i, t in enumerate(sorted_times):
        items = _packet_items_at_time(bt, row_systems, t, om_size)
        if not items:
            continue
        if i + 1 < len(sorted_times):
            nextdur_ms = max(1.0, (sorted_times[i + 1] - t) * 1000.0)
        else:
            nextdur_ms = DEFAULT_NEXTDUR_MS
        count, pos = space_packet(items, count, nextdur_ms, om_size)
        for key, x in pos.items():
            if key[0] == "m":
                _, r, mi = key
                measure_left_x[(r, mi)] = x
            elif key[0] == "n":
                _, r, mi, ei = key
                meas = row_systems[r].measures[mi]
                ev = meas.events[ei]
                meas.events[ei] = dc_replace(ev, x=x)
    return measure_left_x


def _packet_items_at_time(
    bt: TemporalBlock,
    row_systems: list[NotatedSystem],
    t: float,
    om_size: float,
) -> list[dict]:
    items: list[dict] = []
    tol = 1e-5

    for row_idx, row in enumerate(bt.rows):
        ut_list = _row_to_ut_list(row)
        system = row_systems[row_idx]
        for meas_idx, ut in enumerate(ut_list):
            if meas_idx >= len(system.measures):
                continue
            meas = system.measures[meas_idx]
            if abs(ut.offset - t) < tol:
                if not meas.show_barlines:
                    continue
                prev_ts = None
                if meas_idx > 0:
                    prev_ts = system.measures[meas_idx - 1].time_signature
                show_ts = bool(
                    meas.time_signature
                    and should_show_time_sig(meas.time_signature, prev_ts)
                )
                metric_changed = meas_idx > 0 and (
                    ut.tempus != ut_list[meas_idx - 1].tempus
                )
                budget = space_size_offset_measure(
                    first_of_group=(meas_idx == 0),
                    show_time_sig=show_ts,
                    first_measure_of_voice=(meas_idx == 0),
                    metric_changed=metric_changed,
                    size=om_size,
                )
                items.append(
                    {"kind": "measure", "budget": budget, "id": ("m", row_idx, meas_idx)}
                )

            for ev_idx, ev in enumerate(meas.events):
                at = _event_abs_time_in_ut(ev, ut)
                if at is not None and abs(at - t) < tol:
                    b = space_size_offset_note(ev, om_size, compute_min_space)
                    items.append(
                        {
                            "kind": "note",
                            "budget": b,
                            "id": ("n", row_idx, meas_idx, ev_idx),
                        }
                    )
    return items


def _build_event_timebpf(
    bt: TemporalBlock,
    row_systems: list[NotatedSystem],
) -> dict[float, float]:
    merged: dict[float, float] = defaultdict(float)
    for row_idx, row in enumerate(bt.rows):
        ut_list = _row_to_ut_list(row)
        for meas_idx, meas in enumerate(row_systems[row_idx].measures):
            if meas_idx >= len(ut_list):
                continue
            ut = ut_list[meas_idx]
            for ev in meas.events:
                at = _event_abs_time_in_ut(ev, ut)
                if at is not None:
                    k = _time_key(at)
                    merged[k] = max(merged[k], ev.x)
    if not merged:
        return {}
    pairs = [(tk, merged[tk]) for tk in sorted(merged)]
    return build_timebpf_with_sentinel(pairs)


def _chain_adjacent_measure_barlines(row_systems: list[NotatedSystem]) -> None:
    for system in row_systems:
        prev_right: float | None = None
        for m in system.measures:
            if not m.barline_x_positions:
                continue
            if prev_right is not None:
                m.barline_x_positions[0] = prev_right
            prev_right = m.barline_x_positions[-1]


def _align_shared_barlines(bt: TemporalBlock, row_systems: list[NotatedSystem]):
    end_time_groups: dict[float, list[tuple[int, int]]] = defaultdict(list)
    for row_idx, (row, system) in enumerate(zip(bt.rows, row_systems)):
        ut_list = _row_to_ut_list(row)
        for meas_idx, ut in enumerate(ut_list):
            if meas_idx < len(system.measures):
                end_t = round(ut.offset + ut.duration, 10)
                end_time_groups[end_t].append((row_idx, meas_idx))

    for end_t, members in end_time_groups.items():
        if len(members) < 2:
            continue
        max_end_x = 0.0
        for row_idx, meas_idx in members:
            m = row_systems[row_idx].measures[meas_idx]
            if m.barline_x_positions:
                max_end_x = max(max_end_x, m.barline_x_positions[-1])
        for row_idx, meas_idx in members:
            m = row_systems[row_idx].measures[meas_idx]
            if m.barline_x_positions:
                m.barline_x_positions[-1] = max_end_x


def _collect_all_times(bt: TemporalBlock) -> list[float]:
    times = set()
    for row in bt.rows:
        times.update(_get_real_onsets(row))
    return sorted(times)


def _get_real_onsets(row) -> list[float]:
    if isinstance(row, TemporalUnitSequence):
        onsets = []
        for ut in row.seq:
            onsets.extend(ut.onsets)
        return onsets
    elif isinstance(row, TemporalUnit):
        return list(row.onsets)
    return []


def _row_to_ut_list(row) -> list[TemporalUnit]:
    if isinstance(row, TemporalUnitSequence):
        result = []
        for item in row.seq:
            if isinstance(item, TemporalUnitSequence):
                result.extend(_row_to_ut_list(item))
            elif isinstance(item, TemporalUnit):
                result.append(item)
        return result
    elif isinstance(row, TemporalUnit):
        return [row]
    return []


def _event_abs_time_in_ut(ev, ut: TemporalUnit) -> float | None:
    """Absolute performance time of ``ev`` using its parent UT (metric onset is UT-local)."""
    from klotho.chronos.utils.beat import beat_duration

    local_onset = Fraction(ev.onset)
    return float(
        beat_duration(
            ratio=local_onset,
            bpm=ut.bpm,
            beat_ratio=Fraction(ut.beat),
        )
        + ut.offset
    )


def _recompute_barlines(
    row_idx: int,
    row,
    system: NotatedSystem,
    timebpf: dict[float, float],
    measure_left_x: dict[tuple[int, int], float],
):
    from .render.svg_renderer import END_PAD

    ut_list = _row_to_ut_list(row)
    prev_right: float | None = None

    for i, measure in enumerate(system.measures):
        if not measure.show_barlines:
            measure.barline_x_positions = []
            continue

        if i >= len(ut_list):
            measure.barline_x_positions = []
            continue

        ut = ut_list[i]
        start_time = ut.offset
        anchor = measure_left_x.get((row_idx, i))
        if i == 0:
            start_x = (
                anchor
                if anchor is not None
                else interp_timebpf(start_time, timebpf)
            )
        else:
            if prev_right is not None:
                start_x = prev_right
            else:
                start_x = (
                    anchor
                    if anchor is not None
                    else interp_timebpf(start_time, timebpf)
                )

        if measure.events:
            end_x = max(ev.x for ev in measure.events) + END_PAD
        else:
            end_x = interp_timebpf(ut.offset + ut.duration, timebpf)

        if ut.rt.span > 1:
            meas_dur_s = ut.duration / ut.rt.span
            barline_xs = [start_x]
            for bar_i in range(1, ut.rt.span):
                bar_time = start_time + meas_dur_s * bar_i
                bx = interp_timebpf(bar_time, timebpf)
                barline_xs.append(max(barline_xs[-1], bx))
            barline_xs.append(end_x)
            measure.barline_x_positions = barline_xs
        else:
            measure.barline_x_positions = [start_x, end_x]

        prev_right = measure.barline_x_positions[-1]
