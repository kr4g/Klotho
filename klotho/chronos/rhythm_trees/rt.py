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
view : rhythm trees can be long, with a great number of parenthesis and sub lists nested 
within each others.

see: https://support.ircam.fr/docs/om/om6-manual/co/RT.html
--------------------------------------------------------------------------------------
'''
from fractions import Fraction
from typing import Union, Tuple
from math import gcd, lcm
from functools import reduce

from klotho.topos.graphs import Tree
from klotho.topos.graphs.trees.algorithms import rotate_tree, print_subdivisons
from .algorithms.rt_algs import measure_ratios, reduced_decomposition, strict_decomposition, sum_proportions, measure_complexity

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
                 meas:Union[Meas,Fraction,str] = '1/1',
                 subdivisions:Tuple            = (1,1),
                 decomp:str                    = 'reduced'):
        
        super().__init__(Meas(meas), subdivisions)
        self._span = span
        self._tree = Tree(self._root, self._children)
        self._decomp = decomp
        self._ratios = self._evaluate()
        self._type = self._set_type()
    
    @classmethod
    def from_tuple(cls, subdivisions:Tuple, span:int = 1, decomp:str = 'reduced'):
        return cls(span        = span,
                  meas         = Meas(sum(abs(r) for r in measure_ratios(subdivisions))),
                  subdivisions = subdivisions,
                  decomp       = decomp)
    
    @classmethod
    def from_tree(cls, tree:Tree, span:int = 1, decomp:str = 'reduced'):
        return cls(span        = span,
                  meas         = Meas(tree._root),
                  subdivisions = tree._children,
                  decomp       = decomp)
    
    @classmethod
    def from_ratios(cls, lst:Tuple[Fraction], span:int = 1, decomp:str = 'reduced'):
        pgcd_denom = reduce(lcm, (abs(ratio.denominator) for ratio in lst))
        S = tuple((r.numerator * (pgcd_denom // r.denominator)) for r in lst)
        meas = (sum_proportions(S), pgcd_denom)
        return cls(span        = span,
                  meas         = meas,
                  subdivisions = S,
                  decomp       = decomp)

    @property
    def tree(self):
        return self._tree
    
    @property
    def graph(self):
        return self._tree.graph
    
    @property
    def span(self):
        return self._span

    @property
    def meas(self):
        return self._root

    @property
    def subdivisions(self):
        return self._children

    @property
    def ratios(self):
        return self._ratios
    
    @property
    def decomp(self):
        return self._decomp

    @property
    def type(self):
        return self._type
    
    def flatten(self):
        return RhythmTree.from_ratios(self._ratios, self._span, self._decomp)
    
    def rotate(self, n:int = 1):
        return RhythmTree.from_tree(rotate_tree(self, n), self._span, self._decomp)
    
    def concat(self, other):
        if isinstance(other, RhythmTree):
            numer_1, denom_1 = self._root.numerator, self._root.denominator
            numer_2, denom_2 = other._root.numerator, other._root.denominator
            lcm_denom = (denom_1 * denom_2) // gcd(denom_1, denom_2)
            d1 = numer_1 * (lcm_denom // denom_1)
            d2 = numer_2 * (lcm_denom // denom_2)
            subdivs = ((d1, self._children), (d2, other._children))
            if self._root == other._root:
                span = self._span + other._span
                meas = self._root
            else:
                span = 1
                meas = self._root + other._root
            return RhythmTree(span = span,
                    meas = meas,
                    subdivisions = subdivs,
                    decomp = self._decomp)
        raise ValueError('Invalid Rhythm Tree')

    # def _evaluate(self):
    #     ratios = tuple(self._span * r for r in measure_ratios(self._children))
    #     match self._decomp:
    #         case 'reduced':
    #             return reduced_decomposition(ratios, self._root)
    #         case 'strict':
    #             return strict_decomposition(ratios, self._root)
    #         case _:
    #             return ratios
    
    def _evaluate(self):
        def process_subtree(node, parent_ratio=Fraction(1)):
            self._tree.graph.nodes[node]['proportion'] = self._tree.graph.nodes[node]['label']
            children = list(self._tree.graph.successors(node))
            
            if not children:
                ratio = Fraction(self._tree.graph.nodes[node]['label']) * parent_ratio
                self._tree.graph.nodes[node]['ratio'] = ratio
                return
            
            div = sum(abs(self._tree.graph.nodes[c]['label']) for c in children)
            
            for child in children:
                s = self._tree.graph.nodes[child]['label']
                ratio = Fraction(s, div) * parent_ratio
                self._tree.graph.nodes[child]['ratio'] = ratio
                process_subtree(child, ratio)
        
        process_subtree(0, self._span * self._root.to_fraction())
        return tuple(self._tree.graph.nodes[n]['ratio'] for n in self._tree.leaf_nodes)
    
    def _set_type(self):
        div = sum_proportions(self._children)
        if bin(div).count('1') != 1 and div != self._root.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self._children) else 'simple'

    def __len__(self):
        return len(self._ratios)

    def __repr__(self):
        ratios = ', '.join(tuple([str(r) for r in self._ratios]))
        subdivs = print_subdivisons(self._children)
        return (
            f'Span:         {self._span}\n'
            f'Meas:         {self._root}\n'
            f'Subdivisions: {subdivs}\n'
            f'Ratios:       {ratios}\n'
            # f'Type:          {self._type}\n'
            # f'Decomposition: {self._decomp}\n'
        )

# ------------------------------------------------------------------------------------

