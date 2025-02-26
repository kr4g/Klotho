# ------------------------------------------------------------------------
# Klotho/klotho/chronos/temporal_units/ut.py
# ------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Temporal Units
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union, Tuple
from klotho.topos.graphs.trees.algorithms import print_subdivisons
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.chronos.chronos import calc_onsets, beat_duration, seconds_to_hmsms

from enum import Enum
import networkx as nx
import pandas as pd
from sympy import pretty

# Prolationis Types
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
    def start(self): return self._rt[self._node_id]['onset']
    @property
    def duration(self): return self._rt[self._node_id]['duration']
    @property
    def end(self): return self.start + abs(self.duration)
    @property
    def proportion(self): return self._rt[self._node_id]['proportion']
    @property
    def metric_ratio(self): return self._rt[self._node_id]['ratio']
    @property
    def node_id(self): return self._node_id
    @property
    def is_rest(self): return self._rt[self._node_id]['duration'] < 0
    
    def __str__(self):
        return pd.DataFrame({
            'start': [self.start],
            'duration': [self.duration], 
            'end': [self.end],
            'proportion': [self.proportion],
            'ratio': [self.metric_ratio],
            'node_id': [self.node_id],
            'is_rest': [self.is_rest]
        }, index=['']).__str__()
    
    def __repr__(self):
        return self.__str__()


