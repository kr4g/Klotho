import copy

from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import ToneInstrument
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
from klotho.utils.playback._converter_base import (
    DEFAULT_NOTE_DURATION, DEFAULT_CHORD_DURATION,
    DEFAULT_SPECTRUM_DURATION, DEFAULT_DRUM_FREQ,
    KNOWN_KWARGS,
    _get_addressed_collection, _merge_pfields,
    scale_pitch_sequence, extract_convert_kwargs, lower_event_ir_to_voice_events,
)


def _payload(events, instruments=None):
    return {"events": events, "instruments": instruments or {}}


def _deep_merge(base, override):
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _normalize_event_pfields(pfields):
    if 'vel' not in pfields and 'amp' in pfields:
        pfields['vel'] = pfields['amp']
    if 'amp' not in pfields and 'vel' in pfields:
        pfields['amp'] = pfields['vel']
    if 'freq' not in pfields:
        pfields['freq'] = 440.0
    return pfields


def _build_seq_events(pitches, start, instrument, amp=None, per_voice_dur=None,
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
        pf = {
            "freq": pitch.freq,
            "vel": single_voice_amplitude(pitch.freq, amp),
        }
        pf = _merge_pfields(pf, extra_pfields)
        events.append({
            "start": cursor,
            "duration": voice_dur,
            "instrument": instrument,
            "pfields": pf,
        })
        cursor += voice_dur + max(0.0, pause)
    return events


def _build_chord_events(pitches, start, dur, strum, instrument, amp=None,
                        dur_factor=1.0, extra_pfields=None):
    events = []
    num_notes = len(pitches)
    if num_notes == 0:
        return events

    freqs = [p.freq for p in pitches]
    voice_amps = compute_voice_amplitudes(freqs, amp)
    strum = max(0, min(1, strum))

    for i, pitch in enumerate(pitches):
        start_offset = (strum * dur * i) / num_notes if num_notes > 1 else 0
        pf = {
            "freq": pitch.freq,
            "vel": voice_amps[i],
        }
        pf = _merge_pfields(pf, extra_pfields)
        events.append({
            "start": start + start_offset,
            "duration": (dur * dur_factor) - start_offset,
            "instrument": instrument,
            "pfields": pf,
        })
    return events


def compositional_unit_to_events(obj, extra_pfields=None, animation=False):
    events = []
    instruments = {}
    inst_id_map = {}

    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)}
                    if animation else None)

    time_offset = 0
    if animation:
        time_offset = min(ev.start for ev in obj if not ev.is_rest) if any(not ev.is_rest for ev in obj) else 0

    for event in obj:
        step_idx = node_to_step.get(event.node_id, None) if animation else None
        start_time = event.start - time_offset if animation else event.start

        if event.is_rest:
            if animation:
                events.append({
                    "start": start_time,
                    "duration": abs(event.duration),
                    "instrument": "__rest__",
                    "pfields": {},
                    "_stepIndex": step_idx,
                })
            continue

        instrument = obj.get_instrument(event.node_id)
        if not isinstance(instrument, ToneInstrument):
            if animation:
                events.append({
                    "start": start_time,
                    "duration": abs(event.duration),
                    "instrument": "__rest__",
                    "pfields": {},
                    "_stepIndex": step_idx,
                })
            continue

        inst_identity = id(instrument)
        if inst_identity not in inst_id_map:
            key = instrument.name
            if key in instruments:
                existing = instruments[key]
                if existing['tonejs_class'] != instrument.tonejs_class or existing['preset'] != instrument.pfields:
                    raise ValueError(
                        f"Instrument name '{key}' is used by two different instruments. "
                        f"Use distinct names."
                    )
            else:
                instruments[key] = {
                    'tonejs_class': instrument.tonejs_class,
                    'preset': instrument.pfields
                }
            inst_id_map[inst_identity] = key

        routing_key = inst_id_map[inst_identity]
        expanded_voices = lower_event_ir_to_voice_events(event, step_index=step_idx)
        for expanded_voice in expanded_voices:
            pfields = {k: v for k, v in expanded_voice["pfields"].items()
                       if k not in ('defName', 'synthName', 'group')}
            pfields = _normalize_event_pfields(pfields)
            default_pfields = instruments[routing_key].get('preset', {})
            effective_pfields = _deep_merge(default_pfields, pfields)
            effective_pfields = _merge_pfields(effective_pfields, extra_pfields)

            voice_start = expanded_voice["start"] - time_offset if animation else expanded_voice["start"]
            ev_data = {
                "start": voice_start,
                "duration": expanded_voice["duration"],
                "instrument": routing_key,
                "pfields": effective_pfields,
                "_polyGroupId": expanded_voice["poly_group_id"],
                "_logicalStepId": expanded_voice["logical_step_id"],
                "_polyVoiceIndex": expanded_voice["poly_voice_index"],
                "_polyVoiceCount": expanded_voice["poly_voice_count"],
                "_polyLeader": expanded_voice["poly_is_leader"],
                "_animate": expanded_voice["animate"],
            }
            if animation:
                ev_data["_stepIndex"] = step_idx
            events.append(ev_data)

    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


