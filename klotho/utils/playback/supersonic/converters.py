from uuid import uuid4
import json
from pathlib import Path

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
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
    scale_pitch_sequence, extract_convert_kwargs,
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


def _release_mode_for_synth(synth_name):
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
    return _SS_RELEASE_MODE_CACHE.get(synth_name, "gate")


def _synth_needs_release(synth_name):
    return _release_mode_for_synth(synth_name) == "gate"


def _gated_note(uid, synth, start, dur, pfields, step_index=None, extra_pfields=None):
    pf = _merge_pfields(pfields, extra_pfields)
    events = []
    new_ev = {
        "type": "new",
        "id": uid,
        "synthName": synth,
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
        "synthName": synth,
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
                                        total_dur=dur, pause=pause, extra_pfields=extra_pfields)
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
                       amp=None, pause=0.0, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_COLLECTION_SYNTH, amp=amp,
                                    total_dur=dur, pause=pause, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_COLLECTION_SYNTH,
                                      amp=amp, extra_pfields=extra_pfields)


def chord_sequence_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                                amp=None, pause=0.25, extra_pfields=None):
    events = []
    current_time = 0.0
    step = 0

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            n = len(pitches)
            voice_dur = dur / max(1, n)
            for i, p in enumerate(pitches):
                uid = _uid()
                events.extend(_gated_note(uid, DEFAULT_COLLECTION_SYNTH, current_time + i * voice_dur,
                    voice_dur, {
                        "freq": p.freq,
                        "amp": single_voice_amplitude(p.freq, amp),
                    }, step_index=step, extra_pfields=extra_pfields))
            current_time += dur + max(0.0, pause)
            step += 1
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            freqs = [p.freq for p in pitches]
            voice_amps = compute_voice_amplitudes(freqs, amp)
            strum_val = max(0, min(1, strum))
            num = len(pitches)
            for i, p in enumerate(pitches):
                uid = _uid()
                start_offset = (strum_val * dur * i) / num if num > 1 else 0
                events.extend(_gated_note(uid, DEFAULT_COLLECTION_SYNTH, current_time + start_offset,
                    dur - start_offset, {
                        "freq": p.freq,
                        "amp": voice_amps[i],
                    }, step_index=step, extra_pfields=extra_pfields))
            current_time += dur + max(0.0, pause)
            step += 1

    return events


def spectrum_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                          amp=None, pause=0.0, extra_pfields=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SPECTRUM_SYNTH, amp=target,
                                    total_dur=dur, pause=pause, extra_pfields=extra_pfields)
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
        time_offset = min(c.start for c in obj if not c.is_rest) if any(not c.is_rest for c in obj) else 0

    for chronon in obj:
        start = chronon.start - time_offset
        dur = abs(chronon.duration)
        step_idx = node_to_step.get(chronon.node_id, None) if animation else None

        if chronon.is_rest:
            if animation:
                events.append({
                    "type": "new",
                    "id": _uid(),
                    "synthName": "__rest__",
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
    return lower_compositional_ir_to_sc_assembly(
        obj,
        extra_pfields=extra_pfields,
        animation=animation,
        default_synth=DEFAULT_COMPOSITION_SYNTH,
        include_ungated_release=True,
        normalize_sc_pfields=True,
        sort_output=True,
    )


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
    seq_offset = obj.offset

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
    block_offset = obj.offset

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row, extra_pfields=None), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.offset)
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.offset)

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
                                    amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_sc_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction,
                                    amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

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

    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_sc_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                                 direction=direction, amp=amp,
                                                 pause=(0.0 if pause is None else pause),
                                                 extra_pfields=extra_pfields)
        return pitch_collection_to_sc_events(obj, duration=duration, mode="sequential",
                                             amp=amp, pause=(0.0 if pause is None else pause),
                                             extra_pfields=extra_pfields)

    raise TypeError(f"Unsupported object type: {type(obj)}")


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
                "synthName": "__rest__",
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
            "synthName": synth,
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
