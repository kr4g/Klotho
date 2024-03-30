
from typing import Union, List, Tuple, Dict, Set
from math import prod
from itertools import combinations
from fractions import Fraction
from allopy.tonos.tonos import *

class CPS:
  '''
  Calculate a Combination Product Set (CPS) scale from a list of prime factors and a rank value.
  
  The Hexany is a six-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Hexany
  
  Args:
    prime_factors: List of primes to generate the Hexany.
    r: Rank value indicating the number of primes to combine.
    
  Returns:
    A tuple containing two lists:
    - The first list contains the products of combinations of prime factors.
    - The second list is the sorted Hexany scale after octave reduction.
  '''
  def __init__(self, factors: Tuple[int] = (1, 3, 5, 7), r: int = 2):
    self.__factors = tuple(sorted(factors))
    self.__r = r
    self.__pairs, self.__products, self.__ratios = self.__calculate()

  @property
  def factors(self):
    return self.__factors
  
  @property
  def rank(self):
    return self.__r
  
  @property
  def ratios(self):
    return self.__ratios
  
  @property
  def products(self):
    return self.__products
  
  @property
  def pairs(self):
    return self.__pairs

  def __calculate(self):
    combos   = tuple(combinations(self.__factors, self.__r))
    products = tuple(prod(comb) for comb in combos)
    ratios   = tuple(sorted(octave_reduce(Fraction(product)) for product in products))
    return combos, products, ratios

  def __repr__(self):
    r_str = tuple([str(r) for r in self.__ratios])
    out = f'{self.__factors} -> {self.__products}, {r_str}'
    return out
