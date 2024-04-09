import numpy as np
from itertools import combinations

# ------------------------------------------------------------------------------
# Set Operations
# --------------

def union(set1: set, set2: set) -> set:        
    '''Return the union of two sets.'''
    return set1 | set2

def intersect(set1: set, set2: set) -> set:
    '''Return the intersection of two sets.'''
    return set1 & set2

def diff(set1: set, set2: set) -> set:
    '''Return the difference of two sets (elements in set1 but not in set2).'''
    return set1 - set2

def symm_diff(set1: set, set2: set) -> set:
    '''Return the symmetric difference of two sets (elements in either set1 or set2 but not both).'''
    return set1 ^ set2

def is_subset(subset: set, superset: set) -> bool:
    '''Check if the first set is a subset of the second set.'''
    return subset <= superset

def is_superset(superset: set, subset: set) -> bool:
    '''Check if the first set is a superset of the second set.'''
    return superset >= subset

def invert(set1: set, axis: int = 0, modulus: int = 12) -> set:
    '''Invert a set around a given axis using modular arithmetic.'''
    return {(axis * 2 - pitch) % modulus for pitch in set1}

def transpose(set1: set, transposition_interval: int, modulus: int = 12) -> set:
    '''Transpose a set by a given interval using modular arithmetic.'''
    return {(pitch + transposition_interval) % modulus for pitch in set1}

def complement(S: set, modulus: int = 12) -> set:
    '''Return the complement of a set within a given modulus.'''
    return {s for s in range(modulus) if s not in S}

def congruent(S: set, modulus: int, residue: int) -> set:
    '''Return the set of all values in set1 that are congruent modulo the given modulus and residue.'''
    return {s for s in S if s % modulus == residue}

def intervals(S: set) -> set:
    '''
    Calculate the set of intervals between successive numbers in a sorted sequence.

    Args:
        numbers (set): A set of numbers.

    Returns:
        set: A set of intervals between the successive numbers.
    '''
    S = sorted(S)
    return set(np.diff(S))

def interval_vector(set1: set, modulus: int = 12) -> np.ndarray:        
    '''
    Compute the interval vector of a set of pitches.

    The interval vector represents the number of occurrences of each interval between pitches in a set.
    Intervals larger than half the modulus are inverted to their complements.

    Args:
        set1 (set): A set of integers.
        modulus (int): The modulus to use for interval calculations, conventionally 12.

    Returns:
        np.ndarray: An array representing the interval vector.
    '''
    pitches = sorted(set1)
    intervals = np.zeros(modulus // 2, dtype=int)

    for pitch1, pitch2 in combinations(pitches, 2):
        interval = abs(pitch2 - pitch1)
        interval = min(interval, modulus - interval)
        intervals[interval - 1] += 1

    return intervals

# ------------------------------------------------------------------------------
# Sieves
# ------

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
    
    @N.setter
    def N(self, N):
        self.__N = N
        self.__S = set(np.arange(self.__residue, self.__N + 1, self.__modulus))
    
    @property
    def congr(self):
        return congruent(self.__S, self.__modulus, self.__residue)
    
    @property
    def compl(self):
        return complement(self.__S, self.__N)
    