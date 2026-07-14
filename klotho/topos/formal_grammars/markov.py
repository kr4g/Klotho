"""
Weighted random walks over transition tables.
"""

from .rules import _coerce_rng

__all__ = ['markov_walk']


def markov_walk(table, start=None, length=16, rng=None):
    """
    Walk a first-order Markov chain.

    Parameters
    ----------
    table : dict
        Mapping of state to ``{next_state: weight}`` transition options.
    start : hashable, optional
        Starting state. Defaults to a random key of *table*.
    length : int, optional
        Total path length (including the start). Default is 16.
    rng : random.Random or int, optional
        Source of randomness (or a seed).

    Returns
    -------
    list
        The visited states, starting with *start*.

    Examples
    --------
    >>> table = {0: {3: 6, 4: 6}, 3: {4: 6, 0: 3}, 4: {0: 6, 3: 3}}
    >>> path = markov_walk(table, start=0, length=8)
    """
    rng = _coerce_rng(rng)
    if start is None:
        start = rng.choice(list(table))
    path = [start]
    for _ in range(length - 1):
        options = table[path[-1]]
        states = list(options)
        weights = list(options.values())
        path.append(rng.choices(states, weights=weights)[0])
    return path
