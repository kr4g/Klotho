from abc import ABC
from typing import Union, Dict, Tuple
from math import prod
from fractions import Fraction

from klotho.topos.collections import CombinationSet as CS
from klotho.tonos.utils import reduce_interval

__all__ = [
    'CombinationProductSet',
    'Hexany',
    'Dekany',
    'Pentadekany',
    'Eikosany',
    'Diamond',
]

class CombinationProductSet(CS, ABC):
  '''
  General class for an arbitrary Combination Product Set (CPS).
  
  Abstract Base Class for Hexany, Dekany, Pentadekany, and Eikosany class implementations.
  
  A combination product set (CPS) is a scale generated by the following means:
  
      1. A set S of n positive real numbers is the starting point.
      
      2. All the combinations of k elements of the set are obtained, and their 
          products taken.
          
      3. These are combined into a set, and then all of the elements of that set 
          are divided by one of them (which one is arbitrary; if a canonical choice 
          is required, the smallest element could be used).
          
      4. The resulting elements are octave-reduced and sorted in ascending order, 
          resulting in an octave period of a periodic scale (the usual sort of 
          scale, in other words) which we may call CPS(S, k).
  
  see: https://en.xen.wiki/w/Combination_product_set
  '''
  def __init__(self, factors: Tuple[int], r: int, normalized: bool = False):
    super().__init__(factors, r)
    self._normalized = normalized
    self._products, self._ratios, self._mappings = self._calculate()

  @property
  def products(self):
    return self._products
  
  @property
  def ratios(self):
    return self._ratios
  
  @property
  def combo_to_product(self):
    return self._mappings['combo_to_prod']
  
  @property
  def product_to_combo(self):
    return self._mappings['prod_to_combo']
  
  @property
  def combo_to_ratio(self):
    return self._mappings['combo_to_ratio']
  
  @property
  def ratio_to_combo(self):
    return self._mappings['ratio_to_combo']
  
  @property
  def product_to_ratio(self):
    return self._mappings['prod_to_ratio']
  
  @property
  def ratio_to_product(self):
    return self._mappings['ratio_to_prod']

  def _calculate(self):
    products = []
    ratios = []
    combo_to_prod = {}
    combo_to_ratio = {}
    prod_to_ratio = {}
    
    for combo in self._combos:
      product = prod(combo)
      products.append(product)
      combo_to_prod[combo] = product
    
    norm_prod = min(products) if self._normalized else 1
    
    for combo, product in combo_to_prod.items():
      ratio = reduce_interval(Fraction(product, norm_prod))
      ratios.append(ratio)
      combo_to_ratio[combo] = ratio
      prod_to_ratio[product] = ratio
    
    sorted_products = tuple(sorted(products))
    sorted_ratios = tuple(sorted(ratios))
    
    if self._normalized:
      sorted_ratios = sorted_ratios[1:] + (Fraction(2),)
    
    prod_to_combo = {v: k for k, v in combo_to_prod.items()}
    ratio_to_combo = {v: k for k, v in combo_to_ratio.items()}
    ratio_to_prod = {v: k for k, v in prod_to_ratio.items()}
    
    mappings = {
      'combo_to_prod': combo_to_prod,
      'prod_to_combo': prod_to_combo,
      'combo_to_ratio': combo_to_ratio,
      'ratio_to_combo': ratio_to_combo,
      'prod_to_ratio': prod_to_ratio,
      'ratio_to_prod': ratio_to_prod
    }
    
    return sorted_products, sorted_ratios, mappings

  def __str__(self):
    ratios = ', '.join(str(ratio) for ratio in self.ratios)
    return super().__str__() + (
      f'Products: {self.products}\n'
      f'Ratios:   {ratios}\n'
    )
  
  def __repr__(self):
    return self.__str__()


class Hexany(CombinationProductSet):
  '''
  Calculate a Hexany scale from a list of factors and a rank value.
  
  The Hexany is a six-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Hexany
        https://en.xen.wiki/w/Hexany
  
  '''  
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7), normalized:bool = False):
    if len(factors) != 4:
      raise ValueError('Hexany must have exactly 4 factors.')
    super().__init__(factors, r=2, normalized=normalized)

class Dekany(CombinationProductSet):
  '''
  A dekany is a 10-note scale built using all the possible combinations 
  of either 2 or 3 intervals (but not a mix of both) from a given set of 
  5 intervals. It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Dekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11), r:int = 2, normalized:bool = False):
    if len(factors) != 5:
      raise ValueError('Dekany must have exactly 5 factors.')
    if not r in (2, 3):
      raise ValueError('Dekany rank must be 2 or 3.')
    super().__init__(factors, r, normalized)
    
class Pentadekany(CombinationProductSet):
  '''
  A pentadekany is a 15-note scale built using all the possible combinations
  of either 2 or 4 intervals (but not a mix of both) from a given set of 6 
  intervals. Pentadekanies may be chiral, and the choice of whether to take 
  combinations of 2 or 4 elements is equivalent to choosing the chirality. 
  It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Pentadekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11, 13), r:int = 2, normalized:bool = False):
    if len(factors) != 6:
      raise ValueError('Pentadekany must have exactly 6 factors.')
    if not r in (2, 4):
      raise ValueError('Pentadekany rank must be 2 or 4.')
    super().__init__(factors, r, normalized)

class Eikosany(CombinationProductSet):
  '''
  An eikosany is a 20-note scale built using all the possible combinations 
  of 3 intervals from a given set of 6 intervals. It is a particular case 
  of a combination product set (CPS).
  
  see:  https://en.xen.wiki/w/Eikosany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 9, 11), normalized:bool = False):
    if len(factors) != 6:
      raise ValueError('Eikosany must have exactly 6 factors.')
    super().__init__(factors, r=3, normalized=normalized)

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
