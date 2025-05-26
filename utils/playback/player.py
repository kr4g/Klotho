from pythonosc import udp_client
import time
import threading
from klotho.tonos import Pitch, PitchCollection, EquaveCyclicPitchCollection, Scale, Chord, AddressedPitchCollection
from klotho.tonos.chords.chord import AddressedChord
from klotho.tonos.scales.scale import AddressedScale

client = udp_client.SimpleUDPClient("127.0.0.1", 57110) # we want the server port, not the lang port

def play(obj, verbose=False, **kwargs):
    match obj:
        case Pitch():
            _play_pitch(obj, verbose)
        
        case PitchCollection() | EquaveCyclicPitchCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                _play_scale(obj, verbose)
            elif isinstance(obj, (Chord, AddressedChord)):
                _play_chord(obj, verbose)
            else:
                _play_pitch_collection(obj, verbose)
        
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}")

def _get_addressed_collection(obj):
    if hasattr(obj, 'freq') or isinstance(obj, (AddressedPitchCollection, AddressedScale, AddressedChord)):
        return obj
    else:
        return obj.root("C4")

def _play_pitch(pitch, verbose=False):
    node_id = int(time.time() * 1000) % 10000 + 1000
    if verbose:
        print(f"Sending OSC: /s_new ['default', {node_id}, 0, 1, 'freq', {pitch.freq}, 'amp', 0.1]")
    client.send_message("/s_new", ["default", node_id, 0, 1, "freq", pitch.freq, "amp", 0.1])
    threading.Timer(1.0, lambda: _send_gate_off(node_id, verbose)).start()

def _send_gate_off(node_id, verbose=False):
    if verbose:
        print(f"Sending OSC: /n_set [{node_id}, 'gate', 0]")
    client.send_message("/n_set", [node_id, "gate", 0])

def _play_pitch_collection(obj, verbose=False):
    addressed_collection = _get_addressed_collection(obj)
    for i, pitch in enumerate([addressed_collection[j] for j in range(len(addressed_collection))]):
        delay = i * 0.5
        threading.Timer(delay, _play_pitch_with_release, [pitch, 0.08, verbose]).start()

def _play_scale(obj, verbose=False):
    addressed_scale = _get_addressed_collection(obj)
    scale_with_equave = []
    for i in range(len(addressed_scale)):
        scale_with_equave.append(addressed_scale[i])
    scale_with_equave.append(addressed_scale[len(addressed_scale)])
    
    for i, pitch in enumerate(scale_with_equave):
        delay = i * 0.5
        threading.Timer(delay, _play_pitch_with_release, [pitch, 0.08, verbose]).start()

def _play_chord(obj, verbose=False):
    addressed_chord = _get_addressed_collection(obj)
    num_notes = len(addressed_chord)
    base_node_id = int(time.time() * 1000) % 10000 + 2000
    
    max_total_amp = 0.5
    base_amp = max_total_amp / (num_notes * 0.7)
    
    for i, pitch in enumerate([addressed_chord[j] for j in range(num_notes)]):
        taper_factor = 1.0 - (i / num_notes) * 0.6
        amp = base_amp * taper_factor
        
        node_id = base_node_id + i
        if verbose:
            print(f"Sending OSC: /s_new ['default', {node_id}, 0, 1, 'freq', {pitch.freq}, 'amp', {amp:.3f}] (note {i+1}/{num_notes})")
        client.send_message("/s_new", ["default", node_id, 0, 1, "freq", pitch.freq, "amp", amp])
    
    threading.Timer(2.0, lambda: _send_free_group(base_node_id, num_notes, verbose)).start()

def _send_free_group(base_node_id, num_notes, verbose=False):
    for i in range(num_notes):
        node_id = base_node_id + i
        if verbose:
            print(f"Sending OSC: /n_free [{node_id}]")
        client.send_message("/n_free", [node_id])

def _play_pitch_with_release(pitch, amp, verbose=False):
    node_id = int(time.time() * 1000) % 10000 + 3000
    if verbose:
        print(f"Sending OSC: /s_new ['default', {node_id}, 0, 1, 'freq', {pitch.freq}, 'amp', {amp}]")
    client.send_message("/s_new", ["default", node_id, 0, 1, "freq", pitch.freq, "amp", amp])
    threading.Timer(0.4, lambda: _send_gate_off(node_id, verbose)).start()