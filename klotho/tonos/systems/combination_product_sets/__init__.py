from .combination_product_sets import CombinationProductSet
from .master_set import MasterSet, MASTER_SETS
from .algorithms import match_pattern, sub_cps, classify, faces

Hexany = CombinationProductSet.hexany
Dekany = CombinationProductSet.dekany
Pentadekany = CombinationProductSet.pentadekany
Eikosany = CombinationProductSet.eikosany
Hebdomekontany = CombinationProductSet.hebdomekontany

__all__ = [
    'CombinationProductSet',
    'Hexany',
    'Dekany',
    'Pentadekany',
    'Eikosany',
    'Hebdomekontany',
    'MasterSet',
    'MASTER_SETS',
    'match_pattern',
    'sub_cps',
    'classify',
    'faces',
]
