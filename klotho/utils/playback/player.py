from pythonosc import udp_client, osc_bundle_builder, osc_message_builder
import time
import threading
from klotho.tonos import Pitch, PitchCollection, EquaveCyclicCollection, Scale, Chord, AddressedPitchCollection
from klotho.tonos.chords.chord import AddressedChord
from klotho.tonos.scales.scale import AddressedScale
from klotho.dynatos.dynamics import freq_amp_scale, ampdb
from klotho.chronos.temporal_units.temporal import TemporalUnit

client = udp_client.SimpleUDPClient("127.0.0.1", 57110)

BUFFER_TIME = 0.15

class NodeIDGenerator:
    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()
    
    def get_id(self, base_offset=1000):
        with self._lock:
            self._counter += 1
            timestamp_part = int(time.time() * 1000) % 1000
            return base_offset + timestamp_part * 1000 + (self._counter % 1000)

_node_id_gen = NodeIDGenerator()

class SyncPlayer:
    def __init__(self):
        self.pending_plays = []
        self.in_sync_mode = False
    
    def __enter__(self):
        self.in_sync_mode = True
        self.pending_plays = []
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sync_start_time = time.time() + BUFFER_TIME
        cumulative_delay = 0.0
        
        for item in self.pending_plays:
            if item[0] == 'pause':
                cumulative_delay += item[1]
            else:
                obj, verbose, kwargs = item
                event_time = sync_start_time + cumulative_delay
                _execute_play(obj, verbose, event_time, **kwargs)
        
        self.in_sync_mode = False
        self.pending_plays = []
    
    def add_play(self, obj, verbose=False, **kwargs):
        self.pending_plays.append((obj, verbose, kwargs))
    
    def add_pause(self, duration):
        self.pending_plays.append(('pause', duration))

_sync_player = SyncPlayer()

def sync():
    """Context manager for synchronized playback of multiple musical objects."""
    return _sync_player

def pause(duration):
    """Add a pause within a sync() context manager."""
    if not _sync_player.in_sync_mode:
        raise RuntimeError("pause() can only be used within a sync() context manager")
    _sync_player.add_pause(duration)

def stop():
    """Stop all sound immediately, equivalent to cmd+. in SuperCollider."""
    if _sync_player.in_sync_mode:
        _sync_player.pending_plays.clear()
    
    client.send_message("/clearSched", [])
    client.send_message("/g_deepFree", [0])

def play(obj, verbose=False, **kwargs):
    """Play a musical object (Pitch, PitchCollection, Scale, or Chord)."""
    if _sync_player.in_sync_mode:
        _sync_player.add_play(obj, verbose, **kwargs)
    else:
        _execute_play(obj, verbose, time.time() + BUFFER_TIME, **kwargs)

def _execute_play(obj, verbose=False, start_time=None, **kwargs):
    """Execute playback of a musical object at a specific time."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    match obj:
        case Pitch():
            _play_pitch(obj, verbose, start_time)
        
        case PitchCollection() | EquaveCyclicCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                _play_scale(obj, verbose, start_time)
            elif isinstance(obj, (Chord, AddressedChord)):
                _play_chord(obj, verbose, start_time)
            else:
                _play_pitch_collection(obj, verbose, start_time)
        
        case TemporalUnit():
            _play_temporal_unit(obj, verbose, start_time)
        
        case dict():
            _play_structured(obj, verbose, start_time)
        
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}")

def _get_addressed_collection(obj):
    """Get an addressed version of a pitch collection."""
    if hasattr(obj, 'freq') or isinstance(obj, (AddressedPitchCollection, AddressedScale, AddressedChord)):
        return obj
    else:
        return obj.root("C4")

def _send_bundle(bundle):
    """Send a bundle to SuperCollider."""
    client.send(bundle)

def _create_synth_message(synth_name, node_id, freq, amp):
    """Create a /s_new OSC message for creating a synth."""
    msg = osc_message_builder.OscMessageBuilder("/s_new")
    msg.add_arg(synth_name)
    msg.add_arg(node_id)
    msg.add_arg(0)
    msg.add_arg(0)
    msg.add_arg("freq")
    msg.add_arg(freq)
    msg.add_arg("amp")
    msg.add_arg(amp)
    return msg.build()

def _create_gate_off_message(node_id):
    """Create a gate off OSC message for releasing a synth."""
    msg = osc_message_builder.OscMessageBuilder("/n_set")
    msg.add_arg(node_id)
    msg.add_arg("gate")
    msg.add_arg(0)
    return msg.build()

def _create_free_message(node_id):
    """Create a node free OSC message."""
    msg = osc_message_builder.OscMessageBuilder("/n_free")
    msg.add_arg(node_id)
    return msg.build()

def _play_pitch(pitch, verbose=False, start_time=None):
    """Play a single pitch with automatic release."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    node_id = _node_id_gen.get_id(1000)
    
    start_bundle = osc_bundle_builder.OscBundleBuilder(start_time)
    start_bundle.add_content(_create_synth_message(
        "default", node_id, pitch.freq, freq_amp_scale(pitch.freq, ampdb(0.2))
    ))
    
    if verbose:
        print(f"Scheduling OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', {freq_amp_scale(pitch.freq, ampdb(0.2)):.3f}] at {start_time}")
    
    _send_bundle(start_bundle.build())
    
    release_time = start_time + 1.0
    release_bundle = osc_bundle_builder.OscBundleBuilder(release_time)
    release_bundle.add_content(_create_gate_off_message(node_id))
    
    if verbose:
        print(f"Scheduling OSC: /n_set [{node_id}, 'gate', 0] at {release_time}")
    
    _send_bundle(release_bundle.build())

