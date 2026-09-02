from klotho.utils.ids import fast_id

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
    resolve_instrument, dispatch_convert,
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

# Control-envelope curve samples per descriptor block.
_DEFAULT_SCORE_BLOCK_SIZE = 512


def _uid():
    return fast_id()


def _declared_controls(def_name):
    """Controls the named SynthDef declares, or ``None`` if it is unknown.

    ``None`` means "cannot be checked" and every caller must read it that
    way -- withholding a pfield because the manifest has not heard of a
    def would silently starve a runtime-registered instrument. The merged
    manifest already includes runtime registrations and is memoized on the
    registry version, so this is cheap but not free; hoist it out of loops.
    """
    from klotho.thetos.instruments._shared import load_ss_manifest
    return load_ss_manifest().get(def_name)


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
    A declared ``duration`` control receives the note's duration; a ``dur``
    control receives it only on non-gated synths.

    Precedence (WL-36, path 2 of 3): **injection always wins here in
    practice.** The guard below does stand down for a ``duration``/``dur``
    already in ``extra_pfields``, but nothing public can put one there:
    ``_converter_base.KNOWN_KWARGS`` reserves both names, and
    ``extract_convert_kwargs`` consumes them as the note LENGTH before
    building ``extra_pfields`` from what is left over. Every caller of this
    function is fed that way, so the guard is unreachable from the public
    API and only a direct internal call can exercise it.

    That measured behaviour, recorded 2026-08-29, corrects an earlier note
    claiming this path let an authored value win. It does not; it agrees
    with the ``CompositionalUnit`` object-instrument path. The Score path
    below is the one that genuinely differs.

    The three paths are not uniform.
    ``_sc_assembly._duration_inject_key`` states the whole picture and is
    the single place to read before changing any of it.
    """
    if inst_ctx is None:
        return _gated_note(uid, synth, start, dur, pfields,
                           step_index=step_index, extra_pfields=extra_pfields)
    inst_pfields, has_gate, controls = inst_ctx
    combined = _combine_extras(inst_pfields, extra_pfields)
    pf = _merge_pfields(pfields, combined)
    if 'duration' in controls and not (extra_pfields and 'duration' in extra_pfields):
        pf['duration'] = dur
    elif not has_gate and 'dur' in controls and not (extra_pfields and 'dur' in extra_pfields):
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
    pitches = obj.data['pitch'].tolist()
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
    # Looked up once per call, not per chronon: the merged manifest is
    # memoized on the registry version, but the dict lookup is not free
    # and the synth does not change mid-unit.
    perc_controls = _declared_controls(DEFAULT_RHYTHM_SYNTH)

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

        # Ties (07_TIES_CHARTER.md sect5): a bare UT has no instruments, so
        # groups join on structure alone -- the merged event surface already
        # hands us one chronon per group with the summed duration. What is
        # left here: warn on a dangling leading tie (sect6), and reserve
        # each continuation's animation step the way rests do.
        tie_nodes = getattr(chronon, 'tie_group', (chronon.node_id,))
        if not chronon.is_rest and obj._rt[tie_nodes[0]].get('tied', False):
            import warnings
            warnings.warn(
                f"leading tie at leaf {tie_nodes[0]} has no predecessor "
                f"here; rendering as an attack", UserWarning, stacklevel=2)
        if animation and len(tie_nodes) > 1:
            for cn in tie_nodes[1:]:
                marker = {
                    "type": "new",
                    "id": _uid(),
                    "defName": "__rest__",
                    "start": obj.nodes[cn].start - time_offset,
                    "pfields": {},
                }
                cstep = node_to_step.get(cn)
                if cstep is not None:
                    marker["_stepIndex"] = cstep
                events.append(marker)

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
            **perc_env_pfields(dur, controls=perc_controls),
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


def _animation_payload(events, descriptors=(), block_size=_DEFAULT_SCORE_BLOCK_SIZE):
    """Wrap animation events plus control descriptors as the payload dict
    the animation bridge reads.

    Every ``*_to_sc_animation_events`` converter answers in this shape —
    the one :func:`convert_score_to_sc_animation_events` already used. An
    animated figure template injects exactly one JSON blob, so
    ``controlData`` has to ride inside the payload: a bare list reaches
    ``_animation_bridge.js`` as ``controlData = null``, and the widget
    then plays the enveloped pfield at its baked onset value — for a
    ``0 -> 1 -> 0`` swell, silence.
    """
    from klotho.utils.playback.supersonic.engine import serialize_control_data
    control_data = _build_score_control_data(list(descriptors), block_size)
    return {"events": events, "controlData": serialize_control_data(control_data)}


def temporal_unit_to_sc_animation_events(obj, use_absolute_time=False, amp=None, extra_pfields=None):
    """Animation payload for a TemporalUnit.

    A bare TemporalUnit has no parameter layer, so its ``controlData`` is
    always empty; the payload shape still matches the other animation
    converters, so a caller never has to switch on the object type.
    """
    events = temporal_unit_to_sc_events(obj, use_absolute_time=use_absolute_time, amp=amp,
                                        extra_pfields=extra_pfields, animation=True)
    return _animation_payload(events)


def rhythm_tree_to_sc_animation_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    tu = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_sc_animation_events(tu, use_absolute_time=False, amp=amp,
                                                extra_pfields=extra_pfields)


def compositional_unit_to_sc_events(obj, extra_pfields=None, animation=False,
                                    use_absolute_time=False):
    events, _ = _compositional_unit_payload_parts(
        obj,
        extra_pfields=extra_pfields,
        animation=animation,
        use_absolute_time=use_absolute_time,
    )
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=animation)
    return events


def compositional_unit_to_sc_animation_events(obj, extra_pfields=None):
    """Animation payload for a CompositionalUnit, control envelopes included.

    Lowers with absolute times and rebases events *and* descriptors by one
    shared delta, so a ``control=True`` envelope stays on the note it was
    drawn over — and so ``plot(uc).play()`` plays what ``play(uc)`` plays.
    """
    events, descriptors = _compositional_unit_payload_parts(
        obj, extra_pfields=extra_pfields, animation=True, use_absolute_time=True,
    )
    events, descriptors = _shift_payload_to_zero(events, descriptors)
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=True)
    return _animation_payload(events, descriptors)


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


def temporal_sequence_to_sc_events(obj, extra_pfields=None, rebase_to_zero=True,
                                   amp=None):
    """Lower a TemporalUnitSequence to SC events.

    ``amp`` reaches bare :class:`TemporalUnit` members only, exactly as it
    does in :func:`_temporal_container_sc_animation_parts` (the ``plot``
    path this mirrors): a :class:`CompositionalUnit` carries its own
    parameter layer and sources ``amp`` from there.

    It is threaded rather than dropped because ``amp`` is reserved in
    ``_converter_base.KNOWN_KWARGS``, so ``extract_convert_kwargs``
    consumes it and it never survives as an extra pfield either. Dropping
    it here did not ignore the request, it destroyed it: ``play(uts,
    amp=0.2)`` used to lower at the 0.85 default, 12.6 dB above what was
    asked for, while ``play(ut, amp=0.2)`` and ``plot(uts, amp=0.2)``
    both honoured it.
    """
    events = []

    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(unit, extra_pfields=None))
        elif isinstance(unit, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(unit, use_absolute_time=True, amp=amp, extra_pfields=extra_pfields))
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(unit, extra_pfields=extra_pfields, rebase_to_zero=False, amp=amp))
        elif isinstance(unit, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(unit, extra_pfields=extra_pfields, rebase_to_zero=False, amp=amp))

    events = sort_sc_assembly_events(events)
    if rebase_to_zero:
        _shift_events_to_zero(events)
    return events


def temporal_block_to_sc_events(obj, extra_pfields=None, rebase_to_zero=True,
                                amp=None):
    """Lower a TemporalBlock to SC events.

    ``amp`` behaves exactly as in :func:`temporal_sequence_to_sc_events`.
    """
    events = []

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row, extra_pfields=None))
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True, amp=amp, extra_pfields=extra_pfields))
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row, extra_pfields=extra_pfields, rebase_to_zero=False, amp=amp))
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row, extra_pfields=extra_pfields, rebase_to_zero=False, amp=amp))

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


def _temporal_container_sc_animation_parts(obj, amp=None, extra_pfields=None):
    """Build SC animation events and control descriptors for a UTS/BT with
    global step indices.

    Traverses members in structural (DFS) order — the same enumeration
    used by the timeline SVG renderer — assigning each leaf-unit's local
    step indices a running global offset. Times stay absolute; the caller
    rebases events and descriptors together.

    Returns
    -------
    tuple of (list, list, int)
        ``(events, control_descriptors, total_steps)``.
    """
    events = []
    descriptors = []
    step_offset = 0

    for member in obj:
        if isinstance(member, CompositionalUnit):
            sub, sub_descriptors = _compositional_unit_payload_parts(
                member, extra_pfields=None, animation=True, use_absolute_time=True)
            n_steps = len(member._rt.leaf_nodes)
        elif isinstance(member, TemporalUnit):
            sub = temporal_unit_to_sc_events(member, use_absolute_time=True, amp=amp,
                                             extra_pfields=extra_pfields, animation=True)
            sub_descriptors = []
            n_steps = len(member._rt.leaf_nodes)
        elif isinstance(member, (TemporalUnitSequence, TemporalBlock)):
            sub, sub_descriptors, n_steps = _temporal_container_sc_animation_parts(
                member, amp=amp, extra_pfields=extra_pfields)
        else:
            raise TypeError(
                f"Unsupported member type in temporal container: {type(member).__name__}"
            )
        _shift_sc_step_indices(sub, step_offset)
        _merge_sub_sc(events, sub)
        descriptors.extend(sub_descriptors)
        step_offset += n_steps

    return events, descriptors, step_offset


def temporal_container_to_sc_animation_events(obj, amp=None, extra_pfields=None):
    """Animation payload for a TemporalUnitSequence or TemporalBlock.

    Events carry absolute times (rebased so the payload starts at zero)
    and a global ``_stepIndex`` matching the timeline renderer's step
    enumeration. Control-envelope descriptors contributed by member
    CompositionalUnits ride along in ``controlData``, rebased by the same
    delta — so ``plot(container).play()`` plays what ``play(container)``
    plays.
    """
    events, descriptors, _ = _temporal_container_sc_animation_parts(
        obj, amp=amp, extra_pfields=extra_pfields)
    events = sort_sc_assembly_events(events)
    events, descriptors = _shift_payload_to_zero(events, descriptors)
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=True)
    return _animation_payload(events, descriptors)


_SC_CONVERT_HANDLERS = {
    'pitch': pitch_to_sc_events,
    'spectrum': spectrum_to_sc_events,
    'rhythm_tree': rhythm_tree_to_sc_events,
    'temporal_sequence': temporal_sequence_to_sc_events,
    'temporal_block': temporal_block_to_sc_events,
    'compositional_unit': compositional_unit_to_sc_events,
    'temporal_unit': temporal_unit_to_sc_events,
    'chord_sequence': chord_sequence_to_sc_events,
    'scale': scale_to_sc_events,
    'chord': chord_to_sc_events,
    'pitch_collection': pitch_collection_to_sc_events,
}


def convert_to_sc_events(obj, **kwargs):
    from klotho.thetos.instruments.base import reset_kit_rotations
    reset_kit_rotations()
    events = dispatch_convert(obj, kwargs, _SC_CONVERT_HANDLERS,
                              include_inst=True)
    # Backstop only. Every type that can carry a ``speaker`` today is a
    # CompositionalUnit, and those are already refused inside
    # _compositional_unit_payload_parts, which this path also reaches. Kept
    # so a type that GAINS mfield storage later is refused here rather than
    # shipping a label the browser ignores.
    _refuse_bare_speaker(events)
    return events


def _refuse_bare_speaker(events) -> None:
    """Refuse a ``speaker`` mfield on the bare (track-less) playback path.

    A speaker label only means something against a declared array, and an
    array is declared on a Score's track -- a bare ``play(unit)`` has no
    tracks, so there is nothing to resolve the label against and nothing to
    set the bus width. Silently ignoring it would drop the whole spatial
    intent of the material without a word.

    Called from TWO places, and the second one is the load-bearing one:

    * :func:`_compositional_unit_payload_parts` -- the single funnel for
      every bare UC lowering, so it covers ``play(uc)``,
      ``plot(uc).play()``, and the same through a UTS/BT.
    * :func:`convert_to_sc_events` -- a backstop for future types.

    Until 2026-09-01 only the backstop existed, and nothing reaching it had
    mfield storage: the guard was dead for exactly the type it was written
    for, and ``play(uc)`` shipped ``{'speaker': 7, 'speakerLane': None}``
    to a scheduler that reads ``ev.speakerLane || 0``. The Score path never
    comes through either call site (see :func:`_lower_score_uc` /
    :func:`_apply_spatial_routing`), so a voice that HAS an array to
    resolve against is never touched by this.
    """
    if not isinstance(events, list):
        return
    for event in events:
        if not isinstance(event, dict):
            continue
        speaker = event.get('speaker')
        if speaker is None:
            continue
        raise ValueError(
            f"speaker={speaker!r} needs a Score: the speaker array and the "
            f"bus width it implies are declared on a track, and a bare "
            f"play()/plot() has no tracks. Wrap it:\n"
            f"    score = Score()\n"
            f"    score.track('array', speakers=PAVILION)\n"
            f"    score.add(unit, track='array')\n"
            f"    play(score)"
        )


_SC_EVENT_PRIORITY = {'new': 0, 'set': 1, 'release': 2}


def _iter_ucs(unit):
    """Yield every :class:`CompositionalUnit` contained in a (possibly
    nested) temporal structure.

    Bare :class:`TemporalUnit` nodes are not expected inside a
    :class:`~klotho.thetos.composition.score.Score` — they are promoted
    on ``Score.add``.

    Containers are walked through their **public** iterators, exactly as
    :func:`temporal_block_to_sc_events` does. ``TemporalBlock.__iter__``
    validates the block's alignment on the way out (``_ensure_aligned``);
    reaching into ``_rows`` skips that, so a block whose row was grown or
    shrunk through the row's own API would be played at its stale offsets
    while every other reader of the same object reported the new ones.
    """
    if isinstance(unit, CompositionalUnit):
        yield unit
    elif isinstance(unit, TemporalUnitSequence):
        for member in unit:
            yield from _iter_ucs(member)
    elif isinstance(unit, TemporalBlock):
        for row in unit:
            yield from _iter_ucs(row)


# ---------------------------------------------------------------------------
# Spatial routing: speaker labels -> bus lanes
# ---------------------------------------------------------------------------


def _track_spec_for(score, group):
    """The track spec an event with this ``group`` actually plays through.

    Mirrors the scheduler's own resolution exactly --
    ``trackMap[group] -> default -> main`` -- so a typo in a group name
    lands its events on the main chain here for the same reason it does in
    the browser.  Getting this wrong in either direction would validate a
    voice against a track it does not play on.
    """
    tracks = getattr(score, '_tracks', None) or {}
    for key in (group, 'default', 'main'):
        if key in tracks:
            return tracks[key]
    return None


def _spatial_labels(spec):
    """Declared speaker labels of a track spec, or ``None`` if not spatial."""
    return spec.get('labels') if spec else None


def _refuse_speaker_without_array(group, speaker):
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    return ValueError(
        f"speaker={speaker!r} was set on a voice playing through {where}, "
        f"which has no speaker array, so there is no lane {speaker!r} to "
        f"route it to. Declare the array on the track "
        f"(score.track({'main' if group in ('default', 'main') else group!r}, "
        f"speakers=PAVILION)), or drop speaker= to leave the voice in stereo."
    )


def _refuse_missing_speaker(group, labels, def_name):
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    return ValueError(
        f"a voice on {def_name!r} plays through {where}, which declares "
        f"{len(labels)} speakers, but names no speaker -- so Klotho does not "
        f"know which of them it comes out of, and will not pick one for you. "
        f"Set the speaker mfield (uc.set(uc.leaves, speaker={labels[0]!r}), or "
        f"uc.set_mfields(...)), or put this voice on a track with no speaker "
        f"array. Note set_pfields(speaker=...) does NOT route: speaker is an "
        f"engine meta-field, like group."
    )


def _refuse_unknown_speaker(group, labels, speaker):
    from klotho.thetos.composition.score import _format_labels
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    return ValueError(
        f"no speaker labelled {speaker!r} on {where}. Known speakers: "
        f"{_format_labels(labels)}. (Speakers are addressed by the label you "
        f"declared, not by a 0-based index.)"
    )


def _refuse_unknown_width(def_name, group, speaker):
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    return ValueError(
        f"instrument {def_name!r} at speaker {speaker!r} on {where} has no "
        f"recorded channel count, so Klotho cannot tell how many speakers it "
        f"occupies. Bundled SynthDefs record their width in assets/io.json; a "
        f"SynthDef registered at runtime records it via register_synthdef(). "
        f"Add it there, or play this voice on a track with no speaker array."
    )


def _refuse_lane_overrun(def_name, group, speaker, labels, lane, outs):
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    span = labels[lane:lane + outs]
    listed = ', '.join(repr(x) for x in span)
    return ValueError(
        f"instrument {def_name!r} writes {outs} channels, so it occupies "
        f"{outs} adjacent speakers starting at the one it names. Speaker "
        f"{speaker!r} on {where} leaves only {len(span)} ({listed}), because "
        f"the array ends at {labels[-1]!r} -- {len(labels)} speakers in all. "
        f"Use a 1-channel SynthDef for a point source at the last speaker, or "
        f"name a speaker with {outs - 1} more above it."
    )


def _refuse_pan_on_point_source(def_name, group, speaker):
    where = ("the master chain ('main')" if group in ('default', 'main')
             else f"track {group!r}")
    return ValueError(
        f"{def_name!r} writes 1 channel, so it has no stereo image to pan: at "
        f"speaker {speaker!r} on {where} it is a point source. Drop pan, or "
        f"use a 2-channel SynthDef, which occupies two adjacent speakers and "
        f"pans between them."
    )


def _apply_spatial_routing(score, events) -> None:
    """Resolve every event's ``speaker`` label to a bus lane, in place.

    One pass, after both lowering paths have stamped their final ``group``,
    because this is the first moment an event's track is settled and the
    only layer that knows what tracks exist.  Nothing here is left for
    JavaScript: the scheduler adds ``speakerLane`` to the track's bus and
    trusts it, exactly as it trusts ``meta.groups`` today.

    ``new`` events carry the ``defName`` and so are where every check
    happens.  ``set`` and ``release`` target a node that already exists,
    and an engine mfield cannot change on a live node, so they inherit
    their head's lane rather than resolving one of their own -- which is
    also what stops a slur from walking across the array mid-note.
    """
    from klotho.thetos.instruments._shared import ss_synth_channels

    # id -> (speaker, lane, defName, outs) for every spawned node.
    heads: dict = {}
    for event in events:
        if event.get('type') != 'new':
            continue
        # A rest carries no sound, so it has no speaker to come out of.
        # The animation payload keeps ``__rest__`` as a step marker (and
        # ``_lower_score_uc`` appends it BEFORE the ``group`` stamp, so it
        # arrives here reading 'default' -> 'main'); the scheduler's
        # ``_bundleNew`` returns on ``__rest__`` before it ever looks at
        # ``speakerLane``.  Without this, plot(score) on a spatial score
        # containing a rest refused the score and named '__rest__' as the
        # instrument the composer had to set a speaker on.
        if event.get('defName') == '__rest__':
            continue
        group = event.get('group', 'default')
        labels = _spatial_labels(_track_spec_for(score, group))
        speaker = event.get('speaker', None)

        if labels is None:
            if speaker is not None:
                raise _refuse_speaker_without_array(group, speaker)
            continue

        def_name = event.get('defName')
        if speaker is None:
            raise _refuse_missing_speaker(group, labels, def_name)

        spec = _track_spec_for(score, group)
        lanes = spec['lanes']
        if speaker not in lanes:
            raise _refuse_unknown_speaker(group, labels, speaker)
        lane = lanes[speaker]

        _, outs = ss_synth_channels(def_name)
        if outs is None or outs < 1:
            raise _refuse_unknown_width(def_name, group, speaker)
        if lane + outs > len(labels):
            raise _refuse_lane_overrun(def_name, group, speaker, labels,
                                       lane, outs)
        if outs == 1 and 'pan' in (event.get('pfields') or {}):
            raise _refuse_pan_on_point_source(def_name, group, speaker)

        event['speakerLane'] = lane
        heads[event['id']] = (speaker, lane, def_name, outs)

    for event in events:
        if event.get('type') == 'new':
            continue
        head = heads.get(event.get('id'))
        if head is None:
            continue
        speaker, lane, def_name, outs = head
        if outs == 1 and 'pan' in (event.get('pfields') or {}):
            raise _refuse_pan_on_point_source(
                def_name, event.get('group', 'default'), speaker)
        event['speaker'] = speaker
        event['speakerLane'] = lane


def _refuse_narrower_main(score, spatial) -> None:
    """Refuse a ``main`` whose declared array is narrower than a track's.

    Every track sums into main, so main's buses are built at the WIDEST
    declared width -- that is the one place the whole array exists at once.
    A ``main`` that declares an array of its own does not change that; it
    only makes the browser's existing warning (which tests
    ``spatial.widths['main'] == null``) stop firing.  Two things then go
    wrong at once, and both are SILENT:

    * **main's inserts were checked against the wrong width.**
      ``Score.track`` validates an insert against ``len(labels)`` -- main's
      own array -- and the chain is then built at ``mainWidth``.  Measured
      on the shipped defs: ``score.track('main', speakers=['L', 'R'],
      inserts=[SynthDefFX('kl_reverb')])`` beside a 24-speaker track puts a
      2-in/2-out reverb writing fxBus 120-121 onto a chain whose decoder
      reads 120-143.  Twenty-two speakers go silent, with no error and no
      warning, at a concert.
    * **main loses the headphone fold.**  ``scheduler_score.js`` breaks the
      decoder tie in main's favour only when main is AS WIDE as the widest
      track (``chosen = widest.indexOf('main') !== -1 ? 'main' : ...``), so
      a narrower main is not in the tie at all and the geometry the
      composer declared on the master chain is quietly replaced by another
      track's.

    Refused in Python, at lowering, because that is where the composer can
    read it: the same refusal thrown in the browser dies as an unhandled
    promise rejection and reaches nobody.  A ``main`` that declares NO
    array is untouched -- that is the ordinary shape, it is what the
    browser warning already covers, and refusing it would break every
    score that declares its rig on one track.
    """
    main = spatial.get('main')
    if main is None:
        return
    # The width main's chain is actually BUILT at, computed the way the
    # scheduler computes it: the widest declared track, but never narrower
    # than a stereo pair (``mainWidth`` starts at ``BUS_CHANNELS``). The
    # floor matters -- a lone ``speakers=[1]`` on main leaves lane 1 of a
    # two-channel chain unwritten with no track anywhere to blame for it.
    built = max(list(spatial.values()) + [2])
    if main >= built:
        return
    others = {n: w for n, w in spatial.items() if n != 'main' and w == built}
    widest_name = next(iter(others), None)
    widener = (
        f"track {widest_name!r} declares {built}, and every track sums into "
        f"main"
        if widest_name is not None else
        f"a master chain is never narrower than a stereo pair"
    )
    inserts = (getattr(score, '_tracks', None) or {}).get('main', {})
    n_inserts = len(inserts.get('inserts') or ())
    if n_inserts:
        damage = (
            f"Main's {n_inserts} insert(s) were width-checked against "
            f"{main} channel(s) and will be placed on the {built}-channel "
            f"chain, where they read and write {main} lane(s) and leave the "
            f"other {built - main} of main's post-FX bus UNWRITTEN -- those "
            f"speakers play SILENTLY, with nothing downstream to say so. ")
    elif widest_name is not None:
        damage = (
            f"Main is also out of the decoder tie-break -- it is picked only "
            f"when it is as wide as the widest track -- so the headphone fold "
            f"would use {widest_name!r}'s geometry and not the array declared "
            f"here, SILENTLY substituting one for the other. ")
    else:
        damage = (
            f"Nothing is as wide as the chain main is built at, so the "
            f"decoder tie-break selects no track at all and the score gets NO "
            f"headphone fold -- reported as 'labels but no positions', which "
            f"is not what happened. ")
    remedy = (
        f"speakers=<the {built}-speaker array>"
        if widest_name is not None else
        f"speakers=<at least {built} labels>")
    raise ValueError(
        f"track 'main' declares {main} speaker(s) but {widener} -- so main's "
        f"chain is built {built} channels wide and the {main}-speaker array "
        f"declared on it describes only lanes 0..{main - 1} of it. {damage}"
        f"Declare main at the full array -- score.track('main', {remedy}, "
        f"...) -- or take the array off main with score.track('main', "
        f"speakers=[]) and let it be widened to fit, which is what a master "
        f"chain with no speakers= of its own already does.")


def _build_spatial_meta(score) -> dict:
    """Build ``meta.spatial``, or ``{}`` when the score has no spatial track.

    Arrays are deduplicated: two tracks declared against the same speakers
    share one entry, so a 24-speaker coefficient table is serialized once.

    Cross-track width invariants are checked here rather than in
    ``Score.track``, because this is the first moment every track is
    declared: ``score.track('main', speakers=['L', 'R'])`` is not wrong
    until some later cell declares a wider one, and a check at declaration
    would have to guess which of the two calls the composer meant.
    """
    tracks = getattr(score, '_tracks', None) or {}
    spatial = [(name, data) for name, data in tracks.items()
               if data.get('labels') is not None]
    if not spatial:
        return {}

    arrays: dict = {}
    by_key: dict = {}
    track_meta: dict = {}
    for name, data in spatial:
        labels = data['labels']
        array = data.get('speakers')
        key = (id(array), tuple(labels)) if array is not None else \
            (None, tuple(labels))
        array_id = by_key.get(key)
        if array_id is None:
            array_id = _array_id(array, labels, arrays)
            by_key[key] = array_id
            arrays[array_id] = _array_meta(array, labels)
        track_meta[name] = {"array": array_id, "width": len(labels)}
    _refuse_narrower_main(
        score, {name: entry['width'] for name, entry in track_meta.items()})
    return {"arrays": arrays, "tracks": track_meta}


def _array_id(array, labels, taken) -> str:
    base = getattr(array, 'name', None) if array is not None else None
    base = str(base) if base else 'array'
    candidate = base
    n = 2
    while candidate in taken:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def _array_meta(array, labels) -> dict:
    """One array's entry in ``meta.spatial.arrays``.

    ``positions``/``decoder`` are ``null`` for a labels-only declaration.
    That is the honest answer -- a routing-only array has no geometry --
    and the consumer must treat it as "no binaural fold available", never
    as an array at the origin.
    """
    entry: dict = {
        "name": (getattr(array, 'name', None) if array is not None else None),
        "labels": list(labels),
        "width": len(labels),
        "positions": None,
        "units": None,
        "speedOfSound": None,
        "decoder": None,
    }
    if array is None:
        return entry

    from klotho.thetos.spatial import (
        BINAURAL_FIELDS, BINAURAL_STRIDE, DECODER_MAX_DELAY_S,
    )
    entry["positions"] = [list(p) for p in array.positions]
    entry["units"] = array.units
    entry["speedOfSound"] = array.speed_of_sound
    coeffs = array.binaural_coefficients(max_delay=DECODER_MAX_DELAY_S)
    entry["decoder"] = {
        "kind": "binaural",
        "listener": list(coeffs.listener),
        "facing": coeffs.facing,
        "headHalf": coeffs.head_half,
        "fields": list(BINAURAL_FIELDS),
        "stride": BINAURAL_STRIDE,
        "maxDelay": DECODER_MAX_DELAY_S,
        "coefficients": list(coeffs.flat()),
    }
    return entry


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
    # Omitted when unused, exactly as ``groups`` and ``inserts`` are. A
    # non-spatial score's payload must be byte-identical to what it was
    # before this key existed -- an always-present ``"spatial": {}`` would
    # move every payload in the world for no one's benefit.
    spatial = _build_spatial_meta(score)
    if spatial:
        meta["spatial"] = spatial
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
        # ``curve_window`` is the slice of the curve this descriptor carries.
        # An unsplit envelope carries all of it; a descriptor produced by an
        # instrument split carries only its own part, and sampling the WHOLE
        # curve for each half is what made a split envelope play one full
        # hairpin per half instead of the single gesture the composer drew.
        window_start, window_end = desc.get("curve_window") or (0.0, 1.0)
        if total <= 0:
            samples = np.full(block_size, float(env.values[0]), dtype=np.float32)
        else:
            sample_times = np.linspace(window_start * total, window_end * total,
                                       block_size, dtype=np.float64)
            samples = np.array(env.sample(sample_times), dtype=np.float32)
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
            "curve_window": desc.get("curve_window") or (0.0, 1.0),
        })
    return control_descriptors


def _lower_score_uc(uc, track_override, animation=False):
    """Lower one UC to SC events + collect per-envelope targets.

    Returns a tuple ``(events, control_descriptors)`` where each event
    carries its ``group`` (from *track_override* or its own ``group``
    mfield), all event IDs are freshly regenerated (so that the same UC
    can appear in multiple items without uid collisions), and control
    descriptors are already re-keyed against the fresh IDs.

    With ``animation=True`` the lowering stamps per-leaf ``_stepIndex``
    metadata and keeps ``__rest__`` events (they carry step indices too);
    absolute times are preserved either way.
    """
    from klotho.utils.playback._sc_assembly import (
        lower_compositional_ir_to_sc_assembly,
    )

    assembly_events, node_to_event_ids = lower_compositional_ir_to_sc_assembly(
        uc,
        extra_pfields=None,
        animation=animation,
        use_absolute_time=True,
        default_synth='kl_tri',
        normalize_sc_pfields=False,
        sort_output=True,
        return_node_map=True,
    )

    id_map: dict[str, str] = {}
    events: list[dict] = []

    for event in assembly_events:
        if event.get("defName") == "__rest__":
            if animation:
                events.append(event)
            continue

        event_type = event.get("type")

        if track_override is not None:
            event["group"] = track_override
        elif "group" not in event:
            event["group"] = "default"

        if event_type == "new":
            new_uid = fast_id()
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
    # Lane routing, stamped only when set -- same conditional shape as
    # ``group``, so a non-spatial payload gains no key. Validated against
    # the track's declared array by ``_apply_spatial_routing``.
    speaker = event.mfields.get('speaker')

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
        uid = fast_id()
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
        if not is_hold:
            # Precedence (WL-36, path 3): an explicitly authored
            # duration/dur in user_pf WINS -- injection only fills a slot
            # the user left empty. Same as path 1b (string-instrument CU);
            # OPPOSITE of paths 1 and 2, where injection wins. Pinned by
            # tests/test_sampler_kit.py::TestScoreNewKit::test_explicit_duration_overrides_injection;
            # _sc_assembly._duration_inject_key states the whole picture.
            if 'duration' in v_inst_pfields and 'duration' not in user_pf:
                pf['duration'] = voice["duration"]
            elif not v_has_gate and 'dur' in v_inst_pfields and 'dur' not in user_pf:
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
        if speaker is not None:
            new_event["speaker"] = speaker
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
    from klotho.thetos.instruments.base import reset_kit_rotations

    # Family round-robin counters (loose-Event lowering) restart per
    # conversion so replaying a score renders identically.
    reset_kit_rotations()

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

    # Once, after every item has stamped its final `group` -- that is the
    # first moment an event's track, and so its speaker array, is settled.
    _apply_spatial_routing(score, all_events)

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


def _payload_sample_assets(events):
    """Sample assets referenced by ``buf*`` pfields, keyed by name.

    Same discovery rule as ``SuperSonicEngine._needed_samples``; used by
    the animated plot(score) payload, which travels as JSON.
    """
    from klotho.utils.playback.supersonic.samples import (
        sample_info, sample_bytes_b64,
    )
    names = set()
    for ev in events:
        pfields = ev.get("pfields")
        if not isinstance(pfields, dict):
            continue
        for key, val in pfields.items():
            if isinstance(val, str) and key.startswith('buf'):
                names.add(val)
    return {
        name: {"b64": sample_bytes_b64(name),
               "channels": sample_info(name)["channels"]}
        for name in sorted(names)
    }


def convert_score_to_sc_animation_events(score) -> dict:
    """Score payload with global ``_stepIndex`` metadata for plot(score).

    Mirrors :func:`convert_score_to_sc_events` (same item walk, same
    negative-time pre-shift, same uid regeneration) but lowers each UC in
    animation mode — keeping ``__rest__`` step markers — and assigns a
    running global step offset per item: UCs contribute one step per
    rhythm-tree leaf (in the same DFS order the Score SVG renderer
    enumerates), loose Events contribute one step each. ``meta`` and the
    JSON-safe ``controlData`` / ``sampleAssets`` ride along so the
    animated widget's bridge can drive tracks, insert FX, control
    envelopes, and samples exactly like the standalone widget.

    Returns
    -------
    dict
        ``{"events", "meta", "controlData", "sampleAssets"}``.
    """
    from klotho.chronos.temporal_units.temporal import _reoffset
    from klotho.utils.playback.supersonic.engine import serialize_control_data
    from klotho.thetos.instruments.base import reset_kit_rotations

    # Same reset as convert_score_to_sc_events: keeps play(score) and
    # plot(score).play() byte-identical for family round-robin kits.
    reset_kit_rotations()

    all_events: list[dict] = []
    control_descriptors: list[dict] = []
    step_offset = 0

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
                ev_list = _lower_score_event(item)
                leader_marked = False
                for ev in ev_list:
                    ev["_stepIndex"] = step_offset
                    if ev.get("type") == "new" and not leader_marked:
                        ev["_animate"] = True
                        leader_marked = True
                all_events.extend(ev_list)
                step_offset += 1
                continue
            for uc in _iter_ucs(item.unit):
                uc_events, uc_ctrl = _lower_score_uc(uc, item.track,
                                                     animation=True)
                _shift_sc_step_indices(uc_events, step_offset)
                step_offset += len(uc._rt.leaf_nodes)
                all_events.extend(uc_events)
                control_descriptors.extend(uc_ctrl)
    finally:
        if pre_shift:
            for item in items:
                _reoffset(item.unit, item.unit._offset - pre_shift)

    all_events.sort(
        key=lambda e: (e["start"], _SC_EVENT_PRIORITY.get(e["type"], 3))
    )

    # The same pass convert_score_to_sc_events runs, for the same reason.
    # plot(score).play() must sound identical to play(score); without this
    # the animated payload would carry a speaker LABEL and no lane, and
    # every voice would land on lane 0 of its track.
    _apply_spatial_routing(score, all_events)

    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(all_events, animation=True)

    block_size = getattr(score, "_block_size", _DEFAULT_SCORE_BLOCK_SIZE)
    control_data = _build_score_control_data(control_descriptors, block_size)

    return {
        "events": all_events,
        "meta": _build_score_meta(score),
        "controlData": serialize_control_data(control_data),
        "sampleAssets": _payload_sample_assets(all_events),
    }


def _compositional_unit_payload_parts(obj, extra_pfields=None, animation=False,
                                      use_absolute_time=False):
    """Lower a bare UC to ``(events, control_descriptors)``.

    Events keep their assembly uids (no Score-style regeneration) and
    absolute times; descriptors are keyed against those uids via the
    node→event-id map.

    This is the single UC lowering for every non-Score surface — bare
    ``play`` and the animated ``plot(...).play()`` alike. Splitting them
    is what let the animation path return events with no descriptors, so
    a ``control=True`` swell auditioned at its baked onset value (0.0,
    i.e. silence) while ``play`` rendered the curve. Callers that do not
    want the descriptors drop them; they must not lower separately.

    Being that single funnel is also why :func:`_refuse_bare_speaker` is
    called here rather than at each entry point. A ``CompositionalUnit``
    is the ONLY playable type with mfield storage, so it is the only
    thing that can emit a ``speaker`` key at all — and the guard used to
    be called from :func:`convert_to_sc_events` alone, which ``play(uc)``
    and ``plot(uc).play()`` never reach. The guard was therefore dead for
    exactly the type it was written for, and a spatial UC played
    track-less collapsed onto lane 0 in silence (``scheduler_core.js``
    reads ``ev.speakerLane || 0`` and ignores ``speaker``). The Score
    path does not come through here — it lowers via
    :func:`_lower_score_uc` and resolves labels to lanes in
    :func:`_apply_spatial_routing` — so nothing that has an array to
    resolve against is refused.

    Parameters
    ----------
    obj : CompositionalUnit
        Unit to lower.
    extra_pfields : dict, optional
        Extra pfields merged into every event.
    animation : bool, default False
        Keep ``__rest__`` step markers and stamp per-leaf ``_stepIndex``.
    use_absolute_time : bool, default False
        Under ``animation=True``, keep absolute event times instead of
        rebasing to the unit's own zero. Descriptor times are always
        absolute, so a caller that rebases must rebase both together —
        see :func:`_shift_payload_to_zero`.
    """
    events, node_to_event_ids = lower_compositional_ir_to_sc_assembly(
        obj,
        extra_pfields=extra_pfields,
        animation=animation,
        use_absolute_time=use_absolute_time,
        default_synth=DEFAULT_COMPOSITION_SYNTH,
        normalize_sc_pfields=True,
        sort_output=True,
        return_node_map=True,
    )
    _refuse_bare_speaker(events)
    descriptors = _collect_control_descriptors(obj, node_to_event_ids)
    return events, descriptors


def _container_payload_parts(obj, extra_pfields=None, amp=None):
    """Recursively lower a UTS/BT to ``(events, control_descriptors)``
    with absolute (un-rebased) times.

    Mirrors :func:`temporal_sequence_to_sc_events` /
    :func:`temporal_block_to_sc_events` member handling (UC members get
    no extra_pfields; bare TemporalUnits keep their absolute times), and
    threads ``amp`` to bare TemporalUnit members the same way they do --
    this is the path ``play(uts)`` actually takes, so an ``amp`` honoured
    there and dropped here would still be inaudible in the widget.
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
                unit, use_absolute_time=True, amp=amp,
                extra_pfields=extra_pfields
            ))
        elif isinstance(unit, (TemporalUnitSequence, TemporalBlock)):
            ev, desc = _container_payload_parts(
                unit, extra_pfields=extra_pfields, amp=amp)
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

    This is the path ``player.play`` takes for a UC/UTS/BT, so two things
    that used to be true only of :func:`convert_to_sc_events` are true
    here as well: ``amp=`` reaches bare TemporalUnit members instead of
    being consumed and discarded, and a ``speaker`` mfield with no Score
    to resolve it against is refused rather than shipped to a scheduler
    that ignores it.
    """
    from klotho.utils.playback._sc_validate import validate_sc_events
    from klotho.thetos.instruments.base import reset_kit_rotations

    reset_kit_rotations()
    if isinstance(obj, CompositionalUnit):
        events, descriptors = _compositional_unit_payload_parts(obj)
    elif isinstance(obj, (TemporalUnitSequence, TemporalBlock)):
        kw = extract_convert_kwargs(kwargs)
        events, descriptors = _container_payload_parts(
            obj, extra_pfields=kw['extra_pfields'], amp=kw['amp']
        )
        events = sort_sc_assembly_events(events)
        events, descriptors = _shift_payload_to_zero(events, descriptors)
    else:
        events = convert_to_sc_events(obj, **kwargs)
        descriptors = []

    validate_sc_events(events)
    control_data = _build_score_control_data(descriptors, block_size)
    return {"events": events, "control_data": control_data}


