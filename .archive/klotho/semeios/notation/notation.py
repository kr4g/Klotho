from typing import Union, Tuple, List
from fractions import Fraction
from math import gcd, lcm, prod, floor, log
from klotho.chronos.rhythm_trees import Meas, RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import sum_proportions
import abjad

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
    # S = remove_ties(S)
    def process_tuple(t):
        result = []
        for value in t:
            if isinstance(value, tuple):
                processed_tuple = process_tuple(value[1])
                result.append((value[0], processed_tuple))
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
    # return Fraction(f * meas.numerator) / (1 / symbolic_unit(meas) * sum_proportions(S))
    return Fraction(f * meas.numerator) / (Fraction(1, symbolic_unit(meas)) * sum_proportions(S))

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
    div = int(sum_proportions(S))
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
            
    n = int(n)
    m = int(m)
    
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
    # ds = D
    subdiv = int(sum_proportions(S))
    ds = symbolic_duration(D, symbolic_unit(f'{1}/{subdiv}'), S)
    
    if subdiv == 1:
        n = ds
    elif float(ds / subdiv).is_integer() and ((ds // subdiv).bit_length() == 1 or (subdiv // ds).bit_length() == 1):
        n = ds
    else:
        n = subdiv
    
    # ratio = Fraction(ds, subdiv)
    if is_binary(ds):
        m = symbolic_approx(n)
    elif is_ternary(ds):
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

def notate_rt(rt: RT) -> str:
    """Generate Lilypond notation from a RhythmTree.
    Returns a string of Lilypond code."""
    
    _rt = rt  # RT(meas=rt.meas, subdivisions=add_ties(rt.subdivisions))
    
    def _process_node(node=0, parent_dur=symbolic_unit(_rt.meas) * _rt.meas.numerator) -> str:
        children = list(_rt.graph.successors(node))
        if not children:
            return ""
        
        level_sum = sum(abs(_rt.graph.nodes[c]['label']) for c in children)
        p_sum = _rt.graph.nodes[node]['label'] if node != 0 else _rt.graph.nodes[node]['label'].numerator
        
        tuplet = create_tuplet((p_sum, (level_sum,)))
        # tuplet = get_group_subdivision((p_sum, (level_sum,)))
        
        child_notes = []
        for i, child in enumerate(children):
            child_label = _rt.graph.nodes[child]['label']
            is_tied = isinstance(child_label, float)
            
            value = int(child_label) if is_tied else child_label
            
            sym_dur = symbolic_duration(value, parent_dur, (level_sum,))
            unit = symbolic_unit(sym_dur)
            mult = sym_dur.numerator if unit == sym_dur else value
            
            if _rt.graph.out_degree(child) == 0:  # leaf node
                hdb = head_dots_beams(unit * Fraction(mult))
                note_type = hdb[0]
                dots = '.' * hdb[1]
                beams = hdb[2]
                
                base_duration = {
                    'square': '\\longa',
                    'whole': '1',
                    'half': '2',
                    'quarter': '4',
                }[note_type]
                
                if isinstance(base_duration, str) and base_duration.startswith('\\'): 
                    actual_duration = base_duration
                else:
                    duration_value = int(base_duration)
                    if beams > 0:
                        duration_value *= 2 ** beams
                    actual_duration = str(int(duration_value))
                
                is_rest = value < 0
                note = f"r{actual_duration}{dots}" if is_rest else f"bd{actual_duration}{dots}"
                
                if i > 0 and is_tied:
                    child_notes[-1] += " ~"
                
                child_notes.append(note)
            else:
                next_dur = symbolic_unit(sym_dur) * mult
                child_notes.append(_process_node(child, next_dur))
        
        result = ' '.join(child_notes)
        
        if tuplet:
            n, m = tuplet
            result = f"\\tuplet {n}/{m} {{ {result} }}"
            # result = f"\\tuplet {n}/{p_sum} {{ {result} }}"
        
        return result

    lily_code = f"\\time {_rt.meas}\n"
    lily_code += _process_node()
    
    return lily_code

def create_lily_file(rt: RT, filename: str = "rhythm") -> str:
    """Create a complete Lilypond file from a RhythmTree.
    
    Args:
        rt: RhythmTree instance
        filename: Output filename (without extension)
    
    Returns:
        Complete Lilypond code as string
    """
    lily_code = f'''\\version "2.24.0"
    \\header {{
        title = "{rt.subdivisions}"
        tagline = ##f
    }}

    \\score {{
        \\new DrumStaff \\with {{
            \\override StaffSymbol.line-count = #1
            drumStyleTable = #drums-style
            \\override Stem.direction = #up
        }} {{
            \\override Score.TupletNumber.text = #(lambda (grob) (tuplet-number::calc-fraction-text grob))
            \\drummode {{
                {notate_rt(rt)}
            }}
        }}
        \\layout {{ }}
    }}'''
    
    # Write to file
    with open(f"{filename}.ly", "w") as f:
        f.write(lily_code)
    
    return lily_code

def notate_multiple_rts(rts: List[RT]) -> List[str]:
    """Generate Lilypond notation for multiple RhythmTrees.
    Returns a list of strings, each containing Lilypond code for a separate staff."""
    
    def _process_node(rt:RT, node:int=0, parent_dur=None) -> str:
        children = list(rt.graph.successors(node))
        if not children:
            return ""
        
        level_sum = sum(abs(rt.graph.nodes[c]['label']) for c in children)
        p_sum = rt.graph.nodes[node]['label'] if node != 0 else rt.graph.nodes[node]['label'].numerator
        
        tuplet = create_tuplet((p_sum, (level_sum,)))
        # tuplet = get_group_subdivision((p_sum, (level_sum,)))
        # tuplet = (int(level_sum), int(p_sum))
        
        child_notes = []
        for i, child in enumerate(children):
            child_label = rt.graph.nodes[child]['label']
            is_tied = isinstance(child_label, float)
            
            value = int(child_label) if is_tied else child_label
            
            # sym_dur = symbolic_duration(value, parent_dur, (level_sum,))
            sym_dur = rt.graph.nodes[child]['ratio']
            unit = symbolic_unit(sym_dur)
            
            if isinstance(sym_dur, float):
                sym_dur = Fraction(sym_dur).limit_denominator()
            
            # mult = sym_dur.numerator if unit == sym_dur else value
            mult = 1 if unit == sym_dur else abs(value)
            note_duration = unit * Fraction(mult)
            
            if rt.graph.out_degree(child) == 0:  # leaf node
                hdb = head_dots_beams(note_duration)
                note_type = hdb[0]
                dots = '.' * hdb[1]
                beams = hdb[2]
                
                base_duration = {
                    'square': '\\longa',
                    'whole': '1',
                    'half': '2',
                    'quarter': '4',
                }[note_type]
                
                if isinstance(base_duration, str) and base_duration.startswith('\\'): 
                    actual_duration = base_duration
                else:
                    duration_value = int(base_duration)
                    if beams > 0:
                        duration_value *= 2 ** beams
                    actual_duration = str(int(duration_value))
                
                is_rest = value < 0

                note = f"r{actual_duration}{dots}" if is_rest else f"c{actual_duration}{dots}"
                
                if i > 0 and is_tied:
                    child_notes[-1] += " ~"
                
                child_notes.append(note)
            else:
                # next_dur = symbolic_unit(sym_dur) * mult
                next_dur = note_duration
                child_notes.append(_process_node(rt, child, next_dur))
        
        result = ' '.join(child_notes)
        
        if tuplet:
            n, m = tuplet
            if n.bit_length() != 1 and not ((n/m).is_integer() or (m/n).is_integer()):
                result = f"\\tuplet {n}/{m} {{ {result} }}"
                # result = f"\\tuplet {n}/{p_sum} {{ {result} }}"
        
        return result

    lily_codes = []
    for rt in rts:
        parent_dur = symbolic_unit(rt.meas) * rt.meas.numerator
        lily_code = f"\\time {rt.meas}\n"
        lily_code += _process_node(rt, parent_dur=parent_dur)
        lily_codes.append(lily_code)
    
    return lily_codes

def create_lily_file_multiple(rts: List[RT], filename: str = "my_rhythms") -> str:
    """Create a complete Lilypond file from multiple RhythmTrees.
    
    Args:
        rts: List of RhythmTree instances
        filename: Output filename (without extension)
    
    Returns:
        Complete Lilypond code as string
    """
    lily_codes = notate_multiple_rts(rts)
    
    lily_code = f'''\\version "2.24.0"
    \\header {{
        title = "Multiple Rhythm Trees"
        tagline = ##f
    }}
    
    \\score {{
        <<
    '''
    
    for i, code in enumerate(lily_codes):
        lily_code += f'''
        \\new RhythmicStaff {{
            \\override Score.TupletNumber.text = #(lambda (grob) (tuplet-number::calc-fraction-text grob))
            {code}
        }}
        '''
    
    lily_code += '''
        >>
        \\layout {
            \\context {
                \\Score
                \\remove "Bar_number_engraver"
                \\override SpacingSpanner.uniform-stretching = ##t
                proportionalNotationDuration = #(ly:make-moment 1/22)
            }
        }
    }
    '''
    
    # Write to file
    with open(f"{filename}.ly", "w") as f:
        f.write(lily_code)
    
    return lily_code