class TemporalUnit(metaclass=TemporalMeta):
    def __init__(self,
                 span:Union[int,float,Fraction]            = 1,
                 tempus:Union[Meas,Fraction,int,float,str] = '4/4',
                 prolatio:Union[tuple,str]                 = 'd',
                 beat:Union[None,Fraction,int,float,str]   = None,
                 bpm:Union[None,int,float]                 = None):
        
        self._type   = None
        self._rt     = self._set_rt(span, Meas(tempus), prolatio)
        self._beat   = Fraction(beat) if beat else Fraction(1, self._rt.meas._denominator)
        self._bpm    = bpm if bpm else 60
        self._offset = 0.0
        
        self._events = self._set_nodes()
    
    @classmethod
    def from_rt(cls, rt:RhythmTree, beat = None, bpm = None):
        return cls(span     = rt.span,
                   tempus   = rt.meas,
                   prolatio = rt._subdivisions,
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
        return self._rt._subdivisions
    
    @property
    def rt(self):
        """The RhythmTree of the TemporalUnit."""
        return self._rt

    @property
    def ratios(self):
        """The ratios of a RhythmTree which describe the proportional durations of the TemporalUnit."""
        return self._rt._ratios

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
        return tuple(self._rt.graph.nodes[n]['onset'] for n in self._rt.leaf_nodes)

    @property
    def durations(self):
        return tuple(self._rt.graph.nodes[n]['duration'] for n in self._rt.leaf_nodes)

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        # return sum(abs(d) for d in self.durations)
        return beat_duration(ratio      = str(self._rt.meas * self._rt.span),
                             bpm        = self.bpm,
                             beat_ratio = self.beat
                )
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the TemporalUnit."""
        return self._offset, self._offset + self.duration
    
    @property
    def events(self):
        return pd.DataFrame([{
            'start': c.start,
            'duration': c.duration,
            'end': c.end,
            'metric_ratio': c.metric_ratio,
            's': c.proportion,
            'is_rest': c.is_rest,
            'node_id': c.node_id,
        } for c in self._events], index=range(len(self._events)))
    
    @bpm.setter
    def bpm(self, bpm:Union[None,float,int]):
        """Sets the bpm in beats per minute of the TemporalUnit."""
        self._bpm = bpm
        self._events = self._set_nodes()
        
    @beat.setter
    def beat(self, beat:Union[Fraction,str]):
        """Sets the rhythmic ratio that describes the beat of the TemporalUnit."""
        self._beat = Fraction(beat)
        self._events = self._set_nodes()
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the TemporalUnit."""
        self._offset = offset
        self._events = self._set_nodes()
        
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

    def _set_nodes(self):
        """Updates node timings and returns chronon events."""
        leaf_nodes = self._rt.leaf_nodes
        leaf_durations = [beat_duration(ratio=self._rt[n]['ratio'], 
                                      bpm=self.bpm, 
                                      beat_ratio=self.beat) for n in leaf_nodes]
        leaf_onsets = [onset + self._offset for onset in calc_onsets(leaf_durations)]
        
        for node, onset, duration in zip(leaf_nodes, leaf_onsets, leaf_durations):
            self._rt[node]['onset'] = onset
            self._rt[node]['duration'] = duration
        
        non_leaf_nodes = [n for n,d in self._rt.graph.out_degree() if d > 0]
        for node in non_leaf_nodes:
            self._rt[node]['duration'] = beat_duration(
                ratio=str(self._rt[node]['ratio']),
                bpm=self.bpm,
                beat_ratio=self.beat)
            
            current = node
            while self._rt.graph.out_degree(current) > 0:
                current = min(self._rt.graph.successors(current))
            self._rt[node]['onset'] = self._rt[current]['onset']

        return tuple(Chronon(node_id, self._rt) for node_id in leaf_nodes)

    def __getitem__(self, idx: int) -> Chronon:
        return self._events[idx]
    
    def __iter__(self):
        return iter(self._events)
    
    def __len__(self):
        return len(self._events)
        
    def __str__(self):
        result = (
            f'Span:     {self._rt.span}\n'
            f'Tempus:   {self._rt.meas}\n'
            # f'Prolatio: {print_subdivisons(self._rt.subdivisions)}\n'
            f'Prolatio: {self._type.value}\n'
            f'Events:   {len(self)}\n'
            f'Tempo:    {self._beat} = {self._bpm}\n'
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n'
            f'{"-" * 50}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()


class TemporalUnitSequence(metaclass=TemporalMeta):
    """A sequence of TemporalUnit objects that represent consecutive temporal events."""
    
    def __init__(self, ut_seq:list[TemporalUnit]=[]):
        self._seq    = ut_seq
        self._offset = 0.0
        self._set_offsets()

    @property
    def uts(self):
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
    
    @property
    def T(self):
        """Transforms the TemporalUnitSequence into a TemporalBlock."""
        return TemporalBlock([TemporalUnitSequence([ut]) for ut in self._seq])
    
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the sequence."""
        self._offset = offset
        self._set_offsets()
    
    def beat(self, beat:Union[None,Fraction,str]):
        """Sets the beat ratio for all TemporalUnits in the sequence."""
        for ut in self._seq:
            ut.beat = beat
        self._set_offsets()
    
    def bpm(self, bpm:Union[None,int,float]):
        """Sets the bpm for all TemporalUnits in the sequence."""
        for ut in self._seq:
            ut.bpm = bpm
        self._set_offsets()
    
    def _set_offsets(self):
        """Updates the offsets of all TemporalUnits based on their position in the sequence."""
        for i, ut in enumerate(self._seq):
            ut.offset = self._offset + sum(self.durations[j] for j in range(i))

    def __iter__(self):
        return iter(self._seq)
    
    def __len__(self):
        return len(self._seq)

    def __str__(self):
        return pd.DataFrame([{
            'Tempus': ut.tempus,
            'Beat': ut.beat,
            'BPM': ut.bpm,
            'Start': seconds_to_hmsms(ut.time[0]),
            'Duration': seconds_to_hmsms(ut.duration),
            'End': seconds_to_hmsms(ut.time[1]),
        } for ut in self._seq]).__str__()

    def __repr__(self):
        return self.__str__()


class TemporalBlock(metaclass=TemporalMeta):
    """A collection of parallel TemporalUnitSequences that represent simultaneous temporal events."""
    
    def __init__(self, tb:list[TemporalUnitSequence]=[]):
        self._tb = tb
        self._axis = -1.0
        self._offset = 0.0
        self._duration = max(ut_seq.duration for ut_seq in self._tb) if self._tb else 0.0
        self._align_sequences()
        
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

    def _align_sequences(self):
        """Aligns the sequences based on the current axis value."""
        if not self._tb:
            return
            
        max_duration = self._duration
        base_offset = self._offset
        
        for seq in self._tb:
            if seq.duration == max_duration:
                seq.offset = base_offset
                continue
                
            duration_diff = max_duration - seq.duration    
            adjustment = duration_diff * (self._axis + 1) / 2
            seq.offset = base_offset + adjustment

    @property
    def size(self):
        """The number of TemporalUnitSequences in the block."""
        return len(self._tb)
    
    @property
    def utseqs(self):
        """The list of TemporalUnitSequences in the block."""
        return self._tb

    @property
    def duration(self):
        """The total duration (in seconds) of the longest sequence in the block."""
        return self._duration

    @property
    def axis(self):
        """The temporal axis position of the block."""
        return self._axis
    
    @property
    def offset(self):
        """The offset (or absolute start time) in seconds of the block."""
        return self._offset
    
    @offset.setter
    def offset(self, offset):
        """Sets the offset (or absolute start time) in seconds of the block."""
        self._offset = offset
        self._align_sequences()
    
    @axis.setter
    def axis(self, axis: float):
        """
        Sets the temporal axis position of the block and realigns sequences.
        
        Args:
            axis: Float between -1 and 1, where:
                -1: sequences start at block offset (left-aligned)
                 0: sequences are centered within the block
                 1: sequences end at block offset + duration (right-aligned)
                Any value in between creates a proportional alignment
        """
        if not -1 <= axis <= 1:
            raise ValueError("Axis must be between -1 and 1")
        self._axis = float(axis)
        self._align_sequences()
            
    def beat(self, beat):
        """Sets the beat ratio for all TemporalUnitSequences in the block."""
        for utseq in self._tb:
            utseq.beat(beat)
        
    def bpm(self, bpm):
        """Sets the bpm for all TemporalUnitSequences in the block."""
        for utseq in self._tb:
            utseq.bpm(bpm)

    def __iter__(self):
        return iter(self._tb)
