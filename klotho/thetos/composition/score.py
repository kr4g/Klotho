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
from klotho.thetos.composition.compositional import (
    ENGINE_MFIELDS,
    CompositionalUnit,
)
from klotho.thetos.composition.events import Event
from klotho.thetos.instruments.base import Effect
from klotho.thetos.instruments._shared import (
    canonical_def_name,
    ss_synth_channels,
)
from klotho.thetos.spatial import SpeakerArray


_DEFAULT_BLOCK_SIZE = 512


# ---------------------------------------------------------------------------
# Speaker arrays on a track
# ---------------------------------------------------------------------------
#
# A track's ``speakers=`` declaration decides the WIDTH of its buses and of
# its insert chain: one bus channel per speaker.  Everything downstream --
# lane routing, the instrument's adjacent-lane occupancy, the insert width
# contract -- is derived from the labels declared here, so this is the one
# place that normalizes them.
#
# Two shapes are accepted and they carry different amounts of information:
#
#   * a :class:`~klotho.thetos.spatial.SpeakerArray` -- labels AND geometry.
#     Only this one can be auditioned on headphones, because a binaural
#     fold needs positions.
#   * a plain sequence of labels -- routing only.  Honest about having no
#     geometry rather than inventing some; a made-up position would produce
#     a confident, wrong audition.
#
# A bare count is refused in both shapes (see ``_normalize_speakers``).


def _format_labels(labels, limit=12):
    """Labels for an error message, truncated when there are many."""
    labels = tuple(labels)
    if len(labels) <= limit:
        return ', '.join(repr(x) for x in labels)
    head = ', '.join(repr(x) for x in labels[:4])
    return f"{head}, ... , {labels[-1]!r} ({len(labels)} in all)"


def _is_speaker_label(value) -> bool:
    """True for something addressable as a speaker label.

    ``bool`` is excluded on purpose: ``True`` is an ``int`` in Python, so a
    boolean label would silently collide with speaker 1.
    """
    return isinstance(value, str) or (isinstance(value, int)
                                      and not isinstance(value, bool))


