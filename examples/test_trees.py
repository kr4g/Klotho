from klotho.chronos import seconds_to_hmsms
from klotho.chronos.rhythm_trees import RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import measure_ratios
from klotho.chronos.temporal_units import TemporalUnit as UT
from klotho.skora.graphs import plot_graph

# S = (1, (1, (1, 1)), (1, (1, 1, 1, 1)), 1)
S = (3,(2,(1,1)),(3,(1,1,1,1)),2)
ut = UT(span=1, tempus='4/4', prolatio=S, tempo=60, beat='1/4')
print(ut.rtree, end='')
print(seconds_to_hmsms(ut.duration))
print()
print([str(r) for r in measure_ratios(ut.rtree.subdivisions)])
plot_graph(ut.rtree.graph, ['ratio', 'span'], True)
# ut = UT(span=2, tempus='4/5', prolatio=S, tempo=60, beat='1/4')
# print(ut.rtree, end='')
# print(seconds_to_hmsms(ut.duration))
# plot_graph(ut.rtree.graph, ['ratio', 'span'], True)