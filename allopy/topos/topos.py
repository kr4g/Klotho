# ------------------------------------------------------------------------------------
# MUSIC TOPOLOGY TOOLS
# ------------------------------------------------------------------------------------
'''
The `topos` base module.
'''
from allopy.chronos import chronos
from allopy.aikous import aikous

from sympy.utilities.iterables import cartes
import numpy as np
import regex
from math import prod
from fractions import Fraction

TOPOS_WARNINGS = True

def iso_pairs(l1: list, l2: list) -> list:
    '''
    Generates pairs of elements from two lists, l1 and l2, in a cyclic manner. 

    Creates a list of tuples where each element from l1 is paired with each 
    element from l2. The pairing continues cyclically until the length
    of the generated list equals the product of the lengths of l1 and l2. 
    Specifically, when the end of either list is reached, the iteration 
    continues from the beginning of that list, effectively cycling through 
    the shorter list until all pairings are created.
    
    This is a form of "cyclic pairing" or "modulo-based pairing" and is 
    different from computing the Cartesian product.

    Args:
        l1 (list): The first list, consisting of Type 1.
        l2 (list): The second list, consisting of Type 2.
    
    Returns:
        list: A list of tuples where each element from l1 is paired with each 
        element from l2.

    Example:
    >>> iso_pairs(('⚛', '∿'), ('Ξ', '≈'))
    (('⚛', 'Ξ'), ('∿', '≈'), ('⚛', '≈'), ('∿', 'Ξ'))
    '''
    if TOPOS_WARNINGS:
        if Fraction(len(l1), len(l2)).denominator == 1:
            print('PAY HEED! THE TOPOS CAUTIONS YOU: The length of the lists should not evenly divide.' + 
                'Otherwise, the cyclic pairing will be equivalent to a Cartesian product.  If this is your intention, ' +
                'The Topos bids you to proceed.  If this is not your intention, The Topos suggests you ' +
                'provide lists of indivisible lengths.  The Topos has spoken.')

    return tuple((l1[i % len(l1)], l2[i % len(l2)]) for i in range(len(l1) * len(l2)))

def cyclic_cartesian_pairs(l1: list, l2: list) -> list:
    '''
    Generates a sequence of pairs by first creating a Cartesian product of list l1 with itself,
    and then cycling through these pairs while pairing them with elements from list l2.
    Each pair from the Cartesian product of l1 is combined with an element from l2, 
    cycling through l2 as necessary.

    Args:
        l1 (list): The first list, consisting of Type 1.
        l2 (list): The second list, consisting of Type 2.
    
    Returns:
        list: A list of tuples, each containing a pair from the Cartesian product of l1 and an element from l2.

    Example:
    >>> cyclic_cartesian_pairs(['Ψ', '⧭', 'Ω'], ('¤', '〄'))
    (('Ψ', 'Ψ'), '¤'), (('Ψ', '⧭'), '〄'), (('Ψ', 'Ω'), '¤'),
    (('⧭', 'Ψ'), '〄'), (('⧭', '⧭'), '¤'), (('⧭', 'Ω'), '〄'),
    (('Ω', 'Ψ'), '¤'), (('Ω', '⧭'), '〄'), (('Ω', 'Ω'), '¤')
    '''
    return iso_pairs(tuple(cartes(l1, l1)), l2)

def context_sensitive_parsing(rules, axiom):
    i = 0
    while i < len(axiom):
        replaced = False
        for context, replacement in rules.items():
            if "<" in context and ">" in context:  # this is a context-sensitive rule
                left, middle, right = regex.match(r'(.*)<(.*)>(.*)', context).groups()
                left = left.replace('*', '.*')
                right = right.replace('*', '.*')
                pattern = regex.compile(f'(?<={left}){middle}(?={right})')

                if pattern.match(axiom, pos=i):
                    axiom = axiom[:i] + replacement + axiom[i+len(middle):]
                    replaced = True
                    i += len(replacement) - 1
                    break
        if not replaced: # this is a context-free rule
            for context, replacement in rules.items():
                if context == axiom[i]:
                    axiom = axiom[:i] + replacement + axiom[i+1:]
                    i += len(replacement) - 1
                    break
        i += 1
    return axiom