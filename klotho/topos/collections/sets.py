import numpy as np
from itertools import combinations
import pandas as pd
import math
from fractions import Fraction
from functools import cached_property
from typing import List, Tuple, Set, Dict, Any, Union, Literal
import sympy as sp
from scipy.spatial.distance import pdist, squareform
from ..graphs import Graph


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
    """
    Static methods for mathematical set operations.

    This class provides a collection of static methods for performing
    common set operations including union, intersection, difference,
    and specialized musical set operations like transposition and inversion.

    Methods
    -------
    union(set1, set2)
        Return the union of two sets.
    intersect(set1, set2)
        Return the intersection of two sets.
    diff(set1, set2)
        Return the difference of two sets.
    symm_diff(set1, set2)
        Return the symmetric difference of two sets.
    is_subset(subset, superset)
        Check if the first set is a subset of the second set.
    is_superset(superset, subset)
        Check if the first set is a superset of the second set.
    invert(set1, axis, modulus)
        Invert a set around a given axis using modular arithmetic.
    transpose(set1, transposition_interval, modulus)
        Transpose a set by a given interval using modular arithmetic.
    complement(S, modulus)
        Return the complement of a set within a given modulus.
    congruent(S, modulus, residue)
        Return elements congruent to a residue modulo the given modulus.
    intervals(S)
        Calculate intervals between successive numbers in a sorted sequence.
    interval_vector(set1, modulus)
        Compute the interval vector of a set of pitches.

    Examples
    --------
    Basic set operations:
    
    >>> set1 = {0, 1, 4, 7}
    >>> set2 = {0, 2, 5, 9}
    >>> Operations.union(set1, set2)
    {0, 1, 2, 4, 5, 7, 9}
    
    Musical transformations:
    
    >>> chord = {0, 4, 7}  # C major triad
    >>> Operations.transpose(chord, 5, 12)  # Transpose up a fourth
    {5, 9, 0}
    """
    @staticmethod
    def union(set1: set, set2: set) -> set:        
        """
        Return the union of two sets.

        Parameters
        ----------
        set1 : set
            The first set.
        set2 : set
            The second set.

        Returns
        -------
        set
            A new set containing all unique elements from both sets.
        """
        return set1 | set2

    @staticmethod
    def intersect(set1: set, set2: set) -> set:
        """
        Return the intersection of two sets.

        Parameters
        ----------
        set1 : set
            The first set.
        set2 : set
            The second set.

        Returns
        -------
        set
            A new set containing only elements present in both sets.
        """
        return set1 & set2

    @staticmethod
    def diff(set1: set, set2: set) -> set:
        """
        Return the difference of two sets.

        Parameters
        ----------
        set1 : set
            The first set.
        set2 : set
            The second set.

        Returns
        -------
        set
            A new set containing elements in set1 but not in set2.
        """
        return set1 - set2

    @staticmethod
    def symm_diff(set1: set, set2: set) -> set:
        """
        Return the symmetric difference of two sets.

        Parameters
        ----------
        set1 : set
            The first set.
        set2 : set
            The second set.

        Returns
        -------
        set
            A new set containing elements in either set1 or set2 but not both.
        """
        return set1 ^ set2

    @staticmethod
    def is_subset(subset: set, superset: set) -> bool:
        """
        Check if the first set is a subset of the second set.

        Parameters
        ----------
        subset : set
            The potential subset.
        superset : set
            The potential superset.

        Returns
        -------
        bool
            True if subset is a subset of superset, False otherwise.
        """
        return subset <= superset

    @staticmethod
    def is_superset(superset: set, subset: set) -> bool:
        """
        Check if the first set is a superset of the second set.

        Parameters
        ----------
        superset : set
            The potential superset.
        subset : set
            The potential subset.

        Returns
        -------
        bool
            True if superset is a superset of subset, False otherwise.
        """
        return superset >= subset

    @staticmethod
    def invert(set1: set, axis: int = 0, modulus: int = 12) -> set:
        """
        Invert a set around a given axis using modular arithmetic.

        Parameters
        ----------
        set1 : set
            The set to invert.
        axis : int, optional
            The axis of inversion (default is 0).
        modulus : int, optional
            The modulus for the arithmetic (default is 12).

        Returns
        -------
        set
            The inverted set.

        Examples
        --------
        >>> chord = {0, 4, 7}  # C major triad
        >>> Operations.invert(chord, axis=0, modulus=12)
        {0, 8, 5}
        """
        return {(axis * 2 - pitch) % modulus for pitch in set1}

    @staticmethod
    def transpose(set1: set, transposition_interval: int, modulus: int = 12) -> set:
        """
        Transpose a set by a given interval using modular arithmetic.

        Parameters
        ----------
        set1 : set
            The set to transpose.
        transposition_interval : int
            The interval to transpose by.
        modulus : int, optional
            The modulus for the arithmetic (default is 12).

        Returns
        -------
        set
            The transposed set.

        Examples
        --------
        >>> chord = {0, 4, 7}  # C major triad
        >>> Operations.transpose(chord, 7, 12)  # Transpose up a fifth
        {7, 11, 2}
        """
        return {(pitch + transposition_interval) % modulus for pitch in set1}

    @staticmethod
    def complement(S: set, modulus: int = 12) -> set:
        """
        Return the complement of a set within a given modulus.

        Parameters
        ----------
        S : set
            The set to complement.
        modulus : int, optional
            The modulus defining the universal set (default is 12).

        Returns
        -------
        set
            The complement set containing all elements from 0 to modulus-1 not in S.

        Examples
        --------
        >>> pentatonic = {0, 2, 4, 7, 9}
        >>> Operations.complement(pentatonic, 12)
        {1, 3, 5, 6, 8, 10, 11}
        """
        return {s for s in range(modulus) if s not in S}

    @staticmethod
    def congruent(S: set, modulus: int, residue: int) -> set:
        """
        Return elements congruent to a residue modulo the given modulus.

        Parameters
        ----------
        S : set
            The input set.
        modulus : int
            The modulus for congruence testing.
        residue : int
            The residue value to match.

        Returns
        -------
        set
            Elements from S that are congruent to residue modulo modulus.

        Examples
        --------
        >>> numbers = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}
        >>> Operations.congruent(numbers, 3, 1)  # Numbers ≡ 1 (mod 3)
        {1, 4, 7}
        """
        return {s for s in S if s % modulus == residue}

    @staticmethod
    def intervals(S: set) -> set:
        """
        Calculate intervals between successive numbers in a sorted sequence.

        Parameters
        ----------
        S : set
            A set of numbers.

        Returns
        -------
        set
            The intervals between consecutive elements when sorted.

        Examples
        --------
        >>> scale = {0, 2, 4, 5, 7, 9, 11}  # Major scale
        >>> Operations.intervals(scale)
        {1, 2}
        """
        S = sorted(S)
        return set(np.diff(S))

    @staticmethod
    def interval_vector(set1: set, modulus: int = 12) -> np.ndarray:        
        """
        Compute the interval vector of a set of pitches.

        The interval vector represents the number of occurrences of each interval 
        between pitches in a set. Intervals larger than half the modulus are 
        inverted to their complements.

        Parameters
        ----------
        set1 : set
            A set of integers representing pitches.
        modulus : int, optional
            The modulus for interval calculations (default is 12).

        Returns
        -------
        numpy.ndarray
            An array representing the interval vector with length modulus//2.

        Examples
        --------
        >>> chord = {0, 4, 7}  # C major triad
        >>> Operations.interval_vector(chord, 12)
        array([0, 0, 1, 1, 1, 0])
        """
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
    """
    Xenakis-style sieve for generating sets through modular arithmetic operations.

    A Sieve implements Iannis Xenakis's concept of sieves, which are mathematical
    structures based on modular arithmetic used in algorithmic composition. 
    A sieve can represent a single modular constraint or complex combinations 
    of multiple constraints using logical operations.

    In Xenakis's notation, a basic sieve is written as (m,r) where m is the 
    modulus and r is the residue. Complex sieves combine these using union (∪), 
    intersection (∩), and complement operations.

    Parameters
    ----------
    modulus : int, optional
        The step size of the arithmetic progression (default is 1).
    residue : int, optional
        The starting value of the progression (default is 0).
    N : int, optional
        The upper bound for generated values (default is 255).

    Attributes
    ----------
    S : set
        The generated sieve values.
    N : int
        The upper bound for generated values.
    period : int
        The modulus (step size) of the sieve.
    r : int
        The residue (starting value) of the sieve.
    congr : set
        Values congruent to the residue modulo the period.
    compl : set
        The complement of the sieve within [0, N].

    Examples
    --------
    Create a basic sieve (3,1) - multiples of 3 starting from 1:
    
    >>> sieve = Sieve(modulus=3, residue=1, N=10)
    >>> print(sorted(sieve.S))
    [1, 4, 7, 10]
    
    See Also
    --------
    Operations.union : Combine sieves using union operation
    Operations.intersect : Combine sieves using intersection operation
    
    Notes
    -----
    This implementation provides the foundation for Xenakis sieve theory.
    For complex sieve expressions, use the Operations class methods to
    combine multiple Sieve instances with logical operations.
    """
    def __init__(self, modulus: int = 1, residue: int = 0, N: int = 255):
        """
        Initialize a Sieve.

        Parameters
        ----------
        modulus : int, optional
            The step size of the arithmetic progression (default is 1).
        residue : int, optional
            The starting value of the progression (default is 0).
        N : int, optional
            The upper bound for generated values (default is 255).
        """
        self.__S = set(np.arange(residue, N + 1, modulus))
        self.__N = N
        self.__modulus = modulus
        self._residue = residue
    
    @property
    def S(self):
        """
        The generated sieve values.
        
        Returns
        -------
        set
            The set of integers generated by the sieve.
        """
        return self.__S
    
    @property
    def N(self):
        """
        The upper bound for generated values.
        
        Returns
        -------
        int
            The maximum value in the sieve range.
        """
        return self.__N
    
    @property
    def period(self):
        """
        The modulus (step size) of the sieve.
        
        Returns
        -------
        int
            The step size of the arithmetic progression.
        """
        return self.__modulus
    
    @property
    def r(self):
        """
        The residue (starting value) of the sieve.
        
        Returns
        -------
        int
            The starting value of the arithmetic progression.
        """
        return self._residue

    @property
    def congr(self):
        """
        Values congruent to the residue modulo the period.
        
        Returns
        -------
        set
            Elements in S that are congruent to residue mod period.
        """
        return Operations.congruent(self.__S, self.__modulus, self._residue)
    
    @property
    def compl(self):
        """
        The complement of the sieve within [0, N].
        
        Returns
        -------
        set
            All integers from 0 to N that are not in the sieve.
        """
        return Operations.complement(self.__S, self.__N)
    
    @N.setter
    def N(self, N: int):
        """
        Set the upper bound and regenerate the sieve.
        
        Parameters
        ----------
        N : int
            The new upper bound for the sieve.
        """
        self.__N = N
        self.__S = set(np.arange(self._residue, N + 1, self.__modulus))
    
    def __str__(self) -> str:
        """
        String representation of the Sieve.
        
        Returns
        -------
        str
            A formatted string showing the sieve parameters and values.
        """
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

    def __repr__(self) -> str:        
        """
        String representation of the Sieve.
        
        Returns
        -------
        str
            A formatted string showing the sieve parameters and values.
        """
        return self.__str__()
    
    def __or__(self, other: 'Sieve') -> set:
        """
        Union operation between two sieves (Xenakis: A ∪ B).
        
        Parameters
        ----------
        other : Sieve
            The other sieve to combine with.
        
        Returns
        -------
        set
            The union of both sieve sets.
        
        Examples
        --------
        >>> sieve1 = Sieve(3, 1, 10)  # (3,1)
        >>> sieve2 = Sieve(5, 2, 10)  # (5,2)
        >>> combined = sieve1 | sieve2
        >>> print(sorted(combined))
        [1, 2, 4, 7, 10]
        """
        return Operations.union(self.S, other.S)
    
    def __and__(self, other: 'Sieve') -> set:
        """
        Intersection operation between two sieves (Xenakis: A ∩ B).
        
        Parameters
        ----------
        other : Sieve
            The other sieve to intersect with.
        
        Returns
        -------
        set
            The intersection of both sieve sets.
        
        Examples
        --------
        >>> sieve1 = Sieve(2, 0, 20)  # Even numbers
        >>> sieve2 = Sieve(3, 0, 20)  # Multiples of 3
        >>> intersection = sieve1 & sieve2
        >>> print(sorted(intersection))
        [0, 6, 12, 18]
        """
        return Operations.intersect(self.S, other.S)
    
    def __sub__(self, other: 'Sieve') -> set:
        """
        Difference operation between two sieves (Xenakis: A - B).
        
        Parameters
        ----------
        other : Sieve
            The sieve to subtract from this one.
        
        Returns
        -------
        set
            Elements in this sieve but not in the other.
        
        Examples
        --------
        >>> sieve1 = Sieve(2, 0, 10)  # Even numbers
        >>> sieve2 = Sieve(4, 0, 10)  # Multiples of 4
        >>> difference = sieve1 - sieve2
        >>> print(sorted(difference))
        [2, 6, 10]
        """
        return Operations.diff(self.S, other.S)
    
    def __xor__(self, other: 'Sieve') -> set:
        """
        Symmetric difference operation between two sieves (A ⊕ B).
        
        Parameters
        ----------
        other : Sieve
            The other sieve for symmetric difference.
        
        Returns
        -------
        set
            Elements in either sieve but not in both.
        
        Examples
        --------
        >>> sieve1 = Sieve(2, 0, 10)  # Even numbers
        >>> sieve2 = Sieve(3, 0, 10)  # Multiples of 3
        >>> sym_diff = sieve1 ^ sieve2
        >>> print(sorted(sym_diff))
        [2, 3, 4, 8, 9, 10]
        """
        return Operations.symm_diff(self.S, other.S)
    
    def __invert__(self) -> set:
        """
        Complement operation for the sieve (~A).
        
        Returns
        -------
        set
            All integers from 0 to N that are not in this sieve.
        
        Examples
        --------
        >>> sieve = Sieve(2, 0, 10)  # Even numbers
        >>> complement = ~sieve
        >>> print(sorted(complement))
        [1, 3, 5, 7, 9]
        """
        return self.compl
        

