from mido import Message, MidiFile, MidiTrack, MetaMessage
from IPython.display import Audio
import os
import tempfile
import urllib.request
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO

# Optional imports for different environments
try:
    from midi2audio import FluidSynth
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
TICKS_PER_BEAT = 480

# Exact Microtonal Configuration
# Each unique microtonal pitch gets its own dedicated channel with precise pitch bend
# Channels 0-8, 10-15 are available for pitched instruments (channel 9 reserved for percussion)
# When we run out of channels, we wrap around and reuse channels
# This ensures EXACT microtonal tuning with no approximation errors

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
    Play a musical object as MIDI audio in Jupyter/Colab notebooks.
    
    Automatically detects the environment and uses appropriate MIDI synthesis:
    - Google Colab: Uses timidity (install with: !apt install timidity fluid-soundfont-gm)
    - Local Jupyter: Uses FluidSynth if available
    - Fallback: Returns MIDI file for download
    
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
        Additional arguments passed to MIDI creation functions
        
    Returns
    -------
    IPython.display.Audio or IPython.display.FileLink
        Audio widget for playback in Jupyter notebooks, or file link 
        if audio synthesis is unavailable
        
    Notes
    -----
    For Google Colab, run this first in a cell:
    !apt install timidity fluid-soundfont-gm
    """
    match obj:
        case TemporalUnitSequence() | TemporalBlock():
            midi_file = _create_midi_from_collection(obj)
        case CompositionalUnit():
            midi_file = _create_midi_from_compositional_unit(obj)
        case TemporalUnit():
            midi_file = _create_midi_from_temporal_unit(obj)
        case RhythmTree():
            temporal_unit = TemporalUnit.from_rt(obj)
            midi_file = _create_midi_from_temporal_unit(temporal_unit)
        case PitchCollection() | EquaveCyclicCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                midi_file = _create_midi_from_scale(obj, dur=dur or 0.5, prgm=prgm)
            elif isinstance(obj, (Chord, AddressedChord)):
                midi_file = _create_midi_from_chord(obj, dur=dur or 3.0, arp=arp, prgm=prgm)
            else:
                midi_file = _create_midi_from_pitch_collection(obj, dur=dur or 0.5, prgm=prgm)
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}. Supported types: RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, TemporalBlock, PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, AddressedScale, Chord, AddressedChord.")
    
    return _midi_to_audio(midi_file)

def _create_midi_from_temporal_unit(temporal_unit):
    """Create a MIDI file from a TemporalUnit."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    # Use the TemporalUnit's own BPM
    bpm = temporal_unit._bpm
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    events = []
    for chronon in temporal_unit:
        if not chronon.is_rest:
            # Use chronon's actual time values directly (already in seconds)
            start_time = chronon.start
            duration = abs(chronon.duration)
            events.append((start_time, 'note_on'))
            events.append((start_time + duration, 'note_off'))
    
    event_priority = {"note_on": 0, "note_off": 1}
    events.sort(key=lambda x: (x[0], event_priority.get(x[1], 2)))
    
    current_time = 0.0
    for event_time, event_type in events:
        delta_time = event_time - current_time
        # Convert from seconds to MIDI ticks using the beat duration
        beat_duration = 60.0 / bpm  # duration of one beat in seconds
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        if event_type == 'note_on':
            track.append(Message('note_on', 
                               channel=PERCUSSION_CHANNEL, 
                               note=DEFAULT_DRUM_NOTE, 
                               velocity=DEFAULT_VELOCITY, 
                               time=delta_ticks))
        else:
            track.append(Message('note_off', 
                               channel=PERCUSSION_CHANNEL, 
                               note=DEFAULT_DRUM_NOTE, 
                               velocity=0, 
                               time=delta_ticks))
        
        current_time = event_time
    
    # Ensure MIDI file duration matches the TemporalUnit's total duration
    # This handles trailing rests that would otherwise be cut off
    _ensure_midi_duration(track, temporal_unit.duration, bpm)
    
    return midi_file

