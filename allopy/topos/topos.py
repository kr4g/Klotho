# ------------------------------------------------------------------------------------
# MUSIC TOPOLOGY TOOLS
# ------------------------------------------------------------------------------------
'''
The `topos` base module.
'''
from utils.algorithms.tree_algorithms import permut_list

from sympy.utilities.iterables import cartes
import numpy as np
import regex
from math import prod
from fractions import Fraction

class config:
    TOPOS_WARNINGS = True
    TOPOS_SUGGESTIONS = True

def iso_pairs(l1: list, l2: list) -> tuple:
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
        l1 (list): The first list, consisting of Type 1.
        l2 (list): The second list, consisting of Type 2.
    
    Returns:
        list: A list of tuples where each element from l1 is paired with each 
        element from l2.

    Example:
    >>> iso_pairs(('⚛', '∿'), ('Ξ', '≈'))
    (('⚛', 'Ξ'), ('∿', '≈'), ('⚛', '≈'), ('∿', 'Ξ'))
    '''
    if config.TOPOS_WARNINGS and (Fraction(len(l1), len(l2)).denominator == 1 or Fraction(len(l2), len(l1)).denominator == 1):
        print('PAY HEED! THE TOPOS CAUTIONS YOU:\n\nThe lengths of the lists should not evenly divide.  ' + 
            'Otherwise, the cyclic pairing will be equivalent to a simple element-wise pairing.  If ' + 
            'this is your intention, The Topos bids you to proceed.  If this is not your intention, ' + 
            'The Topos suggests you pass lists of indivisible lengths.\n\n  The Topos has spoken.\n')
        if input('Do you wish to proceed? (y/n): ').lower() in ('y', 'yes'):
            pass
        elif config.TOPOS_SUGGESTIONS:
            print('\nThe Topos suggests you pass lists of indivisible lengths.\n\n')
            return
            
    return tuple((l1[i % len(l1)], l2[i % len(l2)]) for i in range(len(l1) * len(l2)))

def cartesian_iso_pairs(l1: list, l2: list) -> tuple:
    '''
    Generates a sequence of pairs by first creating a Cartesian product of list l1 with itself,
    and then cycling through these pairs while pairing them with elements from list l2.
    Each pair from the Cartesian product of l1 is combined with an element from l2, 
    cycling through l2 as necessary.

    Args:
        l1 (list): The first list, consisting of Type 1.
        l2 (list): The second list, consisting of Type 2.
    
    Returns:
        list: A list of tuples, each containing a pair from the Cartesian product of l1 and an element from l2.

    Example:
    >>> cartesian_iso_pairs(['Ψ', '⧭', 'Ω'], ('¤', '〄'))
    (('Ψ', 'Ψ'), '¤'), (('Ψ', '⧭'), '〄'), (('Ψ', 'Ω'), '¤'),
    (('⧭', 'Ψ'), '〄'), (('⧭', '⧭'), '¤'), (('⧭', 'Ω'), '〄'),
    (('Ω', 'Ψ'), '¤'), (('Ω', '⧭'), '〄'), (('Ω', 'Ω'), '¤')
    '''
    return iso_pairs(tuple(cartes(l1, l1)), l2)

def homotopic_map(l1: tuple, l2: tuple) -> tuple:
    '''
    Maps each element of tuple l1 to a unique "path" (sub-tuple) in tuple l2. 
    Each element from l1 is paired with a shifted version of l2, ensuring 
    that each pair is unique and resembles a distinct "path".
    Warns if l1 is longer than l2, as this would disrupt the creation of distinct paths.

    Args:
        l1 (tuple): The first tuple of elements.
        l2 (tuple): The second tuple of elements to form paths.

    Returns:
        tuple: A tuple of pairs, each pair consists of an element from l1 and a unique path in l2.

    Example:
    >>> homotopic_map(('Δ', 'Θ'), ('λ', 'μ', 'ν'))
    (('Δ', ('λ', 'μ', 'ν')), ('Θ', ('μ', 'ν', 'λ')))
    '''
    if config.TOPOS_WARNINGS:
        if len(l1) > len(l2):
            print('PAY HEED! THE TOPOS CAUTIONS YOU:\n\nThe first list is longer than the second. ' +
                  'This will result in non-unique paths for each element in the first list. If this is ' +
                  'your intention, The Topos bids you to proceed.  If this is not your intention, ' + 
                  'The Topos suggests you adjust their lengths accordingly. Know that passing lists of ' + 
                  'equal lengths will yeild the maximum combinatoric diversity. The Topos has spoken.')
            if input('Do you wish to proceed? (y/n) ').lower() not in ('y', 'yes'):
                return
        elif len(l1) < len(l2):
            print('PAY HEED! THE TOPOS CAUTIONS YOU:\n\nThe first list is shorter than the second. ' +
                  'This means that not all possible paths through the second list will be used. If this is ' +
                  'your intention, The Topos bids you to proceed.  If this is not your intention, ' + 
                  'The Topos suggests you adjust their lengths accordingly. Know that passing lists of ' +
                  'equal lengths will yeild the maximum combinatoric diversity. The Topos has spoken.')
            if input('Do you wish to proceed? (y/n) ').lower() not in ('y', 'yes'):
                return
    return tuple((l1[i], tuple(l2[i % len(l2):] + l2[:i % len(l2)])) for i in range(len(l1)))

# Algorithm 5b: AutoRef
def autoref(lst1:tuple, lst2:tuple = None):
    '''
    Algorithm 5: AutoRef

    Data: lst est une liste à n éléments finis
    Result: Liste doublement permuteé circulairement.

    begin
        n = 0;
        lgt = nombre d'éléments dans la liste;
        foreach elt in lst do
            while n ≠ (lgt + 1) do
                return [elt, (PermutList(lst, n))];
                n = n + 1;
            end while
        end foreach
    end
    
    :param lst: List of finite elements to be doubly circularly permuted.
    :return: List containing the original element and its permutations.
    '''
    if lst2 is None:
        lst2 = lst1
    return tuple((elt, permut_list(lst2, n + 1)) for n, elt in enumerate(lst1))

# AutoRef Matrices
def autoref_rotmat(lst1:tuple, lst2:tuple = None, mode:str='G'):
    '''
    '''
    if lst2 is None:
        lst2 = lst1
    result = []
    mode = mode.upper()
    if mode == 'G':
        for i in range(len(lst1)):
            l1 = permut_list(lst1, i)
            l2 = permut_list(lst2, i)
            result.append(autoref(l1, l2))
    elif mode == 'S':
        for i in range(len(lst1)):
            l = tuple((lst1[j], permut_list(lst2, i + j + 1)) for j in range(len(lst1)))
            result.append(l)
    elif mode == 'D':
        l2 = autoref(lst2)
        for i in range(len(lst1)):
            l = permut_list(lst1, i)
            result.append(tuple((elem, l2[j][1]) for j, elem in enumerate(l)))
    # elif mode == 'C':
    #     l1 = autoref(permut_list(lst1, 0))
    #     l2 = autoref(permut_list(lst1, 2))
    #     for i in range(len(lst1)):
    #         l = permut_list(lst1, i)
    #         lp = l1 if i % 2 == 0 else l2
    #         result.append(tuple((elem, lp[j][1]) for j, elem in enumerate(l)))
    else:
        return None
    return tuple(result)