# ------------------------------------------------------------------------------
#  Generated Collection
# --------------

class GenCol:
    """
    Generated Collection - A multiplicative collection formed by repeatedly applying a generator.

    A multiplicative collection created by starting with an initial value and repeatedly
    multiplying by the generator, reducing modulo the period. This is the multiplicative
    analog to the Sieve class, useful for generating multiplicative pitch collections
    and harmonic series subsets.

    Parameters
    ----------
    generator : Union[str, int, float, Fraction]
        The generator value used for multiplication.
    period : Union[str, int, float, Fraction], optional
        The period of equivalence (default is 2).
    iterations : int, optional
        Number of times to apply the generator (default is 12).

    Attributes
    ----------
    generator : Fraction
        The generator value as a Fraction.
    period : Fraction
        The period of equivalence as a Fraction.
    iterations : int
        Number of generator applications.
    collection : list of Fraction
        The raw generated collection values.
    normalized_collection : list of Fraction
        Collection values normalized within the period.
    steps : set of Fraction
        Interval steps between consecutive normalized values.

    Examples
    --------
    Create a collection with default parameters (perfect fifth generator):
    
    >>> gen_col = GenCol()  # Uses '3/2' generator, period=2, iterations=7
    >>> print(*[str(f) for f in gen_col.normalized_collection])
    1 3/2 9/8 27/16 81/64 243/128 729/512 2187/2048
    """
    def __init__(self, generator: Union[str,int,float,Fraction] = '3/2', period: Union[str,int,float,Fraction] = 2, iterations: int = 7):
        """
        Initialize a Generated Collection.

        Parameters
        ----------
        generator : Union[str, int, float, Fraction], optional
            The generator value used for multiplication (default is '3/2').
        period : Union[str, int, float, Fraction], optional
            The period of equivalence (default is 2).
        iterations : int, optional
            Number of times to apply the generator (default is 7).
        """
        self._generator = Fraction(generator)
        self._period = Fraction(period)
        self._iterations = iterations
        self._collection = self._generate()
        
    @property
    def generator(self) -> Fraction:
        """
        The generator value as a Fraction.
        
        Returns
        -------
        Fraction
            The generator used for multiplication.
        """
        return self._generator
    
    @property
    def period(self) -> Fraction:
        """
        The period of equivalence as a Fraction.
        
        Returns
        -------
        Fraction
            The period within which values are considered equivalent.
        """
        return self._period
    
    @property
    def iterations(self) -> int:
        """
        Number of generator applications.
        
        Returns
        -------
        int
            The number of times the generator is applied.
        """
        return self._iterations
    
    @property
    def collection(self) -> List[Fraction]:
        """
        The raw generated collection values.
        
        Returns
        -------
        list of Fraction
            A copy of the generated collection values.
        """
        return self._collection.copy()
    
    @cached_property
    def normalized_collection(self) -> List[Fraction]:
        """
        Collection values normalized within the period.
        
        Returns
        -------
        list of Fraction
            The collection values reduced to within the period range.
        """
        normalized = []
        for value in self._collection:
            current = value
            while current >= self._period:
                current /= self._period
            normalized.append(current)
        return normalized
    
    @cached_property
    def steps(self) -> Set[Fraction]:
        """
        Interval steps between consecutive normalized values.
        
        Returns
        -------
        set of Fraction
            The intervals between consecutive values in the normalized collection.
        """
        values = sorted(self.normalized_collection)
        steps = set()
        
        for i in range(len(values)):
            if i < len(values) - 1:
                steps.add(values[i+1] / values[i])
            else:
                steps.add(self._period * values[0] / values[i])
        
        return steps
    
    def _generate(self) -> List[Fraction]:
        """
        Generate the collection by applying the generator iteratively.
        
        Returns
        -------
        list of Fraction
            The generated collection values.
        """
        return [self._generator ** i for i in range(self._iterations + 1)]
    
    def __str__(self):
        """
        String representation of the GenCol.
        
        Returns
        -------
        str
            Compact string representation showing generator, period, and iterations.
        """
        return f"GenCol(gen={self._generator}, period={self._period}, n={self._iterations})"
    
    def __repr__(self):
        """
        String representation of the GenCol.
        
        Returns
        -------
        str
            Compact string representation showing generator, period, and iterations.
        """
        return self.__str__()