def compositional_unit_to_animation_events(obj, extra_pfields=None):
    return compositional_unit_to_events(obj, extra_pfields=extra_pfields, animation=True)


def pitch_to_events(pitch, duration=None, amp=None, extra_pfields=None):
    dur = duration if duration is not None else 1.0
    pf = {
        "freq": pitch.freq,
        "vel": single_voice_amplitude(pitch.freq, amp),
    }
    pf = _merge_pfields(pf, extra_pfields)
    return _payload([{
        "start": 0.0,
        "duration": dur,
        "instrument": "synth",
        "pfields": pf,
    }])


def pitch_collection_to_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u',
                               amp=None, pause=0.0, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))

        if arp:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                              total_dur=dur, pause=pause, extra_pfields=extra_pfields))
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _payload(_build_chord_events(pitches, 0, dur, strum, "synth",
                                                amp=amp, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                          per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields))


def scale_to_events(obj, duration=None, equaves=1, amp=None, pause=0.0, extra_pfields=None):
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    all_pitches = scale_pitch_sequence(obj, equaves)
    return _payload(_build_seq_events(all_pitches, 0, "synth", amp=amp,
                                      per_voice_dur=dur, pause=pause, extra_pfields=extra_pfields))


def chord_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                    amp=None, pause=0.0, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                          total_dur=dur, pause=pause, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _payload(_build_chord_events(pitches, 0, dur, strum, "synth",
                                            amp=amp, extra_pfields=extra_pfields))


def chord_sequence_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                             amp=None, pause=0.25, extra_pfields=None):
    events = []
    current_time = 0.0

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION

        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))

            n = len(pitches)
            voice_dur = dur / max(1, n)
            for i, pitch in enumerate(pitches):
                pf = {
                    "freq": pitch.freq,
                    "vel": single_voice_amplitude(pitch.freq, amp),
                }
                pf = _merge_pfields(pf, extra_pfields)
                events.append({
                    "start": current_time + i * voice_dur,
                    "duration": voice_dur,
                    "instrument": "synth",
                    "pfields": pf,
                })
            current_time += dur + max(0.0, pause)
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION

        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))

            events.extend(_build_chord_events(pitches, current_time, dur, strum, "synth",
                                              amp=amp, dur_factor=1.0, extra_pfields=extra_pfields))
            current_time += dur + max(0.0, pause)

    return _payload(events)


