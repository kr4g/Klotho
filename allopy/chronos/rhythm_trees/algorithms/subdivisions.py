from typing import Tuple
from fractions import Fraction
from math import gcd, lcm
from functools import reduce

# ------------------------------------------------------------------------------------
# TREE ALGORITHMS
# ----------------------
# 
# Algorithms that operate on either the S part of a rhythmic tree or its corresponding 
# proportions.
# 
# Pseudocode for numbered algorithms by Karim Haddad unless otherwise noted.
# 
# "Let us recall that the mentioned part corresponds to the S part of a rhythmic tree 
# composed of (DS), that is its part constituting the proportions which can also 
# encompass other tree structures."  —- Karim Haddad
# ------------------------------------------------------------------------------------

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
    div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivs)
    result = []
    for s in subdivs:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(D, div)
            # ratio = Fraction(abs(D), div)
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

def auto_subdiv(lst:tuple[int], n:int=1) -> tuple[tuple[int]]:
    def _recurse(idx:int) -> tuple:
        if idx == len(lst):
            return ()
        elt = lst[idx]
        next_elt = (elt, (1,) * lst[(idx + n) % len(lst)])
        return (next_elt,) + _recurse(idx + 1)
    return _recurse(0)

# def factor_subdivs(subdivs:tuple) -> tuple:
#     def _factor(subdivs, acc):
#         for element in subdivs:
#             if isinstance(element, tuple):
#                 _factor(element, acc)
#             else:
#                 acc.append(element)
#         return acc
#     return tuple(_factor(subdivs, []))

# def refactor_subdivs(subdivs:tuple, factors:tuple) -> tuple:
#     def _refactor(subdivs, index):
#         result = []
#         for element in subdivs:
#             if isinstance(element, tuple):
#                 nested_result, index = _refactor(element, index)
#                 result.append(nested_result)
#             else:
#                 result.append(factors[index])
#                 index += 1
#         return tuple(result), index
#     return _refactor(subdivs, 0)[0]

# def rotate_subdivs(subdivs:tuple, n:int=1) -> tuple:
#     factors = factor_subdivs(subdivs)
#     n = n % len(factors)
#     factors = factors[n:] + factors[:n]
#     return refactor_subdivs(subdivs, factors)

def sum_proportions(S:tuple) -> int:
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in S)

def measure_complexity(tree:tuple) -> bool:
    '''
    Assumes a tree in the form (D S) where D represents a duration and S represents a list
    of subdivisions.  S can be also be in the form (D S).

    Recursively traverses the tree.  For any element, if the sum of S != D, return True.
    '''    
    for s in tree:
        if isinstance(s, tuple):
            D, S = s
            div = sum_proportions(S)
            # XXX - this only works for duple meters!!!!!
            if bin(div).count("1") != 1 and div != D:
                return True
            else:
                return measure_complexity(S)
    return False
