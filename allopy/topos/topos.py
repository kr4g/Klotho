# ------------------------------------------------------------------------------------
# MUSIC TOPOLOGY TOOLS
# ------------------------------------------------------------------------------------
'''
The `topos` base module.
'''
from allopy.chronos import chronos
from allopy.aikous import aikous

from sympy.utilities.iterables import cartes
import numpy as np
from math import prod

def iso_pairs(l1: list, l2: list) -> list:
    '''
    Generates pairs of elements from two lists, l1 and l2, in a cyclic manner. 

    Creates a list of tuples where each element from l1 is paired with each 
    element from l2. The pairing continues cyclically until the length
    of the generated list equals the product of the lengths of l1 and l2. 
    Specifically, when the end of either list is reached, the iteration 
    continues from the beginning of that list, effectively cycling through 
    the shorter list until all pairings are created.
    
    This is a form of "cyclic pairing" or "modulo-based pairing" and is 
    different from computing the Cartesian product.

    Args:
        l1 (list): The first list.
        l2 (list): The second list.
    
    Returns:
        list: A list of tuples where each element from l1 is paired with each 
        element from l2.

    Example:
    >>> iso_pairs([1, 2], ['A', 'B', 'C'])
    [(1, 'A'), (2, 'B'), (1, 'C'), (2, 'A'), (1, 'B'), (2, 'C')]
    '''
    return [(l1[i % len(l1)], l2[i % len(l2)]) for i in range(len(l1) * len(l2))]

def cyclic_cartesian_pairs(l1: list, l2: list) -> list:
    '''
    Generates a sequence of pairs by first creating a Cartesian product of list l1 with itself,
    and then cycling through these pairs while pairing them with elements from list l2.
    Each pair from the Cartesian product of l1 is combined with an element from l2, 
    cycling through l2 as necessary.

    Args:
        l1 (list): The first list.
        l2 (list): The second list.
    
    Returns:
        list: A list of tuples, each containing a pair from the Cartesian product of l1 and an element from l2.

    Example:
    >>> cyclic_cartesian_pairs(['A', 'B'], [1, 2, 3])
    [('A', 'A', 1), ('B', 'A', 2), ('A', 'A', 3), ('B', 'B', 1), ('A', 'B', 2), ('B', 'B', 3)]
    '''
    return iso_pairs(list(cartes(l1, l1)), l2)

def poly_sequence_differential_superimposition(lst, is_MM=False):
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)
    