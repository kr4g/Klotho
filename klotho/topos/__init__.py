'''
--------------------------------------------------------------------------------------
The following description is based on the Preface from "The Topos of Music" by Guerino 
Mazzola

see:  https://link.springer.com/book/10.1007/978-3-0348-8141-8

***

This module deals with the topos, the very concept of music.

The name *topos* has been chosen to commicate a double message:

First, the Greek word "topos" alludes to the logical and transcendental location of 
the concept of music in the sense of Aristotle's and Kant's topic.

The second message is intimately entwined with the first since the present concept
framework of the musical sign system is technically based on topos theory, so the
topos of music recieves its topos-theoretica foundation.  In this perspective, the
the double message of this module's title in fact condenses to a unified intention: 

to unite philosphical insight with mathematical explicitness.
--------------------------------------------------------------------------------------
'''
from . import collections
from . import formal_grammars
from . import graphs

from .collections import patterns, sequences, sets, Pattern, CombinationSet, PartitionSet
from .collections import autoref, autoref_rotmat, permut_list

from .formal_grammars import alphabets, grammars

from .graphs import trees, Graph, Tree, Lattice

__all__ = [
    # Classes
    'Pattern', 'CombinationSet', 'PartitionSet',
    'Tree', 'Graph', 'Lattice',
    
    # Functions
    'autoref', 'autoref_rotmat', 'permut_list',
    'patterns', 'sequences', 'sets',
    'alphabets', 'grammars',
    'trees',
]
