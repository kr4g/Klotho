from uuid import uuid4

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.composition.events import Event
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import (
    DEFAULT_NOTE_DURATION, DEFAULT_CHORD_DURATION,
    DEFAULT_SPECTRUM_DURATION, DEFAULT_DRUM_FREQ,
    KNOWN_KWARGS, perc_env_pfields,
    _merge_pfields,
    coerce_sc_pfield_values,
    lower_event_ir_to_voice_events,
    scale_pitch_sequence, extract_convert_kwargs, iter_group_sequence,
    resolve_instrument,
)
from klotho.utils.playback._sc_assembly import (
    _attach_poly_meta,
    _warn_unknown_pfields,
    lower_compositional_ir_to_sc_assembly,
    sort_sc_assembly_events,
)

DEFAULT_PITCH_SYNTH = "kl_tri"
DEFAULT_COLLECTION_SYNTH = "kl_tri"
DEFAULT_SPECTRUM_SYNTH = "kl_sine"
DEFAULT_RHYTHM_SYNTH = "kl_kicktone"
DEFAULT_COMPOSITION_SYNTH = "kl_tri"


def _uid():
    return uuid4().hex


def _resolve_synth(inst, default_synth):
    """Resolve ``inst`` to ``(synth_name, inst_ctx)``.

    ``inst_ctx`` is ``None`` when no instrument was given (callers keep
    their default synth and event shape), otherwise a tuple of
    ``(inst_pfields, has_gate, controls)`` consumed by ``_inst_note``.
    """
    def_name, inst_pfields, has_gate = resolve_instrument(inst)
    if def_name is None:
        return default_synth, None
    return def_name, (inst_pfields, has_gate, inst_pfields)


def _combine_extras(inst_pfields, extra_pfields):
    """Instrument defaults sit below explicit user pfields."""
    if not inst_pfields:
        return extra_pfields
    combined = dict(inst_pfields)
    combined.pop('gate', None)
    combined.pop('out', None)
    if extra_pfields:
        combined.update(extra_pfields)
    return combined


def _inst_note(uid, synth, start, dur, pfields, step_index=None,
               extra_pfields=None, inst_ctx=None):
    """Build a note event honoring an optional resolved instrument context.

    ``inst_ctx`` is ``(inst_pfields, has_gate, controls)`` from
    ``_resolve_synth``; ``None`` preserves the plain gated-note shape.
    Non-gated synths get a ``dur`` pfield only when they declare one.
    """
    if inst_ctx is None:
        return _gated_note(uid, synth, start, dur, pfields,
                           step_index=step_index, extra_pfields=extra_pfields)
    inst_pfields, has_gate, controls = inst_ctx
    combined = _combine_extras(inst_pfields, extra_pfields)
    pf = _merge_pfields(pfields, combined)
    if not has_gate and 'dur' in controls and not (extra_pfields and 'dur' in extra_pfields):
        pf['dur'] = dur
    new_ev = {
        "type": "new",
        "id": uid,
        "defName": synth,
        "start": start,
        "dur": dur,
        "releaseAfter": True,
        "pfields": pf,
    }
    if step_index is not None:
        new_ev["_stepIndex"] = step_index
    return [new_ev]


def _gated_note(uid, synth, start, dur, pfields, step_index=None, extra_pfields=None):
    pf = _merge_pfields(pfields, extra_pfields)
    new_ev = {
        "type": "new",
        "id": uid,
        "defName": synth,
        "start": start,
        "dur": dur,
        "releaseAfter": True,
        "pfields": pf,
    }
    if step_index is not None:
        new_ev["_stepIndex"] = step_index
    return [new_ev]


def _perc_note(uid, synth, start, dur, pfields, step_index=None, extra_pfields=None):
    pf = _merge_pfields(pfields, extra_pfields)
    pf["dur"] = dur
    new_ev = {
        "type": "new",
        "id": uid,
        "defName": synth,
        "start": start,
        "dur": dur,
        "releaseAfter": True,
        "pfields": pf,
    }
    if step_index is not None:
        new_ev["_stepIndex"] = step_index
    return [new_ev]


def pitch_to_sc_events(pitch, duration=None, amp=None, extra_pfields=None, inst=None):
    dur = duration if duration is not None else 1.0
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_PITCH_SYNTH)
    uid = _uid()
    return _inst_note(uid, synth, 0.0, dur, {
        "freq": pitch.freq,
        "amp": single_voice_amplitude(pitch.freq, amp),
    }, step_index=0, extra_pfields=extra_pfields, inst_ctx=inst_ctx)


