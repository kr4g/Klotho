# -----------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_pairs/rp.py
# -----------------------------------------------------------------------------
'''
Rhythm pairs.

A rhythm pair is a combinatorial structure derived from a tuple of integers.
It generates rhythmic sequences by computing the inter-onset intervals from
the superposition of evenly spaced pulse grids, each determined by an element
of the input tuple.
'''
from typing import Tuple
from math import prod
from ..rhythm_trees.algorithms import rhythm_pair

class RhythmPair:
    """
    A rhythm pair derived from a tuple of integers.

    A rhythm pair computes rhythmic sequences from the superimposition of
    evenly spaced pulse grids. Given a tuple of integers, two complementary
    sequences are produced: an MM (metric modulation) sequence and a non-MM
    sequence, along with partitions and measure groupings.

    Parameters
    ----------
    lst : tuple of int
        The tuple of integers from which to derive the rhythm pair.
    subdivs : bool, optional
        If True, partition and measure accessors return full ``(label, parts)``
        tuples; if False, only the labels are returned. Default is False.

    Examples
    --------
    >>> rp = RhythmPair((3, 4))
    >>> rp.product
    12
    >>> rp.beats
    (3, 1, 2, 2, 1, 3)
    """
    def __init__(self, lst: Tuple[int, ...], subdivs: bool = False):
        self.lst = lst
        self._subdivs = subdivs
        self._total_product = prod(lst)
        self._mm_sequence = rhythm_pair(self.lst, MM=True)
        self._non_mm_sequence = rhythm_pair(self.lst, MM=False)
        self._partitions = self._calculate_partitions()
        self._measures = self._calculate_measures()
        self._beats = self._non_mm_sequence

    @property
    def product(self) -> int:
        """
        The total product of all elements in the input tuple.

        Returns
        -------
        int
        """
        return self._total_product
    
    @property
    def products(self) -> Tuple[int, int, int]:
        """
        The total product divided by each element in the input tuple.

        Returns
        -------
        tuple of int
        """
        return tuple(self._total_product // x for x in self.lst)

    @property
    def partitions(self) -> Tuple[Tuple[int, ...], ...]:
        """
        The partitions of the non-MM sequence grouped by each product value.

        When ``subdivs`` is True, each partition element is a ``(label, parts)``
        tuple. When False, only the labels are returned.

        Returns
        -------
        tuple of tuple
        """
        if self._subdivs:
            return self._partitions
        return tuple(tuple(part[0] for part in group) for group in self._partitions)

    @property
    def measures(self) -> Tuple[int, ...]:
        """
        The measure groupings derived from the MM sequence.

        When ``subdivs`` is True, each measure element is a ``(label, parts)``
        tuple. When False, only the labels are returned.

        Returns
        -------
        tuple
        """
        if self._subdivs:
            return self._measures
        return tuple(measure[0] for measure in self._measures)

    @property
    def beats(self) -> Tuple[int, ...]:
        """
        The non-MM (beat-level) rhythmic sequence.

        Returns
        -------
        tuple of int
        """
        return self._beats
    
    @property
    def subdivs(self) -> bool:
        """
        Whether partition and measure accessors return full subdivision detail.

        Returns
        -------
        bool
        """
        return self._subdivs
    
    @subdivs.setter
    def subdivs(self, value: bool):
        self._subdivs = value

    def _calculate_partitions(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        mm_partitions = self.products
        return tuple(self._partition_sequence(self._non_mm_sequence, partition) for partition in mm_partitions)

    def _partition_sequence(self, sequence: Tuple[int, ...], partition_value: int) -> Tuple[int, Tuple[int, ...]]:
        partitions = []
        current_partition = []
        current_sum = 0

        for value in sequence:
            current_partition.append(value)
            current_sum += value

            if current_sum == partition_value:
                partitions.append((partition_value, tuple(current_partition)))
                current_partition = []
                current_sum = 0

        return tuple(partitions)

    def _calculate_measures(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        partitions = []
        current_partition = []
        mm_index = 0
        current_sum = 0

        for value in self._non_mm_sequence:
            current_partition.append(value)
            current_sum += value

            if current_sum == self._mm_sequence[mm_index]:
                partitions.append((self._mm_sequence[mm_index], tuple(current_partition)))
                current_partition = []
                current_sum = 0
                mm_index = (mm_index + 1) % len(self._mm_sequence)

        return tuple(partitions)
