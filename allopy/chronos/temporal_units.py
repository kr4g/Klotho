from fractions import Fraction
from typing import Union

from rhythm_trees import RT
from allopy.chronos.chronos import beat_duration

class UT:
    def __init__(self,
                 tempus:Union[str, Fraction]     = '1/1',
                 prolatio:Union[RT, tuple, str]  = (1,),
                 tempo:Union[None, float]        = None,
                 beat:Union[None, str, Fraction] = None):
        
        self.__prolationis = prolatio
        self.__type        = self.__set_type(prolatio) # sets self.__prolationis as a RT object
        self.__tempus      = Fraction(tempus)
        self.__tempo       = tempo
        self.__beat        = Fraction(beat) if isinstance(self.__beat, str) else beat 
        # self.__duration    = self.duration
    
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
    
    def __set_type(self, prolatio):
        ut_type = None
        if isinstance(prolatio, str):
            prolatio = prolatio.lower()
            if prolatio in {'p', 'pulse', 'phase'}:
                self.__prolationis = RT(duration       = 1,
                                        time_signature = self.__tempus,
                                        subdivisions   = (1,) * self.__tempus.numerator)
                return 'Pulse'
            elif prolatio in {'d', 'duration', 'dur'}:
                self.__prolationis = RT(duration       = 1,
                                        time_signature = self.__tempus,
                                        subdivisions   = (1,))
                return 'Duration'
            elif prolatio in {'r', 'rest', 'silence'}:
                self.__prolationis = RT(duration       = 1,
                                        time_signature = self.__tempus,
                                        subdivisions   = (-1,))
                return 'Silence'
        elif isinstance(prolatio, RT) or isinstance(prolatio, tuple):
            self.__prolationis = RT(duration       = 1,
                                    time_signature = self.__tempus,
                                    subdivisions   = prolatio) if isinstance(prolatio, tuple) else prolatio
            subdivs = prolatio.subdivisions
            ut_type = 'Pulse' if all(isinstance(s, int) for s in subdivs) and len(set(subdivs)) == 1 else 'Ensemble'
            sub_sum = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivs)
            num = prolatio.time_signature.numerator
            return f'{ut_type} (Simple)' if sub_sum != num else f'{ut_type} (Complex)'
        else:
            raise ValueError(f'Invalid prolationis: {prolatio}')
        return ut_type


if __name__ == '__main__':  
    pass
