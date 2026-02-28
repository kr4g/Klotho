from uuid import uuid4

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import SynthDefInstrument
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import (
    DEFAULT_NOTE_DURATION, DEFAULT_CHORD_DURATION,
    DEFAULT_SPECTRUM_DURATION, DEFAULT_DRUM_FREQ,
    KNOWN_KWARGS, freq_to_midi, perc_env_pfields,
    _get_addressed_collection, _merge_pfields,
    scale_pitch_sequence, extract_convert_kwargs,
)

DEFAULT_SYNTH = "sonic-pi-beep"
DEFAULT_SINE_SYNTH = "sonic-pi-beep"
DEFAULT_PERC_SYNTH = "sonic-pi-beep"


def _uid():
    return uuid4().hex


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
    rel_ev = {
        "type": "release",
        "id": uid,
        "start": start + dur,
    }
    if step_index is not None:
        rel_ev["_stepIndex"] = step_index
    return [new_ev, rel_ev]


def pitch_to_sc_events(pitch, duration=None, amp=None, extra_pfields=None):
    dur = duration if duration is not None else 1.0
    uid = _uid()
    return _gated_note(uid, DEFAULT_SYNTH, 0.0, dur, {
        "note": pitch.midi,
        "amp": single_voice_amplitude(pitch.freq, amp),
    }, step_index=0, extra_pfields=extra_pfields)


def pitch_collection_to_sc_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u',
                                  amp=None, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        if arp:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SYNTH, amp=amp,
                                        total_dur=dur, extra_pfields=extra_pfields)
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SYNTH,
                                          amp=amp, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SYNTH, amp=amp,
                                    per_voice_dur=dur, extra_pfields=extra_pfields)


def scale_to_sc_events(obj, duration=None, equaves=1, amp=None, extra_pfields=None):
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    all_pitches = scale_pitch_sequence(obj, equaves)
    return _build_seq_sc_events(all_pitches, 0, synth=DEFAULT_SYNTH, amp=amp,
                                per_voice_dur=dur, extra_pfields=extra_pfields)


def chord_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                       amp=None, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SYNTH, amp=amp,
                                    total_dur=dur, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SYNTH,
                                      amp=amp, extra_pfields=extra_pfields)


def chord_sequence_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                                amp=None, extra_pfields=None):
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
                events.extend(_gated_note(uid, DEFAULT_SYNTH, current_time + i * voice_dur,
                    voice_dur * 0.9, {
                        "note": p.midi,
                        "amp": single_voice_amplitude(p.freq, amp),
                    }, step_index=step, extra_pfields=extra_pfields))
            current_time += dur
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
                events.extend(_gated_note(uid, DEFAULT_SYNTH, current_time + start_offset,
                    (dur * 0.95) - start_offset, {
                        "note": p.midi,
                        "amp": voice_amps[i],
                    }, step_index=step, extra_pfields=extra_pfields))
            current_time += dur
            step += 1

    return events


