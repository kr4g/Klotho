"""
Parallel rewriting systems (L-systems).

:class:`RewriteSystem` drives repeated parallel rewriting of a word from an
axiom through a :class:`~klotho.topos.formal_grammars.rules.RuleSet`. The
minimal use needs nothing but rules and an axiom::

    RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A').generate(5)

Alphabets, weighted rules, brackets, word limits, and mutation are opt-in
layers on top.

Context-sensitive rules (predecessor/successor context matching) are out of
scope for now; the RuleSet key shape can grow keys like ``('A', '<', 'B')``
later without breaking.
"""

from collections import Counter
from collections.abc import Sequence

from .alphabet import Alphabet, DEFAULT_BRACKETS
from .rules import RuleSet, _coerce_rng

__all__ = [
    'RewriteSystem', 'History',
    'balance_brackets', 'bracket_depth',
    'show_generations', 'word_stats',
    'rand_rules', 'constrain_rules', 'apply_rules', 'gen_str',
]


class History(Sequence):
    """
    The generations produced by :meth:`RewriteSystem.generate`.

    Indexing returns words by generation (index 0 is the axiom).
    ``history.rules[i]`` is the rule-set snapshot at generation *i* — when
    mutation is active the rules evolve between generations, and the
    snapshots record that evolution.

    Attributes
    ----------
    words : list
        One word per generation.
    rules : list of RuleSet
        Rule-set snapshot per generation.
    """

    def __init__(self, words, rules):
        self.words = list(words)
        self.rules = list(rules)

    def __getitem__(self, index):
        return self.words[index]

    def __len__(self):
        return len(self.words)

    @property
    def final(self):
        """The last generation's word."""
        return self.words[-1]

    def __repr__(self):
        return f"History({len(self.words)} generations)"


class RewriteSystem:
    """
    A parallel rewriting system: rules plus an axiom.

    Parameters
    ----------
    rules : dict or RuleSet
        Production rules (a raw dict is coerced to :class:`RuleSet`).
    axiom : str or sequence of str
        The starting word.
    alphabet : Alphabet or iterable of str, optional
        Symbol inventory; enables bracket-aware behavior.
    rng : random.Random or int, optional
        Source of randomness (or a seed) for stochastic rules and mutation.

    Examples
    --------
    >>> system = RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A')
    >>> system.generate(3).final
    'ABAAB'
    """

    def __init__(self, rules, axiom, alphabet=None, rng=None):
        if isinstance(rules, RuleSet):
            self._rules = rules if alphabet is None else RuleSet(rules, alphabet=alphabet)
        else:
            self._rules = RuleSet(rules, alphabet=alphabet)
        self._axiom = axiom
        self._rng = _coerce_rng(rng)

    @property
    def rules(self):
        """RuleSet : The production rules."""
        return self._rules

    @property
    def axiom(self):
        """The starting word."""
        return self._axiom

    @property
    def alphabet(self):
        """Alphabet or None : The alphabet, if one was provided."""
        return self._rules.alphabet

    def step(self, word):
        """One parallel rewrite of *word* (unknown tokens map to themselves)."""
        return self._rules.rewrite(word, rng=self._rng)

    def generate(self, generations, word_limit=None, mutation=0.0):
        """
        Run repeated rewriting from the axiom.

        Parameters
        ----------
        generations : int
            Number of rewrite passes.
        word_limit : int, optional
            Maximum word length per generation. When a cut lands mid-branch
            (the alphabet has brackets), the word is re-balanced so brackets
            stay matched.
        mutation : float, optional
            Per-generation rule mutation probability. When greater than 0,
            the rules mutate between generations and each generation's
            rule-set snapshot is recorded in the returned history.

        Returns
        -------
        History
            The words (and rule snapshots) of every generation, index 0
            being the axiom. The system's own rules are not modified.
        """
        brackets = None
        if self.alphabet is not None:
            brackets = self.alphabet.brackets

        rules = self._rules
        word = self._axiom
        words = [word]
        snapshots = [rules]
        for _ in range(generations):
            word = rules.rewrite(word, rng=self._rng)
            if word_limit is not None and len(word) > word_limit:
                if brackets is not None:
                    cut = word_limit
                    capped = balance_brackets(word[:cut], brackets)
                    while len(capped) > word_limit and cut > 0:
                        cut -= len(capped) - word_limit
                        capped = balance_brackets(word[:cut], brackets)
                    word = capped
                else:
                    word = word[:word_limit]
            words.append(word)
            if mutation > 0:
                rules = rules.mutate(mutation, rng=self._rng)
            snapshots.append(rules)
        return History(words, snapshots)

    def grow(self, generations, word_limit=None):
        """
        Run repeated rewriting and return only the final word.

        Shorthand for ``generate(generations, word_limit).final`` when the
        intermediate generations aren't needed.

        Parameters
        ----------
        generations : int
            Number of rewrite passes.
        word_limit : int, optional
            Maximum word length per generation (see :meth:`generate`).

        Returns
        -------
        str or tuple
            The last generation's word.

        Examples
        --------
        >>> RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A').grow(3)
        'ABAAB'
        """
        return self.generate(generations, word_limit=word_limit).final

    def __repr__(self):
        return f"RewriteSystem(axiom={self._axiom!r}, {self._rules!r})"


