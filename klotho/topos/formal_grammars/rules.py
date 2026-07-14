"""
Production rule sets for rewriting systems.

A :class:`RuleSet` maps symbols to right-hand sides. RHS forms are
auto-detected:

- a plain word — ``'AB'`` or a token tuple ``('d', 't')`` — is deterministic;
- a list of ``(weight, word)`` options — ``[(3.0, 'A'), (1.0, 'BB')]`` — is
  stochastic (a probabilistic context-free grammar).

Rule sets work over **strings** (each character a token) or **token
sequences** (tuples/lists of strings, for multi-character tokens like
``'V/II'``). The mode is detected from the RHS types and stored normalized.

Rule sets are value-like: :meth:`constrain`, :meth:`require`, and
:meth:`mutate` return new rule sets rather than mutating in place.
"""

import random as _random
from collections.abc import Mapping

from .alphabet import Alphabet

__all__ = ['RuleSet']


def _coerce_rng(rng):
    if rng is None or rng is _random:
        return _random
    if isinstance(rng, _random.Random):
        return rng
    return _random.Random(rng)


def _is_weighted_options(rhs):
    if not isinstance(rhs, (list, tuple)) or not rhs:
        return False
    return all(
        isinstance(option, (list, tuple)) and len(option) == 2
        and isinstance(option[0], (int, float)) and not isinstance(option[0], bool)
        and isinstance(option[1], (str, list, tuple))
        for option in rhs
    )