def spectrum_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u',
                          amp=None, extra_pfields=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_seq_sc_events(pitches, 0, synth=DEFAULT_SINE_SYNTH, amp=target,
                                    total_dur=dur, extra_pfields=extra_pfields)
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SINE_SYNTH,
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
            "note": freq_to_midi(DEFAULT_DRUM_FREQ),
            "amp": target,
            **perc_env_pfields(dur),
        }
        events.extend(_perc_note(uid, DEFAULT_PERC_SYNTH, start, dur, pf,
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
    events = []
    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)}
                    if animation else None)

    time_offset = 0
    if animation:
        time_offset = min(ev.start for ev in obj if not ev.is_rest) if any(not ev.is_rest for ev in obj) else 0

    for event in obj:
        step_idx = node_to_step.get(event.node_id, None) if animation else None
        start = event.start - time_offset if animation else event.start

        if event.is_rest:
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

        instrument = obj.get_instrument(event.node_id)
        synth_name = DEFAULT_SYNTH
        env_type = ''

        if isinstance(instrument, SynthDefInstrument):
            synth_name = instrument.synth_name or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''
        elif instrument is not None:
            synth_name = getattr(instrument, 'synth_name', None) or getattr(instrument, 'name', None) or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''

        pfields = {k: v for k, v in event.pfields.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}

        if 'freq' in pfields and 'note' not in pfields:
            pfields['note'] = freq_to_midi(pfields['freq']) if isinstance(pfields['freq'], (int, float)) else pfields['freq']
        if 'amp' not in pfields:
            freq = pfields.get('freq', 440.0)
            if isinstance(freq, (int, float)):
                pfields['amp'] = single_voice_amplitude(freq)
            else:
                pfields['amp'] = 0.5

        uid = _uid()
        is_gated = env_type.lower() in ('sustained', 'sus', 'asr', 'adsr', '')
        dur = abs(event.duration)

        if is_gated:
            evts = _gated_note(uid, synth_name, start, dur, pfields,
                               step_index=step_idx, extra_pfields=extra_pfields)
        else:
            evts = _perc_note(uid, synth_name, start, dur, pfields,
                              step_index=step_idx, extra_pfields=extra_pfields)
        events.extend(evts)

    events.sort(key=lambda ev: ev["start"])
    return events


def compositional_unit_to_sc_animation_events(obj, extra_pfields=None):
    return compositional_unit_to_sc_events(obj, extra_pfields=extra_pfields, animation=True)


def _build_seq_sc_events(pitches, start, synth, amp=None, per_voice_dur=None,
                         total_dur=None, extra_pfields=None):
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

    for i, pitch in enumerate(pitches):
        uid = _uid()
        events.extend(_gated_note(uid, synth, start + i * voice_dur, voice_dur * 0.9, {
            "note": pitch.midi,
            "amp": single_voice_amplitude(pitch.freq, amp),
        }, step_index=i, extra_pfields=extra_pfields))
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
                "note": pitch.midi,
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
            _merge_sub_sc(events, compositional_unit_to_sc_events(unit, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(unit, use_absolute_time=True, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(unit, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(unit, extra_pfields=extra_pfields), seq_offset)

    events.sort(key=lambda ev: ev["start"])
    return events


def temporal_block_to_sc_events(obj, extra_pfields=None):
    events = []
    block_offset = obj.offset

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.offset)
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row, extra_pfields=extra_pfields), block_offset + row.offset)

    events.sort(key=lambda ev: ev["start"])
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
        return compositional_unit_to_sc_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_sc_events(obj, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, ChordSequence):
        return chord_sequence_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                           amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, Scale):
        return scale_to_sc_events(obj, duration=duration, equaves=equaves, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_sc_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                                 direction=direction, amp=amp, extra_pfields=extra_pfields)
        return pitch_collection_to_sc_events(obj, duration=duration, mode="sequential",
                                             amp=amp, extra_pfields=extra_pfields)

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
            sc_events.append(rest_ev)
            continue

        freq = pf.get("freq", 440.0)
        amp_val = pf.get("vel", pf.get("amp", 0.5))
        note = freq_to_midi(freq)

        synth = DEFAULT_PERC_SYNTH if instrument == "membrane" else DEFAULT_SYNTH

        if instrument == "membrane":
            pfields = {"note": note, "amp": amp_val, "dur": dur, **perc_env_pfields(dur)}
        else:
            pfields = {"note": note, "amp": amp_val}

        new_ev = {
            "type": "new",
            "id": uid,
            "synthName": synth,
            "start": start,
            "pfields": pfields,
        }
        if step is not None:
            new_ev["_stepIndex"] = step
        sc_events.append(new_ev)

        rel_ev = {
            "type": "release",
            "id": uid,
            "start": start + dur,
        }
        if step is not None:
            rel_ev["_stepIndex"] = step
        sc_events.append(rel_ev)

    sc_events.sort(key=lambda e: e["start"])
    return sc_events
