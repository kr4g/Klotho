# from typing import Tuple

# from ..rhythm_trees import *

# def ratios_to_tree(lst:Tuple[Fraction]) -> RhythmTree:
#     pgcd_denom = reduce(lcm, (abs(ratio.denominator) for ratio in lst))
#     S = tuple((r.numerator * (pgcd_denom // r.denominator)) for r in lst)
#     meas = f'{sum_proportions(S)}/{pgcd_denom}'
#     return RhythmTree(meas=meas, subdivisions=S)

# def flatten_tree(rt:RhythmTree) -> RhythmTree:
#     return ratios_to_tree(rt.ratios)
