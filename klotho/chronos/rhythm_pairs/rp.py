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
import numpy as np
from ..rhythm_trees.algorithms import rhythm_pair

class RhythmPair:
    def __init__(self, lst: Tuple[int, ...]):
        self.lst = lst
        self._mm_sequence = None
        self._non_mm_sequence = None
        self._partitions = None
        self._measures = None
        self._beats = None
        self._subdivs = False
        self._calculate()
        
    @property
    def partitions(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        return self._partitions

    @property
    def measures(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        return self._measures

    @property
    def beats(self) -> Tuple[int, ...]:
        return self._beats

    def _calculate(self):
        # Calculate MM and Non-MM sequences
        self._mm_sequence = rhythm_pair(self.lst, MM=True)
        self._non_mm_sequence = rhythm_pair(self.lst, MM=False)
        
        # Calculate partitions
        self._partitions = self._calculate_partitions(self._non_mm_sequence)
        self._measures = self._calculate_measures(self._non_mm_sequence, self._mm_sequence)
        self._beats = self._non_mm_sequence

    def _calculate_partitions(self, sequence: Tuple[int, ...]) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        total_product = prod(self.lst)
        mm_partitions = tuple(total_product // x for x in self.lst)
        return tuple(self._partition_sequence(sequence, partition) for partition in mm_partitions)

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

    def _calculate_measures(self, sequence: Tuple[int, ...], mm_deltas: Tuple[int, ...]) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        partitions = []
        current_partition = []
        mm_index = 0
        current_sum = 0

        for value in sequence:
            current_partition.append(value)
            current_sum += value

            if current_sum == mm_deltas[mm_index]:
                partitions.append((mm_deltas[mm_index], tuple(current_partition)))
                current_partition = []
                current_sum = 0
                mm_index = (mm_index + 1) % len(mm_deltas)  # Cycle through mm_deltas

        return tuple(partitions)

