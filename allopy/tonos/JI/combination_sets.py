from abc import ABC
from typing import Union
from math import prod
from itertools import combinations
from fractions import Fraction

from utils.algorithms.cps_algorithms import *
from allopy.tonos.tonos import octave_reduce

class CPS:
  '''
  Calculate a Combination Product Set (CPS) scale from a list of prime factors and a rank value.
  
  Args:
    prime_factors: List of primes to generate the CPS.
    r: Rank value indicating the number of primes to combine.
    
  Returns:
    A tuple containing two lists:
    - The first list contains the products of combinations of prime factors.
    - The second list is the sorted CPS scale after octave reduction.
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7), r:int = 2, 
               equave:Union[Fraction, float] = 2, n_equaves:int = 1):
    self._equave = equave
    self._n_equaves = n_equaves

    self.__factors = tuple(sorted(factors))
    self.__r = r
    self.__combos, self.__products, self.__ratios = self._calculate()
    self.__graph = None

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
  def combos(self):
    return self.__combos

  @property
  def graph(self):
    if self.__graph is None:
      self.__graph = graph_cps(self.__combos)
    return self.__graph

  @property
  def equave(self):
    return self._equave
  
  @property
  def n_equaves(self):
    return self._n_equaves
  
  @equave.setter
  def equave(self, equave:Union[Fraction, float]):
    self._equave = equave
    self.__combos, self.__products, self.__ratios = self._calculate()
  
  @n_equaves.setter
  def n_equaves(self, n_equaves:int):
    self._n_equaves = n_equaves
    self.__combos, self.__products, self.__ratios = self._calculate()
  
  def _calculate(self):
    combos   = tuple(combinations(self.__factors, self.__r))
    products = tuple(prod(comb) for comb in combos)
    ratios   = tuple(sorted(octave_reduce(interval  = Fraction(product),
                                          equave    = self._equave,
                                          n_equaves = self._n_equaves) for product in products))
    return combos, products, ratios
  
  def __repr__(self):
    r_str = ', '.join(str(ratio) for ratio in self.__ratios)
    return (
      f'Rank:     {self.__r}\n'
      f'Factors:  {self.__factors}\n'
      f'Combos:   {self.__combos}\n'
      f'Products: {self.__products}\n'
      f'Ratios:   {r_str}\n'
    )
  
class _nany(CPS, ABC):
  '''
  Abstract Base Class for inheritance.
  '''
  def __new__(cls, *args, **kwargs):
        if cls is _nany:
            raise TypeError(f'{cls.__name__} class may not be instantiated.')
        return super().__new__(cls)
  
  def __init__(self, factors:tuple[int], r:int):
    super().__init__(factors, r)
    self.__dyads   = None
    self.__triads  = None
    self.__tetrads = None
  
  @property
  def dyads(self):
    if self.__dyads is None:
      dyad_combos = find_cliques(self.graph, 2)
      self.__dyads = tuple(
        combo_clique_to_ratios(clique    = dyad,
                               equave    = self._equave,
                               n_equaves = self._n_equaves) for dyad in dyad_combos
      )
    return self.__dyads
  
  @property
  def triads(self):
    if self.__triads is None:
      triad_combos = find_cliques(self.graph, 3)
      self.__triads = tuple(
        combo_clique_to_ratios(clique    = triad,
                               equave    = self._equave,
                               n_equaves = self._n_equaves) for triad in triad_combos
      )
    return self.__triads
  
  @property
  def tetrads(self):
    if self.__tetrads is None:
      tetrad_combos = find_cliques(self.graph, 4)
      self.__tetrads = tuple(
        combo_clique_to_ratios(clique    = tetrad,
                               equave    = self._equave,
                               n_equaves = self._n_equaves) for tetrad in tetrad_combos
      )
    return self.__tetrads
  
  def nads(self, n:int):
    if n < 2:
      raise ValueError('n must be greater than 1.')
    elif n == 2:
      return self.dyads
    elif n == 3:
      return self.triads
    elif n == 4:
      return self.tetrads
    else:
      nad_combos = find_cliques(self.graph, n)
      return tuple(
        combo_clique_to_ratios(clique    = nad,
                               equave    = self._equave,
                               n_equaves = self._n_equaves) for nad in nad_combos
      )

  def _reset_nads(self):
    self.__dyads   = None
    self.__triads  = None
    self.__tetrads = None
  
  @CPS.equave.setter
  def equave(self, equave:Union[Fraction, float]):
    super(_nany, _nany).equave.fset(self, equave)
    self._reset_nads()

  @CPS.n_equaves.setter
  def n_equaves(self, n_equaves:int):
    super(_nany, _nany).n_equaves.fset(self, n_equaves)
    self._reset_nads()


class Hexany(_nany):
  '''
  Calculate a Hexany scale from a list of prime factors and a rank value.
  
  The Hexany is a six-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Hexany
  
  Args:
    prime_factors: List of primes to generate the Hexany.
    
  Returns:
    A tuple containing two lists:
    - The first list contains the products of combinations of prime factors.
    - The second list is the sorted Hexany scale after octave reduction.
  '''  
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7)):
    # Hexany must be 4 factors with rank 2
    if len(factors) != 4:
      raise ValueError('Hexany must have exactly 4 factors.')
    super().__init__(factors, r=2)

class Eikosany(_nany):
  '''
  Calculate an Eikosany scale from a list of prime factors and a rank value.
  
  The Eikosany is a twenty-note scale in just intonation derived from combinations
  of prime factors, as conceptualized by Erv Wilson.
  
  see:  https://en.wikipedia.org/wiki/Eikosany
  
  Args:
    prime_factors: List of primes to generate the Eikosany.
    
  Returns:
    A tuple containing two lists:
    - The first list contains the products of combinations of prime factors.
    - The second list is the sorted Eikosany scale after octave reduction.
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
    self.__ratio_sets = self.__calculate()

  def _calculate(self):
    return tuple(
      tuple(Fraction(numerator,
                     denominator) for numerator in self.__factors)
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