def spectrum_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                       amp=None, pause=0.0, extra_pfields=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _payload(_build_seq_events(pitches, 0, "sine", amp=target,
                                          total_dur=dur, pause=pause, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _payload(_build_chord_events(pitches, 0, dur, strum, "sine",
                                            amp=target, extra_pfields=extra_pfields))


def temporal_unit_to_events(obj, use_absolute_time=False, amp=None, extra_pfields=None,
                            animation=False):
    events = []
    target = amp if amp is not None else 0.85

    leaf_nodes = obj._rt.leaf_nodes if animation else None
    node_to_step = ({nid: idx for idx, nid in enumerate(leaf_nodes)}
                    if animation else None)

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(chronon.start for chronon in obj if not chronon.is_rest) if any(not chronon.is_rest for chronon in obj) else 0

    for chronon in obj:
        start_time = chronon.start - time_offset
        duration = abs(chronon.duration)
        step_idx = node_to_step.get(chronon.node_id, None) if animation else None

        if chronon.is_rest:
            if animation:
                events.append({
                    "start": start_time,
                    "duration": duration,
                    "instrument": "__rest__",
                    "pfields": {},
                    "_stepIndex": step_idx,
                })
            continue

        pf = {
            "freq": DEFAULT_DRUM_FREQ,
            "vel": target,
        }
        pf = _merge_pfields(pf, extra_pfields)
        ev_data = {
            "start": start_time,
            "duration": duration,
            "instrument": "membrane",
            "pfields": pf,
        }
        if animation:
            ev_data["_stepIndex"] = step_idx
        events.append(ev_data)

    if animation:
        events.sort(key=lambda ev: ev["start"])
    return _payload(events)


def temporal_unit_to_animation_events(obj, use_absolute_time=False, amp=None, extra_pfields=None):
    return temporal_unit_to_events(obj, use_absolute_time=use_absolute_time, amp=amp,
                                  extra_pfields=extra_pfields, animation=True)


def rhythm_tree_to_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    temporal_unit = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_events(temporal_unit, use_absolute_time=False,
                                  amp=amp, extra_pfields=extra_pfields)


def rhythm_tree_to_animation_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    temporal_unit = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_animation_events(temporal_unit, use_absolute_time=False,
                                            amp=amp, extra_pfields=extra_pfields)


def _merge_sub_payload(target_events, target_instruments, sub_payload, time_offset):
    for ev in sub_payload["events"]:
        ev["start"] -= time_offset
    target_events.extend(sub_payload["events"])
    for key, val in sub_payload["instruments"].items():
        if key in target_instruments:
            existing = target_instruments[key]
            if existing['tonejs_class'] != val['tonejs_class'] or existing['preset'] != val['preset']:
                raise ValueError(
                    f"Instrument name '{key}' is used by two different instruments. "
                    f"Use distinct names."
                )
        else:
            target_instruments[key] = val


def temporal_sequence_to_events(obj, extra_pfields=None):
    events = []
    instruments = {}
    seq_offset = obj.offset

    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            _merge_sub_payload(events, instruments, compositional_unit_to_events(unit, extra_pfields=None), seq_offset)
        elif isinstance(unit, TemporalUnit):
            _merge_sub_payload(events, instruments, temporal_unit_to_events(unit, use_absolute_time=True, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalUnitSequence):
            _merge_sub_payload(events, instruments, temporal_sequence_to_events(unit, extra_pfields=extra_pfields), seq_offset)
        elif isinstance(unit, TemporalBlock):
            _merge_sub_payload(events, instruments, temporal_block_to_events(unit, extra_pfields=extra_pfields), seq_offset)

    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


def temporal_block_to_events(obj, extra_pfields=None):
    events = []
    instruments = {}
    block_offset = obj.offset

    for row in obj:
        if isinstance(row, CompositionalUnit):
            _merge_sub_payload(events, instruments, compositional_unit_to_events(row, extra_pfields=None), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_payload(events, instruments, temporal_unit_to_events(row, use_absolute_time=True, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_payload(events, instruments, temporal_sequence_to_events(row, extra_pfields=extra_pfields), block_offset + row.offset)
        elif isinstance(row, TemporalBlock):
            _merge_sub_payload(events, instruments, temporal_block_to_events(row, extra_pfields=extra_pfields), block_offset + row.offset)

    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


def convert_to_events(obj, **kwargs):
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
        return pitch_to_events(obj, duration=duration, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, Spectrum):
        return spectrum_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_events(obj, beat=beat, bpm=bpm, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalBlock):
        return temporal_block_to_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, CompositionalUnit):
        return compositional_unit_to_events(obj, extra_pfields=None)

    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_events(obj, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, ChordSequence):
        return chord_sequence_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                        amp=amp, pause=(0.25 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, Scale):
        return scale_to_events(obj, duration=duration, equaves=equaves, amp=amp,
                               pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                               amp=amp, pause=(0.0 if pause is None else pause), extra_pfields=extra_pfields)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                              direction=direction, amp=amp,
                                              pause=(0.0 if pause is None else pause),
                                              extra_pfields=extra_pfields)
        return pitch_collection_to_events(obj, duration=duration, mode="sequential",
                                          amp=amp, pause=(0.0 if pause is None else pause),
                                          extra_pfields=extra_pfields)

    raise TypeError(f"Unsupported object type: {type(obj)}")