def pitch_collection_to_sc_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u',
                                  amp=None, pause=0.0, extra_pfields=None, inst=None):
    pitches = [obj[i] for i in range(len(obj))]
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_COLLECTION_SYNTH)

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        if arp:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_seq_sc_events(pitches, 0, synth=synth, amp=amp,
                                        total_dur=dur, pause=0.0, extra_pfields=extra_pfields,
                                        inst_ctx=inst_ctx)
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_chord_sc_events(pitches, 0, dur, strum, synth,
                                          amp=amp, extra_pfields=extra_pfields,
                                          inst_ctx=inst_ctx)
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, synth=synth, amp=amp,
                                    per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields,
                                    inst_ctx=inst_ctx)


def scale_to_sc_events(obj, duration=None, equaves=1, amp=None, pause=0.0, extra_pfields=None, inst=None):
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_COLLECTION_SYNTH)
    all_pitches = scale_pitch_sequence(obj, equaves)
    return _build_seq_sc_events(all_pitches, 0, synth=synth, amp=amp,
                                per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields,
                                inst_ctx=inst_ctx)


def chord_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                       amp=None, extra_pfields=None, inst=None):
    pitches = [obj[i] for i in range(len(obj))]
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_COLLECTION_SYNTH)

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_seq_sc_events(pitches, 0, synth=synth, amp=amp,
                                    total_dur=dur, pause=0.0, extra_pfields=extra_pfields,
                                    inst_ctx=inst_ctx)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, synth,
                                      amp=amp, extra_pfields=extra_pfields,
                                      inst_ctx=inst_ctx)


def chord_sequence_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                                amp=None, pause=0.25, extra_pfields=None, inst=None):
    events = []
    dur = duration if duration is not None else DEFAULT_CHORD_DURATION
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_COLLECTION_SYNTH)
    groups = []
    for chord in obj:
        groups.append([chord[i] for i in range(len(chord))])
    group_voice_amps = [
        compute_voice_amplitudes([p.freq for p in group], amp)
        for group in groups
    ]

    if arp:
        for gi, _, start_time, voice_dur, p in iter_group_sequence(groups, dur, arp=True, direction=direction, pause=pause):
            uid = _uid()
            events.extend(_inst_note(uid, synth, start_time,
                voice_dur, {
                    "freq": p.freq,
                    "amp": single_voice_amplitude(p.freq, amp),
                }, step_index=gi, extra_pfields=extra_pfields, inst_ctx=inst_ctx))
    else:
        for gi, vi, start_time, voice_dur, p in iter_group_sequence(groups, dur, arp=False, strum=strum, direction=direction, pause=pause):
            uid = _uid()
            events.extend(_inst_note(uid, synth, start_time,
                voice_dur, {
                    "freq": p.freq,
                    "amp": group_voice_amps[gi][vi],
                }, step_index=gi, extra_pfields=extra_pfields, inst_ctx=inst_ctx))

    return events


def spectrum_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                          amp=None, extra_pfields=None, inst=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))
    synth, inst_ctx = _resolve_synth(inst, DEFAULT_SPECTRUM_SYNTH)

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_seq_sc_events(pitches, 0, synth=synth, amp=target,
                                    total_dur=dur, pause=0.0, extra_pfields=extra_pfields,
                                    inst_ctx=inst_ctx)
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, synth,
                                      amp=target, extra_pfields=extra_pfields,
                                      inst_ctx=inst_ctx)


def temporal_unit_to_sc_events(obj, use_absolute_time=False, amp=None, extra_pfields=None,
                               animation=False):
    events = []
    target = amp if amp is not None else 0.85

    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)}
                    if animation else None)

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(c.start for c in obj) if len(obj) > 0 else 0

    for chronon in obj:
        start = chronon.start - time_offset
        dur = abs(chronon.duration)
        step_idx = node_to_step.get(chronon.node_id, None) if animation else None

        if chronon.is_rest:
            if animation:
                events.append({
                    "type": "new",
                    "id": _uid(),
                    "defName": "__rest__",
                    "start": start,
                    "pfields": {},
                    "_stepIndex": step_idx,
                })
            continue

        uid = _uid()
        pf = {
            "baseFreq": DEFAULT_DRUM_FREQ,
            "amp": target,
            **perc_env_pfields(dur),
        }
        events.extend(_perc_note(uid, DEFAULT_RHYTHM_SYNTH, start, dur, pf,
                                 step_index=step_idx, extra_pfields=extra_pfields))

    if animation:
        events.sort(key=lambda ev: ev["start"])
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=animation)
    return events


def rhythm_tree_to_sc_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    tu = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_sc_events(tu, use_absolute_time=False, amp=amp,
                                     extra_pfields=extra_pfields)


def temporal_unit_to_sc_animation_events(obj, use_absolute_time=False, amp=None, extra_pfields=None):
    return temporal_unit_to_sc_events(obj, use_absolute_time=use_absolute_time, amp=amp,
                                     extra_pfields=extra_pfields, animation=True)


