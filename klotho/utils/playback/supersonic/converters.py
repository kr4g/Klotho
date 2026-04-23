from uuid import uuid4
import json
from pathlib import Path

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
_SS_MANIFEST_PATH = Path(__file__).resolve().parent / "assets" / "manifest.json"
_SS_RELEASE_MODE_CACHE = None


def _uid():
    return uuid4().hex


def _release_mode_for_synth(def_name):
    global _SS_RELEASE_MODE_CACHE
    if _SS_RELEASE_MODE_CACHE is None:
        _SS_RELEASE_MODE_CACHE = {}
        try:
            data = json.loads(_SS_MANIFEST_PATH.read_text())
            synths = data.get("synths", {})
            for name, meta in synths.items():
                mode = (meta.get("releaseMode") or "gate").lower()
                _SS_RELEASE_MODE_CACHE[name] = mode if mode in ("gate", "free") else "gate"
        except Exception:
            _SS_RELEASE_MODE_CACHE = {}
    return _SS_RELEASE_MODE_CACHE.get(def_name, "gate")


def _synth_needs_release(def_name):
    return _release_mode_for_synth(def_name) == "gate"


def _gated_note(uid, synth, start, dur, pfields, step_index=None, extra_pfields=None):
    pf = _merge_pfields(pfields, extra_pfields)
    events = []
    new_ev = {
        "type": "new",
        "id": uid,
        "defName": synth,
        "start": start,
        "pfields": pf,
    }
    if step_index is not None:
        new_ev["_stepIndex"] = step_index
    events.append(new_ev)

    if _synth_needs_release(synth):
        rel_ev = {
            "type": "release",
            "id": uid,
            "start": start + dur,
        }
        if step_index is not None:
            rel_ev["_stepIndex"] = step_index
        events.append(rel_ev)
    return events


def _perc_note(uid, synth, start, dur, pfields, step_index=None, extra_pfields=None):
    pf = _merge_pfields(pfields, extra_pfields)
    pf["dur"] = dur
    new_ev = {
        "type": "new",
        "id": uid,
        "defName": synth,
        "start": start,
        "pfields": pf,
    }
    if step_index is not None:
        new_ev["_stepIndex"] = step_index
    events = [new_ev]
    if _synth_needs_release(synth):
        rel_ev = {
            "type": "release",
            "id": uid,
            "start": start + dur,
        }
        if step_index is not None:
            rel_ev["_stepIndex"] = step_index
        events.append(rel_ev)
    return events


def pitch_to_sc_events(pitch, duration=None, amp=None, extra_pfields=None):
    dur = duration if duration is not None else 1.0
    uid = _uid()
    return _gated_note(uid, DEFAULT_PITCH_SYNTH, 0.0, dur, {
        "freq": pitch.freq,
        "amp": single_voice_amplitude(pitch.freq, amp),
    }, step_index=0, extra_pfields=extra_pfields)


def pitch_collection_to_sc_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u',
                                  amp=None, pause=0.0, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        if arp:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_seq_sc_events(pitches, 0, synth=DEFAULT_COLLECTION_SYNTH, amp=amp,
                                        total_dur=dur, pause=0.0, extra_pfields=extra_pfields)
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_COLLECTION_SYNTH,
                                          amp=amp, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_COLLECTION_SYNTH, amp=amp,
                                    per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields)


def scale_to_sc_events(obj, duration=None, equaves=1, amp=None, pause=0.0, extra_pfields=None):
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    all_pitches = scale_pitch_sequence(obj, equaves)
    return _build_seq_sc_events(all_pitches, 0, synth=DEFAULT_COLLECTION_SYNTH, amp=amp,
                                per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields)


def chord_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                       amp=None, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_COLLECTION_SYNTH, amp=amp,
                                    total_dur=dur, pause=0.0, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_COLLECTION_SYNTH,
                                      amp=amp, extra_pfields=extra_pfields)


def chord_sequence_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                                amp=None, pause=0.25, extra_pfields=None):
    events = []
    dur = duration if duration is not None else DEFAULT_CHORD_DURATION
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
            events.extend(_gated_note(uid, DEFAULT_COLLECTION_SYNTH, start_time,
                voice_dur, {
                    "freq": p.freq,
                    "amp": single_voice_amplitude(p.freq, amp),
                }, step_index=gi, extra_pfields=extra_pfields))
    else:
        for gi, vi, start_time, voice_dur, p in iter_group_sequence(groups, dur, arp=False, strum=strum, direction=direction, pause=pause):
            uid = _uid()
            events.extend(_gated_note(uid, DEFAULT_COLLECTION_SYNTH, start_time,
                voice_dur, {
                    "freq": p.freq,
                    "amp": group_voice_amps[gi][vi],
                }, step_index=gi, extra_pfields=extra_pfields))

    return events


