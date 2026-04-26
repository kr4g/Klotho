# ------------------------------------------------------------------------
# Klotho/klotho/chronos/temporal_units/ut.py
# ------------------------------------------------------------------------
"""
Temporal units.

A temporal unit binds a rhythm tree to a tempo and beat reference, producing
concrete onset times and durations in seconds. Temporal units can be
collected into sequences and blocks for polyphonic or multi-layered timing
structures.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Iterable, Iterator, Union
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms import auto_subdiv
from klotho.chronos.utils import calc_onsets, beat_duration, seconds_to_hmsms

from enum import Enum
import pandas as pd
import copy

class ProlatioTypes(Enum):
    """
    Enum of prolatio (subdivision) types for a temporal unit.

    The four types describe how a time signature is subdivided:

    - **DURATION** -- a single sustained note spanning the entire measure.
    - **REST** -- a single rest spanning the entire measure.
    - **PULSE** -- evenly spaced pulses matching the numerator.
    - **SUBDIVISION** -- a custom subdivision tuple.

    Each type also carries a set of string aliases for convenient parsing.
    """
    DURATION    = 'Duration'
    REST        = 'Rest'
    PULSE       = 'Pulse'
    SUBDIVISION = 'Subdivision'
    DURTYPES    = {'d', 'duration', 'dur'}
    RESTYPES    = {'r', 'rest', 'silence'}
    PULSTYPES   = {'p', 'pulse', 'phase'}
    SUBTYPES    = {'s', 'subdivision', 'subdivisions'}


class TemporalMeta(type):
    """Metaclass for all temporal structures."""
    pass


@dataclass(frozen=True)
class NodeContext:
    """Context object passed to predicates in ``UTNodeSelector.filter``.

    Attributes
    ----------
    node : int
        The node ID being evaluated.
    index : int
        Zero-based position within the current selection.
    total : int
        Total number of nodes in the current selection.
    """

    node: int
    index: int
    total: int


class UTNodeSelector:
    """An ordered, owner-bound collection of node IDs with fluent selection ops.

    Carries UT-level structural verbs (``make_rest``, ``subdivide``,
    ``sparsify``). Subclasses add domain-specific action verbs; in particular,
    :class:`~klotho.thetos.composition.compositional.UCNodeSelector` adds
    parameter/envelope/slur verbs.

    The selector preserves ownership identity: operations that return another
    selector always point at the same owner (UT/UC) so that subsequent verb
    calls dispatch to the owning object's mutators.

    Indexing, slicing, fancy-indexing, ``filter``, ``where``, and set-algebra
    operations all return a new selector of the same concrete subclass.

    Equality is strict: two selectors compare equal iff they share the same
    owner (``is``) and hold the same ids in the same order; a selector also
    compares equal to a ``tuple`` or ``list`` with matching ids (enabling
    tuple-based test assertions). Any other type returns ``NotImplemented`` -
    in particular, ``selector == int`` is always False via Python's fallback,
    surfacing mistakes loudly rather than silently.
    """

    __slots__ = ('_owner', '_ids')

    def __init__(self, owner: Any, ids: Iterable[int]):
        object.__setattr__(self, '_owner', owner)
        object.__setattr__(self, '_ids', tuple(ids))

    # --- Sequence protocol ---
    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self) -> Iterator[int]:
        return iter(self._ids)

    def __contains__(self, node) -> bool:
        return node in self._ids

    def __bool__(self) -> bool:
        return bool(self._ids)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._ids)})"

    def __eq__(self, other):
        if isinstance(other, UTNodeSelector):
            return self._owner is other._owner and self._ids == other._ids
        if isinstance(other, (tuple, list)):
            return self._ids == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((id(self._owner), self._ids))

    # --- Raw access ---
    @property
    def ids(self) -> tuple:
        """Underlying tuple of node IDs."""
        return self._ids

    @property
    def first(self) -> int:
        """The first node ID in the selection."""
        return self._ids[0]

    @property
    def last(self) -> int:
        """The last node ID in the selection."""
        return self._ids[-1]

    @property
    def owner(self):
        """The UT/UC this selector is bound to."""
        return self._owner

    # --- Indexing (always returns same subclass) ---
    def __getitem__(self, key) -> 'UTNodeSelector':
        if isinstance(key, int):
            return type(self)(self._owner, (self._ids[key],))
        if isinstance(key, slice):
            return type(self)(self._owner, self._ids[key])
        if isinstance(key, (list, tuple)):
            return type(self)(self._owner, tuple(self._ids[i] for i in key))
        raise TypeError(
            f"Invalid selector index: {type(key).__name__}; "
            f"expected int, slice, or list/tuple of ints"
        )

    # --- Sub-selection on the underlying tree ---
    @property
    def leaves(self) -> 'UTNodeSelector':
        """Expand this selection to the union of leaves under each selected node.

        If a selected node is itself a leaf, it is included. Order-preserving
        (left-to-right within each subtree, scenarios preserved in selection
        order) and de-duplicated. Enables chaining like
        ``uc.at_depth(1)[0].leaves.set_pfields(...)``.
        """
        rt = self._owner._rt
        leaf_set = set(rt.leaf_nodes)
        seen: set = set()
        result: list = []
        for n in self._ids:
            if n in leaf_set:
                if n not in seen:
                    seen.add(n)
                    result.append(n)
            else:
                for lf in rt.subtree_leaves(n):
                    if lf not in seen:
                        seen.add(lf)
                        result.append(lf)
        return type(self)(self._owner, tuple(result))

    # --- Composition (all preserve subclass) ---
    def filter(self, predicate: Callable[['NodeContext'], bool]) -> 'UTNodeSelector':
        """Keep nodes for which ``predicate(NodeContext)`` returns truthy."""
        total = len(self._ids)
        return type(self)(self._owner, tuple(
            n for i, n in enumerate(self._ids)
            if predicate(NodeContext(node=n, index=i, total=total))
        ))

    def where(self, mask: Iterable[bool]) -> 'UTNodeSelector':
        """Keep nodes where the corresponding mask entry is truthy."""
        mask_list = list(mask)
        if len(mask_list) != len(self._ids):
            raise ValueError(
                f"where() mask length mismatch: got {len(mask_list)}, "
                f"expected {len(self._ids)}"
            )
        return type(self)(
            self._owner,
            tuple(n for n, m in zip(self._ids, mask_list) if m),
        )

    def __or__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        seen = set(self._ids)
        tail = tuple(n for n in other._ids if n not in seen)
        return type(self)(self._owner, self._ids + tail)

    def __and__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        other_set = set(other._ids)
        return type(self)(self._owner, tuple(n for n in self._ids if n in other_set))

    def __sub__(self, other):
        if not isinstance(other, UTNodeSelector) or other._owner is not self._owner:
            return NotImplemented
        other_set = set(other._ids)
        return type(self)(self._owner, tuple(n for n in self._ids if n not in other_set))

    # --- UT-level mutators ---
    def make_rest(self):
        """Rest every node in the selection (and its subtree)."""
        return self._owner.make_rest(list(self._ids))

    def subdivide(self, S):
        """Subdivide every node in the selection with structure ``S``."""
        return self._owner.subdivide(list(self._ids), S)

    def sparsify(self, probability):
        """Sparsify leaves under the selection's nodes with ``probability``."""
        return self._owner.sparsify(probability, node=list(self._ids))