def _create_midi_from_compositional_unit(compositional_unit):
    """Create a MIDI file from a CompositionalUnit with parameter fields."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    # Use the CompositionalUnit's own BPM
    bpm = compositional_unit._bpm
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    # Reset microtonal channel counter for this new file
    _reset_microtonal_counter()
    
    events = []
    for event in compositional_unit:
        if not event.is_rest:
            # Get instrument information from the parameter tree
            instrument = event._pt.get_active_instrument(event._node_id)
            
            if isinstance(instrument, MidiInstrument):
                is_drum = instrument.is_Drum
                program = 0 if is_drum else instrument.prgm
                note_param = event.get_parameter('note', instrument['note'])
                velocity = event.get_parameter('velocity', instrument['velocity'])
            else:
                # Fallback for non-MidiInstrument cases
                is_drum = event.get_parameter('is_drum', False)
                program = 0 if is_drum else event.get_parameter('program', 0)
                note_param = event.get_parameter('note', DEFAULT_DRUM_NOTE if is_drum else 60)
                velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
            
            start_time = event.start
            duration = abs(event.duration)
            
            # Handle microtonal MIDI float values directly like pitch collections do
            if is_drum:
                # Drums always go to percussion channel
                channel = PERCUSSION_CHANNEL
                midi_note = int(note_param) if note_param else DEFAULT_DRUM_NOTE
                # Add note events - no pitch bend for drums
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            elif isinstance(note_param, Pitch):
                # Use the same logic as pitch collections
                channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(note_param)
                events.append((start_time, 'pitch_bend', channel, pitch_bend))
                # Add note events
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            elif isinstance(note_param, float) and note_param != int(note_param):
                # Microtonal MIDI float - convert to Pitch and use same logic
                pitch = Pitch.from_midi(note_param)
                channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
                events.append((start_time, 'pitch_bend', channel, pitch_bend))
                # Add note events
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
            else:
                # Simple integer MIDI note - use channel 0
                channel = 0
                midi_note = int(note_param) if note_param else 60
                # Add note events
                events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
    
    # Use the exact same event processing as pitch collections
    _events_to_midi_messages(events, track, bpm)
    
    # Ensure MIDI file duration matches the CompositionalUnit's total duration
    # This handles trailing rests that would otherwise be cut off
    _ensure_midi_duration(track, compositional_unit.duration, bpm)
    
    return midi_file

def _create_midi_from_collection(collection):
    """Create a MIDI file from a TemporalUnitSequence or TemporalBlock."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    # Use first unit's BPM as default, or 120 if no units
    if len(collection) > 0:
        first_unit = collection[0]
        # Handle nested structures - get the first actual temporal unit
        while hasattr(first_unit, '__iter__') and not isinstance(first_unit, (TemporalUnit, CompositionalUnit)):
            first_unit = first_unit[0]
        bpm = first_unit._bpm
    else:
        bpm = 120
    
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    # Reset microtonal channel counter for this new file
    _reset_microtonal_counter()
    
    # Collect all events from all units in the collection
    all_events = []
    
    # For TemporalUnitSequence: units are sequential
    # For TemporalBlock: units are parallel (multiple rows)
    if isinstance(collection, TemporalUnitSequence):
        # Sequential units - each unit has its own offset already built in
        for unit in collection:
            _collect_events_from_unit_with_offset(unit, all_events, 0.0)
    elif isinstance(collection, TemporalBlock):
        # Parallel units - all rows start at the same time (time 0)
        for row in collection:
            if isinstance(row, (TemporalUnit, CompositionalUnit)):
                _collect_events_from_unit_with_offset(row, all_events, 0.0)
            elif isinstance(row, TemporalUnitSequence):
                # TemporalBlock can contain TemporalUnitSequences
                for unit in row:
                    _collect_events_from_unit_with_offset(unit, all_events, 0.0)
            # Could also contain nested TemporalBlocks, but keep it simple for now
    
    # Sort all events by time
    event_priority = {"pitch_bend": 0, "note_on": 1, "note_off": 2}
    all_events.sort(key=lambda x: (x[0], event_priority.get(x[1], 3)))
    
    # Track program changes per channel
    current_programs = {}
    current_time = 0.0
    
    # Generate MIDI messages
    for event_data in all_events:
        event_time, event_type = event_data[0], event_data[1]
        
        delta_time = event_time - current_time
        beat_duration = 60.0 / bpm
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        if event_type == 'pitch_bend':
            channel, pitch_bend_value = event_data[2], event_data[3]
            # MIDI pitchwheel expects values in range -8192 to 8191, not 0 to 16383
            pitch_value = pitch_bend_value - 8192
            track.append(Message('pitchwheel', channel=channel, pitch=pitch_value, time=delta_ticks))
        elif event_type in ('note_on', 'note_off'):
            channel, note, velocity, program = event_data[2], event_data[3], event_data[4], event_data[5]
            
            # Add program change if needed (not for drum channel)
            if event_type == 'note_on' and channel != PERCUSSION_CHANNEL and current_programs.get(channel) != program:
                track.append(Message('program_change', 
                                   channel=channel, 
                                   program=program, 
                                   time=delta_ticks))
                current_programs[channel] = program
                delta_ticks = 0  # Reset delta_ticks since we used it for program change
            
            if event_type == 'note_on':
                track.append(Message('note_on', 
                                   channel=channel, 
                                   note=note, 
                                   velocity=velocity, 
                                   time=delta_ticks))
            else:
                track.append(Message('note_off', 
                                   channel=channel, 
                                   note=note, 
                                   velocity=0, 
                                   time=delta_ticks))
        
        current_time = event_time
    
    # Ensure MIDI file duration matches the collection's total duration
    # This handles trailing rests that would otherwise be cut off
    if isinstance(collection, TemporalUnitSequence):
        total_duration = collection.duration
        _ensure_midi_duration(track, total_duration, bpm)
    
    return midi_file

