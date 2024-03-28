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
from utils.algorithms.algorithms import *

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
                 time_signature:Union[Fraction, str] = '1/1',
                 subdivisions:Tuple                  = (1,),
                 decomp:str                          = 'reduced'):
        
        self.__duration       = duration
        self.__time_signature = Fraction(time_signature)
        self.__subdivisions   = subdivisions
        self.__decomp         = decomp
        self.__ratios         = self.__set_ratios()

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
        return factor_tree(self.__subdivisions)
    
    @property
    def ratios(self):
        return self.__ratios

    def __set_ratios(self):
        # Mesure Ratios
        ratios = tuple(self.__duration * r for r in measure_ratios(self.__subdivisions))
        # Decompose Ratios
        if self.__decomp == 'reduced':
            ratios = reduced_decomposition(ratios, self.__time_signature)
        elif self.__decomp == 'strict':
            ratios = strict_decomposition(ratios, self.__time_signature)
        return ratios

    def rotate(self, n=1):
        refactored = rotate_tree(self.__subdivisions, n)
        return RT(duration       = self.__duration,
                  time_signature = self.__time_signature,
                  subdivisions   = refactored,
                  decomp         = self.__decomp)
    
    def is_complex(self):
        div = sum_proportions(self.__subdivisions)
        if bin(div).count('1') != 1 and div != self.__time_signature.numerator:
            return True
        return measure_complexity(self.__subdivisions)

    def __repr__(self):
        ratios = ', '.join(tuple([str(r) for r in self.__ratios]))
        rt_type = 'complex' if self.is_complex() else 'simple'
        return (
            f'Duration: {self.__duration}\n'
            f'Time Signature: {self.__time_signature}\n'
            f'Subdivisions: {self.__subdivisions}\n'
            f'Decomposition: {self.__decomp}\n'
            f'Type: {rt_type}\n'
            f'Ratios: {ratios}\n'
        )


# ------------------------------------------------------------------------------------
# EXPERIMENTAL
# ------------------------------------------------------------------------------------
# def sum_proportions(tree):
#     return sum(abs(s[0]) if isinstance(s, tuple) else abs(s) for s in tree)

def notate(tree, level=0):
    # from utils.algorithms.algorithms import symbolic_approx, get_group_subdivision
    if isinstance(tree, RT):
        return f'\time {tree.time_signature}\n' + notate(tree.subdivisions, level)
    
    print(f'tree: {tree}, level: {level}')
    if isinstance(tree, tuple) and level == 0:
        tuplet_value = sum_proportions(tree)
        return f'\tuplet {tuplet_value}/d ' + '{{' + notate(tree, level+1) + '}}'
    else:
        result = ""
        for element in tree:
            if isinstance(element, int):  # Rest or single note
                if element < 0:  # Rest
                    result += f" -{abs(element)}"
                else:  # Single note
                    result += f" {element}"
            elif isinstance(element, tuple):  # Subdivision
                D, S = element
                if isinstance(D, int):  # If D is an integer, calculate the proportion
                    tuplet_value = sum_proportions(S) if isinstance(S, tuple) else D
                else:  # If D is a tuple, it's a nested tuplet
                    tuplet_value = sum_proportions(D)
                result += f' \\tuplet {tuplet_value}/d {{{notate(S, level+1)}}}'
            if level == 0:
                result = result.strip() + ' '
        return result.strip()

# def notate(tree, level=0):
#     if isinstance(tree, RT):
#         return f'\time {tree.time_signature}\n' + notate(tree.subdivisions, level)
    
#     if isinstance(tree, tuple) and level == 0:
#         tuplet_value = sum_proportions(tree)
#         return f'\tuplet {tuplet_value}/d ' + '{{' + notate(tree, level+1) + '}}'
#     else:
#         result = ""
#         for element in tree:
#             if isinstance(element, int):  # Rest or single note
#                 if element < 0:  # Rest
#                     result += f" -{abs(element)}"
#                 else:  # Single note
#                     result += f" {element}"
#             elif isinstance(element, tuple):  # Subdivision
#                 D, S = element
#                 if isinstance(D, int):  # If D is an integer, calculate the proportion
#                     tuplet_value = sum_proportions(S) if isinstance(S, tuple) else D
#                 else:  # If D is a tuple, it's a nested tuplet
#                     tuplet_value = sum_proportions(D)
#                 result += f' \\tuplet {tuplet_value}/d {{{notate(S, level+1)}}}'
#             if level == 0:
#                 result = result.strip() + ' '
#         return result.strip()
# ------------------------------------------------------------------------------------


if __name__ == '__main__':    
    # ------------------------------------------------------------------------------------
    # Rhythm Tree Examples
    # ------------------------------------------------------------------------------------
    # 
    pass
