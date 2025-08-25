from IPython.display import Audio
import os
import tempfile
import urllib.request
import numpy as np
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

# FluidSynth imports for sequencer-based synthesis
try:
    import fluidsynth
    HAS_FLUIDSYNTH = True
except ImportError:
    HAS_FLUIDSYNTH = False
from klotho.chronos.rhythm_trees.rhythm_tree import RhythmTree
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.instrument import MidiInstrument
from klotho.tonos.pitch.pitch_collections import PitchCollection, EquaveCyclicCollection, AddressedPitchCollection
from klotho.tonos.pitch.pitch import Pitch
from klotho.tonos.scales.scale import Scale, AddressedScale
from klotho.tonos.chords.chord import Chord, AddressedChord

DEFAULT_DRUM_NOTE = 77
PERCUSSION_CHANNEL = 9
DEFAULT_VELOCITY = 120
SEQUENCER_TIME_SCALE = 1000
SAMPLE_RATE = 44100

# Expanded Microtonal Configuration for FluidSynth Sequencer
# Each unique microtonal pitch gets its own dedicated channel with precise pitch bend
# Channels 0-8, 10-255 are available for pitched instruments (channel 9 reserved for percussion)
# 255 channels total eliminates pitch bend conflicts during overlapping microtonal notes
# Each channel is pre-tuned once to its specific microtonal frequency

SOUNDFONT_URL = "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3"
SOUNDFONT_PATH = os.path.expanduser("~/.fluidsynth/default_sound_font.sf2")

def _is_colab():
    """Check if we're running in Google Colab."""
    try:
        import google.colab
        return True
    except ImportError:
        return False


def _ensure_soundfont():
    """Download and install a SoundFont if none exists."""
    sf_dir = os.path.dirname(SOUNDFONT_PATH)
    if not os.path.exists(sf_dir):
        os.makedirs(sf_dir)
    
    if not os.path.exists(SOUNDFONT_PATH):
        print("Downloading SoundFont for MIDI playback (one-time setup)...")
        try:
            urllib.request.urlretrieve(SOUNDFONT_URL, SOUNDFONT_PATH)
            print("SoundFont installed successfully!")
        except Exception as e:
            print(f"Could not download SoundFont: {e}")
            return None
    
    return SOUNDFONT_PATH



def play_midi(obj, dur=None, arp=False, prgm=0, **kwargs):
    """
    Play a musical object as MIDI audio using FluidSynth sequencer.
    
    Uses pyfluidsynth's sequencer API for precise timing and expanded microtonal capabilities.
    Works across all environments (Jupyter, Colab, local) with consistent behavior.
    
    Parameters
    ----------
    obj : RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, TemporalBlock,
          PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, or Chord
        The musical object to play. Different object types have different playback behaviors:
        - RhythmTree/TemporalUnit: Rhythmic playback with default pitch
        - PitchCollection/AddressedPitchCollection: Sequential pitch playback
        - Scale/AddressedScale: Ascending then descending playback
        - Chord/AddressedChord: Block chord or arpeggiated playback
    dur : float, optional
        Duration in seconds. Defaults depend on object type:
        - PitchCollection/Scale: 0.5 seconds per note
        - Chord: 3.0 seconds total (or per note if arpeggiated)
    arp : bool, optional
        For chords only: if True, arpeggiate the chord (default False)
    prgm : int, optional
        MIDI program number (0-127) for instrument sound (default 0 = Acoustic Grand Piano)
    **kwargs
        Additional arguments passed to event creation functions
        
    Returns
    -------
    IPython.display.Audio
        Audio widget for playback in Jupyter notebooks
        
    Notes
    -----
    Requires pyfluidsynth and system FluidSynth libraries to be installed.
    """
    events, bpm, total_duration = _extract_events_from_object(obj, dur, arp, prgm)
    return _create_sequencer_audio(events, bpm, total_duration)

