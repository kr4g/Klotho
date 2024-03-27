# ------------------------------------------------------------------------------------
# AlloPy/allopy/chronos/rhythm_trees.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------

A rhythm tree (RT) is a list representing a rhythmic structure. This list is organized 
hierarchically in sub lists , just as time is organized in measures, time signatures, 
pulses and rhythmic elements in the traditional notation.

Hence, the expression form of rhythm trees is crucially different from that of onsets 
and offsets. It can be exacting and not very "ergonomic", from a musician's point of 
view : rhythm trees can be long, with a great number of parenthesis and sub lists nested 
within each others.

This module provides the syntactic and semantic principles that rule rhythm trees.

see: https://support.ircam.fr/docs/om/om6-manual/co/RT.html

--------------------------------------------------------------------------------------
'''

from fractions import Fraction
from math import gcd
from functools import reduce
import numpy as np

class RT:
  '''
  A rhythm tree is a list representing a rhythmic structure. This list is organized 
  hierarchically in sub lists, just as time is organized in measures, time signatures, 
  pulses and rhythmic elements in the traditional notation.

  Traditionally, rhythm is broken up into several data : meter, measure(s) and duration(s). 
  Rhythm trees must enclose these information in lists and sub list.

  This elementary rhythm:
  
  [1/4, 1/4, 1/4, 1/4] --> (four 1/4-notes in 4/4 time)
  
  can be expressed as follows :

    ( ? ( (4//4 (1 1 1 1) ) ) )
    
  A tree structure can be reduced to a list : (D (S)).
  
  
  >> Main Components : Duration and Subdivisions
  
    D = a duration , or number of measures : ( ? ) or a number ( n ).
    When D = ?, OM calculates the duration.
    By default, this duration is equal to 1.
  
    S = subdivisions (S) of this duration, that is a time signature and rhythmic proportions.
    Time signature = n // n   or ( n n ).
    It must be specified at each new measure, even if it remains unchanged.
    
    Rhythm = proportions : ( n n n n )

  see: https://support.ircam.fr/docs/om/om6-manual/co/RT1.html
  '''
  def __init__(self, duration='?', time_signature=(1,1), subdivisions=(1,), strict_decomp=False):
    self.__duration       = Fraction(1, 1) if duration == '?' else Fraction(duration)
    self.__time_signature = Fraction(time_signature)
    self.__subdivisions   = subdivisions
    self.__strict_decomp  = strict_decomp
    self.__ratios         = tuple(self.__duration * r for r in measure_ratios(self.subdivisions))
    self.__ratios         = strict_decomposition(self.__ratios, self.__time_signature) if self.__strict_decomp else self.__ratios

  @property
  def duration(self):
    return self.__duration

  @property
  def time_signature(self):
    return self.__time_signature

  @property
  def subdivisions(self):
    return self.__subdivisions

  @property
  def decomp(self):
    return 'Strict' if self.__strict_decomp else 'Reduced'
  
  @property
  def ratios(self):
    return self.__ratios
  
  @property
  def factors(self):
    return factor(self.subdivisions)
  
  def rotate(self, n=1):
    factors = factor(self.subdivisions)
    n = n % len(factors)
    factors = factors[n:] + factors[:n]
    refactored = refactor(self.__subdivisions, factors)
    return RT(duration=self.duration, time_signature=self.time_signature, subdivisions=refactored, strict_decomp=self.__strict_decomp)

  def __repr__(self):
    ratios = ', '.join(tuple([str(r) for r in self.ratios]))
    return f'Duration: {self.duration}\nTime Signature: {self.time_signature}\nSubdivisions: {self.subdivisions}\nDecomposition: {self.decomp}\nRatios: {ratios}'

# ------------------------------------------------------------------------------------
# Let us recall that the mentioned part corresponds to the S part of a rhythmic tree 
# composed of (DS), that is its part constituting the proportions which can also 
# encompass other tree structures.  —- Karim Haddad
# ------------------------------------------------------------------------------------

# Algorithm 1: MeasureRatios
def measure_ratios(tree):
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
    if not tree:
        return []

    if isinstance(tree, RT):
        tree = tree.subdivisions

    div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in tree)
    result = []
    for s in tree:
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(abs(D), div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return result

def reduced_decomposition(ratios, meas):
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
    num, denom = meas
    return tuple(Fraction(f.numerator * num, f.denominator * denom) for f in ratios)

def strict_decomposition(ratios, meas):
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
    num, denom = meas
    pgcd = reduce(gcd, (ratio.numerator for ratio in ratios))
    pgcd_denom = denom
    # return tuple(Fraction((ratio.numerator // pgcd) * num, pgcd_denom) for ratio in ratios)
    return tuple(Fraction((Fraction(ratio.numerator, pgcd) * num), pgcd_denom) for ratio in ratios)


def factor(subdivs):
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor(subdivs, factors):
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

def calc_onsets(ratios):
   return np.cumsum([abs(r) for r in ratios]) - ratios[0]


# ------------------------------------------------------------------------------------
# EXPERIMENTAL
# ------------------------------------------------------------------------------------
def sum_proportions(tree):
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in tree)

def notate(tree, level=0):
    if isinstance(tree, RT):
        return f'\time {tree.time_signature}\n' + notate(tree.subdivisions, level)
    
    if isinstance(tree, tuple) and level == 0:
        tuplet_value = sum_proportions(tree)
        return f'\tuplet {tuplet_value}/d ' + '{{' + notate(tree, level+1) + '}}'
    else:
        result = ""
        for element in tree:
            if isinstance(element, int):  # Rest or single note
                if element < 0:  # Rest
                    result += f" -{abs(element)}"
                else:  # Single note
                    result += f" {element}"
            elif isinstance(element, tuple):  # Subdivision
                D, S = element
                if isinstance(D, int):  # If D is an integer, calculate the proportion
                    tuplet_value = sum_proportions(S) if isinstance(S, tuple) else D
                else:  # If D is a tuple, it's a nested tuplet
                    tuplet_value = sum_proportions(D)
                result += f' \\tuplet {tuplet_value}/d {{{notate(S, level+1)}}}'
            if level == 0:
                result = result.strip() + ' '
        return result.strip()
# ------------------------------------------------------------------------------------



if __name__ == '__main__':  
    # ------------------------------------------------------------------------------------
    # Rhythm Tree Examples
    # ------------------------------------------------------------------------------------
    # 
    subdivisions = ((2, (1, 2, 1)), (5, (2, 1, (3, (3, 2)), 1)))
    r_tree = RT(subdivisions=subdivisions)
    print(r_tree)
