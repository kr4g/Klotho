from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.dynatos.dynamics import freq_amp_scale, ampdb
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import SynthDefInstrument
from uuid import uuid4

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 110.0

DEFAULT_SYNTH = "sonic-pi-beep"
DEFAULT_SINE_SYNTH = "sonic-pi-beep"
DEFAULT_PERC_SYNTH = "sonic-pi-beep"

def _freq_to_note(freq):
    import math
    if not isinstance(freq, (int, float)) or freq <= 0:
        return 69.0
    return 69.0 + 12.0 * math.log2(freq / 440.0)


def _uid():
    return uuid4().hex


def freq_to_amp(freq, base_amp=0.5):
    scaled = freq_amp_scale(freq, ampdb(0.2))
    return min(1.0, max(0.1, base_amp * (scaled / 0.2)))


def _get_addressed_collection(obj):
    if hasattr(obj, 'freq'):
        return obj
    if hasattr(obj, 'is_instanced') and obj.is_instanced:
        return obj
    if hasattr(obj, 'is_relative') and not obj.is_relative:
        return obj
    return obj.root("C4")


def _gated_note(uid, synth, start, dur, pfields, step_index=None):
    events = []
    new_ev = {
        "type": "new",
        "id": uid,
        "synthName": synth,
        "start": start,
        "pfields": pfields,
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


def _perc_note(uid, synth, start, dur, pfields, step_index=None):
    pf = dict(pfields)
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
    return [new_ev]


def pitch_to_sc_events(pitch, duration=None):
    dur = duration if duration is not None else 1.0
    uid = _uid()
    return _gated_note(uid, DEFAULT_SYNTH, 0.0, dur, {
        "note": pitch.midi,
        "amp": freq_to_amp(pitch.freq),
    }, step_index=0)


def pitch_collection_to_sc_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u'):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        if arp:
            dur = duration if duration is not None else DEFAULT_NOTE_DURATION
            return _build_seq_sc_events(pitches, 0, dur, DEFAULT_SYNTH, 0.5)
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SYNTH)
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, dur, DEFAULT_SYNTH, 0.5)


def scale_to_sc_events(obj, duration=None, equaves=1):
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    addressed = _get_addressed_collection(obj)

    if equaves == 0:
        equaves = 1

    scale_len = len(addressed)
    abs_equaves = abs(equaves)
    going_up = equaves > 0

    all_pitches = []
    if going_up:
        for idx in range(abs_equaves * scale_len + 1):
            all_pitches.append(addressed[idx])
        pitches_down = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_down
    else:
        for i in range(abs_equaves * scale_len + 1):
            all_pitches.append(addressed[-i])
        pitches_up = list(reversed(all_pitches[:-1]))
        all_pitches = all_pitches + pitches_up

    return _build_seq_sc_events(all_pitches, 0, dur, DEFAULT_SYNTH, 0.5)


def chord_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u'):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, dur, DEFAULT_SYNTH, 0.5)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SYNTH)


def chord_sequence_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u'):
    events = []
    current_time = 0.0
    step = 0

    if arp:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            for p in pitches:
                uid = _uid()
                events.extend(_gated_note(uid, DEFAULT_SYNTH, current_time, dur * 0.9, {
                    "note": p.midi,
                    "amp": freq_to_amp(p.freq, 0.5),
                }, step_index=step))
                current_time += dur
                step += 1
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            num = len(pitches)
            base_amp = 0.5 / (num * 0.7) if num > 0 else 0.5
            for i, p in enumerate(pitches):
                uid = _uid()
                taper = 1.0 - (i / num) * 0.6 if num > 0 else 1.0
                start_offset = (strum * dur * i) / num if num > 1 else 0
                events.extend(_gated_note(uid, DEFAULT_SYNTH, current_time + start_offset,
                    (dur * 0.95) - start_offset, {
                        "note": p.midi,
                        "amp": min(1.0, max(0.1, base_amp * taper)),
                    }, step_index=step))
            current_time += dur
            step += 1

    return events


def spectrum_to_sc_events(obj, duration=None, arp=False, strum=0, direction='u'):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _build_seq_sc_events(pitches, 0, dur, DEFAULT_SINE_SYNTH, 0.4)
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _build_chord_sc_events(pitches, 0, dur, strum, DEFAULT_SINE_SYNTH, max_amp=0.4)


def temporal_unit_to_sc_events(obj, use_absolute_time=False):
    events = []

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(c.start for c in obj if not c.is_rest) if any(not c.is_rest for c in obj) else 0

    for chronon in obj:
        if not chronon.is_rest:
            uid = _uid()
            start = chronon.start - time_offset
            dur = abs(chronon.duration)
            events.extend(_perc_note(uid, DEFAULT_PERC_SYNTH, start, dur, {
                "note": _freq_to_note(DEFAULT_DRUM_FREQ),
                "amp": 0.85,
            }))

    return events


