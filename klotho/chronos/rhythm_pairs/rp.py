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

# # for reference
# def rhythm_pair(lst:Tuple, MM:bool=True) -> Tuple:
#     total_product = prod(lst)
#     if MM:
#         sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
#     else:
#         sequences = [np.arange(0, total_product + 1, x) for x in lst]
#     combined_sequence = np.unique(np.concatenate(sequences))
#     deltas = np.diff(combined_sequence)
#     return tuple(deltas)

# from typing import Tuple
# from math import prod

# def partition_sequence(sequence: Tuple[int, ...], partition_value: int) -> Tuple[int, Tuple[int, ...]]:
#     partitions = []
#     current_partition = []
#     current_sum = 0

#     for value in sequence:
#         current_partition.append(value)
#         current_sum += value

#         if current_sum == partition_value:
#             partitions.append((partition_value, tuple(current_partition)))
#             current_partition = []
#             current_sum = 0
    
#     return tuple(partitions)

# def partition_by_mm(sequence: Tuple[int, ...], mm_deltas: Tuple[int, ...]) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
#     partitions = []
#     current_partition = []
#     mm_index = 0
#     current_sum = 0

#     for value in sequence:
#         current_partition.append(value)
#         current_sum += value

#         if current_sum == mm_deltas[mm_index]:
#             partitions.append((mm_deltas[mm_index], tuple(current_partition)))
#             current_partition = []
#             current_sum = 0
#             mm_index = (mm_index + 1) % len(mm_deltas)  # Cycle through mm_deltas
    
#     return tuple(partitions)

# def rhythm_pair_partitions(lst: Tuple[int, ...]) -> Tuple[Tuple[Tuple[int, Tuple[int, ...]], ...], Tuple[Tuple[int, Tuple[int, ...]], ...]]:
#     total_product = prod(lst)
    
#     # Generate the non-MM sequence
#     sequences = [tuple(range(0, total_product + 1, x)) for x in lst]
#     combined_sequence = tuple(sorted(set(sum(sequences, ()))))
#     deltas = tuple(combined_sequence[i+1] - combined_sequence[i] for i in range(len(combined_sequence) - 1))
    
#     non_mm_sequence = deltas
    
#     # MM partitions are total_product // x
#     mm_partitions = tuple(total_product // x for x in lst)
    
#     # Partition the non-MM sequence by each value in the MM partitions
#     partitioned_sequences_non_mm = tuple(partition_sequence(non_mm_sequence, partition) for partition in mm_partitions)

#     # Now generate the MM deltas sequence
#     mm_sequences = [tuple(range(0, total_product + 1, total_product // x)) for x in lst]
#     combined_mm_sequence = tuple(sorted(set(sum(mm_sequences, ()))))
#     mm_deltas = tuple(combined_mm_sequence[i+1] - combined_mm_sequence[i] for i in range(len(combined_mm_sequence) - 1))
    
#     # Partition the non-MM sequence using the MM deltas
#     partitioned_sequences_mm = partition_by_mm(non_mm_sequence, mm_deltas)
    
#     # Flatten MM partitions into one set
#     flattened_mm_partitions = tuple(partition for partition in partitioned_sequences_mm)
    
#     return partitioned_sequences_non_mm, flattened_mm_partitions

# # Example usage
# lst = (3, 5, 7)
# partitions_non_mm, partitions_mm = rhythm_pair_partitions(lst)

# print("Non-MM Partitions:")
# for partition in partitions_non_mm:
#     print(partition)
#     print()

# print("\nMM Partitions:")
# print(partitions_mm)

class RhythmPair:
    def __init__(self, lst: Tuple[int, ...]):
        self.lst = lst
        self._mm_sequence = None
        self._non_mm_sequence = None
        self._partitions = None
        self._measures = None
        self._beats = None
        self._calculate()

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

    @property
    def partitions(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        return self._partitions

    @property
    def measures(self) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        return self._measures

    @property
    def beats(self) -> Tuple[int, ...]:
        return self._beats

