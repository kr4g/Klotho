# import sys
# from pathlib import Path

# root_path = Path(__file__).parent.parent.parent
# sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# -------
from klotho.topos.sets import CombinationSet as CPS
from klotho.topos.graphs import ComboNet
from klotho.topos.graphs.networks.algorithms import ComboNetTraversal
from klotho.tonos.combination_product_sets import nkany as NKany
from klotho.chronos.rhythm_trees import RhythmTree as RT
from klotho.chronos.temporal_units import TemporalUnitSequence, TemporalUnit as UT

from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.tonos import fold_interval, fold_freq
from klotho.aikous.expression import db_amp, DynamicRange, DYNAMIC_MARKINGS
from klotho.aikous.expression import enevelopes as envs

from klotho.aikous.messaging import Scheduler
sch = Scheduler()

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

def ut_seq_dur(utseq:TemporalUnitSequence):
    return sum(ut_dur(ut) for ut in utseq)

def nth_odd(n:int):
    return 2*n - 1
    
# -------------------------------------------------------------------------------------
# META MATERIAL -----------------------------------------------------------------------
# --------------
variables = ('A', 'B', 'C', 'D')
cps = CPS(variables, r=2)

# print(f'CPS: {cps}')

comb_net = ComboNet(cps)


print(f'{len(comb_net.graph)} nodes in the network.\n')
# for combo in cps.combos:
#     print(f"Node: {combo}\nEdges: {comb_net.graph[combo]}\n{'-'*20}")

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
partials = tuple(nth_odd(i + 1) for i in range(len(variables)))
insts = ['pitchPerc', 'drone', 'horn', 'ping2']
aliases = {
    'partials': { k: v for k, v in zip(variables, partials) },
    'dynamics': { k: v for k, v in zip(variables, np.random.choice(DYNAMIC_MARKINGS, len(variables), False)) },
    'insts': { k: v for k, v in zip(variables, insts) }
}

hx = NKany.Hexany(partials)
print(hx)

n = 17
cg = ComboNetTraversal(comb_net)
start_node = random.choice(list(cps.combos))
path = cg.play(start_node, n)
# print(path)

# vtp = lambda v, p: (v[p[0]], v[p[1]], v[p[2]])
vtp = lambda v, p: (v[p[0]], v[p[1]])

bpm = 76
beat = '1/8'
root_freq = 440.0 * (2/3)

seq = []
seen_ratios = set()
for i, combo in enumerate(path):
    ratio = hx.combo_to_ratio[vtp(aliases['partials'], combo)]
    if ratio in seen_ratios:
        ratio = 1 / ratio
    else:
        seen_ratios.add(ratio)
    seq.append(UT(tempus=ratio, prolatio='p', tempo=bpm, beat=beat))

utseq = TemporalUnitSequence(seq)
print(utseq.time)

S = ((5,(4,3)),3,2,(7,(5,2,3)))
rt = RT(meas='1/1', subdivisions=S)

# # ------------------------------------------------------------------------------------
# # COMPOSITIONAL PROCESS --------------------------------------------------------------
# # ----------------------

# dyn_ranges = {
#     'ping2': DynamicRange(-25, -6),
#     'drone': DynamicRange(-31, -13),
#     'pitchPerc': DynamicRange(-38, -13),
#     'horn': DynamicRange(-32, -4)
# }

# seen_partials = set()
# seen_ratios = set()
# for i, (combo, ut) in enumerate(zip(path, utseq)):
#     synths = vtp(aliases['insts'], combo)
#     root_partial = hx.combo_to_product[vtp(aliases['partials'], combo)]
#     if combo in seen_partials:
#         root_partial = 1 / root_partial
#     else:
#         seen_partials.add(root_partial)
    
#     if 'drone' in synths:
#         dur = ut.duration * 0.833
#         atk = np.random.uniform(0.167, 0.833) * dur
#         dyns = vtp(aliases['dynamics'], combo)
#         freq = np.random.choice([0.5, 2]) * root_freq * fold_interval(root_partial)
#         amp = 0.5 * (db_amp(dyn_ranges['drone'][dyns[0]]) + db_amp(dyn_ranges['drone'][dyns[1]]))
#         sch.new_synth('drone', ut.onsets[0],
#                       duration = dur,
#                       amp = amp * np.interp(freq, [0.5*root_freq, 2*root_freq], [1, db_amp(-16)]),
#                       atk = atk,
#                       rel = dur - atk,
#                       freq = freq)
   
#     for synth in [syn for syn in synths if syn not in ['drone']]:
#         sub_path = ComboNetTraversal(comb_net).play(combo, ut.tempus.numerator)
#         ratios = cycle([hx.combo_to_ratio[vtp(aliases['partials'], cp)] for cp in sub_path])
#         dyns = vtp(aliases['dynamics'], combo)
#         dbs = cycle(envs.line(len(ut), dyn_ranges[synth][dyns[0]], dyn_ranges[synth][dyns[1]]))
#         seen_ratios = set()
#         if synth == 'horn':
#             _ut = UT(tempus=ut.tempus, prolatio=rt.rotate(i).subdivisions, tempo=ut.tempo, beat=ut.beat)
#             _ut.offset = ut.offset
#         else:
#             _ut = ut
#         for j, event in enumerate(_ut):
#             if np.random.rand() < 0.36:
#                 continue
                
#             ratio = next(ratios)
#             if ratio in seen_ratios:
#                 ratio = 1 / ratio
#             else:
#                 seen_ratios.add(ratio)
            
#             amp = db_amp(next(dbs))
#             match synth:
#                 case 'ping2':
#                     pfields = {
#                         'duration': event['duration'],
#                         'amp': amp,
#                         'freq': root_freq * fold_interval(root_partial) * ratio
#                     }
#                 case 'pitchPerc':
#                     pfields = {
#                         'amp': amp,
#                         'ratio': fold_interval(root_partial) * ratio,
#                         'velocity': np.random.uniform(amp, 1 - amp),
#                     }
#                 case 'horn':
#                     atk = np.random.uniform(0.167, 0.667) * event['duration']
#                     pfields = {
#                         'duration': event['duration'],
#                         'atk': atk,
#                         'rel': event['duration'] * 0.33,
#                         'amp': amp * 0.833,
#                         'freq': 0.5 * fold_freq(root_freq * fold_interval(root_partial) * ratio, 250.0, 1500.0)
#                     }
            
#             sch.new_synth(synth, event['start'], **pfields)

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# # --------------------------------
# sch.run()