def rhythm_tree_to_sc_animation_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    tu = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_sc_animation_events(tu, use_absolute_time=False, amp=amp,
                                                extra_pfields=extra_pfields)


def compositional_unit_to_sc_events(obj, extra_pfields=None, animation=False,
                                    use_absolute_time=False):
    events = lower_compositional_ir_to_sc_assembly(
        obj,
        extra_pfields=extra_pfields,
        animation=animation,
        use_absolute_time=use_absolute_time,
        default_synth=DEFAULT_COMPOSITION_SYNTH,
        normalize_sc_pfields=True,
        sort_output=True,
    )
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=animation)
    return events


def compositional_unit_to_sc_animation_events(obj, extra_pfields=None):
    return compositional_unit_to_sc_events(obj, extra_pfields=extra_pfields, animation=True)


def _build_seq_sc_events(pitches, start, synth, amp=None, per_voice_dur=None,
                         total_dur=None, pause=0.0, extra_pfields=None, inst_ctx=None):
    events = []
    n = len(pitches)
    if n == 0:
        return events

    if total_dur is not None:
        voice_dur = total_dur / n
    elif per_voice_dur is not None:
        voice_dur = per_voice_dur
    else:
        voice_dur = DEFAULT_NOTE_DURATION

    cursor = start
    for i, pitch in enumerate(pitches):
        uid = _uid()
        events.extend(_inst_note(uid, synth, cursor, voice_dur, {
            "freq": pitch.freq,
            "amp": single_voice_amplitude(pitch.freq, amp),
        }, step_index=i, extra_pfields=extra_pfields, inst_ctx=inst_ctx))
        cursor += voice_dur + max(0.0, pause)
    return events


def _build_chord_sc_events(pitches, start, dur, strum, synth, amp=None,
                           dur_factor=1.0, extra_pfields=None, inst_ctx=None):
    events = []
    num = len(pitches)
    if num == 0:
        return events

    freqs = [p.freq for p in pitches]
    voice_amps = compute_voice_amplitudes(freqs, amp)
    strum = max(0, min(1, strum))

    for i, pitch in enumerate(pitches):
        uid = _uid()
        start_offset = (strum * dur * i) / num if num > 1 else 0
        events.extend(_inst_note(uid, synth, start + start_offset,
            (dur * dur_factor) - start_offset, {
                "freq": pitch.freq,
                "amp": voice_amps[i],
            }, step_index=i, extra_pfields=extra_pfields, inst_ctx=inst_ctx))
    return events


def _merge_sub_sc(target_events, sub_events):
    target_events.extend(sub_events)


def _shift_events_to_zero(events):
    if not events:
        return events
    min_start = min(ev.get("start", 0.0) for ev in events)
    if min_start == 0.0:
        return events
    for ev in events:
        ev["start"] = ev.get("start", 0.0) - min_start
    return events


def temporal_sequence_to_sc_events(obj, extra_pfields=None, rebase_to_zero=True):
    events = []

    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(unit, extra_pfields=None))
        elif isinstance(unit, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(unit, use_absolute_time=True, extra_pfields=extra_pfields))
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(unit, extra_pfields=extra_pfields, rebase_to_zero=False))
        elif isinstance(unit, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(unit, extra_pfields=extra_pfields, rebase_to_zero=False))

    events = sort_sc_assembly_events(events)
    if rebase_to_zero:
        _shift_events_to_zero(events)
    return events


def temporal_block_to_sc_events(obj, extra_pfields=None, rebase_to_zero=True):
    events = []

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row, extra_pfields=None))
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True, extra_pfields=extra_pfields))
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row, extra_pfields=extra_pfields, rebase_to_zero=False))
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row, extra_pfields=extra_pfields, rebase_to_zero=False))

    events = sort_sc_assembly_events(events)
    if rebase_to_zero:
        _shift_events_to_zero(events)
    return events


def _shift_sc_step_indices(events, step_offset):
    if step_offset == 0:
        return events
    for ev in events:
        if ev.get("_stepIndex") is not None:
            ev["_stepIndex"] = ev["_stepIndex"] + step_offset
    return events


