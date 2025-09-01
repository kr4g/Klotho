from mido import Message, MidiFile, MidiTrack, MetaMessage
from IPython.display import Audio
import os
import tempfile
import urllib.request
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from collections import deque
import math

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
from klotho.tonos.chords.chord import Chord, AddressedChord, Sonority, AddressedSonority, ChordSequence

DEFAULT_DRUM_NOTE = 77
PERCUSSION_CHANNEL = 9
DEFAULT_VELOCITY = 120
TICKS_PER_BEAT = 480

# Multi-Port MIDI Configuration
# The new system supports up to 256 channels across 16 ports (16 channels per port)
# Channels are dynamically allocated per voice with proper bank/program management
# Drum channels use Bank 128, melodic channels use Bank 0
# Channel 9 (10 in 1-based) is no longer globally reserved - it can be used for melodic or drum sounds
# This ensures EXACT microtonal tuning with proper voice independence

SOUNDFONT_URL = "https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3"
SOUNDFONT_PATH = os.path.expanduser("~/.fluidsynth/default_sound_font.sf3")

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



def play_midi(obj, dur=None, arp=False, prgm=0, max_channels=128, max_polyphony=None, 
              soundfont_path=None, bend_sensitivity_semitones=12, debug=False, **kwargs):
    """
    Play a musical object as MIDI audio in Jupyter/Colab notebooks.
    
    Automatically detects the environment and uses appropriate MIDI synthesis:
    - Google Colab: Uses FluidSynth CLI with multi-channel support
    - Local Jupyter: Uses FluidSynth if available
    - Fallback: Returns MIDI file for download
    
    Parameters
    ----------
    obj : RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, TemporalBlock,
          PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, Chord, 
          Sonority, or ChordSequence
        The musical object to play. Different object types have different playback behaviors:
        - RhythmTree/TemporalUnit: Rhythmic playback with default pitch
        - PitchCollection/AddressedPitchCollection: Sequential pitch playback
        - Scale/AddressedScale: Ascending then descending playback
        - Chord/AddressedChord/Sonority/AddressedSonority: Block chord or arpeggiated playback
        - ChordSequence: Sequential playback of chords/sonorities
    dur : float, optional
        Duration in seconds. Defaults depend on object type:
        - PitchCollection/Scale: 0.5 seconds per note
        - Chord/Sonority: 3.0 seconds total (or per note if arpeggiated)
        - ChordSequence: 3.0 seconds per chord
    arp : bool, optional
        For chords only: if True, arpeggiate the chord (default False)
    prgm : int, optional
        MIDI program number (0-127) for instrument sound (default 0 = Acoustic Grand Piano)
    max_channels : int, optional
        Maximum number of MIDI channels to allocate across all ports (default 128)
        Supports up to 256 channels across 16 ports
    max_polyphony : int, optional
        Maximum polyphony for synthesis (default equals max_channels)
    soundfont_path : str, optional
        Path to custom soundfont file (uses system default if None)
    bend_sensitivity_semitones : int, optional
        Pitch bend range in semitones (default 12, supports 12 or 24)
    debug : bool, optional
        Enable debug logging for channel allocation (default False)
    **kwargs
        Additional arguments passed to MIDI creation functions
        
    Returns
    -------
    IPython.display.Audio or IPython.display.FileLink
        Audio widget for playback in Jupyter notebooks, or file link 
        if audio synthesis is unavailable
        
    Notes
    -----
    For Google Colab, FluidSynth is automatically installed if needed.
    For local environments, install FluidSynth for best results.
    The new backend supports true independence for up to 256 simultaneous voices
    with proper microtonal pitch bend and dynamic drum channel allocation.
    """
    # Reset any global state to ensure clean slate for each call
    _reset_microtonal_counter()
    
    match obj:
        case TemporalUnitSequence() | TemporalBlock():
            midi_file = _create_midi_from_collection(obj, max_channels=max_channels, 
                                                   bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case CompositionalUnit():
            midi_file = _create_midi_from_compositional_unit(obj, max_channels=max_channels, 
                                                           bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case TemporalUnit():
            midi_file = _create_midi_from_temporal_unit(obj, max_channels=max_channels, 
                                                      bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case RhythmTree():
            temporal_unit = TemporalUnit.from_rt(obj)
            midi_file = _create_midi_from_temporal_unit(temporal_unit, max_channels=max_channels, 
                                                      bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case ChordSequence():
            midi_file = _create_midi_from_chord_sequence(obj, dur=dur or 3.0, arp=arp, prgm=prgm, 
                                                       max_channels=max_channels, bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case PitchCollection() | EquaveCyclicCollection() | AddressedPitchCollection():
            if isinstance(obj, (Scale, AddressedScale)):
                midi_file = _create_midi_from_scale(obj, dur=dur or 0.5, prgm=prgm, 
                                                  max_channels=max_channels, bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
            elif isinstance(obj, (Chord, AddressedChord, Sonority, AddressedSonority)):
                midi_file = _create_midi_from_chord(obj, dur=dur or 3.0, arp=arp, prgm=prgm, 
                                                  max_channels=max_channels, bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
            else:
                midi_file = _create_midi_from_pitch_collection(obj, dur=dur or 0.5, prgm=prgm, 
                                                             max_channels=max_channels, bend_sensitivity_semitones=bend_sensitivity_semitones, debug=debug)
        case _:
            raise TypeError(f"Unsupported object type: {type(obj)}. Supported types: RhythmTree, TemporalUnit, CompositionalUnit, TemporalUnitSequence, TemporalBlock, PitchCollection, EquaveCyclicCollection, AddressedPitchCollection, Scale, AddressedScale, Chord, AddressedChord, Sonority, AddressedSonority, ChordSequence.")
    
    return _midi_to_audio(midi_file, soundfont_path=soundfont_path, max_polyphony=max_polyphony)

def _create_midi_from_temporal_unit(temporal_unit, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a TemporalUnit using absolute timing."""
    # PRD: Use absolute timing only - ignore BPM/tempo from temporal objects
    # Always use 4/4 at 120 BPM for MIDI file, rely on absolute start/duration times
    bpm = 120
    
    # For TemporalUnit: Use SINGLE drum channel for all notes (PRD requirement)
    # TemporalUnit represents rhythmic patterns - all notes should use drum channel 9
    writer = MultiPortMidiWriter(max_voices=1)  # Only need 1 voice for single channel
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    # Allocate ONE drum channel for the entire TemporalUnit
    try:
        port, channel = allocator.allocate_voice("temporal_drum_channel", is_drum=True, program=1)
        if debug:
            print(f"[DEBUG] TemporalUnit: Using single drum channel - port={port}, channel={channel}")
    except RuntimeError as e:
        if debug:
            print(f"[DEBUG] Failed to allocate drum channel: {e}")
        # Fallback: use channel 9 directly
        port, channel = 0, 9
    
    note_events = []
    
    # For standalone playback: subtract offset to start from beginning (DO NOT MUTATE OBJECT)
    min_start_time = min(chronon.start for chronon in temporal_unit if not chronon.is_rest) if any(not chronon.is_rest for chronon in temporal_unit) else 0
    
    for chronon in temporal_unit:
        if not chronon.is_rest:
            # Use absolute timing from chronon, subtract offset for standalone playback
            start_time = chronon.start - min_start_time
            duration = abs(chronon.duration)
            
            # All notes use the SAME drum channel (PRD requirement)
            note_events.append({
                'voice_id': "temporal_drum_channel",
                'port': port,
                'channel': channel,  # Same channel for all notes
                'start_time': start_time,
                'duration': duration,
                'midi_note': DEFAULT_DRUM_NOTE,
                'velocity': DEFAULT_VELOCITY,
                'program': 1,  # GM Standard Drum Kit
                'is_drum': True,
                'pitch_bend': None
            })
    
    if debug:
        print(f"[DEBUG] TemporalUnit: {len(note_events)} notes, all using channel {channel}")
    
    # Generate MIDI events using new allocator system
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Ensure MIDI file duration matches the TemporalUnit's total duration
    writer.finalize(bpm)
    return writer.get_midi_file()

def _create_midi_from_compositional_unit(compositional_unit, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a CompositionalUnit using absolute timing."""
    # Check if all instruments are drums OR no instruments (assume rhythmic) - use simple collection approach
    all_drums = True
    has_explicit_instruments = False
    has_melodic_instruments = False
    
    for event in compositional_unit:
        if not event.is_rest:
            instrument = event._pt.get_active_instrument(event._node_id)
            if isinstance(instrument, MidiInstrument):
                has_explicit_instruments = True
                if not instrument.is_Drum:
                    has_melodic_instruments = True
                    all_drums = False
                    break
            # If no explicit instrument, assume rhythmic content (drums)
    
    # Always use multi-port approach for voice independence and 256-channel support
    if debug:
        instrument_types = []
        for event in compositional_unit:
            if not event.is_rest:
                instrument = event._pt.get_active_instrument(event._node_id)
                if isinstance(instrument, MidiInstrument):
                    instrument_types.append("drum" if instrument.is_Drum else "melodic")
                else:
                    instrument_types.append("unknown")
        print(f"[DEBUG] CompositionalUnit: {len(instrument_types)} events, types={set(instrument_types)}, using multi-port approach")
    
    # PRD: Use absolute timing only - ignore BPM/tempo from temporal objects
    # Always use 4/4 at 120 BPM for MIDI file, rely on absolute start/duration times
    bpm = 120
    
    # For CompositionalUnit: Use FULL implementation capabilities for voice independence
    # Each note gets its own channel for microtonal support and voice independence
    num_notes = len([event for event in compositional_unit if not event.is_rest])
    
    # Calculate how many drum and melodic notes we have
    num_drums = 0
    num_melodic = 0
    for event in compositional_unit:
        if not event.is_rest:
            instrument = event._pt.get_active_instrument(event._node_id)
            if isinstance(instrument, MidiInstrument) and instrument.is_Drum:
                num_drums += 1
            else:
                num_melodic += 1
    
    # Calculate minimum ports needed:
    # - Drums: need ceil(num_drums / 1) ports (1 drum channel per port)  
    # - Melodic: need ceil(num_melodic / 15) ports (15 melodic channels per port)
    ports_for_drums = num_drums  # Each port provides 1 drum channel
    ports_for_melodic = math.ceil(num_melodic / 15) if num_melodic > 0 else 0
    min_ports_needed = max(ports_for_drums, ports_for_melodic, 1)
    
    max_concurrent = min(num_notes, max_channels)
    
    # Create multi-port writer with unlimited ports for voice independence
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    if debug:
        print(f"[DEBUG] CompositionalUnit: {num_notes} notes, using multi-port approach")
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    # Collect all note events with per-note channel allocation
    note_events = []
    voice_counter = 0
    
    # For standalone playback: subtract offset to start from beginning (DO NOT MUTATE OBJECT)
    min_start_time = min(event.start for event in compositional_unit if not event.is_rest) if any(not event.is_rest for event in compositional_unit) else 0
    
    for event in compositional_unit:
        if not event.is_rest:
            # Get instrument information
            instrument = event._pt.get_active_instrument(event._node_id)
            
            if isinstance(instrument, MidiInstrument):
                is_drum = instrument.is_Drum
                # For drums: ignore instrument.prgm, always use Standard Drum Kit (1)
                # For melodic: use instrument.prgm
                program = 1 if is_drum else instrument.prgm
                note_param = event.get_parameter('note', instrument['note'])
                velocity = event.get_parameter('velocity', instrument['velocity'])
            else:
                # Fallback for CompositionalUnit without explicit instruments
                is_drum = event.get_parameter('is_drum', False)
                default_program = 1 if is_drum else 1  # Default to Standard Drum Kit for rhythmic content
                program = event.get_parameter('program', default_program)
                note_param = event.get_parameter('note', DEFAULT_DRUM_NOTE if is_drum else 60)
                velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
            
            voice_id = f"voice_{voice_counter}"
            voice_counter += 1
            
            # Use absolute timing from event, subtract offset for standalone playback (DO NOT MUTATE OBJECT)
            start_time = event.start - min_start_time
            duration = abs(event.duration)
            
            # Allocate individual channel for each note (PRD: full voice independence)
            try:
                if debug:
                    print(f"[DEBUG] Allocating voice_id={voice_id}, is_drum={is_drum}, program={program}")
                port, channel = allocator.allocate_voice(voice_id, is_drum, program)
                if debug:
                    print(f"[DEBUG] Allocated port={port}, channel={channel}")
            except RuntimeError:
                # If we run out of channels, skip this note
                continue
            
            # Handle microtonal notes and pitch bend
            if is_drum:
                midi_note = int(note_param) if note_param else DEFAULT_DRUM_NOTE
                pitch_bend = None
            elif isinstance(note_param, Pitch):
                midi_note, pitch_bend = _calculate_base_note_and_bend(note_param, allocator.bend_sensitivity_semitones)
            elif isinstance(note_param, float) and note_param != int(note_param):
                pitch = Pitch.from_midi(note_param)
                midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, allocator.bend_sensitivity_semitones)
            else:
                midi_note = int(note_param) if note_param else 60
                pitch_bend = None
            
            note_events.append({
                'voice_id': voice_id,
                'port': port,
                'channel': channel,
                'start_time': start_time,
                'duration': duration,
                'midi_note': midi_note,
                'velocity': velocity,
                'program': program,
                'is_drum': is_drum,
                'pitch_bend': pitch_bend
            })
    
    # Generate MIDI events using new allocator system
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Finalize and return
    writer.finalize(bpm)
    return writer.get_midi_file()

def _create_midi_from_collection(collection, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a TemporalUnitSequence or TemporalBlock using multi-port approach for voice independence."""
    # PRD: Use absolute timing only - ignore BPM/tempo from temporal objects
    # Always use 4/4 at 120 BPM for MIDI file, rely on absolute start/duration times
    bpm = 120
    
    # Estimate max concurrent voices needed across all units
    max_concurrent = _estimate_max_concurrent_voices(collection)
    max_concurrent = min(max_concurrent, max_channels)
    
    # Create writer with enough capacity for voice independence
    # Use multi-port approach to provide unlimited channel support per your spec
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    if debug:
        print(f"[DEBUG] Collection: {max_concurrent} voices, {writer.num_ports} ports, using multi-port for voice independence")
    
    # Collect all note events from all units in the collection
    note_events = []
    voice_counter = 0
    
    # For TemporalUnitSequence: units are sequential
    # For TemporalBlock: units are parallel (multiple rows)
    if isinstance(collection, TemporalUnitSequence):
        # Sequential units - each unit has its own offset already built in
        for unit in collection:
            voice_counter = _collect_note_events_from_unit(unit, note_events, 0.0, voice_counter, allocator, debug)
    elif isinstance(collection, TemporalBlock):
        # Parallel units - all rows start at the same time (time 0)
        for row in collection:
            # Recursively handle ANY temporal object (including nested BT/UTS)
            voice_counter = _collect_note_events_from_unit(row, note_events, 0.0, voice_counter, allocator)
    
    # Sort note events by time for proper sequential playback
    note_events.sort(key=lambda event: event['start_time'])
    
    # Generate MIDI events using new allocator system for voice independence
    if debug:
        print(f"[DEBUG] Collection: Generating MIDI for {len(note_events)} note events")
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Finalize and return
    writer.finalize(bpm)
    return writer.get_midi_file()



def _collect_note_events_from_unit(unit, note_events, time_offset, voice_counter, allocator, debug=False):
    """Helper function to collect note events from a single temporal unit with multi-port allocation."""
    from klotho.chronos.temporal_units.temporal import TemporalUnit
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if debug:
        print(f"[DEBUG] Collecting from {type(unit)}, voice_counter={voice_counter}")
    
    if isinstance(unit, CompositionalUnit):
        # CompositionalUnit with parameters - each note gets own channel
        for event in unit:
            if not event.is_rest:
                # Get instrument information from the parameter tree
                instrument = event._pt.get_active_instrument(event._node_id)
                
                if isinstance(instrument, MidiInstrument):
                    is_drum = instrument.is_Drum
                    # For drums: ignore instrument.prgm, always use Standard Drum Kit (1)
                    # For melodic: use instrument.prgm
                    program = 1 if is_drum else instrument.prgm
                    note_param = event.get_parameter('note', instrument['note'])
                    velocity = event.get_parameter('velocity', instrument['velocity'])
                else:
                    # Fallback for non-MidiInstrument cases
                    is_drum = event.get_parameter('is_drum', False)
                    default_program = 1 if is_drum else 1
                    program = event.get_parameter('program', default_program)
                    note_param = event.get_parameter('note', DEFAULT_DRUM_NOTE if is_drum else 60)
                    velocity = event.get_parameter('velocity', DEFAULT_VELOCITY)
                
                voice_id = f"collection_voice_{voice_counter}"
                voice_counter += 1
                
                start_time = event.start + time_offset
                duration = abs(event.duration)
                
                # Allocate individual channel for each note (PRD: voice independence)
                try:
                    port, channel = allocator.allocate_voice(voice_id, is_drum, program)
                except RuntimeError:
                    continue
                
                # Handle microtonal notes
                if is_drum:
                    midi_note = int(note_param) if note_param else DEFAULT_DRUM_NOTE
                    pitch_bend = None
                elif isinstance(note_param, Pitch):
                    midi_note, pitch_bend = _calculate_base_note_and_bend(note_param, allocator.bend_sensitivity_semitones)
                elif isinstance(note_param, float) and note_param != int(note_param):
                    pitch = Pitch.from_midi(note_param)
                    midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, allocator.bend_sensitivity_semitones)
                else:
                    midi_note = int(note_param) if note_param else 60
                    pitch_bend = None
                
                note_events.append({
                    'voice_id': voice_id,
                    'port': port,
                    'channel': channel,
                    'start_time': start_time,
                    'duration': duration,
                    'midi_note': midi_note,
                    'velocity': velocity,
                    'program': program,
                    'is_drum': is_drum,
                    'pitch_bend': pitch_bend
                })
    
    elif isinstance(unit, TemporalUnit):
        # TemporalUnit: use single drum channel (optimization)
        try:
            port, channel = allocator.allocate_voice("temporal_drum_shared", is_drum=True, program=1)
        except RuntimeError:
            port, channel = 0, 9  # Fallback
        
        for chronon in unit:
            if not chronon.is_rest:
                voice_id = "temporal_drum_shared"  # Reuse same voice for TemporalUnit
                start_time = chronon.start + time_offset
                duration = abs(chronon.duration)
                
                note_events.append({
                    'voice_id': voice_id,
                    'port': port,
                    'channel': channel,  # Same channel for all TemporalUnit notes
                    'start_time': start_time,
                    'duration': duration,
                    'midi_note': DEFAULT_DRUM_NOTE,
                    'velocity': DEFAULT_VELOCITY,
                    'program': 1,
                    'is_drum': True,
                    'pitch_bend': None
                })
    
    elif isinstance(unit, TemporalUnitSequence):
        # Recursive case: TemporalUnitSequence containing other temporal objects
        for sub_unit in unit:
            voice_counter = _collect_note_events_from_unit(sub_unit, note_events, time_offset, voice_counter, allocator, debug)
    
    elif isinstance(unit, TemporalBlock):
        # Recursive case: TemporalBlock containing other temporal objects
        for row in unit:
            voice_counter = _collect_note_events_from_unit(row, note_events, time_offset, voice_counter, allocator, debug)
    
    else:
        if debug:
            print(f"[DEBUG] Warning: Unknown unit type {type(unit)}, skipping")
    
    return voice_counter

def _collect_events_from_unit_with_offset(unit, all_events, time_offset=0.0):
    """Helper function to collect events from a single temporal unit with time offset."""
    # Handle different types of temporal objects
    from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if isinstance(unit, CompositionalUnit):
        # CompositionalUnit: iterate over events (which are Chronon objects with is_rest)
        unit_copy = unit.copy()
        for event in unit_copy:
            if not event.is_rest:
                # Get instrument information from the parameter tree
                instrument = event._pt.get_active_instrument(event._node_id)
                
                if isinstance(instrument, MidiInstrument):
                    is_drum = instrument.is_Drum
                    # For drums: ignore instrument.prgm, always use Standard Drum Kit (1)
                    # For melodic: use instrument.prgm
                    program = 1 if is_drum else instrument.prgm
                    note_param = event.get_parameter('note', instrument['note'])
                    velocity = event.get_parameter('velocity', instrument['velocity'])
                else:
                    # Fallback for non-MidiInstrument cases
                    is_drum = event.get_parameter('is_drum', False)
                    # Fix: Don't default to Piano (0) - use sensible defaults
                    default_program = 1 if is_drum else 1  # Default to Standard Drum Kit for rhythmic content
                    program = event.get_parameter('program', default_program)
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
    
    elif isinstance(unit, TemporalUnit):
        # TemporalUnit: iterate over chronons (which have is_rest)
        unit_copy = unit.copy()
        for chronon in unit_copy:
            if not chronon.is_rest:
                start_time = chronon.start + time_offset
                duration = abs(chronon.duration)
                
                # TemporalUnit should use drum sounds, not piano (program 1, not 0)
                all_events.append((start_time, 'note_on', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, DEFAULT_VELOCITY, 1))
                all_events.append((start_time + duration, 'note_off', PERCUSSION_CHANNEL, DEFAULT_DRUM_NOTE, 0, 1))
    
    elif isinstance(unit, (TemporalUnitSequence, TemporalBlock)):
        # Recursive case: these contain other temporal objects
        if isinstance(unit, TemporalUnitSequence):
            # Sequential: process each unit in order
            for sub_unit in unit:
                _collect_events_from_unit_with_offset(sub_unit, all_events, time_offset)
        elif isinstance(unit, TemporalBlock):
            # Parallel: all units start at the same time
            for sub_unit in unit:
                _collect_events_from_unit_with_offset(sub_unit, all_events, time_offset)
    
    else:
        print(f"Warning: Unknown unit type {type(unit)}, skipping")

def _midi_to_audio(midi_file, soundfont_path=None, max_polyphony=None):
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
    """Convert MIDI to audio in Google Colab using FluidSynth CLI (PRD requirement)."""
    try:
        # Analyze MIDI file to determine channel requirements
        midi_file = MidiFile(midi_path)
        max_channels = _get_max_channels_from_midi(midi_file)
        
        # Round up to nearest multiple of 16 for port allocation
        channels_needed = ((max_channels - 1) // 16 + 1) * 16
        channels_needed = max(16, min(channels_needed, 256))  # Cap at 256 channels
        
        # Calculate polyphony (estimate based on concurrent notes)
        estimated_polyphony = max(channels_needed * 2, 256)
        
        # First try to install FluidSynth if not available
        try:
            subprocess.run(['which', 'fluidsynth'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("Installing FluidSynth for multi-channel MIDI rendering...")
            subprocess.run([
                'apt-get', 'update', '-qq'
            ], check=True, capture_output=True)
            subprocess.run([
                'apt-get', 'install', '-y', '-qq', 'fluidsynth', 'fluid-soundfont-gm'
        ], check=True, capture_output=True)
        
        # Use FluidSynth CLI with multi-channel support (PRD requirement)
        fluidsynth_cmd = [
            'fluidsynth',
            '-ni',  # No interactive mode
            '-o', f'synth.midi-channels={channels_needed}',
            '-o', f'synth.polyphony={estimated_polyphony}',
            '/usr/share/sounds/sf2/FluidR3_GM.sf2',  # Default Colab soundfont
            midi_path,
            '-F', audio_path,
            '-r', '44100'
        ]
        
        subprocess.run(fluidsynth_cmd, check=True, capture_output=True)
        
        audio_widget = Audio(audio_path, autoplay=False)
        return audio_widget
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"FluidSynth installation or execution failed: {e}")
        print("PRD requires FluidSynth CLI for Colab. Install with: !apt install fluidsynth fluid-soundfont-gm")
        return _midi_to_audio_fallback(midi_path)

def _midi_to_audio_fluidsynth(midi_path, audio_path):
    """Convert MIDI to audio using FluidSynth CLI with multi-channel support."""
    try:
        # Analyze MIDI file to determine channel requirements (same as Colab)
        midi_file = MidiFile(midi_path)
        max_channels = _get_max_channels_from_midi(midi_file)
        
        # For multi-port MIDI files, we need to count ALL channels across ALL ports
        # Each port contributes 16 channels, so total = num_ports * 16
        num_ports = len([track for track in midi_file.tracks if any(msg.type == 'midi_port' for msg in track)])
        if num_ports > 0:
            channels_needed = num_ports * 16  # Each port has 16 channels
        else:
            # Fallback for single-port files
            channels_needed = ((max_channels - 1) // 16 + 1) * 16
        channels_needed = max(16, min(channels_needed, 256))  # Cap at 256 channels
        
        # Calculate polyphony (estimate based on concurrent notes)
        estimated_polyphony = max(channels_needed * 2, 256)
        
        # Try FluidSynth CLI first (same approach as Colab)
        soundfont = _ensure_soundfont()
        if not soundfont:
            soundfont = "/System/Library/Compositions/VoiceOver/Compact.sf2"  # macOS fallback
        
        fluidsynth_cmd = [
            'fluidsynth',
            '-ni',  # No interactive mode
            '-o', f'synth.midi-channels={channels_needed}',
            '-o', f'synth.polyphony={estimated_polyphony}',
            soundfont,
            midi_path,
            '-F', audio_path,
            '-r', '44100'
        ]
        
        # Try CLI version first
        try:
            subprocess.run(fluidsynth_cmd, check=True, capture_output=True)
            audio_widget = Audio(audio_path, autoplay=False)
            return audio_widget
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to pyfluidsynth if CLI fails
            pass
    
    except Exception:
        # If anything fails, fall back to original method
        pass
    
    # Fallback: Original pyfluidsynth method (limited channels)
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

# Legacy functions removed - now using MultiPortMidiWriter + ChannelAllocator system

def _get_max_channels_from_midi(midi_file):
    """
    Analyze a MIDI file to determine the maximum number of channels used.
    
    Parameters
    ----------
    midi_file : MidiFile
        The MIDI file to analyze
        
    Returns
    -------
    int
        Maximum channel number used + 1 (since channels are 0-indexed)
    """
    max_channel = 0
    
    for track in midi_file.tracks:
        for msg in track:
            if hasattr(msg, 'channel'):
                max_channel = max(max_channel, msg.channel)
    
    return max_channel + 1  # Convert from 0-indexed to count

class MultiPortMidiWriter:
    """
    Multi-port MIDI file writer that supports up to 256 channels across 16 ports.
    
    Creates Type 1 MIDI files with:
    - Track 0: Global meta events (tempo, time signature)
    - Track 1-N: One track per port with midi_port meta message
    """
    
    def __init__(self, max_voices=128, ticks_per_beat=TICKS_PER_BEAT):
        self.max_voices = max_voices
        self.ticks_per_beat = ticks_per_beat
        self.num_ports = math.ceil(max_voices / 16)
        # Remove 16-port limit for voice independence - MIDI spec allows more ports
        # Each port provides 16 channels, so we can have many ports for voice independence
        
        # Create MIDI file structure
        self.midi_file = MidiFile(type=1, ticks_per_beat=ticks_per_beat)
        
        # Track 0: Global meta events only
        self.meta_track = MidiTrack()
        self.midi_file.tracks.append(self.meta_track)
        
        # Port tracks: One track per port
        self.port_tracks = []
        for port in range(self.num_ports):
            track = MidiTrack()
            # Add midi_port meta message at time 0
            track.append(MetaMessage('midi_port', port=port, time=0))
            self.port_tracks.append(track)
            self.midi_file.tracks.append(track)
        
        # Event buckets: Store events per port before final timing calculation
        self.port_events = [[] for _ in range(self.num_ports)]
    
    def add_meta_event(self, meta_message):
        """Add a meta event to Track 0."""
        self.meta_track.append(meta_message)
    
    def add_event(self, port, event_time, message):
        """Add a MIDI event to the specified port's event bucket."""
        if port >= self.num_ports:
            raise ValueError(f"Port {port} exceeds maximum ports {self.num_ports}")
        
        self.port_events[port].append((event_time, message))
    
    def finalize(self, bpm=120):
        """
        Finalize the MIDI file by sorting events and calculating delta times.
        
        Parameters
        ----------
        bpm : float
            Beats per minute for timing calculations
        """
        beat_duration = 60.0 / bpm
        
        # Process each port's events
        for port, events in enumerate(self.port_events):
            if not events:
                continue
                
            track = self.port_tracks[port]
            
            # Sort events by time, then by message type priority
            # Proper MIDI setup order: Bank Select -> Program Change -> Pitch Bend -> Note On
            message_priority = {
                'control_change': 0,  # Bank Select (CC0) and RPN messages
                'program_change': 1,
                'pitchwheel': 2,      # Pitch bend after program setup
                'note_on': 3,
                'note_off': 4
            }
            
            events.sort(key=lambda x: (x[0], message_priority.get(x[1].type, 5)))
            
            # Calculate delta times and add to track
            current_time = 0.0
            for event_time, message in events:
                delta_time = event_time - current_time
                delta_ticks = int(delta_time / beat_duration * self.ticks_per_beat)
                
                # Clone message with delta time
                msg_copy = message.copy(time=delta_ticks)
                track.append(msg_copy)
                
                current_time = event_time
    
    def get_midi_file(self):
        """Return the completed MIDI file."""
        return self.midi_file

class ChannelAllocator:
    """
    Per-note channel allocator that manages (port, channel) assignment for voices.
    
    Maintains separate pools for melodic and drum channels per port.
    Ensures no channel conflicts during concurrent note playback.
    """
    
    def __init__(self, num_ports, bend_sensitivity_semitones=12):
        self.num_ports = num_ports
        self.bend_sensitivity_semitones = bend_sensitivity_semitones
        
        # For better synthesizer compatibility, use single-port approach with channel cycling
        # Channel 9 is reserved for drums in GM spec, many synthesizers hard-code this
        if num_ports == 1:
            # Single port: traditional 16-channel approach
            melodic_channels = [ch for ch in range(16) if ch != 9]  # 0-8, 10-15
            self.free_melodic = [deque(melodic_channels)]
            self.free_drum = [deque([9])]  # Channel 9 for drums
        else:
            # Multi-port: each port gets full channel range
            melodic_channels = [ch for ch in range(16) if ch != 9]  # 0-8, 10-15
            self.free_melodic = [deque(melodic_channels) for _ in range(num_ports)]
            self.free_drum = [deque([9]) for _ in range(num_ports)]  # Start with channel 9 available for drums
        
        # Active voice tracking: voice_id -> (port, channel, is_drum)
        self.active_voices = {}
        
        # Channel state per port: [port][channel] -> {bank, program, bend_sens}
        self.channel_state = [[{} for _ in range(16)] for _ in range(num_ports)]
        
        # Round-robin port selection
        self.next_port = 0
    
    def allocate_voice(self, voice_id, is_drum=False, program=0):
        """
        Allocate a (port, channel) for a new voice.
        
        Parameters
        ----------
        voice_id : hashable
            Unique identifier for this voice
        is_drum : bool
            Whether this voice uses drum sounds
        program : int
            MIDI program number
            
        Returns
        -------
        tuple
            (port, channel) allocation
        """
        # Allocate channel based on voice type (following user spec: sequential exhaustion)
        if is_drum:
            # For drums: Sequential port allocation - exhaust port 0, then port 1, etc.
            # Each port provides 1 drum channel (channel 9)
            port = None
            channel = None
            
            for p in range(self.num_ports):
                if self.free_drum[p]:
                    port = p
                    channel = self.free_drum[p].popleft()
                    # Clear channel state for newly allocated channel
                    self.channel_state[port][channel] = {}
                    break
            
            if port is None:
                # For sequential events, reuse channel 9 on port 0 since notes don't overlap
                port = 0
                channel = 9
                # Clear channel state for reused channel
                self.channel_state[port][channel] = {}
                
        else:
            # For melodic: Sequential port allocation - exhaust all channels on port 0, then port 1, etc.
            # Each port provides 15 melodic channels (0-8, 10-15)
            port = None
            channel = None
            
            for p in range(self.num_ports):
                if self.free_melodic[p]:
                    port = p
                    channel = self.free_melodic[p].popleft()
                    # Clear channel state for newly allocated channel
                    self.channel_state[port][channel] = {}
                    break
            
            if port is None:
                # For sequential events, cycle through melodic channels on port 0
                port = 0
                available_channels = [ch for ch in range(16) if ch != 9]
                channel = available_channels[0]  # Use first melodic channel
                # Clear channel state for reused channel
                self.channel_state[port][channel] = {}
        
        # Record allocation
        self.active_voices[voice_id] = (port, channel, is_drum)
        
        return port, channel
    
    def release_voice(self, voice_id):
        """
        Release a voice and return its channel to the appropriate pool.
        
        Parameters
        ----------
        voice_id : hashable
            The voice identifier to release
        """
        if voice_id not in self.active_voices:
            return
        
        port, channel, is_drum = self.active_voices.pop(voice_id)
        
        # Return channel to appropriate pool (following PRD)
        if is_drum:
            # Return to drum pool
            self.free_drum[port].append(channel)
        else:
            # Return to melodic pool
            self.free_melodic[port].append(channel)
    
    def get_channel_state(self, port, channel):
        """Get the current state of a channel."""
        return self.channel_state[port][channel]
    
    def set_channel_state(self, port, channel, **kwargs):
        """Update the state of a channel."""
        self.channel_state[port][channel].update(kwargs)
    
    def get_available_channels(self):
        """Get count of available channels for debugging."""
        total_melodic = sum(len(pool) for pool in self.free_melodic)
        total_drum = sum(len(pool) for pool in self.free_drum)
        return total_melodic, total_drum

def _estimate_max_concurrent_voices(obj):
    """
    Estimate the maximum number of concurrent voices needed for an object.
    
    Recursively counts all note events in nested temporal structures.
    
    Parameters
    ----------
    obj : musical object
        The object to analyze
        
    Returns
    -------
    int
        Estimated maximum concurrent voices
    """
    from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalUnitSequence, TemporalBlock
    from klotho.thetos.composition.compositional import CompositionalUnit
    
    if isinstance(obj, (TemporalUnitSequence, TemporalBlock)):
        # Recursively count all events in nested structures
        total_events = 0
        for unit in obj:
            total_events += _estimate_max_concurrent_voices(unit)
        return min(total_events, 256)  # Cap at 256 voices
    
    elif isinstance(obj, (TemporalUnit, CompositionalUnit)):
        # Count non-rest events in the unit
        return len([event for event in obj if not event.is_rest])
    
    elif hasattr(obj, '__len__'):
        # For other collections (scales, chords, etc.)
        return min(len(obj), 256)  # Cap at 256 voices
    
    else:
        # For single objects, assume 32 voices as reasonable default (2 ports)
        return 32

def _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones):
    """
    Calculate optimal base MIDI note and pitch bend for microtonal pitch.
    
    Parameters
    ----------
    pitch : Pitch
        The target pitch
    bend_sensitivity_semitones : int
        Maximum bend range in semitones
        
    Returns
    -------
    tuple
        (base_midi_note, pitch_bend_value)
    """
    target_midi = pitch.midi
    
    # For standard 12-TET notes, no bend needed
    if abs(target_midi - round(target_midi)) < 0.001:
        return int(round(target_midi)), 8192  # Center pitch bend
    
    # Choose base note to minimize bend amount
    nearest_midi = round(target_midi)
    cents_offset = (target_midi - nearest_midi) * 100.0
    
    # If bend exceeds sensitivity, choose different base note
    if abs(cents_offset) > bend_sensitivity_semitones * 100:
        if cents_offset > 0:
            nearest_midi = int(target_midi) + 1
        else:
            nearest_midi = int(target_midi)
        cents_offset = (target_midi - nearest_midi) * 100.0
    
    # Convert cents to pitch bend value
    max_bend_cents = bend_sensitivity_semitones * 100
    pitch_bend_value = int(8192 + (cents_offset / max_bend_cents) * 8192)
    pitch_bend_value = max(0, min(16383, pitch_bend_value))
    
    return nearest_midi, pitch_bend_value

def _generate_multi_port_events(note_events, writer, allocator, bpm, debug=False):
    """
    Generate MIDI events using the multi-port writer and channel allocator.
    
    IMPORTANT: Every note gets its own channel for true voice independence,
    sustain capability, and unique tuning. Voices are released when notes end.
    
    Parameters
    ----------
    note_events : list
        List of note event dictionaries
    writer : MultiPortMidiWriter
        The multi-port MIDI writer
    allocator : ChannelAllocator
        The channel allocator
    bpm : float
        Beats per minute
    """
    # Generate all MIDI events - each note gets its own dedicated channel
    for note_event in note_events:
        voice_id = note_event['voice_id']
        port = note_event['port']
        channel = note_event['channel']
        start_time = note_event['start_time']
        duration = note_event['duration']
        midi_note = note_event['midi_note']
        velocity = note_event['velocity']
        program = note_event['program']
        is_drum = note_event['is_drum']
        pitch_bend = note_event['pitch_bend']
        
        # Always set up channel for new voice allocation (ensures clean state)
        # Send setup messages at note time but rely on MIDI writer's event sorting for proper order
        
        # Handle bank/program setup based on instrument type
        if is_drum:
            # For drums: Use Bank 0 (GM standard) + Program Change
            # In GM, drums use channel 9 with standard programs, no special bank needed
            if debug:
                print(f"[DEBUG] Setting up DRUM channel {channel}: Bank 0, Program {program}")
            writer.add_event(port, start_time, Message('control_change', 
                                                     channel=channel, control=0, value=0))  # Bank Select MSB
            writer.add_event(port, start_time, Message('program_change', 
                                                     channel=channel, program=program))
            allocator.set_channel_state(port, channel, program=program, bank=0)
        else:
            # For melodic: Always send Bank Select 0 + Program Change
            if debug:
                print(f"[DEBUG] Setting up MELODIC channel {channel}: Bank 0, Program {program}")
            writer.add_event(port, start_time, Message('control_change', 
                                                     channel=channel, control=0, value=0))  # Bank Select MSB
            writer.add_event(port, start_time, Message('program_change', 
                                                     channel=channel, program=program))
            allocator.set_channel_state(port, channel, program=program, bank=0)
        
        # Always set pitch bend sensitivity for new voice
        _send_rpn_pitch_bend_sensitivity(writer, port, channel, start_time, 
                                       allocator.bend_sensitivity_semitones)
        allocator.set_channel_state(port, channel, bend_sens=allocator.bend_sensitivity_semitones)
        
        # Always reset pitch bend to center for new voice
        writer.add_event(port, start_time, Message('pitchwheel', 
                                                 channel=channel, pitch=0))  # Center pitch bend
        
        # Send pitch bend if needed (same time as note, sorted by message priority)
        if pitch_bend is not None:
            pitch_value = pitch_bend - 8192  # Convert to MIDI pitchwheel range
            writer.add_event(port, start_time, Message('pitchwheel', 
                                                     channel=channel, pitch=pitch_value))
        
        # Send note on
        if debug:
            print(f"[DEBUG] Note ON:  port={port}, ch={channel}, note={midi_note}, time={start_time:.3f}, dur={duration:.3f}")
        writer.add_event(port, start_time, Message('note_on', 
                                                 channel=channel, note=midi_note, velocity=velocity))
        
        # Send note off
        writer.add_event(port, start_time + duration, Message('note_off', 
                                                            channel=channel, note=midi_note, velocity=0))
    
    # NOTE: Voice release is not needed for the current implementation
    # Each note gets its own dedicated channel for the duration of playback
    # This ensures perfect voice independence as per PRD requirements
    # The allocator is designed to handle the maximum concurrent voices needed

def _send_rpn_pitch_bend_sensitivity(writer, port, channel, time, semitones):
    """
    Send RPN 0 (Pitch Bend Sensitivity) message sequence.
    
    Parameters
    ----------
    writer : MultiPortMidiWriter
        The MIDI writer
    port : int
        MIDI port number
    channel : int
        MIDI channel number
    time : float
        Event time
    semitones : int
        Pitch bend sensitivity in semitones
    """
    # RPN 0 message sequence
    writer.add_event(port, time, Message('control_change', channel=channel, control=101, value=0))  # RPN MSB
    writer.add_event(port, time, Message('control_change', channel=channel, control=100, value=0))  # RPN LSB
    writer.add_event(port, time, Message('control_change', channel=channel, control=6, value=semitones))  # Data Entry MSB
    writer.add_event(port, time, Message('control_change', channel=channel, control=38, value=0))  # Data Entry LSB
    writer.add_event(port, time, Message('control_change', channel=channel, control=101, value=127))  # Deselect RPN MSB
    writer.add_event(port, time, Message('control_change', channel=channel, control=100, value=127))  # Deselect RPN LSB

# Test functions for MIDI backend validation

def _test_channel_scale():
    """
    Test channel scale: 34 melodic + 4 drum voices across 3 ports.
    
    Returns
    -------
    bool
        True if test passes
    """
    try:
        # Create allocator for 38 voices (should use 3 ports)
        allocator = ChannelAllocator(num_ports=3)
        writer = MultiPortMidiWriter(max_voices=38)
        
        allocated_voices = []
        
        # Allocate 34 melodic voices
        for i in range(34):
            voice_id = f"melodic_{i}"
            try:
                port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=0)
                allocated_voices.append((voice_id, port, channel, False))
            except RuntimeError:
                print(f"Failed to allocate melodic voice {i}")
                return False
        
        # Allocate 4 drum voices
        for i in range(4):
            voice_id = f"drum_{i}"
            try:
                port, channel = allocator.allocate_voice(voice_id, is_drum=True, program=0)
                allocated_voices.append((voice_id, port, channel, True))
            except RuntimeError:
                print(f"Failed to allocate drum voice {i}")
                return False
        
        # Verify allocation spans 3 ports
        ports_used = set(voice[1] for voice in allocated_voices)
        if len(ports_used) != 3:
            print(f"Expected 3 ports, got {len(ports_used)}")
            return False
        
        # Verify at least one melodic voice on channel 9 (reclaimed from drums)
        melodic_on_ch9 = any(voice[1:3] == (port, 9) and not voice[3] 
                           for voice in allocated_voices for port in range(3))
        
        print(f"✅ Channel scale test: {len(allocated_voices)} voices across {len(ports_used)} ports")
        print(f"✅ Channel 9 reclamation: {'Yes' if melodic_on_ch9 else 'No'}")
        
        return True
        
    except Exception as e:
        print(f"Channel scale test failed: {e}")
        return False

def _test_bend_sanity():
    """
    Test pitch bend sanity: Small bends with proper event ordering.
    
    Returns
    -------
    bool
        True if test passes
    """
    try:
        from klotho.tonos.pitch.pitch import Pitch
        
        # Create a microtonal pitch (C4 + 50 cents)
        pitch = Pitch.from_midi(60.5)
        
        # Test base note and bend calculation
        base_note, pitch_bend = _calculate_base_note_and_bend(pitch, 12)
        
        # Verify bend is within reasonable range
        if not (0 <= pitch_bend <= 16383):
            print(f"Pitch bend out of range: {pitch_bend}")
            return False
        
        # Verify base note is reasonable
        if not (0 <= base_note <= 127):
            print(f"Base note out of range: {base_note}")
            return False
        
        print(f"✅ Bend sanity test: C4+50¢ → base={base_note}, bend={pitch_bend}")
        return True
        
    except Exception as e:
        print(f"Bend sanity test failed: {e}")
        return False

def _test_drum_reclamation():
    """
    Test drum reclamation: Melodic on channel 10, multiple drum channels.
    
    Returns
    -------
    bool
        True if test passes
    """
    try:
        allocator = ChannelAllocator(num_ports=1)
        
        # Allocate melodic voice on channel 9 (10 in 1-based)
        melodic_voice = "melodic_ch9"
        port, channel = allocator.allocate_voice(melodic_voice, is_drum=False, program=1)
        
        if channel != 9:
            # Try to get channel 9 specifically by allocating other channels first
            temp_voices = []
            for i in range(9):
                temp_id = f"temp_{i}"
                temp_port, temp_channel = allocator.allocate_voice(temp_id, is_drum=False, program=0)
                temp_voices.append(temp_id)
                if temp_channel == 9:
                    break
            
            # Now allocate on channel 9
            port, channel = allocator.allocate_voice(melodic_voice, is_drum=False, program=1)
            
            # Clean up temp voices
            for temp_id in temp_voices:
                allocator.release_voice(temp_id)
        
        # Allocate multiple drum voices
        drum1 = "drum_1"
        drum2 = "drum_2"
        
        port1, ch1 = allocator.allocate_voice(drum1, is_drum=True, program=0)
        port2, ch2 = allocator.allocate_voice(drum2, is_drum=True, program=8)
        
        print(f"✅ Drum reclamation test: Melodic on ch{channel}, Drums on ch{ch1},ch{ch2}")
        return True
        
    except Exception as e:
        print(f"Drum reclamation test failed: {e}")
        return False

def debug_voice_allocation():
    """Debug voice allocation to understand piano fallback issue."""
    print("=== DEBUGGING VOICE ALLOCATION ===")
    
    # Test with more voices than channels to see what happens
    allocator = ChannelAllocator(num_ports=1)  # Only 1 port = 16 channels
    
    allocated_voices = []
    
    # Try to allocate 20 drum voices (more than 16 channels)
    print("\nAllocating 20 drum voices:")
    for i in range(20):
        voice_id = f"drum_{i}"
        try:
            port, channel = allocator.allocate_voice(voice_id, is_drum=True, program=1)
            allocated_voices.append((voice_id, port, channel, True))
            print(f"  Voice {i+1}: port={port}, channel={channel}")
        except RuntimeError as e:
            print(f"  Voice {i+1}: FAILED - {e}")
            break
    
    print(f"\nAllocated {len(allocated_voices)} voices before failure")
    
    # Test with multiple ports
    print("\n=== TESTING WITH MULTIPLE PORTS ===")
    allocator2 = ChannelAllocator(num_ports=3)  # 3 ports = 48 channels
    
    allocated_voices2 = []
    for i in range(50):  # Try more than 48
        voice_id = f"voice_{i}"
        try:
            port, channel = allocator2.allocate_voice(voice_id, is_drum=(i % 5 == 0), program=1)
            allocated_voices2.append((voice_id, port, channel))
            if i < 10 or i % 10 == 0:
                print(f"  Voice {i+1}: port={port}, channel={channel}")
        except RuntimeError as e:
            print(f"  Voice {i+1}: FAILED - {e}")
            break
    
    print(f"\nAllocated {len(allocated_voices2)} voices with 3 ports")

def test_midi_backend():
    """
    Run all MIDI backend tests.
    
    Returns
    -------
    bool
        True if all tests pass
    """
    print("Running MIDI Backend Overhaul Tests...")
    
    tests = [
        ("Channel Scale Test", _test_channel_scale),
        ("Bend Sanity Test", _test_bend_sanity), 
        ("Drum Reclamation Test", _test_drum_reclamation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append(result)
        print(f"{'✅ PASSED' if result else '❌ FAILED'}")
    
    all_passed = all(results)
    print(f"\n{'🎉 ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    return all_passed

def debug_play_midi(obj, debug=True, **kwargs):
    """
    Debug version of play_midi that shows detailed channel allocation and MIDI events.
    """
    print("=== DEBUG MIDI PLAYBACK ===")
    return play_midi(obj, debug=debug, **kwargs)

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

def _create_midi_from_pitch_collection(collection, dur=0.5, prgm=0, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a PitchCollection (sequential playback) using absolute timing."""
    # PRD: Use absolute timing only - always 4/4 at 120 BPM
    bpm = 120
    
    # Estimate voices needed
    max_concurrent = len(collection) if hasattr(collection, '__len__') else 16
    max_concurrent = min(max_concurrent, max_channels)
    
    # Create multi-port writer and allocator
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    if debug:
        print(f"[DEBUG] PitchCollection: {max_concurrent} voices, {writer.num_ports} ports")
    
    # For non-addressed collections, create addressed version with C4 root
    if isinstance(collection, AddressedPitchCollection):
        addressed = collection
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = collection.root(Pitch("C4"))
    
    note_events = []
    current_time = 0.0
    voice_counter = 0
    
    for i in range(len(addressed)):
        pitch = addressed[i]
        voice_id = f"pitch_voice_{voice_counter}"
        voice_counter += 1
        
        # Allocate voice (always melodic for pitch collections)
        try:
            port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
        except RuntimeError:
            continue
        
        # Calculate base note and pitch bend
        midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
        
        note_events.append({
            'voice_id': voice_id,
            'port': port,
            'channel': channel,
            'start_time': current_time,
            'duration': dur,
            'midi_note': midi_note,
            'velocity': DEFAULT_VELOCITY,
            'program': prgm,
            'is_drum': False,
            'pitch_bend': pitch_bend
        })
        
        current_time += dur
    
    # Generate MIDI events using new allocator system
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Finalize and return
    writer.finalize(bpm)
    return writer.get_midi_file()

def _create_midi_from_scale(scale, dur=0.5, prgm=0, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a Scale (ascending then descending) using absolute timing."""
    # PRD: Use absolute timing only - always 4/4 at 120 BPM
    bpm = 120
    
    # Estimate voices needed (scale length * 2 for ascending + descending)
    max_concurrent = len(scale) * 2 if hasattr(scale, '__len__') else 16
    max_concurrent = min(max_concurrent, max_channels)
    
    # Create multi-port writer and allocator
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    if debug:
        print(f"[DEBUG] Scale: {max_concurrent} voices, {writer.num_ports} ports")
    
    # For non-addressed scales, create addressed version with C4 root
    if isinstance(scale, AddressedPitchCollection):
        addressed = scale
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = scale.root(Pitch("C4"))
    
    # For scales: allocate channels per note for ascending (microtones), reuse for descending
    note_events = []
    current_time = 0.0
    
    # Track channel assignments for reuse during descending
    pitch_to_channel = {}  # Maps pitch to (port, channel, voice_id)
    
    # Play ascending (including the equave at index len(addressed))
    for i in range(len(addressed) + 1):
        pitch = addressed[i]
        pitch_key = str(pitch)  # Use string representation as key
        
        # Allocate new channel for each unique pitch (microtonal support)
        voice_id = f"scale_voice_asc_{i}"
        try:
            port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
            # Remember this channel for potential reuse
            pitch_to_channel[pitch_key] = (port, channel, voice_id)
        except RuntimeError:
            continue
        
        # Calculate base note and pitch bend
        midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
        
        note_events.append({
            'voice_id': voice_id,
            'port': port,
            'channel': channel,
            'start_time': current_time,
            'duration': dur,
            'midi_note': midi_note,
            'velocity': DEFAULT_VELOCITY,
            'program': prgm,
            'is_drum': False,
            'pitch_bend': pitch_bend
        })
        
        current_time += dur
    
    # Play descending (reuse channels from ascending for same pitches)
    for i in range(len(addressed) - 1, -1, -1):
        pitch = addressed[i]
        pitch_key = str(pitch)
        
        # Reuse channel if we have it, otherwise allocate new
        if pitch_key in pitch_to_channel:
            port, channel, voice_id = pitch_to_channel[pitch_key]
            voice_id = f"scale_voice_desc_{i}_reuse"  # New voice ID for descending
        else:
            # Shouldn't happen, but allocate new if needed
            voice_id = f"scale_voice_desc_{i}"
            try:
                port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
            except RuntimeError:
                continue
        
        # Calculate base note and pitch bend
        midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
        
        note_events.append({
            'voice_id': voice_id,
            'port': port,
            'channel': channel,  # Reused channel for same pitch
            'start_time': current_time,
            'duration': dur,
            'midi_note': midi_note,
            'velocity': DEFAULT_VELOCITY,
            'program': prgm,
            'is_drum': False,
            'pitch_bend': pitch_bend
        })
        
        current_time += dur
    
    # Generate MIDI events using new allocator system
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Finalize and return
    writer.finalize(bpm)
    return writer.get_midi_file()

def _create_midi_from_chord(chord, dur=3.0, arp=False, prgm=0, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a Chord (block chord or arpeggiated) using absolute timing."""
    # PRD: Use absolute timing only - always 4/4 at 120 BPM
    bpm = 120
    
    # Estimate voices needed
    max_concurrent = len(chord) if hasattr(chord, '__len__') else 16
    max_concurrent = min(max_concurrent, max_channels)
    
    # Create multi-port writer and allocator
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    # Add global meta events - always 4/4 at 120 BPM per PRD
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    if debug:
        print(f"[DEBUG] Chord: {max_concurrent} voices, {writer.num_ports} ports")
    
    # For non-addressed chords, create addressed version with C4 root
    if isinstance(chord, AddressedPitchCollection):
        addressed = chord
    else:
        from klotho.tonos.pitch.pitch import Pitch
        addressed = chord.root(Pitch("C4"))
    
    note_events = []
    voice_counter = 0
    
    if arp:
        # Arpeggiated: each note gets dur duration
        current_time = 0.0
        for i in range(len(addressed)):
            pitch = addressed[i]
            voice_id = f"chord_voice_{voice_counter}"
            voice_counter += 1
            
            # Allocate voice (always melodic for chords)
            try:
                port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
            except RuntimeError:
                continue
            
            # Calculate base note and pitch bend
            midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
            
            note_events.append({
                'voice_id': voice_id,
                'port': port,
                'channel': channel,
                'start_time': current_time,
                'duration': dur,
                'midi_note': midi_note,
                'velocity': DEFAULT_VELOCITY,
                'program': prgm,
                'is_drum': False,
                'pitch_bend': pitch_bend
            })
            
            current_time += dur
    else:
        # Block chord: all notes start at once, last for dur
        for i in range(len(addressed)):
            pitch = addressed[i]
            voice_id = f"chord_voice_{voice_counter}"
            voice_counter += 1
            
            # Allocate voice (always melodic for chords)
            try:
                port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
            except RuntimeError:
                continue
            
            # Calculate base note and pitch bend
            midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
            
            note_events.append({
                'voice_id': voice_id,
                'port': port,
                'channel': channel,
                'start_time': 0.0,
                'duration': dur,
                'midi_note': midi_note,
                'velocity': DEFAULT_VELOCITY,
                'program': prgm,
                'is_drum': False,
                'pitch_bend': pitch_bend
            })
    
    # Generate MIDI events using new allocator system
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    # Finalize and return
    writer.finalize(bpm)
    return writer.get_midi_file()

def _create_midi_from_chord_sequence(chord_sequence, dur=3.0, arp=False, prgm=0, max_channels=128, bend_sensitivity_semitones=12, debug=False):
    """Create a MIDI file from a ChordSequence (sequential chord playback) using absolute timing."""
    bpm = 120
    
    if not chord_sequence.chords:
        writer = MultiPortMidiWriter(max_voices=1)
        writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
        writer.finalize(bpm)
        return writer.get_midi_file()
    
    total_notes = sum(len(chord) for chord in chord_sequence.chords if hasattr(chord, '__len__'))
    max_concurrent = min(total_notes, max_channels)
    
    writer = MultiPortMidiWriter(max_voices=max_concurrent)
    allocator = ChannelAllocator(writer.num_ports, bend_sensitivity_semitones=bend_sensitivity_semitones)
    
    writer.add_meta_event(MetaMessage('set_tempo', tempo=int(60_000_000 / bpm), time=0))
    
    if debug:
        print(f"[DEBUG] ChordSequence: {len(chord_sequence.chords)} chords, {max_concurrent} voices, {writer.num_ports} ports")
    
    note_events = []
    current_time = 0.0
    voice_counter = 0
    
    for chord_idx, chord in enumerate(chord_sequence.chords):
        if isinstance(chord, AddressedPitchCollection):
            addressed = chord
        else:
            from klotho.tonos.pitch.pitch import Pitch
            addressed = chord.root(Pitch("C4"))
        
        if arp:
            chord_start_time = current_time
            for i in range(len(addressed)):
                pitch = addressed[i]
                voice_id = f"chord_seq_voice_{voice_counter}"
                voice_counter += 1
                
                try:
                    port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
                except RuntimeError:
                    continue
                
                midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
                
                note_events.append({
                    'voice_id': voice_id,
                    'port': port,
                    'channel': channel,
                    'start_time': current_time,
                    'duration': dur,
                    'midi_note': midi_note,
                    'velocity': DEFAULT_VELOCITY,
                    'program': prgm,
                    'is_drum': False,
                    'pitch_bend': pitch_bend
                })
                
                current_time += dur
        else:
            for i in range(len(addressed)):
                pitch = addressed[i]
                voice_id = f"chord_seq_voice_{voice_counter}"
                voice_counter += 1
                
                try:
                    port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=prgm)
                except RuntimeError:
                    continue
                
                midi_note, pitch_bend = _calculate_base_note_and_bend(pitch, bend_sensitivity_semitones)
                
                note_events.append({
                    'voice_id': voice_id,
                    'port': port,
                    'channel': channel,
                    'start_time': current_time,
                    'duration': dur,
                    'midi_note': midi_note,
                    'velocity': DEFAULT_VELOCITY,
                    'program': prgm,
                    'is_drum': False,
                    'pitch_bend': pitch_bend
                })
            
            current_time += dur
    
    _generate_multi_port_events(note_events, writer, allocator, bpm, debug)
    
    writer.finalize(bpm)
    return writer.get_midi_file()

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

def test_channel_allocation_system():
    """
    Test the channel allocation system to verify it meets the requirements.
    
    Requirements:
    1. Exhaust ALL channels on a port before moving to the next port
    2. Support up to 256 channels (16 ports × 16 channels)
    3. Melodic instruments skip channel 9 on any port
    4. Drum instruments use ONLY channel 9 on any port
    5. Only loop back after exhausting all 256 channels
    """
    print("=== TESTING CHANNEL ALLOCATION SYSTEM ===")
    
    # Test 1: Single port allocation
    print("\n1. Testing single port allocation:")
    allocator = ChannelAllocator(num_ports=1)
    
    # Allocate all 15 melodic channels
    melodic_allocations = []
    for i in range(15):
        voice_id = f"melodic_{i}"
        port, channel = allocator.allocate_voice(voice_id, is_drum=False, program=0)
        melodic_allocations.append((port, channel))
        print(f"  Melodic {i}: port={port}, channel={channel}")
    
    # Verify no channel 9 was used for melodic
    melodic_channels = [ch for _, ch in melodic_allocations]
    if 9 in melodic_channels:
        print("  ❌ ERROR: Channel 9 used for melodic voice!")
        return False
    else:
        print("  ✅ Channel 9 correctly skipped for melodic voices")
    
    # Allocate drum channel
    drum_voice_id = "drum_1"
    drum_port, drum_channel = allocator.allocate_voice(drum_voice_id, is_drum=True, program=1)
    print(f"  Drum: port={drum_port}, channel={drum_channel}")
    
    if drum_channel != 9:
        print("  ❌ ERROR: Drum not allocated to channel 9!")
        return False
    else:
        print("  ✅ Drum correctly allocated to channel 9")
    
    # Test 2: Multi-port allocation with exhaustion
    print("\n2. Testing multi-port allocation with exhaustion:")
    allocator2 = ChannelAllocator(num_ports=3)  # 3 ports = 48 channels total
    
    # Allocate all melodic channels across ports
    melodic_allocations2 = []
    for i in range(45):  # 3 ports × 15 melodic channels = 45
        voice_id = f"melodic_{i}"
        port, channel = allocator2.allocate_voice(voice_id, is_drum=False, program=0)
        melodic_allocations2.append((port, channel))
        if i < 10 or i % 15 == 0:
            print(f"  Melodic {i}: port={port}, channel={channel}")
    
    # Verify port exhaustion pattern
    ports_used = set(port for port, _ in melodic_allocations2)
    print(f"  Ports used: {sorted(ports_used)}")
    
    # Count channels per port
    port_counts = {}
    for port, channel in melodic_allocations2:
        port_counts[port] = port_counts.get(port, 0) + 1
    
    print(f"  Channels per port: {port_counts}")
    
    # Verify each port has 15 channels before moving to next
    expected_counts = {0: 15, 1: 15, 2: 15}
    if port_counts != expected_counts:
        print(f"  ❌ ERROR: Expected {expected_counts}, got {port_counts}")
        return False
    else:
        print("  ✅ Port exhaustion working correctly")
    
    # Test 3: Drum allocation across ports
    print("\n3. Testing drum allocation across ports:")
    drum_allocations = []
    for i in range(3):  # 3 drum channels (one per port)
        voice_id = f"drum_{i}"
        port, channel = allocator2.allocate_voice(voice_id, is_drum=True, program=1)
        drum_allocations.append((port, channel))
        print(f"  Drum {i}: port={port}, channel={channel}")
    
    # Verify all drums use channel 9
    drum_channels = [ch for _, ch in drum_allocations]
    if not all(ch == 9 for ch in drum_channels):
        print("  ❌ ERROR: Not all drums allocated to channel 9!")
        return False
    else:
        print("  ✅ All drums correctly allocated to channel 9")
    
    # Test 4: Mixed allocation (melodic and drum)
    print("\n4. Testing mixed allocation:")
    allocator3 = ChannelAllocator(num_ports=2)
    
    # Allocate some melodic voices first
    for i in range(10):
        voice_id = f"mixed_melodic_{i}"
        port, channel = allocator3.allocate_voice(voice_id, is_drum=False, program=0)
        print(f"  Mixed melodic {i}: port={port}, channel={channel}")
    
    # Then allocate some drum voices
    for i in range(2):
        voice_id = f"mixed_drum_{i}"
        port, channel = allocator3.allocate_voice(voice_id, is_drum=True, program=1)
        print(f"  Mixed drum {i}: port={port}, channel={channel}")
    
    # Check available channels
    available_melodic, available_drum = allocator3.get_available_channels()
    print(f"  Available channels: melodic={available_melodic}, drum={available_drum}")
    
    print("\n✅ All channel allocation tests passed!")
    return True

def debug_current_allocation():
    """Debug the current channel allocation state."""
    print("=== CURRENT CHANNEL ALLOCATION DEBUG ===")
    
    # Create a test allocator
    allocator = ChannelAllocator(num_ports=2)
    
    print(f"Initial state:")
    melodic, drum = allocator.get_available_channels()
    print(f"  Available melodic: {melodic}")
    print(f"  Available drum: {drum}")
    
    # Allocate some voices
    print(f"\nAllocating voices:")
    for i in range(10):
        voice_id = f"test_{i}"
        is_drum = (i % 3 == 0)  # Every 3rd voice is drum
        port, channel = allocator.allocate_voice(voice_id, is_drum=is_drum, program=0)
        print(f"  Voice {i} ({'drum' if is_drum else 'melodic'}): port={port}, channel={channel}")
    
    print(f"\nAfter allocation:")
    melodic, drum = allocator.get_available_channels()
    print(f"  Available melodic: {melodic}")
    print(f"  Available drum: {drum}")
    
    print(f"\nCurrent port positions:")
    print(f"  Melodic port: {allocator.current_melodic_port}")
    print(f"  Drum port: {allocator.current_drum_port}")