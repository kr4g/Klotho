from klotho.tonos import Pitch
from klotho.tonos.pitch.pitch_collections import PitchCollectionBase
from klotho.tonos.chords.chord import Chord, Voicing, Sonority, ChordSequence
from klotho.tonos.scales.scale import Scale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.dynatos.dynamics import freq_amp_scale, ampdb
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import JsInstrument
import copy

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 110.0


def freq_to_velocity(freq, base_vel=0.6):
    scaled_amp = freq_amp_scale(freq, ampdb(0.2))
    return min(1.0, max(0.1, base_vel * (scaled_amp / 0.2)))


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


def compositional_unit_to_events(obj):
    events = []
    instruments = {}
    inst_id_map = {}
    class_counters = {}

    for event in obj:
        if event.is_rest:
            continue
        instrument = event._pt.get_active_instrument(event.node_id)
        if not isinstance(instrument, JsInstrument):
            continue

        inst_identity = id(instrument)
        if inst_identity not in inst_id_map:
            tc = instrument.tonejs_class
            idx = class_counters.get(tc, 0)
            class_counters[tc] = idx + 1
            routing_key = f"{tc}_{idx}"
            inst_id_map[inst_identity] = routing_key
            instruments[routing_key] = {
                'tonejs_class': tc,
                'preset': instrument.pfields
            }

        routing_key = inst_id_map[inst_identity]
        pfields = {k: v for k, v in event.parameters.items()
                   if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}
        pfields = _normalize_event_pfields(pfields)
        default_pfields = instruments[routing_key].get('preset', {})
        effective_pfields = _deep_merge(default_pfields, pfields)
        events.append({
            "start": event.start,
            "duration": abs(event.duration),
            "instrument": routing_key,
            "pfields": effective_pfields
        })
    events.sort(key=lambda ev: ev["start"])
    return {"events": events, "instruments": instruments}


def _get_addressed_collection(obj):
    if hasattr(obj, 'freq'):
        return obj
    if hasattr(obj, 'is_instanced') and obj.is_instanced:
        return obj
    if hasattr(obj, 'is_relative') and not obj.is_relative:
        return obj
    return obj.root("C4")


def pitch_to_events(pitch, duration=None):
    dur = duration if duration is not None else 1.0
    return [{
        "start": 0.0,
        "duration": dur,
        "instrument": "synth",
        "pfields": {
            "freq": pitch.freq,
            "vel": freq_to_velocity(pitch.freq),
        }
    }]


def pitch_collection_to_events(obj, duration=None, mode="seq", arp=False, strum=0, direction='u'):
    events = []
    addressed = _get_addressed_collection(obj)
    pitches = [addressed[i] for i in range(len(addressed))]
    
    if mode == "chord":
        pitches = sorted(pitches, key=lambda p: p.freq)
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        
        if arp:
            note_dur = duration if duration is not None else DEFAULT_NOTE_DURATION
            for i, pitch in enumerate(pitches):
                events.append({
                    "start": i * note_dur,
                    "duration": note_dur * 0.9,
                    "instrument": "synth",
                    "pfields": {
                        "freq": pitch.freq,
                        "vel": freq_to_velocity(pitch.freq, 0.5),
                    }
                })
        else:
            dur = duration if duration is not None else DEFAULT_CHORD_DURATION
            num_notes = len(pitches)
            max_total_amp = 0.5
            base_amp = max_total_amp / (num_notes * 0.7) if num_notes > 0 else 0.5
            
            strum = max(0, min(1, strum))
            
            for i, pitch in enumerate(pitches):
                taper_factor = 1.0 - (i / num_notes) * 0.6 if num_notes > 0 else 1.0
                vel = base_amp * taper_factor
                
                start_offset = (strum * dur * i) / num_notes if num_notes > 1 else 0
                
                events.append({
                    "start": start_offset,
                    "duration": dur - start_offset,
                    "instrument": "synth",
                    "pfields": {
                        "freq": pitch.freq,
                        "vel": min(1.0, max(0.1, vel)),
                    }
                })
    else:
        dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        for i, pitch in enumerate(pitches):
            events.append({
                "start": i * dur,
                "duration": dur * 0.9,
                "instrument": "synth",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": freq_to_velocity(pitch.freq, 0.5),
                }
            })
    
    return events


def scale_to_events(obj, duration=None, equaves=1):
    events = []
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
    
    for i, pitch in enumerate(all_pitches):
        events.append({
            "start": i * dur,
            "duration": dur * 0.9,
            "instrument": "synth",
            "pfields": {
                "freq": pitch.freq,
                "vel": freq_to_velocity(pitch.freq, 0.5),
            }
        })
    
    return events


