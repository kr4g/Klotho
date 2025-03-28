# ------------------------------------------------------------------------------------
# Klotho/klotho/topos/topos.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
General functions for generating and transforming sequences in a topological manner.
--------------------------------------------------------------------------------------
'''
from math import prod

__all__ = [
    'permut_list',
    'autoref',
    'autoref_rotmat',
    'iso_pairs',
    'pair_adjacent',
    'nested_chain',
    'alternate_sequence',
]

# Algorithm 4: PermutList
def permut_list(lst:tuple, pt:int, preserve_signs:bool=False) -> tuple:
    '''
    Algorithm 4: PermutList with optional sign preservation
    
    :param lst: List of elements to be permuted.
    :param pt: Starting position for the permutation.
    :param preserve_signs: If True, preserves signs while rotating absolute values.
    :return: Circularly permuted list.
    '''
    if not preserve_signs:
        pt = pt % len(lst)
        return lst[pt:] + lst[:pt]
    
    signs = tuple(1 if x >= 0 else -1 for x in lst)
    abs_values = tuple(abs(x) for x in lst)
    
    pt = pt % len(abs_values)
    rotated = abs_values[pt:] + abs_values[:pt]
    
    return tuple(val * sign for val, sign in zip(rotated, signs))

# Algorithm 5: AutoRef
def autoref(*args, preserve_signs:bool=False):    
    '''
    Algorithm 5: AutoRef with optional sign preservation
    
    :param args: One or two lists to be doubly circularly permuted.
    :param preserve_signs: If True, preserves signs while rotating absolute values.
    :return: List containing the original element and its permutations.
    '''
    if len(args) == 1:
        lst1 = lst2 = tuple(args[0])
    elif len(args) == 2:
        lst1, lst2 = map(tuple, args)
    else:
        raise ValueError('Function expects either one or two iterable arguments.')

    if len(lst1) != len(lst2):
        raise ValueError('The tuples must be of equal length.')

    return tuple((elt, permut_list(lst2, n + 1, preserve_signs)) 
                 for n, elt in enumerate(lst1))

# AutoRef Matrices
def autoref_rotmat(*args, mode='G', preserve_signs:bool=False):
    '''
    AutoRef rotation matrices with optional sign preservation
    
    :param args: One or two lists to generate rotation matrices from.
    :param mode: Rotation mode ('G', 'S', 'D', or 'C').
    :param preserve_signs: If True, preserves signs while rotating absolute values.
    :return: Tuple of rotation matrices based on the specified mode.
    '''
    if len(args) == 1:
        lst1 = lst2 = tuple(args[0])
    elif len(args) == 2:
        lst1, lst2 = map(tuple, args)
    else:
        raise ValueError('Function expects either one or two iterable arguments.')

    if len(lst1) != len(lst2):
        raise ValueError('The tuples must be of equal length.')

    match mode.upper():
        case 'G':
            return tuple(autoref(permut_list(lst1, i, preserve_signs), 
                               permut_list(lst2, i, preserve_signs), 
                               preserve_signs=preserve_signs) 
                        for i in range(len(lst1)))
        case 'S':
            return tuple(tuple((lst1[j], permut_list(lst2, i + j + 1, preserve_signs)) 
                             for j in range(len(lst1))) 
                        for i in range(len(lst1)))
        case 'D':
            return tuple(tuple((elem, autoref(lst2, preserve_signs=preserve_signs)[j][1]) 
                             for j, elem in enumerate(permut_list(lst1, i, preserve_signs))) 
                        for i in range(len(lst1)))
        case 'C':
            return None
        case _:
            raise ValueError('Invalid mode. Choose from G, S, D, or C.')

# ------------------------------------------------------------------------------------

def iso_pairs(*lists):
    '''
    Generates tuples of elements from any number of input lists in a cyclic manner.

    Creates a list of tuples where each tuple contains one element from each input list.
    The pairing continues cyclically until the length of the generated list equals
    the product of the lengths of all input lists. When the end of any list is reached, 
    the iteration continues from the beginning of that list, effectively cycling through 
    the shorter lists until all combinations are created.

    This is a form of "cyclic pairing" or "modulo-based pairing" and is 
    different from computing the Cartesian product.

    Args:
        *lists: Any number of input lists.

    Returns:
        tuple: A tuple of tuples where each inner tuple contains one element 
        from each input list.

    Raises:
        ValueError: If no lists are provided.

    Example:
        >> iso_pairs([1, 2], ['a', 'b', 'c'])
        ((1, 'a'), (2, 'b'), (1, 'c'), (2, 'a'), (1, 'b'), (2, 'c'))

    '''
    if not lists:
        raise ValueError("At least one list must be provided")

    total_length = prod(len(lst) for lst in lists)

    return tuple(tuple(lst[i % len(lst)] for lst in lists) for i in range(total_length))

# ------------------------------------------------------------------------------------

def pair_adjacent(elements):
    '''
    Creates groups where elements are paired with their adjacent elements.
    
    Args:
        elements: A tuple of elements to be grouped.
        
    Returns:
        A tuple of valid groups.
        
    Example:
        >> pair_adjacent((1, 2, 3, 4, 5))
        ((1, (2, 3)), (2, (3, 4)), (3, (4, 5)), (4, (5, 1)), (5, (1, 2)))
    '''
    if not elements:
        return ()
    
    n = len(elements)
    if n == 1:
        return ((elements[0], ()),)
    
    if n == 2:
        return ((elements[0], (elements[1],)), (elements[1], (elements[0],)))
    
    result = []
    for i in range(n):
        next_idx = (i + 1) % n
        next_next_idx = (i + 2) % n
        result.append((elements[i], (elements[next_idx], elements[next_next_idx])))
    
    return tuple(result)

def nested_chain(elements):
    '''
    Creates a nested chain structure with elements.
    
    Args:
        elements: A tuple of elements to chain.
        
    Returns:
        A valid group with a nested chain structure.
        
    Example:
        >> nested_chain((1, 2, 3, 4, 5))
        (1, (2, 3, 4, 5))
    '''
    if not elements:
        return None
    
    if len(elements) == 1:
        return (elements[0], ())
    
    if len(elements) == 2:
        return (elements[0], (elements[1],))
    
    return (elements[0], elements[1:])

def alternate_sequence(elements):
    '''
    Creates a sequence where elements alternate between being part of the head and tail.
    
    Args:
        elements: A tuple of elements to alternate.
        
    Returns:
        A valid group with alternating elements.
        
    Example:
        >> alternate_sequence((1, 2, 3, 4, 5))
        (1, (3, 5, 2, 4))
    '''
    if not elements:
        return None
    
    if len(elements) == 1:
        return (elements[0], ())
    
    if len(elements) == 2:
        return (elements[0], (elements[1],))
    
    odds = elements[1::2]
    evens = elements[2::2]
    
    return (elements[0], odds + evens)
