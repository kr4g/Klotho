import numpy as np
from itertools import combinations
import pandas as pd
import math
from fractions import Fraction
from typing import List, Tuple, Set, Dict, Any, Union
import networkx as nx
import sympy as sp

__all__ = [
    'Operations',
    'Sieve',
    'CombinationSet',
    'PartitionSet',
    'GenCol',
]

# ------------------------------------------------------------------------------
# Set Operations
# --------------

class Operations:
    '''
    Class for set operations.
    '''
    @staticmethod
    def union(set1: set, set2: set) -> set:        
        '''Return the union of two sets.'''
        return set1 | set2

    @staticmethod
    def intersect(set1: set, set2: set) -> set:
        '''Return the intersection of two sets.'''
        return set1 & set2

    @staticmethod
    def diff(set1: set, set2: set) -> set:
        '''Return the difference of two sets (elements in set1 but not in set2).'''
        return set1 - set2

    @staticmethod
    def symm_diff(set1: set, set2: set) -> set:
        '''Return the symmetric difference of two sets (elements in either set1 or set2 but not both).'''
        return set1 ^ set2

    @staticmethod
    def is_subset(subset: set, superset: set) -> bool:
        '''Check if the first set is a subset of the second set.'''
        return subset <= superset

    @staticmethod
    def is_superset(superset: set, subset: set) -> bool:
        '''Check if the first set is a superset of the second set.'''
        return superset >= subset

    @staticmethod
    def invert(set1: set, axis: int = 0, modulus: int = 12) -> set:
        '''Invert a set around a given axis using modular arithmetic.'''
        return {(axis * 2 - pitch) % modulus for pitch in set1}

    @staticmethod
    def transpose(set1: set, transposition_interval: int, modulus: int = 12) -> set:
        '''Transpose a set by a given interval using modular arithmetic.'''
        return {(pitch + transposition_interval) % modulus for pitch in set1}

    @staticmethod
    def complement(S: set, modulus: int = 12) -> set:
        '''Return the complement of a set within a given modulus.'''
        return {s for s in range(modulus) if s not in S}

    @staticmethod
    def congruent(S: set, modulus: int, residue: int) -> set:
        '''Return the set of all values in set1 that are congruent modulo the given modulus and residue.'''
        return {s for s in S if s % modulus == residue}

    @staticmethod
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

    @staticmethod
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

class Sieve:
    def __init__(self, modulus: int = 1, residue: int = 0, N: int = 255):
        self.__S = set(np.arange(residue, N + 1, modulus))
        self.__N = N
        self.__modulus = modulus
        self._residue = residue
    
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
        return self._residue

    @property
    def congr(self):
        return Operations.congruent(self.__S, self.__modulus, self._residue)
    
    @property
    def compl(self):
        return Operations.complement(self.__S, self.__N)
    
    @N.setter
    def N(self, N: int):
        self.__N = N
        self.__S = set(np.arange(self._residue, N + 1, self.__modulus))
    
    def __str__(self) -> str:
        if len(self.__S) > 10:
            sieve = f'{list(self.__S)[:5]} ... {list(self.__S)[-1]}'
        else:
            sieve = list(self.__S)
        return (
            f'Period:  {self.__modulus}\n'
            f'Residue: {self._residue}\n'
            f'N:       {self.__N}\n'
            f'Sieve:   {sieve}\n'
        )

    def _repr__(self) -> str:        
        return self.__str__()
    

# ------------------------------------------------------------------------------
#  Generated Collection
# --------------

