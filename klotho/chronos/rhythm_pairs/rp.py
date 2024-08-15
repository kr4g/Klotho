from typing import Tuple
from math import prod
import numpy as np

def rhythm_pair(lst:Tuple, is_MM:bool=True) -> Tuple:
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)