def chord_to_events(obj, duration=None, arp=False, strum=0, direction='u'):
    addressed = _get_addressed_collection(obj)
    
    if arp:
        note_dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        events = []
        pitches = [addressed[i] for i in range(len(addressed))]
        if direction.lower() == 'd':
            pitches = list(reversed(pitches))
        
        for i, pitch in enumerate(pitches):
            events.append({
                "start": i * note_dur,
                "duration": note_dur * 0.9,
                "instrument": "synth",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": freq_to_velocity(pitch.freq, 0.5),
                }
            })
        return events
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        return _chord_to_events_internal(addressed, dur, strum, direction)


def _chord_to_events_internal(addressed, dur, strum=0, direction='u'):
    events = []
    pitches = [addressed[i] for i in range(len(addressed))]
    
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))
    
    num_notes = len(pitches)
    max_total_amp = 0.5
    base_amp = max_total_amp / (num_notes * 0.7) if num_notes > 0 else 0.5
    
    strum = max(0, min(1, strum))
    
    for i, pitch in enumerate(pitches):
        taper_factor = 1.0 - (i / num_notes) * 0.6 if num_notes > 0 else 1.0
        vel = base_amp * taper_factor
        
        start_offset = (strum * dur * i) / num_notes if num_notes > 1 else 0
        
        events.append({
            "start": start_offset,
            "duration": dur - start_offset,
            "instrument": "synth",
            "pfields": {
                "freq": pitch.freq,
                "vel": min(1.0, max(0.1, vel)),
            }
        })
    
    return events


def chord_sequence_to_events(obj, duration=None, arp=False, strum=0, direction='u'):
    events = []
    current_time = 0.0
    
    if arp:
        note_dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            
            for i, pitch in enumerate(pitches):
                events.append({
                    "start": current_time + i * note_dur,
                    "duration": note_dur * 0.9,
                    "instrument": "synth",
                    "pfields": {
                        "freq": pitch.freq,
                        "vel": freq_to_velocity(pitch.freq, 0.5),
                    }
                })
            
            current_time += len(pitches) * note_dur
    else:
        dur = duration if duration is not None else DEFAULT_CHORD_DURATION
        strum = max(0, min(1, strum))
        
        for chord in obj:
            addressed = _get_addressed_collection(chord)
            pitches = [addressed[i] for i in range(len(addressed))]
            
            if direction.lower() == 'd':
                pitches = list(reversed(pitches))
            
            num_notes = len(pitches)
            max_total_amp = 0.5
            base_amp = max_total_amp / (num_notes * 0.7) if num_notes > 0 else 0.5
            
            for i, pitch in enumerate(pitches):
                taper_factor = 1.0 - (i / num_notes) * 0.6 if num_notes > 0 else 1.0
                vel = base_amp * taper_factor
                
                start_offset = (strum * dur * i) / num_notes if num_notes > 1 else 0
                
                events.append({
                    "start": current_time + start_offset,
                    "duration": (dur * 0.95) - start_offset,
                    "instrument": "synth",
                    "pfields": {
                        "freq": pitch.freq,
                        "vel": min(1.0, max(0.1, vel)),
                    }
                })
            
            current_time += dur
    
    return events


def spectrum_to_events(obj, duration=None, arp=False, strum=0, direction='u'):
    events = []
    
    pitches = [row['pitch'] for _, row in obj.data.iterrows()]
    
    if direction.lower() == 'd':
        pitches = list(reversed(pitches))
    
    num_partials = len(pitches)
    
    if arp:
        note_dur = duration if duration is not None else DEFAULT_NOTE_DURATION
        for i, pitch in enumerate(pitches):
            events.append({
                "start": i * note_dur,
                "duration": note_dur * 0.9,
                "instrument": "sine",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": freq_to_velocity(pitch.freq, 0.4),
                }
            })
    else:
        dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
        max_total_amp = 0.4
        base_amp = max_total_amp / (num_partials * 0.7) if num_partials > 0 else 0.4
        
        strum = max(0, min(1, strum))
        
        for i, pitch in enumerate(pitches):
            taper_factor = 1.0 - (i / num_partials) * 0.6 if num_partials > 0 else 1.0
            vel = base_amp * taper_factor
            
            start_offset = (strum * dur * i) / num_partials if num_partials > 1 else 0
            
            events.append({
                "start": start_offset,
                "duration": dur - start_offset,
                "instrument": "sine",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": min(1.0, max(0.05, vel)),
                }
            })
    
    return events


def temporal_unit_to_events(obj, use_absolute_time=False):
    events = []
    
    if use_absolute_time:
        time_offset = 0
    else:
        time_offset = min(chronon.start for chronon in obj if not chronon.is_rest) if any(not chronon.is_rest for chronon in obj) else 0
    
    for chronon in obj:
        if not chronon.is_rest:
            start_time = chronon.start - time_offset
            duration = abs(chronon.duration)
            
            events.append({
                "start": start_time,
                "duration": duration,
                "instrument": "membrane",
                "pfields": {
                    "freq": DEFAULT_DRUM_FREQ,
                    "vel": 0.85,
                }
            })
    
    return events


