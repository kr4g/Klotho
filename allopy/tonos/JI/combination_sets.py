from abc import ABC
from typing import Union
from math import prod
from itertools import combinations
from fractions import Fraction

from allopy.topos.sets import CombinationProductSet as CPS
# from utils.algorithms.cps_algorithms import *
from allopy.tonos.tonos import fold_interval

# XXX - call fold_interval octavize instead?
  
class _nkany(CPS, ABC):
  '''
  Abstract Base Class for inheritance purposes only.  
  
  Used for Hexany, Dekany, Pentadekany, and Eikosany class implementations.
  '''
  def __new__(cls, *args, **kwargs):
    if cls is _nkany:
      raise TypeError(f'{cls.__name__} class may not be instantiated.')
    return super().__new__(cls)
  
  def __init__(self, factors:tuple[int], r:int, normalized:bool = False):
    super().__init__(factors, r)
    self._products, self._ratios = self._calculate(normalized)

  @property
  def products(self):
    return self._products
  
  @property
  def ratios(self):
    return self._ratios

  def _calculate(self, normalize:bool):
    products = tuple(prod(comb) for comb in self._combos)
    norm_prod = min(products) if normalize else 1
    ratios = tuple(sorted(fold_interval(Fraction(product, norm_prod)) for product in products))
    if normalize:
      ratios = ratios[1:] + (Fraction(2),)
    return products, ratios
  
  def __str__(self):
    ratios = ', '.join(str(ratio) for ratio in self._ratios)
    return super().__str__() + (
      f'Products: {self._products}\n'
      f'Ratios:   {ratios}\n'
    )

class Hexany(_nkany):
  '''
  Calculate a Hexany scale from a list of factors and a rank value.
  
  The Hexany is a six-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Hexany
        https://en.xen.wiki/w/Hexany
  
  '''  
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7)):
    # Hexany must be 4 factors with rank 2
    if len(factors) != 4:
      raise ValueError('Hexany must have exactly 4 factors.')
    super().__init__(factors, r=2)

class Dekany(_nkany):
  '''
  A dekany is a 10-note scale built using all the possible combinations 
  of either 2 or 3 intervals (but not a mix of both) from a given set of 
  5 intervals. It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Dekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11), r:int = 2):
    if len(factors) != 5:
      raise ValueError('Dekany must have exactly 5 factors.')
    if not r in (2, 3):
      raise ValueError('Dekany rank must be 2 or 3.')
    super().__init__(factors, r)
    
class Pentadekany(_nkany):
  '''
  A pentadekany is a 15-note scale built using all the possible combinations
  of either 2 or 4 intervals (but not a mix of both) from a given set of 6 
  intervals. Pentadekanies may be chiral, and the choice of whether to take 
  combinations of 2 or 4 elements is equivalent to choosing the chirality. 
  It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Pentadekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11, 13), r:int = 2):
    if len(factors) != 6:
      raise ValueError('Pentadekany must have exactly 6 factors.')
    if not r in (2, 4):
      raise ValueError('Pentadekany rank must be 2 or 4.')
    super().__init__(factors, r)

class Eikosany(_nkany):
  '''
  An eikosany is a 20-note scale built using all the possible combinations 
  of 3 intervals from a given set of 6 intervals. It is a particular case 
  of a combination product set (CPS).
  
  see:  https://en.xen.wiki/w/Eikosany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 9, 11)):
    # Eikosany must be exactly 6 factors with rank 3
    if len(factors) != 6:
      raise ValueError('Eikosany must have exactly 6 factors.')
    super().__init__(factors, r=3)

class Diamond:
  '''
  Calculate the ratios of each odd number up to and including the upper limit to every other odd number 
  in the set, grouped by common denominators.

  Args:
    upper_limit: An integer representing the upper limit to generate the odd numbers.

  Returns:
    A tuple of tuples, each inner tuple containing ratios of each odd number to every other odd number, 
    grouped by common denominators.
  '''
  def __init__(self, n:Union[tuple, int]):
    self.__factors = tuple(range(1, n + 1, 2)) if isinstance(n, int) else tuple(sorted(n))
    self.__ratio_sets = self._calculate()

  def _calculate(self):
    return tuple(
      tuple(Fraction(numerator, denominator) for numerator in self.__factors)
      for denominator in self.__factors
    )
  
  @property
  def limit(self):
    return self.__factors[-1]

  @property
  def factors(self):
    return self.__factors
  
  @property
  def ratio_sets(self):
    return self.__ratio_sets
  
  @property
  def otonal(self):
    pass

  @property
  def utonal(self):
    pass

  def __repr__(self):
    return (
      f'Limit:   {self.__factors[-1]}\n'
      f'Factors: {self.__factors}\n'
    )
