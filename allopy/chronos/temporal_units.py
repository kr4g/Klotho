from fractions import Fraction
from typing import Union

from .rhythm_trees import RT, Meas
from utils.algorithms.tree_algorithms import measure_ratios
from allopy.chronos.chronos import beat_duration, calc_onsets

class UT:
    def __init__(self,
                 tempus:Union[Meas,str]       = '1/1',
                 prolatio:Union[RT,tuple,str] = 'd',
                 tempo:Union[None,float]      = None,
                 beat:Union[str,Fraction]     = None):
        
        self.__type        = None
        self.__tempus      = Meas(tempus)
        self.__prolationis = self._set_prolationis(prolatio) # RT object
        self.__tempo       = tempo
        self.__beat        = self._set_beat(beat, prolatio)

        self.__onsets      = None
        self.__durations   = None
    
    @classmethod
    def from_tree(cls, tree:Union[RT, tuple]):
        meas = sum(measure_ratios(tree)) if isinstance(tree, tuple) else tree.time_signature
        s = tree if isinstance(tree, tuple) else tree.subdivisions
        return cls(tempus   = meas,
                   prolatio = s,
                   tempo    = None,
                   beat     = Fraction(1, meas.denominator))

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
    def onsets(self):
        if self.__tempo is None:
            return None
        if self.__onsets is None:
            self.__onsets = calc_onsets(self.durations)
        return self.__onsets

    @property
    def durations(self):
        if self.__tempo is None:
            return None
        if self.__durations is None:
            self.__durations = tuple(beat_duration(ratio      = r,
                                                   bpm        = self.__tempo,
                                                   beat_ratio = self.__beat) for r in self.__prolationis.ratios)
        return self.__durations

    @property
    def duration(self):
        if self.__tempo is None:
            return 0
        return sum(self.durations)
    
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
            comp = 'Complex' if prolatio.type else 'Simple'
            self.__type = f'Ensemble ({comp})'
        elif isinstance(prolatio, tuple):
            prolatio = RT(duration       = 1,
                          time_signature = self.__tempus,
                          subdivisions   = prolatio)
            comp = 'Complex' if prolatio.type else 'Simple'
            self.__type = f'Ensemble ({comp})'            
        elif isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in {'p', 'pulse', 'phase'}:
                self.__type = 'Pulse'
                prolatio = RT(duration       = 1,
                              time_signature = self.__tempus,
                              subdivisions   = (1,) * self.__tempus.numerator)
            elif prolatio in {'d', 'duration', 'dur'}:
                self.__type = 'Duration'
                prolatio = RT(duration       = 1,
                              time_signature = self.__tempus,
                              subdivisions   = (1,))
            elif prolatio in {'r', 'rest', 'silence'}:
                self.__type = 'Silence'
                prolatio = RT(duration       = 1,
                              time_signature = self.__tempus,
                              subdivisions   = (-1,))
            else:
                raise ValueError(f'Invalid string: {prolatio}')
        else:
            raise ValueError(f'Invalid prolationis: {prolatio}')
        return prolatio
    
    def _set_beat(self, beat, prolatio):
        if isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in {'p', 'pulse', 'phase',
                            'd', 'duration', 'dur',
                            'r', 'rest', 'silence'} and self.__beat is None:
                return Fraction(1, self.__tempus.denominator)
        return Fraction(beat)
    
    def __add__(self, other:Union['UT', Fraction]):
        if isinstance(other, UT):
            new_tempus = self.__tempus + other.__tempus
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
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
        return zip(
            self.onsets,
            self.durations,
        )
    
    def __repr__(self):
        return (
            f'Tempus: {self.__tempus}\n'
            f'Tempo: {self.__tempo}\n' if self.__tempo else ''
            f'Beat: {self.__beat}\n' 
            f'Prolationis: {self.__prolationis.subdivisions}\n'
            f'Type: {self.__type}\n'     
        )

class UTSeq:
    def __init__(self, ut_seq:tuple[UT]):
        self.__seq = ut_seq
    
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

    def __and__(self, other:Union[UT, 'UTSeq']):
        if isinstance(other, UT):
            return TB((self.__seq, (other,)))
        elif isinstance(other, UTSeq):
            return TB((self.__seq, other.__seq))
        raise ValueError('Invalid Operand')

    def __iter__(self):
        return zip(
            self.onsets,
            self.durations,
        )

# Time Block
class TB:
    def __init__(self, tb:tuple[UTSeq], axis:float=0.0):
        self.__tb = tb
        self.__axis = axis

    @property
    def utseqs(self):
        return self.__tb    

    @property
    def duration(self):
        return max(ut_seq.duration for ut_seq in self.__tb)
    
    @property
    def axis(self):
        return self.__axis

    @axis.setter
    def axis(self, axis):
        self.__axis = axis
        pass

    def __iter__(self):
        return iter(self.__tb)
    

if __name__ == '__main__':  
    pass