# ----------------------------------------------------------------------
# Bracket utilities
# ----------------------------------------------------------------------
def balance_brackets(word, brackets=DEFAULT_BRACKETS):
    """
    Drop orphaned closers and close any brackets left open.

    Needed after a hard length cut, which can land mid-branch.

    Parameters
    ----------
    word : str or sequence of str
        The word to balance.
    brackets : (open, close) pair, optional
        The bracket pair. Default is ``('[', ']')``.

    Returns
    -------
    str or tuple
        The balanced word (same kind as the input).
    """
    open_, close_ = brackets
    out = []
    depth = 0
    for token in word:
        if token == open_:
            depth += 1
        elif token == close_:
            if depth == 0:
                continue
            depth -= 1
        out.append(token)
    out.extend([close_] * depth)
    if isinstance(word, str):
        return ''.join(out)
    return tuple(out)


def bracket_depth(word, brackets=DEFAULT_BRACKETS):
    """
    Maximum bracket nesting depth of *word*.

    Parameters
    ----------
    word : str or sequence of str
        The word to measure.
    brackets : (open, close) pair, optional
        The bracket pair. Default is ``('[', ']')``.

    Returns
    -------
    int
    """
    open_, close_ = brackets
    depth = 0
    max_depth = 0
    for token in word:
        if token == open_:
            depth += 1
            max_depth = max(max_depth, depth)
        elif token == close_:
            depth -= 1
    return max_depth


# ----------------------------------------------------------------------
# Diagnostics
# ----------------------------------------------------------------------
def _iter_generations(history):
    if isinstance(history, dict):
        return sorted(history.items())
    return list(enumerate(history))


def show_generations(history, formatter=None, max_chars=120):
    """
    Print one line per generation, truncating long words.

    Parameters
    ----------
    history : History, list, or dict
        Generations to display.
    formatter : callable, optional
        Per-token formatter; when given, tokens are joined with spaces.
    max_chars : int, optional
        Maximum characters per line before truncation. Default is 120.
    """
    items = _iter_generations(history)
    if not items:
        return
    width = len(str(items[-1][0]))
    for gen, word in items:
        text = RuleSet._format_word(word, formatter)
        if len(text) > max_chars:
            text = f"{text[:max_chars]}… (+{len(word) - max_chars:,} more)"
        print(f"Gen {gen:>{width}} : {text}")


def word_stats(word, alphabet=None):
    """
    Token statistics for a word.

    Parameters
    ----------
    word : str or sequence of str
        The word to analyze.
    alphabet : Alphabet or iterable of str, optional
        When given, the result includes the alphabet symbols missing from
        the word.

    Returns
    -------
    dict
        Keys: ``length``, ``counts`` (per-token occurrence counts),
        ``distribution`` (normalized counts), and — when an alphabet is
        given — ``missing`` (sorted list of absent symbols).
    """
    counts = Counter(word)
    total = len(word)
    stats = {
        'length': total,
        'counts': dict(counts),
        'distribution': {token: count / total for token, count in counts.items()} if total else {},
    }
    if alphabet is not None:
        symbols = set(alphabet.symbols) if isinstance(alphabet, Alphabet) else set(alphabet)
        stats['missing'] = sorted(symbols - set(counts))
    return stats


# ----------------------------------------------------------------------
# Legacy API (delegates to the classes above)
# ----------------------------------------------------------------------
def rand_rules(symbols, word_length_min=1, word_length_max=3):
    """Legacy: random deterministic rules as a plain dict."""
    ruleset = RuleSet.random(Alphabet(symbols),
                             word_length=(word_length_min, word_length_max))
    return {symbol: ruleset[symbol] for symbol in symbols}


def constrain_rules(rules, constraints):
    """Legacy: enforce constraints on a plain rules dict (in place)."""
    constrained = RuleSet(rules).constrain(constraints)
    for symbol in rules:
        rules[symbol] = constrained[symbol]
    return rules


def apply_rules(rules, axiom):
    """Legacy: one parallel rewrite pass (unknown tokens map to themselves)."""
    return RuleSet(rules).rewrite(axiom)


def gen_str(generations=0, axiom='', rules=None, display=False):
    """Legacy: generate a ``{generation: word}`` dict from an axiom."""
    history = RewriteSystem(rules or {}, axiom).generate(generations)
    gen_dict = {i: word for i, word in enumerate(history)}
    if display:
        show_generations(gen_dict)
    return gen_dict
