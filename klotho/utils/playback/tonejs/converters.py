from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import JsInstrument
from klotho.utils.playback._amplitude import single_voice_amplitude, compute_voice_amplitudes
import copy

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 110.0

KNOWN_KWARGS = frozenset({
    'dur', 'duration', 'arp', 'strum', 'dir', 'direction',
    'equaves', 'beat', 'bpm', 'mode', 'amp', 'ring_time',
})


def _payload(events, instruments=None):
    return {"events": events, "instruments": instruments or {}}


def freq_to_velocity(freq, base_vel=0.6):
    return single_voice_amplitude(freq, base_vel)


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


def _get_addressed_collection(obj):
    if hasattr(obj, 'freq'):
        return obj
    if hasattr(obj, 'is_instanced') and obj.is_instanced:
        return obj
    if hasattr(obj, 'is_relative') and not obj.is_relative:
        return obj
    return obj.root("C4")


def _merge_pfields(base, extra):
    if not extra:
        return base
    merged = dict(extra)
    merged.update(base)
    return merged


def _build_seq_events(pitches, start, instrument, amp=None, per_voice_dur=None,
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
        pf = {
            "freq": pitch.freq,
            "vel": single_voice_amplitude(pitch.freq, amp),
        }
        pf = _merge_pfields(pf, extra_pfields)
        events.append({
            "start": start + i * voice_dur,
            "duration": voice_dur * 0.9,
            "instrument": instrument,
            "pfields": pf,
        })
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


def compositional_unit_to_events(obj, extra_pfields=None):
    events = []
    instruments = {}
    inst_id_map = {}

    for event in obj:
        if event.is_rest:
            continue
        instrument = obj.get_active_instrument(event.node_id)
        if not isinstance(instrument, JsInstrument):
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
        pfields = {k: v for k, v in event.parameters.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}
        pfields = _normalize_event_pfields(pfields)
        default_pfields = instruments[routing_key].get('preset', {})
        effective_pfields = _deep_merge(default_pfields, pfields)
        effective_pfields = _merge_pfields(effective_pfields, extra_pfields)
        events.append({
            "start": event.start,
            "duration": abs(event.duration),
            "instrument": routing_key,
            "pfields": effective_pfields
        })
    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


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
                               amp=None, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))

        if arp:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                              total_dur=dur, extra_pfields=extra_pfields))
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            return _payload(_build_chord_events(pitches, 0, dur, strum, "synth",
                                                amp=amp, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                          per_voice_dur=dur, extra_pfields=extra_pfields))


def scale_to_events(obj, duration=None, equaves=1, amp=None, extra_pfields=None):
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

    return _payload(_build_seq_events(all_pitches, 0, "synth", amp=amp,
                                      per_voice_dur=dur, extra_pfields=extra_pfields))


def chord_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                    amp=None, extra_pfields=None):
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    if arp:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _payload(_build_seq_events(pitches, 0, "synth", amp=amp,
                                          total_dur=dur, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _payload(_build_chord_events(pitches, 0, dur, strum, "synth",
                                            amp=amp, extra_pfields=extra_pfields))


def chord_sequence_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                             amp=None, extra_pfields=None):
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
                    "duration": voice_dur * 0.9,
                    "instrument": "synth",
                    "pfields": pf,
                })
            current_time += dur
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION

        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))

            events.extend(_build_chord_events(pitches, current_time, dur, strum, "synth",
                                              amp=amp, dur_factor=0.95, extra_pfields=extra_pfields))
            current_time += dur

    return _payload(events)


def spectrum_to_events(obj, duration=None, arp=False, strum=0, direction='u',
                       amp=None, extra_pfields=None):
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]

    if direction.lower() == 'd':
        pitches = list(reversed(pitches))

    target = amp if amp is not None else 0.4
    if arp:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _payload(_build_seq_events(pitches, 0, "sine", amp=target,
                                          total_dur=dur, extra_pfields=extra_pfields))
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        return _payload(_build_chord_events(pitches, 0, dur, strum, "sine",
                                            amp=target, extra_pfields=extra_pfields))


def temporal_unit_to_events(obj, use_absolute_time=False, amp=None, extra_pfields=None):
    events = []
    target = amp if amp is not None else 0.85

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(chronon.start for chronon in obj if not chronon.is_rest) if any(not chronon.is_rest for chronon in obj) else 0

    for chronon in obj:
        if not chronon.is_rest:
            start_time = chronon.start - time_offset
            duration = abs(chronon.duration)

            pf = {
                "freq": DEFAULT_DRUM_FREQ,
                "vel": target,
            }
            pf = _merge_pfields(pf, extra_pfields)
            events.append({
                "start": start_time,
                "duration": duration,
                "instrument": "membrane",
                "pfields": pf,
            })

    return _payload(events)


def rhythm_tree_to_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    temporal_unit = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_events(temporal_unit, use_absolute_time=False,
                                  amp=amp, extra_pfields=extra_pfields)


