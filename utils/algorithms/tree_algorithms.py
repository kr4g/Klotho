
from typing import Union, Tuple
from fractions import Fraction
from math import gcd, lcm, prod
from functools import reduce
from itertools import count
import numpy as np
import networkx as nx

# ------------------------------------------------------------------------------------
# TREE ALGORITHMS
# ----------------------
# 
# All Pseudocode by Karim Haddad unless otherwise noted.
# 
# "Let us recall that the mentioned part corresponds to the S part of a rhythmic tree 
# composed of (DS), that is its part constituting the proportions which can also 
# encompass other tree structures."  —- Karim Haddad
# ------------------------------------------------------------------------------------

# Algorithm 1: MeasureRatios
def measure_ratios(subdivisions:tuple):
    '''
    Algorithm 1: MeasureRatios

    Data: S is the part of a RT
    Result: Transforms the part (s) of a rhythm tree into fractional proportions.

    div = for all s elements of S do
    if s is a list of the form (DS) then 
        return |D of s|;
    else
        return |s|;
    end if
    end for all
    begin
        for all s of S do
            if s is a list then
                return (|D of s| / div) * MeasureRatios(S of s);
            else
                |s|/div;
            end if
        end for all
    end
    '''
    div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivisions)
    result = []
    for s in subdivisions:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(abs(D), div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return tuple(result)

# Algorithm 2: ReducedDecomposition
def reduced_decomposition(lst, meas):
    '''
    Algorithm 2: ReducedDecomposition
    
    Data: frac is a list of proportions; meas is the Tempus
    Result: Reduction of the proportions of frac.
    
    begin
        for all f of frac do
            (f * [numerator of meas]) / [denominator of meas];
        end for all
    end
        
    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of reduced proportions.
    '''
    return tuple(Fraction(f.numerator * meas.numerator,
                          f.denominator * meas.denominator) for f in lst)

# Algorithm 3: StrictDecomposition
def strict_decomposition(lst, meas):
    '''
    Algorithm 3: StrictDecomposition
    
    Data: liste is a list of proportions resulting from MeasureRatios; meas is the Tempus
    Result: List of proportions with common denominators.
    
    num = numerator of meas;
    denom = denominator of meas;
    pgcd = gcd of the list;
    pgcd_denom = denominator of pgcd;
    
    begin
        foreach i of liste do
            [ ((i/pgcd) * num) , pgcd_denom ];
        end foreach
    end

    :param ratios: List of Fraction objects representing proportions.
    :param meas: A tuple representing the Tempus (numerator, denominator).
    :return: List of proportions with a common denominator.
    '''
    pgcd = reduce(gcd, (ratio.numerator for ratio in lst))
    pgcd_denom = reduce(lcm, (ratio.denominator for ratio in lst))
    return tuple(Fraction((f / pgcd) * meas.numerator, pgcd_denom) for f in lst)

# Algorithm 4: PermutList
def permut_list(lst:tuple, pt:int):
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

# Algorithm 5: AutoRef
def autoref(lst:tuple):
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
    return tuple((elt, permut_list(lst, n + 1)) for n, elt in enumerate(lst))

# AutoRef Matrices
def autoref_rotmat(lst:tuple, mode:str='G'):
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
    result = []
    mode = mode.upper()
    if mode == 'G':        
        for i in range(len(lst)):
            l = permut_list(lst, i)
            result.append(autoref(l))
    elif mode == 'S':
        for i in range(len(lst)):
            l = tuple((lst[j], permut_list(lst, i + j + 1)) for j in range(len(lst)))
            result.append(l)
    elif mode == 'D':
        l1 = autoref(lst)
        for i in range(len(lst)):
            l = permut_list(lst, i)
            result.append(tuple((elem, l1[j][1]) for j, elem in enumerate(l)))
    # elif mode == 'C':
    #     l1 = autoref(permut_list(lst, 0))
    #     l2 = autoref(permut_list(lst, 2))
    #     for i in range(len(lst)):
    #         l = permut_list(lst, i)
    #         lp = l1 if i % 2 == 0 else l2
    #         result.append(tuple((elem, lp[j][1]) for j, elem in enumerate(l)))
    else:
        result = lst
    return tuple(result)

def symbolic_unit(time_signature:Union[Fraction, str]):
    return Fraction(1, symbolic_approx(Fraction(time_signature).denominator))

def symbolic_duration(f:int, time_signature:Union[Fraction, str], S:tuple):
    # ds (f,m) = (f * numerator (D)) / (1/us (m) * sum of elements in S)
    time_signature = Fraction(time_signature)
    return Fraction(f * time_signature.numerator) / (1 / symbolic_unit(time_signature) * sum_proportions(S))

# Algorithm 6: SymbolicApprox
def symbolic_approx(n:int):
    '''
    Algorithm 6: SymbolicApprox

    Data: n is an integer (1 = whole note, 2 = half note, 4 = quarter note, ...)
    Result: Returns the note value corresponding to the denominator of a time signature or a given Tempus
    begin
        if n = 1 then
            return 1;
        else if n belongs to {4, 5, 6, 7} then
            return 4;
        else if n belongs to {8, 9, 10, 11, 12, 13, 14} then
            return 8;
        else if n belongs to {15, 16} then
            return 16;
        else
            pi = first power of 2 <= n;
            ps = first power of 2 >= n;
            if |n - pi| > |n - ps| then
                return ps;
            else
                return pi;
            end if
        end case
    end
    '''
    if n == 1:
        return 1
    elif n in {2, 3}: # absent in the original pseudocode
        return 2
    elif n in {4, 5, 6, 7}:
        return 4
    elif n in {8, 9, 10, 11, 12, 13, 14}:
        return 8
    elif n in {15, 16}:
        return 16
    else:
        pi = 2 ** (n.bit_length() - 1) # first power of 2 <= n
        ps = 2 ** n.bit_length()       # first power of 2 >= n
        return ps if abs(n - pi) > abs(n - ps) else pi

# Algorithm 10: GetGroupSubdivision
def get_group_subdivision(G:tuple):
    '''
    Algorithm 10: GetGroupSubdivision

    Data: G is a group in the form (D S)
    Result: Provides the value of the "irrational" composition of the prolationis of a complex Temporal Unit
    ds = symbolic duration of G;
    subdiv = sum of the elements of S;

    n = {
        if subdiv = 1 then
            return ds;
        else if ds/subdiv is an integer && (ds/subdiv is a power of 2 OR subdiv/ds is a power of 2) then
            return ds;
        else
            return subdiv;
        end if
    };

    m = {
        if n is binary then
            return SymbolicApprox(n);
        else if n is ternary then
            return SymbolicApprox(n) * 3/2;
        else
            num = numerator of n; if (num + 1) = ds then
                return ds;
            else if num = ds then return num;
            else if num < ds then return [n = num * 2, m = ds];
            else if num < ((ds * 2) / 1) then return ds;
            else
                pi = first power of 2 <= n; ps = first power of 2 > n;  if |n - pi| > |n - ps| then
                    return ps;
                else
                    return pi;
                end if
            end if
        end if
    }

    return [n, m];
    '''
    D, S = G
    ds = D
    subdiv = sum_proportions(S)
    
    if subdiv == 1:
        n = ds
    elif (ds / subdiv).is_integer() and ((ds // subdiv).bit_length() == 1 or (subdiv // ds).bit_length() == 1):
        n = ds
    else:
        n = subdiv
    
    if bin(n).count('1') == 1:     # n is binary
        m = symbolic_approx(n)
    elif n % 3 == 0 and (subdiv / ds).is_integer(): # n is ternary
    # elif (n * 3 / 2).is_integer(): # n is ternary
        m = int(symbolic_approx(n) * 3 / 2)
    else:
        num = n
        if num + 1 == ds:# or num == ds:
            m = ds
        elif num == ds:
            m = num
        elif num < ds:
            return [num * 2, ds]
        elif num < (ds * 2) - 1:
            m = ds
        else:            
            pi = 2 ** (n.bit_length() - 1) # first power of 2 <= n
            ps = 2 ** n.bit_length()       # first power of 2 > n
            m = ps if abs(n - pi) > abs(n - ps) else pi
    
    return [n, m]

def factor_tree(subdivs:tuple):
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor_tree(subdivs:tuple, factors:tuple):
    def _refactor(subdivs, index):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                nested_result, index = _refactor(element, index)
                result.append(nested_result)
            else:
                result.append(factors[index])
                index += 1
        return tuple(result), index
    return _refactor(subdivs, 0)[0]

def rotate_tree(subdivs:tuple, n=1):
    factors = factor_tree(subdivs)
    n = n % len(factors)
    factors = factors[n:] + factors[:n]
    return refactor_tree(subdivs, factors)

def sum_proportions(subdivisions:tuple):
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in subdivisions)

def measure_complexity(tree:tuple):
    '''
    Assumes a tree in the form (D S) where D represents a duration and S represents a list
    of subdivisions.  S can be also be in the form (D S).

    Recursively traverses the tree.  For any element, if the sum of S != D, return True.
    '''    
    for s in tree:
        if isinstance(s, tuple):
            D, S = s
            div = sum_proportions(S)
            # XXX - this only works for duple meters!!!!!
            if bin(div).count("1") != 1 and div != D:
                return True
            else:
                return measure_complexity(S)
    return False

def graph_tree(root, S):
    def add_nodes(graph, parent_id, children_list):        
        for child in children_list:
            if isinstance(child, int):
                child_id = next(unique_id)
                graph.add_node(child_id, label=child)
                graph.add_edge(parent_id, child_id)
            elif isinstance(child, tuple):
                duration, subdivisions = child
                duration_id = next(unique_id)
                graph.add_node(duration_id, label=duration)
                graph.add_edge(parent_id, duration_id)
                add_nodes(graph, duration_id, subdivisions)
    unique_id = count()
    G = nx.DiGraph()
    root_id = next(unique_id)
    G.add_node(root_id, label=root)
    add_nodes(G, root_id, S)
    return G

def graph_depth(G):
    return max(nx.single_source_shortest_path_length(G, 0).values())

# EXPERIMENTAL
def notate(tree, level=0):
    # from utils.algorithms.algorithms import symbolic_approx, get_group_subdivision
    if level == 0:
        return f'\\time {tree.time_signature}\n' + notate(tree, level + 1)
    
    # print(f'tree: {tree}, level: {level}')
    if level == 1:
        tup = tree.time_signature.numerator, (sum_proportions(tree.subdivisions),)
        n, m = get_group_subdivision(tup)
        return f'\\tuplet {n}/{m} ' + '{{' + notate(tree.subdivisions, level + 1) + '}}'
    else:
        result = ""
        for element in tree:
            if isinstance(element, int):      # Rest or single note
                if element < 0:  # Rest
                    result += f" -{abs(element)}"
                else:  # Single note
                    result += f" {element}"
            elif isinstance(element, tuple):  # Subdivision                
                D, S = element
                # print(f'D: {D}, S: {S}')
                tup = D, (sum_proportions(S),)
                n, m = get_group_subdivision(tup)
                result += f' \\tuplet {n}/{m} {{{notate(S, level + 1)}}}'
            if level == 0:
                result = result.strip() + ' '
        return result.strip()
# ------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------
# TIME BLOCK ALGORITHMS
# ----------------------
#
# 
# ------------------------------------------------------------------------------------

def rhythm_pair(lst, is_MM=True):
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)
