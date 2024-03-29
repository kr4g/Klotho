from fractions import Fraction
from typing import Union

from .rhythm_trees import RT
from utils.algorithms.algorithms import measure_ratios
from allopy.chronos.chronos import beat_duration

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
        self.__duration    = None
    
    @classmethod
    def from_tree(cls, tree:Union[RT, tuple]):
        meas = sum(measure_ratios(tree)) if isinstance(tree, tuple) else tree.time_signature
        s = tree if isinstance(tree, tuple) else tree.subdivisions
        return cls(tempus   = meas,
                   prolatio = s,
                   tempo    = None,
                   beat     = None)

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
    def duration(self):
        if self.__tempo is None:
            return None
        self.__duration = sum(beat_duration(ratio      = r,
                                            bpm        = self.__tempo,
                                            beat_ratio = self.__beat) for r in self.__prolationis.ratios)
        return self.__duration
    
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
        if isinstance(beat, str):
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
    
    def __repr__(self):
        return (
            f'Tempus: {self.__tempus}\n'
            f'Prolationis: {self.__prolationis.subdivisions}\n'            
        )

if __name__ == '__main__':  
    pass
