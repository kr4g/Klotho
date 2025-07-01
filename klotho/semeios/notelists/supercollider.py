"""
Scheduler: A module for scheduling musical events and nodes.

Provides the Scheduler class for managing timed musical events 
with priority-based scheduling.
"""

from uuid import uuid4
import heapq
import json
import os
from typing import Union

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.chronos.temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock

class Scheduler:
    def __init__(self):
        self.events = []
        self.total_events = 0
        self.event_counter = 0  # sorting for final tiebreaker
        
    def new_node(self, synth_name: str, start: float = 0, dur: Union[float, None] = None, group: str = None, **pfields):
        uid = str(uuid4()).replace('-', '')
        
        event = {
            "type": "new",
            "id": uid,
            "synthName": synth_name,
            "start": start,
            "pfields": pfields
        }
        
        if group:
            event["group"] = group
        else:
            event["group"] = "default"
            
        priority = 0 # higher priority
        heapq.heappush(self.events, (start, priority, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
        if dur:
            self.set_node(uid, start = start + dur, gate = 0)
        
        return uid

    def set_node(self, uid: str, start: float, **pfields):
        event = {
            "type": "set",
            "id": uid,
            "start": start,
            "pfields": pfields
        }
        
        priority = 1 # lower priority
        heapq.heappush(self.events, (start, priority, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
    def add(self, uc: Union[CompositionalUnit, TemporalUnit, TemporalUnitSequence, TemporalBlock]):
        
        if isinstance(uc, TemporalUnitSequence):
            for unit in uc:
                self.add(unit)
            return
        elif isinstance(uc, TemporalBlock):
            for unit in uc:
                self.add(unit)
            return
        
        slur_uids = {}
        
        for event in uc:
            if event.is_rest:
                continue
                
            event_synth_name = event.get_parameter('synth_name') or event.get_parameter('synthName')
            if not event_synth_name:
                continue
            
            is_slur_start = event.get_parameter('_slur_start', 0)
            is_slur_end = event.get_parameter('_slur_end', 0)
            slur_id = event.get_parameter('_slur_id')
            
            event_group = event.get_parameter('group')
            pfields = {k: v for k, v in event.parameters.items() 
                      if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}
            
            if is_slur_start:
                instrument = uc._pt.get_active_instrument(event.node_id)
                if instrument:
                    env_type = getattr(instrument, 'env_type', None) or ''
                    if env_type and env_type.lower() in ('standard', 'std'):
                        sustain_param = None
                        for param in ['sustaintime', 'releasetime']:
                            if param in [k.lower() for k in instrument.keys()]:
                                sustain_param = next(k for k in instrument.keys() if k.lower() == param)
                                break
                        
                        if sustain_param:
                            end_event = next(e for e in uc._events if e.get_parameter('_slur_id') == slur_id and e.get_parameter('_slur_end'))
                            total_duration = end_event.end - event.start
                            pfields[sustain_param] = total_duration
                
                slur_uid = self.new_node(
                    synth_name=event_synth_name,
                    start=event.start,
                    group=event_group,
                    **pfields
                )
                slur_uids[slur_id] = slur_uid
            elif slur_id is not None:
                self.set_node(slur_uids[slur_id], start=event.start, **pfields)
                if is_slur_end:
                    instrument = uc._pt.get_active_instrument(event.node_id)
                    if instrument and hasattr(instrument, 'env_type'):
                        env_type = getattr(instrument, 'env_type', '') or ''
                        if env_type.lower() in ('sustained', 'sus'):
                            self.set_node(slur_uids[slur_id], start=event.end, gate=0)
            else:
                uid = self.new_node(
                    synth_name=event_synth_name,
                    start=event.start,
                    group=event_group,
                    **pfields
                )
                if getattr(uc._pt.get_active_instrument(event.node_id), 'env_type').lower() in ('sustained', 'sus'):
                    self.set_node(uid, start=event.end, gate=0)
            
    def clear_events(self):
        self.events = []
        self.total_events = 0
        self.event_counter = 0
        
    def write(self, filepath, start_time: Union[float, None] = None, time_scale: float = 1.0):
        sorted_events = []
        events_copy = self.events.copy()
        
        if events_copy:
            if start_time is not None:
                min_start = min(start for start, _, _, _, _ in events_copy)
                time_shift = start_time - min_start
            else:
                time_shift = 0
            
            while events_copy:
                start, _, _, _, event = heapq.heappop(events_copy)
                new_start = (start + time_shift) * time_scale
                event["start"] = new_start
                sorted_events.append(event)
            
        try:
            with open(filepath, 'w') as f:
                json.dump(sorted_events, f, indent=2)
            print(f"Successfully wrote {self.total_events} events to {os.path.abspath(filepath)}")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
