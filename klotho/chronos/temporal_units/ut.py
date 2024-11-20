# ------------------------------------------------------------------------
# Klotho/klotho/chronos/temporal_units/ut.py
# ------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Temporal Units
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union, Protocol, runtime_checkable, Tuple, Iterator
from itertools import cycle
from klotho.topos.graphs import Tree
from klotho.topos.graphs.trees.algorithms import print_subdivisons
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms.rt_algs import measure_ratios, auto_subdiv
from klotho.chronos.chronos import calc_onsets, beat_duration, seconds_to_hmsms

import numpy as np

# Prolationis Types
DURTYPES  = {'d', 'duration', 'dur'}
RESTYPES  = {'r', 'rest', 'silence'}
PULSTYPES = {'p', 'pulse', 'phase'}
SUBTYPES  = {'s', 'subdivision', 'subdivisions'}
ALLTYPES  = DURTYPES | RESTYPES | PULSTYPES | SUBTYPES


@runtime_checkable
class TemporalStructure(Protocol):
    """Protocol defining the interface for temporal structures in the chronos system.
    
    Any class that implements these properties and methods is considered a temporal structure,
    regardless of how they're implemented.
    """
    
    @property
    def duration(self) -> float:
        """The total duration (in seconds) of the temporal structure."""
        ...
    
    @property
    def offset(self) -> float:
        """The offset (or absolute start time) in seconds of the structure."""
        ...
    
    @property
    def time(self) -> Tuple[float, float]:
        """The absolute start and end times (in seconds) of the structure."""
        ...
    
    def tempo(self, tempo: Union[None, int, float]) -> None:
        """Sets the tempo for the temporal structure."""
        ...
    
    def beat(self, beat: Union[None, 'Fraction', str]) -> None:
        """Sets the beat ratio for the temporal structure."""
        ...
    
    def __iter__(self) -> Iterator:
        """Makes the structure iterable."""
        ...