def _temporal_container_sc_animation_events(obj, amp=None, extra_pfields=None):
    """Build SC animation events for a UTS/BT with global step indices.

    Traverses members in structural (DFS) order — the same enumeration
    used by the timeline SVG renderer — assigning each leaf-unit's local
    step indices a running global offset.

    Returns
    -------
    tuple of (list, int)
        ``(events, total_steps)``.
    """
    events = []
    step_offset = 0

    for member in obj:
        if isinstance(member, CompositionalUnit):
            sub = compositional_unit_to_sc_events(member, extra_pfields=None,
                                                  animation=True, use_absolute_time=True)
            n_steps = len(member._rt.leaf_nodes)
        elif isinstance(member, TemporalUnit):
            sub = temporal_unit_to_sc_events(member, use_absolute_time=True, amp=amp,
                                             extra_pfields=extra_pfields, animation=True)
            n_steps = len(member._rt.leaf_nodes)
        elif isinstance(member, (TemporalUnitSequence, TemporalBlock)):
            sub, n_steps = _temporal_container_sc_animation_events(
                member, amp=amp, extra_pfields=extra_pfields)
        else:
            raise TypeError(
                f"Unsupported member type in temporal container: {type(member).__name__}"
            )
        _shift_sc_step_indices(sub, step_offset)
        _merge_sub_sc(events, sub)
        step_offset += n_steps

    return events, step_offset


def temporal_container_to_sc_animation_events(obj, amp=None, extra_pfields=None):
    """SC animation events for a TemporalUnitSequence or TemporalBlock.

    Events carry absolute times (rebased so the payload starts at zero)
    and a global ``_stepIndex`` matching the timeline renderer's step
    enumeration.
    """
    events, _ = _temporal_container_sc_animation_events(obj, amp=amp,
                                                        extra_pfields=extra_pfields)
    events = sort_sc_assembly_events(events)
    _shift_events_to_zero(events)
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=True)
    return events


def convert_to_sc_events(obj, **kwargs):
    kw = extract_convert_kwargs(kwargs)
    duration = kw['duration']
    arp = kw['arp']
    mode = kw['mode']
    strum = kw['strum']
    direction = kw['direction']
    equaves = kw['equaves']
    beat = kw['beat']
    bpm = kw['bpm']
    amp = kw['amp']
    pause = kw['pause']
    inst = kw['inst']
    extra_pfields = kw['extra_pfields']

    if isinstance(obj, Pitch):
        return pitch_to_sc_events(obj, duration=duration, amp=amp, extra_pfields=extra_pfields, inst=inst)

    if isinstance(obj, Spectrum):
        return spectrum_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                    amp=amp, extra_pfields=extra_pfields, inst=inst)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_sc_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction,
                                    amp=amp, extra_pfields=extra_pfields, inst=inst)

    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_sc_events(obj, beat=beat, bpm=bpm, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_sc_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalBlock):
        return temporal_block_to_sc_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, CompositionalUnit):
        return compositional_unit_to_sc_events(obj, extra_pfields=None)

    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_sc_events(obj, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, ChordSequence):
        return chord_sequence_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                           amp=amp, pause=(0.25 if pause is None else pause), extra_pfields=extra_pfields,
                                           inst=inst)

    if isinstance(obj, Scale):
        return scale_to_sc_events(obj, duration=duration, equaves=equaves, amp=amp,
                                  pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields,
                                  inst=inst)

    if isinstance(obj, (Chord, Voicing)):
        return chord_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, extra_pfields=extra_pfields, inst=inst)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_sc_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                                 direction=direction, amp=amp,
                                                 pause=0.0,
                                                 extra_pfields=extra_pfields, inst=inst)
        return pitch_collection_to_sc_events(obj, duration=duration, mode="sequential",
                                             amp=amp, pause=(0.0 if pause is None else pause),
                                             extra_pfields=extra_pfields, inst=inst)

    raise TypeError(f"Unsupported object type: {type(obj)}")


_SC_EVENT_PRIORITY = {'new': 0, 'set': 1, 'release': 2}
_DEFAULT_SCORE_BLOCK_SIZE = 512


def _iter_ucs(unit):
    """Yield every :class:`CompositionalUnit` contained in a (possibly
    nested) temporal structure.

    Bare :class:`TemporalUnit` nodes are not expected inside a
    :class:`~klotho.thetos.composition.score.Score` — they are promoted
    on ``Score.add``.
    """
    if isinstance(unit, CompositionalUnit):
        yield unit
    elif isinstance(unit, TemporalUnitSequence):
        for member in unit._seq:
            yield from _iter_ucs(member)
    elif isinstance(unit, TemporalBlock):
        for row in unit._rows:
            yield from _iter_ucs(row)


def _build_score_meta(score) -> dict:
    """Build the SuperSonic ``meta`` dict (tracks + inserts) for a Score."""
    groups = [name for name in score._tracks if name != "main"]
    inserts: dict[str, list] = {}
    for name, track_data in score._tracks.items():
        if track_data["inserts"]:
            inserts[name] = [
                {"uid": ins.uid, "defName": ins.defName, "args": ins.args}
                for ins in track_data["inserts"]
            ]
    meta: dict = {}
    if groups:
        meta["groups"] = groups
    if inserts:
        meta["inserts"] = inserts
    return meta


