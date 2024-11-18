from klotho.topos.sequences import Norg
from klotho.tonos import fold_interval, fold_freq
from klotho.chronos import seconds_to_hmsms
# from klotho.aikous.messaging import Scheduler
from utils.messaging import Scheduler
from klotho.tonos.combination_product_sets import NKany
from klotho.topos.graphs.networks import ComboNet
from klotho.topos.graphs.networks.algorithms import ComboNetTraversal
from klotho.aikous.expression import amp_freq_scale, db_amp
from klotho.topos.sequences import Pattern
from klotho.chronos.rhythm_trees import auto_subdiv
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq, TemporalUnitMatrix as UTMat
import networkx as nx
import math
from fractions import Fraction

HARMONICS = [
    1, 129, 65, 131, 33, 133, 67, 135, 17, 137, 69, 139, 35, 141, 71, 143, 9,
    145, 73, 147, 37, 149, 75, 151, 19, 153, 77, 155, 39, 157, 79, 159, 5, 161,
    81, 163, 41, 165, 83, 167, 21, 169, 85, 171, 43, 173, 87, 175, 11, 177, 89,
    179, 45, 181, 91, 183, 23, 185, 93, 187, 47, 189, 95, 191, 3, 193, 97, 195,
    49, 197, 99, 199, 25, 201, 101, 203, 51, 205, 103, 207, 13, 209, 105, 211,
    53, 213, 107, 215, 27, 217, 109, 219, 55, 221, 111, 223, 7, 225, 113, 227,
    57, 229, 115, 231, 29, 233, 117, 235, 59, 237, 119, 239, 15, 241, 121, 243,
    61, 245, 123, 247, 31, 249, 125, 251, 63, 253, 127, 255
]

G = nx.Graph()
G.add_nodes_from(HARMONICS)
for i in range(len(HARMONICS)):
    for j in range(i + 1, len(HARMONICS)):
        harmonic1 = HARMONICS[i]
        harmonic2 = HARMONICS[j]

        gcd = math.gcd(harmonic1, harmonic2)

        if gcd > 1:# and gcd in HARMONICS:
            G.add_edge(harmonic1, harmonic2)

def get_connected_nodes(graph, node):
    if node in graph:
        connected_nodes = list(graph.neighbors(node))
        return connected_nodes
    else:
        print(f"Node {node} does not exist in the graph.")
        return []

node = 5
connected_nodes = get_connected_nodes(G, node)
pairs = {n: n // node for n in connected_nodes}

hx = NKany(connected_nodes, 2, normalized=False)
combnet = ComboNet(hx)
# print(hx)
path = ComboNetTraversal(combnet).play(list(hx.combos)[0], 120)
# print(path)

import numpy as np
scheduler = Scheduler()

for i, p in enumerate(path):
    # print(p)
    # print(Fraction(p[0], p[1]))
    start = i * 3
    fund = 666.0
    freq1 = fund * fold_interval(hx.combo_to_ratio[p]) * 4
    freq2 = fund * fold_interval(hx.combo_to_product[p]) * 0.25
    freq3 = fund * fold_interval(p[0]) * 2
    freq4 = fund * fold_interval(p[1])
    scheduler.new_event('test', start=start + 0.0, freq=freq1, amp=0.05, attackTime=0.05, releaseTime=3.5, pan=np.sin(start * 5.1))
    scheduler.new_event('test', start=start + 0.0, freq=freq2, amp=0.25, attackTime=0.75, releaseTime=5.5, pan=0)
    scheduler.new_event('test', start=start + 0.0, freq=freq3, amp=0.10, attackTime=0.25, releaseTime=1.5, pan=np.cos(start * 0.5))
    scheduler.new_event('test', start=start + 0.0, freq=freq4, amp=0.10, attackTime=0.25, releaseTime=1.5, pan=np.sin(start * 0.5))
scheduler.run()
