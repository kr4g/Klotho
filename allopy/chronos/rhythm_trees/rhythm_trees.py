# ------------------------------------------------------------------------------------
# AlloPy/allopy/chronos/rhythm_trees.py
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
# from math import gcd

# from .rt_algorithms import measure_ratios, sum_proportions, measure_complexity, reduced_decomposition, strict_decomposition
from .algorithms.subdivisions import measure_ratios, sum_proportions, measure_complexity, reduced_decomposition, strict_decomposition

from allopy.topos.graphs import Tree
    
class Meas:    
    '''
    Time signature class that accepts a Fraction, string, or tuple
    and stores the numerator and denominator separately.
    '''
    def __init__(self, signature: Union[Fraction, str, tuple] = '1/1'):
        if isinstance(signature, Meas):
            self._numerator, self._denominator = signature.numerator, signature.denominator        
        elif isinstance(signature, Fraction):
            self._numerator, self._denominator = signature.numerator, signature.denominator
        elif isinstance(signature, tuple):
            self._numerator, self._denominator = signature
        elif isinstance(signature, (int, float)):
            self._numerator, self._denominator = Fraction(signature).numerator, Fraction(signature).denominator
        elif isinstance(signature, str):
            parts = signature.replace('//', '/').split('/')
            if len(parts) == 2:
                self._numerator, self._denominator = map(int, parts)
            else:
                raise ValueError('Invalid time signature format')
        else:
            raise ValueError('Invalid time signature type')

        if self._denominator == 0:
            raise ValueError('Time signature denominator cannot be zero')

    @property
    def numerator(self):
        return self._numerator

    @property
    def denominator(self):
        return self._denominator
    
    def __add__(self, other):
        if isinstance(other, (Meas, Fraction)):
            if self.denominator == other.denominator:
                return Meas((self.numerator + other.numerator, self.denominator))
            return Meas(Fraction(self.numerator, self.denominator) + Fraction(other.numerator, other.denominator))
        raise ValueError('Invalid time signature')

    def __sub__(self, other):
        if isinstance(other, (Meas, Fraction)):
            if self.denominator == other.denominator:
                return Meas((self.numerator - other.numerator, self.denominator))
            return Meas(Fraction(self.numerator, self.denominator) - Fraction(other.numerator, other.denominator))
        raise ValueError('Invalid time signature')            
    
    def __eq__(self, other):
        if isinstance(other, (Meas, Fraction)):
            return (self.numerator, self.denominator) == (other.numerator, other.denominator)
        elif isinstance(other, tuple) and len(other) == 2:
            return (self.numerator, self.denominator) == tuple(map(int, other))
        elif isinstance(other, str):
            try:
                other_numerator, other_denominator = map(int, other.replace('//', '/').split('/'))
                return (self.numerator, self.denominator) == (other_numerator, other_denominator)
            except ValueError:
                return False
        return NotImplemented

    def __repr__(self) -> str:
        return f'{self._numerator}/{self._denominator}'
    
    def __str__(self):
        return f'{self._numerator}/{self._denominator}'


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
                 duration:int          = 1,
                 meas:Union[Meas, str] = '1/1',
                 subdivisions:Tuple    = (1,),
                 decomp:str            = 'reduced'):
        
        super().__init__(Meas(meas), subdivisions)
        self.__duration = duration
        self.__decomp   = decomp
        self.__ratios   = self._evaluate()
        self.__type     = self._set_type()
    
    @classmethod
    def from_tuple(cls, subdivisions:Tuple, duration:int = 1, decomp:str = 'reduced'):
        return cls(duration     = duration,
                   meas         = Meas(sum(abs(r) for r in measure_ratios(subdivisions))),
                   subdivisions = subdivisions,
                   decomp       = decomp)
    
    @classmethod
    def from_tree(cls, tree:Tree, duration:int = 1, decomp:str = 'reduced'):
        return cls(duration     = duration,
                   meas         = Meas(tree._root),
                   subdivisions = tree._children,
                   decomp       = decomp)

    @property
    def tree(self):
        return Tree(self._root, self._children)
    
    @property
    def duration(self):
        return self.__duration

    @property
    def meas(self):
        return self._root

    @property
    def subdivisions(self):
        return self._children

    @property
    def decomp(self):
        return self.__decomp

    @property
    def ratios(self):
        return self.__ratios
    
    @property
    def type(self):
        return self.__type

    # def rotate(self, n=1):
    #     refactored = rotate_tree(self.__children, n)
    #     return RhythmTree(duration       = self.__duration,
    #               meas = self.__root,
    #               subdivisions   = refactored,
    #               decomp         = self.__decomp)
    
    # def concat(self, other):
    #     if isinstance(other, RhythmTree):
    #         numer_1, denom_1 = self.__root.numerator, self.__root.denominator
    #         numer_2, denom_2 = other.__root.numerator, other.__root.denominator
    #         lcm_denom = (denom_1 * denom_2) // gcd(denom_1, denom_2)
    #         d1 = numer_1 * (lcm_denom // denom_1)
    #         d2 = numer_2 * (lcm_denom // denom_2)
    #         subdivs = ((d1, self.__children), (d2, other.__children))
    #         if self.__root == other.__root:
    #             duration = self.__duration + other.__duration
    #             meas = self.__root
    #         else:
    #             duration = 1
    #             meas = self.__root + other.__root
    #         return RhythmTree(duration       = duration,
    #                   meas = meas,
    #                   subdivisions   = subdivs,
    #                   decomp         = self.__decomp)
    #     raise ValueError('Invalid Rhythm Tree')

    def _evaluate(self):
        # ratios = tuple(self.__duration * r for r in measure_ratios(remove_ties(self.__children)))
        ratios = tuple(self.__duration * r for r in measure_ratios(self._children))
        if self.__decomp == 'reduced':
            return reduced_decomposition(ratios, self._root)
        elif self.__decomp == 'strict':
            return strict_decomposition(ratios, self._root)
        return ratios
    
    def _set_type(self):
        div = sum_proportions(self._children)
        if bin(div).count('1') != 1 and div != self._root.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self._children) else 'simple'

    def __repr__(self):
        ratios = ', '.join(tuple([str(r) for r in self.__ratios]))
        return (
            f'Duration:       {self.__duration}\n'
            f'Time Signature: {self._root}\n'
            f'Subdivisions:   {self._children}\n'
            f'Decomposition:  {self.__decomp}\n'
            f'Type:           {self.__type}\n'
            f'Ratios:         {ratios}\n'
        )

# ------------------------------------------------------------------------------------
