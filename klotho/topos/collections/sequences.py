import numpy as np
from collections.abc import Iterable
from itertools import cycle
from math import lcm
from typing import List, Optional, Union, Any, TypeVar

T = TypeVar('T')
from klotho.utils.algorithms.lists import normalize_sum

__all__ = [
    'Norg',
    'Pattern',
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
    """Cyclical pattern iterator built from arbitrarily nested iterables.

    Converts a (possibly nested) iterable into a set of cycling iterators
    whose combined period equals the least common multiple of the lengths
    at every nesting level.  Once the full pattern period has been
    exhausted, subsequent calls to ``__next__`` return *end* (or delegate
    to *end* if it is itself a ``Pattern``).

    Parameters
    ----------
    iterable : Iterable
        A (possibly nested) iterable defining the cyclic pattern.
    end : object or Pattern, optional
        Value returned after the pattern period is exhausted.  If another
        ``Pattern`` is supplied its ``__next__`` is called instead
        (default is ``False``, meaning the pattern simply repeats *end*).

    Examples
    --------
    >>> p = Pattern([1, [2, 3]])
    >>> [next(p) for _ in range(6)]
    [1, 2, 1, 3, 1, 2]
    """

    def __init__(self, iterable, end=False):
        """Initialise the pattern from a nested iterable.

        Parameters
        ----------
        iterable : Iterable
            Source structure defining the cyclic pattern.
        end : object or Pattern, optional
            Sentinel returned once the LCM-period is exceeded
            (default is ``False``).
        """
        self._iterable = iterable
        self._cycles, self._pattern_length = self._create_cycles(iterable)
        self._end = end
        self._current = 0
        
    @property
    def length(self):
        """int : Total pattern length (LCM of all nesting-level lengths)."""
        return self._pattern_length
    
    @property
    def pattern(self):
        """Iterable : The original nested iterable used to build this pattern."""
        return self._iterable
    
    @property
    def end(self):
        """object or Pattern : Value returned after the pattern period is exhausted."""
        return self._end
        
    def _create_cycles(self, item):
        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            sub_results = [self._create_cycles(subitem) for subitem in item]
            subcycles, lengths = zip(*sub_results)
            this_level_length = len(item)
            nested_lengths = [this_level_length * length for length in lengths if length > 0]
            total_length = lcm(*nested_lengths) if nested_lengths else this_level_length
            return cycle(subcycles), total_length
        return item, 1

    def __iter__(self):
        return self

    def __next__(self):
        if self._current >= self._pattern_length and self._end:
            return next(self._end) if isinstance(self._end, Pattern) else self._end
        self._current += 1
        return self._get_next(self._cycles)

    def _get_next(self, cyc):
        item = next(cyc)
        while isinstance(item, cycle):
            item = self._get_next(item)
        return item
    
    def __len__(self):
        return self._pattern_length
    
    def __str__(self):
        return str(list(self._iterable))

    def __repr__(self):
        return self.__str__()
    
    @staticmethod
    def from_random(elements: List[T], 
                    length: int = 5,
                    max_nesting_level: int = 3,
                    max_inner_length: int = 3,
                    weights: Optional[List[float]] = None,
                    nesting_probability: float = 0.333) -> 'Pattern':
        """Create a ``Pattern`` with a randomly generated nested structure.

        Elements are drawn from *elements* according to *weights*, and
        nesting is introduced stochastically up to *max_nesting_level*
        deep.

        Parameters
        ----------
        elements : list of T
            Pool of values that may appear as leaves in the pattern.
        length : int, optional
            Number of items at the top level of the generated structure
            (default is 5).
        max_nesting_level : int, optional
            Maximum depth of nesting allowed (default is 3).
        max_inner_length : int, optional
            Maximum number of items in any nested sub-list (default is 3).
        weights : list of float or None, optional
            Selection weights for *elements*.  Must have the same length as
            *elements*.  Weights are normalised internally (default is
            ``None``, meaning uniform probability).
        nesting_probability : float, optional
            Probability that any given position becomes a nested sub-list
            rather than a leaf element (default is 0.333).

        Returns
        -------
        Pattern
            A new ``Pattern`` instance built from the generated structure.

        Raises
        ------
        ValueError
            If *weights* is provided and its length differs from *elements*.

        Examples
        --------
        >>> import numpy as np; np.random.seed(0)
        >>> p = Pattern.from_random(['a', 'b', 'c'], length=4)
        >>> len(p) > 0
        True
        """
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
                    element = elements[index]
                    structure.append(element)
            return structure
        
        generated_structure = _generate_structure(length, max_nesting_level)
        return Pattern(generated_structure)
