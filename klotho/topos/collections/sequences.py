from itertools import cycle, combinations
from typing import List, Optional, Union, Any, TypeVar

import numpy as np

from klotho.topos.collections._pattern import (
    Cyclic,
    NodeSpec,
    _advance_runtime,
    _build_runtime,
    _compile_item,
    _reset_runtime,
    child_restore,
    child_snapshot,
)

T = TypeVar('T')

__all__ = [
    'Norg',
    'Pattern',
    'Cyclic',
]

class Norg:
    """Per Nørgård's "infinity" sequences.

    Provides static methods for generating various integer sequences devised
    by the Danish composer Per Nørgård, most notably the *infinity series*
    used extensively in his compositional practice.

    References
    ----------
    .. [1] https://web.archive.org/web/20071010091253/http://www.pernoergaard.dk/eng/strukturer/uendelig/uindhold.html

    Examples
    --------
    >>> Norg.inf(size=8)
    array([ 0,  1, -1,  2,  1,  0, -2,  3])
    """

    @staticmethod
    def inf(start: int = 0, size: int = 128, step: int = 1):
        """Generate the infinity series.

        When *start* is 0 and *step* is 1 an optimised pair-wise recurrence is
        used.  For arbitrary start/step combinations the series is computed
        element-wise via `inf_num`.

        Parameters
        ----------
        start : int, optional
            Index at which to begin the series (default is 0).
        size : int, optional
            Number of elements to generate (default is 128).
        step : int, optional
            Index step between successive elements (default is 1).

        Returns
        -------
        numpy.ndarray
            One-dimensional integer array of length *size*.

        References
        ----------
        .. [1] https://web.archive.org/web/20071010092334/http://www.pernoergaard.dk/eng/strukturer/uendelig/ukonstruktion05.html

        Examples
        --------
        >>> Norg.inf(size=8)
        array([ 0,  1, -1,  2,  1,  0, -2,  3])

        >>> Norg.inf(start=4, size=4)
        array([1, 0, -2, 3])
        """
        if start == 0 and step == 1:
            p = np.empty(size, dtype=int)
            p[0] = 0
            p[1] = 1
            for i in range(1, (size - 1) // 2 + 1):
                delta = p[i] - p[i - 1]
                if 2 * i < size:
                    p[2 * i] = p[2 * i - 2] - delta
                if 2 * i + 1 < size:
                    p[2 * i + 1] = p[2 * i - 1] + delta
            return p
        return np.array([Norg.inf_num(start + step * i) for i in range(size)])

    @staticmethod
    def inf_num(n):
        """Compute the *n*-th value of the infinity series.

        Uses the recursive definition: ``f(0) = 0``, ``f(2n) = -f(n)``,
        ``f(2n+1) = f(n) + 1``.

        Parameters
        ----------
        n : int
            Non-negative index into the infinity series.

        Returns
        -------
        int
            The value of the infinity series at position *n*.

        References
        ----------
        .. [1] https://arxiv.org/pdf/1402.3091.pdf

        Examples
        --------
        >>> Norg.inf_num(0)
        0
        >>> Norg.inf_num(7)
        3
        """
        if n == 0: return 0
        if n % 2 == 0:
            return -Norg.inf_num(n // 2)
        return Norg.inf_num((n - 1) // 2) + 1

    @staticmethod
    def n_partite(seed: list = [0,-2,-1], inv_pat: list = [-1,1,1], size: int = 128):
        """Generate a generalised *n*-partite infinity series.

        Extends the tripartite construction to an arbitrary seed length and
        inversion pattern, producing self-similar integer sequences by
        recursively applying delta-inversion rules.

        Parameters
        ----------
        seed : list of int, optional
            Initial values of the series (default is ``[0, -2, -1]``).
        inv_pat : list of int, optional
            Cyclic pattern of inversion multipliers applied to successive
            deltas (default is ``[-1, 1, 1]``).
        size : int, optional
            Number of elements to generate (default is 128).

        Returns
        -------
        numpy.ndarray
            One-dimensional integer array of length *size*.

        References
        ----------
        .. [1] https://web.archive.org/web/20071010091606/http://www.pernoergaard.dk/eng/strukturer/uendelig/u3.html

        Examples
        --------
        >>> Norg.n_partite(size=9)
        array([ 0, -2, -1,  2,  0, -1, -2,  0,  1])
        """
        seed_len = len(seed)
        p = np.empty(size, dtype=int)
        p[:seed_len] = seed
        inv_pat_cycle = cycle(inv_pat)
        for i in range(1, (size - 1) // seed_len + 1):
            delta = p[i] - p[i - 1]
            for j in range(seed_len):
                if seed_len * i + j < size:
                    p[seed_len * i + j] = p[seed_len * i + j - seed_len] + next(inv_pat_cycle) * delta
        return p

    @staticmethod
    def lake():
        """Generate Nørgård's *tone lake* sequence.

        .. note:: Not yet implemented.

        Returns
        -------
        None

        References
        ----------
        .. [1] https://web.archive.org/web/20071010093955/http://www.pernoergaard.dk/eng/strukturer/toneso/tkonstruktion.html
        """
        pass


class Pattern:
    """Cyclical pattern iterator built from nested structure and delegates."""

    def __init__(self, iterable, end=False):
        self._iterable = iterable
        self._end = end
        self._spec = _compile_item(iterable)
        self._pattern_length = self._spec.period
        self._root = _build_runtime(self._spec, iterable)
        self._current = 0
        self._period_cache: Optional[tuple[Any, ...]] = None

    @property
    def length(self) -> int:
        return self._pattern_length

    @property
    def spec(self) -> NodeSpec:
        return self._spec

    @property
    def pattern(self):
        return self._iterable

    @property
    def end(self):
        return self._end

    @property
    def position(self) -> int:
        return self._current

    def reset(self):
        self._current = 0
        _reset_runtime(self._root)
        self._period_cache = None

    def materialize_period(self) -> tuple[Any, ...]:
        if self._period_cache is None:
            snap = self._snapshot()
            try:
                self._period_cache = tuple(self._next_value() for _ in range(self._pattern_length))
            finally:
                self._restore(snap)
        return self._period_cache

    def _snapshot(self):
        return {
            'current': self._current,
            'root': child_snapshot(self._root),
        }

    def _restore(self, state):
        self._current = state['current']
        child_restore(self._root, state['root'])

    def _next_value(self):
        if self._current >= self._pattern_length and self._end:
            return next(self._end) if isinstance(self._end, Pattern) else self._end
        value = _advance_runtime(self._root)
        self._current += 1
        return value

    def __iter__(self):
        return self

    def __next__(self):
        return self._next_value()

    def __len__(self):
        return self._pattern_length

    def __str__(self):
        return str(list(self._iterable)) if isinstance(self._iterable, list) else str(self._iterable)

    def __repr__(self):
        return f"Pattern({self._iterable!r}, end={self._end!r})"

    @staticmethod
    def from_random(
        elements: List[T],
        length: int = 5,
        max_nesting_level: int = 3,
        max_inner_length: int = 3,
        weights: Optional[List[float]] = None,
        nesting_probability: float = 0.333,
    ) -> 'Pattern':
        from klotho.utils.algorithms.lists import normalize_sum

        if weights is not None:
            if len(weights) != len(elements):
                raise ValueError("Length of weights must match length of elements")
            normalized_weights = normalize_sum(weights)
        else:
            normalized_weights = [1.0 / len(elements)] * len(elements)

        def _generate_structure(target_length: int, current_nesting_level: int) -> List[Union[T, List[Any]]]:
            structure = []
            for _ in range(target_length):
                if max_inner_length > 0 and current_nesting_level > 0 and np.random.random() < nesting_probability:
                    nested_length = np.random.randint(2, max_inner_length + 1)
                    nested_structure = _generate_structure(nested_length, current_nesting_level - 1)
                    structure.append(nested_structure)
                else:
                    index = np.random.choice(len(elements), p=normalized_weights)
                    structure.append(elements[index])
            return structure

        return Pattern(_generate_structure(length, max_nesting_level))


# class Golomb:

#     def __init__(self, length: int, order: int, *, reflections=False):
#         self._length = length
#         self._order = order
#         self._reflections = reflections
#         self._rulers = self._golomb_rulers_of_length(length, order, reflections=reflections)

#     def _is_golomb_ruler(marks):
#         diffs = set()

#         for i in range(len(marks)):
#             for j in range(i + 1, len(marks)):
#                 d = marks[j] - marks[i]
#                 if d in diffs:
#                     return False
#                 diffs.add(d)

#         return True

#     def _golomb_rulers_of_length(length, order, *, reflections=True):
#         if order < 1:
#             raise ValueError("order must be >= 1")

#         if order == 1:
#             return [[0]] if length == 0 else []

#         if order == 2:
#             return [[0, length]] if length > 0 else []

#         rulers = []

#         for interior in combinations(range(1, length), order - 2):
#             marks = [0, *interior, length]

#             if not _is_golomb_ruler(marks):
#                 continue

#             if not reflections:
#                 reflected = [length - x for x in reversed(marks)]
#                 if marks > reflected:
#                     continue

#             rulers.append(marks)

#         return rulers
