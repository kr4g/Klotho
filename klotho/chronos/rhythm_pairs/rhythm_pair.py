# -----------------------------------------------------------------------------
# Klotho/klotho/chronos/rhythm_pairs/rp.py
# -----------------------------------------------------------------------------
'''
--------------------------------------------------------------------------------------
Rhythm pairs.
--------------------------------------------------------------------------------------
'''
from typing import Tuple
from math import prod
from ..rhythm_trees.algorithms import rhythm_pair

class RhythmPair:
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
        '''Return the total product of the list.'''
        return self._total_product
    
    @property
    def products(self) -> Tuple[int, int, int]:
        '''Return the products of the total product divided by each element in the list.'''
        return tuple(self._total_product // x for x in self.lst)

    @property
    def partitions(self) -> Tuple[Tuple[int, ...], ...]:
        '''Return partitions or just the partition labels depending on subdivs.'''
        if self._subdivs:
            return self._partitions
        return tuple(tuple(part[0] for part in group) for group in self._partitions)

    @property
    def measures(self) -> Tuple[int, ...]:
        '''Return measures or just the measure labels depending on subdivs.'''
        if self._subdivs:
            return self._measures
        return tuple(measure[0] for measure in self._measures)

    @property
    def beats(self) -> Tuple[int, ...]:
        '''Return the non-MM sequence (beats).'''
        return self._beats
    
    @property
    def subdivs(self) -> bool:
        '''Get the current state of subdivs.'''
        return self._subdivs
    
    @subdivs.setter
    def subdivs(self, value: bool):
        '''Set the subdivs flag.'''
        self._subdivs = value

    def _calculate_partitions(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        '''Calculate partitions based on the non-MM sequence.'''
        mm_partitions = self.products
        return tuple(self._partition_sequence(self._non_mm_sequence, partition) for partition in mm_partitions)

    def _partition_sequence(self, sequence: Tuple[int, ...], partition_value: int) -> Tuple[int, Tuple[int, ...]]:
        '''Partition the sequence based on a given partition value.'''
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
        '''Calculate measures based on the MM sequence.'''
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
