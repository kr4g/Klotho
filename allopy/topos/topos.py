# ------------------------------------------------------------------------------------
# MUSIC TOPOLOGY TOOLS
# ------------------------------------------------------------------------------------
'''
The `topos` base module.
'''
from math import prod

class config:
    TOPOS_WARNINGS = True
    TOPOS_SUGGESTIONS = True

# Algorithm 4: PermutList
def permut_list(lst:tuple, pt:int) -> tuple:
    '''
    Algorithm 4: PermutList
    
    Data: lst is a list with n finite elements; pt is the position of the element where circular permutation of list lst begins
    Result: List circularly permuted starting from position pt
    
    begin
        n = 0;
        while n ≠ (pt + 1) do
            lst = ([car of lst] [cdr of lst]);
            n = n + 1;
        end while
        return lst;
    end
    
    /* car = returns the first element of lst  */
    /* cdr = returns lst without its first element  */
    
    :param lst: List of elements to be permuted.
    :param pt: Starting position for the permutation.
    :return: Circularly permuted list.
    '''
    pt = pt % len(lst)
    return lst[pt:] + lst[:pt]

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

# Algorithm 5: AutoRef
def autoref(*args):    
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
    if len(args) == 1:
        lst1 = lst2 = tuple(args[0])
    elif len(args) == 2:
        lst1, lst2 = map(tuple, args)
    else:
        raise ValueError('Function expects either one or two iterable arguments.')

    if len(lst1) != len(lst2):
        raise ValueError('The tuples must be of equal length.')

    return tuple((elt, permut_list(lst2, n + 1)) for n, elt in enumerate(lst1))

# AutoRef Matrices
def autoref_rotmat(*args, mode='G'):
    '''
    Matrices for lst = (3,4,5,7):

    Mode G (Group Rotation):

    ((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)))
    ((4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)), (3, (4, 5, 7, 3)))
    ((5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)), (3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)))
    ((7, (3, 4, 5, 7)), (3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)))

    Mode S:

    ((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)))
    ((3, (5, 7, 3, 4)), (4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3)))
    ((3, (7, 3, 4, 5)), (4, (3, 4, 5, 7)), (5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)))
    ((3, (3, 4, 5, 7)), (4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)), (7, (7, 3, 4, 5)))

    Mode D:

    ((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)))
    ((4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)), (7, (7, 3, 4, 5)), (3, (3, 4, 5, 7)))
    ((5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)), (3, (7, 3, 4, 5)), (4, (3, 4, 5, 7)))
    ((7, (4, 5, 7, 3)), (3, (5, 7, 3, 4)), (4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)))

    Mode C (Circular Rotation):

    ((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)))
    ((4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3)), (3, (5, 7, 3, 4)))
    ((5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)), (3, (7, 3, 4, 5)), (4, (3, 4, 5, 7)))
    ((7, (7, 3, 4, 5)), (3, (3, 4, 5, 7)), (4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)))
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
            return tuple(autoref(permut_list(lst1, i), permut_list(lst2, i)) for i in range(len(lst1)))
        case 'S':
            return tuple(tuple((lst1[j], permut_list(lst2, i + j + 1)) for j in range(len(lst1))) for i in range(len(lst1)))
        case 'D':
            return tuple(tuple((elem, autoref(lst2)[j][1]) for j, elem in enumerate(permut_list(lst1, i))) for i in range(len(lst1)))
        case 'C':
            return None
        case _:
            raise ValueError('Invalid mode. Choose from G, S, D, or C.')
