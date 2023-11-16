import numpy as np
from math import prod

def rhythm_pair(lst, is_MM=False):
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)