# --------------------------------------------------------------------------------
# Combination Sets (CS)
# ---------------------

class CombinationSet:
    """
    A combinatorial set generating all r-combinations from a set of factors.

    This class generates all possible combinations of size r from a given set of factors,
    useful for combinatorial analysis and set operations. It also creates symbolic
    aliases and an associated graph structure for analysis.

    Parameters
    ----------
    factors : tuple, optional
        The factors to combine (default is ('A', 'B', 'C', 'D')).
    r : int, optional
        The size of each combination (default is 2).

    Attributes
    ----------
    factors : tuple
        The sorted tuple of input factors.
    rank : int
        The size of each combination.
    combos : set
        The set of all r-combinations from the factors.
    graph : networkx.Graph
        A complete graph with combinations as nodes.
    factor_to_alias : dict
        Mapping from factors to symbolic aliases.
    alias_to_factor : dict
        Mapping from symbolic aliases to factors.

    Examples
    --------
    Create combinations with default parameters:
    
    >>> cs = CombinationSet()  # Uses ('A', 'B', 'C', 'D') with r=2
    >>> print(cs.combos)
    {('A', 'B'), ('A', 'C'), ('A', 'D'), ('B', 'C'), ('B', 'D'), ('C', 'D')}
    """
    def __init__(self, factors:tuple = ('A', 'B', 'C', 'D'), r:int = 2):
        """
        Initialize a CombinationSet.

        Parameters
        ----------
        factors : tuple, optional
            The factors to combine (default is ('A', 'B', 'C', 'D')).
        r : int, optional
            The size of each combination (default is 2).
        """
        self._factors = tuple(sorted(factors))
        self._r = r
        self._combos = set(combinations(self._factors, self._r))
        self._factor_aliases = {f: sp.Symbol(chr(65 + i)) for i, f in enumerate(self._factors)}
        self._graph = self._generate_graph()

    @property
    def factors(self):
        """
        The sorted tuple of input factors.
        
        Returns
        -------
        tuple
            The factors used to generate combinations.
        """
        return self._factors
    
    @property
    def rank(self):
        """
        The size of each combination.
        
        Returns
        -------
        int
            The number of elements in each combination.
        """
        return self._r
    
    @property
    def combos(self):
        """
        The set of all r-combinations from the factors.
        
        Returns
        -------
        set
            All possible combinations of size r from the factors.
        """
        return self._combos
    
    @property
    def graph(self):
        """
        A complete graph with combinations as nodes.
        
        Returns
        -------
        Graph
            A complete graph where each node represents a combination.
        """
        return self._graph
    
    @property
    def factor_to_alias(self):
        """
        Mapping from factors to symbolic aliases.
        
        Returns
        -------
        dict
            Dictionary mapping each factor to a symbolic representation.
        """
        return self._factor_aliases
    
    @property
    def alias_to_factor(self):
        """
        Mapping from symbolic aliases to factors.
        
        Returns
        -------
        dict
            Dictionary mapping symbolic representations back to factors.
        """
        return {v: k for k, v in self._factor_aliases.items()}
    
    def _generate_graph(self):
        """
        Generate a complete graph with combinations as nodes.
        
        Returns
        -------
        Graph
            A complete graph where each node has a 'combo' attribute.
        """
        n_nodes = len(self._combos)
        G = Graph.complete_graph(n_nodes)
        for i, combo in enumerate(self._combos):
            G[i]['combo'] = combo
        return G
    
    def __str__(self):    
        """
        String representation of the CombinationSet.
        
        Returns
        -------
        str
            A formatted string showing rank, factors, and combinations.
        """
        return (        
            f'Rank:    {self._r}\n'
            f'Factors: {self._factors}\n'
            f'Combos:  {self._combos}\n'
        )
    
    def __repr__(self) -> str:
        """
        String representation of the CombinationSet.
        
        Returns
        -------
        str
            A formatted string showing rank, factors, and combinations.
        """
        return self.__str__()