def temporal_unit_to_animation_events(obj, use_absolute_time=False, amp=None, extra_pfields=None):
    events = []
    leaf_nodes = obj._rt.leaf_nodes
    target = amp if amp is not None else 0.85

    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(c.start for c in obj if not c.is_rest) if any(not c.is_rest for c in obj) else 0

    node_to_step = {nid: idx for idx, nid in enumerate(leaf_nodes)}

    for chronon in obj:
        start_time = chronon.start - time_offset
        duration = abs(chronon.duration)
        step_idx = node_to_step.get(chronon.node_id, None)

        if chronon.is_rest:
            events.append({
                "start": start_time,
                "duration": duration,
                "instrument": "__rest__",
                "pfields": {},
                "_stepIndex": step_idx,
            })
        else:
            pf = {
                "freq": DEFAULT_DRUM_FREQ,
                "vel": target,
            }
            pf = _merge_pfields(pf, extra_pfields)
            events.append({
                "start": start_time,
                "duration": duration,
                "instrument": "membrane",
                "pfields": pf,
                "_stepIndex": step_idx,
            })

    events.sort(key=lambda ev: ev["start"])
    return _payload(events)


def rhythm_tree_to_animation_events(obj, beat=None, bpm=None, amp=None, extra_pfields=None):
    temporal_unit = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_animation_events(temporal_unit, use_absolute_time=False,
                                            amp=amp, extra_pfields=extra_pfields)


def compositional_unit_to_animation_events(obj, extra_pfields=None):
    events = []
    instruments = {}
    inst_id_map = {}
    leaf_nodes = obj._rt.leaf_nodes
    node_to_step = {nid: idx for idx, nid in enumerate(leaf_nodes)}

    time_offset = min(ev.start for ev in obj if not ev.is_rest) if any(not ev.is_rest for ev in obj) else 0

    for event in obj:
        step_idx = node_to_step.get(event.node_id, None)
        start_time = event.start - time_offset

        if event.is_rest:
            events.append({
                "start": start_time,
                "duration": abs(event.duration),
                "instrument": "__rest__",
                "pfields": {},
                "_stepIndex": step_idx,
            })
            continue

        instrument = obj.get_active_instrument(event.node_id)
        if not isinstance(instrument, JsInstrument):
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
        pfields = {k: v for k, v in event.parameters.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}
        pfields = _normalize_event_pfields(pfields)
        default_pfields = instruments[routing_key].get('preset', {})
        effective_pfields = _deep_merge(default_pfields, pfields)
        effective_pfields = _merge_pfields(effective_pfields, extra_pfields)
        events.append({
            "start": start_time,
            "duration": abs(event.duration),
            "instrument": routing_key,
            "pfields": effective_pfields,
            "_stepIndex": step_idx,
        })

    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


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
            _merge_sub_payload(events, instruments, compositional_unit_to_events(unit, extra_pfields=extra_pfields), seq_offset)
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
            _merge_sub_payload(events, instruments, compositional_unit_to_events(row, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnit):
            _merge_sub_payload(events, instruments, temporal_unit_to_events(row, use_absolute_time=True, extra_pfields=extra_pfields), block_offset)
        elif isinstance(row, TemporalUnitSequence):
            _merge_sub_payload(events, instruments, temporal_sequence_to_events(row, extra_pfields=extra_pfields), block_offset + row.offset)
        elif isinstance(row, TemporalBlock):
            _merge_sub_payload(events, instruments, temporal_block_to_events(row, extra_pfields=extra_pfields), block_offset + row.offset)

    events.sort(key=lambda ev: ev["start"])
    return _payload(events, instruments)


def convert_to_events(obj, **kwargs):
    duration = kwargs.get('dur', kwargs.get('duration', None))
    arp = kwargs.get('arp', False)
    mode = kwargs.get('mode', None)
    strum = kwargs.get('strum', 0)
    direction = kwargs.get('dir', 'u')
    equaves = kwargs.get('equaves', 1)
    beat = kwargs.get('beat', None)
    bpm = kwargs.get('bpm', None)
    amp = kwargs.get('amp', None)

    extra_pfields = {k: v for k, v in kwargs.items() if k not in KNOWN_KWARGS}
    if not extra_pfields:
        extra_pfields = None

    if isinstance(obj, Pitch):
        return pitch_to_events(obj, duration=duration, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, Spectrum):
        return spectrum_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction,
                                  amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_events(obj, beat=beat, bpm=bpm, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalBlock):
        return temporal_block_to_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, CompositionalUnit):
        return compositional_unit_to_events(obj, extra_pfields=extra_pfields)

    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_events(obj, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, ChordSequence):
        return chord_sequence_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                                        amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, Scale):
        return scale_to_events(obj, duration=duration, equaves=equaves, amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction,
                               amp=amp, extra_pfields=extra_pfields)

    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_events(obj, duration=duration, mode="chord", arp=arp, strum=strum,
                                              direction=direction, amp=amp, extra_pfields=extra_pfields)
        return pitch_collection_to_events(obj, duration=duration, mode="sequential",
                                          amp=amp, extra_pfields=extra_pfields)

    raise TypeError(f"Unsupported object type: {type(obj)}")