class GenCol:
    """
    Generated Collection - A multiplicative collection formed by repeatedly
    applying a generator within a periodic space.
    
    The collection is created by starting with an initial value (default 1)
    and repeatedly multiplying by the generator, reducing modulo the period.
    
    This is the multiplicative analog to the Sieve class.
    """
    def __init__(self, generator: Union[str,int,float,Fraction], period: Union[str,int,float,Fraction] = 2, iterations: int = 12, normalize: bool = True):
        """
        Initialize a Generated Collection.
        
        Args:
            generator: The generator value (as str, int, float, or Fraction)
            period: The period of equivalence (as str, int, float, or Fraction)
            iterations: Number of times to apply the generator
            normalize: If True, values will be normalized within the period
        """
        self._generator = Fraction(generator)
        self._period = Fraction(period)
        self._iterations = iterations
        self._normalize = normalize
        self._generate()
        
    @property
    def generator(self) -> Fraction:
        return self._generator
    
    @property
    def period(self) -> Fraction:
        return self._period
    
    @property
    def iterations(self) -> int:
        return self._iterations
        
    @iterations.setter
    def iterations(self, value: int):
        self._iterations = value
        self._generate()
    
    @property
    def normalize(self) -> bool:
        return self._normalize
    
    @normalize.setter
    def normalize(self, value: bool):
        self._normalize = value
        self._generate()
    
    @property
    def collection(self) -> List[Fraction]:
        return self._collection.copy()
    
    @property
    def sorted_collection(self) -> List[Fraction]:
        return sorted(self._collection)
    
    @property
    def steps(self) -> List[Fraction]:
        values = sorted(self._collection)
        steps = []
        
        for i in range(len(values)):
            if i < len(values) - 1:
                steps.append(values[i+1] / values[i])
            elif self._normalize:
                steps.append(self._period * values[0] / values[i])
        
        return steps
    
    def _generate(self):
        self._collection = [Fraction(1, 1)]
        current = Fraction(1, 1)
        
        for _ in range(self._iterations):
            current = current * self._generator
            
            if self._normalize:
                while current >= self._period:
                    current /= self._period
            
            self._collection.append(current)
    
    def __str__(self):
        result = (
            f"Generated Collection\n"
            f"Generator: {self._generator}\n"
            f"Period: {self._period}\n"
            f"Iterations: {self._iterations}\n"
            f"Normalize: {self._normalize}\n"
        )
        
        if len(self._collection) <= 20:
            sorted_values = sorted(self._collection)
            result += f"Values (sorted): {', '.join([str(s) for s in sorted_values])}\n"
            result += f"Steps: {', '.join([str(s) for s in self.steps])}\n"
        
        return result
    
    def __repr__(self):
        return self.__str__()


# --------------------------------------------------------------------------------
# Combination Sets (CS)
# ---------------------

class CombinationSet:
    '''
    A class representing a combination set where elements from a set of factors
    are combined according to a specified rank parameter.
    
    This class generates all combinations of size r from a set of factors.
    '''
    def __init__(self, factors:tuple = ('A', 'B', 'C', 'D'), r:int = 2):
        self._factors = tuple(sorted(factors))
        self._r = r
        self._combos = set(combinations(self._factors, self._r))
        self._factor_aliases = {f: sp.Symbol(chr(65 + i)) for i, f in enumerate(self._factors)}
        self._graph = self._generate_graph()

    @property
    def factors(self):
        return self._factors
    
    @property
    def rank(self):
        return self._r
    
    @property
    def combos(self):
        return self._combos
    
    @property
    def graph(self):
        return self._graph
    
    @property
    def factor_to_alias(self):
        return self._factor_aliases
    
    @property
    def alias_to_factor(self):
        return {v: k for k, v in self._factor_aliases.items()}
    
    def _generate_graph(self):
        G = nx.DiGraph()
        for i, combo in enumerate(self._combos):
            G.add_node(i, combo=combo)
        return G
    
    def __str__(self):    
        return (        
            f'Rank:    {self._r}\n'
            f'Factors: {self._factors}\n'
            f'Combos:  {self._combos}\n'
        )
    
    def _repr__(self) -> str:
        return self.__str__()


# ------------------------------------------------------------------------------
#  Partition Set
# --------------

class PartitionSet:
    def __init__(self, n: int, k: int):
        self._n = n
        self._k = k
        self._data = self._generate_partitions()
    
    def _generate_partitions(self) -> pd.DataFrame:
        '''
        Generate all possible partitions of n into k parts using backtracking,
        computing metadata for each partition as it's generated.
        
        Returns:
            pd.DataFrame: DataFrame containing partitions and their metadata.
        '''
        def backtrack(remaining: int, k: int, start: int, current: tuple) -> list:
            if k == 0:
                if remaining == 0:
                    return [{
                        'partition': current,
                        'unique_count': len(set(current)),
                        'span': max(current) - min(current),
                        'variance': np.var(current)
                    }]
                return []
            
            results = []
            for x in range(start, 0, -1):
                if x <= remaining:
                    results.extend(backtrack(remaining - x, k - 1, x, current + (x,)))
            return results
                    
        return pd.DataFrame(backtrack(self._n, self._k, self._n, ()))
    
    @property
    def data(self):
        return self._data
    
    @property
    def partitions(self):
        return tuple(self._data['partition'])
    
    @property
    def mean(self) -> float:
        '''The mean value of every partition in this set.'''
        return self._n / self._k

    def __str__(self) -> str:
        display_df = self._data.copy()
        display_df['variance'] = display_df['variance'].round(4)
        
        df_str = str(display_df)
        width = max(len(line) for line in df_str.split('\n'))
        border = '-' * width
        
        header = (
            f"{border}\n"
            f"PS(n={self._n}, k={self._k})\n"
            f"Mean: ~{round(self.mean, 4)}\n"
            f"{border}\n"
        )
        return header + df_str + f"\n{border}\n"
    
    def __repr__(self) -> str:
        return self.__str__()