def _normalize_speakers(value, track_name: str, has_array: bool = False):
    """``speakers=`` -> ``(labels, lanes, array)``.

    *labels* is a tuple in lane order, *lanes* maps label to 0-based lane,
    and *array* is the :class:`SpeakerArray` when one was given (``None``
    for a labels-only declaration, which has no geometry to fold).

    An EMPTY sequence is the un-declare spelling, and *has_array* says
    whether there is anything to un-declare.  With one, ``speakers=[]``
    returns ``(None, None, None)`` -- the track keeps existing but stops
    being spatial -- which is the same shape ``inserts=[]`` already has for
    the chain.  Without one it is refused, because "no speakers" and "no
    ``speakers=`` argument" would then be the same track, and an empty list
    arriving there is far more likely a label list that computed to nothing
    than a deliberate no-op.
    """
    if isinstance(value, SpeakerArray):
        labels = value.labels
        return labels, {lb: i for i, lb in enumerate(labels)}, value

    if isinstance(value, bool) or isinstance(value, (int, float)):
        raise ValueError(
            f"speakers={value!r} on track {track_name!r} is ambiguous: Klotho "
            f"will not guess whether your speakers are labelled 0..n-1 or "
            f"1..n, and a lane index is not a speaker. Pass the labels "
            f"(speakers=range(1, 25)) or a SpeakerArray "
            f"(SpeakerArray.grid(cols=6, rows=4, col_spacing=50.0, "
            f"row_spacing=60.0)), which also carries the geometry the "
            f"binaural preview folds."
        )

    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError(
            f"speakers={value!r} on track {track_name!r} is one label, not an "
            f"array of them: a string iterates to its characters, so this "
            f"would declare {len(value)} speakers. Pass a sequence "
            f"(speakers=['FL', 'FR']) or a SpeakerArray."
        )

    try:
        items = list(value)
    except TypeError:
        raise ValueError(
            f"speakers={value!r} on track {track_name!r} is not a sequence of "
            f"speaker labels ({type(value).__name__}). Pass the labels "
            f"(speakers=range(1, 25), speakers=['FL', 'FR']) or a "
            f"SpeakerArray."
        ) from None

    if not items:
        if has_array:
            # The un-declare: this track HAS an array and the caller states
            # an empty one, so it stops being spatial.  Symmetric with
            # inserts=[], and the only way back to stereo -- omitting
            # speakers= on a re-registration KEEPS the array (that is what
            # makes the incremental notebook shape work), so it cannot also
            # mean "clear".
            return None, None, None
        raise ValueError(
            f"speakers={value!r} on track {track_name!r} declares no speakers, "
            f"so there is no lane to route a voice to, and {track_name!r} has "
            f"no array for an empty list to clear. Give it at least one label "
            f"(speakers=[1]), or leave speakers= off entirely -- a track that "
            f"declares no speakers IS an ordinary stereo track. ('main' is "
            f"the only track that can be registered twice: on 'main' an "
            f"empty speakers=[] un-declares an array it already has, and "
            f"omitting speakers= keeps it. Every other track refuses a "
            f"second track() call outright, so there is no re-registration "
            f"to clear anything on.)"
        )

    lanes = {}
    for label in items:
        if not _is_speaker_label(label):
            raise ValueError(
                f"speaker label {label!r} on track {track_name!r} must be an "
                f"int or a str, not {type(label).__name__}. Rigs are labelled "
                f"1..24 or 'FL'/'FR'; a float or a bool cannot name a speaker."
            )
        if label in lanes:
            raise ValueError(
                f"speaker label {label!r} appears twice in track "
                f"{track_name!r}'s speakers ({_format_labels(items)}). Every "
                f"speaker needs its own label -- a repeated one would make "
                f"speaker={label!r} mean two different lanes."
            )
        lanes[label] = len(lanes)
    return tuple(items), lanes, None


def _check_insert_width(effect, track_name: str, width: int) -> None:
    """Refuse an insert that cannot process a *width*-channel track.

    A spatial track's chain carries one channel per speaker, so an insert
    must read and write exactly that many.  Klotho does not adapt the
    width: summing lanes would move the music to a different loudspeaker
    and duplicating them would put it on two.

    *width* is the declaring track's own speaker count, which is the whole
    story for every track **but** ``"main"``.  Main's chain is built at
    ``max(every declared width, 2)``, so its inserts are checked a second
    time at lowering, against that number, by
    ``converters._refuse_broken_main_chain`` -- including when main
    declares no array at all and this function was never reached.  The
    floor and the widening are main's alone; every other track's chain is
    built at exactly the width checked here.
    """
    def_name = canonical_def_name(getattr(effect, 'defName', None))
    label = getattr(effect, 'name', None) or def_name
    shown = repr(label) if label == def_name else f"{label!r} ({def_name})"
    ins, outs = ss_synth_channels(def_name)
    if ins is None or outs is None:
        raise ValueError(
            f"Insert {shown} has no "
            f"recorded channel count, so Klotho cannot check it against track "
            f"{track_name!r} ({width} speakers). Bundled SynthDefs record "
            f"their width in assets/io.json; a SynthDef registered at runtime "
            f"records it via register_synthdef(). Add it there, or put this "
            f"insert on a stereo track."
        )
    if ins != width or outs != width:
        raise ValueError(
            f"Insert {shown} reads "
            f"{ins} and writes {outs} channels, but track {track_name!r} is "
            f"{width} channels wide ({width} speakers). A spatial track's "
            f"inserts must read and write exactly as many channels as the "
            f"track has speakers: declare the SynthDef as "
            f"In.ar(inBus, {width}) ... ReplaceOut.ar(outBus, sig) with "
            f"{width} channels. Klotho will not adapt the width for you -- "
            f"silently summing or duplicating lanes would change where the "
            f"music comes from."
        )


