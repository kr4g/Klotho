"""
Alphabets for rewriting systems.

An :class:`Alphabet` declares the symbol inventory of an L-system or other
string/token rewriting system: which symbols carry production rules
(*variables*), which rewrite to themselves (*constants*), and whether a pair
of bracket symbols carries branching semantics.
"""

DEFAULT_BRACKETS = ('[', ']')

__all__ = ['Alphabet', 'DEFAULT_BRACKETS']


def _normalize_brackets(brackets):
    """Normalize a brackets argument to ``None`` or an ``(open, close)`` pair."""
    if brackets is None or brackets is False:
        return None
    if brackets is True:
        return DEFAULT_BRACKETS
    open_, close_ = brackets
    if open_ == close_:
        raise ValueError("bracket symbols must be distinct")
    return (open_, close_)


class Alphabet:
    """
    The symbol inventory of a rewriting system.

    Parameters
    ----------
    variables : iterable of str
        Symbols that carry production rules.
    constants : iterable of str, optional
        Symbols that always rewrite to themselves.
    brackets : None, True, or (open, close) pair, optional
        ``None`` (default) gives brackets no special treatment: ``'['`` and
        ``']'`` are ordinary symbols. ``True`` enables branching semantics
        with the default pair ``('[', ']')``. Any two distinct symbols may
        be given as a custom pair.

    Examples
    --------
    >>> a = Alphabet('AB')
    >>> a.symbols
    ('A', 'B')

    >>> a = Alphabet(['p', '+', '-'], constants=['.'], brackets=True)
    >>> a.brackets
    ('[', ']')
    """

    def __init__(self, variables, constants=(), brackets=None):
        self._variables = tuple(variables)
        self._constants = tuple(constants)
        self._brackets = _normalize_brackets(brackets)
        overlap = set(self._variables) & set(self._constants)
        if overlap:
            raise ValueError(f"symbols cannot be both variable and constant: {sorted(overlap)}")

    @property
    def variables(self):
        """tuple of str : Symbols with production rules."""
        return self._variables

    @property
    def constants(self):
        """tuple of str : Symbols that rewrite to themselves."""
        return self._constants

    @property
    def brackets(self):
        """tuple or None : The ``(open, close)`` branching pair, if enabled."""
        return self._brackets

    @property
    def symbols(self):
        """tuple of str : Union of variables and constants (excluding brackets)."""
        return self._variables + self._constants

    def __contains__(self, symbol):
        if symbol in self._variables or symbol in self._constants:
            return True
        return self._brackets is not None and symbol in self._brackets

    def __iter__(self):
        return iter(self.symbols)

    def __len__(self):
        return len(self._variables) + len(self._constants)

    def validate(self, word):
        """
        Check that every token in *word* belongs to this alphabet.

        Parameters
        ----------
        word : str or sequence of str
            The word to validate.

        Returns
        -------
        bool
        """
        return all(token in self for token in word)

    def __repr__(self):
        parts = [f"variables={list(self._variables)}"]
        if self._constants:
            parts.append(f"constants={list(self._constants)}")
        if self._brackets is not None:
            parts.append(f"brackets={self._brackets}")
        return f"Alphabet({', '.join(parts)})"
