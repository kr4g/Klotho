from klotho.chronos import seconds_to_hmsms
from klotho.chronos.rhythm_trees import RhythmTree as RT
from klotho.chronos.temporal_units import TemporalUnit as UT
from klotho.skora.graphs import plot_graph

S = (1, (1, (1, 1)), (1, (1, 1, 1, 1)), 1)
ut = UT(span=1, tempus='5/4', prolatio=S, tempo=60, beat='1/4')
print(ut.rtree, end='')
print(seconds_to_hmsms(ut.duration))
print()
plot_graph(ut.rtree.graph)
ut = UT(span=2, tempus='4/5', prolatio=S, tempo=60, beat='1/4')
print(ut.rtree, end='')
print(seconds_to_hmsms(ut.duration))
plot_graph(ut.rtree.graph)