def _play_pitch_collection(obj, verbose=False, start_time=None):
    """Play a pitch collection as an arpeggio."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    addressed_collection = _get_addressed_collection(obj)
    
    for i, pitch in enumerate([addressed_collection[j] for j in range(len(addressed_collection))]):
        note_time = start_time + i * 0.5
        _play_pitch_with_release_at_time(pitch, 0.08, note_time, verbose)

def _play_scale(obj, verbose=False, start_time=None):
    """Play a scale as an arpeggio with octave completion."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    addressed_scale = _get_addressed_collection(obj)
    scale_with_equave = []
    for i in range(len(addressed_scale)):
        scale_with_equave.append(addressed_scale[i])
    scale_with_equave.append(addressed_scale[len(addressed_scale)])
    
    for i, pitch in enumerate(scale_with_equave):
        note_time = start_time + i * 0.5
        _play_pitch_with_release_at_time(pitch, 0.08, note_time, verbose)

def _play_chord(obj, verbose=False, start_time=None):
    """Play a chord with all notes sounding simultaneously."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    addressed_chord = _get_addressed_collection(obj)
    num_notes = len(addressed_chord)
    
    max_total_amp = 0.5
    base_amp = max_total_amp / (num_notes * 0.7)
    
    chord_start_bundle = osc_bundle_builder.OscBundleBuilder(start_time)
    chord_release_bundle = osc_bundle_builder.OscBundleBuilder(start_time + 2.0)
    
    for i, pitch in enumerate([addressed_chord[j] for j in range(num_notes)]):
        taper_factor = 1.0 - (i / num_notes) * 0.6
        amp = base_amp * taper_factor
        
        node_id = _node_id_gen.get_id(2000)
        
        chord_start_bundle.add_content(_create_synth_message("default", node_id, pitch.freq, amp))
        chord_release_bundle.add_content(_create_free_message(node_id))
        
        if verbose:
            print(f"Scheduling OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', {amp:.3f}] at {start_time} (note {i+1}/{num_notes})")
    
    _send_bundle(chord_start_bundle.build())
    _send_bundle(chord_release_bundle.build())

def _play_temporal_unit(temporal_unit, verbose=False, start_time=None):
    """Play a TemporalUnit by scheduling each individual Chronon event."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    default_pitch = Pitch("C4")
    
    for chronon in temporal_unit:
        if chronon.is_rest:
            continue
        
        event_time = start_time + chronon.start
        event_duration = abs(chronon.duration * 0.25)
        
        node_id = _node_id_gen.get_id(4000)
        
        start_bundle = osc_bundle_builder.OscBundleBuilder(event_time)
        start_bundle.add_content(_create_synth_message(
            "default", node_id, default_pitch.freq, freq_amp_scale(default_pitch.freq, ampdb(0.2))
        ))
        
        if verbose:
            print(f"Scheduling OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {default_pitch.freq}, 'amp', {freq_amp_scale(default_pitch.freq, ampdb(0.2)):.3f}] at {event_time}")
        
        _send_bundle(start_bundle.build())
        
        release_time = event_time + event_duration
        release_bundle = osc_bundle_builder.OscBundleBuilder(release_time)
        release_bundle.add_content(_create_gate_off_message(node_id))
        
        if verbose:
            print(f"Scheduling OSC: /n_set [{node_id}, 'gate', 0] at {release_time}")
        
        _send_bundle(release_bundle.build())

