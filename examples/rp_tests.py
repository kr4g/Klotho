from klotho.chronos.rhythm_pairs.rp import *

lst = (3, 5, 7)
rp = RhythmPair(lst)
print("Partitions:")
for partition in rp.partitions:
    print(partition)
    print()
print("\nMeasures:")
print(rp.measures)
print("\nBeats:")
print(rp.beats)