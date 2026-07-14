"""
Formal grammars: L-systems, rewriting, derivation trees, and interpreters.

The core apparatus is graded — ``RewriteSystem({'A': 'AB', 'B': 'A'},
axiom='A').generate(5)`` works with nothing else configured; alphabets,
weighted rules, brackets, constraints, and mutation are opt-in layers.
"""

from .alphabet import Alphabet
from .rules import RuleSet
from .rewriting import (
    RewriteSystem, History,
    balance_brackets, bracket_depth,
    show_generations, word_stats,
    rand_rules, constrain_rules, apply_rules, gen_str,
)
from .derivation import DerivationTree, derive
from .interpreter import Interpreter, State
from .markov import markov_walk

__all__ = [
    'Alphabet',
    'RuleSet',
    'RewriteSystem',
    'History',
    'DerivationTree',
    'derive',
    'Interpreter',
    'State',
    'markov_walk',
    'balance_brackets',
    'bracket_depth',
    'show_generations',
    'word_stats',
    'rand_rules',
    'constrain_rules',
    'apply_rules',
    'gen_str',
]