def _extract_events_from_object(obj, dur=None, arp=False, prgm=0):
    """Extract events from musical objects and return (events, bpm, total_duration)."""
    _reset_microtonal_counter()
    
    match obj:
        case TemporalUnitSequence() | TemporalBlock():
            return _extract_events_from_collection(obj)
        case CompositionalUnit():
            return _extract_events_from_compositional_unit(obj)
        case TemporalUnit():
            return _extract_events_from_temporal_unit(obj)
        case RhythmTree():
            temporal_unit = TemporalUnit.from_rt(obj)
            return _extract_events_from_temporal_unit(temporal_unit)
        case PitchCollection() | EquaveCyclicCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                return _extract_events_from_scale(obj, dur=dur or 0.3, prgm=prgm)
            elif isinstance(obj, (Chord, AddressedChord)):
                return _extract_events_from_chord(obj, dur=dur or 3.0, arp=arp, prgm=prgm)
            else:
                return _extract_events_from_pitch_collection(obj, dur=dur or 0.5, prgm=prgm)
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}. Supported types: RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, TemporalBlock, PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, AddressedScale, Chord, AddressedChord.")
    
def _create_sequencer_audio(events, bpm, total_duration):
    """Create audio using FluidSynth sequencer for precise timing."""
    if not HAS_FLUIDSYNTH:
        raise ImportError("pyfluidsynth is required for MIDI playback. Install with: pip install pyfluidsynth")
    
    events = _assign_channels_per_note(events)

    synth = fluidsynth.Synth(samplerate=44100)
    synth.start()
    
    soundfont_path = _ensure_soundfont()
    if soundfont_path and os.path.exists(soundfont_path):
        sfid = synth.sfload(soundfont_path)
    else:
        try:
            sfid = synth.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        except:
            try:
                sfid = synth.sfload("/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls")
            except:
                raise RuntimeError("No suitable soundfont found. Please install fluidsynth soundfonts.")
    
    note_events = [e for e in events if e[1] in ('note_on', 'note_off')]
    
    seq = fluidsynth.Sequencer(use_system_timer=False, time_scale=2000)
    synth_id = seq.register_fluidsynth(synth)
    
    current_time = seq.get_tick() + 1000
    
    for event in sorted(events, key=lambda x: x[0]):
        event_time, event_type = event[0], event[1]
        
        if event_type == 'note_on':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            tick_time = current_time + int(event_time * 2000)
            seq.note_on(time=tick_time, channel=channel, key=note, velocity=velocity, dest=synth_id, absolute=True)
        elif event_type == 'note_off':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            tick_time = current_time + int(event_time * 2000)
            seq.note_off(time=tick_time, channel=channel, key=note, dest=synth_id, absolute=True)
    
    synth.delete()
    seq.delete()
    
    synth = fluidsynth.Synth(samplerate=48000.0, gain=0.5)
    
    soundfont_path = _ensure_soundfont()
    if soundfont_path and os.path.exists(soundfont_path):
        sfid = synth.sfload(soundfont_path)
    else:
        try:
            sfid = synth.sfload("/usr/share/sounds/sf2/FluidR3_GM.sf2")
        except:
            try:
                sfid = synth.sfload("/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls")
            except:
                raise RuntimeError("No suitable soundfont found. Please install fluidsynth soundfonts.")
    
    _setup_programs_and_pitch_bends(events, synth, sfid)
    
    sample_rate = 48000
    samples = []
    
    all_events = sorted(events, key=lambda x: x[0])
    current_time = 0.0
    
    for event in all_events:
        event_time, event_type = event[0], event[1]
        
        if event_time > current_time:
            silence_duration = event_time - current_time
            silence_samples = int(silence_duration * sample_rate)
            samples.extend(synth.get_samples(silence_samples))
            current_time = event_time
        
        if event_type == 'note_on':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            synth.noteon(channel, note, velocity)
        elif event_type == 'note_off':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            synth.noteoff(channel, note)
        elif event_type == 'pitch_bend':
            channel, pitch_bend_value = event[2], event[3]
            synth.pitch_bend(channel, pitch_bend_value - 8192)
    
    remaining_duration = total_duration - current_time + 0.5
    if remaining_duration > 0:
        remaining_samples = int(remaining_duration * sample_rate)
        samples.extend(synth.get_samples(remaining_samples))
    
    synth.delete()
    
    audio_data = np.array(samples, dtype=np.int16)
    
    if len(audio_data) % 2 == 0:
        audio_data = audio_data[::2]
    
    audio_array = audio_data.astype(np.float32) / 32767.0
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
    
    max_val = np.max(np.abs(audio_array))
    if max_val > 0:
        audio_array = audio_array / max_val * 0.8
    
    try:
        import soundfile as sf
        sf.write(temp_path, audio_array, sample_rate)
    except ImportError:
        import wave
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            audio_16bit = (audio_array * 32767).astype(np.int16)
            wav_file.writeframes(audio_16bit.tobytes())
    
    return Audio(temp_path, rate=sample_rate, autoplay=False)

