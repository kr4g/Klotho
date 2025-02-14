# ------------------------------------------------------------------------------------
# Klotho/klotho/topos/topos.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
General functions for generating and transforming sequences in a topological manner.
--------------------------------------------------------------------------------------
'''
from math import prod

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

def planar_spiral(*args):
    '''
    Algorithm: Planar Spiral Transform
    
    Data: args is one or more tuples
    Result: 2D tuple representing a spiral pattern of the input sequence
    
    begin
        seq = flatten args into a single tuple
        size = square root of length of seq
        result = 2D tuple of size x size, initialized with None
        directions = ((0, 1), (1, 0), (0, -1), (-1, 0))
        d = 0
        r, c = 0, 0
        for each item in seq do
            result[r][c] = item
            r_next, c_next = r + directions[d][0], c + directions[d][1]
            if r_next and c_next are within bounds and result[r_next][c_next] is None then
                r, c = r_next, c_next
            else
                d = (d + 1) mod 4
                r, c = r + directions[d][0], c + directions[d][1]
        end for
        return result
    end
    
    :param args: One or more tuples to be transformed into a spiral pattern.
    :return: 2D tuple representing the spiral pattern.

    Example:
    >>> planar_spiral((1, 2, 3), (4, 5, 6), (7, 8, 9))
    ((1, 2, 3), (8, 9, 4), (7, 6, 5))
    '''
    seq = sum(args, ())  # Flatten input tuples into a single tuple
    size = int(len(seq) ** 0.5)
    result = tuple(tuple(None for _ in range(size)) for _ in range(size))
    
    directions = ((0, 1), (1, 0), (0, -1), (-1, 0))
    d = 0
    r, c = 0, 0
    
    def fill_spiral(seq, result, r, c, d):
        if not seq:
            return result
        new_result = tuple(
            row[:c] + (seq[0],) + row[c+1:]
            if i == r else row
            for i, row in enumerate(result)
        )
        r_next, c_next = r + directions[d][0], c + directions[d][1]
        if 0 <= r_next < size and 0 <= c_next < size and result[r_next][c_next] is None:
            return fill_spiral(seq[1:], new_result, r_next, c_next, d)
        else:
            d = (d + 1) % 4
            r, c = r + directions[d][0], c + directions[d][1]
            return fill_spiral(seq[1:], new_result, r, c, d)
    
    return fill_spiral(seq, result, r, c, d)

def fract_seq(*args, depth=3):
    '''
    Algorithm: Self-Similar Sequence Generation
    
    Data: args is one or more tuples, depth is the recursion depth
    Result: Self-similar tuple based on the input
    
    begin
        seq = flatten args into a single tuple
        function expand(s, d)
            if d == 0 then
                return s
            else
                return concatenate(expand((x,) * length(s), d-1) for x in s)
            end if
        end function
        
        return expand(seq, depth)
    end
    
    :param args: One or more tuples to generate the self-similar sequence from.
    :param depth: Recursion depth for the self-similar pattern.
    :return: Self-similar tuple based on the input.

    Example:
    >>> fract_seq((1, 2, 3), depth=2)
    (1, 2, 3, 1, 1, 2, 3, 2, 1, 2, 3, 3)
    '''
    seq = sum(args, ())
    
    def expand(s, d):
        if d == 0:
            return s
        return sum((expand((x,) * len(s), d-1) for x in s), ())
    
    return expand(seq, depth)

def symmetry_fold(*args, fold_points=2):
    '''
    Algorithm: Symmetry Fold
    
    Data: args is one or more tuples, fold_points is the number of folds
    Result: Tuple folded onto itself to create symmetry
    
    begin
        seq = flatten args into a single tuple
        result = seq
        for i = 1 to fold_points do
            result = result + reverse(result)
        end for
        return result
    end
    
    :param args: One or more tuples to be folded for symmetry.
    :param fold_points: Number of times to fold the sequence.
    :return: Symmetrically folded tuple.

    Example:
    >>> symmetry_fold((1, 2), (3, 4), fold_points=2)
    (1, 2, 3, 4, 4, 3, 2, 1, 1, 2, 3, 4, 4, 3, 2, 1)
    '''
    seq = sum(args, ())
    
    result = seq
    for _ in range(fold_points):
        result = result + result[::-1]
    
    return result

def hyper_fold(*args):
    '''
    Algorithm: Hypercube Fold
    
    Data: args is one or more tuples with a total of exactly 8 elements
    Result: Tuple arranged in a 4D hypercube-like structure
    
    begin
        seq = flatten args into a single tuple
        if length of seq ≠ 8 then
            raise error "Total number of elements must be exactly 8"
        end if
        return (seq[0], seq[7], seq[3], seq[4], seq[1], seq[6], seq[2], seq[5],
                seq[7], seq[0], seq[4], seq[3], seq[6], seq[1], seq[5], seq[2])
    end
    
    :param args: One or more tuples with a total of exactly 8 elements to be folded into a hypercube-like structure.
    :return: Tuple representing the hypercube fold.

    Example:
    >>> hyper_fold((1, 2, 3, 4), (5, 6, 7, 8))
    (1, 8, 4, 5, 2, 7, 3, 6, 8, 1, 5, 4, 7, 2, 6, 3)
    '''
    seq = sum(args, ())
    
    if len(seq) != 8:
        raise ValueError("Total number of elements must be exactly 8 for a hypercube fold")
    
    return (seq[0], seq[7], seq[3], seq[4], seq[1], seq[6], seq[2], seq[5],
            seq[7], seq[0], seq[4], seq[3], seq[6], seq[1], seq[5], seq[2])

def klein_mapping(*args):
    '''
    Algorithm: Non-Orientable Surface Mapping
    
    Data: args is one or more tuples
    Result: Tuple of tuples representing a non-orientable surface-like structure
    
    begin
        seq = flatten args into a single tuple
        mid = length of seq / 2
        return (
            seq[0:mid],
            reverse(seq[mid:]),
            reverse(seq[0:mid]),
            seq[mid:]
        )
    end
    
    :param args: One or more tuples to be mapped onto a non-orientable surface-like structure.
    :return: Tuple of tuples representing the mapping.

    Example:
    >>> klein_mapping((1, 2, 3, 4), (5, 6, 7, 8))
    ((1, 2, 3, 4), (8, 7, 6, 5), (4, 3, 2, 1), (5, 6, 7, 8))
    '''
    seq = sum(args, ())
    
    mid = len(seq) // 2
    return (
        seq[:mid],
        seq[mid:][::-1],
        seq[:mid][::-1],
        seq[mid:]
    )

def mobius_ladder(*args):
    '''
    Algorithm: Twisted Ladder Structure
    
    Data: args is one or more tuples
    Result: Tuple of tuples arranged in a twisted ladder structure
    
    begin
        seq = flatten args into a single tuple
        n = length of seq
        return (
            (seq[i], seq[(n-i-1) mod n]) for i from 0 to n-1
        )
    end
    
    :param args: One or more tuples to be arranged in a twisted ladder structure.
    :return: Tuple of tuples representing the twisted ladder.

    Example:
    >>> mobius_ladder((1, 2, 3), (4, 5, 6))
    ((1, 6), (2, 5), (3, 4), (4, 3), (5, 2), (6, 1))
    '''
    seq = sum(args, ())
    
    n = len(seq)
    return tuple((seq[i], seq[(n-i-1) % n]) for i in range(n))

def mobius_strip(*args):
    '''
    Algorithm: Non-Orientable Strip Transform
    
    Data: args is one or more tuples
    Result: Tuple of tuples representing a non-orientable strip-like pattern
    
    begin
        seq = flatten args into a single tuple
        mid = length of seq / 2
        return (
            seq[0:mid],
            reverse(seq[mid:]),
            seq[0:mid]
        )
    end
    
    :param args: One or more tuples to be transformed into a non-orientable strip-like pattern.
    :return: Tuple of tuples representing the transformed sequence.

    Example:
    >>> mobius_strip((1, 2, 3), (4, 5, 6))
    ((1, 2, 3), (6, 5, 4), (1, 2, 3))
    '''
    seq = sum(args, ())
    
    mid = len(seq) // 2
    return (
        seq[:mid],
        seq[mid:][::-1],
        seq[:mid]
    )
