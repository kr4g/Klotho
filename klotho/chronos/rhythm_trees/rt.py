# ------------------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_trees/rt.py
# ------------------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
A rhythm tree (RT) is a list representing a rhythmic structure. This list is organized 
hierarchically in sub lists , just as time is organized in measures, time signatures, 
pulses and rhythmic elements in the traditional notation.

Hence, the expression form of rhythm trees is crucially different from that of onsets 
and offsets. It can be exacting and not very "ergonomic", from a musician's point of 
view : rhythm trees can be long, with a great number of parenthesis and sub lists 
nested within each others.

see: https://support.ircam.fr/docs/om/om6-manual/co/RT.html
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union, Tuple
from math import gcd, lcm
from functools import reduce
import pandas as pd

from klotho.topos.graphs import Tree
from klotho.topos.graphs.trees.algorithms import print_subdivisons
from .algorithms.rt_algs import sum_proportions, measure_complexity, ratios_to_subdivs

class Meas:
    '''
    Time signature class that preserves unreduced fractions.
    Similar to Python's Fraction class, but for musical time signatures.
    '''
    def __init__(self, numerator, denominator=None):
        match (numerator, denominator):
            case (Meas() as m, None):
                self._numerator, self._denominator = m.numerator, m.denominator
            case (Fraction() as f, None):
                self._numerator, self._denominator = f.numerator, f.denominator
            case (int() as n, None):
                self._numerator, self._denominator = n, 1
            case (float() as f, None):
                frac = Fraction(f).limit_denominator()
                self._numerator, self._denominator = frac.numerator, frac.denominator
            case (str() as s, None):
                try:
                    num, den = map(int, s.replace('//', '/').split('/'))
                    self._numerator, self._denominator = num, den
                except ValueError:
                    raise ValueError('Invalid time signature format')
            case (int() as num, int() as den):
                self._numerator, self._denominator = num, den
            case _:
                raise ValueError('Invalid time signature arguments')

        if self._denominator == 0:
            raise ValueError('Time signature denominator cannot be zero')

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator
    
    def __add__(self, other):
        match other:
            case Meas() | Fraction():
                common_denominator = self._denominator * other.denominator
                new_numerator = (self._numerator * other.denominator) + (other.numerator * self._denominator)
                divisor = gcd(self._denominator, other.denominator)
                new_numerator = new_numerator // divisor
                common_denominator = common_denominator // divisor
                return Meas(new_numerator, common_denominator)
            case int():
                return Meas(self._numerator + (other * self._denominator), self._denominator)
            case float():
                return self + Meas(other)
            case str():
                try:
                    return self + Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __radd__(self, other):
        return self + other

    def __sub__(self, other):
        match other:
            case Meas() | Fraction():
                common_denominator = self._denominator * other.denominator
                new_numerator = (self._numerator * other.denominator) - (other.numerator * self._denominator)
                divisor = gcd(self._denominator, other.denominator)
                new_numerator = new_numerator // divisor
                common_denominator = common_denominator // divisor
                return Meas(new_numerator, common_denominator)
            case int():
                return Meas(self._numerator - (other * self._denominator), self._denominator)
            case float():
                return self - Meas(other)
            case str():
                try:
                    return self - Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rsub__(self, other):
        match other:
            case int():
                return Meas((other * self._denominator) - self._numerator, self._denominator)
            case float():
                return Meas(other) - self
            case str():
                try:
                    return Meas(other) - self
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __mul__(self, other):
        match other:
            case Meas() | Fraction():
                new_numerator = self._numerator * other.numerator
                new_denominator = self._denominator * other.denominator
                divisor = gcd(new_numerator, new_denominator)
                return Meas(new_numerator // divisor, new_denominator // divisor)
            case int():
                new_numerator = self._numerator * other
                divisor = gcd(new_numerator, self._denominator)
                return Meas(new_numerator // divisor, self._denominator // divisor)
            case float():
                return self * Meas(other)
            case str():
                try:
                    return self * Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rmul__(self, other):
        return self * other

    def __truediv__(self, other):
        match other:
            case Meas() | Fraction():
                if other.numerator == 0:
                    raise ZeroDivisionError("division by zero")
                new_numerator = self._numerator * other.denominator
                new_denominator = self._denominator * other.numerator
                divisor = gcd(new_numerator, new_denominator)
                return Meas(new_numerator // divisor, new_denominator // divisor)
            case int():
                if other == 0:
                    raise ZeroDivisionError("division by zero")
                new_denominator = self._denominator * other
                divisor = gcd(self._numerator, new_denominator)
                return Meas(self._numerator // divisor, new_denominator // divisor)
            case float():
                if other == 0:
                    raise ZeroDivisionError("division by zero")
                return self / Meas(other)
            case str():
                try:
                    return self / Meas(other)
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __rtruediv__(self, other):
        if self._numerator == 0:
            raise ZeroDivisionError("division by zero")
        match other:
            case int():
                new_numerator = other * self._denominator
                divisor = gcd(new_numerator, self._numerator)
                return Meas(new_numerator // divisor, self._numerator // divisor)
            case float():
                return Meas(other) / self
            case str():
                try:
                    return Meas(other) / self
                except ValueError:
                    return NotImplemented
            case _:
                return NotImplemented

    def __eq__(self, other):
        """Strict equality - exact same time signature representation"""
        match other:
            case Meas() | Fraction():
                return (self._numerator == other.numerator and 
                       self._denominator == other.denominator)
            case int():
                return self._numerator == other * self._denominator
            case float():
                try:
                    return self == Meas(other)
                except ValueError:
                    return False
            case str():
                try:
                    return self == Meas(other)
                except ValueError:
                    return False
            case _:
                return NotImplemented
    
    def __abs__(self):
        return Meas(abs(self._numerator), abs(self._denominator))

    def is_equivalent(self, other) -> bool:
        """Check if two time signatures represent the same metric proportion"""
        match other:
            case Meas() | Fraction():
                return (self._numerator * other.denominator == 
                       other.numerator * self._denominator)
            case str():
                try:
                    return self.is_equivalent(Meas(other))
                except ValueError:
                    return False
            case _:
                return False

    def __str__(self):
        return f'{self._numerator}/{self._denominator}'

    def __repr__(self) -> str:
        return self.__str__()
    
    def __float__(self):
        return self._numerator / self._denominator
    
    def to_fraction(self):
        return Fraction(self._numerator, self._denominator)
    
    def reduced(self):
        """Return a new Meas with reduced form"""
        return Meas(self.to_fraction().limit_denominator())
    

class RhythmTree(Tree):
    '''
    A rhythm tree is a list representing a rhythmic structure. This list is organized 
    hierarchically in sub lists, just as time is organized in measures, time signatures, 
    pulses and rhythmic elements in the traditional notation.

    Traditionally, rhythm is broken up into several data : meter, measure(s) and duration(s). 
    Rhythm trees must enclose these information in lists and sub list.

    This elementary rhythm:

    [1/4, 1/4, 1/4, 1/4] --> (four 1/4-notes in 4/4 time)

    can be expressed as follows :

    ( ? ( (4//4 (1 1 1 1) ) ) )

    A tree structure can be reduced to a list : (D (S)).


    >> Main Components : Duration and Subdivisions

    D = a duration , or number of measures : ( ? ) or a number ( n ).
    When D = ?, OM calculates the duration.
    By default, this duration is equal to 1.

    S = subdivisions (S) of this duration, that is a time signature and rhythmic proportions.
    Time signature = n // n   or ( n n ).
    It must be specified at each new measure, even if it remains unchanged.

    Rhythm = proportions : ( n n n n )

    see: https://support.ircam.fr/docs/om/om6-manual/co/RT1.html
    '''
    def __init__(self, 
                 span:int                      = 1,
                 meas:Union[Meas,Fraction,str] = '4/4',
                 subdivisions:Tuple            = (1,1)):
        super().__init__(Meas(meas).numerator, subdivisions)
        self._meta['span'] = span
        self._meta['meas'] = str(Meas(meas))
        self._meta['type'] = None
        self._subdivisions = self._cast_subdivs(subdivisions)
        self._ratios = self._evaluate()
    
    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1):
        return cls(span = span, meas = Meas(tree[tree.root]['ratio']), subdivisions = tree._list[1])
    
    @classmethod
    def from_ratios(cls, ratios:Tuple[Fraction, float, str], span:int = 1):
        ratios = tuple(Fraction(r) for r in ratios)
        S = ratios_to_subdivs(ratios)
        meas = Meas(sum(abs(r) for r in ratios))
        return cls(span = span, meas = meas, subdivisions = S)

    @property
    def span(self):
        return self._meta['span'].iloc[0]

    @property
    def meas(self):
        return Meas(self._meta['meas'].iloc[0])

    @property
    def subdivisions(self):
        return self._subdivisions

    @property
    def ratios(self):
        return self._ratios
    
    # @property
    # def type(self):
    #     if self._meta['type'] is None:
    #         self._meta['type'] = self._set_type()
    #     return self._meta['type']

    def subtree(self, node, renumber=True):
        tree_subtree = super().subtree(node, renumber)
        return self.__class__.from_tree(tree_subtree, 1)
    
    def _cast_subdivs(self, children):
        def convert_to_tuple(item):
            if isinstance(item, RhythmTree):
                return (item.meas.numerator * item.span, item.subdivisions)
            if isinstance(item, tuple):
                return tuple(convert_to_tuple(x) for x in item)
            return item
        
        return tuple(convert_to_tuple(child) for child in children)
    
    def _evaluate(self):
        self.graph.nodes[self.root]['ratio'] = self.meas
        def _process_subtree(node=0, parent_ratio=self.span * self.meas.to_fraction()):
            node_data = self.graph.nodes[node]
            
            if 'meta' in node_data:
                node_data['label'] = node_data['label'] * node_data['meta']['span']
            
            label = node_data['label']
            is_tied = isinstance(label, float)
            self.graph.nodes[node]['tied'] = is_tied
            label_value = int(label) if is_tied else label
            
            self.graph.nodes[node]['proportion'] = label_value
            children = list(self.graph.successors(node))
            
            if not children:
                ratio = Fraction(label_value) * parent_ratio
                self.graph.nodes[node]['ratio'] = ratio
                return
            
            div = int(sum(abs(self.graph.nodes[c]['label'] * 
                             self.graph.nodes[c]['meta']['span'] if 'meta' in self.graph.nodes[c]
                             else self.graph.nodes[c]['label']) 
                         for c in children))
            
            for child in children:
                child_data = self.graph.nodes[child]
                
                # if 'meta' in child_data:
                    # child_data['label'] = child_data['label'] * child_data['meta']['span']
                
                s = child_data['label']
                if 'meta' in child_data:
                    s = s * child_data['meta']['span']
                s = int(s) if isinstance(s, float) else s
                ratio = Fraction(s, div) * parent_ratio
                self.graph.nodes[child]['ratio'] = ratio
                self.graph.nodes[child]['proportion'] = s
                if self.graph.out_degree(child) > 0:
                    _process_subtree(child, ratio)
        
        _process_subtree()
        return tuple(self.graph.nodes[n]['ratio'] for n in self.leaf_nodes)

    def _set_type(self):
        div = sum_proportions(self.subdivisions)
        if bin(div).count('1') != 1 and div != self.meas.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self.subdivisions) else 'simple'

    def __len__(self):
        return len(self._ratios)

    def __str__(self):
        meta_dict = self._meta.iloc[0].to_dict()
        ordered_meta = {k: meta_dict[k] for k in ['span', 'meas', 'type', 'depth', 'k']}
        meta_str = ' | '.join(f"{k}: {v}" for k, v in ordered_meta.items())
        
        content = [
            meta_str,
            f"Subdivs: {print_subdivisons(self.subdivisions)}",
            f"Ratios:  {', '.join(str(r) for r in self._ratios)}"
        ]
        
        width = max(len(line) for block in content 
                   for line in block.split('\n'))
        border = '-' * width
        
        return (
            f"{border}\n"
            f"{content[0]}\n"
            f"{border}\n"
            f"{content[1]}\n"
            f"{content[2]}\n"
            f"{border}\n"
        )

    def __repr__(self):
        return self.__str__()

# ------------------------------------------------------------------------------------
