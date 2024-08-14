import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# -------
from allopy.topos.sets import CombinationProductSet as CPS
from allopy.topos.graphs import CombNet
from allopy.tonos.JI import combination_sets as NKany
from allopy.chronos.temporal_units import UTSeq, TB, TemporalUnit as UT

from allopy.chronos import seconds_to_hmsms, beat_duration
from allopy.tonos import fold_interval, fold_freq
from allopy.aikous import db_amp
from allopy.aikous.curves import enevelopes as envs

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
def ut_dur(ut:UT):
    return beat_duration(str(ut.tempus), bpm=ut.tempo, beat_ratio=ut.beat)

def ut_seq_dur(utseq:UTSeq):
    return sum(ut_dur(ut) for ut in utseq)

def nth_odd(n:int):
    return 2*n - 1
import random
from collections import defaultdict
from allopy.topos.graphs import CombNet

class CombNetTraversal:
    def __init__(self, combnet: CombNet):
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

        # Group neighbors by weight and visit count
        candidates = defaultdict(lambda: defaultdict(list))
        for neighbor, weight in neighbors.items():
            visit_count = self.visited_edges[self.edge_key(current_node, neighbor)]
            candidates[weight][visit_count].append(neighbor)

        # Sort weights in descending order
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

comb_net = CombNet(cps)
print(f'{len(comb_net.graph)} nodes in the network.\n')
for combo in cps.combos:
    print(f"Node: {combo}\nEdges: {comb_net.graph[combo]}\n{'-'*20}")

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
partials = tuple(nth_odd(i + 1) for i in range(len(variables)))
aliases = {
    k: v for k, v in zip(variables, partials)
}

hx = NKany.Hexany(partials)
print(hx)

bpm = 132
beat = '1/4'
seq = []

n = 13
cg = CombNetTraversal(comb_net)
start_node = random.choice(list(cps.combos))
path = cg.play(start_node, n)
# print(path)

vtp = lambda v, p: (v[p[0]], v[p[1]])


for i, combo in enumerate(path):
    print(f'{combo} -> {hx.combo_ratio(vtp(aliases, combo))}')

# # samples = np.random.choice(hx.ratios, size=n, replace=True)
# # for sample in samples:
# #     if np.random.uniform() < 0.5:
# #         tempus = tempus=1/sample
# #     else:
# #         tempus = tempus=sample
# #     seq.append(UT(tempus=tempus, prolatio='p', tempo=bpm, beat=beat))

utseq = UTSeq(seq)

# # ------------------------------------------------------------------------------------
# # COMPOSITIONAL PROCESS --------------------------------------------------------------
# # ----------------------
# for i, ut in enumerate(utseq):
#     # seed = np.random.uniform()
#     # seed = hash((ut.tempus.numerator, ut.tempus.denominator))
#     min_amp = np.interp(len(ut), (1, max(len(ut) for ut in utseq.uts)), (db_amp(-24), db_amp(-48)))
#     min_max = (min_amp, db_amp(-6))
#     if np.random.uniform() < 0.5:
#         min_max = min_max[::-1]
#     if np.random.uniform() < 0.5:
#         amps = envs.swell(len(ut), *min_max)
#     else:
#         amps = envs.line(len(ut), *min_max)
#     for j, event in enumerate(ut):
#         if event['duration'] < 0:
#             continue
#         scheduler.add_new_event('honk', event['start'],
#                                 duration=event['duration']*0.33,
#                                 freq=333.0 * Fraction(samples[i]),
#                                 amp=amps[j])


# comp_dur = ut_seq_dur(utseq)
# print(f'{round(comp_dur, 2)}, {seconds_to_hmsms(comp_dur)}.')

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# # --------------------------------
# scheduler.send_all_events()