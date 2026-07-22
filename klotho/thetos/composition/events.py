"""Standalone score events.

An :class:`Event` is the smallest schedulable unit a :class:`~klotho.thetos.composition.score.Score`
accepts: one ``{start | dur | inst | **pfields}`` gesture outside any
:class:`~klotho.thetos.composition.compositional.CompositionalUnit`. It lowers
to the same SC assembly format as UC leaves — one ``new`` node per voice
(a tuple pfield expands to simultaneous voices), plus any scheduled
``set`` / ``release`` messages targeting those nodes, mirroring scsynth's
``/s_new`` / ``/n_set`` commands.

Scheduled ``set``/``release`` times are stored relative to the event's
start, so they travel with the event when it is repositioned or scaled.
"""

from dataclasses import dataclass, field

from klotho.thetos.composition.compositional import (
    ENGINE_MFIELDS,
    _coerce_set_pfield_value,
)


@dataclass
class SetSpec:
    """A scheduled ``/n_set`` on an event's live node(s).

    ``offset`` is seconds after the owning event's start. Tuple values
    map element-wise onto the event's voices (modulo-cycling); scalars
    broadcast to every voice.
    """

    offset: float
    pfields: dict = field(default_factory=dict)


@dataclass
class ReleaseSpec:
    """A scheduled gate-off (``/n_set gate 0``), ``offset`` seconds after
    the owning event's start."""

    offset: float


class Event:
    """A single standalone event: ``{start | dur | inst | **pfields}``.

    Parameters
    ----------
    inst : None, str, or Instrument
        SynthDef name or instrument object (resolved eagerly so typos
        fail at construction time). None falls back to the converter's
        default synth.
    dur : float or None
        Duration in seconds. None means hold until an explicit release
        (requires a gated synth).
    pfields : dict, optional
        Initial pfield values. A tuple value means a simultaneity: one
        synth voice per element, exactly as in ``UC.set_pfields``.
    mfields : dict, optional
        Engine meta-fields (``strum``, ``group``).  When ``group`` is
        not given and *inst* carries an ensemble family tag (from
        ``ens['name']`` or a family view), ``group`` defaults to that
        family, so the event auto-routes to the family's track.

    Notes
    -----
    Position on the timeline lives in ``_offset`` (seconds), assigned by
    ``Score.add`` via ``_reoffset`` — the same protocol temporal units
    follow.
    """

    def __init__(self, inst=None, dur=None, pfields=None, mfields=None):
        if dur is not None:
            dur = float(dur)
            if dur < 0:
                raise ValueError(f"dur must be >= 0 or None, got {dur}")
        self.inst = inst
        self._dur = dur
        self.pfields = {
            k: _coerce_set_pfield_value(k, v) for k, v in (pfields or {}).items()
        }
        self.mfields = dict(mfields or {})
        if 'group' not in self.mfields:
            family = getattr(inst, '_ensemble_family', None)
            if family is not None:
                self.mfields['group'] = family
        self._sets: list = []
        self._release = None
        self._offset = 0.0
        self._validate_instrument()

    def _validate_instrument(self):
        from klotho.utils.playback._converter_base import resolve_instrument

        _, _, has_gate = resolve_instrument(self.inst)
        if self._dur is None and not has_gate:
            raise ValueError(
                f"dur=None (hold until release) requires a gated synth; "
                f"{self.inst!r} has no 'gate' control"
            )

    @property
    def duration(self) -> float:
        """Duration in seconds for placement math.

        ``dur`` when numeric, else the release offset when a release has
        been scheduled, else 0 (a bare hold occupies no timeline span).
        Scheduled ``set`` times never extend the duration.
        """
        if self._dur is not None:
            return self._dur
        if self._release is not None:
            return self._release.offset
        return 0.0

    def add_set(self, offset: float, pfields: dict) -> "Event":
        """Schedule a pfield change *offset* seconds after the event starts."""
        offset = float(offset)
        if offset < 0:
            raise ValueError(
                f"set offset must be >= 0 (the node does not exist before "
                f"the event starts), got {offset}"
            )
        if not pfields:
            raise ValueError("set requires at least one pfield")
        forbidden = ENGINE_MFIELDS & pfields.keys()
        if forbidden:
            raise ValueError(
                f"{sorted(forbidden)} are engine meta-fields and cannot be "
                f"changed on a live node"
            )
        coerced = {k: _coerce_set_pfield_value(k, v) for k, v in pfields.items()}
        self._sets.append(SetSpec(offset=offset, pfields=coerced))
        return self

    def add_release(self, offset: float) -> "Event":
        """Schedule a gate-off *offset* seconds after the event starts."""
        offset = float(offset)
        if offset < 0:
            raise ValueError(f"release offset must be >= 0, got {offset}")
        if self._release is not None:
            raise ValueError(
                f"event already has a release at offset "
                f"{self._release.offset}"
            )
        self._release = ReleaseSpec(offset=offset)
        return self

    def copy(self) -> "Event":
        dup = Event.__new__(Event)
        dup.inst = self.inst
        dup._dur = self._dur
        dup.pfields = dict(self.pfields)
        dup.mfields = dict(self.mfields)
        dup._sets = [SetSpec(s.offset, dict(s.pfields)) for s in self._sets]
        dup._release = (
            ReleaseSpec(self._release.offset) if self._release else None
        )
        dup._offset = self._offset
        return dup

    def _scale_bpm(self, factor: float) -> None:
        """Scale the whole gesture by ``1/factor`` — dur and every
        set/release offset together (mirrors ``TemporalUnit._scale_bpm``,
        where factor 2 halves the duration)."""
        if self._dur is not None:
            self._dur /= factor
        for spec in self._sets:
            spec.offset /= factor
        if self._release is not None:
            self._release.offset /= factor

    def __repr__(self) -> str:
        dur = "hold" if self._dur is None else f"{self._dur:.3f}"
        return (
            f"Event(inst={self.inst!r}, dur={dur}, "
            f"pfields={sorted(self.pfields)}, sets={len(self._sets)}, "
            f"released={self._release is not None})"
        )
