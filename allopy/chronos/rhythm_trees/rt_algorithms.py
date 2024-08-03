from typing import Union, Tuple, List
from fractions import Fraction
from math import gcd, lcm, prod, floor, log
from functools import reduce
from itertools import count
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt




# ------------------------------------------------------------------------------------
# EXPERIMENTAL

def notate(tree):
    def _notate(tree, level=0):
        if level == 0:
            return f'\\time {tree.time_signature}\n' + _notate(tree, level + 1)
        
        # print(f'tree: {tree}, level: {level}')
        if level == 1:
            S = add_ties(tree.subdivisions)
            tup = tree.time_signature.numerator, (sum_proportions(tree.subdivisions),)
            n, m = get_group_subdivision(tup)
            if n == m: # no tuplet
                return _notate(S, level + 1)
            return f'\\tuplet {n}/{m} ' + '{' + _notate(S, level + 1) + '}'
        else:
            result = ""
            for element in tree:
                if isinstance(element, (int, float)):      # Rest or single note
                    if element < 0:     # Rest
                        result += f" r{abs(element)}"
                    else:       # Single note
                        result += f" {element}"
                elif isinstance(element, tuple):           # Subdivision                
                    D, S = element
                    tup = D, (sum_proportions(S),)
                    n, m = get_group_subdivision(tup)
                    if n == m:
                        result += f' {_notate(S, level + 1)}'
                    else:
                        result += f' \\tuplet {n}/{m} ' + '{' + _notate(S, level + 1) + '}'
                if level == 0:
                    result = result.strip() + ' '
            return result.strip()
    return _notate(tree)
# ------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------
# TIME BLOCK ALGORITHMS
# ----------------------
#
# ------------------------------------------------------------------------------------

def rhythm_pair(lst:Tuple, is_MM:bool=True) -> Tuple:
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)
