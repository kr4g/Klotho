from fractions import Fraction
from typing import Union

from ..rhythm_trees import RT, Meas
from allopy.chronos.rhythm_trees.rt_algorithms import measure_ratios, subdivide_tree
from allopy.chronos.chronos import beat_duration, calc_onsets

# Prolationis Types
PULSTYPES = {'p', 'pulse', 'phase'}
DURTYPES  = {'d', 'duration', 'dur'}
RESTYPES  = {'r', 'rest', 'silence'}
ALLTYPES  = PULSTYPES | DURTYPES | RESTYPES

# Temporal Unit
class UT:    
    def __init__(self,
                 duration:int                 = 1,
                 tempus:Union[Meas,str]       = '1/1',
                 prolatio:Union[RT,tuple,str] = 'd',
                 tempo:Union[None,float]      = None,
                 beat:Union[str,Fraction]     = None):
        
        self.__type        = None
        self.__duration    = duration
        self.__tempus      = Meas(tempus)
        self.__prolationis = self._set_prolationis(prolatio) # RT object
        self.__tempo       = tempo
        self.__beat        = self._set_beat(beat)

        self.__onsets      = None
        self.__durations   = None

        self.__offset      = 0.0
    
    @classmethod
    def from_tree(cls, tree:Union[RT, tuple], tempo=None, beat=None):
        meas = sum(abs(r) for r in measure_ratios(tree)) if isinstance(tree, tuple) else tree.time_signature
        s = tree if isinstance(tree, tuple) else tree.subdivisions
        return cls(tempus   = meas,
                   prolatio = s,
                   tempo    = tempo,
                   beat     = beat)

    @property
    def tempus(self):
        return self.__tempus
    
    @property
    def prolationis(self):        
        return self.__prolationis.subdivisions
    
    @property
    def ratios(self):
        return self.__prolationis.ratios
    
    @property
    def tree(self):
        return self.__prolationis

    @property
    def tempo(self):
        return self.__tempo

    @property
    def beat(self):
        return self.__beat
    
    @property
    def type(self):
        return self.__type
    
    @property
    def offset(self):
        return self.__offset
    
    @property
    def onsets(self):
        if self.__tempo is None:
            return None
        if self.__onsets is None:
            self.__onsets = tuple(onset + self.__offset for onset in calc_onsets(self.durations))
        return self.__onsets

    @property
    def durations(self):
        if self.__tempo is None:
            raise ValueError('Tempo is not set')
        if self.__durations is None:
            self.__durations = tuple(
                beat_duration(ratio      = r,
                              bpm        = self.__tempo,
                              beat_ratio = self.__beat) for r in self.__prolationis.ratios
                )
        return self.__durations

    @property
    def duration(self):
        if self.__tempo is None:
            raise ValueError('Tempo is not set')
        return sum(abs(d) for d in self.durations)
    
    @tempo.setter
    def tempo(self, tempo:Union[None,float,int]):
        self.__tempo = tempo
        self.__onsets = None
        self.__durations = None
    
    @beat.setter
    def beat(self, beat:Union[str,Fraction]):
        self.__beat = Fraction(beat)
        self.__onsets = None
        self.__durations = None
    
    @offset.setter
    def offset(self, offset:float):
        self.__offset = offset
        self.__onsets = None
        
    def decompose(self, prolatio:Union[RT,tuple,str] = 'd') -> 'UTSeq':
        if prolatio.lower() in {'s'}: prolatio = self.__prolationis.subdivisions
        return UTSeq(UT(tempus   = ratio,
                        prolatio = prolatio,
                        tempo    = self.__tempo,
                        beat     = self.__beat) for ratio in self.__prolationis.ratios)

    def _set_prolationis(self, prolatio):
        if isinstance(prolatio, RT) and self.__tempus != prolatio.time_signature: # if there's a difference...            
            prolatio = RT(duration       = prolatio.duration,
                          time_signature = self.__tempus,  # ...the UT wins
                          subdivisions   = prolatio.subdivisions)
            self.__type = f'Ensemble ({prolatio.type})'
        elif isinstance(prolatio, tuple):
            prolatio = RT(duration       = self.__duration,
                          time_signature = self.__tempus,
                          subdivisions   = prolatio)
            self.__type = f'Ensemble ({prolatio.type})'
        elif isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in PULSTYPES:
                self.__type = 'Pulse'
                prolatio = RT(duration       = self.__duration,
                              time_signature = self.__tempus,
                              subdivisions   = (1,) * self.__tempus.numerator)
            elif prolatio in DURTYPES:
                self.__type = 'Duration'
                prolatio = RT(duration       = self.__duration,
                              time_signature = self.__tempus,
                              subdivisions   = (1,))
            elif prolatio in RESTYPES:
                self.__type = 'Silence'
                prolatio = RT(duration       = self.__duration,
                              time_signature = self.__tempus,
                              subdivisions   = (-1,))
            else:
                raise ValueError(f'Invalid string: {prolatio}')
        else:
            raise ValueError(f'Invalid prolationis: {prolatio}')
        return prolatio
    
    def _set_beat(self, beat):
        if beat is None:
            return Fraction(1, self.__tempus.denominator)
        return Fraction(beat)
    
    def __add__(self, other:Union['UT', 'UTSeq', Fraction]):
        if isinstance(other, UT):
            new_tempus = self.__tempus + other.__tempus
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, UTSeq):
            return UTSeq((self,) + other.uts)
        elif isinstance(other, Fraction):
            new_tempus = self.__tempus + other
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')

    def __sub__(self, other:Union['UT', Fraction]):
        if isinstance(other, UT):
            new_tempus = abs(self.__tempus - other.__tempus)
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, Fraction):
            new_tempus = abs(self.__tempus - other)
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')

    def __mul__(self, other:Union['UT', Fraction, int]):
        if not isinstance(other, (UT, Fraction, int)):
            raise ValueError('Invalid Operand')
        elif isinstance(other, UT):
            new_tempus = self.__tempus * other.__tempus            
        else:
            new_tempus = self.__tempus * other
        return UT(tempus   = new_tempus,
                  prolatio = self.__prolationis.subdivisions,
                  tempo    = self.__tempo,
                  beat     = self.__beat)
    
    def __truediv__(self, other:Union['UT', Fraction, int]):
        if isinstance(other, UT):
            new_tempus = self.__tempus / other.__tempus
            return UT(tempus   = new_tempus,
                      prolatio = self.__prolationis.subdivisions,
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, (Fraction, int)):
            new_tempus = self.__tempus / other
            return UT(tempus   = new_tempus,
                      prolatio = self.__prolationis.subdivisions,
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')
    
    def __and__(self, other:'UT'):
        if isinstance(other, UT):
            return UTSeq((self, other))
        raise ValueError('Invalid Operand')
    
    def __iter__(self):
        return zip(self.onsets, self.durations)

    def __repr__(self):
        return (
            f'Tempus: {self.__tempus}\n'
            f'Tempo: {self.__tempo}\n'
            f'Beat: {self.__beat}\n'
            f'Prolationis: {self.__prolationis.subdivisions}\n'
            f'Type: {self.__type}\n'
        )

# Temporal Unit Sequence
class UTSeq:
    def __init__(self, ut_seq:tuple[UT]=(), offset:float=0.0):
        self.__seq = ut_seq
        self.__offset = offset
        self.offset = offset

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
        return sum(self.durations)

    @property
    def T(self):
        return TB((UTSeq((ut,)) for ut in self.__seq))
    
    @property
    def offset(self):
        return self.__offset
    
    @offset.setter
    def offset(self, offset:float):
        self.__offset = offset
        for i, ut in enumerate(self.__seq):
            ut.offset = offset + sum(self.durations[j] for j in range(i))

    def __add__(self, other:Union[UT, 'UTSeq']):
        if isinstance(other, UT):
            return UTSeq(self.__seq + (other,))
        elif isinstance(other, UTSeq):
            return UTSeq(self.__seq + other.__seq)
        raise ValueError('Invalid Operand')

    def __and__(self, other:Union[UT, 'UTSeq']):
        if isinstance(other, UT):
            return TB((self.__seq, (other,)))
        elif isinstance(other, UTSeq):
            return TB((self.__seq, other.__seq))
        raise ValueError('Invalid Operand')

    def __iter__(self):
        # out = []
        # for i, ut in enumerate(self.__seq):
        #     for start, duration in ut:
        #         out.append((i, start + self.onsets[i], duration))
        # return iter(out)
        return zip(self.onsets, self.durations)

# Time Block
class TB:
    def __init__(self, tb:tuple[UTSeq]=(), offset:float=0.0, axis:float=0.0):
        self.__tb = tb
        self.__axis = axis
        self.__duration = max(ut_seq.duration for ut_seq in self.__tb) if self.__tb else 0.0

    @classmethod
    def from_tree_mat(cls, matrix, meas_denom:int=1, subdiv:bool=False,
                      rotation_offset:int=1, tempo=None, beat=None):
        tb = []
        for i, row in enumerate(matrix):
            seq = []
            for e in row:
                if subdiv:
                    D, S = e[0], subdivide_tree(e[1][::-1], i + rotation_offset)
                else:
                    D, S = e[0], e[1]
                seq.append(UT(tempus   = Meas((D, meas_denom)),
                              prolatio = S,
                              tempo    = tempo,
                              beat     = beat))
            tb.append(UTSeq(seq))
        return cls(tuple(tb))

    @property
    def utseqs(self):
        return self.__tb

    @property
    def duration(self):
        return self.__duration

    @property
    def axis(self):
        return self.__axis

    # XXX - TO DO:
    @axis.setter
    def axis(self, axis):
        self.__axis = axis
        pass

    def tempo(self, tempo):
        for utseq in self.__tb:
            for ut in utseq:
                ut.tempo = tempo

    def beat(self, beat):
        for utseq in self.__tb:
            for ut in utseq:
                ut.beat = beat

    def __add__(self, other:Union[UTSeq, 'TB']):
        if isinstance(other, UTSeq):
            return TB(self.__tb + (other,))
        # elif isinstance(other, TB):
        #     return TB(self.__tb + other.__tb)
        raise ValueError('Invalid Operand')

    def __iter__(self):
        return iter(self.__tb)

# Temporal Block Sequence
class TBSeq:
    pass
    # def __init__(self, tb_seq:tuple[TB]=(), offset:float=0.0):
    #     self.__seq = tb_seq
    #     for i, tb in enumerate(self.__seq):
    #         tb.offset = offset + sum(tb_seq[j].duration for j in range(i))

    # @property
    # def tbs(self):
    #     return self.__seq

    # @property
    # def onsets(self):
    #     return calc_onsets(self.durations)
    
    # @property    
    # def durations(self):
    #     return tuple(tb.duration for tb in self.__seq)
    
    # @property
    # def duration(self):
    #     return sum(self.durations)

    # def __add__(self, other:Union[TB, 'TBSeq']):
    #     if isinstance(other, TB):
    #         return TBSeq(self.__seq + (other,))
    #     elif isinstance(other, TBSeq):
    #         return TBSeq(self.__seq + other.__seq)
    #     raise ValueError('Invalid Operand')

    # def __and__(self, other:Union[TB, 'TBSeq']):
    #     if isinstance(other, TB):
    #         return TBSeq((self.__seq, (other,)))
    #     elif isinstance(other, TBSeq):
    #         return TBSeq((self.__seq, other.__seq))
    #     raise ValueError('Invalid Operand')

    # def __iter__(self):
    #     return zip(self.onsets, self.durations)