def _assign_channels_per_note(events):
    """Assign each pitched note its own channel with wrap-around, reserving percussion channel."""
    allowed_channels = list(range(0, 9)) + list(range(10, 256))
    channel_index = 0
    new_events = []
    active_notes = {}

    by_time = {}
    for e in events:
        by_time.setdefault(e[0], []).append(e)

    prepared = {}

    for t in sorted(by_time.keys()):
        group = by_time[t]
        prepared.clear()
        for e in group:
            et = e[1]
            if et == 'note_on':
                ch, note, vel, prg = e[2], e[3], e[4], e[5]
                if ch == PERCUSSION_CHANNEL:
                    key = ('prepared_perc', note, prg)
                    prepared.setdefault(key, []).append(PERCUSSION_CHANNEL)
                else:
                    key = (note, prg)
                    chn = allowed_channels[channel_index % len(allowed_channels)]
                    channel_index += 1
                    prepared.setdefault(key, []).append(chn)

        for e in group:
            et = e[1]
            if et == 'pitch_bend':
                ch, val = e[2], e[3]
                midi_note = e[4] if len(e) > 4 else None
                program = e[5] if len(e) > 5 else None
                if midi_note is not None and program is not None:
                    key = (midi_note, program)
                    if key in prepared and prepared[key]:
                        chn = prepared[key][0]
                        new_events.append((t, 'pitch_bend', chn, val))
                        continue
                new_events.append(e)
            elif et == 'note_on':
                ch, note, vel, prg = e[2], e[3], e[4], e[5]
                if ch == PERCUSSION_CHANNEL:
                    new_events.append(e)
                else:
                    key = (note, prg)
                    chn = prepared[key].pop(0)
                    new_events.append((t, 'note_on', chn, note, vel, prg))
                    active_key = (note, prg)
                    active_notes.setdefault(active_key, []).append(chn)
            elif et == 'note_off':
                ch, note, vel, prg = e[2], e[3], e[4], e[5]
                if ch == PERCUSSION_CHANNEL:
                    new_events.append(e)
                else:
                    active_key = (note, prg)
                    if active_key in active_notes and active_notes[active_key]:
                        chn = active_notes[active_key].pop(0)
                        new_events.append((t, 'note_off', chn, note, vel, prg))
                    else:
                        new_events.append(e)
            else:
                new_events.append(e)

    return sorted(new_events, key=lambda x: x[0])

def _setup_programs_and_pitch_bends(events, synth, sfid):
    """Set up program changes and pitch bends on the synthesizer before scheduling."""
    channel_programs = {}
    channel_pitch_bends = {}
    
    # Explicitly set up percussion channel as drum kit
    synth.program_select(PERCUSSION_CHANNEL, sfid, 128, 0)  # Bank 128 = drums
    
    for event in events:
        event_type = event[1]
        
        if event_type == 'pitch_bend':
            channel, pitch_bend_value = event[2], event[3]
            if channel not in channel_pitch_bends or channel_pitch_bends[channel] != pitch_bend_value:
                synth.pitch_bend(channel, pitch_bend_value - 8192)
                channel_pitch_bends[channel] = pitch_bend_value
        elif event_type == 'note_on':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            if channel != PERCUSSION_CHANNEL and (channel not in channel_programs or channel_programs[channel] != program):
                synth.program_select(channel, sfid, 0, program)
                channel_programs[channel] = program

def _schedule_events_with_sequencer(events, seq, synth_id, bpm):
    """Schedule note events using FluidSynth sequencer."""
    events.sort(key=lambda x: x[0])
    
    for event in events:
        event_time, event_type = event[0], event[1]
        tick_time = int(event_time * 2000)
        
        if event_type == 'note_on':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            seq.note_on(time=tick_time, channel=channel, key=note, velocity=velocity, dest=synth_id, absolute=True)
        elif event_type == 'note_off':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            seq.note_off(time=tick_time, channel=channel, key=note, dest=synth_id, absolute=True)

def _extract_events_from_temporal_unit(temporal_unit):
    """Extract events from a TemporalUnit."""
    bpm = temporal_unit._bpm
    
    events = []
    for chronon in temporal_unit:
        if not chronon.is_rest:
            start_time = chronon.start
            duration = abs(chronon.duration)
            events.append((start_time, 'note_on', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, DEFAULT_VELOCITY, 0))
            events.append((start_time + duration, 'note_off', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, 0, 0))
    
    return events, bpm, temporal_unit.duration