class TemporalUnit:
    def __init__(self,
                 duration:Union[int,float]                 = 1,
                 tempus:Union[Meas,Fraction,int,float,str] = '1/1',
                 prolatio:Union[RhythmTree,tuple,str]      = 'd',
                 tempo:Union[None,int,float]               = 60,
                 beat:Union[Fraction,int,float,str]        = '1/4'):
        
        self.__type      = None
        self.__rtree     = self._set_rtree(duration, Meas(tempus), prolatio) # RhythmTree object
        self.__tempo     = tempo
        self.__beat      = self._set_beat(beat) # Fraction object
        self.__onsets    = None
        self.__durations = None
        self.__offset    = 0.0
        self.__events    = None
    
    @classmethod
    def from_tree(cls, tree:Union[Tree, RhythmTree], tempo = None, beat = None):
        return cls(duration = tree.duration if isinstance(tree, RhythmTree) else 1,
                   tempus   = tree._root,
                   prolatio = tree._children,
                   tempo    = tempo,
                   beat     = beat)

    @classmethod
    def from_subdivs(cls, subdivisions:tuple, duration:int = 1, tempo = None, beat = None):
        return cls(tempus   = Meas(sum(abs(r) * duration for r in measure_ratios(subdivisions))),
                   prolatio = subdivisions,
                   tempo    = tempo,
                   beat     = beat)

    @property
    def span(self):
        """The number of measures that the TemporalUnit spans."""
        return self.__rtree.duration

    @property
    def tempus(self):
        """The time signature of the TemporalUnit."""
        return self.__rtree._root
    
    @property
    def prolationis(self):        
        """The S-part of a RhythmTree which describes the subdivisions of the TemporalUnit."""
        return self.__rtree._children
    
    @property
    def ratios(self):
        """The ratios of a RhythmTree which describe the proportional durations of the TemporalUnit."""
        return self.__rtree.ratios
    
    @property
    def rtree(self):
        """The RhythmTree of the TemporalUnit."""
        return self.__rtree
    
    @property
    def tree(self):
        """The Tree of the RhythmTree."""
        return self.__rtree.tree

    @property
    def tempo(self):
        """The tempo in beats per minute of the TemporalUnit."""
        return self.__tempo

    @property
    def beat(self):
        """The rhythmic ratio that describes the beat of the TemporalUnit."""
        return self.__beat
    
    @property
    def type(self):
        """The type of the TemporalUnit."""
        return self.__type
    
    @property
    def offset(self):
        """The offset (or absolute start time) in seconds of the TemporalUnit."""
        return self.__offset
    
    @property
    def onsets(self):
        """A tuple of onset times (in seconds) for each event in the TemporalUnit."""
        if self.__onsets is None:
            self.__onsets = tuple(onset + self.__offset for onset in calc_onsets(self.durations))
        return self.__onsets

    @property
    def durations(self):
        """A tuple of durations (in seconds) for each event in the TemporalUnit."""
        if self.__durations is None:
            self.__durations = tuple(
                beat_duration(ratio      = r,
                              bpm        = self.__tempo,
                              beat_ratio = self.__beat) for r in self.__rtree.ratios
                )
        return self.__durations

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        # return sum(abs(d) for d in self.durations)
        return beat_duration(ratio      = str(self.__rtree._root * self.__rtree.duration),
                             bpm        = self.__tempo,
                             beat_ratio = self.__beat)
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the TemporalUnit."""
        return self.__offset, self.__offset + self.duration
    
    @property
    def events(self):
        """A list of events (dicts) for each event in the TemporalUnit."""
        if self.__events is None:
            self.__events = self._set_events()
        return self.__events
    
    @tempo.setter
    def tempo(self, tempo:Union[None,float,int]):
        """Sets the tempo in beats per minute of the TemporalUnit."""
        self.__tempo     = tempo
        self.__onsets    = None
        self.__durations = None
        
    @beat.setter
    def beat(self, beat:Union[Fraction,str]):
        """Sets the rhythmic ratio that describes the beat of the TemporalUnit."""
        self.__beat      = Fraction(beat)
        self.__onsets    = None
        self.__durations = None
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the TemporalUnit."""
        self.__offset = offset
        self.__onsets = None
        
    # TODO: make free method in UT algos
    def decompose(self, prolatio:Union[RhythmTree,tuple,str] = 'd') -> 'TemporalUnitSequence':
        if isinstance(prolatio, tuple):
            prolatio = [prolatio]
        elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
            prolatio = [self.__rtree.subdivisions]
        prolatio = cycle(prolatio)
        return TemporalUnitSequence([
            TemporalUnit(tempus   = ratio,
                         prolatio = next(prolatio),
                         tempo    = self.__tempo,
                         beat     = self.__beat) for ratio in self.__rtree.ratios])

    def _set_rtree(self, duration:int, tempus:Union[Meas,Fraction,str], prolatio:Union[tuple,str]) -> RhythmTree:
        if isinstance(prolatio, RhythmTree):
            r_tree = prolatio
            self.__type = 'Subdivision'
        elif isinstance(prolatio, tuple):
            r_tree = RhythmTree(duration = duration, meas = tempus, subdivisions = prolatio)
            # self.__type = f'Ensemble ({r_tree.type})'
            self.__type = 'Subdivision'
        elif isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in PULSTYPES:
                self.__type = 'Pulse'
                r_tree = RhythmTree(duration = duration, meas = tempus, subdivisions = (1,) * tempus.numerator)
            elif prolatio in DURTYPES:
                self.__type = 'Duration'
                r_tree = RhythmTree(duration = duration, meas = tempus, subdivisions = (1,))
            elif prolatio in RESTYPES:
                self.__type = 'Rest'
                r_tree = RhythmTree(duration = duration, meas = tempus, subdivisions = (-1,))
            else:
                raise ValueError(f'Invalid string: {prolatio}')
            
        return r_tree
    
    def _set_beat(self, beat:Union[None,str,Fraction]) -> Fraction:
        if beat is None:
            return Fraction(1, self.__rtree.meas.denominator)
        return Fraction(beat)

    def _set_events(self):
        return [
            {
                'start'    : onset,
                'duration' : duration,
                'end'      : onset + duration,
                'ratio'    : ratio,
            }
            for onset, duration, ratio in zip(self.onsets, self.durations, self.__rtree.ratios)
        ]

    def __mul__(self, other:Union[int,float,Fraction]):
        return TemporalUnit(duration = self.duration * other,
                             tempus   = self.__rtree._root,
                             prolatio = self.__rtree._children,
                             tempo    = self.__tempo,
                             beat     = self.__beat)

    def __iter__(self):
        return iter(self.events)
    
    def __len__(self):
        return len(self.__rtree.ratios)

    def __str__(self):
        prolat = print_subdivisons(self.__rtree.subdivisions) if self.__type.lower() in SUBTYPES else self.__type
        return (
            f'Tempus:   {self.__rtree._root}\n'
            f'Span:     {self.__rtree.duration}\n'
            f'Events:   {len(self)}\n'
            f'Prolatio: {prolat}\n'
            f'Tempo:    {self.__beat} = {self.__tempo}\n'
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n'
            f'-----------------------------------\n'
        )

    def __repr__(self):
        return self.__str__()