def _check_insert_fits_stereo(effect, track_name: str) -> None:
    """Refuse an insert left behind by ``speakers=[]`` that is too wide.

    Un-declaring an array changes the track's width contract from N
    channels back to 2, so an insert that was accepted against the array
    and is not restated in the same call would land on a stereo chain.  An
    insert reading more channels than the bus carries reads PAST it -- into
    whatever bus is allocated next -- and nothing downstream says so.

    Only the too-wide direction is refused, and only when the width is
    recorded.  A narrower or unrecorded insert is left alone so that
    clearing an array lands on exactly the rules an ordinary stereo track
    has always had, rather than inventing a stricter regime reachable only
    through this one spelling.
    """
    def_name = canonical_def_name(getattr(effect, 'defName', None))
    label = getattr(effect, 'name', None) or def_name
    shown = repr(label) if label == def_name else f"{label!r} ({def_name})"
    ins, outs = ss_synth_channels(def_name)
    if ins is None or outs is None:
        return
    if ins <= 2 and outs <= 2:
        return
    raise ValueError(
        f"speakers=[] un-declares the array on track {track_name!r}, which "
        f"leaves it stereo, but its chain still carries insert {shown}, which "
        f"reads {ins} and writes {outs} channels. On a stereo chain that insert "
        f"would read past the two channels the bus has. State the chain the "
        f"stereo track should have in the same call -- "
        f"score.track({track_name!r}, speakers=[], inserts=[...]) -- or "
        f"inserts=[] to empty it."
    )


TemporalLike = Union[
    TemporalUnit, TemporalUnitSequence, TemporalBlock, CompositionalUnit, Event
]


# ---------------------------------------------------------------------------
# Auto-promotion: bare UT → UC
# ---------------------------------------------------------------------------


def _promote_in_place(unit: TemporalLike) -> TemporalLike:
    """Recursively promote bare :class:`TemporalUnit` nodes to
    :class:`CompositionalUnit`, mutating containers IN PLACE.

    Only for objects the caller already owns (a fresh ``.copy()``).
    Containers keep their identity; a member list is only rewritten (and
    the ``_set_offsets`` / ``_align_rows`` cascade re-run) when a member
    was actually promoted, so the common all-UC case touches nothing.
    """
    if isinstance(unit, (Event, CompositionalUnit)):
        return unit
    if isinstance(unit, TemporalUnit):
        return CompositionalUnit.from_ut(unit)
    if isinstance(unit, TemporalUnitSequence):
        promoted = [_promote_in_place(u) for u in unit._seq]
        if any(p is not o for p, o in zip(promoted, unit._seq)):
            unit._seq = promoted
            unit._set_offsets()
        return unit
    if isinstance(unit, TemporalBlock):
        promoted = [_promote_in_place(r) for r in unit._rows]
        if any(p is not o for p, o in zip(promoted, unit._rows)):
            unit._rows = promoted
            unit._align_rows()
        return unit
    raise TypeError(f"Unsupported unit type: {type(unit).__name__}")


def _own_promoted(unit: TemporalLike) -> TemporalLike:
    """Copy *unit* once and promote bare TemporalUnits on the owned copy.

    Replaces the old ``_promote_to_uc(unit).copy()`` pattern, whose
    promotion pass rebuilt containers through constructors that copy
    every member (recursively compounding) before ``.copy()`` copied
    everything AGAIN — ~4 structural copies per member for the common
    no-promotion case.
    """
    return _promote_in_place(unit.copy())


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
# EventItem: handle for standalone events (Score.new)
# ---------------------------------------------------------------------------