def _extract_events_from_compositional_unit(compositional_unit):
    """Extract events from a CompositionalUnit with parameter fields."""
    bpm = compositional_unit._bpm
    
    events = []
    for event in compositional_unit:
        if not event.is_rest:
            instrument = event._pt.get_active_instrument(event._node_id)
            
            if isinstance(instrument, MidiInstrument):
                is_drum = instrument.is_Drum
                program = 0 if is_drum else instrument.prgm
                note_param = event.get_parameter('note', instrument['note'])
                velocity = event.get_parameter('velocity', instrument['velocity'])
            else:
                is_drum = event.get_parameter('is_drum', False)
                program = 0 if is_drum else event.get_parameter('program', 0)
                note_param = event.get_parameter('note', DEFAULT_DRUM_NOTE if is_drum else 60)
                velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
            
            start_time = event.start
            duration = abs(event.duration)
            
            if is_drum:
                channel = PERCUSSION_CHANNEL
                midi_note = int(note_param) if note_param else DEFAULT_DRUM_NOTE
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            elif isinstance(note_param, Pitch):
                channel, midi_note, pitch_bend = _get_exact_microtonal_channel(note_param)
                if pitch_bend != 8192:
                    events.append((start_time, 'pitch_bend', channel, pitch_bend, midi_note, program))
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            elif isinstance(note_param, float) and note_param != int(note_param):
                pitch = Pitch.from_midi(note_param)
                channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
                if pitch_bend != 8192:
                    events.append((start_time, 'pitch_bend', channel, pitch_bend, midi_note, program))
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            else:
                channel = 0
                midi_note = int(note_param) if note_param else 60
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
    
    return events, bpm, compositional_unit.duration

def _extract_events_from_collection(collection):
    """Extract events from a TemporalUnitSequence or TemporalBlock using recursive traversal."""
    if len(collection) > 0:
        first_unit = collection[0]
        while hasattr(first_unit, '__iter__') and not isinstance(first_unit, (TemporalUnit, CompositionalUnit)):
            first_unit = first_unit[0]
        bpm = first_unit._bpm
    else:
        bpm = 120
    
    all_events = _extract_all_events_recursively(collection)
    all_events.sort(key=lambda x: x[0])
    
    if isinstance(collection, TemporalUnitSequence):
        total_duration = collection.duration
    else:
        total_duration = max((event[0] + (event[0] if len(event) > 6 else 1.0) for event in all_events), default=3.0)
    
    return all_events, bpm, total_duration

def _extract_all_events_recursively(structure):
    """Recursively extract all events from deeply nested temporal structures."""
    all_events = []
    
    if isinstance(structure, (TemporalUnit, CompositionalUnit)):
        if isinstance(structure, CompositionalUnit):
            events, _, _ = _extract_events_from_compositional_unit(structure)
        else:
            events, _, _ = _extract_events_from_temporal_unit(structure)
        all_events.extend(events)
    elif isinstance(structure, TemporalUnitSequence):
        for unit in structure:
            all_events.extend(_extract_all_events_recursively(unit))
    elif isinstance(structure, TemporalBlock):
        for row in structure:
            all_events.extend(_extract_all_events_recursively(row))
    elif hasattr(structure, '__iter__'):
        for item in structure:
            all_events.extend(_extract_all_events_recursively(item))
    
    return all_events