def _build_score_control_data(control_descriptors, block_size):
    """Build ``{buffer, blockSize, descriptors}`` for SuperSonic from the
    per-UC resolved control-envelope descriptors collected during
    lowering."""
    if not control_descriptors:
        return {"buffer": None, "blockSize": block_size, "descriptors": []}

    import numpy as np

    blocks = []
    serializable: list[dict] = []

    for i, desc in enumerate(control_descriptors):
        env = desc["envelope"]
        total = env.total_time
        if total <= 0:
            samples = np.full(block_size, float(env.values[0]), dtype=np.float32)
        else:
            sample_times = np.linspace(0.0, total, block_size, dtype=np.float64)
            samples = np.array(
                [env.at_time(float(x)) for x in sample_times],
                dtype=np.float32,
            )
        blocks.append(samples)

        serializable.append({
            "blockIndex": i,
            "start": desc["start"],
            "dur": desc["duration"],
            "pfields": desc["pfields"],
            "targets": desc["targets"],
        })

    buffer_data = np.concatenate(blocks)
    return {
        "buffer": buffer_data,
        "blockSize": block_size,
        "descriptors": serializable,
    }


def _collect_control_descriptors(uc, node_to_event_ids, id_map=None):
    """Build control-envelope descriptors for one lowered UC.

    Maps each envelope's ``target_nodes`` through the node→event-id map
    (optionally remapped via *id_map*, as the Score path regenerates
    uids), computing per-target ``startTime = max(synth_start,
    env_start)`` and deduping by uid (keeping the earliest start).
    Descriptor times are absolute (same timeline as the events).
    """
    from collections import OrderedDict

    control_descriptors: list[dict] = []
    for desc in uc.resolved_control_envelopes():
        env_start, env_end = desc["time_span"]
        target_map: "OrderedDict[str, float]" = OrderedDict()
        for nid in desc["target_nodes"]:
            for entry in node_to_event_ids.get(nid, []):
                eid, synth_start = entry
                uid = id_map.get(eid, eid) if id_map else eid
                mapping_start = max(float(synth_start), float(env_start))
                if uid in target_map:
                    if mapping_start < target_map[uid]:
                        target_map[uid] = mapping_start
                else:
                    target_map[uid] = mapping_start
        if not target_map:
            continue
        targets = [
            {"id": uid, "startTime": start} for uid, start in target_map.items()
        ]
        control_descriptors.append({
            "envelope": desc["envelope"],
            "pfields": desc["pfields"],
            "start": env_start,
            "duration": env_end - env_start,
            "targets": targets,
        })
    return control_descriptors


def _lower_score_uc(uc, track_override):
    """Lower one UC to SC events + collect per-envelope targets.

    Returns a tuple ``(events, control_descriptors)`` where each event
    carries its ``group`` (from *track_override* or its own ``group``
    mfield), all event IDs are freshly regenerated (so that the same UC
    can appear in multiple items without uid collisions), and control
    descriptors are already re-keyed against the fresh IDs.
    """
    from uuid import uuid4

    from klotho.utils.playback._sc_assembly import (
        lower_compositional_ir_to_sc_assembly,
    )

    assembly_events, node_to_event_ids = lower_compositional_ir_to_sc_assembly(
        uc,
        extra_pfields=None,
        animation=False,
        default_synth='kl_tri',
        normalize_sc_pfields=False,
        sort_output=True,
        return_node_map=True,
    )

    id_map: dict[str, str] = {}
    events: list[dict] = []

    for event in assembly_events:
        if event.get("defName") == "__rest__":
            continue

        event_type = event.get("type")

        if track_override is not None:
            event["group"] = track_override
        elif "group" not in event:
            event["group"] = "default"

        if event_type == "new":
            new_uid = uuid4().hex
            id_map[event["id"]] = new_uid
            event["id"] = new_uid
            events.append(event)
        elif event_type == "set":
            orig_id = event.get("id")
            mapped_uid = id_map.get(orig_id, orig_id)
            event["id"] = mapped_uid
            events.append(event)
        elif event_type == "release":
            mapped_uid = id_map.get(event.get("id"))
            if mapped_uid is None:
                continue
            event["id"] = mapped_uid
            events.append(event)

    control_descriptors = _collect_control_descriptors(
        uc, node_to_event_ids, id_map=id_map
    )

    return events, control_descriptors


# Once-per-process dedupe for standalone-event FYI notes (mirrors the
# unknown-pfield FYIs in _sc_assembly). Playback always continues.
_WARNED_EVENT_FYIS: set = set()


def _event_fyi(tag, message):
    if tag in _WARNED_EVENT_FYIS:
        return
    _WARNED_EVENT_FYIS.add(tag)
    print(f"Klotho FYI: {message}")


