"""
Score: a timeline container for :class:`CompositionalUnit` objects.

A ``Score`` is an ordered, inspectable collection of
:class:`ScoreItem` wrappers.  Each item owns a copy of the unit submitted
to :meth:`Score.add`, so mutations through the external reference do not
leak into the score and vice versa.  Bare :class:`TemporalUnit` inputs
are auto-promoted to :class:`CompositionalUnit` on entry.

Placement is handled at ``add`` time via the mutually-exclusive kwargs
``at``, ``after``, and ``before``.  Convenience methods :meth:`append`
and :meth:`prepend` shift the timeline automatically.

Lowering to audio events is deferred: :func:`klotho.play` (not a method
on ``Score``) invokes a converter that produces the SC event payload at
playback time.  This keeps the Score a stable "what's in the composition"
view that timeline tooling can read, and removes the opacity of the old
"events accumulated eagerly on add" design.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Iterable, Optional, Union

from klotho.chronos.temporal_units import (
    TemporalBlock,
    TemporalUnit,
    TemporalUnitSequence,
)
from klotho.chronos.temporal_units.temporal import _reoffset
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.base import Effect


_DEFAULT_BLOCK_SIZE = 512

TemporalLike = Union[
    TemporalUnit, TemporalUnitSequence, TemporalBlock, CompositionalUnit
]


# ---------------------------------------------------------------------------
# Auto-promotion: bare UT → UC
# ---------------------------------------------------------------------------


def _promote_to_uc(unit: TemporalLike) -> TemporalLike:
    """Recursively promote bare :class:`TemporalUnit` nodes to
    :class:`CompositionalUnit`.

    Containers (:class:`TemporalUnitSequence`, :class:`TemporalBlock`) are
    walked and rebuilt with promoted members; existing
    :class:`CompositionalUnit` instances pass through unchanged.  The
    outer structure's private ``_offset`` is preserved so that internal
    cascades (``_set_offsets`` / ``_align_rows``) re-align correctly after
    reconstruction.
    """
    if isinstance(unit, CompositionalUnit):
        return unit
    if isinstance(unit, TemporalUnit):
        return CompositionalUnit.from_ut(unit)
    if isinstance(unit, TemporalUnitSequence):
        new_seq = [_promote_to_uc(u) for u in unit._seq]
        new_uts = TemporalUnitSequence(ut_seq=new_seq)
        new_uts._offset = unit._offset
        new_uts._set_offsets()
        return new_uts
    if isinstance(unit, TemporalBlock):
        new_rows = [_promote_to_uc(r) for r in unit._rows]
        new_bt = TemporalBlock(
            rows=new_rows, axis=unit._axis, sort_rows=unit._sort_rows
        )
        new_bt._offset = unit._offset
        new_bt._align_rows()
        return new_bt
    raise TypeError(f"Unsupported unit type: {type(unit).__name__}")


# ---------------------------------------------------------------------------
# ScoreItem: wrapper with name, track, and time-manipulation methods
# ---------------------------------------------------------------------------


@dataclass
class ScoreItem:
    """A named, owned wrapper around a temporal unit inside a
    :class:`Score`.

    A ``ScoreItem`` exposes read-only time queries (:attr:`start`,
    :attr:`end`, :attr:`duration`) and provides the only API for
    mutating a unit's total duration after it has entered a Score.

    Attribute access not matched on the item falls through to the owned
    unit, so ``score['verse'].leaf_nodes``,
    ``score['verse'].set_pfields(...)``, and so on work transparently.

    Parameters
    ----------
    unit : TemporalUnit, TemporalUnitSequence, TemporalBlock, or CompositionalUnit
        The wrapped unit.  Ownership belongs to the score; external
        references to the unit are not held (``Score.add`` always copies).
    name : str
        Unique identifier within the owning score.
    track : str or None
        Track assignment used during lowering (overrides any per-event
        ``group`` mfield when set).
    frozen : bool
        When True, :meth:`set_duration` raises :class:`RuntimeError`.
    """

    unit: TemporalLike
    name: str
    track: Optional[str] = None
    frozen: bool = False
    _score: Optional["Score"] = field(default=None, repr=False)

    @property
    def start(self) -> float:
        """Absolute start time in seconds."""
        return self.unit._offset

    @property
    def end(self) -> float:
        """Absolute end time in seconds."""
        return self.unit._offset + self.unit.duration

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        return self.unit.duration

    def set_duration(self, target: float, *, ripple: bool = False) -> None:
        """Scale bpm(s) on the owned unit so that its total duration
        matches *target*.

        Parameters
        ----------
        target : float
            Target total duration in seconds. Must be positive.
        ripple : bool, default=False
            When True, every item whose ``start`` is at or after this
            item's current ``end`` is shifted by the duration delta so
            that the rest of the timeline reflows.

        Raises
        ------
        RuntimeError
            If the item is :attr:`frozen`.
        ValueError
            If *target* is not positive.
        """
        if self.frozen:
            raise RuntimeError(f"ScoreItem '{self.name}' is frozen")
        if target <= 0:
            raise ValueError("Target duration must be positive")

        old_duration = self.unit.duration
        if old_duration == 0:
            raise ValueError(
                f"Cannot scale duration of item '{self.name}' with zero duration"
            )
        old_end = self.end

        factor = old_duration / target
        self.unit._scale_bpm(factor)

        if ripple and self._score is not None:
            delta = target - old_duration
            self._score._shift_items_at_or_after(
                exclude_name=self.name, pivot=old_end, by=delta
            )

    def stretch(self, factor: float, *, ripple: bool = False) -> None:
        """Multiply the total duration by *factor* (``factor=2`` doubles
        the duration by halving the bpm).

        See :meth:`set_duration` for ripple semantics.
        """
        if factor <= 0:
            raise ValueError("Stretch factor must be positive")
        self.set_duration(self.unit.duration * factor, ripple=ripple)

    def freeze(self) -> None:
        """Disallow subsequent :meth:`set_duration` / :meth:`stretch`
        calls on this item."""
        self.frozen = True

    def __getattr__(self, name: str):
        if name.startswith("_") or name in (
            "unit", "name", "track", "frozen", "start", "end",
            "duration", "set_duration", "stretch", "freeze",
        ):
            raise AttributeError(name)
        return getattr(self.__dict__["unit"], name)

    def __repr__(self) -> str:
        return (
            f"ScoreItem(name={self.name!r}, track={self.track!r}, "
            f"start={self.start:.3f}, end={self.end:.3f}, "
            f"unit={type(self.unit).__name__})"
        )


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Score:
    """Ordered collection of :class:`ScoreItem` objects on a shared
    timeline, with optional per-track FX chains.

    Units submitted to :meth:`add` are always copied (via
    ``unit.copy()``) so the external reference is never mutated through
    the score, and score-internal mutations (e.g.
    ``score['verse'].set_pfields(...)``) do not leak out.  Bare
    :class:`TemporalUnit` nodes are auto-promoted to
    :class:`CompositionalUnit` on entry.

    Rendering and export are handled outside the class:

    * ``play(score)`` — render an interactive SuperSonic widget via the
      universal :func:`klotho.play` dispatcher.
    * :meth:`write` — serialize the lowered event payload to JSON (for
      the native SC ``EventScheduler``).

    Examples
    --------
    >>> s = Score()
    >>> s.track("melody", inserts=[SynthDefFX("__reverb", mix=0.3)])
    >>> s.add(my_uc, name="intro", track="melody")
    >>> s.add(other_uc, name="verse", after="intro")
    >>> play(s)
    """

    def __init__(self, block_size: int = _DEFAULT_BLOCK_SIZE):
        self._block_size = block_size
        self._tracks: "OrderedDict[str, dict]" = OrderedDict()
        self._items: "OrderedDict[str, ScoreItem]" = OrderedDict()
        self._insert_registry: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def track(self, name: str, inserts: Optional[Iterable[Effect]] = None) -> "Score":
        """Register a named track with optional insert effects.

        Parameters
        ----------
        name : str
            Unique track name.  ``"main"`` is implicit and always
            exists; calling ``track("main", inserts=[...])`` sets master
            inserts.
        inserts : list of Effect or None
            Insert FX instances to place in this track's chain.

        Returns
        -------
        Score
            ``self``, for chaining.
        """
        if name != "main" and name in self._tracks:
            raise ValueError(f"Track '{name}' already exists")
        for ins in (inserts or []):
            if not isinstance(ins, Effect):
                raise TypeError(f"Expected SynthDefFX, got {type(ins).__name__}")
            if ins.uid in self._insert_registry:
                existing = self._insert_registry[ins.uid]
                raise ValueError(
                    f"Insert '{ins.name}' (uid={ins.uid}) already assigned to "
                    f"track '{existing}'"
                )
            self._insert_registry[ins.uid] = name
        self._tracks[name] = {"inserts": list(inserts or [])}
        return self

    # ------------------------------------------------------------------
    # Item placement
    # ------------------------------------------------------------------

    def add(
        self,
        unit: TemporalLike,
        *,
        name: Optional[str] = None,
        track: Optional[str] = None,
        at: Union[float, str, None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> ScoreItem:
        """Add a temporal unit to the score with optional placement.

        The unit is always copied (``unit.copy()``) so the external
        reference is unaffected by subsequent mutations through the
        score.  Bare ``TemporalUnit`` nodes are auto-promoted to
        ``CompositionalUnit`` on entry.

        Parameters
        ----------
        unit : TemporalUnit, TemporalUnitSequence, TemporalBlock, or CompositionalUnit
            The unit to place.
        name : str, optional
            Item name; must be unique.  Auto-generated (``"item_N"``) if
            omitted.
        track : str, optional
            Track name (registered via :meth:`track`).  Defaults to
            each event's own ``group`` mfield (or ``"default"``).
        at : float or str, optional
            Absolute start time in seconds, or the name of an existing
            item whose ``start`` will be matched.  Default is 0 when no
            placement kwarg is supplied.
        after : str, optional
            Name of an existing item; the new item starts at that
            item's ``end``.
        before : str, optional
            Name of an existing item; the new item ends at that item's
            ``start``.

        Returns
        -------
        ScoreItem
            The registered item (also retrievable via
            ``score[name]``).

        Raises
        ------
        ValueError
            If more than one of ``at``, ``after``, ``before`` is
            supplied, or if *name* already exists, or if *track* is not
            registered.
        KeyError
            If ``at=<str>``, ``after``, or ``before`` references a
            non-existent item.
        """
        placement_count = sum(
            1 for x in (at, after, before) if x is not None
        )
        if placement_count > 1:
            provided = [
                lbl for lbl, v in (('at', at), ('after', after), ('before', before))
                if v is not None
            ]
            raise ValueError(
                f"Specify at most one of 'at', 'after', 'before' "
                f"(got {', '.join(provided)})"
            )

        for arg_name, arg_val in (('after', after), ('before', before)):
            if arg_val is not None and arg_val not in self._items:
                raise KeyError(
                    f"No item named {arg_val!r} (for {arg_name}=); "
                    f"existing: {list(self._items)}"
                )
        if isinstance(at, str) and at not in self._items:
            raise KeyError(
                f"No item named {at!r} (for at=); existing: {list(self._items)}"
            )

        owned = _promote_to_uc(unit).copy()

        if after is not None:
            t = self._items[after].end
        elif before is not None:
            t = self._items[before].start - owned.duration
        elif isinstance(at, str):
            t = self._items[at].start
        elif isinstance(at, (int, float)):
            t = float(at)
        else:
            t = 0.0

        _reoffset(owned, t)

        if name is None:
            name = f"item_{len(self._items)}"
        if name in self._items:
            raise ValueError(f"Item {name!r} already exists")

        if track is not None and track != 'main' and track not in self._tracks:
            raise ValueError(
                f"Track {track!r} not registered; call score.track() first"
            )

        item = ScoreItem(unit=owned, name=name, track=track, _score=self)
        self._items[name] = item
        return item

    def append(
        self,
        unit: TemporalLike,
        *,
        name: Optional[str] = None,
        track: Optional[str] = None,
    ) -> ScoreItem:
        """Append *unit* so it starts at the current latest ``end`` of
        the score (or at 0 if the score is empty)."""
        if not self._items:
            return self.add(unit, name=name, track=track)
        latest_name = max(self._items, key=lambda n: self._items[n].end)
        return self.add(unit, name=name, track=track, after=latest_name)

    def prepend(
        self,
        unit: TemporalLike,
        *,
        name: Optional[str] = None,
        track: Optional[str] = None,
    ) -> ScoreItem:
        """Prepend *unit* at time 0, shifting every existing item right
        by ``unit.duration``."""
        owned = _promote_to_uc(unit).copy()
        shift_by = owned.duration

        for existing in self._items.values():
            _reoffset(existing.unit, existing.unit._offset + shift_by)

        _reoffset(owned, 0.0)

        if name is None:
            name = f"item_{len(self._items)}"
        if name in self._items:
            raise ValueError(f"Item {name!r} already exists")
        if track is not None and track != 'main' and track not in self._tracks:
            raise ValueError(
                f"Track {track!r} not registered; call score.track() first"
            )

        item = ScoreItem(unit=owned, name=name, track=track, _score=self)
        new_items: "OrderedDict[str, ScoreItem]" = OrderedDict()
        new_items[name] = item
        for k, v in self._items.items():
            new_items[k] = v
        self._items = new_items
        return item

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def __getitem__(self, name: str) -> ScoreItem:
        if name not in self._items:
            raise KeyError(
                f"No item named {name!r}; existing: {list(self._items)}"
            )
        return self._items[name]

    def __iter__(self):
        return iter(self._items.values())

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)

    def items(self):
        """Iterable view of all :class:`ScoreItem` objects in insertion order."""
        return self._items.values()

    def names(self) -> list[str]:
        """List of item names in insertion order."""
        return list(self._items.keys())

    def remove(self, name: str) -> ScoreItem:
        """Remove and return the item named *name*.

        Other items' placements are not adjusted; use
        :meth:`ScoreItem.set_duration` with ``ripple=True`` to reflow a
        timeline."""
        if name not in self._items:
            raise KeyError(
                f"No item named {name!r}; existing: {list(self._items)}"
            )
        return self._items.pop(name)

    # ------------------------------------------------------------------
    # Time queries
    # ------------------------------------------------------------------

    @property
    def start(self) -> float:
        """Earliest ``start`` across items, or 0 if the score is empty."""
        if not self._items:
            return 0.0
        return min(item.start for item in self._items.values())

    @property
    def end(self) -> float:
        """Latest ``end`` across items, or 0 if the score is empty."""
        if not self._items:
            return 0.0
        return max(item.end for item in self._items.values())

    @property
    def duration(self) -> float:
        """``end - start`` across the whole score."""
        return self.end - self.start

    # ------------------------------------------------------------------
    # Ripple edit support
    # ------------------------------------------------------------------

    def _shift_items_at_or_after(
        self, *, exclude_name: str, pivot: float, by: float
    ) -> None:
        """Shift every item (except ``exclude_name``) whose ``start`` is
        at or after *pivot* by *by* seconds.

        Called by :meth:`ScoreItem.set_duration` when ``ripple=True``.
        """
        for item in self._items.values():
            if item.name == exclude_name:
                continue
            if item.unit._offset >= pivot:
                _reoffset(item.unit, item.unit._offset + by)

    # ------------------------------------------------------------------
    # Ensemble integration
    # ------------------------------------------------------------------

    def from_ensemble(self, ensemble) -> "Score":
        """Create tracks (with insert chains) from an Ensemble's family
        structure.

        Each family becomes a track.  Insert FX are copied with fresh
        ``uid`` values so every Score gets independent FX nodes.
        """
        from klotho.thetos.instruments.ensemble import _copy_inserts_with_fresh_uids
        for family_name in ensemble.families:
            raw_inserts = ensemble.inserts(family_name)
            if raw_inserts:
                inserts = _copy_inserts_with_fresh_uids(raw_inserts)
            else:
                inserts = None
            self.track(family_name, inserts=inserts)
        return self

    # ------------------------------------------------------------------
    # Export (native SC EventScheduler JSON)
    # ------------------------------------------------------------------

    def write(
        self,
        filepath: str,
        start_time: Optional[float] = None,
        time_scale: float = 1.0,
    ) -> None:
        """Serialize the lowered event payload to a JSON file.

        If control envelopes are present, a companion ``.wav`` file
        containing the buffer data is written alongside the JSON.

        Parameters
        ----------
        filepath : str
            Output path for the JSON data.
        start_time : float or None
            Shift the earliest event to this time.  When None, events
            retain their absolute times as recorded in the score.
        time_scale : float
            Multiplicative factor for all event / envelope times.
        """
        import json
        import os
        from pathlib import Path

        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )

        payload = convert_score_to_sc_events(self)
        events = payload["events"]
        meta = payload.get("meta") or {}
        ctrl = payload.get("control_data") or {
            "buffer": None, "blockSize": self._block_size, "descriptors": []
        }

        time_shift = 0.0
        if start_time is not None and events:
            min_start = min(ev["start"] for ev in events)
            time_shift = start_time - min_start

        shifted_events = []
        for ev in events:
            ev_copy = dict(ev)
            ev_copy["start"] = (ev["start"] + time_shift) * time_scale
            shifted_events.append(ev_copy)

        shifted_descriptors = []
        for d in ctrl.get("descriptors", []):
            d_copy = dict(d)
            d_copy["start"] = (d["start"] + time_shift) * time_scale
            d_copy["dur"] = d["dur"] * time_scale
            shifted_descriptors.append(d_copy)

        output: dict = {"meta": dict(meta), "events": shifted_events}
        if shifted_descriptors:
            output["meta"]["controlEnvelopes"] = shifted_descriptors

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        print(
            f"Score: wrote {len(shifted_events)} events to "
            f"{os.path.abspath(filepath)}"
        )

        buffer = ctrl.get("buffer")
        if buffer is not None:
            try:
                import scipy.io.wavfile as wavfile
                buf_path = str(Path(filepath).with_suffix('.wav'))
                wavfile.write(buf_path, 44100, buffer)
                print(
                    f"Score: wrote control buffer to {os.path.abspath(buf_path)}"
                )
            except ImportError:
                print("Score: scipy not available; skipping .wav buffer export")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self) -> "Score":
        """Remove all items, tracks, and insert registrations."""
        self._items.clear()
        self._tracks.clear()
        self._insert_registry.clear()
        return self

    @property
    def tracks(self) -> dict:
        """Dict view of registered tracks."""
        return dict(self._tracks)

    def __repr__(self) -> str:
        tracks = list(self._tracks.keys()) or ["(none)"]
        return (
            f"Score(items={len(self._items)}, duration={self.duration:.3f}, "
            f"tracks={tracks})"
        )
