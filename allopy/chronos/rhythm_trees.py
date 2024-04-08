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
from math import gcd

from utils.algorithms.tree_algorithms import *

class Meas:    
    '''
    Time signature class that accepts a Fraction, string, or tuple
    and stores the numerator and denominator separately.
    '''
    def __init__(self, signature: Union[Fraction, str, tuple] = '1/1'):
        if isinstance(signature, Fraction):
            self._numerator, self._denominator = signature.numerator, signature.denominator
        elif isinstance(signature, tuple):
            self._numerator, self._denominator = signature
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
            # if the denominator is the same, add the numerators
            if self.denominator == other.denominator:
                return Meas((self.numerator + other.numerator, self.denominator))
            # if the denominators are different, cast to fractions and add
            return Meas(Fraction(self.numerator, self.denominator) + Fraction(other.numerator, other.denominator))
        raise ValueError('Invalid time signature')

    def __sub__(self, other):
        if isinstance(other, (Meas, Fraction)):
            # if the denominator is the same, subtract the numerators
            if self.denominator == other.denominator:
                return Meas((self.numerator - other.numerator, self.denominator))
            # if the denominators are different, cast to fractions and subtract
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


class RT:
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
                 duration:int                        = 1,
                 time_signature:Union[Meas, str]     = '1/1',
                 subdivisions:Tuple                  = (1,),
                 decomp:str                          = 'reduced'):
        
        self.__duration       = duration
        self.__time_signature = Meas(time_signature)
        self.__subdivisions   = subdivisions
        self.__decomp         = decomp
        self.__ratios         = self._set_ratios()
        self.__type           = self._set_complexity()
        self.__graph          = None
        self.__factors        = None
        
    @classmethod
    def from_tuple(cls, tup:Tuple):
        return cls(duration       = 1,
                   time_signature = sum(measure_ratios(tup)),
                   subdivisions   = tup,
                   decomp         = 'reduced')

    @property
    def duration(self):
        return self.__duration

    @property
    def time_signature(self):
        return self.__time_signature

    @property
    def subdivisions(self):
        return self.__subdivisions

    @property
    def decomp(self):
        return self.__decomp

    @property
    def factors(self):
        if self.__factors is None:
            self.__factors = factor_tree(self.__subdivisions)
        return self.__factors
    
    @property
    def ratios(self):
        return self.__ratios
    
    @property
    def type(self):
        return self.__type
    
    @property
    def graph(self):
        if self.__graph is None:
            self.__graph = graph_tree(self.time_signature, self.__subdivisions)
        return self.__graph

    def rotate(self, n=1):
        refactored = rotate_tree(self.__subdivisions, n)
        return RT(duration       = self.__duration,
                  time_signature = self.__time_signature,
                  subdivisions   = refactored,
                  decomp         = self.__decomp)
    
    def concat(self, other):
        if isinstance(other, RT):
            numer_1, denom_1 = self.__time_signature.numerator, self.__time_signature.denominator
            numer_2, denom_2 = other.__time_signature.numerator, other.__time_signature.denominator
            lcm_denom = (denom_1 * denom_2) // gcd(denom_1, denom_2)
            d1 = numer_1 * (lcm_denom // denom_1)
            d2 = numer_2 * (lcm_denom // denom_2)
            subdivs = ((d1, self.__subdivisions), (d2, other.__subdivisions))
            if self.__time_signature == other.__time_signature:
                duration = self.__duration + other.__duration
                time_signature = self.__time_signature
            else:
                duration = 1
                time_signature = self.__time_signature + other.__time_signature
            return RT(duration       = duration,
                      time_signature = time_signature,
                      subdivisions   = subdivs,
                      decomp         = self.__decomp)
        raise ValueError('Invalid Rhythm Tree')

    def _set_ratios(self):
        ratios = tuple(self.__duration * r for r in measure_ratios(self.__subdivisions))
        if self.__decomp == 'reduced':
            ratios = reduced_decomposition(ratios, self.__time_signature)
        elif self.__decomp == 'strict':
            ratios = strict_decomposition(ratios, self.__time_signature)
        return ratios
    
    def _set_complexity(self):
        div = sum_proportions(self.__subdivisions)
        if bin(div).count('1') != 1 and div != self.__time_signature.numerator:
            return True
        return measure_complexity(self.__subdivisions)

    def __repr__(self):
        ratios = ', '.join(tuple([str(r) for r in self.__ratios]))
        rt_type = 'complex' if self.__type else 'simple'
        return (
            f'Duration: {self.__duration}\n'
            f'Time Signature: {self.__time_signature}\n'
            f'Subdivisions: {self.__subdivisions}\n'
            f'Decomposition: {self.__decomp}\n'
            f'Type: {rt_type}\n'
            f'Ratios: {ratios}\n'
        )

# ------------------------------------------------------------------------------------


if __name__ == '__main__':    
    # ------------------------------------------------------------------------------------
    # Rhythm Tree Examples
    # ------------------------------------------------------------------------------------
    print('Rhythm Tree Examples')
    s = ((4, (3, (8, (3, 4)))), -3)
    rt = RT(time_signature='4/3', subdivisions=s)
    print(rt)
