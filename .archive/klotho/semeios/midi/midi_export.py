import mido
from typing import Union, List
from pathlib import Path

def midi(obj: Union['TemporalUnit', 'TemporalUnitSequence', 'TemporalBlock'], 
         file_path: Union[str, Path], 
         ticks_per_beat: int = 480,
         default_velocity: int = 64,
         middle_c: int = 60) -> None:
    
    file_path = Path(file_path)
    if file_path.suffix != '.mid':
        file_path = file_path.with_suffix('.mid')
    
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    
    if hasattr(obj, 'events'):
        _add_temporal_unit_track(mid, obj, default_velocity, middle_c, ticks_per_beat)
    elif hasattr(obj, 'seq'):
        _add_temporal_sequence_track(mid, obj, default_velocity, middle_c, ticks_per_beat)
    elif hasattr(obj, 'rows'):
        _add_temporal_block_tracks(mid, obj, default_velocity, middle_c, ticks_per_beat)
    else:
        raise ValueError(f"Unsupported object type: {type(obj)}")
    
    mid.save(file_path)

def _add_temporal_unit_track(mid: mido.MidiFile, 
                           temporal_unit: 'TemporalUnit',
                           default_velocity: int,
                           middle_c: int,
                           ticks_per_beat: int) -> None:
    
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    events = temporal_unit.events
    absolute_offset = temporal_unit.offset
    
    previous_time = 0
    
    for _, event in events.iterrows():
        if event['is_rest']:
            continue
            
        start_time = event['start'] + absolute_offset
        duration = abs(event['duration'])
        
        note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
        note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
        
        track.append(mido.Message('note_on', 
                                 channel=0, 
                                 note=middle_c, 
                                 velocity=default_velocity, 
                                 time=note_on_delta))
        
        track.append(mido.Message('note_off', 
                                 channel=0, 
                                 note=middle_c, 
                                 velocity=0, 
                                 time=note_off_delta))
        
        previous_time = start_time + duration

def _add_temporal_sequence_track(mid: mido.MidiFile,
                               temporal_sequence: 'TemporalUnitSequence',
                               default_velocity: int,
                               middle_c: int,
                               ticks_per_beat: int) -> None:
    
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    absolute_offset = temporal_sequence.offset
    previous_time = 0
    
    for temporal_unit in temporal_sequence.seq:
        events = temporal_unit.events
        unit_offset = temporal_unit.offset
        
        for _, event in events.iterrows():
            if event['is_rest']:
                continue
                
            start_time = event['start'] + unit_offset + absolute_offset
            duration = abs(event['duration'])
            
            note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
            note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
            
            track.append(mido.Message('note_on', 
                                     channel=0, 
                                     note=middle_c, 
                                     velocity=default_velocity, 
                                     time=note_on_delta))
            
            track.append(mido.Message('note_off', 
                                     channel=0, 
                                     note=middle_c, 
                                     velocity=0, 
                                     time=note_off_delta))
            
            previous_time = start_time + duration

def _add_temporal_block_tracks(mid: mido.MidiFile,
                             temporal_block: 'TemporalBlock',
                             default_velocity: int,
                             middle_c: int,
                             ticks_per_beat: int) -> None:
    
    absolute_offset = temporal_block.offset
    
    for row_idx, row in enumerate(temporal_block.rows):
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        previous_time = 0
        
        if hasattr(row, 'events'):
            events = row.events
            unit_offset = row.offset
            
            for _, event in events.iterrows():
                if event['is_rest']:
                    continue
                    
                start_time = event['start'] + unit_offset + absolute_offset
                duration = abs(event['duration'])
                
                note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
                note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
                
                track.append(mido.Message('note_on', 
                                         channel=0, 
                                         note=middle_c + row_idx, 
                                         velocity=default_velocity, 
                                         time=note_on_delta))
                
                track.append(mido.Message('note_off', 
                                         channel=0, 
                                         note=middle_c + row_idx, 
                                         velocity=0, 
                                         time=note_off_delta))
                
                previous_time = start_time + duration
                
        elif hasattr(row, 'seq'):
            for temporal_unit in row.seq:
                events = temporal_unit.events
                unit_offset = temporal_unit.offset
                
                for _, event in events.iterrows():
                    if event['is_rest']:
                        continue
                        
                    start_time = event['start'] + unit_offset + absolute_offset
                    duration = abs(event['duration'])
                    
                    note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
                    note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
                    
                    track.append(mido.Message('note_on', 
                                             channel=0, 
                                             note=middle_c + row_idx, 
                                             velocity=default_velocity, 
                                             time=note_on_delta))
                    
                    track.append(mido.Message('note_off', 
                                             channel=0, 
                                             note=middle_c + row_idx, 
                                             velocity=0, 
                                             time=note_off_delta))
                    
                    previous_time = start_time + duration
                    
        elif hasattr(row, 'rows'):
            _add_temporal_block_tracks_recursive(track, row, absolute_offset, 
                                               default_velocity, middle_c + row_idx, 
                                               ticks_per_beat, previous_time)

def _add_temporal_block_tracks_recursive(track: mido.MidiTrack,
                                       temporal_block: 'TemporalBlock',
                                       absolute_offset: float,
                                       default_velocity: int,
                                       note_offset: int,
                                       ticks_per_beat: int,
                                       previous_time: float) -> float:
    
    block_offset = temporal_block.offset
    
    for sub_row_idx, sub_row in enumerate(temporal_block.rows):
        if hasattr(sub_row, 'events'):
            events = sub_row.events
            unit_offset = sub_row.offset
            
            for _, event in events.iterrows():
                if event['is_rest']:
                    continue
                    
                start_time = event['start'] + unit_offset + block_offset + absolute_offset
                duration = abs(event['duration'])
                
                note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
                note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
                
                track.append(mido.Message('note_on', 
                                         channel=0, 
                                         note=note_offset + sub_row_idx, 
                                         velocity=default_velocity, 
                                         time=note_on_delta))
                
                track.append(mido.Message('note_off', 
                                         channel=0, 
                                         note=note_offset + sub_row_idx, 
                                         velocity=0, 
                                         time=note_off_delta))
                
                previous_time = start_time + duration
                
        elif hasattr(sub_row, 'seq'):
            for temporal_unit in sub_row.seq:
                events = temporal_unit.events
                unit_offset = temporal_unit.offset
                
                for _, event in events.iterrows():
                    if event['is_rest']:
                        continue
                        
                    start_time = event['start'] + unit_offset + block_offset + absolute_offset
                    duration = abs(event['duration'])
                    
                    note_on_delta = _seconds_to_ticks(start_time - previous_time, ticks_per_beat, 120)
                    note_off_delta = _seconds_to_ticks(duration, ticks_per_beat, 120)
                    
                    track.append(mido.Message('note_on', 
                                             channel=0, 
                                             note=note_offset + sub_row_idx, 
                                             velocity=default_velocity, 
                                             time=note_on_delta))
                    
                    track.append(mido.Message('note_off', 
                                             channel=0, 
                                             note=note_offset + sub_row_idx, 
                                             velocity=0, 
                                             time=note_off_delta))
                    
                    previous_time = start_time + duration
    
    return previous_time

def _seconds_to_ticks(seconds: float, ticks_per_beat: int, bpm: int) -> int:
    if seconds <= 0:
        return 0
    beats_per_second = bpm / 60.0
    beats = seconds * beats_per_second
    ticks = int(beats * ticks_per_beat)
    return max(0, ticks) 