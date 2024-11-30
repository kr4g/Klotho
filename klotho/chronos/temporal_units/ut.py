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
from klotho.topos.graphs.trees.algorithms import print_subdivisons
from ..rhythm_trees import Meas, RhythmTree
from ..rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.chronos.chronos import calc_onsets, beat_duration, seconds_to_hmsms

import numpy as np
from enum import Enum

# Prolationis Types
DURTYPES  = {'d', 'duration', 'dur'}
RESTYPES  = {'r', 'rest', 'silence'}
PULSTYPES = {'p', 'pulse', 'phase'}
SUBTYPES  = {'s', 'subdivision', 'subdivisions'}
ALLTYPES  = DURTYPES | RESTYPES | PULSTYPES | SUBTYPES

class ProlatioTypes(Enum):
    DURATION    = 'Duration'
    REST        = 'Rest'
    PULSE       = 'Pulse'
    SUBDIVISION = 'Subdivision'


@runtime_checkable
class TemporalStructure(Protocol):
    """Protocol defining the interface for temporal structures in the chronos system.
    
    Any class that implements these properties and methods is considered a temporal structure,
    regardless of how they're implemented.
    """
    
    @property
    def offset(self) -> float:
        """The offset (or absolute start time) in seconds of the structure."""
        ...
    
    @property
    def duration(self) -> float:
        """The total duration (in seconds) of the temporal structure."""
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
    _PROTECTED_KEYS = {'start', 'duration', 'end', 'metric_ratio', 'beat', 'bpm'}

    def __init__(self,
                 span:Union[int,float,Fraction]            = 1,
                 tempus:Union[Meas,Fraction,int,float,str] = '1/1',
                 prolatio:Union[RhythmTree,tuple,str]      = 'd',
                 tempo:Union[None,int,float]               = 60,
                 beat:Union[None,Fraction,int,float,str]   = None):
        
        self._type      = None
        self._rtree     = self._set_rtree(span, Meas(tempus), prolatio)
        self._tempo     = tempo
        self._beat      = beat
        self._onsets    = None
        self._durations = None
        self._offset    = 0.0
        self._elements  = [dict() for _ in range(len(self._rtree.ratios))]
        
        self._set_elements()
    
    @classmethod
    def from_tree(cls, tree:RhythmTree, tempo = 60, beat = None):
        return cls(span     = tree.span,
                   tempus   = tree._root,
                   prolatio = tree._children,
                   tempo    = tempo,
                   beat     = beat)

    # @property
    # def size(self):
    #     """The number of events in the TemporalUnit."""
    #     return len(self._rtree.ratios)
    
    @property
    def span(self):
        """The number of measures that the TemporalUnit spans."""
        return self._rtree.span

    @property
    def tempus(self):
        """The time signature of the TemporalUnit."""
        return self._rtree._root
    
    @property
    def prolationis(self):        
        """The S-part of a RhythmTree which describes the subdivisions of the TemporalUnit."""
        return self._rtree._children
    
    @property
    def rtree(self):
        """The RhythmTree of the TemporalUnit."""
        return self._rtree

    @property
    def ratios(self):
        """The ratios of a RhythmTree which describe the proportional durations of the TemporalUnit."""
        return self._rtree.ratios
    
    @property
    def tempo(self):
        """The tempo in beats per minute of the TemporalUnit."""
        return self._tempo

    @property
    def beat(self):
        """The rhythmic ratio that describes the beat of the TemporalUnit."""
        if self._beat is None:
            self._beat = Fraction(1, self._rtree.meas.denominator)
        return self._beat
    
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
        """A tuple of onset times (in seconds) for each event in the TemporalUnit."""
        if self._onsets is None:
            self._onsets = tuple(onset + self._offset for onset in calc_onsets(self.durations))
        return self._onsets

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        # return sum(abs(d) for d in self.durations)
        return beat_duration(ratio      = str(self._rtree._root * self._rtree.span),
                             bpm        = self._tempo,
                             beat_ratio = self.beat)
    
    @property
    def durations(self):
        """A tuple of durations (in seconds) for each event in the TemporalUnit."""
        if self._durations is None:
            self._durations = tuple(
                beat_duration(ratio      = r,
                              bpm        = self._tempo,
                              beat_ratio = self.beat) for r in self._rtree.ratios
                )
        return self._durations

    @property
    def time(self):
        """The absolute start and end times (in seconds) of the TemporalUnit."""
        return self._offset, self._offset + self.duration
    
    @property
    def events(self):
        """A list of events (dicts) for each event in the TemporalUnit."""
        return self._elements
    
    @tempo.setter
    def tempo(self, tempo:Union[None,float,int]):
        """Sets the tempo in beats per minute of the TemporalUnit."""
        self._tempo     = tempo
        self._onsets    = None
        self._durations = None
        self._set_elements()
        
    @beat.setter
    def beat(self, beat:Union[Fraction,str]):
        """Sets the rhythmic ratio that describes the beat of the TemporalUnit."""
        self._beat      = Fraction(beat)
        self._onsets    = None
        self._durations = None
        self._set_elements()
        
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the TemporalUnit."""
        self._offset = offset
        self._onsets = None
        self._set_elements()

    def _set_rtree(self, span:int, tempus:Union[Meas,Fraction,str], prolatio:Union[RhythmTree,tuple,str]) -> RhythmTree:
        match prolatio:
            case RhythmTree():
                self._type = ProlatioTypes.SUBDIVISION
                return prolatio
            
            case tuple():
                self._type = ProlatioTypes.SUBDIVISION
                return RhythmTree(span = span, meas = tempus, subdivisions = prolatio)
            
            case str():
                prolatio = prolatio.lower()
                match prolatio:
                    case p if p in PULSTYPES:
                        self._type = ProlatioTypes.PULSE
                        return RhythmTree(span = span,
                                          meas = tempus,
                                          subdivisions = (1,) * tempus.numerator)
                    
                    case d if d in DURTYPES:
                        self._type = ProlatioTypes.DURATION
                        return RhythmTree(span = span,
                                          meas = tempus,
                                          subdivisions = (1,))
                    
                    case r if r in RESTYPES:
                        self._type = ProlatioTypes.REST
                        return RhythmTree(span = span,
                                          meas = tempus,
                                          subdivisions = (-1,))
                    
                    case _:
                        raise ValueError(f'Invalid string: {prolatio}')
                    
            case _:
                raise ValueError(f'Invalid prolatio type: {type(prolatio)}')

    def _set_elements(self):
        for i, (onset, duration, ratio) in enumerate(zip(self.onsets, self.durations, self._rtree.ratios)):
            match self._elements[i]:
                case dict():
                    self._elements[i]['start']        = onset
                    self._elements[i]['duration']     = duration
                    self._elements[i]['end']          = onset + duration
                    self._elements[i]['metric_ratio'] = ratio
                    self._elements[i]['beat']         = self._beat
                    self._elements[i]['bpm']          = self._tempo
                case TemporalStructure():
                    self._elements[i].offset = onset
                    self._elements[i].beat   = self._beat
                    self._elements[i].tempo  = self._tempo
                    
    def __getitem__(self, idx: int) -> dict:
        """Allows indexing into the TemporalUnit to access specific events.
        
        Args:
            idx: The index of the event to retrieve
            
        Returns:
            dict: A copy of the event at the specified index
            
        Raises:
            IndexError: If the index is out of range
        """
        return self._elements[idx]
    
    def __setitem__(self, idx: int, value: dict):
        """Allows setting values in the TemporalUnit's events while protecting certain keys.
        
        Args:
            idx: The index of the event to modify
            value: The key-value pair to set
            
        Raises:
            IndexError: If the index is out of range
            KeyError: If attempting to modify a protected key
        """
        if not isinstance(value, dict):
            raise TypeError("Value must be a dictionary with a single key-value pair")
        
        for key, val in value.items():
            if key in self._PROTECTED_KEYS:
                raise KeyError(f"Cannot modify protected key: {key}")
            self._elements[idx][key] = val
    
    def __iter__(self):
        return iter(self.events)
    
    def __len__(self):
        return len(self._rtree.ratios)
    
    def __mul__(self, other:Union[int,float,Fraction]):
        return TemporalUnit(span     = self.span * other,
                            tempus   = self._rtree._root,
                            prolatio = self._rtree._children,
                            tempo    = self._tempo,
                            beat     = self._beat)
        
    def __str__(self):
        prolat = print_subdivisons(self._rtree.subdivisions) if self._type == ProlatioTypes.SUBDIVISION else self._type.value
        return (
            f'Span:     {self._rtree.span}\n'
            f'Tempus:   {self._rtree._root}\n'
            f'Prolatio: {prolat}\n'
            f'Events:   {len(self)}\n'
            f'Tempo:    {self._beat} = {self._tempo}\n'
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n'
            f'-----------------------------------\n'
        )

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        """Serializes the TemporalUnit into a dictionary for visualization."""
        return {
            'events': [{
                'start': event['start'],
                'duration': event['duration'],
                'metric_ratio': str(event['metric_ratio']),
            } for event in self.events],
            'tempo': self.tempo,
            'beat': str(self.beat),
            'time': self.time
        }


class TemporalUnitMatrix:
    pass


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


class TemporalUnitSequenceBlock:
    """A collection of parallel TemporalUnitSequences that represent simultaneous temporal events."""
    
    def __init__(self, tb:list[TemporalUnitSequence]=[]):
        self.__tb = tb
        self.__axis = -1.0
        self.__offset = 0.0
        self.__duration = max(ut_seq.duration for ut_seq in self.__tb) if self.__tb else 0.0
        self._align_sequences()
        
    # TODO: make free method in UT algos
    # Matrix to Block
    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, tempo=None, beat=None):
        """Creates a TemporalUnitSequenceBlock from a matrix of tree specifications.
        
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

    def _align_sequences(self):
        """Aligns the sequences based on the current axis value."""
        if not self.__tb:
            return
            
        max_duration = self.__duration
        base_offset = self.__offset
        
        for seq in self.__tb:
            if seq.duration == max_duration:
                seq.offset = base_offset
                continue
                
            duration_diff = max_duration - seq.duration    
            adjustment = duration_diff * (self.__axis + 1) / 2
            seq.offset = base_offset + adjustment

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
    
    @offset.setter
    def offset(self, offset):
        """Sets the offset (or absolute start time) in seconds of the block."""
        self.__offset = offset
        self._align_sequences()
    
    @axis.setter
    def axis(self, axis: float):
        """Sets the temporal axis position of the block and realigns sequences.
        
        Args:
            axis: Float between -1 and 1, where:
                -1: sequences start at block offset (left-aligned)
                 0: sequences are centered within the block
                 1: sequences end at block offset + duration (right-aligned)
                Any value in between creates a proportional alignment
        """
        if not -1 <= axis <= 1:
            raise ValueError("Axis must be between -1 and 1")
        self.__axis = float(axis)
        self._align_sequences()
        
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
    