def _get_exact_microtonal_channel(pitch):
    """
    Assign unique microtonal pitches to dedicated channels with precise pitch bend.
    
    Each unique microtonal pitch gets its own channel for precise tuning.
    Channels 0-8, 10-255 are available (skip 9 for percussion).
    255 channels total eliminates pitch bend conflicts during overlapping microtonal notes.
    
    Returns:
        tuple: (channel, midi_note, pitch_bend_value)
    """
    target_midi = pitch.midi
    
    # For standard 12-TET notes (no decimal part), always use channel 0
    if abs(target_midi - round(target_midi)) < 0.001:
        return 0, int(round(target_midi)), 8192
    
    # For microtonal notes, calculate exact pitch bend
    nearest_midi = round(target_midi)
    cents_offset = (target_midi - nearest_midi) * 100.0
    
    # Convert cents to pitch bend value (±200 cents = ±4096 pitch bend units)
    pitch_bend_value = int(8192 + (cents_offset / 200.0) * 4096)
    pitch_bend_value = max(0, min(16383, pitch_bend_value))
    
    # Create lookup table for unique pitches to dedicated channels
    if not hasattr(_get_exact_microtonal_channel, '_pitch_to_channel'):
        _get_exact_microtonal_channel._pitch_to_channel = {}
        _get_exact_microtonal_channel._channel_counter = 1  # Start at 1 (0 is for 12-TET)
    
    # Use frequency as key for exact matching
    pitch_key = round(target_midi, 6)
    
    if pitch_key not in _get_exact_microtonal_channel._pitch_to_channel:
        # Available channels: 1-8, 10-255 (skip 9 for percussion)
        available_channels = list(range(1, 9)) + list(range(10, 256))  # 254 channels total
        
        # Assign next available channel and increment counter
        channel_index = (_get_exact_microtonal_channel._channel_counter - 1) % len(available_channels)
        channel = available_channels[channel_index]
        _get_exact_microtonal_channel._pitch_to_channel[pitch_key] = channel
        _get_exact_microtonal_channel._channel_counter += 1
    
    channel = _get_exact_microtonal_channel._pitch_to_channel[pitch_key]
    return channel, nearest_midi, pitch_bend_value

def _reset_microtonal_counter():
    """Reset the global channel counter and pitch mapping for new sequences."""
    if hasattr(_get_exact_microtonal_channel, '_pitch_to_channel'):
        _get_exact_microtonal_channel._pitch_to_channel = {}
        _get_exact_microtonal_channel._channel_counter = 1



def _extract_events_from_pitch_collection(collection, dur=0.5, bpm=120, prgm=0):
    """Extract events from a PitchCollection (sequential playback)."""
    if isinstance(collection, AddressedPitchCollection):
        addressed = collection
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = collection.root(Pitch("C4"))
    
    events = []
    current_time = 0.0
    
    for i in range(len(addressed)):
        pitch = addressed[i]
        
        channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
        
        if pitch_bend != 8192:
            events.append((current_time, 'pitch_bend', channel, pitch_bend, midi_note, prgm))
        
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    return events, bpm, current_time

def _extract_events_from_scale(scale, dur=0.5, bpm=120, prgm=0):
    """Extract events from a Scale (ascending then descending)."""
    if isinstance(scale, AddressedPitchCollection):
        addressed = scale
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = scale.root(Pitch("C4"))
    
    events = []
    current_time = 0.0
    
    # Play ascending (including the equave at index len(addressed))
    for i in range(len(addressed) + 1):
        pitch = addressed[i]
        
        channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
        
        if pitch_bend != 8192:
            events.append((current_time, 'pitch_bend', channel, pitch_bend, midi_note, prgm))
        
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    # Play descending (skip the equave to avoid repetition, stop at index 0)
    for i in range(len(addressed) - 1, -1, -1):
        pitch = addressed[i]
        
        channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
        
        if pitch_bend != 8192:
            events.append((current_time, 'pitch_bend', channel, pitch_bend))
        
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    return events, bpm, current_time

def _extract_events_from_chord(chord, dur=3.0, arp=False, bpm=120, prgm=0):
    """Extract events from a Chord (block chord or arpeggiated)."""
    if isinstance(chord, AddressedPitchCollection):
        addressed = chord
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = chord.root(Pitch("C4"))
    
    events = []
    
    if arp:
        # Arpeggiated: each note gets dur duration
        current_time = 0.0
        for i in range(len(addressed)):
            pitch = addressed[i]
            
            channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
            
            if pitch_bend != 8192:
                events.append((current_time, 'pitch_bend', channel, pitch_bend, midi_note, prgm))
            
            events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
            events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
            
            current_time += dur
        total_duration = current_time
    else:
        # Block chord: all notes start at once, last for dur
        for i in range(len(addressed)):
            pitch = addressed[i]
            
            channel, midi_note, pitch_bend = _get_exact_microtonal_channel(pitch)
            
            if pitch_bend != 8192:
                events.append((0.0, 'pitch_bend', channel, pitch_bend, midi_note, prgm))
            
            events.append((0.0, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
            events.append((dur, 'note_off', channel, midi_note, 0, prgm))
        total_duration = dur
    
    return events, bpm, total_duration

