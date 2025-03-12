# ------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_trees/algorithms/subdivs.py
# ------------------------------------------------------------------------
'''
------------------------------------------------------------------------------------
TREE ALGORITHMS
---------------

Algorithms that operate on either the S part of a rhythmic tree or its corresponding 
proportions.

Pseudocode for numbered algorithms by Karim Haddad unless otherwise noted.

"Let us recall that the mentioned part corresponds to the S part of a rhythmic tree 
composed of (DS), that is its part constituting the proportions which can also 
encompass other tree structures."  —- Karim Haddad
------------------------------------------------------------------------------------
'''
from typing import Tuple
from fractions import Fraction
from math import gcd, lcm, prod
from functools import reduce
import numpy as np
from typing import Union

# Algorithm 1: MeasureRatios
def measure_ratios(subdivs:tuple[int]) -> Tuple[Fraction]:
    '''
    Algorithm 1: MeasureRatios

    Data: S is the part of a RT
    Result: Transforms the part (s) of a rhythm tree into fractional proportions.

    div = for all s elements of S do
    if s is a list of the form (DS) then 
        return |D of s|;
    else
        return |s|;
    end if
    end for all
    begin
        for all s of S do
            if s is a list then
                return (|D of s| / div) * MeasureRatios(S of s);
            else
                |s|/div;
            end if
        end for all
    end
    '''
    # div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivs)
    div = sum_proportions(subdivs)
    result = []
    for s in subdivs:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(D, div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return tuple(result)

# Algorithm 2: ReducedDecomposition
def reduced_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
    '''
    Algorithm 2: ReducedDecomposition
    
    Data: frac is a list of proportions; meas is the Tempus
    Result: Reduction of the proportions of frac.
    
    begin
        for all f of frac do
            (f * [numerator of meas]) / [denominator of meas];
        end for all
    end
        
    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of reduced proportions.
    '''
    return tuple(Fraction(f.numerator * meas.numerator, f.denominator * meas.denominator) for f in lst)

# Algorithm 3: StrictDecomposition
def strict_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
    '''
    Algorithm 3: StrictDecomposition
    
    Data: liste is a list of proportions resulting from MeasureRatios; meas is the Tempus
    Result: List of proportions with common denominators.
    
    num = numerator of meas;
    denom = denominator of meas;
    pgcd = gcd of the list;
    pgcd_denom = denominator of pgcd;
    
    begin
        foreach i of liste do
            [ ((i/pgcd) * num) , pgcd_denom ];
        end foreach
    end

    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of proportions with a common denominator.
    '''
    pgcd = reduce(gcd, (ratio.numerator for ratio in lst))
    pgcd_denom = reduce(lcm, (ratio.denominator for ratio in lst))
    return tuple(Fraction((f / pgcd) * meas.numerator, pgcd_denom) for f in lst)

# ------------------------------------------------------------------------------------

def ratios_to_subdivs(ratios:tuple[Fraction]) -> tuple[int]:
    common_denom = reduce(lcm, (abs(f.denominator) for f in ratios), 1)
    ints = [int(f * common_denom) for f in ratios]
    overall_gcd = reduce(gcd, ints)
    return tuple(x // overall_gcd for x in ints)

# ------------------------------------------------------------------------------------

def auto_subdiv(subdivs:tuple[int], n:int=1) -> tuple[tuple[int]]:
    '''
    Algorithm: AutoSubdiv
    
    Data: S is the part of a RT; n is the number of rotations
    Result: Automatic subdivision of S
    
    TODO: pseudocode
    '''
    def _recurse(idx:int) -> tuple:
        if idx == len(subdivs):
            return ()
        elt = subdivs[idx]
        next_elt = (elt, (1,) * subdivs[(idx + n) % len(subdivs)])
        return (next_elt,) + _recurse(idx + 1)
    return _recurse(0)

def auto_subdiv_matrix(matrix, rotation_offset=1):
    '''
    Applies auto_subdiv to each element in a matrix of tree specifications.
    
    This function takes a matrix where each element is a tuple (D, S) with D representing
    a duration and S representing subdivisions. It applies auto_subdiv to each element's
    subdivisions with a rotation offset that depends on the element's position in the matrix.
    
    Args:
        matrix: A matrix (tuple of tuples) where each element is a tuple (D, S)
        rotation_offset: Base offset for rotation calculations (default: 1)
        
    Returns:
        A new matrix with the same structure but with auto_subdiv applied to each element
    '''
    result = []
    for i, row in enumerate(matrix):
        new_row = []
        for j, e in enumerate(row):
            offset = rotation_offset * i
            D, S = e[0], auto_subdiv(e[1], j - i + offset)
            new_row.append((D, S))
        result.append(tuple(new_row))
    return tuple(result)

def rhythm_pair(lst:Tuple, MM:bool=True) -> Tuple:
    total_product = prod(lst)
    if MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(int(x) for x in deltas)

def segment(ratio: Union[Fraction, float, str]) -> tuple[int]:
    """
    Segments a ratio into a tuple of two integers.
    
    Args:
        ratio (Union[Fraction, float, str]): The ratio to segment.
        
    Returns:
        tuple[int]: A tuple of two integers representing the numerator and denominator of the ratio.
    """
    ratio = Fraction(ratio)
    if ratio >= 1:
        raise ValueError("Ratio must be less than 1")
    return (ratio.numerator, ratio.denominator - ratio.numerator)

# ------------------------------------------------------------------------------------

def sum_proportions(S:tuple) -> int:
    '''
    '''
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in S)

def measure_complexity(subdivs:tuple) -> bool:
    '''
    Assumes a tree in the form (D S) where D represents a duration and S represents a list
    of subdivisions.  S can be also be in the form (D S).

    Recursively traverses the tree.  For any element, if the sum of S != D, return True.
    '''    
    for s in subdivs:
        if isinstance(s, tuple):
            D, S = s
            div = sum_proportions(S)
            # XXX - only works for binary meters!!!
            if bin(div).count("1") != 1 and div != D:
                return True
            else:
                return measure_complexity(S)
    return False

def clean_subdivs(subdivs:tuple) -> tuple:
    pass

# def flatten(self):
#     return RhythmTree.from_ratios(self._ratios, self._span, self._decomp)

# def rotate(self, n:int = 1):
#     return RhythmTree.from_tree(rotate_tree(self, n), self._span, self._decomp)
