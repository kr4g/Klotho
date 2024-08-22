import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# -------
from klotho.topos.sets import CombinationSet as CPS
from klotho.topos.graphs import ComboNet
from klotho.tonos.combination_product_sets import nkany as NKany
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq

from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.tonos import fold_interval, fold_freq
from klotho.aikous import db_amp
from klotho.aikous import enevelopes as envs

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np
from fractions import Fraction
from math import gcd, lcm
from functools import reduce
from itertools import cycle
import random

# -------------------------------------------------------------------------------------
# HELPER FUNCTIONS --------------------------------------------------------------------
# -----------------
def nth_odd(n:int):
    return 2*n - 1

import random
from collections import defaultdict
from klotho.topos.graphs import ComboNet

class ComboNetTraversal:
    def __init__(self, combnet: ComboNet):
        self.combnet = combnet
        self.visited_edges = defaultdict(int)

    def play(self, start_node, num_steps):
        current_node = start_node
        path = [current_node]

        for _ in range(num_steps):
            next_node = self.choose_next_node(current_node)
            if next_node is None:
                print("No more available moves. Game over.")
                break
            
            path.append(next_node)
            self.visited_edges[self.edge_key(current_node, next_node)] += 1
            current_node = next_node

        return path

    def choose_next_node(self, current_node):
        neighbors = self.combnet.graph[current_node]
        if not neighbors:
            return None
        
        candidates = defaultdict(lambda: defaultdict(list))
        
        for neighbor, weight in neighbors.items():
            visit_count = self.visited_edges[self.edge_key(current_node, neighbor)]
            candidates[weight][visit_count].append(neighbor)

        sorted_weights = sorted(candidates.keys(), reverse=True)

        for weight in sorted_weights:
            visit_counts = sorted(candidates[weight].keys())
            for visit_count in visit_counts:
                if candidates[weight][visit_count]:
                    return random.choice(candidates[weight][visit_count])

        return None

    def edge_key(self, node1, node2):
        return tuple(sorted([node1, node2]))
    
# -------------------------------------------------------------------------------------
# META MATERIAL -----------------------------------------------------------------------
# --------------
variables = ('A', 'B', 'C', 'D')

cps = CPS(variables, r=2)
print(f'CPS: {cps}')

comb_net = ComboNet(cps)
print(f'{len(comb_net.graph)} nodes in the network.\n')
for combo in cps.combos:
    print(f"Node: {combo}\nEdges: {comb_net.graph[combo]}\n{'-'*20}")

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
partials = tuple(nth_odd(i + 1) for i in range(len(variables)))
dynamics = ['ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff']
aliases = {
    'partials' : { k: v for k, v in zip(variables, partials) },
    'dynamics': { k: v for k, v in zip(variables, np.random.choice(dynamics, len(variables), False)) },
}

min_db = -60
max_db = 0  

step_size = (max_db - min_db) / (len(dynamics) - 1)

dynamic_db_ranges = {
    dynamics[i]: db_amp(min_db + i * step_size)
    for i in range(len(dynamics))
}

print(dynamic_db_ranges)

hx = NKany.Hexany(partials)
print(hx)

n = 17
cg = ComboNetTraversal(comb_net)
start_node = random.choice(list(cps.combos))
path = cg.play(start_node, n)
# print(path)

vtp = lambda v, p: (v[p[0]], v[p[1]])

beat = '1/4'
bpm = 132
seq = []

root_freq = 333.0

seen = set()
ratios = []
for i, combo in enumerate(path):
    # seen.add(combo)
    ratio = hx.combo_to_ratio[vtp(aliases['partials'], combo)]
    ratios.append(ratio)
    if combo in seen:
        ratio = 1/ratio
    else:
        seen.add(combo)
    print(f'{combo} -> {ratio}')
    seq.append(UT(tempus=ratio, prolatio='d', tempo=bpm, beat=beat))

utseq = UTSeq(seq)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------
seen = set()
# amp = db_amp(-13)
uid_pad = None
for i, (ut, combo) in enumerate(zip(utseq, path)): 
    ratio = hx.combo_to_ratio[vtp(aliases['partials'], combo)]
    if combo in seen:
        ratio = 1/ratio
    else:
        seen.add(combo)
        
    for j, event in enumerate(ut):
        if event['duration'] < 0:
            continue
        scheduler.add_event('ping2', event['start'],
                                freq=root_freq * Fraction(ratio) * 2.0**2,
                                amp=db_amp(-18))

comp_dur = utseq.time
print(f'{round(comp_dur, 2)}, {seconds_to_hmsms(comp_dur)}.')

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# --------------------------------
scheduler.send_all_events()