# ------------------------------------------------------------------------------
#  Partition Set
# --------------

class PartitionSet:
    """
    A set of integer partitions with associated graph structures for analysis.

    This class generates all partitions of an integer n into exactly k parts,
    analyzes their structural properties, and creates various graph representations
    for studying relationships between partitions.

    Parameters
    ----------
    n : int
        The integer to partition.
    k : int
        The number of parts in each partition.
    graph_type : {'feature_distance', 'decomposition_tree', 'substructure_embedding'}, optional
        The type of graph to construct (default is 'feature_distance').

    Attributes
    ----------
    data : pandas.DataFrame
        DataFrame containing partitions and their computed features.
    partitions : tuple
        Tuple of all generated partitions.
    mean : float
        The mean value of partition parts (n/k).
    graph : networkx.Graph or networkx.DiGraph
        Graph representation based on the specified graph_type.
    graph_type : str
        The type of graph construction used.

    Examples
    --------
    Generate partitions of 8 into 3 parts:
    
    >>> ps = PartitionSet(8, 3)
    >>> ps.data
       partition  unique_count  span  variance
    0  (6, 1, 1)             2     5    5.5556
    1  (5, 2, 1)             3     4    2.8889
    2  (4, 3, 1)             3     3    1.5556
    3  (4, 2, 2)             2     2    0.8889
    4  (3, 3, 2)             2     1    0.2222
    """
    def __init__(self, n: int, k: int, graph_type: Literal['feature_distance', 'decomposition_tree', 'substructure_embedding'] = 'feature_distance'):
        """
        Initialize a PartitionSet.

        Parameters
        ----------
        n : int
            The integer to partition.
        k : int
            The number of parts in each partition.
        graph_type : {'feature_distance', 'decomposition_tree', 'substructure_embedding'}, optional
            The type of graph to construct (default is 'feature_distance').
        """
        self._n = n
        self._k = k
        self._graph_type = graph_type
        self._data = self._generate_partitions()
        self._graph = self._generate_graph()
    
    def _generate_partitions(self) -> pd.DataFrame:
        """
        Generate all partitions of n into k parts with computed features.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame with columns for partition, unique_count, span, and variance.
        """
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
    
    def _generate_graph(self):
        """
        Generate a graph based on the specified graph type.
        
        Returns
        -------
        networkx.Graph or networkx.DiGraph
            The generated graph representation of partition relationships.
        
        Raises
        ------
        ValueError
            If an unknown graph type is specified.
        """
        if self._graph_type == 'feature_distance':
            return self._build_feature_distance_graph()
        elif self._graph_type == 'decomposition_tree':
            return self._build_decomposition_tree_graph()
        elif self._graph_type == 'substructure_embedding':
            return self._build_substructure_embedding_graph()
        else:
            raise ValueError(f"Unknown graph type: {self._graph_type}")
    
    def _build_feature_distance_graph(self):
        """
        Build a graph where edge weights represent feature distances.
        
        Returns
        -------
        Graph
            A complete graph with edge weights based on normalized feature distances.
        """
        features = self._data[['unique_count', 'span', 'variance']].values
        features_normalized = (features - features.mean(axis=0)) / (features.std(axis=0) + 1e-8)
        distances = pdist(features_normalized, metric='euclidean')
        distance_matrix = squareform(distances)
        
        G = Graph()
        n_partitions = len(self._data)
        
        for i in range(n_partitions):
            G.add_node(partition=tuple(self._data.iloc[i]['partition']))
        
        for i in range(n_partitions):
            for j in range(i + 1, n_partitions):
                G.add_edge(i, j, weight=distance_matrix[i, j])
        
        return G
    
    def _build_decomposition_tree_graph(self):
        """
        Build a graph where edge weights represent transformation costs.
        
        Returns
        -------
        Graph
            A complete graph with edge weights based on partition transformation costs.
        """
        partitions = [tuple(row['partition']) for _, row in self._data.iterrows()]
        G = Graph()
        
        for i, partition in enumerate(partitions):
            G.add_node(partition=partition)
        
        for i, partition_a in enumerate(partitions):
            for j, partition_b in enumerate(partitions):
                if i < j:
                    cost = self._partition_transformation_cost(partition_a, partition_b)
                    G.add_edge(i, j, weight=cost)
        
        return G
    
    def _partition_transformation_cost(self, partition_a: tuple, partition_b: tuple) -> float:
        """
        Calculate the cost of transforming one partition to another.
        
        Parameters
        ----------
        partition_a : tuple
            The first partition.
        partition_b : tuple
            The second partition.
        
        Returns
        -------
        float
            The transformation cost between the partitions.
        """
        a_parts = sorted(partition_a, reverse=True)
        b_parts = sorted(partition_b, reverse=True)
        
        max_len = max(len(a_parts), len(b_parts))
        a_padded = a_parts + [0] * (max_len - len(a_parts))
        b_padded = b_parts + [0] * (max_len - len(b_parts))
        
        cost = sum(abs(a - b) for a, b in zip(a_padded, b_padded)) / 2.0
        
        return cost
    
    def _build_substructure_embedding_graph(self):
        """
        Build a directed graph based on substructure embedding costs.
        
        Returns
        -------
        Graph
            A directed graph where edge weights represent embedding costs.
        """
        partitions = [tuple(row['partition']) for _, row in self._data.iterrows()]
        G = Graph.digraph()
        
        for i, partition in enumerate(partitions):
            G.add_node(partition=partition)
        
        for i, partition_a in enumerate(partitions):
            for j, partition_b in enumerate(partitions):
                if i != j:
                    embedding_cost = self._substructure_embedding_cost(partition_a, partition_b)
                    G.add_edge(i, j, weight=embedding_cost)
        
        return G
    
    def _substructure_embedding_cost(self, partition_a: tuple, partition_b: tuple) -> float:
        """
        Calculate the cost of embedding one partition structure into another.
        
        Parameters
        ----------
        partition_a : tuple
            The partition to embed.
        partition_b : tuple
            The target partition for embedding.
        
        Returns
        -------
        float
            The embedding cost between the partitions.
        """
        a_parts = sorted(partition_a, reverse=True)
        b_parts = sorted(partition_b, reverse=True)
        
        b_remaining = list(b_parts)
        total_cost = 0.0
        
        for a_part in a_parts:
            best_match_cost = float('inf')
            best_match_idx = -1
            
            for idx, b_part in enumerate(b_remaining):
                if b_part >= a_part:
                    cost = abs(b_part - a_part) / max(a_part, 1)
                    if cost < best_match_cost:
                        best_match_cost = cost
                        best_match_idx = idx
                else:
                    cost = 2.0 + (a_part - b_part) / a_part
                    if cost < best_match_cost:
                        best_match_cost = cost
                        best_match_idx = idx
            
            if best_match_idx != -1:
                total_cost += best_match_cost
                if b_remaining[best_match_idx] >= a_part:
                    b_remaining[best_match_idx] -= a_part
                    if b_remaining[best_match_idx] == 0:
                        b_remaining.pop(best_match_idx)
                else:
                    b_remaining.pop(best_match_idx)
            else:
                total_cost += 5.0
        
        return total_cost
    
    @property
    def data(self):
        """
        DataFrame containing partitions and their computed features.
        
        Returns
        -------
        pandas.DataFrame
            DataFrame with partition, unique_count, span, and variance columns.
        """
        return self._data
    
    @property
    def partitions(self):
        """
        Tuple of all generated partitions.
        
        Returns
        -------
        tuple
            All partitions of n into k parts.
        """
        return tuple(self._data['partition'])
    
    @property
    def mean(self) -> float:
        """
        The mean value of partition parts.
        
        Returns
        -------
        float
            The arithmetic mean n/k.
        """
        return self._n / self._k
    
    @property
    def graph(self):
        """
        Graph representation based on the specified graph_type.
        
        Returns
        -------
        Graph
            The graph representation of partition relationships.
        """
        return self._graph
    
    @property
    def graph_type(self):
        """
        The type of graph construction used.
        
        Returns
        -------
        str
            The graph type identifier.
        """
        return self._graph_type

    def __str__(self) -> str:
        """
        String representation of the PartitionSet.
        
        Returns
        -------
        str
            A formatted string showing partition data and statistics.
        """
        display_df = self._data.copy()
        display_df['variance'] = display_df['variance'].round(4)
        
        df_str = str(display_df)
        width = max(len(line) for line in df_str.split('\n'))
        border = '-' * width
        
        header = (
            f"{border}\n"
            f"PS(n={self._n}, k={self._k}) - Graph: {self._graph_type}\n"
            f"Mean: ~{round(self.mean, 4)}\n"
            f"{border}\n"
        )
        return header + df_str + f"\n{border}\n"
    
    def __repr__(self) -> str:
        """
        String representation of the PartitionSet.
        
        Returns
        -------
        str
            A formatted string showing partition data and statistics.
        """
        return self.__str__()

