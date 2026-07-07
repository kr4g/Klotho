from uuid import uuid4

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import (
    DEFAULT_NOTE_DURATION, DEFAULT_CHORD_DURATION,
    DEFAULT_SPECTRUM_DURATION, DEFAULT_DRUM_FREQ,
    KNOWN_KWARGS, perc_env_pfields,
    _get_addressed_collection, _merge_pfields,
    scale_pitch_sequence, extract_convert_kwargs, iter_group_sequence,
    resolve_instrument,
)
from klotho.utils.playback._sc_assembly import (
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
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]
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
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]
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
        addressed = _get_addressed_collection(chord)
        groups.append([addressed[i] for i in range(len(addressed))])
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

    t = np.linspace(0.0, 1.0, block_size, dtype=np.float64)
    blocks = []
    serializable: list[dict] = []

    for i, desc in enumerate(control_descriptors):
        env = desc["envelope"]
        total = env.total_time
        if total <= 0:
            bp_times = [0.0] * len(env.values)
        else:
            cumulative = [0.0]
            for seg_t in env.times:
                cumulative.append(cumulative[-1] + seg_t * env.time_scale)
            bp_times = [c / total for c in cumulative]

        samples = np.interp(
            t,
            np.array(bp_times, dtype=np.float64),
            np.array(env.values, dtype=np.float64),
        ).astype(np.float32)
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

    from collections import OrderedDict
    control_descriptors: list[dict] = []
    for desc in uc.resolved_control_envelopes():
        env_start, env_end = desc["time_span"]
        target_map: "OrderedDict[str, float]" = OrderedDict()
        for nid in desc["target_nodes"]:
            for entry in node_to_event_ids.get(nid, []):
                eid, synth_start = entry
                score_uid = id_map.get(eid, eid)
                mapping_start = max(float(synth_start), float(env_start))
                if score_uid in target_map:
                    if mapping_start < target_map[score_uid]:
                        target_map[score_uid] = mapping_start
                else:
                    target_map[score_uid] = mapping_start
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

    return events, control_descriptors


def convert_score_to_sc_events(score, **kwargs) -> dict:
    """Lower every item in a Score to a SuperCollider event payload.

    The converter iterates items in insertion order, walks each item's
    owned unit to collect its :class:`CompositionalUnit` leaves, and
    lowers each UC via
    :func:`klotho.utils.playback._sc_assembly.lower_compositional_ir_to_sc_assembly`.
    Event IDs are regenerated per lowering so the same external UC
    reused across multiple items does not collide.

    Parameters
    ----------
    score : Score
        The score to lower.
    **kwargs
        Reserved for future engine options; unused today.

    Returns
    -------
    dict
        ``{"events": [...], "meta": {...}, "control_data": {...}}``.
        ``control_data`` is a SuperSonic-ready payload with ``buffer``,
        ``blockSize``, and ``descriptors``.
    """
    all_events: list[dict] = []
    control_descriptors: list[dict] = []

    for item in score.items():
        for uc in _iter_ucs(item.unit):
            uc_events, uc_ctrl = _lower_score_uc(uc, item.track)
            all_events.extend(uc_events)
            control_descriptors.extend(uc_ctrl)

    all_events.sort(
        key=lambda e: (e["start"], _SC_EVENT_PRIORITY.get(e["type"], 3))
    )

    block_size = getattr(score, "_block_size", _DEFAULT_SCORE_BLOCK_SIZE)
    meta = _build_score_meta(score)
    control_data = _build_score_control_data(control_descriptors, block_size)

    return {
        "events": all_events,
        "meta": meta,
        "control_data": control_data,
    }


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
