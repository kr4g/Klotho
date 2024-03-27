
from typing import Union, Tuple
from fractions import Fraction
from math import gcd
from functools import reduce
import numpy as np

# ------------------------------------------------------------------------------------
# RHYTHM TREE ALGORITHMS
# ----------------------
# Let us recall that the mentioned part corresponds to the S part of a rhythmic tree 
# composed of (DS), that is its part constituting the proportions which can also 
# encompass other tree structures.  —- Karim Haddad
# ------------------------------------------------------------------------------------

# Algorithm 1: MeasureRatios
def measure_ratios(subdivisions:Tuple):
    '''
    Algorithm 1: MeasureRatios

    Pseudocode by Karim Haddad

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
    div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivisions)
    result = []
    for s in subdivisions:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(abs(D), div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return tuple(result)

# Algorithm 2: ReducedDecomposition
def reduced_decomposition(frac, meas):
    '''
    Algorithm 2: ReducedDecomposition
    
    Psuedocode by Karim Haddad
    
    Data: frac is a list of proportions; meas is the Tempus
    Result: Reduction of the proportions of frac.
    
    begin
        for all f of frac do
            (f * [numerator of meas]) / [denominator of meas];
        end for all
    end
    
    Reduces the proportions in fractions according to the given Tempus (meas).
    
    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of reduced proportions.
    '''
    return tuple(Fraction(f.numerator * meas.numerator,
                          f.denominator * meas.denominator) for f in frac)

# Algorithm 3: StrictDecomposition
def strict_decomposition(frac, meas):
    '''
    Algorithm 3: StrictDecomposition
    
    Pseudocode by Karim Haddad
    
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
    
    Decomposes the proportions in fractions with a common denominator, according to Tempus (meas).
    
    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of proportions with a common denominator.
    '''
    pgcd = reduce(gcd, (ratio.numerator for ratio in frac))
    pgcd_denom = meas.denominator
    return tuple(Fraction((Fraction(ratio.numerator, pgcd) * meas.numerator),
                                    pgcd_denom) for ratio in frac)

def factor(subdivs:tuple):
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor(subdivs:tuple, factors:tuple):
    def _refactor(subdivs, index):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                nested_result, index = _refactor(element, index)
                result.append(nested_result)
            else:
                result.append(factors[index])
                index += 1
        return tuple(result), index
    return _refactor(subdivs, 0)[0]

def calc_onsets(ratios:tuple):
   return tuple(np.cumsum([abs(r) for r in ratios]) - ratios[0])