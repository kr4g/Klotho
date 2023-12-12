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

if __name__ == '__main__':  
    # ------------------------------------------------------------------------------------
    # Rhythm Pair Examples
    # ------------------------------------------------------------------------------------
    # 
    print(f'\nRhythm Pair Examples\n')
    prolationis = (3, 5, 7)
    r_pair_MM = rhythm_pair(prolationis, True)
    print(f'Prolationis: {prolationis}\nPartitions:  {r_pair_MM}\n')

    print(f'\nRhythm Pair as the subdivision of a Rhythm Tree\n')
    import rhythm_trees as rt
    r_tree = rt.RT(('?', ((1, 1), r_pair_MM)))
    print(f'{r_tree}\n')