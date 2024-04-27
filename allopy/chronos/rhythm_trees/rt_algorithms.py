from typing import Union, Tuple, List
from fractions import Fraction
from math import gcd, lcm, prod, floor, log
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
def measure_ratios(S:tuple[int]) -> Tuple[Fraction]:
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
    div = sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in S)
    result = []
    for s in S:  
        if isinstance(s, tuple):
            D, S = s
            ratio = Fraction(abs(D), div)
            result.extend([ratio * el for el in measure_ratios(S)])
        else:
            result.append(Fraction(s, div))
    return tuple(result)

# Algorithm 2: ReducedDecomposition
def reduced_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
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
def strict_decomposition(lst:Tuple[Fraction], meas:Fraction) -> Tuple[Fraction]:
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
    # print(f'pgcd: {pgcd}, pgcd_denom: {pgcd_denom}')
    return tuple(Fraction((f / pgcd) * meas.numerator, pgcd_denom) for f in lst)

# ------------------------------------------------------------------------------------

# Algorithm 4: PermutList
def permut_list(lst:tuple, pt:int) -> Tuple:
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
def autoref(lst:tuple) -> Tuple[Tuple]:
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
def autoref_rotmat(lst:tuple, mode:str='G') -> Tuple[Tuple[Tuple]]:
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

# ------------------------------------------------------------------------------------
# NOTATION

def add_tie(n) -> Union[int, Tuple[int]]:
    p = 1
    while p * 2 <= n:
        p *= 2    
    if p == n or p * 1.5 == n or p * 1.75 == n:
        return n
    elif n > p * 1.5:
        return (p + p//2, add_tie(n - (p * 1.5)))
    else:
        return (p, float(add_tie(n - p)))
    
def add_ties(S:Tuple) -> Tuple:
    S = remove_ties(S)
    def process_tuple(t):
        result = []
        for value in t:
            if isinstance(value, tuple):
                processed_tuple = process_tuple(value)
                result.append(processed_tuple)
            elif isinstance(value, int):
                v = add_tie(value)
                result.extend(v if isinstance(v, tuple) else (v,))
        return tuple(result)
    return process_tuple(S)

def remove_ties(S:Tuple) -> Tuple:
    def process_tuple(t):
        result = []
        previous = 0
        for value in t:
            if isinstance(value, tuple):
                processed_tuple = process_tuple(value)
                if previous != 0:
                    result.append(previous)
                    previous = 0
                result.append(processed_tuple)
            elif isinstance(value, int):
                if previous != 0:
                    result.append(previous)
                previous = abs(value)
            elif isinstance(value, float):
                previous += int(abs(value))
        if previous != 0:
            result.append(previous)
        return tuple(result)        
    return process_tuple(S)

def symbolic_unit(time_signature:Union[Fraction, str]) -> Fraction:
    return Fraction(1, symbolic_approx(Fraction(time_signature).denominator))

def symbolic_duration(f:int, time_signature:Union[Fraction, str], S:tuple) -> Fraction:
    # ds (f,m) = (f * numerator (D)) / (1/us (m) * sum of elements in S)
    time_signature = Fraction(time_signature)
    return Fraction(f * time_signature.numerator) / (1 / symbolic_unit(time_signature) * sum_proportions(S))

def get_denom(n:int, n_type:str = 'bin') -> int:
    if n_type == 'bin':
        return symbolic_approx(n)
    elif n_type == 'tern':
        if n == 1:
            return 1
        elif n in {2, 3, 4}:
            return 3
        elif n in {5, 6, 7, 8, 9}:
            return 6
        elif n in {10, 11, 12, 13, 14, 15, 16, 17}:
            return 12
        # else:
        #     pi, ps = pow_n_bounds(n, 3)
        #     return ps if abs(n - pi) > abs(n - ps) else pi

def pow_n_bounds(n:int, pow:int=2) -> Tuple[int]:
    if n < 1:
        return (None, pow)
    k = floor(log(n, pow))
    pi = pow ** k
    ps = pow ** (k + 1)
    return pi, ps

def head_dots_beams(n:Fraction) -> List:
    num, denom = n.numerator, n.denominator
    p, _ = pow_n_bounds(num, 2)
    if p == num:
        return [
            get_note_head(n),
            0,
            get_note_beams(n)
        ]
    elif p * 1.5 == num:
        return [
            get_note_head(Fraction(p, denom)),
            1,
            get_note_beams(Fraction(p, denom))
        ]
    elif p * 1.75 == num:
        return [
            get_note_head(Fraction(p, denom)),
            2,
            get_note_beams(Fraction(p, denom))
        ]

def get_note_head(r:Fraction):
    if r > 2:
        return 'square'
    elif r == 1:
        return 'whole'
    elif r == 1/2:
        return 'half'
    else:
        return 'quarter'

def get_note_beams(r:Fraction):
    if r > 2 or r == 1/4 or r == 1/2 or r == 1:
        return 0
    else:
        return log(r.denominator, 2) - 2

def is_binary(durtot:Fraction) -> bool:
    durtot = Fraction(durtot)
    if durtot.numerator != 1:
        return False    
    denom = durtot.denominator
    exp = 0
    while (1 << exp) < denom:  # (1 << exp) == (2 ** exp)
        exp += 1
    return (1 << exp) == denom

def is_ternary(durtot:Fraction) -> bool:
    durtot = Fraction(durtot)
    if durtot.numerator == 3 and is_binary(Fraction(1, durtot.denominator)):
        return True
    return False

# Algorithm 6: SymbolicApprox
def symbolic_approx(n:int) -> int:
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
        pi, ps = pow_n_bounds(n, 2)
        return ps if abs(n - pi) > abs(n - ps) else pi

# Algorithm 10: GetGroupSubdivision
def get_group_subdivision(G:tuple) -> List[int]:
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
            else if num < ((ds * 2) - 1) then return ds;
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
    
    ratio = Fraction(ds, subdiv)
    if is_binary(ratio):
        m = symbolic_approx(n)
    elif is_ternary(ratio):
        m = int(symbolic_approx(n) * 3 / 2)
    else:
        num = n.numerator if isinstance(n, Fraction) else n
        if num + 1 == ds:
            m = ds
        elif num == ds:
            m = num
        elif num < ds:
            return [num * 2, ds]
        elif num < (ds * 2) - 1:
            m = ds
        else:
            # print(f'num: {num}, ds: {ds}')
            pi, ps = pow_n_bounds(n, 2)
            # print(f'pi: {pi}, ps: {ps}')
            m = ps if abs(n - pi) > abs(n - ps) else pi
    return [n, m]

# ------------------------------------------------------------------------------------

def factor_tree(subdivs:tuple) -> tuple:
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor_tree(subdivs:tuple, factors:tuple[int]) -> tuple:
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

def rotate_tree(subdivs:tuple, n:int=1) -> tuple:
    factors = factor_tree(subdivs)
    n = n % len(factors)
    factors = factors[n:] + factors[:n]
    return refactor_tree(subdivs, factors)

def sum_proportions(S:tuple) -> int:
    return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in S)

