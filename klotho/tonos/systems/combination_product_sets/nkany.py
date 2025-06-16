from .cps import CombinationProductSet

__all__ = [
    'Hexany',
    'Dekany',
    'Pentadekany',
    'Eikosany',
    'Hebdomekontany',
]

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
    super().__init__(factors, r=2, normalized=normalized, master_set="tetrad")

class Dekany(CombinationProductSet):
  '''
  A dekany is a 10-note scale built using all the possible combinations 
  of either 2 or 3 intervals (but not a mix of both) from a given set of 
  5 intervals. It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Dekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11), r:int = 2, normalized:bool = False, master_set:str = None):
    if len(factors) != 5:
      raise ValueError('Dekany must have exactly 5 factors.')
    if not r in (2, 3):
      raise ValueError('Dekany rank must be 2 or 3.')
    super().__init__(factors, r, normalized=normalized, master_set=master_set)
    
class Pentadekany(CombinationProductSet):
  '''
  A pentadekany is a 15-note scale built using all the possible combinations
  of either 2 or 4 intervals (but not a mix of both) from a given set of 6 
  intervals. Pentadekanies may be chiral, and the choice of whether to take 
  combinations of 2 or 4 elements is equivalent to choosing the chirality. 
  It is a particular case of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Pentadekany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 11, 13), r:int = 2, normalized:bool = False, master_set:str = None):
    if len(factors) != 6:
      raise ValueError('Pentadekany must have exactly 6 factors.')
    if not r in (2, 4):
      raise ValueError('Pentadekany rank must be 2 or 4.')
    super().__init__(factors, r, normalized=normalized, master_set=master_set)

class Eikosany(CombinationProductSet):
  '''
  An eikosany is a 20-note scale built using all the possible combinations 
  of 3 intervals from a given set of 6 intervals. It is a particular case 
  of a combination product set (CPS).
  
  see:  https://en.xen.wiki/w/Eikosany
  
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 9, 11), normalized:bool = False, master_set:str = "asterisk"):
    if len(factors) != 6:
      raise ValueError('Eikosany must have exactly 6 factors.')
    valid_master_sets = ("asterisk", "irregular_hexagon", "centered_pentagon")
    if master_set and master_set.lower() not in valid_master_sets:
      raise ValueError(f'Master set must be one of: {", ".join(valid_master_sets)}.')
    super().__init__(factors, r=3, normalized=normalized, master_set=master_set)

class Hebdomekontany(CombinationProductSet):
  '''
  A hebdomekontany is a 70-note scale built using all the possible combinations
  of 4 intervals from a given set of 8 intervals. It is a particular case 
  of a combination product set (CPS).
  
  see: https://en.xen.wiki/w/Hebdomekontany
  '''
  def __init__(self, factors:tuple[int] = (1, 3, 5, 7, 9, 11, 13, 17), normalized:bool = False):
    if len(factors) != 8:
      raise ValueError('Hebdomekontany must have exactly 8 factors.')
    super().__init__(factors, r=4, normalized=normalized, master_set='ogdoad') 