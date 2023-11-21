
from typing import Union, List, Tuple, Dict, Set
from math import prod
from itertools import combinations
from fractions import Fraction
from allopy.tonos.tonos import octave_reduce

def hexany(prime_factors: Tuple[int] = (1,3,5,7), r: int = 2) -> Tuple[List[float], List[float]]:
  '''
  Calculate a Hexany scale from a list of prime factors and a rank value.
  
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
  products = tuple([prod(comb) for comb in combinations(prime_factors, r)])
  scale = tuple(sorted([octave_reduce(Fraction(product)) for product in products]))
  return products, scale

def n_tet(divisions=12, equave=2, nth_division=1):
  '''
  Calculate the size of the nth division of an interval in equal temperament.
  
  see:  https://en.wikipedia.org/wiki/Equal_temperament

  :param interval: The interval to divide (default is 2 for an octave)
  :param divisions: The number of equal divisions
  :param nth_division: The nth division to calculate
  :return: The frequency ratio of the nth division
  '''
  return equave ** (nth_division / divisions)