class EventItem(ScoreItem):
    """The handle returned by :meth:`Score.new` — also the score entry.

    Wraps a standalone :class:`~klotho.thetos.composition.events.Event`
    and schedules ``set`` / ``release`` messages on its live synth
    node(s), analogous to scsynth ``/n_set``. Times are given in
    absolute score seconds (consistent with ``Score.add(at=...)``) but
    stored relative to the event's start, so scheduled messages travel
    with the event when it is repositioned or time-scaled.
    """

    def set(self, *, at: float, **pfields) -> "EventItem":
        """Schedule a pfield change at absolute score time *at*.

        Tuple values map element-wise onto the event's voices
        (modulo-cycling); scalars broadcast to every voice.
        """
        rel = float(at) - self.start
        if rel < 0:
            raise ValueError(
                f"set at={at} precedes event '{self.name}' start "
                f"({self.start}); the node does not exist yet"
            )
        self.unit.add_set(rel, pfields)
        return self

    def release(self, *, at: float) -> "EventItem":
        """Schedule a gate-off at absolute score time *at*."""
        rel = float(at) - self.start
        if rel < 0:
            raise ValueError(
                f"release at={at} precedes event '{self.name}' start "
                f"({self.start})"
            )
        self.unit.add_release(rel)
        return self

    def __repr__(self) -> str:
        ev = self.unit
        dur = "hold" if ev._dur is None else f"{ev._dur:.3f}"
        return (
            f"EventItem(name={self.name!r}, inst={ev.inst!r}, "
            f"start={self.start:.3f}, dur={dur}, sets={len(ev._sets)}, "
            f"released={ev._release is not None})"
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

    def track(self, name: str, inserts: Optional[Iterable[Effect]] = None,
              speakers=None) -> "Score":
        """Register a named track with optional insert effects.

        A track's chain is selected per *event*, not per unit: an event enters
        this chain when its ``group`` mfield equals *name*. Granularity is
        therefore whatever granularity the mfield was set at --
        ``uc.set_mfields(uc.leaves[1], group='solo')`` sends exactly that one
        leaf through the ``'solo'`` chain and leaves its siblings on
        ``'default'``. Untagged events carry ``group='default'`` and bypass
        every non-master chain.

        Chains can also be declared per instrument family on an
        :class:`~klotho.thetos.instruments.ensemble.Ensemble` and copied in
        with :meth:`from_ensemble`, which creates one track per family.

        Parameters
        ----------
        name : str
            Unique track name, matched against the ``group`` mfield of each
            lowered event.  ``"main"`` is implicit and always
            exists; calling ``track("main", inserts=[...])`` sets master
            inserts.  Every other name may be registered only once.

            ``"main"`` may be registered again, and a second call
            **merges**: the arguments this call names are set, the ones it
            omits keep what the earlier call declared.  So the ordinary
            notebook shape -- declare the rig in one cell, add a master
            insert in a later one -- keeps both::

                score.track('main', speakers=PAVILION)   # cell 3
                score.track('main', inserts=[limiter])   # cell 9: array kept

            Naming an argument again replaces that argument's previous
            value; it never appends to it.  ``inserts=`` is the whole chain
            in signal order, exactly as ``speakers=`` is the whole array,
            so re-running one cell declares the same chain rather than
            stacking a second copy of it, and ``inserts=[]`` empties the
            chain.  An insert dropped this way is released and may be
            placed on another track.  ``speakers=[]`` is the same spelling
            on the other argument: it un-declares the array and leaves the
            track stereo.
        inserts : list of Effect, Effect, or None
            Insert FX instances to place in this track's chain, applied in
            list order (signal flows left to right).  A bare
            ``Effect`` is accepted as a one-element chain.  ``None`` means
            "not stated": on a first registration the chain is empty, and
            on a re-registration of ``"main"`` the existing chain is kept.
            One ``Effect`` cannot appear twice in the same chain -- the
            engine addresses an insert node by its uid, so a repeat would
            leave one of the two nodes unreachable.
        speakers : SpeakerArray, sequence of labels, or None
            Declare this a **spatial** track carrying one bus channel per
            speaker.  A :class:`~klotho.thetos.spatial.SpeakerArray`
            carries labels *and* geometry (the only form a binaural
            audition can fold); a plain sequence of labels
            (``range(1, 25)``, ``['FL', 'FR']``) declares routing only.
            A bare count (``speakers=24``) is refused -- see
            :func:`_normalize_speakers`.

            Speakers are addressed by the **label you declare**, never by
            a lane index, and a voice picks one with the ``speaker``
            mfield::

                score.track('array', speakers=PAVILION)
                uc.set(uc.leaves, speaker=17)      # or set_mfields(...)
                score.add(uc, track='array')

            Speakers and inserts compose: a spatial voice still goes
            through its track's chain.  The chain is simply as wide as the
            array, so each insert must read and write exactly that many
            channels (an N-wide reverb is N independent reverbs, which is
            the correct semantics for speakers that share no room
            response).  Inserts are checked here, at declaration, before
            any audio exists.  ``None`` means "not stated" here too: a
            re-registration of ``"main"`` that omits ``speakers=`` keeps
            the array declared earlier, and the inserts it carries over are
            re-checked against that array's width.

            **Width checks that need more than one track happen later, at
            lowering, not here**, because none of them is decidable from a
            single call:

            * a speaker count outside the precompiled SynthDef family (see
              :data:`~klotho.utils.playback.supersonic.spatial_defs.PRECOMPILED_WIDTHS`)
              is refused when the score is prepared for playback;
            * ``"main"`` declaring an array NARROWER than some other track
              is refused when the score is lowered;
            * **every insert on ``"main"`` is re-checked against the width
              main's chain is actually BUILT at** -- ``max(every declared
              width, 2)``, not the width main itself declared, and not two
              just because main declared nothing.  ``main`` is the master
              chain and every track sums into it, so a stereo insert on a
              24-speaker rig bridges lanes 0..1 and leaves 22 speakers
              silent whether or not main names an array of its own.

            The last two cannot be checked at declaration:
            ``track('main', speakers=['L', 'R'])`` and
            ``track('main', inserts=[reverb])`` are not wrong until a later
            cell declares a wider track, and by then either call could be
            the one the composer meant to change.

            **There is no bundled effect wider than stereo.**  All 30 of
            Klotho's bundled ``fx`` SynthDefs are 2-in/2-out, so a master
            insert on a rig wider than a stereo pair needs a SynthDef the
            composer authors and passes to
            :func:`~klotho.utils.playback.supersonic.registry.register_synthdef`
            with ``kind='fx'``.  The refusal says so rather than offering a
            remedy that cannot be carried out.

            ``speakers=[]`` is the un-declare, matching ``inserts=[]``: the
            track keeps existing and stops being spatial.  It is refused on
            a track that declares no array, where it would be a no-op that
            is much more likely a label list that computed to nothing.
            Because a stereo chain is two channels wide, an insert carried
            over from the array that reads or writes more than two is
            refused too -- state the stereo chain in the same call.  Note
            that on a score where another equally-wide spatial track is
            still declared, un-declaring main's array hands the headphone
            fold to THAT track's geometry (see the comment at the merge
            site); the fold changes, silently and by design.

        Returns
        -------
        Score
            ``self``, for chaining.

        Raises
        ------
        ValueError
            For a bare speaker count, a duplicate or non-label speaker
            name, an empty array on a track that has none to un-declare,
            an insert listed twice in one chain or already owned by
            another track, or an insert whose channel width does not match
            the array's (including an insert whose width is not recorded
            anywhere -- unknown widths are refused, never guessed).
        """
        if isinstance(inserts, Effect):
            inserts = [inserts]
        prior = self._tracks.get(name)
        if name != "main" and prior is not None:
            raise ValueError(f"Track '{name}' already exists")

        # A second registration of 'main' MERGES rather than replaces the
        # whole record.  An omitted argument is "not stated", not "cleared":
        # a full replacement made the ordinary incremental shape (declare the
        # rig in one cell, add a master insert in a later one) silently throw
        # away whichever half was configured first, taking the stereo fold and
        # the spatial decoder with it.  An argument that IS stated wins,
        # because the caller stated an intent this time; that also keeps a
        # re-run cell idempotent instead of stacking a second copy of its
        # chain, and leaves inserts=[] as the way to empty one.
        had_array = prior is not None and prior["labels"] is not None
        if speakers is not None:
            # An empty sequence is the un-declare, and only when there is
            # something to un-declare; see _normalize_speakers.
            labels, lanes, array = _normalize_speakers(speakers, name,
                                                       has_array=had_array)
        elif prior is not None:
            # CARRYING MAIN'S ARRAY OVER CHANGES WHICH GEOMETRY IS HEARD.
            # The headphone fold is one decoder for the summed main bus, so
            # when several equally-wide spatial tracks declare DIFFERENT
            # arrays only one geometry can describe the result, and
            # scheduler_score.js breaks that tie in main's favour
            # (``var chosen = (widest.indexOf('main') !== -1) ? 'main' : ...``,
            # near line 250).  While the second call erased main's array,
            # main dropped out of the tie and the other track's geometry was
            # folded; keeping it, main's own geometry is -- with measurably
            # different binaural coefficients, no error either way.  Main's
            # is the right answer -- it is the chain the decoder sits on --
            # and the composer is now TOLD, because the "different speaker
            # arrays at the same width" warning beside that line fires only
            # when the tie has more than one array in it, which under the
            # erasure it never did.
            #
            # The other warning at the far end goes the other way: the one
            # in scheduler_score.js beginning "the master chain has inserts
            # and main was widened ... but main declares no speakers of its
            # own -- so those inserts were only ever checked as STEREO"
            # tests ``spatial.widths['main'] == null``.  The erasure made
            # that true and the warning fired; keeping the array makes it
            # false and the warning stops.
            #
            # CORRECTED (AF-1): "and rightly so, since the inserts really
            # were checked against the array" is true only when main's array
            # is AS WIDE as the widest track.  Declaring a NARROWER one --
            # ``speakers=['L', 'R']`` beside a 24-speaker track -- silenced
            # that warning while leaving every bit of the damage: main's
            # chain is still built at 24, the inserts were still checked
            # against 2, and lanes 2..23 of main's post-FX bus are still
            # never written.  Following the warning's own advice was
            # therefore a way to make it stop lying about nothing.
            #
            # CORRECTED AGAIN (AF-1b): the whole width argument above is
            # about main's ARRAY, and main's array was never what made the
            # insert width matter -- the widest OTHER track's width is.
            # Both branches of that JS warning (main declares none, main
            # declares a narrow one) are the same defect wearing two hats,
            # and lowering now checks the thing they share:
            # ``converters._refuse_broken_main_chain`` refuses any insert on
            # main that does not read and write ``max(every declared width,
            # 2)`` channels, array or no array.  Note the consequence for
            # that JS warning: it fires on ``widths['main'] == null`` alone,
            # so it now also fires on the ONE configuration that works --
            # main undeclared carrying a correctly-wide insert -- where its
            # "only ever checked as STEREO" is no longer true.  Conservative
            # and merely noisy, not a silence, and scheduler_score.js is not
            # this lane's file to fix; filed for the JS owner.
            labels, lanes, array = (prior["labels"], prior["lanes"],
                                    prior["speakers"])
        else:
            labels = lanes = array = None
        cleared_array = had_array and labels is None

        if inserts is None and prior is not None:
            incoming = list(prior["inserts"])
        else:
            incoming = list(inserts or [])

        # Validate BEFORE mutating anything: a refused declaration must
        # leave the score exactly as it was, or a caught error would leave
        # half a track registered and its inserts owned by it.  Inserts
        # carried over from a previous call are re-validated too -- a newly
        # declared array changes the width they have to match.
        checked = []
        seen: dict[str, Effect] = {}
        for ins in incoming:
            if not isinstance(ins, Effect):
                raise TypeError(f"Expected SynthDefFX, got {type(ins).__name__}")
            owner = self._insert_registry.get(ins.uid)
            if owner is not None and owner != name:
                raise ValueError(
                    f"Insert '{ins.name}' (uid={ins.uid}) already assigned to "
                    f"track '{owner}'"
                )
            if ins.uid in seen:
                # ``defName`` belongs to SynthDefFX, not to the Effect base
                # class, so read it the way _check_insert_width does: a bare
                # Effect must reach the teaching ValueError below, not an
                # AttributeError raised while formatting it.
                def_name = canonical_def_name(getattr(ins, 'defName', None))
                how = (
                    f"build two instances (inserts=[SynthDefFX('{def_name}'), "
                    f"SynthDefFX('{def_name}')])"
                    if def_name is not None else
                    "build two instances rather than listing one of them twice"
                )
                raise ValueError(
                    f"Insert '{ins.name}' (uid={ins.uid}) appears twice in "
                    f"the chain of track '{name}'. The engine addresses an "
                    f"insert node by its uid, so the second node would "
                    f"overwrite the first one's handle and leave it "
                    f"unreachable. For two stages of the same effect, "
                    f"{how}."
                )
            if labels is not None:
                _check_insert_width(ins, name, len(labels))
            elif cleared_array:
                _check_insert_fits_stereo(ins, name)
            seen[ins.uid] = ins
            checked.append(ins)

        # Release the uids this track owned and no longer carries, so a
        # dropped insert is placeable again instead of staying owned by a
        # chain it has left.
        for uid, owner in list(self._insert_registry.items()):
            if owner == name and uid not in seen:
                del self._insert_registry[uid]
        for ins in checked:
            self._insert_registry[ins.uid] = name
        self._tracks[name] = {
            "inserts": checked,
            "speakers": array,
            "labels": labels,
            "lanes": lanes,
        }
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

        owned = _own_promoted(unit)

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
            prefix = "event" if isinstance(owned, Event) else "item"
            name = f"{prefix}_{len(self._items)}"
        if name in self._items:
            raise ValueError(f"Item {name!r} already exists")

        if track is not None and track != 'main' and track not in self._tracks:
            raise ValueError(
                f"Track {track!r} not registered; call score.track() first"
            )

        item_cls = EventItem if isinstance(owned, Event) else ScoreItem
        item = item_cls(unit=owned, name=name, track=track, _score=self)
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
        owned = _own_promoted(unit)
        shift_by = owned.duration

        for existing in self._items.values():
            _reoffset(existing.unit, existing.unit._offset + shift_by)

        _reoffset(owned, 0.0)

        if name is None:
            prefix = "event" if isinstance(owned, Event) else "item"
            name = f"{prefix}_{len(self._items)}"
        if name in self._items:
            raise ValueError(f"Item {name!r} already exists")
        if track is not None and track != 'main' and track not in self._tracks:
            raise ValueError(
                f"Track {track!r} not registered; call score.track() first"
            )

        item_cls = EventItem if isinstance(owned, Event) else ScoreItem
        item = item_cls(unit=owned, name=name, track=track, _score=self)
        new_items: "OrderedDict[str, ScoreItem]" = OrderedDict()
        new_items[name] = item
        for k, v in self._items.items():
            new_items[k] = v
        self._items = new_items
        return item

    # ------------------------------------------------------------------
    # Standalone events (scsynth node analogy: /s_new, /n_set, gate-off)
    # ------------------------------------------------------------------

    def new(
        self,
        start: float = 0.0,
        dur: Optional[float] = None,
        inst=None,
        *,
        name: Optional[str] = None,
        track: Optional[str] = None,
        **pfields,
    ) -> EventItem:
        """Schedule a single standalone event (→ ``/s_new``).

        Parameters
        ----------
        start : float
            Absolute start time in seconds.
        dur : float or None
            Duration in seconds.  None holds the synth until an explicit
            :meth:`release` (requires a gated synth).
        inst : None, str, or Instrument
            SynthDef name or instrument object; None uses the default
            synth.
        name : str, optional
            Item name; auto-generated (``"event_N"``) if omitted.
        track : str, optional
            Track name (registered via :meth:`track`).
        **pfields
            Pfield values, with the same semantics as
            ``UC.set_pfields`` — a tuple value means a simultaneity (one
            synth voice per element).  ``strum``, ``group`` and
            ``speaker`` are routed to engine meta-fields; ``speaker``
            names a loudspeaker in the track's declared array.

        Returns
        -------
        EventItem
            The handle (also the score entry), usable as the target of
            :meth:`set` / :meth:`release` — even when tuple pfields
            expand to multiple voices, the event is one logical handle.
        """
        mfields = {
            k: pfields.pop(k) for k in list(pfields) if k in ENGINE_MFIELDS
        }
        ev = Event(inst=inst, dur=dur, pfields=pfields, mfields=mfields)
        return self.add(ev, name=name, track=track, at=float(start))

    def set(self, target, *, at: float, **pfields) -> EventItem:
        """Schedule pfield changes on a standalone event's live node(s)
        at absolute score time *at* (→ ``/n_set``).

        Tuple values map element-wise onto the event's voices
        (modulo-cycling); scalars broadcast.  Note that
        ``score['uc_item'].set(...)`` on a unit item is different: it
        falls through to ``CompositionalUnit.set``, a static
        (pre-playback) parameter assignment.

        Parameters
        ----------
        target : EventItem or str
            The handle returned by :meth:`new`, or its item name.
        at : float
            Absolute score time in seconds; must not precede the
            event's start.
        """
        return self._resolve_event_target(target, 'set').set(at=at, **pfields)

    def release(self, target, *, at: float) -> EventItem:
        """Schedule a gate-off on a standalone event's live node(s) at
        absolute score time *at* (→ ``/n_set gate 0``).

        See :meth:`set` for target/time semantics.
        """
        return self._resolve_event_target(target, 'release').release(at=at)

    def _resolve_event_target(self, target, op: str) -> EventItem:
        if isinstance(target, str):
            if target not in self._items:
                raise KeyError(
                    f"No item named {target!r}; existing: {list(self._items)}"
                )
            target = self._items[target]
        if not isinstance(target, EventItem):
            raise TypeError(
                f"Score.{op}() targets standalone events (from Score.new); "
                f"got {type(target).__name__}. For unit items use "
                f"set_pfields(...) instead."
            )
        if target._score is not self:
            raise ValueError(
                f"Event '{target.name}' belongs to a different Score"
            )
        return target

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
            retain their absolute times as recorded in the score,
            except that a timeline beginning at a negative time is
            always pulled up to start at 0 during lowering.
        time_scale : float
            Multiplicative factor for all event / envelope times.
        """
        import json
        import os
        from pathlib import Path

        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )

        payload = convert_score_to_sc_events(self, start_time=start_time)
        events = payload["events"]
        meta = payload.get("meta") or {}
        ctrl = payload.get("control_data") or {
            "buffer": None, "blockSize": self._block_size, "descriptors": []
        }

        shifted_events = []
        for ev in events:
            ev_copy = dict(ev)
            ev_copy["start"] = ev["start"] * time_scale
            shifted_events.append(ev_copy)

        shifted_descriptors = []
        for d in ctrl.get("descriptors", []):
            d_copy = dict(d)
            d_copy["start"] = d["start"] * time_scale
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

    def clear(self, keep_tracks: bool = False) -> "Score":
        """Remove all items; optionally keep the track structure.

        Parameters
        ----------
        keep_tracks : bool, default=False
            When False, tracks and insert registrations are removed too,
            leaving a blank score.  When True, registered tracks (and
            their insert FX chains) are preserved so the score can be
            refilled and played with the same mixer layout.
        """
        self._items.clear()
        if not keep_tracks:
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
