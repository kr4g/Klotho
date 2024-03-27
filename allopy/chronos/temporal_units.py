from fractions import Fraction
import numpy as np
from math import prod

class UT:
    def __init__(self, tempus: tuple, prolatio: tuple, tempo: float = 60, beat = '1/4') -> None:
        self.tempus      = Fraction(tempus[0], tempus[1]) if isinstance(tempus, tuple) else tempus
        self.prolationis = prolatio
        self.tempo       = tempo
        self.beat        = Fraction(beat)
    
    @property
    def tempus(self):
        return self.__tempus
    
    @property
    def prolationis(self):        
        return self.__prolationis
    
    @property
    def tempo(self):
        return self.__tempo

    @property
    def beat(self):
        return self.__beat



def rhythm_pair(lst, is_MM=True):
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)


if __name__ == '__main__':  
    pass
