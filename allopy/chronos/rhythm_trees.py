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
  def __init__(self, data):
    self.data = data

  @property
  def duration(self):
    return self.data[0]

  @property
  def time_signature(self):
    return self.data[1][0]

  @property
  def subdivisions(self):
    return self.data[1][1]

  def __getitem__(self, key):
    return self.data[key]

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

from fractions import Fraction

def reduced_decomposition(fractions, meas):
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
    
    :param fractions: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of reduced proportions.
    '''
    num, denom = meas
    return [Fraction(f.numerator * num, f.denominator * denom) for f in fractions]

def strict_decomposition(fractions, meas):
    '''
    Decomposes the proportions in fractions with a common denominator, according to Tempus (meas).
    
    :param fractions: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of proportions with a common denominator.
    '''
    num, denom = meas
    common_denom = reduce(lambda a, b: gcd(a, b.denominator), fractions, fractions[0].denominator)
    return [Fraction((f / common_denom).numerator * num, denom) for f in fractions]