def _collect_events_from_unit_with_offset(unit, all_events, time_offset=0.0):
    """Helper function to collect events from a single temporal unit with time offset."""
    # Create a temporary copy to avoid modifying the original unit's state
    unit_copy = unit.copy()
    
    if isinstance(unit_copy, CompositionalUnit):
        # CompositionalUnit with parameters
        for event in unit_copy:
            if not event.is_rest:
                # Get instrument information from the parameter tree
                instrument = event._pt.get_active_instrument(event._node_id)
                
                if isinstance(instrument, MidiInstrument):
                    is_drum = instrument.is_Drum
                    program = 0 if is_drum else instrument.prgm
                    note_param = event.get_parameter('note', instrument['note'])
                    velocity = event.get_parameter('velocity', instrument['velocity'])
                else:
                    # Fallback for non-MidiInstrument cases
                    is_drum = event.get_parameter('is_drum', False)
                    program = 0 if is_drum else event.get_parameter('program', 0)
                    note_param = event.get_parameter('note', DEFAULT_DRUM_NOTE if is_drum else 60)
                    velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
                
                start_time = event.start + time_offset
                duration = abs(event.duration)
                
                # Handle microtonal MIDI float values directly like CompositionalUnit
                if is_drum:
                    # Drums always go to percussion channel
                    channel = PERCUSSION_CHANNEL
                    midi_note = int(note_param) if note_param else DEFAULT_DRUM_NOTE
                    # Add note events - no pitch bend for drums
                    all_events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                    all_events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
                elif isinstance(note_param, Pitch):
                    # Use the same logic as pitch collections
                    channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(note_param)
                    all_events.append((start_time, 'pitch_bend', channel, pitch_bend))
                    # Add note events
                    all_events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                    all_events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
                elif isinstance(note_param, float) and note_param != int(note_param):
                    # Microtonal MIDI float - convert to Pitch and use same logic
                    pitch = Pitch.from_midi(note_param)
                    channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
                    all_events.append((start_time, 'pitch_bend', channel, pitch_bend))
                    # Add note events
                    all_events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                    all_events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
                else:
                    # Simple integer MIDI note - use channel 0
                    channel = 0
                    midi_note = int(note_param) if note_param else 60
                    # Add note events
                    all_events.append((start_time, 'note_on', channel, midi_note, velocity, program))
                    all_events.append((start_time + duration, 'note_off', channel, midi_note, 0, program))
    else:
        # Regular TemporalUnit - use defaults
        for chronon in unit_copy:
            if not chronon.is_rest:
                start_time = chronon.start + time_offset
                duration = abs(chronon.duration)
                
                all_events.append((start_time, 'note_on', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, DEFAULT_VELOCITY, 0))
                all_events.append((start_time + duration, 'note_off', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, 0, 0))

