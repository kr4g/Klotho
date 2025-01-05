from typing import Union, Tuple, List
from fractions import Fraction
from math import gcd, lcm, prod, floor, log
from ...chronos.rhythm_trees import Meas, RhythmTree as RT
from ...chronos.rhythm_trees.algorithms import sum_proportions

# ------------------------------------------------------------------------------------
# NOTATION

def add_tie(n) -> Union[int, Tuple[int]]:
    p = 1
    if n > 0:
        while p * 2 <= n:
            p *= 2    
        if p == n or p * 1.5 == n or p * 1.75 == n:
            return n
        elif n > p * 1.5:
            return (p + p//2, add_tie(n - (p * 1.5)))
        else:
            return (p, float(add_tie(n - p)))
    else:
        n = abs(n)
        while p * 2 <= n:
            p *= 2    
        if p == n or p * 1.5 == n or p * 1.75 == n:
            return -n
        elif n > p * 1.5:
            return (-(p + p//2), -add_tie(n - (p * 1.5)))
        else:
            return (-p, -add_tie(n - p))
    
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

# XXX - this removes rests!!! Wrong.
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

def symbolic_unit(meas:Union[Meas, Fraction, str]) -> Fraction:
    return Fraction(1, symbolic_approx(Meas(meas).denominator))

def symbolic_duration(f:int, meas:Union[Meas, Fraction, str], S:tuple) -> Fraction:
    # ds (f,m) = (f * numerator (D)) / (1/us (m) * sum of elements in S)
    meas = Meas(meas)
    return Fraction(f * meas.numerator) / (1 / symbolic_unit(meas) * sum_proportions(S))

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
    n = abs(n)
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
    r = abs(r)
    if r >= 2:
        return 'square'
    elif r == 1:
        return 'whole'
    elif r == 1/2:
        return 'half'
    else:
        return 'quarter'

def get_note_beams(r:Fraction):
    r = abs(r)
    if r >= 2 or r == 1/4 or r == 1/2 or r == 1:
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

def create_tuplet(G):
    D, S = G
    div = sum_proportions(S)
    n, m = div, D
    
    if n > m and n % 2 == 0:
        while (new_n := n // 2) > m and new_n % 2 == 0:
            n = new_n
    elif n < m and n % 2 == 0:
        while (new_n := n * 2) < m and new_n % 2 == 0:
            n = new_n
    
    if m > n and m % 2 == 0:
        while (new_m := m // 2) >= n and new_m % 2 == 0:
            m = new_m
    elif m < n and m % 2 == 0:
        while (new_m := m * 2) <= n and new_m % 2 == 0:
            m = new_m
    if n == m:
        return None
    return [n, m]

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
            pi, ps = pow_n_bounds(n, 2)
            m = ps if abs(n - pi) > abs(n - ps) else pi
    return [n, m]

# def notate(tree):
#     def _notate(tree, level=0):
#         if level == 0:
#             return f'\\time {tree.meas}\n' + _notate(tree, level + 1)
        
#         # print(f'tree: {tree}, level: {level}')
#         if level == 1:
#             S = add_ties(tree.subdivisions)
#             tup = tree.meas.numerator, (sum_proportions(tree.subdivisions),)
#             n, m = get_group_subdivision(tup)
#             if n == m: # no tuplet
#                 return _notate(S, level + 1)
#             return f'\\tuplet {n}/{m} ' + '{' + _notate(S, level + 1) + '}'
#         else:
#             result = ""
#             for element in tree:
#                 if isinstance(element, (int, float)):      # Rest or single note
#                     if element < 0:     # Rest
#                         result += f" r{abs(element)}"
#                     else:       # Single note
#                         result += f" {element}"
#                 elif isinstance(element, tuple):           # Subdivision                
#                     D, S = element
#                     tup = D, (sum_proportions(S),)
#                     n, m = get_group_subdivision(tup)
#                     if n == m:
#                         result += f' {_notate(S, level + 1)}'
#                     else:
#                         result += f' \\tuplet {n}/{m} ' + '{' + _notate(S, level + 1) + '}'
#                 if level == 0:
#                     result = result.strip() + ' '
#             return result.strip()
#     return _notate(tree)

def notate(rt: RT):
    def _process(node=0, parent_dur=symbolic_unit(rt.meas) * rt.meas.numerator):
        children = list(rt.graph.successors(node))
        if children:
            level_sum = sum(abs(rt.graph.nodes[c]['label']) for c in children)
            
            p_sum = rt.graph.nodes[node]['label'] if node != 0 else rt.graph.nodes[node]['label'].numerator
            print(f"{level_sum} : {p_sum}")
            # n, m = get_group_subdivision((p_sum, (level_sum,)))
            # print(f"n: {n}, m: {m}")
            
            for child in children:
                child_label = rt.graph.nodes[child]['label']
                sym_dur = symbolic_duration(child_label, parent_dur, (level_sum,))
                unit = symbolic_unit(sym_dur)
                mult = sym_dur.numerator if unit == sym_dur else child_label
                if rt.graph.out_degree(child) == 0:  # leaf node
                    hdb = head_dots_beams(unit * mult)
                    print(f"Node {child} -> {hdb}")
                else:  # internal node
                    # next_dur = symbolic_unit(sym_dur) * child_label
                    next_dur = symbolic_unit(sym_dur) * mult
                    _process(child, next_dur)
    return _process()
