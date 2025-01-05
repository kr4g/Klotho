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
    """An indivisible unit of musical time within a TemporalUnit."""
    
    __slots__ = ('_data',)
    _PROTECTED_KEYS = {'start', 'duration', 'end', 'metric_ratio', 'beat', 'bpm'}
    
    def __init__(self, start:float=0.0, duration:float=0.0, end:float=0.0,
                 metric_ratio:Union[None,Fraction]=None, beat:Union[None,Fraction]=None,
                 bpm:Union[None,int,float]=None):
        
        self._data = {
            'start'        : start,
            'duration'     : duration,
            'end'          : end,
            'metric_ratio' : metric_ratio,
            'beat'         : beat,
            'bpm'          : bpm
        }
    
    @property
    def start(self):
        return self._data['start']
    
    @property
    def duration(self):
        return self._data['duration']
    
    @property
    def end(self):
        return self._data['end']
    
    @property
    def metric_ratio(self):
        return self._data['metric_ratio']
    
    @property
    def beat(self):
        return self._data['beat']
    
    @property
    def bpm(self):
        return self._data['bpm']
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    

class TemporalUnit(metaclass=TemporalMeta):
    def __init__(self,
                 span:Union[int,float,Fraction]            = 1,
                 tempus:Union[Meas,Fraction,int,float,str] = '1/1',
                 prolatio:Union[tuple,str]                 = 'd',
                 beat:Union[None,Fraction,int,float,str]   = None,
                 bpm:Union[None,int,float]                 = None):
        
        self._type      = None
        self._rtree     = self._set_rtree(span, Meas(tempus), prolatio)
        self._beat      = beat
        self._bpm       = bpm
        self._onsets    = None
        self._durations = None
        self._offset    = 0.0
        self._elements  = [Chronon() for _ in range(len(self._rtree._ratios))]
        
        self._set_elements()
    
    @classmethod
    def from_tree(cls, tree:RhythmTree, beat = None, bpm = None):
        return cls(span     = tree._span,
                   tempus   = tree._root,
                   prolatio = tree._children,
                   beat     = beat,
                   bpm      = bpm)

    # @property
    # def size(self):
    #     """The number of events in the TemporalUnit."""
    #     return len(self._rtree.ratios)
    
    @property
    def span(self):
        """The number of measures that the TemporalUnit spans."""
        return self._rtree._span

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
        return self._rtree._ratios

    @property
    def beat(self):
        """The rhythmic ratio that describes the beat of the TemporalUnit."""
        if self._beat is None:
            self._beat = Fraction(1, self._rtree._root._denominator)
        return self._beat
    
    @property
    def bpm(self):
        """The beats per minute of the TemporalUnit."""
        if self._bpm is None:
            self._bpm = 60
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
        """A tuple of onset times (in seconds) for each event in the TemporalUnit."""
        if self._onsets is None:
            self._onsets = tuple(onset + self._offset for onset in calc_onsets(self.durations))
        return self._onsets

    @property
    def duration(self):
        """The total duration (in seconds) of the TemporalUnit."""
        # return sum(abs(d) for d in self.durations)
        return beat_duration(ratio      = str(self._rtree._root * self._rtree._span),
                             bpm        = self.bpm,
                             beat_ratio = self.beat
                )
    
    @property
    def durations(self):
        """A tuple of durations (in seconds) for each event in the TemporalUnit."""
        if self._durations is None:
            self._durations = tuple(
                beat_duration(ratio      = r,
                              bpm        = self.bpm,
                              beat_ratio = self.beat) for r in self._rtree._ratios
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
    
    # @tempus.setter
    # def tempus(self, tempus:Union[Meas,Fraction,int,float,str]):
    #     """Sets the time signature of the TemporalUnit."""
    #     self._rtree = self._set_rtree(self._span, tempus, self._rtree._children)
    #     self._set_elements()
    
    @bpm.setter
    def bpm(self, bpm:Union[None,float,int]):
        """Sets the bpm in beats per minute of the TemporalUnit."""
        self._bpm       = bpm
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

    def _set_rtree(self, span:int, tempus:Union[Meas,Fraction,str], prolatio:Union[tuple,str]) -> RhythmTree:
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

    def _set_elements(self):
        for i, (onset, duration, ratio) in enumerate(zip(self.onsets, self.durations, self._rtree._ratios)):
            match self._elements[i]:
                case Chronon():
                    self._elements[i]['start']        = onset
                    self._elements[i]['duration']     = duration
                    self._elements[i]['end']          = onset + duration
                    self._elements[i]['metric_ratio'] = ratio
                    self._elements[i]['beat']         = self._beat
                    self._elements[i]['bpm']          = self._bpm
                # case TemporalStructure():
                #     self._elements[i].offset = onset
                #     self._elements[i].beat   = self._beat
                #     self._elements[i].bpm    = self._bpm
                    
    def __getitem__(self, idx: int) -> dict:
        """
        Allows indexing into the TemporalUnit to access specific events.
        
        Args:
            idx: The index of the event to retrieve
            
        Returns:
            dict: A copy of the event at the specified index
            
        Raises:
            IndexError: If the index is out of range
        """
        return self._elements[idx]
    
    def __setitem__(self, idx: int, value: Union[dict, TemporalMeta]):
        """
        Allows setting values in the TemporalUnit's events while protecting certain keys.
        
        Args:
            idx: The index of the event to modify
            value: The key-value pair to set or a temporal structure
        """
        match value:
            case dict():
                for key, val in value.items():
                    if key in Chronon._PROTECTED_KEYS:
                        raise KeyError(f"Cannot modify protected key: {key}")
                    self._elements[idx][key] = val
            case _ if isinstance(value.__class__, TemporalMeta):
                if value.beat is None:
                    value.beat = self._beat
                if value.bpm is None:
                    value.bpm = self._bpm
                value.bpm = value.bpm * (value.duration / self._elements[idx]['duration'])
                self._elements[idx] = value
            case _:
                raise TypeError(f"Value must be a dictionary or temporal structure")
    
    def __iter__(self):
        return iter(self._elements)
    
    def __len__(self):
        return len(self._elements)
        
    def __str__(self):
        result = (
            f'Span:     {self._rtree.span}\n'
            f'Tempus:   {self._rtree._root}\n'
            f'Prolatio: {print_subdivisons(self._rtree._children)}\n'
            f'Events:   {len(self)}\n'
            f'Tempo:    {self._beat} = {self._bpm}\n'
            f'Time:     {seconds_to_hmsms(self.time[0])} - {seconds_to_hmsms(self.time[1])} ({seconds_to_hmsms(self.duration)})\n'
            f'{"-" * 40}\n'
        )
        return result

    def __repr__(self):
        return self.__str__()


class TemporalUnitMatrix:
    pass


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
    
    @offset.setter
    def offset(self, offset:float):
        """Sets the offset (or absolute start time) in seconds of the sequence."""
        self._offset = offset
        self._set_offsets()
    
    def bpm(self, bpm:Union[None,int,float]):
        """Sets the bpm for all TemporalUnits in the sequence."""
        for ut in self._seq:
            ut.bpm = bpm
    
    def beat(self, beat:Union[None,Fraction,str]):
        """Sets the beat ratio for all TemporalUnits in the sequence."""
        for ut in self._seq:
            ut.beat = beat
    
    def _set_offsets(self):
        """Updates the offsets of all TemporalUnits based on their position in the sequence."""
        for i, ut in enumerate(self._seq):
            ut.offset = self._offset + sum(self.durations[j] for j in range(i))

    def __iter__(self):
        return iter(self._seq)
    
    def __len__(self):
        return len(self._seq)


class TemporalUnitSequenceBlock(metaclass=TemporalMeta):
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
        Creates a TemporalUnitSequenceBlock from a matrix of tree specifications.
        
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
                seq.append(TemporalUnit(tempus   = Meas(D, meas_denom),
                                        prolatio = S,
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
        
    def bpm(self, bpm):
        """Sets the bpm for all TemporalUnitSequences in the block."""
        for utseq in self._tb:
            utseq.bpm(bpm)
            
    def beat(self, beat):
        """Sets the beat ratio for all TemporalUnitSequences in the block."""
        for utseq in self._tb:
            utseq.beat(beat)

    def __iter__(self):
        return iter(self._tb)


class TemporalComposition(metaclass=TemporalMeta):
    pass
    