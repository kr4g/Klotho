from fractions import Fraction
from typing import Union
import numpy as np

from .rhythm_trees import RT
from utils.algorithms.algorithms import measure_ratios
from allopy.chronos.chronos import beat_duration, calc_onsets

class UT:
    def __init__(self,
                 tempus:Union[str,Fraction]   = '1/1',
                 prolatio:Union[RT,tuple,str] = 'd',
                 tempo:Union[None,float]      = None,
                 beat:Union[str,Fraction]     = '1/1'):
        
        self.__type        = None
        self.__tempus      = Fraction(tempus)
        self.__prolationis = self.__set_prolationis(prolatio) # RT object
        self.__tempo       = tempo
        self.__beat        = self.__set_beat(beat, prolatio)
    
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
        return calc_onsets(self.durations)

    @property
    def durations(self):
        if self.__tempo is None:
            return None
        return tuple(beat_duration(ratio      = r,
                                   bpm        = self.__tempo,
                                   beat_ratio = self.__beat) for r in self.__prolationis.ratios)

    @property
    def duration(self):
        if self.__tempo is None:
            return 0
        return sum(self.durations)
    
    @tempo.setter
    def tempo(self, tempo:Union[None,float,int]):
        self.__tempo = tempo
    
    @beat.setter
    def beat(self, beat:Union[str,Fraction]):
        self.__beat = Fraction(beat)    

    def __set_prolationis(self, prolatio):
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
    
    def __set_beat(self, beat, prolatio):
        if isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in {'p', 'pulse', 'phase',
                            'd', 'duration', 'dur',
                            'r', 'rest', 'silence'}:
                return Fraction(1, self.__tempus.denominator)
        else:
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
        if isinstance(other, UT):
            new_tempus = self.__tempus * other.__tempus
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, (Fraction, int)):
            new_tempus = self.__tempus * other
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        raise ValueError('Invalid Operand')
    
    def __truediv__(self, other:Union['UT', Fraction, int]):
        if isinstance(other, UT):
            new_tempus = self.__tempus / other.__tempus
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
                      tempo    = self.__tempo,
                      beat     = self.__beat)
        elif isinstance(other, (Fraction, int)):
            new_tempus = self.__tempus / other
            return UT(tempus   = new_tempus,
                      prolatio = 'd',
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
            f'Prolationis: {self.__prolationis.subdivisions}\n'            
        )

class UTSeq:
    def __init__(self, ut_seq:tuple[UT]):
        self.__seq = ut_seq
    
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
        return zip(self.__seq)

# Time Block
class TB:
    def __init__(self, tb:tuple[UTSeq]):
        self.__tb = tb
        
    def __iter__(self):
        return iter(self.__tb)

if __name__ == '__main__':  
    pass
