from klotho.tonos import Pitch, PitchCollection, EquaveCyclicCollection, InstancedPitchCollection
from klotho.tonos.chords.chord import Chord, InstancedChord, Sonority, InstancedSonority, ChordSequence
from klotho.tonos.scales.scale import Scale, InstancedScale
from klotho.tonos.systems.harmonic_trees import Spectrum, HarmonicTree
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.dynatos.dynamics import freq_amp_scale, ampdb

DEFAULT_NOTE_DURATION = 0.5
DEFAULT_CHORD_DURATION = 2.0
DEFAULT_SPECTRUM_DURATION = 3.0
DEFAULT_DRUM_FREQ = 120.0


def freq_to_velocity(freq, base_vel=0.6):
    scaled_amp = freq_amp_scale(freq, ampdb(0.2))
    return min(1.0, max(0.1, base_vel * (scaled_amp / 0.2)))


def _get_addressed_collection(obj):
    if hasattr(obj, 'freq') or isinstance(obj, (InstancedPitchCollection, InstancedScale, InstancedChord, InstancedSonority)):
        return obj
    else:
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


def pitch_collection_to_events(obj, duration=None, mode="sequential"):
    events = []
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    addressed = _get_addressed_collection(obj)
    
    pitches = [addressed[i] for i in range(len(addressed))]
    
    if mode == "chord":
        num_notes = len(pitches)
        max_total_amp = 0.5
        base_amp = max_total_amp / (num_notes * 0.7) if num_notes > 0 else 0.5
        
        for i, pitch in enumerate(pitches):
            taper_factor = 1.0 - (i / num_notes) * 0.6 if num_notes > 0 else 1.0
            vel = base_amp * taper_factor
            events.append({
                "start": 0.0,
                "duration": dur,
                "instrument": "synth",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": min(1.0, max(0.1, vel)),
                }
            })
    else:
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


def scale_to_events(obj, duration=None):
    events = []
    dur = duration if duration is not None else DEFAULT_NOTE_DURATION
    addressed = _get_addressed_collection(obj)
    
    pitches_up = [addressed[i] for i in range(len(addressed))]
    pitches_up.append(addressed[len(addressed)])
    
    pitches_down = list(reversed(pitches_up[:-1]))
    
    all_pitches = pitches_up + pitches_down
    
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


def chord_to_events(obj, duration=None, arp=False):
    dur = duration if duration is not None else DEFAULT_CHORD_DURATION
    
    if arp:
        return pitch_collection_to_events(obj, duration=dur / len(_get_addressed_collection(obj)), mode="sequential")
    else:
        return pitch_collection_to_events(obj, duration=dur, mode="chord")


def chord_sequence_to_events(obj, duration=None):
    events = []
    dur = duration if duration is not None else DEFAULT_CHORD_DURATION
    current_time = 0.0
    
    for chord in obj:
        addressed = _get_addressed_collection(chord)
        pitches = [addressed[i] for i in range(len(addressed))]
        num_notes = len(pitches)
        max_total_amp = 0.5
        base_amp = max_total_amp / (num_notes * 0.7) if num_notes > 0 else 0.5
        
        for i, pitch in enumerate(pitches):
            taper_factor = 1.0 - (i / num_notes) * 0.6 if num_notes > 0 else 1.0
            vel = base_amp * taper_factor
            events.append({
                "start": current_time,
                "duration": dur * 0.95,
                "instrument": "synth",
                "pfields": {
                    "freq": pitch.freq,
                    "vel": min(1.0, max(0.1, vel)),
                }
            })
        
        current_time += dur
    
    return events


