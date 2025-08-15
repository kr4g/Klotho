# ------------------------------------------------------------------------
# Klotho/klotho/chronos/temporal_units/ut.py
# ------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Temporal Units
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms import auto_subdiv
from klotho.chronos.utils import calc_onsets, beat_duration, seconds_to_hmsms

from enum import Enum
import pandas as pd
import copy

class ProlatioTypes(Enum):
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


class Chronon(metaclass=TemporalMeta):
    __slots__ = ('_node_id', '_rt')
    
    def __init__(self, node_id:int, rt:RhythmTree):
        self._node_id = node_id
        self._rt = rt
    
    @property
    def start(self): return abs(self._rt[self._node_id]['real_onset'])
    @property
    def duration(self): return abs(self._rt[self._node_id]['real_duration'])
    @property
    def end(self): return self.start + abs(self.duration)
    @property
    def proportion(self): return self._rt[self._node_id]['proportion']
    @property
    def metric_duration(self): return self._rt[self._node_id]['metric_duration']
    @property
    def metric_onset(self): return self._rt[self._node_id]['metric_onset']
    @property
    def node_id(self): return self._node_id
    @property
    def is_rest(self): return self._rt[self._node_id]['proportion'] < 0
    
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
        
        self._beat   = Fraction(beat) if beat else Fraction(1, self._rt.meas._denominator)
        self._bpm    = bpm if bpm else 60
        self._offset = offset
        
        self._events = None
    
    @classmethod
    def from_rt(cls, rt:RhythmTree, beat = None, bpm = None):
        return cls(span     = rt.span,
                   tempus   = rt.meas,
                   prolatio = rt.subdivisions,
                   beat     = beat,
                   bpm      = bpm)
    
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
    #     self._events = self._set_nodes()
    
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
        return tuple(self._rt[n]['real_onset'] for n in self._rt.leaf_nodes)

    @property
    def durations(self):
        return tuple(self._rt[n]['real_duration'] for n in self._rt.leaf_nodes)

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
        if self._events is None:
            self._events = self._evaluate()
        return pd.DataFrame([{
            'node_id': c.node_id,
            'start': c.start,
            'duration': c.duration,
            'end': c.end,
            'is_rest': c.is_rest,
            's': c.proportion,
            'metric_onset': c.metric_onset,
            'metric_duration': c.metric_duration,
        } for c in self._events], index=range(len(self._events)))
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the TemporalUnit."""
        self._offset = offset
        self._events = None
        
    def set_duration(self, target_duration: float) -> None:
        """
        Sets the tempo (bpm) to achieve a specific duration in seconds.
        
        This method calculates and sets the appropriate bpm value so that
        the TemporalUnit's total duration matches the target duration.
        
        Args:
            target_duration: The desired duration in seconds
            
        Raises:
            ValueError: If target_duration is not positive
        """
        if target_duration <= 0:
            raise ValueError("Target duration must be positive")
            
        current_duration = self.duration
        ratio = current_duration / target_duration
        new_bpm = self._bpm * ratio
        self._bpm = new_bpm
        self._events = None

    def make_rest(self, node: int) -> None:
        """
        Make a node and all its descendants into rests by setting their proportions to negative.
        
        This method calls the RhythmTree's make_rest method and then re-evaluates the
        TemporalUnit to update the timing information.
        
        Args:
            node: The node ID to make into a rest along with all its descendants
            
        Raises:
            ValueError: If the node is not found in the rhythm tree
        """
        self._rt.make_rest(node)
        self._events = None

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

    def _evaluate(self):
        """Updates node timings and returns chronon events."""
        for node in self._rt.nodes:
            metric_duration = self._rt[node]['metric_duration']
            metric_onset = self._rt[node]['metric_onset']
            
            real_duration = beat_duration(ratio=metric_duration, bpm=self.bpm, beat_ratio=self.beat)
            real_onset = beat_duration(ratio=metric_onset, bpm=self.bpm, beat_ratio=self.beat) + self._offset
            
            self._rt[node]['real_duration'] = real_duration
            self._rt[node]['real_onset'] = real_onset

        return tuple(Chronon(node_id, self._rt) for node_id in self._rt.leaf_nodes)

    def __getitem__(self, idx: int) -> Chronon:
        if self._events is None:
            self._events = self._evaluate()
        return self._events[idx]
    
    def __iter__(self):
        if self._events is None:
            self._events = self._evaluate()
        return iter(self._events)
    
    def __len__(self):
        if self._events is None:
            self._events = self._evaluate()
        return len(self._events)
        
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

    def copy(self):
        """Create a deep copy of this TemporalUnit."""
        return copy.deepcopy(self)


class TemporalUnitSequence(metaclass=TemporalMeta):
    """A sequence of TemporalUnit objects that represent consecutive temporal events."""
    
    def __init__(self, ut_seq:list[TemporalUnit]=[], offset:float=0):
        self._seq    = [ut for ut in ut_seq] # XXX - this needs to be ut.copy()
        self._offset = offset
        self._set_offsets()
    
    def _set_offsets(self):
        """Updates the offsets of all TemporalUnits based on their position in the sequence."""
        for i, ut in enumerate(self._seq):
            ut.offset = self._offset + sum(self.durations[j] for j in range(i))

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
        Sets the tempo (bpm) of all TemporalUnits to achieve a specific total duration in seconds.
        
        This method calculates and sets the appropriate bpm values for all TemporalUnits
        in the sequence so that the total duration matches the target duration.
        The relative durations between units are preserved by scaling all bpm values
        by the same factor.
        
        Args:
            target_duration: The desired total duration in seconds
            
        Raises:
            ValueError: If target_duration is not positive or if sequence is empty
        """
        if target_duration <= 0:
            raise ValueError("Target duration must be positive")
        
        if not self._seq:
            raise ValueError("Cannot set duration of empty sequence")
            
        current_duration = self.duration
        ratio = current_duration / target_duration
        
        for ut in self._seq:
            ut._bpm = ut.bpm * ratio
            ut._events = None
        
        self._set_offsets()
        
    def append(self, ut: TemporalUnit) -> None:
        """
        Append a TemporalUnit to the end of the sequence.
        
        Args:
            ut: The TemporalUnit to append
        """
        self._seq.append(ut.copy())
        self._set_offsets()
        
    def prepend(self, ut: TemporalUnit) -> None:
        """
        Prepend a TemporalUnit to the beginning of the sequence.
        
        Args:
            ut: The TemporalUnit to prepend
        """
        self._seq.insert(0, ut.copy())
        self._set_offsets()
        
    def insert(self, index: int, ut: TemporalUnit) -> None:
        """
        Insert a TemporalUnit at the specified index in the sequence.
        
        Args:
            index: The index at which to insert the TemporalUnit
            ut: The TemporalUnit to insert
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._seq) <= index <= len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.insert(index, ut.copy())
        self._set_offsets()
        
    def remove(self, index: int) -> None:
        """
        Remove the TemporalUnit at the specified index.
        
        Args:
            index: The index of the TemporalUnit to remove
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq.pop(index)
        self._set_offsets()
        
    def replace(self, index: int, ut: TemporalUnit) -> None:
        """
        Replace the TemporalUnit at the specified index with a new one.
        
        Args:
            index: The index of the TemporalUnit to replace
            ut: The new TemporalUnit
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._seq) <= index < len(self._seq):
            raise IndexError(f"Index {index} out of range for sequence of length {len(self._seq)}")
        
        self._seq[index] = ut.copy()
        self._set_offsets()
        
    def extend(self, other_seq: 'TemporalUnitSequence') -> None:
        """
        Extend the sequence by appending all TemporalUnits from another sequence.
        
        Args:
            other_seq: The TemporalUnitSequence to extend from
        """
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
        return copy.deepcopy(self)


class TemporalBlock(metaclass=TemporalMeta):
    """
    A collection of parallel temporal structures that represent simultaneous temporal events.
    Each row can be a TemporalUnit, TemporalUnitSequence, or another TemporalBlock.
    """
    
    def __init__(self, rows:list[Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']]=[], axis:float = -1, offset:float=0, sort_rows:bool=True):
        """
        Initialize a TemporalBlock with rows of temporal structures.
        
        Args:
            rows: List of temporal structures (TemporalUnit, TemporalUnitSequence, or TemporalBlock)
            offset: Initial time offset in seconds
            sort_rows: Whether to sort rows by duration (longest at index 0)
        """
        self._rows = [row for row in rows] if rows else [] # XXX - this needs to be row.copy()
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
        Creates a TemporalBlock from a matrix of tree specifications.
        
        Args:
            matrix: Input matrix containing duration and subdivision specifications
            meas_denom: Denominator for measure fractions
            subdiv: Whether to automatically generate subdivisions
            rotation_offset: Offset for rotation calculations
            bpm: bpm in beats per minute
            beat: Beat ratio specification
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
        
        if self._sort_rows:
            self._rows = sorted(self._rows, key=lambda row: -row.duration, reverse=False)
        
        max_duration = self.duration
        
        for row in self._rows:
            if row.duration == max_duration:
                row.offset = self._offset
                continue
            
            duration_diff = max_duration - row.duration    
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
        Sets the temporal axis position of the block and realigns rows.
        
        Args:
            axis: Float between -1 and 1, where:
                -1: rows start at block offset (left-aligned)
                 0: rows are centered within the block
                 1: rows end at block offset + duration (right-aligned)
                Any value in between creates a proportional alignment
        """
        if not -1 <= axis <= 1:
            raise ValueError("Axis must be between -1 and 1")
        self._axis = float(axis)
        self._align_rows()
        
    def set_duration(self, target_duration: float) -> None:
        """
        Sets the tempo (bpm) of all rows to achieve a specific total duration in seconds.
        
        This method calculates and sets the appropriate bpm values for all rows
        in the block so that the total duration matches the target duration.
        The relative durations between rows are preserved by scaling all bpm values
        by the same factor.
        
        Args:
            target_duration: The desired total duration in seconds
            
        Raises:
            ValueError: If target_duration is not positive or if block is empty
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
        Add a temporal structure at the beginning of the block (index 0).
        
        Note: In this implementation, index 0 is considered the "bottom" row.
        
        Args:
            row: The temporal structure to add (TemporalUnit, TemporalUnitSequence, or TemporalBlock)
        """
        self._rows.insert(0, row.copy())
        self._align_rows()
        
    def append(self, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Add a temporal structure at the end of the block (highest index).
        
        Note: In this implementation, the highest index is considered the "top" row.
        
        Args:
            row: The temporal structure to add (TemporalUnit, TemporalUnitSequence, or TemporalBlock)
        """
        self._rows.append(row.copy())
        self._align_rows()
        
    def insert(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Insert a temporal structure at the specified index in the block.
        
        Note: Index 0 is the first row (bottom), with higher indices moving upward.
        
        Args:
            index: The index at which to insert the row
            row: The temporal structure to insert
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._rows) <= index <= len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.insert(index, row.copy())
        self._align_rows()

    def remove(self, index: int) -> None:
        """
        Remove the row at the specified index.
        
        Args:
            index: The index of the row to remove
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows.pop(index)
        self._align_rows()
        
    def replace(self, index: int, row: Union[TemporalUnit, TemporalUnitSequence, 'TemporalBlock']) -> None:
        """
        Replace the row at the specified index with a new one.
        
        Args:
            index: The index of the row to replace
            row: The new temporal structure
            
        Raises:
            IndexError: If the index is out of range
        """
        if not -len(self._rows) <= index < len(self._rows):
            raise IndexError(f"Index {index} out of range for block of height {len(self._rows)}")
        
        self._rows[index] = row.copy()
        self._align_rows()
        
    def extend(self, other_block: 'TemporalBlock') -> None:
        """
        Extend the block by appending all rows from another block.
        
        Args:
            other_block: The TemporalBlock to extend from
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
        return copy.deepcopy(self)