def measure_complexity(tree:tuple) -> bool:
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

def graph_tree(root, S:Tuple) -> nx.DiGraph:
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

def graph_depth(G:nx.DiGraph) -> int:
    return max(nx.single_source_shortest_path_length(G, 0).values())

def prune_tree(tree, depth):
    if depth == 0:
        return 0 # ignore for now
    if depth == 1:
        return tuple(el if isinstance(el, int) else el[0] for el in tree)
    else:
        pass

# EXPERIMENTAL
def notate(tree):
    def _notate(tree, level=0):
        if level == 0:
            return f'\\time {tree.time_signature}\n' + _notate(tree, level + 1)
        
        # print(f'tree: {tree}, level: {level}')
        if level == 1:
            tup = tree.time_signature.numerator, (sum_proportions(tree.subdivisions),)
            n, m = get_group_subdivision(tup)
            return f'\\tuplet {n}/{m} ' + '{{' + _notate(tree.subdivisions, level + 1) + '}}'
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
                    tup = D, (sum_proportions(S),)
                    n, m = get_group_subdivision(tup)
                    result += f' \\tuplet {n}/{m} {{{_notate(S, level + 1)}}}'
                if level == 0:
                    result = result.strip() + ' '
            return result.strip()
    return _notate(tree)
# ------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------
# TIME BLOCK ALGORITHMS
# ----------------------
#
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