def _midi_to_audio(midi_file):
    """Convert MIDI file to audio for playback."""
    with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as midi_temp:
        midi_file.save(midi_temp.name)
        midi_path = midi_temp.name
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as audio_temp:
        audio_path = audio_temp.name
    
    try:
        # Always try Colab method first if we're in Colab
        if _is_colab():
            # print("Detected Google Colab environment, using timidity...")
            return _midi_to_audio_colab(midi_path, audio_path)
        
        # Try FluidSynth for local environments
        if HAS_FLUIDSYNTH:
            # print("Using FluidSynth for MIDI synthesis...")
            try:
                return _midi_to_audio_fluidsynth(midi_path, audio_path)
            except Exception as e:
                print(f"FluidSynth failed ({e}), trying fallback...")
                return _midi_to_audio_fallback(midi_path)
        else:
            print("No MIDI synthesis available, using fallback...")
            return _midi_to_audio_fallback(midi_path)
        
    finally:
        try:
            os.unlink(midi_path)
            if os.path.exists(audio_path):
                os.unlink(audio_path)
        except OSError:
            pass

def _midi_to_audio_colab(midi_path, audio_path):
    """Convert MIDI to audio in Google Colab using timidity."""
    try:
        # Use timidity to convert MIDI to WAV
        subprocess.run([
            'timidity', midi_path, 
            '-Ow', '-o', audio_path,
            # '--preserve-silence',  # Prevent dropping initial/trailing rests
            '--quiet'
        ], check=True, capture_output=True)
        
        audio_widget = Audio(audio_path, autoplay=False)
        return audio_widget
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # If --preserve-silence option failed, try without it
        try:
            print("--preserve-silence option not supported, trying without it...")
            subprocess.run([
                'timidity', midi_path, 
                '-Ow', '-o', audio_path,
                '--quiet'
            ], check=True, capture_output=True)
            
            audio_widget = Audio(audio_path, autoplay=False)
            return audio_widget
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e2:
            print("Timidity not found. Install it first with: !apt install timidity fluid-soundfont-gm")
            return _midi_to_audio_fallback(midi_path)

def _midi_to_audio_fluidsynth(midi_path, audio_path):
    """Convert MIDI to audio using FluidSynth (original method)."""
    soundfont = _ensure_soundfont()
    
    # Create FluidSynth instance
    if soundfont and os.path.exists(soundfont):
        fs = FluidSynth(sound_font=soundfont)
    else:
        fs = FluidSynth()
    
    # Suppress output by redirecting to devnull at subprocess level
    with open(os.devnull, 'w') as devnull:
        old_stdout = os.dup(1)
        old_stderr = os.dup(2)
        os.dup2(devnull.fileno(), 1)
        os.dup2(devnull.fileno(), 2)
        
        try:
            fs.midi_to_audio(midi_path, audio_path)
        finally:
            os.dup2(old_stdout, 1)
            os.dup2(old_stderr, 2)
            os.close(old_stdout)
            os.close(old_stderr)
    
    audio_widget = Audio(audio_path, autoplay=False)
    return audio_widget

