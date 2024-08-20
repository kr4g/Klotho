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
from math import gcd

from klotho.topos.graphs import Tree
from klotho.topos.graphs.trees.algorithms import rotate_tree
from .algorithms.rt_algs import *

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
                 duration:int                  = 1,
                 meas:Union[Meas,Fraction,str] = '1/1',
                 subdivisions:Tuple            = (1,),
                 decomp:str                    = 'reduced'):
        
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
    
    @classmethod
    def from_ratios(cls, lst:Tuple[Fraction], duration:int = 1, decomp:str = 'reduced'):
        pgcd_denom = reduce(lcm, (abs(ratio.denominator) for ratio in lst))
        S = tuple((r.numerator * (pgcd_denom // r.denominator)) for r in lst)
        meas = (sum_proportions(S), pgcd_denom)
        return cls(duration     = duration,
                   meas         = meas,
                   subdivisions = S,
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
    
    def flatten(self):
        return RhythmTree.from_ratios(self.__ratios, self.__duration, self.__decomp)
    
    def rotate(self, n:int = 1):
        return RhythmTree.from_tree(rotate_tree(self, n), self.__duration, self.__decomp)
    
    def concat(self, other):
        if isinstance(other, RhythmTree):
            numer_1, denom_1 = self._root.numerator, self._root.denominator
            numer_2, denom_2 = other._root.numerator, other._root.denominator
            lcm_denom = (denom_1 * denom_2) // gcd(denom_1, denom_2)
            d1 = numer_1 * (lcm_denom // denom_1)
            d2 = numer_2 * (lcm_denom // denom_2)
            subdivs = ((d1, self._children), (d2, other._children))
            if self._root == other._root:
                duration = self.__duration + other.__duration
                meas = self._root
            else:
                duration = 1
                meas = self._root + other._root
            return RhythmTree(duration       = duration,
                    meas = meas,
                    subdivisions   = subdivs,
                    decomp         = self.__decomp)
        raise ValueError('Invalid Rhythm Tree')

    def _evaluate(self):
        # ratios = tuple(self.__duration * r for r in measure_ratios(remove_ties(self._children)))
        ratios = tuple(self.__duration * r for r in measure_ratios(self._children))
        match self.__decomp:
            case 'reduced':
                return reduced_decomposition(ratios, self._root)
            case 'strict':
                return strict_decomposition(ratios, self._root)
            case _:
                return ratios
    
    def _set_type(self):
        div = sum_proportions(self._children)
        if bin(div).count('1') != 1 and div != self._root.numerator:
            return 'complex'
        return 'complex' if measure_complexity(self._children) else 'simple'

    def __len__(self):
        return len(self.__ratios)

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

class Meas:
    '''
    Time signature class that preserves unreduced fractions.
    '''
    def __init__(self, signature: Union[str, tuple, int, float] = '1/1'):
        if isinstance(signature, Meas):
            self._numerator, self._denominator = signature.numerator, signature.denominator
        elif isinstance(signature, Fraction):
            self._numerator = signature.numerator
            self._denominator = signature.denominator
        elif isinstance(signature, tuple):
            if len(signature) != 2:
                raise ValueError("Tuple must have exactly two elements")
            self._numerator, self._denominator = signature
        elif isinstance(signature, int):
            self._numerator = signature
            self._denominator = 1
        elif isinstance(signature, float):
            frac = Fraction(signature).limit_denominator()
            self._numerator = frac.numerator
            self._denominator = frac.denominator
        elif isinstance(signature, str):
            try:
                parts = signature.replace('//', '/').split('/')
                if len(parts) != 2:
                    raise ValueError('Invalid time signature format')
                self._numerator = int(parts[0])
                self._denominator = int(parts[1])
            except ValueError:
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
            common_denominator = self._denominator * other.denominator
            new_numerator = (self._numerator * other.denominator) + (other.numerator * self._denominator)
            divisor = gcd(self._denominator, other.denominator)
            new_numerator = new_numerator // divisor
            common_denominator = common_denominator // divisor
            return Meas((new_numerator, common_denominator))
        raise ValueError('Invalid type for addition')

    def __sub__(self, other):
        if isinstance(other, (Meas, Fraction)):
            common_denominator = self._denominator * other.denominator
            new_numerator = (self._numerator * other.denominator) - (other.numerator * self._denominator)
            divisor = gcd(self._denominator, other.denominator)
            new_numerator = new_numerator // divisor
            common_denominator = common_denominator // divisor
            return Meas((new_numerator, common_denominator))
        raise ValueError('Invalid type for subtraction')

    def __mul__(self, other):
        if isinstance(other, (Meas, Fraction)):
            new_numerator = self._numerator * other.numerator
            new_denominator = self._denominator * other.denominator
            return Meas((new_numerator, new_denominator))
        raise ValueError('Invalid type for multiplication')

    def __truediv__(self, other):
        if isinstance(other, (Meas, Fraction)):
            new_numerator = self._numerator * other.denominator
            new_denominator = self._denominator * other.numerator
            return Meas((new_numerator, new_denominator))
        raise ValueError('Invalid type for division')

    def __eq__(self, other):
        if isinstance(other, (Meas, Fraction)):
            return (self._numerator, self._denominator) == (other.numerator, other.denominator)
        elif isinstance(other, tuple) and len(other) == 2:
            return (self._numerator, self._denominator) == tuple(map(int, other))
        elif isinstance(other, str):
            try:
                other_numerator, other_denominator = map(int, other.replace('//', '/').split('/'))
                return (self._numerator, self._denominator) == (other_numerator, other_denominator)
            except ValueError:
                return False
        return NotImplemented

    def __str__(self):
        return f'{self._numerator}/{self._denominator}'

    def __repr__(self) -> str:
        return self.__str__()
    
    def __float__(self):
        return self._numerator / self._denominator
    
    def to_fraction(self):
        return Fraction(self._numerator, self._denominator)
    
    def type(self):
        '''
        Determines the type of time signature: "simple duple", "simple triple", 
        "compound duple", "compound triple", "complex", "additive", or "irregular".
        '''
        if self._denominator in [2, 4, 8, 16]:
            if self._numerator in [2, 3, 4]:
                if self._numerator == 2:
                    return "simple duple"
                elif self._numerator == 3:
                    return "simple triple"
                elif self._numerator == 4:
                    return "simple quadruple"
            elif self._numerator in [6, 9, 12]:
                if self._numerator == 6:
                    return "compound duple"
                elif self._numerator == 9:
                    return "compound triple"
                elif self._numerator == 12:
                    return "compound quadruple"
            elif self._numerator in [5, 7, 10, 11]:
                return "complex"
            elif self._numerator > 12:
                if all(x in [2, 3, 4] for x in self._numerator_digits()):
                    return "additive"
                else:
                    return "complex"
            else:
                return "irregular"
        else:
            return "irregular"

    def _numerator_digits(self):
        '''
        Helper function to break down the numerator into its component parts.
        Useful for additive meters like 5/8 (2+3/8).
        '''
        digits = []
        n = self._numerator
        while n > 0:
            digits.append(n % 10)
            n //= 10
        return digits[::-1]
