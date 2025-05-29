from pythonosc import udp_client
import time
import threading
from klotho.tonos import Pitch, PitchCollection, EquaveCyclicPitchCollection, Scale, Chord, AddressedPitchCollection
from klotho.tonos.chords.chord import AddressedChord
from klotho.tonos.scales.scale import AddressedScale
from klotho.aikous.expression.dynamics import freq_amp_scale, ampdb, dbamp

client = udp_client.SimpleUDPClient("127.0.0.1", 57110)

_active_timers = []
_timer_lock = threading.Lock()

def _track_timer(timer):
    with _timer_lock:
        _active_timers.append(timer)

def _cleanup_timer(timer):
    with _timer_lock:
        if timer in _active_timers:
            _active_timers.remove(timer)

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
        sync_time = time.time()
        cumulative_delay = 0.0
        
        for item in self.pending_plays:
            if item[0] == 'pause':
                cumulative_delay += item[1]
            else:
                obj, verbose, kwargs = item
                timer = threading.Timer(cumulative_delay, lambda o=obj, v=verbose, k=kwargs: _execute_play(o, v, sync_time, **k))
                _track_timer(timer)
                timer.start()
        
        self.in_sync_mode = False
        self.pending_plays = []
    
    def add_play(self, obj, verbose=False, **kwargs):
        self.pending_plays.append((obj, verbose, kwargs))
    
    def add_pause(self, duration):
        self.pending_plays.append(('pause', duration))

_sync_player = SyncPlayer()

def sync():
    return _sync_player

def pause(duration):
    if not _sync_player.in_sync_mode:
        raise RuntimeError("pause() can only be used within a sync() context manager")
    _sync_player.add_pause(duration)

def stop():
    with _timer_lock:
        for timer in _active_timers[:]:
            timer.cancel()
        _active_timers.clear()
    
    if _sync_player.in_sync_mode:
        _sync_player.pending_plays.clear()
    
    client.send_message("/g_freeAll", [0])

def play(obj, verbose=False, **kwargs):
    if _sync_player.in_sync_mode:
        _sync_player.add_play(obj, verbose, **kwargs)
    else:
        _execute_play(obj, verbose, None, **kwargs)

def _execute_play(obj, verbose=False, sync_time=None, **kwargs):
    match obj:
        case Pitch():
            _play_pitch(obj, verbose, sync_time)
        
        case PitchCollection() | EquaveCyclicPitchCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                _play_scale(obj, verbose, sync_time)
            elif isinstance(obj, (Chord, AddressedChord)):
                _play_chord(obj, verbose, sync_time)
            else:
                _play_pitch_collection(obj, verbose, sync_time)
        
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}")

def _get_addressed_collection(obj):
    if hasattr(obj, 'freq') or isinstance(obj, (AddressedPitchCollection, AddressedScale, AddressedChord)):
        return obj
    else:
        return obj.root("C4")

def _create_timer_with_cleanup(delay, func):
    timer = None
    
    def cleanup_wrapper():
        func()
        if timer:
            _cleanup_timer(timer)
    
    timer = threading.Timer(delay, cleanup_wrapper)
    _track_timer(timer)
    return timer

def _play_pitch(pitch, verbose=False, sync_time=None):
    node_id = _node_id_gen.get_id(1000)
    if verbose:
        print(f"Sending OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', 0.1]")
    client.send_message("/s_new", ["default", node_id, 0, 0, "freq", pitch.freq, "amp", freq_amp_scale(pitch.freq, ampdb(0.2))])
    
    timer = _create_timer_with_cleanup(1.0, lambda: _send_gate_off(node_id, verbose))
    timer.start()

def _send_gate_off(node_id, verbose=False):
    if verbose:
        print(f"Sending OSC: /n_set [{node_id}, 'gate', 0]")
    client.send_message("/n_set", [node_id, "gate", 0])

def _play_pitch_collection(obj, verbose=False, sync_time=None):
    addressed_collection = _get_addressed_collection(obj)
    base_delay = 0.0 if sync_time else 0.0
    for i, pitch in enumerate([addressed_collection[j] for j in range(len(addressed_collection))]):
        delay = base_delay + i * 0.5
        timer = _create_timer_with_cleanup(delay, lambda p=pitch: _play_pitch_with_release(p, 0.08, verbose))
        timer.start()

def _play_scale(obj, verbose=False, sync_time=None):
    addressed_scale = _get_addressed_collection(obj)
    scale_with_equave = []
    for i in range(len(addressed_scale)):
        scale_with_equave.append(addressed_scale[i])
    scale_with_equave.append(addressed_scale[len(addressed_scale)])
    
    base_delay = 0.0 if sync_time else 0.0
    for i, pitch in enumerate(scale_with_equave):
        delay = base_delay + i * 0.5
        timer = _create_timer_with_cleanup(delay, lambda p=pitch: _play_pitch_with_release(p, 0.08, verbose))
        timer.start()

def _play_chord(obj, verbose=False, sync_time=None):
    addressed_chord = _get_addressed_collection(obj)
    num_notes = len(addressed_chord)
    
    max_total_amp = 0.5
    base_amp = max_total_amp / (num_notes * 0.7)
    
    node_ids = []
    for i, pitch in enumerate([addressed_chord[j] for j in range(num_notes)]):
        taper_factor = 1.0 - (i / num_notes) * 0.6
        amp = base_amp * taper_factor
        
        node_id = _node_id_gen.get_id(2000)
        node_ids.append(node_id)
        if verbose:
            print(f"Sending OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', {amp:.3f}] (note {i+1}/{num_notes})")
        client.send_message("/s_new", ["default", node_id, 0, 0, "freq", pitch.freq, "amp", amp])
    
    timer = _create_timer_with_cleanup(2.0, lambda ids=node_ids: _send_free_group_by_ids(ids, verbose))
    timer.start()

def _send_free_group_by_ids(node_ids, verbose=False):
    for node_id in node_ids:
        if verbose:
            print(f"Sending OSC: /n_free [{node_id}]")
        client.send_message("/n_free", [node_id])

def _play_pitch_with_release(pitch, amp, verbose=False):
    node_id = _node_id_gen.get_id(3000)
    if verbose:
        print(f"Sending OSC: /s_new ['default', {node_id}, 0, 0, 'freq', {pitch.freq}, 'amp', {amp}]")
    client.send_message("/s_new", ["default", node_id, 0, 0, "freq", pitch.freq, "amp", amp])
    
    timer = _create_timer_with_cleanup(0.4, lambda: _send_gate_off(node_id, verbose))
    timer.start() 