def _midi_to_audio_fallback(midi_path):
    """Fallback method that returns the MIDI file directly."""
    print("Audio synthesis not available. Returning MIDI file for download.")
    print(f"MIDI file available at: {midi_path}")
    
    # Return an Audio widget that points to the MIDI file
    # This won't play in most browsers, but at least won't crash
    try:
        # Try to return as a download link if possible
        from IPython.display import FileLink
        return FileLink(midi_path)
    except ImportError:
        # Fallback to basic Audio widget
        return Audio(midi_path, autoplay=False)

def _get_microtonal_channel_and_note(pitch, channel_assignments=None):
    """
    Assign exact microtonal pitches to dedicated channels with precise pitch bend.
    
    Each unique microtonal pitch gets its own channel for precise tuning.
    Channels 0-8, 10-15 are available (skip 9 for percussion).
    
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
    
    # Global counter for channel assignment
    if not hasattr(_get_microtonal_channel_and_note, '_channel_counter'):
        _get_microtonal_channel_and_note._channel_counter = 1  # Start at 1 (0 is for 12-TET)
    
    # Available channels: 1-8, 10-15 (skip 9 for percussion)
    available_channels = list(range(1, 9)) + list(range(10, 16))  # 14 channels total
    
    # Assign next available channel and increment counter
    channel_index = (_get_microtonal_channel_and_note._channel_counter - 1) % len(available_channels)
    channel = available_channels[channel_index]
    _get_microtonal_channel_and_note._channel_counter += 1
    
    return channel, nearest_midi, pitch_bend_value

def _reset_microtonal_counter():
    """Reset the global channel counter for new MIDI files."""
    if hasattr(_get_microtonal_channel_and_note, '_channel_counter'):
        _get_microtonal_channel_and_note._channel_counter = 1

def _ensure_midi_duration(track, target_duration_seconds, bpm):
    """
    Ensure MIDI track duration matches target duration by adding silent padding if needed.
    
    This handles cases where the temporal structure ends with rests, ensuring
    the MIDI file doesn't cut off prematurely and allows reverb/sustain to play out.
    
    Parameters
    ----------
    track : MidiTrack
        The MIDI track to extend
    target_duration_seconds : float
        The target duration in seconds
    bpm : float
        Beats per minute for timing calculations
    """
    if not track:
        return
    
    # Calculate current track duration
    current_time_ticks = 0
    for msg in track:
        current_time_ticks += msg.time
    
    # Convert to seconds
    beat_duration = 60.0 / bpm
    current_duration_seconds = current_time_ticks * beat_duration / TICKS_PER_BEAT
    
    # If we need more duration, add a silent padding message
    if target_duration_seconds > current_duration_seconds:
        missing_duration = target_duration_seconds - current_duration_seconds
        missing_ticks = int(missing_duration / beat_duration * TICKS_PER_BEAT)
        
        # Add a silent message (could be a control change or just a dummy note off)
        # Using a note off with velocity 0 on a silent channel as padding
        from mido import Message
        track.append(Message('note_off', 
                           channel=15,  # Use channel 15 for silent padding
                           note=127,    # High note that won't interfere
                           velocity=0, 
                           time=missing_ticks))

def _create_midi_from_pitch_collection(collection, dur=0.5, bpm=120, prgm=0):
    """Create a MIDI file from a PitchCollection (sequential playback)."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    # Reset microtonal channel counter for this new file
    _reset_microtonal_counter()
    
    # For non-addressed collections, create addressed version with C4 root
    if isinstance(collection, AddressedPitchCollection):
        addressed = collection
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = collection.root(Pitch("C4"))
    
    events = []
    current_time = 0.0
    
    for i in range(len(addressed)):
        pitch = addressed[i]
        
        # Get the best 144-TET channel and note approximation
        channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
        
        events.append((current_time, 'pitch_bend', channel, pitch_bend))
        
        # Add note events
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    # Convert events to MIDI messages
    _events_to_midi_messages(events, track, bpm)
    
    return midi_file