class RuleSet(Mapping):
    """
    A mapping from symbols to production rule right-hand sides.

    Parameters
    ----------
    rules : dict or RuleSet
        Mapping of symbol to RHS. An RHS may be a plain word (``str`` or
        tuple/list of tokens) or a list of ``(weight, word)`` options.
    alphabet : Alphabet or iterable of str, optional
        The alphabet the rules operate over. Enables bracket-aware behavior
        (constraints and mutations respect branching) and supplies the symbol
        pool for :meth:`mutate`.

    Examples
    --------
    >>> rules = RuleSet({'A': 'AB', 'B': 'A'})
    >>> rules['A']
    'AB'

    >>> pcfg = RuleSet({'t': [(4.0, ('t',)), (2.5, ('d', 't'))]})
    >>> pcfg.is_stochastic
    True
    """

    def __init__(self, rules, alphabet=None):
        if isinstance(alphabet, Alphabet) or alphabet is None:
            self._alphabet = alphabet
        else:
            self._alphabet = Alphabet(alphabet)
        if isinstance(rules, RuleSet):
            if self._alphabet is None:
                self._alphabet = rules._alphabet
            self._rules = dict(rules._rules)
            self._token_mode = rules._token_mode
            return

        normalized = {}
        token_mode = False
        for symbol, rhs in dict(rules).items():
            options = self._normalize_rhs(rhs)
            if any(isinstance(word, tuple) for _, word in options):
                token_mode = True
            normalized[symbol] = options

        if token_mode:
            normalized = {
                symbol: tuple(
                    (w, word if isinstance(word, tuple) else (word,))
                    for w, word in options
                )
                for symbol, options in normalized.items()
            }

        self._rules = normalized
        self._token_mode = token_mode

    @staticmethod
    def _normalize_rhs(rhs):
        if _is_weighted_options(rhs):
            options = []
            for weight, word in rhs:
                if isinstance(word, (list, tuple)):
                    word = tuple(word)
                options.append((float(weight), word))
            return tuple(options)
        if isinstance(rhs, (list, tuple)):
            return ((1.0, tuple(rhs)),)
        if isinstance(rhs, str):
            return ((1.0, rhs),)
        raise TypeError(f"Invalid RHS for rule: {rhs!r}")

    def _replace(self, rules):
        new = RuleSet.__new__(RuleSet)
        new._alphabet = self._alphabet
        new._rules = rules
        new._token_mode = self._token_mode
        return new

    # ------------------------------------------------------------------
    # Mapping protocol
    # ------------------------------------------------------------------
    def __getitem__(self, symbol):
        options = self._rules[symbol]
        if len(options) == 1:
            return options[0][1]
        return [(w, word) for w, word in options]

    def __iter__(self):
        return iter(self._rules)

    def __len__(self):
        return len(self._rules)

    @property
    def alphabet(self):
        """Alphabet or None : The alphabet these rules operate over."""
        return self._alphabet

    @property
    def token_mode(self):
        """bool : True when rules operate over token sequences rather than strings."""
        return self._token_mode

    @property
    def is_stochastic(self):
        """bool : True when any symbol has more than one weighted option."""
        return any(len(options) > 1 for options in self._rules.values())

    def options(self, symbol):
        """All ``(weight, word)`` options for *symbol* (empty for unknown symbols)."""
        return list(self._rules.get(symbol, ()))

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    def sample(self, symbol, rng=None):
        """
        Draw an expansion for *symbol* (weighted choice for stochastic rules).

        Returns ``None`` for symbols with no rule.
        """
        options = self._rules.get(symbol)
        if options is None:
            return None
        if len(options) == 1:
            return options[0][1]
        rng = _coerce_rng(rng)
        words = [word for _, word in options]
        weights = [w for w, _ in options]
        return rng.choices(words, weights=weights)[0]

    def rewrite(self, word, rng=None):
        """
        Apply one parallel rewrite pass to *word*.

        Tokens with no rule map to themselves. Returns a ``str`` when given
        a string, otherwise a tuple of tokens.
        """
        rng = _coerce_rng(rng)
        out = []
        for token in word:
            expansion = self.sample(token, rng)
            if expansion is None:
                out.append(token)
            else:
                out.extend(expansion)
        if isinstance(word, str) and not self._token_mode:
            return ''.join(out)
        return tuple(out)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def random(cls, alphabet, word_length=(1, 3), branch_probability=0.0,
               branch_requires=None, constrain=None, rng=None):
        """
        Generate a random deterministic rule set over *alphabet*.

        Each variable gets a random word; constants (and bracket symbols)
        map to themselves. When the alphabet has brackets and
        ``branch_probability > 0``, a rule may have one random sub-word
        wrapped in a matched bracket pair; brackets only ever enter as
        matched pairs, so generated words stay balanced by construction.

        Parameters
        ----------
        alphabet : Alphabet or iterable of str
            Symbol inventory. A plain iterable is treated as all-variables.
        word_length : int or (min, max) tuple, optional
            Length range for random words. Default is ``(1, 3)``.
        branch_probability : float, optional
            Per-rule probability of wrapping a sub-word in brackets.
        branch_requires : str, optional
            When set, every bracketed sub-word is guaranteed to contain at
            least one occurrence of this symbol.
        constrain : dict, optional
            ``{symbol: required}`` constraints applied to the generated
            rules. Exactly equivalent to calling
            ``RuleSet.random(..., rng=rng).constrain(constrain, rng=rng)``.
        rng : random.Random or int, optional
            Source of randomness (or a seed).

        Returns
        -------
        RuleSet
        """
        if not isinstance(alphabet, Alphabet):
            alphabet = Alphabet(alphabet)
        constrain_rng = rng          # the raw argument, so the constrain pass
        rng = _coerce_rng(rng)       # matches a separate .constrain(..., rng=rng) call
        if isinstance(word_length, int):
            lo, hi = word_length, word_length
        else:
            lo, hi = word_length
        pool = list(alphabet.symbols)
        if not pool:
            raise ValueError("alphabet has no symbols")

        rules = {}
        for symbol in alphabet.variables:
            length = rng.randint(lo, hi)
            word = [rng.choice(pool) for _ in range(length)]
            if (alphabet.brackets is not None and branch_probability > 0
                    and len(word) >= 2 and rng.random() < branch_probability):
                open_, close_ = alphabet.brackets
                i = rng.randint(0, len(word) - 2)
                j = rng.randint(i + 1, len(word) - 1)
                inner = word[i:j]
                if branch_requires is not None and branch_requires not in inner:
                    k = rng.randrange(len(inner))
                    inner[k] = branch_requires
                word = word[:i] + [open_] + inner + [close_] + word[j:]
            rules[symbol] = word
        for symbol in alphabet.constants:
            rules[symbol] = [symbol]
        if alphabet.brackets is not None:
            open_, close_ = alphabet.brackets
            rules[open_] = [open_]
            rules[close_] = [close_]

        string_mode = all(isinstance(s, str) and len(s) == 1 for s in pool) and (
            alphabet.brackets is None
            or all(len(b) == 1 for b in alphabet.brackets)
        )
        if string_mode:
            rules = {symbol: ''.join(word) for symbol, word in rules.items()}
        ruleset = cls(rules, alphabet=alphabet)
        if constrain is not None:
            ruleset = ruleset.constrain(constrain, rng=constrain_rng)
        return ruleset

    # ------------------------------------------------------------------
    # Bracket-aware word surgery
    # ------------------------------------------------------------------
    def _brackets(self):
        return self._alphabet.brackets if self._alphabet is not None else None

    def _stem_positions(self, word):
        """Indices of depth-0, non-bracket tokens in *word*."""
        brackets = self._brackets()
        if brackets is None:
            return list(range(len(word)))
        open_, close_ = brackets
        positions = []
        depth = 0
        for i, token in enumerate(word):
            if token == open_:
                depth += 1
            elif token == close_:
                depth -= 1
            elif depth == 0:
                positions.append(i)
        return positions

    @staticmethod
    def _set_token(word, index, token):
        if isinstance(word, str):
            return word[:index] + token + word[index + 1:]
        return word[:index] + (token,) + word[index + 1:]

    @staticmethod
    def _append_token(word, token):
        if isinstance(word, str):
            return word + token
        return word + (token,)

    def constrain(self, constraints, rng=None):
        """
        Guarantee that each rule contains its required symbol on the stem.

        For every ``{symbol: required}`` pair, each option of
        ``rules[symbol]`` is checked for *required* at bracket depth 0 (the
        stem); if absent, a random stem token is replaced with it (or it is
        appended when the stem is empty).

        Parameters
        ----------
        constraints : dict
            Mapping of symbol to required symbol.
        rng : random.Random or int, optional
            Source of randomness (or a seed).

        Returns
        -------
        RuleSet
            A new rule set; the original is unchanged.
        """
        rng = _coerce_rng(rng)
        rules = dict(self._rules)
        for symbol, required in constraints.items():
            options = rules.get(symbol)
            if options is None:
                continue
            new_options = []
            for weight, word in options:
                stem = self._stem_positions(word)
                if any(word[i] == required for i in stem):
                    new_options.append((weight, word))
                elif stem:
                    index = rng.choice(stem)
                    new_options.append((weight, self._set_token(word, index, required)))
                else:
                    new_options.append((weight, self._append_token(word, required)))
            rules[symbol] = tuple(new_options)
        return self._replace(rules)

    def require(self, symbol, required, min_count=1, rng=None):
        """
        Guarantee at least *min_count* occurrences of *required* on the stem
        of ``rules[symbol]``.

        Parameters
        ----------
        symbol : str
            The rule whose RHS is checked.
        required : str
            The symbol that must appear on the stem (bracket depth 0).
        min_count : int, optional
            Minimum number of stem occurrences. Default is 1.
        rng : random.Random or int, optional
            Source of randomness (or a seed).

        Returns
        -------
        RuleSet
            A new rule set; the original is unchanged.
        """
        rng = _coerce_rng(rng)
        options = self._rules.get(symbol)
        if options is None:
            raise KeyError(f"No rule for symbol {symbol!r}")
        new_options = []
        for weight, word in options:
            while True:
                stem = self._stem_positions(word)
                count = sum(1 for i in stem if word[i] == required)
                if count >= min_count:
                    break
                other = [i for i in stem if word[i] != required]
                if other:
                    word = self._set_token(word, rng.choice(other), required)
                else:
                    word = self._append_token(word, required)
            new_options.append((weight, word))
        rules = dict(self._rules)
        rules[symbol] = tuple(new_options)
        return self._replace(rules)

    def mutate(self, probability, rng=None):
        """
        Randomly mutate rule words.

        Each rule mutates with the given probability by replacing one random
        non-bracket token with a random alphabet symbol. Bracket symbols
        never mutate and mutations never insert brackets, so words generated
        by the mutated rules stay balanced.

        Parameters
        ----------
        probability : float
            Per-rule mutation probability.
        rng : random.Random or int, optional
            Source of randomness (or a seed).

        Returns
        -------
        RuleSet
            A new rule set; the original is unchanged.
        """
        rng = _coerce_rng(rng)
        brackets = self._brackets()
        bracket_set = set(brackets) if brackets is not None else set()
        if self._alphabet is not None:
            pool = list(self._alphabet.symbols)
        else:
            pool = [s for s in self._rules if s not in bracket_set]
        if not pool:
            return self._replace(dict(self._rules))

        rules = {}
        for symbol, options in self._rules.items():
            if symbol in bracket_set:
                rules[symbol] = options
                continue
            new_options = []
            for weight, word in options:
                if rng.random() < probability:
                    positions = [i for i, token in enumerate(word)
                                 if token not in bracket_set]
                    if positions:
                        index = rng.choice(positions)
                        word = self._set_token(word, index, rng.choice(pool))
                new_options.append((weight, word))
            rules[symbol] = tuple(new_options)
        return self._replace(rules)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    @staticmethod
    def _format_word(word, formatter=None):
        if formatter is not None:
            return ' '.join(formatter(token) for token in word)
        if isinstance(word, str):
            return word
        return ' '.join(str(token) for token in word)

    def _format(self, formatter=None):
        lines = []
        for symbol, options in self._rules.items():
            head = formatter(symbol) if formatter is not None else str(symbol)
            if len(options) == 1:
                lines.append(f"{head} → {self._format_word(options[0][1], formatter)}")
            else:
                rhs = ' | '.join(
                    f"{self._format_word(word, formatter)} ({weight:g})"
                    for weight, word in options
                )
                lines.append(f"{head} → {rhs}")
        return '\n'.join(lines)

    def show(self, formatter=None, title='Rewrite Rules'):
        """Print the rules, one per line, optionally formatting tokens."""
        if title:
            print(title)
        body = self._format(formatter)
        if body:
            print('\n'.join(f"  {line}" for line in body.split('\n')))

    def __str__(self):
        return self._format()

    def __repr__(self):
        mode = 'tokens' if self._token_mode else 'string'
        kind = 'stochastic' if self.is_stochastic else 'deterministic'
        return f"RuleSet({len(self._rules)} rules, {kind}, {mode})"
