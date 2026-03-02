"""
Score: an orchestrator for multi-track SuperCollider / SuperSonic playback.

Accumulates :class:`CompositionalUnit` objects, manages tracks with insert
FX chains, collects control-envelope metadata, and produces either a
browser-based SuperSonic widget (via :meth:`play`) or a JSON file for the
native SC EventScheduler (via :meth:`write`).
"""

from __future__ import annotations

import heapq
import json
import os
from collections import OrderedDict
from typing import Union
from uuid import uuid4

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.base import InsertBase
from klotho.chronos.temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


_SC_EVENT_PRIORITY = {'new': 0, 'set': 1, 'release': 2}
_DEFAULT_BLOCK_SIZE = 512


class Score:
    """Multi-track score that accumulates events, tracks, and control envelopes.

    Parameters
    ----------
    block_size : int, optional
        Number of samples per control-envelope block (default 512).

    Examples
    --------
    >>> s = Score()
    >>> s.track("melody", inserts=[Insert("__reverb", mix=0.3)])
    >>> s.add(my_uc, track="melody")
    >>> s.play()
    """

    def __init__(self, block_size: int = _DEFAULT_BLOCK_SIZE):
        self._block_size = block_size
        self._tracks: OrderedDict[str, dict] = OrderedDict()
        self._event_heap: list = []
        self._event_counter: int = 0
        self._total_events: int = 0
        self._control_descriptors: list[dict] = []
        self._insert_registry: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def track(self, name: str, inserts=None) -> 'Score':
        """Register a named track with optional insert effects.

        Parameters
        ----------
        name : str
            Unique track name.  ``"main"`` is implicit and always exists;
            calling ``track("main", inserts=[...])`` sets master inserts.
        inserts : list of Insert or None
            Insert FX instances to place in this track's chain.

        Returns
        -------
        Score
            ``self``, for chaining.
        """
        if name != "main" and name in self._tracks:
            raise ValueError(f"Track '{name}' already exists")
        for ins in (inserts or []):
            if not isinstance(ins, InsertBase):
                raise TypeError(f"Expected Insert, got {type(ins).__name__}")
            if ins.uid in self._insert_registry:
                existing = self._insert_registry[ins.uid]
                raise ValueError(
                    f"Insert '{ins.name}' (uid={ins.uid}) already assigned to track '{existing}'"
                )
            self._insert_registry[ins.uid] = name
        self._tracks[name] = {"inserts": list(inserts or [])}
        return self

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def _push_event(self, event: dict, priority: int | None = None):
        if priority is None:
            priority = _SC_EVENT_PRIORITY.get(event.get("type"), 3)
        start = event.get("start", 0.0)
        uid = event.get("id", uuid4().hex)
        heapq.heappush(
            self._event_heap,
            (start, priority, uid, self._event_counter, event),
        )
        self._event_counter += 1
        self._total_events += 1

    def add(
        self,
        uc: Union[CompositionalUnit, TemporalUnit, TemporalUnitSequence, TemporalBlock],
        track: str | None = None,
    ) -> 'Score':
        """Add events from a musical structure.

        Parameters
        ----------
        uc : CompositionalUnit, TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The musical structure whose events should be scheduled.
        track : str or None
            Override the track for all events from this UC.  If ``None``,
            the ``group`` mfield on each event is used (defaulting to
            ``"default"``).

        Returns
        -------
        Score
            ``self``, for chaining.
        """
        if isinstance(uc, (TemporalUnitSequence, TemporalBlock)):
            for unit in uc:
                self.add(unit, track=track)
            return self

        if isinstance(uc, CompositionalUnit):
            self._add_compositional_unit(uc, track=track)
        else:
            self._add_temporal_unit(uc, track=track)

        return self

    def _add_compositional_unit(self, uc: CompositionalUnit, track: str | None):
        assembly_events, node_to_event_ids = lower_compositional_ir_to_sc_assembly(
            uc,
            extra_pfields=None,
            animation=False,
            default_synth='kl_tri',
            include_ungated_release=False,
            normalize_sc_pfields=False,
            sort_output=True,
            return_node_map=True,
        )

        id_map: dict[str, str] = {}

        for event in assembly_events:
            if event.get("defName") == "__rest__":
                continue

            event_type = event.get("type")

            if track is not None:
                event["group"] = track
            elif "group" not in event:
                event["group"] = "default"

            if event_type == "new":
                new_uid = uuid4().hex
                id_map[event["id"]] = new_uid
                event["id"] = new_uid
                self._push_event(event)

            elif event_type == "set":
                orig_id = event.get("id")
                mapped_uid = id_map.get(orig_id, orig_id)
                event["id"] = mapped_uid
                self._push_event(event)

            elif event_type == "release":
                mapped_uid = id_map.get(event.get("id"))
                if mapped_uid is None:
                    continue
                event["id"] = mapped_uid
                self._push_event(event)

        self._collect_control_envelopes(uc, id_map, node_to_event_ids)

    def _add_temporal_unit(self, uc: TemporalUnit, track: str | None):
        for event in uc:
            if event.is_rest:
                continue
            instrument = uc.get_instrument(event.node_id) if hasattr(uc, 'get_instrument') else None
            if isinstance(instrument, str):
                def_name = instrument
            elif instrument is not None and hasattr(instrument, 'defName'):
                def_name = instrument.defName
            else:
                def_name = 'kl_tri'

            group = track or (event.get_mfield('group') if hasattr(event, 'get_mfield') else None) or 'default'
            pfields = {k: v for k, v in event.pfields.items() if k != 'group'}

            uid = uuid4().hex
            new_event = {
                "type": "new",
                "id": uid,
                "defName": def_name,
                "start": event.start,
                "group": group,
                "pfields": pfields,
            }
            self._push_event(new_event)

            release_mode = (getattr(instrument, 'release_mode', '') or '').lower() if instrument is not None else 'gate'
            if release_mode not in ('gate', 'free'):
                release_mode = 'gate'
            if release_mode == 'gate':
                rel_event = {"type": "release", "id": uid, "start": event.end}
                self._push_event(rel_event)

    # ------------------------------------------------------------------
    # Control envelope collection
    # ------------------------------------------------------------------

    def _collect_control_envelopes(self, uc: CompositionalUnit, id_map: dict[str, str], node_to_event_ids: dict | None = None):
        node_to_event_ids = node_to_event_ids or {}
        for desc in uc.resolved_control_envelopes():
            remapped = []
            for nid in desc["target_nodes"]:
                assembly_eids = node_to_event_ids.get(nid, [])
                for eid in assembly_eids:
                    score_uid = id_map.get(eid, eid)
                    if score_uid not in remapped:
                        remapped.append(score_uid)

            if not remapped:
                continue

            start, end = desc["time_span"]
            self._control_descriptors.append({
                "envelope": desc["envelope"],
                "pfields": desc["pfields"],
                "start": start,
                "duration": end - start,
                "targetIds": remapped,
            })

    # ------------------------------------------------------------------
    # Metadata builders
    # ------------------------------------------------------------------

    def _build_meta(self) -> dict:
        groups = [name for name in self._tracks if name != "main"]
        inserts: dict[str, list] = {}
        for name, track_data in self._tracks.items():
            if track_data["inserts"]:
                inserts[name] = [
                    {"uid": ins.uid, "defName": ins.defName, "args": ins.args}
                    for ins in track_data["inserts"]
                ]
        meta: dict = {}
        if groups:
            meta["groups"] = groups
        if inserts:
            meta["inserts"] = inserts
        return meta

    def _build_control_data(self) -> dict:
        if not self._control_descriptors:
            return {"buffer": None, "blockSize": self._block_size, "descriptors": []}

        import numpy as np

        t = np.linspace(0.0, 1.0, self._block_size, dtype=np.float64)
        blocks = []
        serializable: list[dict] = []

        for i, desc in enumerate(self._control_descriptors):
            env = desc["envelope"]
            total = env.total_time
            if total <= 0:
                bp_times = [0.0] * len(env.values)
            else:
                cumulative = [0.0]
                for seg_t in env.times:
                    cumulative.append(cumulative[-1] + seg_t * env.time_scale)
                bp_times = [c / total for c in cumulative]

            samples = np.interp(
                t,
                np.array(bp_times, dtype=np.float64),
                np.array(env.values, dtype=np.float64),
            ).astype(np.float32)
            blocks.append(samples)

            serializable.append({
                "blockIndex": i,
                "start": desc["start"],
                "dur": desc["duration"],
                "pfields": desc["pfields"],
                "targetIds": desc["targetIds"],
            })

        buffer_data = np.concatenate(blocks)
        return {
            "buffer": buffer_data,
            "blockSize": self._block_size,
            "descriptors": serializable,
        }

    # ------------------------------------------------------------------
    # Event drain (non-destructive)
    # ------------------------------------------------------------------

    def _drain_events(self, start_time: float | None = None, time_scale: float = 1.0) -> list[dict]:
        events_copy = list(self._event_heap)
        sorted_events: list[dict] = []
        if not events_copy:
            return sorted_events

        time_shift = 0.0
        if start_time is not None:
            min_start = min(s for s, _, _, _, _ in events_copy)
            time_shift = start_time - min_start

        while events_copy:
            start, _, _, _, event = heapq.heappop(events_copy)
            event_copy = dict(event)
            event_copy["start"] = (start + time_shift) * time_scale
            sorted_events.append(event_copy)

        return sorted_events

    # ------------------------------------------------------------------
    # Playback (SuperSonic browser widget)
    # ------------------------------------------------------------------

    def play(self, ring_time: int = 5, **kwargs):
        """Render and display a SuperSonic playback widget.

        Parameters
        ----------
        ring_time : int
            Seconds of ring-out time after playback ends.
        **kwargs
            Forwarded to the engine.

        Returns
        -------
        IPython.display.DisplayHandle
        """
        from klotho.utils.playback._session_boot import boot_supersonic
        from klotho.utils.playback.supersonic import SuperSonicEngine

        boot_supersonic()

        events = self._drain_events()
        meta = self._build_meta()
        ctrl = self._build_control_data()

        engine = SuperSonicEngine(
            events,
            meta=meta,
            control_data=ctrl,
            ring_time=ring_time,
        )
        return engine.display()

    # ------------------------------------------------------------------
    # Export (native SC EventScheduler JSON)
    # ------------------------------------------------------------------

    def write(self, filepath: str, start_time: float | None = None, time_scale: float = 1.0):
        """Serialize events and metadata to a JSON file.

        If control envelopes are present, a companion ``.wav`` file
        containing the buffer data is written alongside the JSON.

        Parameters
        ----------
        filepath : str
            Output path for the JSON data.
        start_time : float or None
            Shift the earliest event to this time.
        time_scale : float
            Multiplicative factor for all event times.
        """
        from pathlib import Path

        events = self._drain_events(start_time=start_time, time_scale=time_scale)
        meta = self._build_meta()
        ctrl = self._build_control_data()

        output: dict = {"meta": meta, "events": events}
        if ctrl["descriptors"]:
            output["meta"]["controlEnvelopes"] = ctrl["descriptors"]

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Score: wrote {self._total_events} events to {os.path.abspath(filepath)}")

        if ctrl["buffer"] is not None:
            try:
                import scipy.io.wavfile as wavfile
                buf_path = str(Path(filepath).with_suffix('.wav'))
                wavfile.write(buf_path, 44100, ctrl["buffer"])
                print(f"Score: wrote control buffer to {os.path.abspath(buf_path)}")
            except ImportError:
                print("Score: scipy not available; skipping .wav buffer export")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self) -> 'Score':
        """Remove all events, tracks, and control envelope descriptors."""
        self._event_heap.clear()
        self._event_counter = 0
        self._total_events = 0
        self._tracks.clear()
        self._control_descriptors.clear()
        self._insert_registry.clear()
        return self

    @property
    def total_events(self) -> int:
        return self._total_events

    @property
    def tracks(self) -> dict:
        return dict(self._tracks)

    def __repr__(self):
        tracks = list(self._tracks.keys()) or ["(none)"]
        return f"Score(events={self._total_events}, tracks={tracks})"
