from fractions import Fraction
from typing import Union

from .rhythm_trees import RT
from utils.algorithms.algorithms import measure_ratios
from allopy.chronos.chronos import beat_duration

class UT:
    def __init__(self,
                 tempus:Union[str,Fraction]      = '1/1',
                 prolatio:Union[RT,tuple,str]    = 'r',
                 tempo:Union[None,float]         = None,
                 beat:Union[None,str,Fraction]   = None):
        
        self.__type        = None
        self.__tempus      = Fraction(tempus)
        self.__prolationis = self.__set_prolationis(prolatio) # RT object
        self.__tempo       = tempo
        self.__beat        = Fraction(beat) if isinstance(self.__beat, str) else beat 
        self.__duration    = 0
    
    @classmethod
    def from_tree(cls, tree:Union[RT, tuple]):
        meas = sum(measure_ratios(tree.subdivisions)) if isinstance(tree, tuple) else tree.time_signature
        s = tree.subdivisions if isinstance(tree, tuple) else tree.subdivisions
        return cls(tempus      = meas,
                   prolatio    = s,
                   tempo       = None,
                   beat        = None)

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
        if self.__duration is None:
            beat = Fraction(1, self.__tempus.denominator) if self.__beat is None else self.__beat
            self.__duration = sum(beat_duration(ratio      = r,
                                                bpm        = self.__tempo,
                                                beat_ratio = beat) for r in self.__prolationis.ratios)
        return self.__duration
    
    def __set_prolationis(self, prolatio):
        if isinstance(prolatio, RT) and self.__tempus != prolatio.time_signature: # if there's a difference...            
            self.__type = 'Ensemble'
            prolatio = RT(duration       = prolatio.duration,
                          time_signature = self.__tempus,  # ...the UT wins
                          subdivisions   = prolatio.subdivisions)
        elif isinstance(prolatio, tuple):
            self.__type = 'Ensemble'
            prolatio = RT(duration       = 1,
                          time_signature = self.__tempus,
                          subdivisions   = prolatio)
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


if __name__ == '__main__':  
    pass
