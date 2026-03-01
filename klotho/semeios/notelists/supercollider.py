"""
Scheduler for SuperCollider event export.

Provides the ``Scheduler`` class for building priority-ordered event
lists that can be serialized to JSON for playback in SuperCollider.
"""

from uuid import uuid4
import heapq
import json
import os
from typing import Union

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.chronos.temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock

ENV_TYPES = {
    'gated': ('sustained', 'sus', 'asr', 'adsr'),
    'ungated': ('standard', 'std', 'perc', 'linen'),
}

class Scheduler:
    """Priority-queue based scheduler for SuperCollider synth events.

    Manages a heap of timed events (``new``, ``set``, ``release``) that are
    sorted by start time and priority, then serialized to a JSON file
    consumable by a SuperCollider playback engine.

    Attributes
    ----------
    events : list
        Min-heap of ``(start, priority, uid, counter, event_dict)`` tuples.
    total_events : int
        Cumulative number of events pushed onto the heap.
    event_counter : int
        Monotonic counter used as a tiebreaker when start time and
        priority are equal.
    meta : dict
        Metadata dictionary (synth groups, insert effects, etc.) written
        alongside events.
    """

    def __init__(self):
        self.events = []
        self.total_events = 0
        self.event_counter = 0  # sorting for final tiebreaker
        self.meta = {}
        
    def new_node(self, synth_name: str, start: float = 0, dur: Union[float, None] = None, group: str = None, **pfields):
        """Create a new synth node event.

        Pushes a ``"new"`` event onto the scheduler heap.  If *dur* is
        provided, a corresponding ``"set"`` event with ``gate=0`` is
        automatically scheduled at ``start + dur``.

        Parameters
        ----------
        synth_name : str
            Name of the SuperCollider SynthDef to instantiate.
        start : float, optional
            Start time in seconds (default ``0``).
        dur : float or None, optional
            Duration in seconds.  When given, the node is automatically
            released after this period.
        group : str or None, optional
            Synth group name.  Defaults to ``"default"``.
        **pfields
            Arbitrary parameter fields forwarded to the synth.

        Returns
        -------
        str
            Unique identifier for the created node.
        """
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
        """Schedule a parameter-update event on an existing node.

        Parameters
        ----------
        uid : str
            Unique identifier of the target node.
        start : float
            Time in seconds at which the update takes effect.
        **pfields
            Parameter fields to set on the node.
        """
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
    
    def release_node(self, uid: str, start: float):
        """Schedule a release event for a gated synth node.

        Parameters
        ----------
        uid : str
            Unique identifier of the node to release.
        start : float
            Time in seconds at which the release occurs.
        """
        event = {
            "type": "release",
            "id": uid,
            "start": start
        }
        priority = 1
        heapq.heappush(self.events, (start, priority, uid, self.event_counter, event))
        self.event_counter += 1
        self.total_events += 1
        
    def add(self, uc: Union[CompositionalUnit, TemporalUnit, TemporalUnitSequence, TemporalBlock]):
        """Add events from a compositional or temporal structure.

        Iterates over the chronons in *uc*, creating ``new_node``,
        ``set_node``, and ``release_node`` events as appropriate based on
        envelope type (gated vs. ungated) and slur markings.

        Parameters
        ----------
        uc : CompositionalUnit, TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The musical structure whose events should be scheduled.
            Sequences and blocks are recursively expanded.
        """
        
        if isinstance(uc, TemporalUnitSequence):
            for unit in uc:
                self.add(unit)
            return
        elif isinstance(uc, TemporalBlock):
            for unit in uc:
                self.add(unit)
            return
        
        slur_end_events = {}
        sustain_param_cache = {}
        events_iterable = uc
        if isinstance(uc, CompositionalUnit):
            events_iterable = tuple(uc)
            for event in events_iterable:
                if event.is_rest:
                    continue
                slur_id = event.get_parameter('_slur_id')
                if slur_id is None:
                    continue
                if event.get_parameter('_slur_end', 0):
                    slur_end_events[slur_id] = event

        slur_uids = {}
        
        for event in events_iterable:
            if event.is_rest:
                continue
                
            event_synth_name = event.get_parameter('synth_name') or event.get_parameter('synthName')
            if not event_synth_name:
                continue
            
            is_slur_start = event.get_parameter('_slur_start', 0)
            is_slur_end = event.get_parameter('_slur_end', 0)
            slur_id = event.get_parameter('_slur_id')
            
            event_group = event.get_parameter('group')
            pfields = {k: v for k, v in event.pfields.items() 
                      if k not in ('synth_name', 'synthName', 'group', '_slur_start', '_slur_end', '_slur_id')}
            
            if is_slur_start:
                instrument = uc.get_instrument(event.node_id)
                if instrument:
                    env_type = getattr(instrument, 'env_type', None) or ''
                    if env_type and env_type.lower() in ENV_TYPES['ungated']:
                        instrument_id = id(instrument)
                        sustain_param = sustain_param_cache.get(instrument_id)
                        if instrument_id not in sustain_param_cache:
                            sustain_param = None
                            lower_to_key = {k.lower(): k for k in instrument.keys()}
                            for param in ['sustaintime', 'releasetime']:
                                if param in lower_to_key:
                                    sustain_param = lower_to_key[param]
                                    break
                            sustain_param_cache[instrument_id] = sustain_param
                        
                        if sustain_param:
                            end_event = slur_end_events.get(slur_id)
                            if end_event is not None:
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
                    instrument = uc.get_instrument(event.node_id)
                    if instrument and hasattr(instrument, 'env_type'):
                        env_type = getattr(instrument, 'env_type', '') or ''
                        if env_type.lower() in ENV_TYPES['gated']:
                            self.set_node(slur_uids[slur_id], start=event.end, gate=0)
            else:
                uid = self.new_node(
                    synth_name=event_synth_name,
                    start=event.start,
                    group=event_group,
                    **pfields
                )
                instrument = uc.get_instrument(event.node_id)
                env_type = getattr(instrument, 'env_type', '') if instrument is not None else ''
                if env_type.lower() in ENV_TYPES['gated']:
                    self.release_node(uid, start=event.end)
            
    def synth_groups(self, groups):
        """Register one or more synth group names in the scheduler metadata.

        Parameters
        ----------
        groups : str or list of str
            Group name(s) to register.  ``"main"`` is reserved and will
            raise a ``ValueError``.

        Raises
        ------
        ValueError
            If any group is named ``"main"``.
        """
        if 'groups' not in self.meta:
            self.meta['groups'] = []
        
        if isinstance(groups, str):
            groups = [groups]
        
        for group in groups:
            if group == "main":
                raise ValueError("Group name 'main' is not allowed")
            if group not in self.meta['groups']:
                self.meta['groups'].append(group)
    
    def group_inserts(self, inserts):
        """Assign insert-effect mappings to registered synth groups.

        Parameters
        ----------
        inserts : dict
            Mapping of group names to their insert-effect configurations.

        Raises
        ------
        ValueError
            If ``synth_groups`` has not been called first.
        """
        if 'groups' not in self.meta:
            raise ValueError("Must add groups before adding inserts")
        # self.synth_groups(inserts.keys())
        
        if 'inserts' not in self.meta:
            self.meta['inserts'] = []

        self.meta['inserts'] = inserts
        # if isinstance(inserts, dict):
        #     inserts = [inserts]
        
        # for insert in inserts:
        #     for group_name in insert.keys():
        #         if group_name not in self.meta['groups'] and group_name != "main":
        #             raise ValueError(f"Group '{group_name}' not found in groups list")
        #     self.meta['inserts'].append(insert)
    
    def clear_events(self):
        """Remove all scheduled events and reset counters."""
        self.events = []
        self.total_events = 0
        self.event_counter = 0
        
    def write(self, filepath, start_time: Union[float, None] = None, time_scale: float = 1.0):
        """Serialize all scheduled events to a JSON file.

        Events are sorted by start time, optionally shifted and scaled,
        then written alongside the scheduler metadata.

        Parameters
        ----------
        filepath : str
            Output file path for the JSON data.
        start_time : float or None, optional
            If given, the earliest event is shifted so that it begins at
            this time.
        time_scale : float, optional
            Multiplicative factor applied to all event start times
            (default ``1.0``).
        """
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
        
        output_data = {
            "meta": self.meta,
            "events": sorted_events
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"Successfully wrote {self.total_events} events to {os.path.abspath(filepath)}")
        except Exception as e:
            print(f"Error writing to {filepath}: {e}")
