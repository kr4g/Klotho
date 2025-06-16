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
    
    def free_node(self, uid: str):
        event = {
            "type": "free",
            "id": uid
        }
        heapq.heappush(self.events, (0, 0, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
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