class TemporalUnitSequence:
    """A sequence of TemporalUnit objects that represent consecutive temporal events."""
    
    def __init__(self, ut_seq:list[TemporalUnit]=[]):
        self.__seq    = ut_seq
        self.__offset = 0.0
        self._set_offsets()

    @property
    def uts(self):
        """The list of TemporalUnit objects in the sequence."""
        return self.__seq

    @property
    def onsets(self):
        """A tuple of onset times (in seconds) for each TemporalUnit in the sequence."""
        return calc_onsets(self.durations)
    
    @property    
    def durations(self):
        """A tuple of durations (in seconds) for each TemporalUnit in the sequence."""
        return tuple(ut.duration for ut in self.__seq)
    
    @property
    def duration(self):
        """The total duration (in seconds) of the sequence."""
        return sum(abs(d) for d in self.durations)

    @property
    def T(self):
        """Returns a TemporalSequenceBlock containing single-unit sequences of this sequence's units."""
        return TemporalSequenceBlock([TemporalUnitSequence([ut]) for ut in self.__seq])
    
    @property
    def offset(self):
        """The offset (or absolute start time) in seconds of the sequence."""
        return self.__offset
    
    @property
    def size(self):
        """The total number of events across all TemporalUnits in the sequence."""
        return sum(len(ut) for ut in self.__seq)
    
    @property
    def time(self):
        """The absolute start and end times (in seconds) of the sequence."""
        return self.offset, self.offset + self.duration
    
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the sequence."""
        self.__offset = offset
        self._set_offsets()
    
    def tempo(self, tempo:Union[None,int,float]):
        """Sets the tempo for all TemporalUnits in the sequence."""
        for ut in self.__seq:
            ut.tempo = tempo
    
    def beat(self, beat:Union[None,Fraction,str]):
        """Sets the beat ratio for all TemporalUnits in the sequence."""
        for ut in self.__seq:
            ut.beat = beat
    
    def _set_offsets(self):
        """Updates the offsets of all TemporalUnits based on their position in the sequence."""
        for i, ut in enumerate(self.__seq):
            ut.offset = self.__offset + sum(self.durations[j] for j in range(i))

    def __iter__(self):
        return iter(self.__seq)
    
    def __len__(self):
        return len(self.__seq)


class TemporalSequenceBlock:
    """A collection of parallel TemporalUnitSequences that represent simultaneous temporal events."""
    
    def __init__(self, tb:list[TemporalUnitSequence]=[]):
        self.__tb = tb
        self.__axis = -1.0
        self.__offset = 0.0
        self.__duration = max(ut_seq.duration for ut_seq in self.__tb) if self.__tb else 0.0

    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, tempo=None, beat=None):
        """Creates a TemporalSequenceBlock from a matrix of tree specifications.
        
        Args:
            matrix: Input matrix containing duration and subdivision specifications
            meas_denom: Denominator for measure fractions
            subdiv: Whether to automatically generate subdivisions
            rotation_offset: Offset for rotation calculations
            tempo: Tempo in beats per minute
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
                seq.append(TemporalUnit(tempus   = Meas(D, meas_denom),
                                        prolatio = S,
                                        tempo    = tempo,
                                        beat     = beat))
            tb.append(TemporalUnitSequence(seq))
        return cls(tuple(tb))

    @property
    def size(self):
        """The number of TemporalUnitSequences in the block."""
        return len(self.__tb)
    
    @property
    def utseqs(self):
        """The list of TemporalUnitSequences in the block."""
        return self.__tb

    @property
    def duration(self):
        """The total duration (in seconds) of the longest sequence in the block."""
        return self.__duration

    @property
    def axis(self):
        """The temporal axis position of the block."""
        return self.__axis
    
    @property
    def offset(self):
        """The offset (or absolute start time) in seconds of the block."""
        return self.__offset
    
    @axis.setter
    def axis(self, axis):
        """Sets the temporal axis position of the block."""
        self.__axis = axis
        pass
    
    # @offset.setter
    # def offset(self, offset):
    #     self.__offset = offset
    #     for i, utseq in enumerate(self.__tb):
    #         utseq.offset = offset + sum(self.durations[j] for j in range(i))

    def tempo(self, tempo):
        """Sets the tempo for all TemporalUnitSequences in the block."""
        for utseq in self.__tb:
            utseq.tempo(tempo)
            
    def beat(self, beat):
        """Sets the beat ratio for all TemporalUnitSequences in the block."""
        for utseq in self.__tb:
            utseq.beat(beat)

    def __iter__(self):
        return iter(self.__tb)


class TemporalComposition:
    pass
    