def _create_midi_from_scale(scale, dur=0.5, bpm=120, prgm=0):
    """Create a MIDI file from a Scale (ascending then descending)."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    # Reset microtonal channel counter for this new file
    _reset_microtonal_counter()
    
    # For non-addressed scales, create addressed version with C4 root
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
        
        # Get the best 144-TET channel and note approximation
        channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
        
        events.append((current_time, 'pitch_bend', channel, pitch_bend))
        
        # Add note events
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    # Play descending (skip the equave to avoid repetition, stop at index 0)
    for i in range(len(addressed) - 1, -1, -1):
        pitch = addressed[i]
        
        # Get the best 144-TET channel and note approximation
        channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
        
        events.append((current_time, 'pitch_bend', channel, pitch_bend))
        
        # Add note events
        events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
        events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
        
        current_time += dur
    
    # Convert events to MIDI messages
    _events_to_midi_messages(events, track, bpm)
    
    return midi_file

def _create_midi_from_chord(chord, dur=3.0, arp=False, bpm=120, prgm=0):
    """Create a MIDI file from a Chord (block chord or arpeggiated)."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    # Reset microtonal channel counter for this new file
    _reset_microtonal_counter()
    
    # For non-addressed chords, create addressed version with C4 root
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
            
            # Get the best 144-TET channel and note approximation
            channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
            
            events.append((current_time, 'pitch_bend', channel, pitch_bend))
            
            # Add note events
            events.append((current_time, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
            events.append((current_time + dur, 'note_off', channel, midi_note, 0, prgm))
            
            current_time += dur
    else:
        # Block chord: all notes start at once, last for dur
        for i in range(len(addressed)):
            pitch = addressed[i]
            
            # Get the best 144-TET channel and note approximation
            channel, midi_note, pitch_bend = _get_microtonal_channel_and_note(pitch)
            
            events.append((0.0, 'pitch_bend', channel, pitch_bend))
            
            # Add note events
            events.append((0.0, 'note_on', channel, midi_note, DEFAULT_VELOCITY, prgm))
            events.append((dur, 'note_off', channel, midi_note, 0, prgm))
    
    # Convert events to MIDI messages
    _events_to_midi_messages(events, track, bpm)
    
    return midi_file

def _events_to_midi_messages(events, track, bpm):
    """Convert time-based events to MIDI messages with proper timing."""
    # Sort by time, then by event type priority (pitch_bend before note_on/note_off)
    event_priority = {"pitch_bend": 0, "note_on": 1, "note_off": 2}
    events.sort(key=lambda x: (x[0], event_priority.get(x[1], 3)))
    
    current_time = 0.0
    beat_duration = 60.0 / bpm
    
    # Track program changes per channel
    current_programs = {}
    
    for event in events:
        event_time, event_type = event[0], event[1]
        
        delta_time = event_time - current_time
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        if event_type == 'pitch_bend':
            channel, pitch_bend_value = event[2], event[3]
            # MIDI pitchwheel expects values in range -8192 to 8191, not 0 to 16383
            pitch_value = pitch_bend_value - 8192
            track.append(Message('pitchwheel', channel=channel, pitch=pitch_value, time=delta_ticks))
        elif event_type == 'note_on':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            
            # Add program change if needed (channels 0-11 are for pitched instruments)
            # Note: We use channels 0-11 for the 144-TET grid, all pitched instruments
            if current_programs.get(channel) != program:
                track.append(Message('program_change', 
                                   channel=channel, 
                                   program=program, 
                                   time=delta_ticks))
                current_programs[channel] = program
                delta_ticks = 0  # Reset delta_ticks since we used it for program change
            
            track.append(Message('note_on', channel=channel, note=note, velocity=velocity, time=delta_ticks))
        elif event_type == 'note_off':
            channel, note, velocity, program = event[2], event[3], event[4], event[5]
            track.append(Message('note_off', channel=channel, note=note, velocity=velocity, time=delta_ticks))
        
        current_time = event_time