def rhythm_tree_to_events(obj, beat=None, bpm=None):
    temporal_unit = TemporalUnit.from_rt(obj, beat=beat, bpm=bpm)
    return temporal_unit_to_events(temporal_unit, use_absolute_time=False)


def temporal_sequence_to_events(obj):
    events = []
    instruments = {}
    
    seq_offset = obj.offset
    
    for unit in obj:
        if isinstance(unit, CompositionalUnit):
            payload = compositional_unit_to_events(unit)
            unit_events = payload["events"]
            instruments.update(payload["instruments"])
            for ev in unit_events:
                ev["start"] -= seq_offset
            events.extend(unit_events)
        elif isinstance(unit, TemporalUnit):
            unit_events = temporal_unit_to_events(unit, use_absolute_time=True)
            for ev in unit_events:
                ev["start"] -= seq_offset
            events.extend(unit_events)
        elif isinstance(unit, TemporalUnitSequence):
            sub_events = temporal_sequence_to_events(unit)
            if isinstance(sub_events, dict):
                for ev in sub_events["events"]:
                    ev["start"] -= seq_offset
                events.extend(sub_events["events"])
                instruments.update(sub_events["instruments"])
            else:
                events.extend(sub_events)
        elif isinstance(unit, TemporalBlock):
            sub_events = temporal_block_to_events(unit)
            if isinstance(sub_events, dict):
                for ev in sub_events["events"]:
                    ev["start"] -= seq_offset
                events.extend(sub_events["events"])
                instruments.update(sub_events["instruments"])
            else:
                events.extend(sub_events)
    
    events.sort(key=lambda ev: ev["start"])
    if instruments:
        return {"events": events, "instruments": instruments}
    return events


def temporal_block_to_events(obj):
    events = []
    instruments = {}
    
    block_offset = obj.offset
    
    for row in obj:
        if isinstance(row, CompositionalUnit):
            payload = compositional_unit_to_events(row)
            row_events = payload["events"]
            instruments.update(payload["instruments"])
            for ev in row_events:
                ev["start"] -= block_offset
            events.extend(row_events)
        elif isinstance(row, TemporalUnit):
            row_events = temporal_unit_to_events(row, use_absolute_time=True)
            for ev in row_events:
                ev["start"] -= block_offset
            events.extend(row_events)
        elif isinstance(row, TemporalUnitSequence):
            sub_events = temporal_sequence_to_events(row)
            if isinstance(sub_events, dict):
                for ev in sub_events["events"]:
                    ev["start"] -= block_offset + row.offset
                events.extend(sub_events["events"])
                instruments.update(sub_events["instruments"])
            else:
                for ev in sub_events:
                    ev["start"] -= block_offset + row.offset
                events.extend(sub_events)
        elif isinstance(row, TemporalBlock):
            sub_events = temporal_block_to_events(row)
            if isinstance(sub_events, dict):
                for ev in sub_events["events"]:
                    ev["start"] -= block_offset + row.offset
                events.extend(sub_events["events"])
                instruments.update(sub_events["instruments"])
            else:
                for ev in sub_events:
                    ev["start"] -= block_offset + row.offset
                events.extend(sub_events)
    
    events.sort(key=lambda ev: ev["start"])
    if instruments:
        return {"events": events, "instruments": instruments}
    return events


def convert_to_events(obj, **kwargs):
    duration = kwargs.get('dur', kwargs.get('duration', None))
    arp = kwargs.get('arp', False)
    mode = kwargs.get('mode', None)
    strum = kwargs.get('strum', 0)
    direction = kwargs.get('dir', 'u')
    equaves = kwargs.get('equaves', 1)
    beat = kwargs.get('beat', None)
    bpm = kwargs.get('bpm', None)
    
    if isinstance(obj, Pitch):
        return pitch_to_events(obj, duration=duration)
    
    if isinstance(obj, Spectrum):
        return spectrum_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)
    
    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_events(spectrum, duration=duration, arp=arp, strum=strum, direction=direction)
    
    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_events(obj, beat=beat, bpm=bpm)
    
    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_events(obj)
    
    if isinstance(obj, TemporalBlock):
        return temporal_block_to_events(obj)
    
    if isinstance(obj, CompositionalUnit):
        return compositional_unit_to_events(obj)
    
    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_events(obj)
    
    if isinstance(obj, ChordSequence):
        return chord_sequence_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)
    
    if isinstance(obj, Scale):
        return scale_to_events(obj, duration=duration, equaves=equaves)
    
    if isinstance(obj, (Chord, Voicing, Sonority)):
        return chord_to_events(obj, duration=duration, arp=arp, strum=strum, direction=direction)
    
    if isinstance(obj, PitchCollectionBase):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_events(obj, duration=duration, mode="chord", arp=arp, strum=strum, direction=direction)
        return pitch_collection_to_events(obj, duration=duration, mode="sequential")
    
    raise TypeError(f"Unsupported object type: {type(obj)}")

