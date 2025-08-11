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

BASS_DRUM_NOTE = 35
PERCUSSION_CHANNEL = 9
DEFAULT_VELOCITY = 100
TICKS_PER_BEAT = 480

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



def play_midi(obj, **kwargs):
    """
    Play a musical object as MIDI audio in Jupyter/Colab notebooks.
    
    Automatically detects the environment and uses appropriate MIDI synthesis:
    - Google Colab: Uses timidity (install with: !apt install timidity fluid-soundfont-gm)
    - Local Jupyter: Uses FluidSynth if available
    - Fallback: Returns MIDI file for download
    
    Parameters
    ----------
    obj : RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, or TemporalBlock
        The musical object to play. If RhythmTree, it will be converted 
        to TemporalUnit with default timing.
    **kwargs
        Additional arguments (currently unused)
        
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
    if isinstance(obj, (TemporalUnitSequence, TemporalBlock)):
        midi_file = _create_midi_from_collection(obj)
    elif isinstance(obj, CompositionalUnit):
        midi_file = _create_midi_from_compositional_unit(obj)
    elif isinstance(obj, TemporalUnit):
        midi_file = _create_midi_from_temporal_unit(obj)
    elif isinstance(obj, RhythmTree):
        temporal_unit = TemporalUnit.from_rt(obj)
        midi_file = _create_midi_from_temporal_unit(temporal_unit)
    else:
        raise TypeError(f"Unsupported object type: {type(obj)}. Only RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, and TemporalBlock are supported.")
    
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
    
    events.sort(key=lambda x: x[0])
    
    current_time = 0.0
    for event_time, event_type in events:
        delta_time = event_time - current_time
        # Convert from seconds to MIDI ticks using the beat duration
        beat_duration = 60.0 / bpm  # duration of one beat in seconds
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        if event_type == 'note_on':
            track.append(Message('note_on', 
                               channel=PERCUSSION_CHANNEL, 
                               note=60, 
                               velocity=DEFAULT_VELOCITY, 
                               time=delta_ticks))
        else:
            track.append(Message('note_off', 
                               channel=PERCUSSION_CHANNEL, 
                               note=60, 
                               velocity=0, 
                               time=delta_ticks))
        
        current_time = event_time
    
    return midi_file

def _create_midi_from_compositional_unit(compositional_unit):
    """Create a MIDI file from a CompositionalUnit with parameter fields."""
    midi_file = MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = MidiTrack()
    midi_file.tracks.append(track)
    
    # Use the CompositionalUnit's own BPM
    bpm = compositional_unit._bpm
    track.append(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm)))
    
    events = []
    for event in compositional_unit:
        if not event.is_rest:
            # Get instrument information from the parameter tree
            instrument = event._pt.get_active_instrument(event._node_id)
            
            if isinstance(instrument, MidiInstrument):
                is_drum = instrument.is_Drum
                program = 0 if is_drum else instrument.prgm
                note = event.get_parameter('note', instrument['note'])
                velocity = event.get_parameter('velocity', instrument['velocity'])
            else:
                # Fallback for non-MidiInstrument cases
                is_drum = event.get_parameter('is_drum', False)
                program = 0 if is_drum else event.get_parameter('program', 0)
                note = event.get_parameter('note', BASS_DRUM_NOTE if is_drum else 60)
                velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
            
            # Determine channel based on is_drum
            channel = PERCUSSION_CHANNEL if is_drum else 0
            
            start_time = event.start
            duration = abs(event.duration)
            
            events.append((start_time, 'note_on', channel, note, velocity, program))
            events.append((start_time + duration, 'note_off', channel, note, 0, program))
    
    events.sort(key=lambda x: x[0])
    
    # Track program changes per channel
    current_programs = {}
    current_time = 0.0
    
    for event_data in events:
        event_time, event_type = event_data[0], event_data[1]
        channel, note, velocity, program = event_data[2], event_data[3], event_data[4], event_data[5]
        
        delta_time = event_time - current_time
        beat_duration = 60.0 / bpm
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        # Add program change if needed (not for drum channel)
        if channel != PERCUSSION_CHANNEL and current_programs.get(channel) != program:
            track.append(Message('program_change', 
                               channel=channel, 
                               program=program, 
                               time=delta_ticks if event_type == 'note_on' else 0))
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
    
    # Collect all events from all units in the collection
    all_events = []
    
    # For TemporalUnitSequence: units are sequential
    # For TemporalBlock: units are parallel (multiple rows)
    if isinstance(collection, TemporalUnitSequence):
        # Sequential units - each has its own offset
        for unit in collection:
            _collect_events_from_unit(unit, all_events)
    elif isinstance(collection, TemporalBlock):
        # Parallel units - iterate through rows
        for row in collection:
            if isinstance(row, (TemporalUnit, CompositionalUnit)):
                _collect_events_from_unit(row, all_events)
            elif isinstance(row, TemporalUnitSequence):
                # TemporalBlock can contain TemporalUnitSequences
                for unit in row:
                    _collect_events_from_unit(unit, all_events)
            # Could also contain nested TemporalBlocks, but keep it simple for now
    
    # Sort all events by time
    all_events.sort(key=lambda x: x[0])
    
    # Track program changes per channel
    current_programs = {}
    current_time = 0.0
    
    # Generate MIDI messages
    for event_data in all_events:
        event_time, event_type = event_data[0], event_data[1]
        channel, note, velocity, program = event_data[2], event_data[3], event_data[4], event_data[5]
        
        delta_time = event_time - current_time
        beat_duration = 60.0 / bpm
        delta_ticks = int(delta_time / beat_duration * TICKS_PER_BEAT)
        
        # Add program change if needed (not for drum channel)
        if channel != PERCUSSION_CHANNEL and current_programs.get(channel) != program:
            track.append(Message('program_change', 
                               channel=channel, 
                               program=program, 
                               time=delta_ticks if event_type == 'note_on' else 0))
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
    
    return midi_file

def _collect_events_from_unit(unit, all_events):
    """Helper function to collect events from a single temporal unit."""
    if isinstance(unit, CompositionalUnit):
        # CompositionalUnit with parameters
        for event in unit:
            if not event.is_rest:
                # Get instrument information from the parameter tree
                instrument = event._pt.get_active_instrument(event._node_id)
                
                if isinstance(instrument, MidiInstrument):
                    is_drum = instrument.is_Drum
                    program = 0 if is_drum else instrument.prgm
                    note = event.get_parameter('note', instrument['note'])
                    velocity = event.get_parameter('velocity', instrument['velocity'])
                else:
                    # Fallback for non-MidiInstrument cases
                    is_drum = event.get_parameter('is_drum', False)
                    program = 0 if is_drum else event.get_parameter('program', 0)
                    note = event.get_parameter('note', BASS_DRUM_NOTE if is_drum else 60)
                    velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
                
                channel = PERCUSSION_CHANNEL if is_drum else 0
                start_time = event.start
                duration = abs(event.duration)
                
                all_events.append((start_time, 'note_on', channel, note, velocity, program))
                all_events.append((start_time + duration, 'note_off', channel, note, 0, program))
    else:
        # Regular TemporalUnit - use defaults
        for chronon in unit:
            if not chronon.is_rest:
                start_time = chronon.start
                duration = abs(chronon.duration)
                
                all_events.append((start_time, 'note_on', PERCUSSION_CHANNEL, BASS_DRUM_NOTE, DEFAULT_VELOCITY, 0))
                all_events.append((start_time + duration, 'note_off', PERCUSSION_CHANNEL, BASS_DRUM_NOTE, 0, 0))

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
            print("Detected Google Colab environment, using timidity...")
            return _midi_to_audio_colab(midi_path, audio_path)
        
        # Try FluidSynth for local environments
        if HAS_FLUIDSYNTH:
            print("Using FluidSynth for MIDI synthesis...")
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
            '--quiet'
        ], check=True, capture_output=True)
        
        audio_widget = Audio(audio_path, autoplay=False)
        return audio_widget
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
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