def _lower_score_event(item):
    """Lower one standalone Event item to SC events.

    Emits one ``new`` per voice (a tuple pfield expands to simultaneous
    voices via the standard poly expansion), then the event's scheduled
    ``set`` / ``release`` messages, each targeting the per-voice ids
    minted here.  Ids are regenerated per lowering call, matching
    :func:`_lower_score_uc`.
    """
    from types import SimpleNamespace

    from klotho.thetos.instruments._shared import load_ss_manifest
    from klotho.thetos.instruments.base import Kit

    event = item.unit
    kit = event.inst if isinstance(event.inst, Kit) else None
    if kit is not None:
        def_name, inst_pfields, has_gate = resolve_instrument(kit._resolve(None))
    else:
        def_name, inst_pfields, has_gate = resolve_instrument(event.inst)
    if def_name is None:
        def_name = DEFAULT_COMPOSITION_SYNTH

    if item.track is not None:
        group = item.track
    else:
        group = event.mfields.get('group') or 'default'

    is_hold = event._dur is None
    if is_hold and event.mfields.get('strum'):
        _event_fyi(
            ('strum-hold', item.name),
            f"strum has no effect on a held event (dur=None) "
            f"['{item.name}']; voices start together.",
        )

    shim = SimpleNamespace(
        start=item.start,
        duration=0.0 if is_hold else event._dur,
        pfields=dict(event.pfields),
        mfields=dict(event.mfields),
        node_id=None,
    )
    voices = lower_event_ir_to_voice_events(shim)

    release_time = None
    if event._release is not None:
        release_time = item.start + event._release.offset
        if not is_hold and abs(event._release.offset - event._dur) > 1e-9:
            _event_fyi(
                ('release-vs-dur', item.name),
                f"event '{item.name}' has dur={event._dur} and an explicit "
                f"release at offset {event._release.offset}; the release "
                f"wins.",
            )

    manifest = load_ss_manifest()
    events = []
    voice_ids = []

    for voice in voices:
        uid = uuid4().hex
        voice_ids.append(uid)

        user_pf = coerce_sc_pfield_values(voice["pfields"])
        v_def_name, v_inst_pfields, v_has_gate = def_name, inst_pfields, has_gate
        if kit is not None:
            # Kit member is chosen per voice from the selector pfield
            # (tuple selectors were already expanded per voice above);
            # the selector itself never reaches the synth.
            voice_sel = user_pf.pop(kit.selector, None)
            member = kit._resolve(voice_sel)
            v_def_name, v_inst_pfields, v_has_gate = resolve_instrument(member)
        pf = coerce_sc_pfield_values(_combine_extras(v_inst_pfields, user_pf))
        if not v_has_gate and not is_hold:
            if 'duration' in v_inst_pfields and 'duration' not in user_pf:
                pf['duration'] = voice["duration"]
            elif 'dur' in v_inst_pfields and 'dur' not in user_pf:
                pf['dur'] = voice["duration"]
        _warn_unknown_pfields(v_def_name, pf, manifest)

        if release_time is not None:
            dur_val = max(0.0, release_time - voice["start"])
            release_after = False
        elif is_hold:
            dur_val = None
            release_after = False
        else:
            dur_val = voice["duration"]
            release_after = True

        new_event = {
            "type": "new",
            "id": uid,
            "defName": v_def_name,
            "start": voice["start"],
            "dur": dur_val,
            "releaseAfter": release_after,
            "pfields": pf,
            "group": group,
        }
        _attach_poly_meta(new_event, voice)
        events.append(new_event)

    voice_count = len(voice_ids)
    sounding_end = release_time
    if sounding_end is None and not is_hold:
        sounding_end = item.start + event._dur

    for spec in event._sets:
        set_start = item.start + spec.offset
        if sounding_end is not None and set_start > sounding_end + 1e-9:
            _event_fyi(
                ('set-past-end', item.name, spec.offset),
                f"set at {set_start}s on event '{item.name}' fires after "
                f"its node(s) end at {sounding_end}s; it will have no "
                f"effect.",
            )
        for key, value in spec.pfields.items():
            if isinstance(value, tuple) and len(value) > voice_count:
                _event_fyi(
                    ('set-extra-voices', item.name, key),
                    f"set on event '{item.name}' gives {len(value)} values "
                    f"for '{key}' but the event has {voice_count} "
                    f"voice(s); extra values are unused.",
                )
        for voice_index, uid in enumerate(voice_ids):
            pf = {}
            for key, value in spec.pfields.items():
                if isinstance(value, tuple):
                    pf[key] = value[voice_index % len(value)]
                else:
                    pf[key] = value
            pf = coerce_sc_pfield_values(pf)
            _warn_unknown_pfields(def_name, pf, manifest)
            events.append({
                "type": "set",
                "id": uid,
                "start": set_start,
                "pfields": pf,
                "group": group,
            })

    if release_time is not None:
        if not has_gate:
            _event_fyi(
                ('release-ungated', item.name),
                f"event '{item.name}' uses ungated synth '{def_name}'; "
                f"the scheduled release is a no-op and was dropped.",
            )
        else:
            for uid in voice_ids:
                events.append({
                    "type": "release",
                    "id": uid,
                    "start": release_time,
                    "group": group,
                })

    return events


