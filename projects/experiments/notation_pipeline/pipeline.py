"""Notation pipeline: RhythmTree → NotatedMeasure → SVG."""

from __future__ import annotations

from fractions import Fraction
from dataclasses import replace
from typing import Optional

from .models import (
    EngravingLeaf, TupletBracket, BeamGroup, NotatedMeasure, NoteType,
)
from .core.duration import classify_duration, beam_count
from .core.tie_split import (
    decompose_note_durations,
    measure_segments_only,
    measure_split_points_global,
    split_at_boundaries,
    split_duration,
    split_proportion_fraction,
)
from .core.tuplet import collect_tuplets, get_tuplet_scale_for_leaf
from .core.beam import assign_beams
from .spacing.modes import BAR_X, space_hybrid, space_proportional, space_traditional, space_with_barlines
from .spacing.om_packet import (
    DEFAULT_OM_SIZE,
    layout_single_measure_events_om,
    space_with_barlines_om,
)


def notate(
    rt,
    spacing_mode: str = 'hybrid',
    max_dots: int = 2,
    scale: float = 400.0,
    left_margin: float = 62.0,
    barlines: bool = True,
    tempo_beat=None,
    tempo_bpm=None,
    *,
    om_first_of_group: Optional[bool] = None,
    om_first_measure_of_voice: Optional[bool] = None,
    om_show_time_sig: Optional[bool] = None,
    om_metric_changed: Optional[bool] = None,
) -> NotatedMeasure:
    """Convert a RhythmTree into a fully annotated NotatedMeasure.

    When ``spacing_mode`` is ``hybrid`` or ``om`` and barlines are enabled, horizontal
    spacing uses OpenMusic ``space-packet`` (``spacing.om_packet``), not legacy
    ``space_hybrid``.

    Parameters
    ----------
    barlines : bool
        When True (default), draw barlines and time signature; for span > 1,
        apply per-measure spacing with barline buffer zones.
        When False, suppress barlines and time signature; run spacing "raw"
        as a single stream regardless of span.  Tuplets still apply.
        Tempo markings are still shown when present (for UT/UC contexts).
    tempo_beat : Fraction, optional
        Beat unit for tempo marking (e.g., Fraction(1,4) for quarter note).
    tempo_bpm : float, optional
        Beats per minute for tempo marking.
    om_first_of_group, om_first_measure_of_voice, om_show_time_sig, om_metric_changed : bool, optional
        OpenMusic ``space-size&offset`` / ``get-chiffrage-space`` inputs for ``span == 1``.
        When ``None`` (default), use first-measure behavior (matches standalone ``notate``).
    """
    meas = rt.meas

    _fg = True if om_first_of_group is None else om_first_of_group
    _fmv = True if om_first_measure_of_voice is None else om_first_measure_of_voice
    _sts = True if om_show_time_sig is None else om_show_time_sig
    _mc = False if om_metric_changed is None else om_metric_changed

    # Compute left_margin to accommodate time sig (OM: get-chiffrage-space)
    if barlines and meas is not None:
        _TS_DIGIT_W = 8.5   # matches renderer's TS_DIGIT_W at TS_FONT=20
        _TS_BAR_GAP = 4     # matches renderer's TS_BARLINE_GAP
        _TS_NOTE_GAP = 10   # gap between time sig right edge and first note
        _BAR_X = 44.0       # matches renderer's BAR_X
        max_digits = max(len(str(meas.numerator)), len(str(meas.denominator)))
        ts_w = max_digits * _TS_DIGIT_W + 2
        left_margin = max(left_margin, _BAR_X + _TS_BAR_GAP + ts_w + _TS_NOTE_GAP)

    # --- Pass 1: Tuplet detection (must happen first to build cache) ---
    tuplets, tuplet_cache = collect_tuplets(rt)

    # --- Pass 2+3: Extract leaves, classify durations, tie-split ---
    events: list[EngravingLeaf] = []
    leaf_node_to_event_indices: dict[int, list[int]] = {}

    meas_dur = (
        Fraction(meas.numerator, meas.denominator)
        if meas is not None
        else None
    )
    split_measures = rt.span > 1 and meas_dur is not None

    for leaf in rt.leaf_nodes:
        data = rt[leaf]
        raw_dur = Fraction(data['metric_duration'])
        onset = Fraction(data['metric_onset'])
        is_rest = data.get('proportion', 1) < 0
        is_tied = bool(data.get('tied', False))

        dur = abs(raw_dur)
        tuplet_scale = get_tuplet_scale_for_leaf(leaf, rt, _tuplet_cache=tuplet_cache)

        crosses_meas = (
            split_measures
            and meas_dur is not None
            and bool(measure_split_points_global(onset, dur, meas_dur))
        )
        split_at_measure_boundary = crosses_meas and tuplet_scale is None

        classification = classify_duration(dur, max_dots=max_dots, tuplet_scale=tuplet_scale)

        if classification is not None and not split_at_measure_boundary:
            note_type, dots = classification
            idx = len(events)
            leaf_node_to_event_indices[leaf] = [idx]
            events.append(EngravingLeaf(
                node_id=leaf,
                duration=dur,
                onset=onset,
                note_type=note_type,
                dots=dots,
                is_rest=is_rest,
                is_continuation_tie=is_tied and not is_rest,
                is_tied_forward=False,
                tuplet_scale=tuplet_scale,
            ))
        else:
            if is_rest:
                if crosses_meas and meas_dur is not None:
                    segs = measure_segments_only(onset, dur, meas_dur)
                else:
                    segs = [(onset, dur)]
                indices = []
                for s0, sd in segs:
                    for rd in split_proportion_fraction(sd):
                        seg_class = classify_duration(rd, tuplet_scale=tuplet_scale)
                        if seg_class is not None:
                            rnt, rdots = seg_class
                        else:
                            rnt, rdots = _fallback_classify(rd, tuplet_scale)
                        idx = len(events)
                        indices.append(idx)
                        events.append(EngravingLeaf(
                            node_id=leaf, duration=rd, onset=s0,
                            note_type=rnt, dots=rdots,
                            is_rest=True, is_continuation_tie=False,
                            is_tied_forward=False, tuplet_scale=tuplet_scale,
                        ))
                        s0 += rd
                leaf_node_to_event_indices[leaf] = indices
            else:
                if tuplet_scale is not None:
                    split_durs = _split_in_tuplet_context(dur, tuplet_scale, max_dots)
                else:
                    if split_at_measure_boundary:
                        split_durs = []
                        for _, seg_dur in measure_segments_only(onset, dur, meas_dur):
                            split_durs.extend(split_proportion_fraction(seg_dur))
                    else:
                        split_durs = split_proportion_fraction(dur)

                if not split_durs:
                    split_durs = [dur]

                indices = []
                current_onset = onset
                for j, seg_dur in enumerate(split_durs):
                    seg_class = classify_duration(
                        seg_dur, max_dots=max_dots, tuplet_scale=tuplet_scale
                    )
                    if seg_class is not None:
                        seg_note_type, seg_dots = seg_class
                    else:
                        seg_note_type, seg_dots = _fallback_classify(
                            seg_dur, tuplet_scale
                        )

                    idx = len(events)
                    indices.append(idx)
                    events.append(EngravingLeaf(
                        node_id=leaf, duration=seg_dur, onset=current_onset,
                        note_type=seg_note_type, dots=seg_dots,
                        is_rest=False,
                        is_continuation_tie=(is_tied or j > 0),
                        is_tied_forward=(j < len(split_durs) - 1),
                        tuplet_scale=tuplet_scale,
                    ))
                    current_onset += seg_dur

                leaf_node_to_event_indices[leaf] = indices

    # --- Pass 4: Map tuplet brackets to event indices ---
    for bracket in tuplets:
        leaf_descs = _leaf_descendants(bracket.group_node_id, rt)
        bracket.event_indices = []
        for leaf_id in leaf_descs:
            if leaf_id in leaf_node_to_event_indices:
                bracket.event_indices.extend(leaf_node_to_event_indices[leaf_id])

    # --- Pass 5: Beam assignment ---
    beam_groups = assign_beams(rt, events, leaf_node_to_event_indices)

    # --- Pass 6: Spacing (OM space-packet for hybrid/om; see spacing/om_packet.py) ---
    barline_x_positions = []
    beat_ratio = (
        Fraction(tempo_beat)
        if tempo_beat is not None
        else (Fraction(1, int(meas.denominator)) if meas is not None else Fraction(1, 4))
    )
    tbpm = float(tempo_bpm) if tempo_bpm is not None else 60.0

    if barlines and rt.span > 1:
        meas_dur = Fraction(meas.numerator, meas.denominator)
        barline_onsets = [meas_dur * i for i in range(1, rt.span)]
        if spacing_mode in ('hybrid', 'om'):
            events, barline_x_positions = space_with_barlines_om(
                events,
                barline_onsets,
                meas,
                bpm=tbpm,
                beat_ratio=beat_ratio,
                om_size=DEFAULT_OM_SIZE,
            )
        else:
            events, barline_x_positions = space_with_barlines(
                events, barline_onsets, meas, spacing_mode=spacing_mode,
                scale=scale, left_margin=left_margin,
            )
    elif barlines and rt.span == 1:
        raw_margin = left_margin
        if spacing_mode in ('hybrid', 'om'):
            events, _ = layout_single_measure_events_om(
                events,
                bpm=tbpm,
                beat_ratio=beat_ratio,
                barlines=True,
                show_time_sig=_sts,
                first_of_group=_fg,
                first_measure_of_voice=_fmv,
                metric_changed=_mc,
                om_size=DEFAULT_OM_SIZE,
                initial_count=BAR_X,
            )
        elif spacing_mode == 'proportional':
            events = space_proportional(events, scale=scale, left_margin=raw_margin)
        elif spacing_mode == 'traditional':
            events = space_traditional(events, left_margin=raw_margin)
        else:
            events = space_hybrid(events, scale=scale, left_margin=raw_margin)
    else:
        raw_margin = left_margin if barlines else 20.0
        if spacing_mode == 'proportional':
            events = space_proportional(events, scale=scale, left_margin=raw_margin)
        elif spacing_mode == 'traditional':
            events = space_traditional(events, left_margin=raw_margin)
        else:
            events = space_hybrid(events, scale=scale, left_margin=raw_margin)

    rt_text = _build_rt_text(rt)

    tempo_beat_frac = None
    if tempo_beat is not None:
        tempo_beat_frac = Fraction(tempo_beat)

    return NotatedMeasure(
        time_signature=meas if barlines else None,
        events=events,
        tuplets=tuplets,
        beam_groups=beam_groups,
        rt_text=rt_text,
        barline_x_positions=barline_x_positions,
        show_barlines=barlines,
        tempo_beat=tempo_beat_frac,
        tempo_bpm=float(tempo_bpm) if tempo_bpm is not None else None,
    )