def _play_structured(obj_dict, verbose=False, start_time=None):
    """Play a structured musical expression from a dictionary with freq, dur, amp keys."""
    if start_time is None:
        start_time = time.time() + BUFFER_TIME
    
    freq_obj = obj_dict.get('freq')
    dur_obj = obj_dict.get('dur') 
    amp_obj = obj_dict.get('amp')
    
    frequencies = _extract_frequencies(freq_obj)
    durations, onsets = _extract_durations_and_onsets(dur_obj)
    amplitudes = _extract_amplitudes(amp_obj, frequencies)
    
    min_length = min(len(frequencies), len(durations), len(amplitudes))
    
    for i in range(min_length):
        event_time = start_time + onsets[i]
        node_id = _node_id_gen.get_id(5000)
        
        start_bundle = osc_bundle_builder.OscBundleBuilder(event_time)
        start_bundle.add_content(_create_synth_message(
            "default", node_id, frequencies[i], amplitudes[i]
        ))
        
        if verbose:
            print(f"Scheduling OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {frequencies[i]}, 'amp', {amplitudes[i]:.3f}] at {event_time}")
        
        _send_bundle(start_bundle.build())
        
        release_time = event_time + durations[i]
        release_bundle = osc_bundle_builder.OscBundleBuilder(release_time)
        release_bundle.add_content(_create_gate_off_message(node_id))
        
        if verbose:
            print(f"Scheduling OSC: /n_set [{node_id}, 'gate', 0] at {release_time}")
        
        _send_bundle(release_bundle.build())

def _extract_frequencies(freq_obj):
    """Extract frequencies from various pitch object types."""
    if freq_obj is None:
        return [Pitch("C4").freq]
    
    if isinstance(freq_obj, Pitch):
        return [freq_obj.freq]
    
    if isinstance(freq_obj, (PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, Chord, AddressedScale, AddressedChord)):
        addressed_collection = _get_addressed_collection(freq_obj)
        return [addressed_collection[i].freq for i in range(len(addressed_collection))]
    
    return [Pitch("C4").freq]

def _extract_durations_and_onsets(dur_obj):
    """Extract durations and onset times from temporal objects or values."""
    if dur_obj is None:
        return [1.0], [0.0]
    
    if isinstance(dur_obj, TemporalUnit):
        durations = []
        onsets = []
        for chronon in dur_obj:
            if not chronon.is_rest:
                durations.append(abs(chronon.duration * 0.25))
                onsets.append(chronon.start)
        return durations or [1.0], onsets or [0.0]
    
    if isinstance(dur_obj, (int, float)):
        return [float(dur_obj)], [0.0]
    
    if isinstance(dur_obj, (list, tuple)):
        cumulative_onset = 0.0
        durations = []
        onsets = []
        for d in dur_obj:
            durations.append(float(d))
            onsets.append(cumulative_onset)
            cumulative_onset += float(d)
        return durations, onsets
    
    return [1.0], [0.0]

def _extract_amplitudes(amp_obj, frequencies):
    """Extract amplitudes, with frequency-based defaults."""
    if amp_obj is None:
        return [freq_amp_scale(freq, ampdb(0.2)) for freq in frequencies]
    
    if isinstance(amp_obj, (int, float)):
        return [float(amp_obj)] * len(frequencies)
    
    if isinstance(amp_obj, (list, tuple)):
        return [float(amp) for amp in amp_obj]
    
    return [freq_amp_scale(freq, ampdb(0.2)) for freq in frequencies]

def _play_pitch_with_release_at_time(pitch, amp, start_time, verbose=False):
    """Play a pitch with automatic release at a specific absolute time."""
    node_id = _node_id_gen.get_id(3000)
    
    start_bundle = osc_bundle_builder.OscBundleBuilder(start_time)
    start_bundle.add_content(_create_synth_message("default", node_id, pitch.freq, amp))
    
    if verbose:
        print(f"Scheduling OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', {amp}] at {start_time}")
    
    _send_bundle(start_bundle.build())
    
    release_time = start_time + 0.4
    release_bundle = osc_bundle_builder.OscBundleBuilder(release_time)
    release_bundle.add_content(_create_gate_off_message(node_id))
    
    if verbose:
        print(f"Scheduling OSC: /n_set [{node_id}, 'gate', 0] at {release_time}")
    
    _send_bundle(release_bundle.build())