class UTNodeView:
    """View of UT nodes; subscripting returns a Chronon for that node."""

    def __init__(self, ut):
        self._ut = ut

    def __getitem__(self, node):
        return Chronon(node, self._ut)

    def __iter__(self):
        return iter(self._ut._rt.nodes)

    def __contains__(self, node):
        return node in self._ut._rt

    def __len__(self):
        return len(self._ut._rt)

    def __call__(self, data=False):
        if data:
            for node in self._ut._rt.nodes:
                yield (node, Chronon(node, self._ut))
        else:
            for node in self._ut._rt.nodes:
                yield node


class Chronon(metaclass=TemporalMeta):
    """
    A node in its temporal context within a :class:`TemporalUnit`.

    Exposes real-time onset/duration and metric data for any node (leaf or branch).
    Supports dict-like access (e.g. chronon['real_onset']) for compatibility.

    Parameters
    ----------
    node_id : int
        The node identifier within the rhythm tree.
    ut : TemporalUnit
        The parent temporal unit that owns this node.
    """
    __slots__ = ('_node_id', '_ut')

    def __init__(self, node_id: int, ut: 'TemporalUnit'):
        self._node_id = node_id
        self._ut = ut

    def _rt_node(self):
        return self._ut._rt[self._node_id]

    def _real_data(self):
        return self._ut._real_times.get(self._node_id, {})

    def __getattr__(self, key):
        if key in ('real_onset', 'real_duration'):
            return self._real_data()[key]
        try:
            return self._rt_node()[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' has no attribute '{key}'")

    def __getitem__(self, key):
        if key in ('real_onset', 'real_duration'):
            return self._real_data()[key]
        return self._rt_node()[key]

    def get(self, key, default=None):
        if key in ('real_onset', 'real_duration'):
            return self._real_data().get(key, default)
        return self._rt_node().get(key, default)

    def __contains__(self, key):
        if key in ('real_onset', 'real_duration'):
            return key in self._real_data()
        return key in self._rt_node()

    @property
    def start(self):
        """The absolute start time in seconds."""
        return abs(self.real_onset)

    @property
    def duration(self):
        """The absolute duration in seconds."""
        return abs(self.real_duration)

    @property
    def end(self):
        """The absolute end time in seconds."""
        return self.start + abs(self.duration)

    @property
    def proportion(self):
        """The integer proportion value from the rhythm tree."""
        return self._rt_node()['proportion']

    @property
    def metric_duration(self):
        """The fractional metric duration relative to the measure."""
        return self._rt_node()['metric_duration']

    @property
    def metric_onset(self):
        """The fractional metric onset relative to the measure."""
        return self._rt_node()['metric_onset']

    @property
    def node_id(self):
        """The node identifier within the parent rhythm tree."""
        return self._node_id

    @property
    def is_rest(self):
        """Whether this event is a rest (negative proportion)."""
        return self._rt_node()['proportion'] < 0

    def __str__(self):
        return pd.DataFrame({
            'node_id': [self.node_id],
            'start': [self.start],
            'duration': [self.duration], 
            'end': [self.end],
            'is_rest': [self.is_rest],
            'proportion': [self.proportion],
            'metric_onset': [self.metric_onset],
            'metric_duration': [self.metric_duration],
        }, index=['']).__str__()
    
    def __repr__(self):
        return self.__str__()


class TemporalUnit(metaclass=TemporalMeta):
    """
    A rhythmic structure bound to a tempo, producing real-time events.

    A ``TemporalUnit`` combines a :class:`RhythmTree` (defined by
    *tempus* and *prolatio*) with a tempo specification (*beat*, *bpm*)
    to produce concrete onset times and durations in seconds.

    Outside a :class:`~klotho.thetos.composition.score.Score`, a temporal
    unit always starts at time 0 and its duration is fixed after
    construction.  Placement within a timeline and duration adjustment are
    handled by :class:`~klotho.thetos.composition.score.ScoreItem` after
    the unit has been added to a Score.

    Parameters
    ----------
    span : int, float, or Fraction, optional
        Number of measures. Default is 1.
    tempus : Meas, Fraction, int, float, or str, optional
        The time signature. Default is ``'4/4'``.
    prolatio : tuple or str, optional
        The subdivision specification. A tuple gives explicit proportions;
        a string selects a preset (``'d'`` = duration, ``'r'`` = rest,
        ``'p'`` = pulse). Default is ``'d'``.
    beat : Fraction, int, float, str, or None, optional
        The beat reference for tempo calculation. When None, the
        denominator of the time signature is used. Default is None.
    bpm : int, float, or None, optional
        Beats per minute. Default is None (falls back to 60).

    Examples
    --------
    >>> ut = TemporalUnit(tempus='4/4', prolatio='p', bpm=120)
    >>> len(ut)
    4
    """
    def __init__(self,
                 span     : Union[int,float,Fraction]          = 1,
                 tempus   : Union[Meas,Fraction,int,float,str] = '4/4',
                 prolatio : Union[tuple,str]                   = 'd',
                 beat     : Union[None,Fraction,int,float,str] = None,
                 bpm      : Union[None,int,float]              = None,
        ):
        
        self._type   = None
        
        self._rt     = self._set_rt(span, abs(Meas(tempus)), prolatio)
        self._real_times = {}
        
        self._beat   = Fraction(beat) if beat else Fraction(1, self._rt.meas._denominator)
        self._bpm    = bpm if bpm else 60
        self._offset = 0.0

        self._timing_dirty = True
    
    @classmethod
    def from_rt(cls, rt:RhythmTree, beat = None, bpm = None):
        """
        Construct a ``TemporalUnit`` from an existing :class:`RhythmTree`.

        Parameters
        ----------
        rt : RhythmTree
            The rhythm tree to wrap.
        beat : Fraction, int, float, str, or None, optional
            Beat reference. Default is None.
        bpm : int, float, or None, optional
            Beats per minute. Default is None.

        Returns
        -------
        TemporalUnit
        """
        return cls(span     = rt.span,
                   tempus   = rt.meas,
                   prolatio = rt.subdivisions,
                   beat     = beat,
                   bpm      = bpm)
    
    _node_selector_class = UTNodeSelector

    @property
    def nodes(self):
        return UTNodeView(self)

    # ------------------------------------------------------------------
    # Node-returning traversal (returns selector bound to this UT/UC)
    # ------------------------------------------------------------------

    @property
    def leaves(self):
        """All leaves in left-to-right order (selector form of RT.leaf_nodes)."""
        return self._node_selector_class(self, self._rt.leaf_nodes)

    @property
    def root(self):
        """1-element selector for the root node.

        Chain mutations: ``uc.root.set_pfields(amp=0.3)``.
        """
        return self._node_selector_class(self, (self._rt.root,))

    def leaves_of(self, node: int):
        """Leaves of the subtree rooted at ``node`` (selector form of RT.subtree_leaves)."""
        return self._node_selector_class(self, self._rt.subtree_leaves(node))

    def at_depth(self, d: int, operator: str = '=='):
        """Nodes at a specific depth (selector form of RT.at_depth)."""
        return self._node_selector_class(self, self._rt.at_depth(d, operator))

    def successors(self, node: int):
        """Direct children of ``node`` (selector form of RT.successors)."""
        return self._node_selector_class(self, self._rt.successors(node))

    def select(self, *ids):
        """Build an ad-hoc selector from ints or a single iterable of ints."""
        if len(ids) == 1 and not isinstance(ids[0], int):
            return self._node_selector_class(self, tuple(ids[0]))
        return self._node_selector_class(self, ids)

    # ------------------------------------------------------------------
    # Non-node scalar forwards (unchanged return types)
    # ------------------------------------------------------------------

    @property
    def depth(self):
        """Maximum depth of the underlying RT."""
        return self._rt.depth

    @property
    def k(self):
        """Maximum branching factor of the underlying RT."""
        return self._rt.k

    def depth_of(self, node):
        """Depth of ``node`` in the underlying RT."""
        return self._rt.depth_of(node)

    def out_degree(self, node):
        """Out-degree of ``node`` in the underlying RT."""
        return self._rt.out_degree(node)

    def topological_sort(self):
        """Topological sort of the underlying RT's nodes."""
        return self._rt.topological_sort()

    @property
    def span(self):
        """The number of measures that the TemporalUnit spans."""
        return self._rt.span

    @property
    def tempus(self):
        """The time signature of the TemporalUnit."""
        return self._rt.meas
    
    @property
    def prolationis(self):        
        """The S-part of a RhythmTree which describes the subdivisions of the TemporalUnit."""
        return self._rt.subdivisions
    
    # @prolationis.setter
    # def prolationis(self, prolatio: Union[tuple, str]):
    #     self._rt = self._set_rt(self.span, self.tempus, prolatio)
    
    @property
    def rt(self):
        """The RhythmTree of the TemporalUnit (returns a copy)."""
        return self._rt.copy()

    @property
    def metric_durations(self):
        """The metric durations from the RhythmTree which describe the proportional durations of the TemporalUnit."""
        return self._rt.durations

    @property
    def metric_onsets(self):
        """The metric onsets from the RhythmTree which describe the proportional onset times of the TemporalUnit."""
        return self._rt.onsets

    @property
    def beat(self):
        """The rhythmic ratio that describes the beat of the TemporalUnit."""
        return self._beat
    
    @property
    def bpm(self):
        """The beats per minute of the TemporalUnit."""
        return self._bpm
    
    @property
    def type(self):
        """The type of the TemporalUnit."""
        return self._type
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds.

        Always ``0`` for a unit outside a Score.  Inside a Score the start
        time is assigned by placement kwargs on
        :meth:`~klotho.thetos.composition.score.Score.add`.
        """
        return self._offset
    
    @property
    def onsets(self):
        """The real-time onset of each leaf event in seconds."""
        self._ensure_timing_cache()
        return tuple(self._real_times[n]['real_onset'] for n in self._rt.leaf_nodes)

    @property
    def durations(self):
        """The real-time duration of each leaf event in seconds."""
        self._ensure_timing_cache()
        return tuple(self._real_times[n]['real_duration'] for n in self._rt.leaf_nodes)

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        return beat_duration(ratio      = str(self._rt.meas * self._rt.span),
                             beat_ratio = self.beat,
                             bpm        = self.bpm
                )
    
    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def time(self):
        """The absolute start and end times (in seconds) of the TemporalUnit."""
        return self._offset, self._offset + self.duration
    
    @property
    def events(self):
        """
        A :class:`~pandas.DataFrame` of all leaf events with timing and metric data.

        Returns
        -------
        pandas.DataFrame
        """
        events = self._materialize_events()
        return pd.DataFrame([{
            'node_id': c.node_id,
            'start': c.start,
            'duration': c.duration,
            'end': c.end,
            'is_rest': c.is_rest,
            's': c.proportion,
            'metric_onset': c.metric_onset,
            'metric_duration': c.metric_duration,
        } for c in events], index=range(len(events)))
        
    def _scale_bpm(self, factor: float) -> None:
        """Multiply bpm by ``factor`` (private; used by ``ScoreItem``).

        A factor of ``0.5`` halves the bpm, doubling the resulting duration.
        This method is deliberately private: outside a Score, a unit's
        duration is immutable; duration editing is mediated by
        :meth:`klotho.thetos.composition.score.ScoreItem.set_duration`.
        """
        self._bpm = self._bpm * factor
        self._invalidate_timing_cache()

    def make_rest(self, node) -> None:
        """
        Turn a node (or each node in an iterable) and all descendants into rests.

        Delegates to :meth:`RhythmTree.make_rest` and re-evaluates timing once
        at the end (batched across all provided nodes).

        Parameters
        ----------
        node : int or iterable of int
            A single node ID, or an iterable of node IDs, to convert to rests.

        Raises
        ------
        ValueError
            If any node is not found in the rhythm tree.
        """
        nodes = [node] if isinstance(node, int) else list(node)
        for n in nodes:
            self._rt.make_rest(n)
        self._invalidate_timing_cache()

    def subdivide(self, node: int, S) -> None:
        """
        Subdivide a leaf node with structure (D, S).

        Delegates to :meth:`RhythmTree.subdivide` and invalidates cached events.

        Parameters
        ----------
        node : int
            The leaf node to subdivide.
        S : tuple
            Valid subdivisions tuple (integers or nested (D, S) tuples).

        Raises
        ------
        ValueError
            If the node is not found or is not a leaf.
        """
        self._rt.subdivide(node, S)
        self._invalidate_timing_cache()

    def sparsify(self, probability, node=None):
        """
        Randomly convert leaf events to rests with a given probability.

        Parameters
        ----------
        probability : float
            Probability (0--1) that each eligible leaf becomes a rest.
        node : int, list of int, or None, optional
            Restrict to leaves under this node (or nodes). When None,
            all leaves are candidates. Default is None.
        """
        import numpy as _np
        if node is None:
            targets = list(self._rt.leaf_nodes)
        elif isinstance(node, int):
            targets = list(self._rt.subtree_leaves(node))
        else:
            seen = set()
            targets = []
            for n in node:
                for leaf in self._rt.subtree_leaves(n):
                    if leaf not in seen:
                        seen.add(leaf)
                        targets.append(leaf)

        targets = [n for n in targets
                   if self._rt[n].get('proportion', 1) >= 0]

        for leaf in targets:
            if _np.random.uniform() < probability:
                self.make_rest(leaf)

    def _set_rt(self, span:int, tempus:Union[Meas,Fraction,str], prolatio:Union[tuple,str]) -> RhythmTree:
        match prolatio:
            case tuple():
                self._type = ProlatioTypes.SUBDIVISION
                return RhythmTree(span = span, meas = tempus, subdivisions = prolatio)
            
            case str():
                prolatio = prolatio.lower()
                match prolatio:
                    case p if p.lower() in ProlatioTypes.PULSTYPES.value:
                        self._type = ProlatioTypes.PULSE
                        return RhythmTree(
                            span = span,
                            meas = tempus,
                            subdivisions = (1,) * tempus._numerator
                        )
                    
                    case d if d.lower() in ProlatioTypes.DURTYPES.value:
                        self._type = ProlatioTypes.DURATION
                        return RhythmTree(
                            span = span,
                            meas = tempus,
                            subdivisions = (1,)
                        )
                    
                    case r if r.lower() in ProlatioTypes.RESTYPES.value:
                        self._type = ProlatioTypes.REST
                        return RhythmTree(
                            span = span,
                            meas = tempus,
                            subdivisions = (-1,)
                        )
                    
                    case _:
                        raise ValueError(f'Invalid string: {prolatio}')
            
            case _:
                raise ValueError(f'Invalid prolatio type: {type(prolatio)}')

    def _compute_timing_cache(self):
        """Recompute real-time onset/duration cache for all nodes."""
        self._real_times.clear()
        for node in self._rt.nodes:
            metric_duration = self._rt[node]['metric_duration']
            metric_onset = self._rt[node]['metric_onset']
            
            real_duration = beat_duration(ratio=metric_duration, bpm=self.bpm, beat_ratio=self.beat)
            real_onset = beat_duration(ratio=metric_onset, bpm=self.bpm, beat_ratio=self.beat) + self._offset
            
            self._real_times[node] = {'real_duration': real_duration, 'real_onset': real_onset}
        self._timing_dirty = False

    def _ensure_timing_cache(self):
        if self._timing_dirty or len(self._real_times) != len(self._rt):
            self._compute_timing_cache()

    def _event_context(self):
        self._ensure_timing_cache()
        return None

    def _make_event(self, node_id: int, event_context=None):
        return Chronon(node_id, self)

    def _materialize_events(self):
        """Materialize leaf Chronons lazily from current tree state."""
        leaf_nodes = tuple(self._rt.leaf_nodes)
        event_context = self._event_context()
        return tuple(self._make_event(node_id, event_context) for node_id in leaf_nodes)

    def _invalidate_timing_cache(self):
        self._timing_dirty = True

    def __getitem__(self, idx):
        leaf_nodes = tuple(self._rt.leaf_nodes)
        event_context = self._event_context()
        if isinstance(idx, slice):
            return tuple(self._make_event(node_id, event_context) for node_id in leaf_nodes[idx])
        return self._make_event(leaf_nodes[idx], event_context)
    
    def __iter__(self):
        leaf_nodes = tuple(self._rt.leaf_nodes)
        event_context = self._event_context()
        for node_id in leaf_nodes:
            yield self._make_event(node_id, event_context)
    
    def __len__(self):
        return len(self._rt.leaf_nodes)
        
    def __str__(self):
        result = (
            f'Tempus:   {self._rt.meas}' + (f' (x{self._rt.span})' if self._rt.span > 1 else '') + '\n' +
            f'Prolatio: {self._type.value}\n' +
            f'Events:   {len(self)}\n' +
            f'Tempo:    {self._beat} = {self._bpm}\n' +
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n' +
            f'{"-" * 50}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()

    def repeat(self, n):
        """
        Create a :class:`TemporalUnitSequence` of *n* copies of this unit.

        Parameters
        ----------
        n : int
            Number of repetitions.

        Returns
        -------
        TemporalUnitSequence
        """
        uts = TemporalUnitSequence()
        uts.extend([self] * n)
        return uts

    def copy(self):
        """Create a deep copy of this TemporalUnit.

        The copy preserves any internal placement (``_offset``) so that
        containers like :class:`TemporalUnitSequence` can rebuild cleanly.
        """
        c = TemporalUnit(
            span=self.span,
            tempus=self.tempus,
            prolatio=self.prolationis,
            beat=self.beat,
            bpm=self.bpm,
        )
        c._offset = self._offset
        c._invalidate_timing_cache()
        return c


class TemporalUnitSequence(metaclass=TemporalMeta):
    """
    An ordered sequence of :class:`TemporalUnit` objects representing
    consecutive temporal events.

    Units are automatically offset so that each begins where the previous
    one ends.  Outside a :class:`~klotho.thetos.composition.score.Score`,
    a sequence always starts at time 0 and its duration is fixed after
    construction.

    Parameters
    ----------
    ut_seq : list of TemporalUnit, optional
        Initial sequence of temporal units. Default is an empty list.
    """
    
    def __init__(self, ut_seq:Union[list[TemporalUnit], None]=None):
        if ut_seq is None:
            ut_seq = []
        self._seq    = [ut.copy() for ut in ut_seq]
        self._offset = 0.0
        self._set_offsets()
    
    def _set_offsets(self):
        """Updates the offsets of all members based on their position in the sequence.

        Members may be ``TemporalUnit``, ``CompositionalUnit``,
        ``TemporalUnitSequence``, or ``TemporalBlock``; ``_reoffset``
        dispatches the correct cascade for each.
        """
        running_offset = self._offset
        for ut in self._seq:
            _reoffset(ut, running_offset)
            running_offset += ut.duration

    @property
    def seq(self):
        """The list of TemporalUnit objects in the sequence."""
        return self._seq

    @property
    def onsets(self):
        """A tuple of onset times (in seconds) for each TemporalUnit in the sequence."""
        return calc_onsets(self.durations)
    
    @property    
    def durations(self):
        """A tuple of durations (in seconds) for each TemporalUnit in the sequence."""
        return tuple(ut.duration for ut in self._seq)
    
    @property
    def duration(self):
        """The total duration (in seconds) of the sequence."""
        return sum(abs(d) for d in self.durations)
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds (``0`` outside a Score)."""
        return self._offset

    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def size(self):
        """The total number of events across all TemporalUnits in the sequence."""
        return sum(len(ut) for ut in self._seq)
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the sequence."""
        return self._offset, self._offset + self.duration

    def _scale_bpm(self, factor: float) -> None:
        """Multiply every member's bpm by ``factor`` and recompute offsets.

        Private; used by :class:`~klotho.thetos.composition.score.ScoreItem`
        to stretch a sequence's total duration while preserving the relative
        durations between its members.
        """
        for ut in self._seq:
            ut._scale_bpm(factor)
        self._set_offsets()

    
    def append(self, ut: TemporalUnit, repeat: int = 1) -> None:
        """
        Append a temporal unit to the end of the sequence.

        Parameters
        ----------
        ut : TemporalUnit
            The unit to append.
        repeat : int, optional
            Number of independent copies to append. Default is 1.
        """
        for _ in range(repeat):
            self._seq.append(ut.copy())
        self._set_offsets()
        
    def prepend(self, ut: TemporalUnit) -> None:
        """
        Prepend a temporal unit to the beginning of the sequence.

        Parameters
        ----------
        ut : TemporalUnit
            The unit to prepend.
        """
        self._seq.insert(0, ut.copy())
        self._set_offsets()
        
    def insert(self, index: int, ut: TemporalUnit) -> None:
        """
        Insert a temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The position at which to insert.
        ut : TemporalUnit
            The unit to insert.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index <= len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.insert(index, ut.copy())
        self._set_offsets()
        
    def remove(self, index: int) -> None:
        """
        Remove the temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The index of the unit to remove.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.pop(index)
        self._set_offsets()
        
    def replace(self, index: int, ut: TemporalUnit) -> None:
        """
        Replace the temporal unit at the specified index.

        Parameters
        ----------
        index : int
            The index of the unit to replace.
        ut : TemporalUnit
            The replacement unit.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq[index] = ut.copy()
        self._set_offsets()
        
    def extend(self, other_seq, repeat: int = 1) -> None:
        """
        Extend the sequence by appending all units from another iterable.

        Parameters
        ----------
        other_seq : TemporalUnitSequence or iterable of TemporalUnit
            The source of units to append.
        repeat : int, optional
            Number of times to repeat the extension. Default is 1.
        """
        for _ in range(repeat):
            for ut in other_seq:
                self._seq.append(ut.copy())
        self._set_offsets()

    def __getitem__(self, idx: int) -> TemporalUnit:
        return self._seq[idx]
    
    def __setitem__(self, idx: int, ut: TemporalUnit) -> None:
        self._seq[idx] = ut.copy()
        self._set_offsets()

    def __iter__(self):
        return iter(self._seq)
    
    def __len__(self):
        return len(self._seq)

    def __str__(self):
        return pd.DataFrame([{
            'Tempus': ut.tempus,
            'Type': ut.type.name[0] if ut.type else '',
            'Tempo': f'{ut.beat} = {round(ut.bpm, 3)}',
            'Start': seconds_to_hmsms(ut.time[0]),
            'End': seconds_to_hmsms(ut.time[1]),
            'Duration': seconds_to_hmsms(ut.duration),
        } for ut in self._seq]).__str__()

    def __repr__(self):
        return self.__str__()

    def copy(self):
        """Create a deep copy of this TemporalUnitSequence.

        Internal placement (``_offset``) is preserved on the copy so that
        :class:`TemporalBlock` and :class:`~klotho.thetos.composition.score.Score`
        can rebuild their layouts cleanly.
        """
        c = TemporalUnitSequence(ut_seq=[ut.copy() for ut in self._seq])
        c._offset = self._offset
        c._set_offsets()
        return c


class TemporalBlock(metaclass=TemporalMeta):
    """
    A collection of parallel temporal structures representing simultaneous events.

    Each row can be a :class:`TemporalUnit`, :class:`TemporalUnitSequence`,
    or another ``TemporalBlock``. Rows are aligned according to the *axis*
    parameter and optionally sorted by duration.

    Parameters
    ----------
    rows : list, optional
        Temporal structures (``TemporalUnit``, ``TemporalUnitSequence``,
        or ``TemporalBlock``). Default is an empty list.
    axis : float, optional
        Alignment axis from -1 (left) through 0 (center) to 1 (right).
        Default is -1.
    sort_rows : bool, optional
        Whether to sort rows by duration (longest first). Default is True.

    Notes
    -----
    Outside a :class:`~klotho.thetos.composition.score.Score`, a block
    always starts at time 0 and its total duration is fixed after
    construction.
    """
    
    def __init__(self,
                 rows:Union[list[Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']], None]=None,
                 axis:float = -1,
                 sort_rows:bool=True):
        if rows is None:
            rows = []
        self._rows = [row.copy() for row in rows] if rows else []
        self._axis = axis
        self._offset = 0.0
        self._sort_rows = sort_rows
        
        self._align_rows()
      
    # TODO: make free method in UT algos
    # Matrix to Block
    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, beat=None, bpm=None):
        """
        Create a ``TemporalBlock`` from a matrix of tree specifications.

        Parameters
        ----------
        matrix : tuple of tuple
            Matrix where each element is a ``(D, S)`` pair.
        meas_denom : int, optional
            Denominator for measure fractions. Default is 1.
        subdiv : bool, optional
            Whether to apply automatic subdivision. Default is False.
        rotation_offset : int, optional
            Offset for rotation calculations. Default is 1.
        beat : Fraction, str, float, or None, optional
            Beat ratio specification. Default is None.
        bpm : int, float, or None, optional
            Beats per minute. Default is None.

        Returns
        -------
        TemporalBlock
        """
        tb = []
        for i, row in enumerate(matrix):
            seq = []
            for j, e in enumerate(row):
                offset = rotation_offset * i
                if subdiv:
                    D, S = e[0], auto_subdiv(e[1][::-1], offset - j - i)
                else:
                    D, S = e[0], e[1]
                seq.append(TemporalUnit(tempus   = Meas(abs(D), meas_denom),
                                        prolatio = S if D > 0 else 'r',
                                        bpm      = bpm,
                                        beat     = beat))
            tb.append(TemporalUnitSequence(seq))
        return cls(tuple(tb))

    def _align_rows(self):
        """
        Aligns the rows based on the current axis value and optionally sorts them by duration.
        If sorting is enabled, the longest duration will be at the bottom (index 0), 
        shortest at the top. If two rows have the same duration, their original order is preserved.
        """
        if not self._rows:
            return

        row_duration_pairs = [(row, row.duration) for row in self._rows]
        if self._sort_rows:
            row_duration_pairs = sorted(row_duration_pairs, key=lambda pair: -pair[1], reverse=False)
            self._rows = [pair[0] for pair in row_duration_pairs]

        max_duration = max(duration for _, duration in row_duration_pairs)

        for row, row_duration in row_duration_pairs:
            if row_duration == max_duration:
                _reoffset(row, self._offset)
                continue

            duration_diff = max_duration - row_duration
            adjustment = duration_diff * (self._axis + 1) / 2
            _reoffset(row, self._offset + adjustment)

    @property
    def height(self):
        """The number of rows in the block."""
        return len(self._rows)
    
    @property
    def rows(self):
        """The list of temporal structures in the block."""
        return self._rows

    @property
    def duration(self):
        """The total duration (in seconds) of the longest row in the block."""
        return max(row.duration for row in self._rows) if self._rows else 0.0

    @property
    def axis(self):
        """The temporal axis position of the block."""
        return self._axis
    
    @property
    def start(self) -> float:
        """Absolute start time in seconds (``0`` outside a Score)."""
        return self._offset

    @property
    def end(self) -> float:
        """Absolute end time in seconds (``start + duration``)."""
        return self._offset + self.duration

    @property
    def sort_rows(self):
        """Whether to sort rows by duration (longest at index 0)."""
        return self._sort_rows
    
    @sort_rows.setter
    def sort_rows(self, sort_rows:bool):
        self._sort_rows = sort_rows
        self._align_rows()
        
    @axis.setter
    def axis(self, axis: float):
        """
        Set the temporal axis and realign rows.

        Parameters
        ----------
        axis : float
            Value between -1 and 1 controlling alignment:
            -1 = left-aligned, 0 = centered, 1 = right-aligned.

        Raises
        ------
        ValueError
            If *axis* is outside [-1, 1].
        """
        if not -1 <= axis <= 1:
            raise ValueError("Axis must be between -1 and 1")
        self._axis = float(axis)
        self._align_rows()

    def _scale_bpm(self, factor: float) -> None:
        """Multiply every row's bpm(s) by ``factor`` and realign.

        Private; used by :class:`~klotho.thetos.composition.score.ScoreItem`
        to stretch a block's total duration while preserving the relative
        durations of its rows.
        """
        for row in self._rows:
            row._scale_bpm(factor)
        self._align_rows()

    def prepend(self, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Add a temporal structure at the beginning (index 0) of the block.

        Parameters
        ----------
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to prepend.
        """
        self._rows.insert(0, row.copy())
        self._align_rows()
        
    def append(self, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Add a temporal structure at the end (highest index) of the block.

        Parameters
        ----------
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to append.
        """
        self._rows.append(row.copy())
        self._align_rows()
        
    def insert(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Insert a temporal structure at the specified index.

        Parameters
        ----------
        index : int
            The position at which to insert.
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The temporal structure to insert.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index <= len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.insert(index, row.copy())
        self._align_rows()

    def remove(self, index: int) -> None:
        """
        Remove the row at the specified index.

        Parameters
        ----------
        index : int
            The index of the row to remove.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.pop(index)
        self._align_rows()
        
    def replace(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Replace the row at the specified index.

        Parameters
        ----------
        index : int
            The index of the row to replace.
        row : TemporalUnit, TemporalUnitSequence, or TemporalBlock
            The replacement temporal structure.

        Raises
        ------
        IndexError
            If the index is out of range.
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows[index] = row.copy()
        self._align_rows()
        
    def extend(self, other_block: 'TemporalBlock') -> None:
        """
        Extend the block by appending all rows from another block.

        Parameters
        ----------
        other_block : TemporalBlock
            The block whose rows will be appended.
        """
        for row in other_block:
            self._rows.append(row.copy())
        self._align_rows()

    def __getitem__(self, idx: int) -> Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']:
        return self._rows[idx]

    def __iter__(self):
        return iter(self._rows)
    
    def __len__(self):
        return len(self._rows)
    
    def __str__(self):
        result = (
            f'Rows:     {len(self._rows)}\n'
            f'Axis:     {self._axis}\n'
            f'Duration: {seconds_to_hmsms(self.duration)}\n'
            f'Time:     {seconds_to_hmsms(self._offset)} - {seconds_to_hmsms(self._offset + self.duration)}\n'
            f'{"-" * 50}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()

    def copy(self):
        """Create a deep copy of this TemporalBlock.

        Internal placement (``_offset``) is preserved on the copy so that
        :class:`~klotho.thetos.composition.score.Score` can rebuild its
        timeline cleanly.
        """
        c = TemporalBlock(
            rows=[row.copy() for row in self._rows],
            axis=self._axis,
            sort_rows=self._sort_rows,
        )
        c._offset = self._offset
        c._align_rows()
        return c


def _reoffset(unit, t: float) -> None:
    """Assign ``t`` as the internal offset of *unit* and cascade.

    Used by containers (``TemporalBlock``) and
    :class:`~klotho.thetos.composition.score.Score` to position a unit at
    an absolute time without going through a public setter.
    """
    unit._offset = float(t)
    if isinstance(unit, TemporalUnitSequence):
        unit._set_offsets()
    elif isinstance(unit, TemporalBlock):
        unit._align_rows()
    elif hasattr(unit, '_invalidate_timing_cache'):
        unit._invalidate_timing_cache()
