from klotho.chronos.rhythm_pairs import *

lst = (3, 5, 7)
rp = RhythmPair(lst)
print("Partitions:")
print(rp.partitions)
print("\nMeasures:")
print(rp.measures)
print("\nBeats:")
print(rp.beats)