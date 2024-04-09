import numpy as np

class Sieve():
    def __init__(self, modulus: int = 1, residue: int = 0, N: int = 255):
        self.__S = set(np.arange(residue, N + 1, modulus))
    
    @property
    def S(self):
        return self.__S
    
    @property
    def N(self):
        return self.__N
    
    @property
    def period(self):
        return self.__modulus
    
    @property
    def r(self):
        return self.__residue
    
    @property
    def congruent(self):
        ''' Returns a set of all values in the sieve that are congruent modulo the sieve's period. '''
        return {x for x in self.__S if x % self.__modulus == self.__residue}