def spectrum_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                          amp=None, extra_pfields=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SPECTRUM_SYNTH, amp=target,
                                    total_dur=dur, pause=0.0, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SPECTRUM_SYNTH,
                                      amp=target, extra_pfields=extra_pfields)


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


def compositional_unit_to_sc_events(obj, extra_pfields=None, animation=False):
    events = lower_compositional_ir_to_sc_assembly(
        obj,
        extra_pfields=extra_pfields,
        animation=animation,
        default_synth=DEFAULT_COMPOSITION_SYNTH,
        include_ungated_release=True,
        normalize_sc_pfields=True,
        sort_output=True,
    )
    from klotho.utils.playback._sc_validate import validate_sc_events
    validate_sc_events(events, animation=animation)
    return events


def compositional_unit_to_sc_animation_events(obj, extra_pfields=None):
    return compositional_unit_to_sc_events(obj, extra_pfields=extra_pfields, animation=True)


def _build_seq_sc_events(pitches, start, synth, amp=None, per_voice_dur=None,
                         total_dur=None, pause=0.0, extra_pfields=None):
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
        events.extend(_gated_note(uid, synth, cursor, voice_dur, {
            "freq": pitch.freq,
            "amp": single_voice_amplitude(pitch.freq, amp),
        }, step_index=i, extra_pfields=extra_pfields))
        cursor += voice_dur + max(0.0, pause)
    return events


def _build_chord_sc_events(pitches, start, dur, strum, synth, amp=None,
                           dur_factor=1.0, extra_pfields=None):
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
        events.extend(_gated_note(uid, synth, start + start_offset,
            (dur * dur_factor) - start_offset, {
                "freq": pitch.freq,
                "amp": voice_amps[i],
            }, step_index=i, extra_pfields=extra_pfields))
    return events


def _merge_sub_sc(target_events, sub_events, time_offset):
    for ev in sub_events:
        ev["start"] -= time_offset
    target_events.extend(sub_events)


def temporal_sequence_to_sc_events(obj, extra_pfields=None):
    events = []
    seq_offset = obj.start

    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(unit, extra_pfields=None), seq_offset)
        elif isinstance(unit, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(unit, use_absolute_time=True, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(unit, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(unit, extra_pfields=extra_pfields), seq_offset)

    return sort_sc_assembly_events(events)


def temporal_block_to_sc_events(obj, extra_pfields=None):
    events = []
    block_offset = obj.start

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row, extra_pfields=None), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.start)
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.start)

    return sort_sc_assembly_events(events)


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
    extra_pfields = kw['extra_pfields']

    if isinstance(obj, Pitch):
        return pitch_to_sc_events(obj, duration=duration, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, Spectrum):
        return spectrum_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                    amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_sc_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction,
                                    amp=amp, extra_pfields=extra_pfields)

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
                                           amp=amp, pause=(0.25 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, Scale):
        return scale_to_sc_events(obj, duration=duration, equaves=equaves, amp=amp,
                                  pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, (Chord, Voicing)):
        return chord_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_sc_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                                 direction=direction, amp=amp,
                                                 pause=0.0,
                                                 extra_pfields=extra_pfields)
        return pitch_collection_to_sc_events(obj, duration=duration, mode="sequential",
                                             amp=amp, pause=(0.0 if pause is None else pause),
                                             extra_pfields=extra_pfields)

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
        include_ungated_release=False,
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

        if _synth_needs_release(synth):
            rel_ev = {
                "type": "release",
                "id": uid,
                "start": start + dur,
            }
            if step is not None:
                rel_ev["_stepIndex"] = step
            rel_ev["_animate"] = animate
            if "_polyGroupId" in ev:
                rel_ev["_polyGroupId"] = ev["_polyGroupId"]
            if "_logicalStepId" in ev:
                rel_ev["_logicalStepId"] = ev["_logicalStepId"]
            if "_polyVoiceIndex" in ev:
                rel_ev["_polyVoiceIndex"] = ev["_polyVoiceIndex"]
            if "_polyVoiceCount" in ev:
                rel_ev["_polyVoiceCount"] = ev["_polyVoiceCount"]
            if "_polyLeader" in ev:
                rel_ev["_polyLeader"] = ev["_polyLeader"]
            sc_events.append(rel_ev)

    sc_events.sort(key=lambda e: e["start"])
    return sc_events