def spectrum_to_events(obj, duration=None):
    events = []
    dur = duration if duration is not None else DEFAULT_SPECTRUM_DURATION
    
    num_partials = len(obj.data)
    max_total_amp = 0.4
    base_amp = max_total_amp / (num_partials * 0.7) if num_partials > 0 else 0.4
    
    for i, row in obj.data.iterrows():
        pitch = row['pitch']
        taper_factor = 1.0 - (i / num_partials) * 0.6 if num_partials > 0 else 1.0
        vel = base_amp * taper_factor
        
        events.append({
            "start": 0.0,
            "duration": dur,
            "instrument": "sine",
            "pfields": {
                "freq": pitch.freq,
                "vel": min(1.0, max(0.05, vel)),
            }
        })
    
    return events


def temporal_unit_to_events(obj):
    events = []
    
    min_start = min(chronon.start for chronon in obj if not chronon.is_rest) if any(not chronon.is_rest for chronon in obj) else 0
    
    for chronon in obj:
        if not chronon.is_rest:
            start_time = chronon.start - min_start
            duration = abs(chronon.duration)
            
            events.append({
                "start": start_time,
                "duration": min(duration, 0.15),
                "instrument": "membrane",
                "pfields": {
                    "freq": DEFAULT_DRUM_FREQ,
                    "vel": 0.85,
                }
            })
    
    return events


def rhythm_tree_to_events(obj):
    temporal_unit = TemporalUnit.from_rt(obj)
    return temporal_unit_to_events(temporal_unit)


def temporal_sequence_to_events(obj):
    events = []
    
    for unit in obj:
        if isinstance(unit, TemporalUnit):
            unit_events = temporal_unit_to_events(unit)
            events.extend(unit_events)
        elif isinstance(unit, TemporalUnitSequence):
            events.extend(temporal_sequence_to_events(unit))
        elif isinstance(unit, TemporalBlock):
            events.extend(temporal_block_to_events(unit))
    
    return events


def temporal_block_to_events(obj):
    events = []
    
    for row in obj:
        if isinstance(row, TemporalUnit):
            events.extend(temporal_unit_to_events(row))
        elif isinstance(row, TemporalUnitSequence):
            events.extend(temporal_sequence_to_events(row))
        elif isinstance(row, TemporalBlock):
            events.extend(temporal_block_to_events(row))
    
    return events


def convert_to_events(obj, **kwargs):
    duration = kwargs.get('dur', kwargs.get('duration', None))
    arp = kwargs.get('arp', False)
    mode = kwargs.get('mode', None)
    
    if isinstance(obj, Pitch):
        return pitch_to_events(obj, duration=duration)
    
    if isinstance(obj, Spectrum):
        return spectrum_to_events(obj, duration=duration)
    
    if isinstance(obj, HarmonicTree):
        spectrum = Spectrum(Pitch("C4"), list(obj.partials) if hasattr(obj, 'partials') else [1, 2, 3, 4, 5])
        return spectrum_to_events(spectrum, duration=duration)
    
    if isinstance(obj, RhythmTree):
        return rhythm_tree_to_events(obj)
    
    if isinstance(obj, TemporalUnitSequence):
        return temporal_sequence_to_events(obj)
    
    if isinstance(obj, TemporalBlock):
        return temporal_block_to_events(obj)
    
    if isinstance(obj, TemporalUnit):
        return temporal_unit_to_events(obj)
    
    if isinstance(obj, ChordSequence):
        return chord_sequence_to_events(obj, duration=duration)
    
    if isinstance(obj, Scale) and not isinstance(obj, InstancedPitchCollection):
        return scale_to_events(obj, duration=duration)
    
    if isinstance(obj, (Chord, Sonority)) and not isinstance(obj, InstancedPitchCollection):
        return chord_to_events(obj, duration=duration, arp=arp)
    
    if isinstance(obj, (PitchCollection, EquaveCyclicCollection, InstancedPitchCollection)):
        effective_mode = mode if mode else "sequential"
        if effective_mode == "chord":
            return pitch_collection_to_events(obj, duration=duration or DEFAULT_CHORD_DURATION, mode="chord")
        return pitch_collection_to_events(obj, duration=duration, mode="sequential")
    
    raise TypeError(f"Unsupported object type: {type(obj)}")

