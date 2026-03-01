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
from fractions import Fraction
from typing import Union
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
    and an optional time *offset* to produce concrete onset times and
    durations in seconds.

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
    offset : float, optional
        Absolute start time in seconds. Default is 0.

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
                 offset   : float                              = 0
        ):
        
        self._type   = None
        
        self._rt     = self._set_rt(span, abs(Meas(tempus)), prolatio)
        self._real_times = {}
        
        self._beat   = Fraction(beat) if beat else Fraction(1, self._rt.meas._denominator)
        self._bpm    = bpm if bpm else 60
        self._offset = offset

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
    
    _RT_QUERY_METHODS = frozenset({
        'leaf_nodes', 'at_depth', 'subtree_leaves', 'successors',
        'descendants', 'ancestors', 'parent', 'depth', 'depth_of',
        'k', 'root', 'out_degree', 'topological_sort', 'branch',
    })

    @property
    def nodes(self):
        return UTNodeView(self)

    def __getattr__(self, name):
        if name in TemporalUnit._RT_QUERY_METHODS:
            try:
                rt = object.__getattribute__(self, '_rt')
            except AttributeError:
                raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
            return getattr(rt, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __dir__(self):
        return list(super().__dir__()) + list(self._RT_QUERY_METHODS) + ['nodes']

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
    def offset(self):
        """The offset (or absolute start time) in seconds of the TemporalUnit."""
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
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the TemporalUnit."""
        self._offset = offset
        self._invalidate_timing_cache()
        
    def set_duration(self, target_duration: float) -> None:
        """
        Set the tempo (bpm) to achieve a specific total duration.

        Calculates and sets the appropriate bpm so that this unit's
        total duration matches *target_duration*.

        Parameters
        ----------
        target_duration : float
            The desired duration in seconds.

        Raises
        ------
        ValueError
            If *target_duration* is not positive.
        """
        if target_duration <= 0:
            raise ValueError("Target duration must be positive")
            
        current_duration = self.duration
        ratio = current_duration / target_duration
        new_bpm = self._bpm * ratio
        self._bpm = new_bpm
        self._invalidate_timing_cache()

    def make_rest(self, node: int) -> None:
        """
        Turn a node and all its descendants into rests.

        Delegates to :meth:`RhythmTree.make_rest` and re-evaluates timing.

        Parameters
        ----------
        node : int
            The node ID to convert to a rest.

        Raises
        ------
        ValueError
            If the node is not found in the rhythm tree.
        """
        self._rt.make_rest(node)
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
        """Create a deep copy of this TemporalUnit."""
        # return copy.deepcopy(self)
        return TemporalUnit(span=self.span, tempus=self.tempus, prolatio=self.prolationis, beat=self.beat, bpm=self.bpm, offset=self.offset)


class TemporalUnitSequence(metaclass=TemporalMeta):
    """
    An ordered sequence of :class:`TemporalUnit` objects representing
    consecutive temporal events.

    Units are automatically offset so that each begins where the previous
    one ends.

    Parameters
    ----------
    ut_seq : list of TemporalUnit, optional
        Initial sequence of temporal units. Default is an empty list.
    offset : float, optional
        Absolute start time in seconds. Default is 0.
    """
    
    def __init__(self, ut_seq:Union[list[TemporalUnit], None]=None, offset:float=0):
        if ut_seq is None:
            ut_seq = []
        self._seq    = [ut.copy() for ut in ut_seq] # XXX - this needs to be ut.copy()
        self._offset = offset
        self._set_offsets()
    
    def _set_offsets(self):
        """Updates the offsets of all TemporalUnits based on their position in the sequence."""
        running_offset = self._offset
        for ut in self._seq:
            ut.offset = running_offset
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
    def offset(self):
        """The offset (or absolute start time) in seconds of the sequence."""
        return self._offset
    
    @property
    def size(self):
        """The total number of events across all TemporalUnits in the sequence."""
        return sum(len(ut) for ut in self._seq)
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the sequence."""
        return self.offset, self.offset + self.duration
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the sequence."""
        self._offset = offset
        self._set_offsets()
    
    def set_duration(self, target_duration: float) -> None:
        """
        Scale the tempo of all units to achieve a specific total duration.

        Relative durations between units are preserved by applying the same
        scaling factor to every bpm value.

        Parameters
        ----------
        target_duration : float
            The desired total duration in seconds.

        Raises
        ------
        ValueError
            If *target_duration* is not positive or the sequence is empty.
        """
        if target_duration <= 0:
            raise ValueError("Target duration must be positive")
        
        if not self._seq:
            raise ValueError("Cannot set duration of empty sequence")
            
        current_duration = self.duration
        ratio = current_duration / target_duration
        
        for ut in self._seq:
            ut._bpm = ut.bpm * ratio
            ut._invalidate_timing_cache()
        
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
        """Create a deep copy of this TemporalUnitSequence."""
        return TemporalUnitSequence(ut_seq=[ut.copy() for ut in self._seq], offset=self._offset)


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
    offset : float, optional
        Initial time offset in seconds. Default is 0.
    sort_rows : bool, optional
        Whether to sort rows by duration (longest first). Default is True.
    """
    
    def __init__(self, rows:Union[list[Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']], None]=None, axis:float = -1, offset:float=0, sort_rows:bool=True):
        if rows is None:
            rows = []
        self._rows = [row.copy() for row in rows] if rows else [] # XXX - this needs to be row.copy()
        self._axis = axis
        self._offset = offset
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
                row.offset = self._offset
                continue

            duration_diff = max_duration - row_duration
            adjustment = duration_diff * (self._axis + 1) / 2
            row.offset = self._offset + adjustment

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
    def offset(self):
        """The offset (or absolute start time) in seconds of the block."""
        return self._offset

    @property
    def sort_rows(self):
        """Whether to sort rows by duration (longest at index 0)."""
        return self._sort_rows
    
    @sort_rows.setter
    def sort_rows(self, sort_rows:bool):
        self._sort_rows = sort_rows
        self._align_rows()
        
    @offset.setter
    def offset(self, offset):
        """Sets the offset (or absolute start time) in seconds of the block."""
        self._offset = offset
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
        
    def set_duration(self, target_duration: float) -> None:
        """
        Scale the tempo of all rows to achieve a specific total duration.

        Relative durations between rows are preserved by applying the same
        scaling factor.

        Parameters
        ----------
        target_duration : float
            The desired total duration in seconds.

        Raises
        ------
        ValueError
            If *target_duration* is not positive or the block is empty.
        """
        if target_duration <= 0:
            raise ValueError("Target duration must be positive")
        
        if not self._rows:
            raise ValueError("Cannot set duration of empty block")
            
        current_duration = self.duration
        ratio = current_duration / target_duration
        
        for row in self._rows:
            if hasattr(row, 'set_duration'):
                row_target = row.duration / ratio
                row.set_duration(row_target)
        
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
        """Create a deep copy of this TemporalBlock."""
        return TemporalBlock(rows=[row.copy() for row in self._rows], axis=self._axis, offset=self._offset, sort_rows=self._sort_rows)
