from typing import Tuple

from allopy.topos.graphs.graph_algorithms import rotate_tree as _rotate_tree
from ..rhythm_tree import RhythmTree, Fraction
from .subdivisions import sum_proportions, reduce, lcm

def ratios_to_tree(lst:Tuple[Fraction]) -> RhythmTree:
    pgcd_denom = reduce(lcm, (abs(ratio.denominator) for ratio in lst))
    S = tuple((r.numerator * (pgcd_denom // r.denominator)) for r in lst)
    meas = f'{sum_proportions(S)}/{pgcd_denom}'
    return RhythmTree(meas=meas, subdivisions=S)

def flatten_tree(rt:RhythmTree) -> RhythmTree:
    return ratios_to_tree(rt.ratios)

def rotate_tree(rt:RhythmTree, n:int=1) -> RhythmTree:
    return RhythmTree.from_tree(_rotate_tree(rt.tree, n),
                                duration=rt.duration,
                                decomp=rt.decomp)
