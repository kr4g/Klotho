import numpy as np
from collections.abc import Iterable
from itertools import cycle
from math import lcm

__all__ = [
    'Norg',
    'Pattern',
]

class Norg:
    '''
    Class for Per Nørgård's "infinity" sequences.

    see: https://web.archive.org/web/20071010091253/http://www.pernoergaard.dk/eng/strukturer/uendelig/uindhold.html
    '''
    @staticmethod
    def inf(start: int = 0, size: int = 128, step:int = 1):
        '''
        from: https://web.archive.org/web/20071010092334/http://www.pernoergaard.dk/eng/strukturer/uendelig/ukonstruktion05.html

        '''
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
        '''
        see: https://arxiv.org/pdf/1402.3091.pdf

        '''
        if n == 0: return 0
        if n % 2 == 0:
            return -Norg.inf_num(n // 2)
        return Norg.inf_num((n - 1) // 2) + 1

    @staticmethod
    def n_partite(seed: list = [0,-2,-1], inv_pat: list = [-1,1,1], size: int = 128):
        '''
        Generalized form of the tripartite series for any arbitrary length seed and inv_pat.

        from: https://web.archive.org/web/20071010091606/http://www.pernoergaard.dk/eng/strukturer/uendelig/u3.html

        '''
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
        '''
        see: https://web.archive.org/web/20071010093955/http://www.pernoergaard.dk/eng/strukturer/toneso/tkonstruktion.html

        '''
        pass


class Pattern:
    def __init__(self, iterable, end=False):
        self._iterable = iterable
        self._cycles, self._pattern_length = self._create_cycles(iterable)
        self._end = end
        self._current = 0
        
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
