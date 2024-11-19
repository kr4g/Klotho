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
from itertools import cycle
from klotho.topos.graphs import Tree
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
        """The tempo of the TemporalUnit."""
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
    
    @tempo.setter
    def tempo(self, tempo:Union[None,float,int]):
        self.__tempo     = tempo
        self.__onsets    = None
        self.__durations = None
    
    @beat.setter
    def beat(self, beat:Union[Fraction,str]):
        self.__beat      = Fraction(beat)
        self.__onsets    = None
        self.__durations = None
    
    @offset.setter
    def offset(self, offset:float):
        self.__offset = offset
        self.__onsets = None
        
    # TODO: make free method in UT algos
    def decompose(self, prolatio:Union[RhythmTree,tuple,str] = 'd') -> 'TemporalUnitSequence':
        if isinstance(prolatio, tuple):
            prolatio = [prolatio]
        elif isinstance(prolatio, str) and prolatio.lower() in {'s'}:
            prolatio = [self.__rtree.subdivisions]
        # print(prolatio)
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
    
    def __add__(self, other:Union['TemporalUnit', 'TemporalUnitSequence', Fraction]):
        if isinstance(other, TemporalUnit):
            new_tempus = self.__rtree._root + other.__rtree._root
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, TemporalUnitSequence):
            return TemporalUnitSequence((self,) + other.uts)
        elif isinstance(other, Fraction):
            new_tempus = self.__rtree._root + other
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')

    def __sub__(self, other:Union['TemporalUnit', Fraction]):
        if isinstance(other, TemporalUnit):
            new_tempus = abs(self.__rtree._root - other.__rtree._root)
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, Fraction):
            new_tempus = abs(self.__rtree._root - other)
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')

    def __mul__(self, other:Union['TemporalUnit', Fraction, int]):
        if not isinstance(other, (TemporalUnit, Fraction, int)):
            raise ValueError('Invalid Operand')
        elif isinstance(other, TemporalUnit):
            new_tempus = self.__rtree._root * other.__rtree._root            
        else:
            new_tempus = self.__rtree._root * other
        return TemporalUnit(tempus   = new_tempus,
                  prolatio = self.__rtree.subdivisions,
                  tempo    = self.__tempo,
                  beat     = self.__beat)
    
    def __truediv__(self, other:Union['TemporalUnit', Fraction, int]):
        if isinstance(other, TemporalUnit):
            new_tempus = self.__rtree._root / other.__rtree._root
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = self.__rtree.subdivisions,
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, (Fraction, int)):
            new_tempus = self.__rtree._root / other
            return TemporalUnit(tempus   = new_tempus,
                      prolatio = self.__rtree.subdivisions,
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')
    
    def __and__(self, other:'TemporalUnit'):
        if isinstance(other, TemporalUnit):
            return TemporalUnitSequence((self, other))
        raise ValueError('Invalid Operand')
    
    def __iter__(self):
        return iter(
            [
                {
                    'start'    : onset,
                    'duration' : duration,
                    'end'      : onset + duration,
                    'ratio'    : ratio,
                }
                for onset, duration, ratio in zip(self.onsets, self.durations, self.__rtree.ratios)
            ]
        )
    
    def __len__(self):
        return len(self.__rtree.ratios)
    
    def _format_prolatio(self, prolatio):
        """Format nested tuple structure removing commas."""
        if isinstance(prolatio, (tuple, list)):
            inner = ' '.join(str(self._format_prolatio(x)) for x in prolatio)
            return f"({inner})"
        return str(prolatio)

    def __str__(self):
        prolat = self._format_prolatio(self.__rtree.subdivisions) if self.__type.lower() in SUBTYPES else self.__type
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
    def __init__(self, ut_seq:list[TemporalUnit]=[]):
        self.__seq    = ut_seq
        self.__offset = 0.0
        self._set_offsets()

    @property
    def uts(self):
        return self.__seq

    @property
    def onsets(self):
        return calc_onsets(self.durations)
    
    @property    
    def durations(self):
        return tuple(ut.duration for ut in self.__seq)
    
    @property
    def duration(self):
        return sum(abs(d) for d in self.durations)

    @property
    def T(self):
        return TemporalSequenceBlock([TemporalUnitSequence([ut]) for ut in self.__seq])
    
    @property
    def offset(self):
        return self.__offset
    
    @property
    def size(self):
        return sum(len(ut) for ut in self.__seq)
    
    @property
    def time(self):
        return self.offset, self.offset + self.duration
    
    @offset.setter
    def offset(self, offset:float):
        self.__offset = offset
        self._set_offsets()
    
    def tempo(self, tempo:Union[None,int,float]):
        for ut in self.__seq:
            ut.tempo = tempo
    
    def beat(self, beat:Union[None,Fraction,str]):
        for ut in self.__seq:
            ut.beat = beat
    
    # def append(self, ut:TemporalUnit):
    #     self.__seq.append(ut)
    #     self._set_offsets()
    
    # def extend(self, uts:list[TemporalUnit]):
    #     self.__seq.extend(uts)
    #     self._set_offsets()
    
    def _set_offsets(self):
        for i, ut in enumerate(self.__seq):
            ut.offset = self.__offset + sum(self.durations[j] for j in range(i))

    # TODO: implement cases for int, float, Fraction (affects the Tempus of each UT)
    def __add__(self, other:Union[TemporalUnit,'TemporalUnitSequence']):
        if isinstance(other, TemporalUnit):
            self.append(other)
        elif isinstance(other, TemporalUnitSequence):
            self.extend(other.__seq)
        raise ValueError('Invalid Operand')

    def __and__(self, other:Union[TemporalUnit, 'TemporalUnitSequence']):
        if isinstance(other, TemporalUnit):
            return TemporalSequenceBlock((self.__seq, (other,)))
        elif isinstance(other, TemporalUnitSequence):
            return TemporalSequenceBlock((self.__seq, other.__seq))
        raise ValueError('Invalid Operand')

    def __iter__(self):
        return iter(self.__seq)
    
    def __len__(self):
        return len(self.__seq)

# Time Block
class TemporalSequenceBlock:
    def __init__(self, tb:list[TemporalUnitSequence]=[]):
        self.__tb = tb# if isinstance(tb, list[TemporalUnitSequence]) else list(tb)
        self.__axis = -1.0
        self.__offset = 0.0
        self.__duration = max(ut_seq.duration for ut_seq in self.__tb) if self.__tb else 0.0

    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, tempo=None, beat=None):
        tb = []
        for i, row in enumerate(matrix):
            seq = []
            for j, e in enumerate(row):
                offset = rotation_offset * i
                if subdiv:
                    D, S = e[0], auto_subdiv(e[1][::-1], offset - j - i)
                else:
                    D, S = e[0], e[1]
                seq.append(TemporalUnit(tempus   = Meas((D, meas_denom)),
                                        prolatio = S,
                                        tempo    = tempo,
                                        beat     = beat))
            tb.append(TemporalUnitSequence(seq))
        return cls(tuple(tb))

    @property
    def size(self):
        return len(self.__tb)
    
    @property
    def utseqs(self):
        return self.__tb

    @property
    def duration(self):
        return self.__duration

    @property
    def axis(self):
        return self.__axis
    
    @property
    def offset(self):
        return self.__offset
    
    # XXX - TO DO:
    @axis.setter
    def axis(self, axis):
        self.__axis = axis
        pass
    
    # @offset.setter
    # def offset(self, offset):
    #     self.__offset = offset
    #     for i, utseq in enumerate(self.__tb):
    #         utseq.offset = offset + sum(self.durations[j] for j in range(i))

    def tempo(self, tempo):
        for utseq in self.__tb:
            utseq.tempo(tempo)
            
    def beat(self, beat):
        for utseq in self.__tb:
            utseq.beat(beat)

    def __iter__(self):
        return iter(self.__tb)
