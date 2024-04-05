class Sets:
    @staticmethod
    def union(set1, set2):
        return set(set1).union(set(set2))

    @staticmethod
    def intersect(set1, set2):
        return set(set1).intersection(set(set2))

    @staticmethod
    def diff(set1, set2):
        return set(set1).difference(set(set2))

    @staticmethod
    def symm_diff(set1, set2):
        return set(set1).symmetric_difference(set(set2))

    @staticmethod
    def is_subset(subset, superset):
        return set(subset).issubset(set(superset))

    @staticmethod
    def is_superset(superset, subset):
        return set(superset).issuperset(set(subset))
    
    @staticmethod
    def invert(set1, axis=0, modulus=12):
        return tuple((axis * 2 - pitch) % modulus for pitch in set1)
    
    @staticmethod
    def transpose(set1, transposition_interval, modulus=12):
        return tuple((pitch + transposition_interval) % modulus for pitch in set1)
    
    @staticmethod
    def interval_vector(set1, modulus=12):
        intervals = [0] * (modulus // 2)
        for i in range(len(set1)):
            for j in range(i + 1, len(set1)):
                interval = abs(set1[j] - set1[i])
                if interval > modulus // 2:
                    interval = modulus - interval
                intervals[interval - 1] += 1
        return tuple(intervals)