def convert_score_to_sc_events(score, start_time=None, **kwargs) -> dict:
    """Lower every item in a Score to a SuperCollider event payload.

    The converter iterates items in insertion order, walks each item's
    owned unit to collect its :class:`CompositionalUnit` leaves, and
    lowers each UC via
    :func:`klotho.utils.playback._sc_assembly.lower_compositional_ir_to_sc_assembly`.
    Event IDs are regenerated per lowering so the same external UC
    reused across multiple items does not collide.

    The timeline is normalized: items may sit at negative score times
    (e.g. a riser placed before the "downbeat" at 0), and the whole
    score is shifted uniformly so the earliest item lands at 0 before
    lowering.  The pre-lowering shift matters: leaf extraction encodes
    rests as negative onsets (recovered via ``abs``), so genuinely
    negative timelines must never reach it.  *start_time* then shifts
    the lowered payload — events and control-envelope descriptors
    alike — so the earliest event lands exactly there.

    Parameters
    ----------
    score : Score
        The score to lower.
    start_time : float or None
        Shift the earliest event to this time.  When None, only
        timelines that begin at a negative time are shifted (so the
        earliest item starts at 0).
    **kwargs
        Reserved for future engine options; unused today.

    Returns
    -------
    dict
        ``{"events": [...], "meta": {...}, "control_data": {...}}``.
        ``control_data`` is a SuperSonic-ready payload with ``buffer``,
        ``blockSize``, and ``descriptors``.
    """
    from klotho.chronos.temporal_units.temporal import _reoffset

    all_events: list[dict] = []
    control_descriptors: list[dict] = []

    items = list(score.items())
    pre_shift = 0.0
    if items:
        score_start = min(item.start for item in items)
        if score_start < 0:
            pre_shift = -score_start

    try:
        if pre_shift:
            for item in items:
                _reoffset(item.unit, item.unit._offset + pre_shift)

        for item in items:
            if isinstance(item.unit, Event):
                all_events.extend(_lower_score_event(item))
                continue
            for uc in _iter_ucs(item.unit):
                uc_events, uc_ctrl = _lower_score_uc(uc, item.track)
                all_events.extend(uc_events)
                control_descriptors.extend(uc_ctrl)
    finally:
        if pre_shift:
            for item in items:
                _reoffset(item.unit, item.unit._offset - pre_shift)

    all_events.sort(
        key=lambda e: (e["start"], _SC_EVENT_PRIORITY.get(e["type"], 3))
    )

    if start_time is not None and all_events:
        shift = float(start_time) - all_events[0]["start"]
        if shift:
            for ev in all_events:
                ev["start"] += shift
            for desc in control_descriptors:
                desc["start"] += shift
                for target in desc["targets"]:
                    target["startTime"] += shift

    block_size = getattr(score, "_block_size", _DEFAULT_SCORE_BLOCK_SIZE)
    meta = _build_score_meta(score)
    control_data = _build_score_control_data(control_descriptors, block_size)

    return {
        "events": all_events,
        "meta": meta,
        "control_data": control_data,
    }


def _compositional_unit_payload_parts(obj):
    """Lower a bare UC to ``(events, control_descriptors)``.

    Events keep their assembly uids (no Score-style regeneration) and
    absolute times; descriptors are keyed against those uids via the
    node→event-id map.
    """
    events, node_to_event_ids = lower_compositional_ir_to_sc_assembly(
        obj,
        extra_pfields=None,
        animation=False,
        default_synth=DEFAULT_COMPOSITION_SYNTH,
        normalize_sc_pfields=True,
        sort_output=True,
        return_node_map=True,
    )
    descriptors = _collect_control_descriptors(obj, node_to_event_ids)
    return events, descriptors


def _container_payload_parts(obj, extra_pfields=None):
    """Recursively lower a UTS/BT to ``(events, control_descriptors)``
    with absolute (un-rebased) times.

    Mirrors :func:`temporal_sequence_to_sc_events` /
    :func:`temporal_block_to_sc_events` member handling (UC members get
    no extra_pfields; bare TemporalUnits keep their absolute times).
    """
    events: list[dict] = []
    descriptors: list[dict] = []
    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            ev, desc = _compositional_unit_payload_parts(unit)
            events.extend(ev)
            descriptors.extend(desc)
        elif isinstance(unit, TemporalUnit):
            events.extend(temporal_unit_to_sc_events(
                unit, use_absolute_time=True, extra_pfields=extra_pfields
            ))
        elif isinstance(unit, (TemporalUnitSequence, TemporalBlock)):
            ev, desc = _container_payload_parts(unit, extra_pfields=extra_pfields)
            events.extend(ev)
            descriptors.extend(desc)
    return events, descriptors