def _split_in_tuplet_context(dur, tuplet_scale, max_dots):
    one = classify_duration(dur, max_dots=max_dots, tuplet_scale=tuplet_scale)
    if one is not None:
        return [dur]
    notated_dur = dur / tuplet_scale
    notated_splits = split_duration(notated_dur, max_dots=max_dots)
    return [s * tuplet_scale for s in notated_splits]


def _fallback_classify(dur: Fraction, tuplet_scale=None) -> tuple[NoteType, int]:
    """Best-effort classification for non-engravable durations."""
    from .models import NOTE_TYPE_DURATIONS
    check_dur = dur
    if tuplet_scale is not None and tuplet_scale != 0:
        check_dur = dur / tuplet_scale
    best_type = NoteType.QUARTER
    best_diff = abs(check_dur - Fraction(1, 4))
    for nt, base_dur in NOTE_TYPE_DURATIONS.items():
        diff = abs(check_dur - base_dur)
        if diff < best_diff:
            best_diff = diff
            best_type = nt
    return best_type, 0


def _leaf_descendants(node_id, rt):
    if rt.out_degree(node_id) == 0:
        return [node_id]
    result = []
    for child in rt.successors(node_id):
        result.extend(_leaf_descendants(child, rt))
    return result


def _build_rt_text(rt):
    lines = []
    lines.append(f"meas={rt.meas}, span={rt.span}")
    lines.append(f"subdivisions={_fmt(rt.subdivisions)}")
    leaf_info = []
    for leaf in rt.leaf_nodes:
        d = rt[leaf]
        dur = d['metric_duration']
        prop = d.get('proportion', '?')
        tied = d.get('tied', False)
        info = f"{float(dur):.4f}"
        if prop < 0:
            info += "(r)"
        if tied:
            info += "(t)"
        leaf_info.append(info)
    lines.append(f"leaf durations: [{', '.join(leaf_info)}]")
    return '\n'.join(lines)


def _fmt(s):
    if isinstance(s, (int, float)):
        return str(s)
    if isinstance(s, tuple):
        return '(' + ', '.join(_fmt(x) for x in s) + ')'
    return str(s)