def rhythm_tree_to_sc_events(obj, beat=None, bpm=None):
    tu = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_sc_events(tu, use_absolute_time=False)


def temporal_unit_to_sc_animation_events(obj, use_absolute_time=False):
    events = []
    leaf_nodes = obj._rt.leaf_nodes

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(c.start for c in obj if not c.is_rest) if any(not c.is_rest for c in obj) else 0

    node_to_step = {nid: idx for idx, nid in enumerate(leaf_nodes)}

    for chronon in obj:
        start = chronon.start - time_offset
        dur = abs(chronon.duration)
        step_idx = node_to_step.get(chronon.node_id, None)

        if chronon.is_rest:
            events.append({
                "type": "new",
                "id": _uid(),
                "synthName": "__rest__",
                "start": start,
                "pfields": {},
                "_stepIndex": step_idx,
            })
        else:
            uid = _uid()
            events.extend(_perc_note(uid, DEFAULT_PERC_SYNTH, start, dur, {
                "note": _freq_to_note(DEFAULT_DRUM_FREQ),
                "amp": 0.85,
            }, step_index=step_idx))

    events.sort(key=lambda ev: ev["start"])
    return events


def rhythm_tree_to_sc_animation_events(obj, beat=None, bpm=None):
    tu = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_sc_animation_events(tu, use_absolute_time=False)


def compositional_unit_to_sc_events(obj):
    events = []

    for event in obj:
        if event.is_rest:
            continue

        instrument = obj.get_active_instrument(event.node_id)
        synth_name = DEFAULT_SYNTH
        env_type = ''

        if isinstance(instrument, SynthDefInstrument):
            synth_name = instrument.synth_name or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''
        elif instrument is not None:
            synth_name = getattr(instrument, 'synth_name', None) or getattr(instrument, 'name', None) or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''

        pfields = {k: v for k, v in event.parameters.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}

        if 'freq' in pfields and 'note' not in pfields:
            pfields['note'] = _freq_to_note(pfields['freq']) if isinstance(pfields['freq'], (int, float)) else pfields['freq']
        if 'amp' not in pfields:
            freq = pfields.get('freq', 440.0)
            if isinstance(freq, (int, float)):
                pfields['amp'] = freq_to_amp(freq)
            else:
                pfields['amp'] = 0.5

        uid = _uid()
        is_gated = env_type.lower() in ('sustained', 'sus', 'asr', 'adsr', '')

        if is_gated:
            events.extend(_gated_note(uid, synth_name, event.start, abs(event.duration), pfields))
        else:
            events.extend(_perc_note(uid, synth_name, event.start, abs(event.duration), pfields))

    events.sort(key=lambda ev: ev["start"])
    return events


def compositional_unit_to_sc_animation_events(obj):
    events = []
    leaf_nodes = obj._rt.leaf_nodes
    node_to_step = {nid: idx for idx, nid in enumerate(leaf_nodes)}

    time_offset = min(ev.start for ev in obj if not ev.is_rest) if any(not ev.is_rest for ev in obj) else 0

    for event in obj:
        step_idx = node_to_step.get(event.node_id, None)
        start = event.start - time_offset

        if event.is_rest:
            events.append({
                "type": "new",
                "id": _uid(),
                "synthName": "__rest__",
                "start": start,
                "pfields": {},
                "_stepIndex": step_idx,
            })
            continue

        instrument = obj.get_active_instrument(event.node_id)
        synth_name = DEFAULT_SYNTH
        env_type = ''

        if isinstance(instrument, SynthDefInstrument):
            synth_name = instrument.synth_name or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''
        elif instrument is not None:
            synth_name = getattr(instrument, 'synth_name', None) or getattr(instrument, 'name', None) or DEFAULT_SYNTH
            env_type = getattr(instrument, 'env_type', '') or ''

        pfields = {k: v for k, v in event.parameters.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}

        if 'freq' in pfields and 'note' not in pfields:
            pfields['note'] = _freq_to_note(pfields['freq']) if isinstance(pfields['freq'], (int, float)) else pfields['freq']
        if 'amp' not in pfields:
            freq = pfields.get('freq', 440.0)
            if isinstance(freq, (int, float)):
                pfields['amp'] = freq_to_amp(freq)
            else:
                pfields['amp'] = 0.5

        uid = _uid()
        is_gated = env_type.lower() in ('sustained', 'sus', 'asr', 'adsr', '')
        dur = abs(event.duration)

        if is_gated:
            evts = _gated_note(uid, synth_name, start, dur, pfields, step_index=step_idx)
        else:
            evts = _perc_note(uid, synth_name, start, dur, pfields, step_index=step_idx)
        events.extend(evts)

    events.sort(key=lambda ev: ev["start"])
    return events