def _shift_payload_to_zero(events, descriptors):
    """Apply one shared rebase delta to events AND descriptor times so
    control envelopes stay in sync with the audio timeline."""
    if not events:
        return events, descriptors
    min_start = min(ev.get("start", 0.0) for ev in events)
    if min_start == 0.0:
        return events, descriptors
    for ev in events:
        ev["start"] = ev.get("start", 0.0) - min_start
    for desc in descriptors:
        desc["start"] = desc["start"] - min_start
        for tgt in desc["targets"]:
            tgt["startTime"] = tgt["startTime"] - min_start
    return events, descriptors


def convert_to_sc_payload(obj, block_size=_DEFAULT_SCORE_BLOCK_SIZE, **kwargs):
    """Convert a bare UC/UTS/BT (or any playable object) to a payload
    ``{"events": [...], "control_data": {...}}``.

    Unlike :func:`convert_to_sc_events` (which returns a plain event
    list), this harvests control-envelope descriptors from every
    :class:`CompositionalUnit` so ``apply_envelope(..., control=True)``
    produces continuous bus automation outside a Score. Other object
    types fall through to :func:`convert_to_sc_events` with an empty
    ``control_data``.
    """
    from klotho.utils.playback._sc_validate import validate_sc_events

    if isinstance(obj, CompositionalUnit):
        events, descriptors = _compositional_unit_payload_parts(obj)
    elif isinstance(obj, (TemporalUnitSequence, TemporalBlock)):
        kw = extract_convert_kwargs(kwargs)
        events, descriptors = _container_payload_parts(
            obj, extra_pfields=kw['extra_pfields']
        )
        events = sort_sc_assembly_events(events)
        events, descriptors = _shift_payload_to_zero(events, descriptors)
    else:
        events = convert_to_sc_events(obj, **kwargs)
        descriptors = []

    validate_sc_events(events)
    control_data = _build_score_control_data(descriptors, block_size)
    return {"events": events, "control_data": control_data}


def tonejs_events_to_sc(tone_events):
    """Convert Tone.js animation events to SuperSonic format.

    Used by ``_maybe_convert_payload`` in ``animated.py`` when the
    SuperSonic engine is active but the animation events were originally
    built for Tone.js.
    """
    sc_events = []
    for ev in tone_events:
        uid = _uid()
        start = ev.get("start", 0)
        dur = ev.get("duration", 0.5)
        pf = ev.get("pfields", {})
        step = ev.get("_stepIndex", None)
        animate = ev.get("_animate", True)
        instrument = ev.get("instrument", "")

        if instrument == "__rest__":
            rest_ev = {
                "type": "new",
                "id": uid,
                "defName": "__rest__",
                "start": start,
                "pfields": {},
            }
            if step is not None:
                rest_ev["_stepIndex"] = step
            rest_ev["_animate"] = animate
            sc_events.append(rest_ev)
            continue

        freq = pf.get("freq", 440.0)
        amp_val = pf.get("vel", pf.get("amp", 0.5))
        synth = DEFAULT_RHYTHM_SYNTH if instrument == "membrane" else DEFAULT_PITCH_SYNTH

        if instrument == "membrane":
            pfields = {"baseFreq": freq, "amp": amp_val, "dur": dur, **perc_env_pfields(dur)}
        else:
            pfields = {"freq": freq, "amp": amp_val}

        new_ev = {
            "type": "new",
            "id": uid,
            "defName": synth,
            "start": start,
            "dur": dur,
            "releaseAfter": True,
            "pfields": pfields,
        }
        if step is not None:
            new_ev["_stepIndex"] = step
        new_ev["_animate"] = animate
        if "_polyGroupId" in ev:
            new_ev["_polyGroupId"] = ev["_polyGroupId"]
        if "_logicalStepId" in ev:
            new_ev["_logicalStepId"] = ev["_logicalStepId"]
        if "_polyVoiceIndex" in ev:
            new_ev["_polyVoiceIndex"] = ev["_polyVoiceIndex"]
        if "_polyVoiceCount" in ev:
            new_ev["_polyVoiceCount"] = ev["_polyVoiceCount"]
        if "_polyLeader" in ev:
            new_ev["_polyLeader"] = ev["_polyLeader"]
        sc_events.append(new_ev)

    sc_events.sort(key=lambda e: e["start"])
    return sc_events