def _build_seq_sc_events(pitches, start, dur, synth, base_amp):
    events = []
    for i, pitch in enumerate(pitches):
        uid = _uid()
        events.extend(_gated_note(uid, synth, start + i * dur, dur * 0.9, {
            "note": pitch.midi,
            "amp": freq_to_amp(pitch.freq, base_amp),
        }, step_index=i))
    return events


def _build_chord_sc_events(pitches, start, dur, strum, synth, max_amp=0.5, dur_factor=1.0):
    events = []
    num = len(pitches)
    base_amp = max_amp / (num * 0.7) if num > 0 else max_amp
    strum = max(0, min(1, strum))

    for i, pitch in enumerate(pitches):
        uid = _uid()
        taper = 1.0 - (i / num) * 0.6 if num > 0 else 1.0
        amp = min(1.0, max(0.1, base_amp * taper))
        start_offset = (strum * dur * i) / num if num > 1 else 0
        events.extend(_gated_note(uid, synth, start + start_offset,
            (dur * dur_factor) - start_offset, {
                "note": pitch.midi,
                "amp": amp,
            }, step_index=i))
    return events


def _merge_sub_sc(target_events, sub_events, time_offset):
    for ev in sub_events:
        ev["start"] -= time_offset
    target_events.extend(sub_events)


def temporal_sequence_to_sc_events(obj):
    events = []
    seq_offset = obj.offset

    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(unit), seq_offset)
        elif isinstance(unit, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(unit, use_absolute_time=True), seq_offset)
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(unit), seq_offset)
        elif isinstance(unit, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(unit), seq_offset)

    events.sort(key=lambda ev: ev["start"])
    return events


def temporal_block_to_sc_events(obj):
    events = []
    block_offset = obj.offset

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_sc(events, compositional_unit_to_sc_events(row), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_sc(events, temporal_unit_to_sc_events(row, use_absolute_time=True), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_sc(events, temporal_sequence_to_sc_events(row), block_offset + row.offset)
        elif isinstance(row, TemporalBlock):
            _merge_sub_sc(events, temporal_block_to_sc_events(row), block_offset + row.offset)

    events.sort(key=lambda ev: ev["start"])
    return events


def convert_to_sc_events(obj, **kwargs):
    duration = kwargs.get('dur', kwargs.get('duration', None))
    arp = kwargs.get('arp', False)
    mode = kwargs.get('mode', None)
    strum = kwargs.get('strum', 0)
    direction = kwargs.get('dir', 'u')
    equaves = kwargs.get('equaves', 1)
    beat = kwargs.get('beat', None)
    bpm = kwargs.get('bpm', None)

    if isinstance(obj, Pitch):
        return pitch_to_sc_events(obj, duration=duration)

    if isinstance(obj, Spectrum):
        return spectrum_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_sc_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction)

    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_sc_events(obj, beat=beat, bpm=bpm)

    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_sc_events(obj)

    if isinstance(obj, TemporalBlock):
        return temporal_block_to_sc_events(obj)

    if isinstance(obj, CompositionalUnit):
        return compositional_unit_to_sc_events(obj)

    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_sc_events(obj)

    if isinstance(obj, ChordSequence):
        return chord_sequence_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)

    if isinstance(obj, Scale):
        return scale_to_sc_events(obj, duration=duration, equaves=equaves)

    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_sc_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_sc_events(obj, duration=duration, mode="chord", arp=arp, strum=strum, direction=direction)
        return pitch_collection_to_sc_events(obj, duration=duration, mode="sequential")

    raise TypeError(f"Unsupported object type: {type(obj)}")


def tonejs_events_to_sc(tone_events):
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
        amp = pf.get("vel", pf.get("amp", 0.5))
        note = _freq_to_note(freq)

        synth = DEFAULT_PERC_SYNTH if instrument == "membrane" else DEFAULT_SYNTH

        if instrument == "membrane":
            new_ev = {
                "type": "new",
                "id": uid,
                "synthName": synth,
                "start": start,
                "pfields": {"note": note, "amp": amp, "dur": dur},
            }
            if step is not None:
                new_ev["_stepIndex"] = step
            sc_events.append(new_ev)
        else:
            new_ev = {
                "type": "new",
                "id": uid,
                "synthName": synth,
                "start": start,
                "pfields": {"note": note, "amp": amp},
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
