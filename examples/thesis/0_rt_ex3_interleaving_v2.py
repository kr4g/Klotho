import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# --------
from klotho.topos import autoref
from klotho.chronos.temporal_units import TemporalUnitSequence as UTSeq, TemporalUnit as UT
from klotho.chronos.rhythm_trees.rt import *
from klotho.chronos.rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.topos.sequences import Pattern
from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.aikous.expression import db_amp
from klotho.skora.graphs import *
from klotho.skora.animation.animate import *

# from utils.data_structures import scheduler as sch
# scheduler = sch.Scheduler()
from klotho.aikous.messaging import Scheduler
scheduler = Scheduler()

import os

import numpy as np
from math import gcd, lcm
from functools import reduce
from itertools import cycle

def ut_dur(ut:UT):
    return beat_duration(str(ut.tempus), bpm=ut.tempo, beat_ratio=ut.beat)

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
# tempus = '2/4'
tempus = '1/1'
beat = '1/8'
# bpm = 84
bpm = 84*2

# S = autoref((3, 1, 2))
S = autoref((5, 2, 3))
# S = autoref((7, 3, 5))
print('-'*50)
print(f'S: {S}')
print('-'*50)

mS = []
for i, d in enumerate(S):
    mS.append((d[0], auto_subdiv(d[1], n=i + 1)))
mS = tuple(mS)
print(f'mS: {mS}')
print('-'*50)

rts = {}
rts['prime'] = RhythmTree(meas=tempus, subdivisions=(mS))
print(f"rt_prime:\n{rts['prime']}")
# plot_graph(graph_tree(rts['prime'].meas, rts['prime'].subdivisions))
# animate_temporal_unit(UT.from_tree(rts['prime'], tempo=bpm*1.1, beat=beat), save_mp4=True, file_name='rt_prime')
print('-'*50)
rts['prime_flat'] = rts['prime'].flatten()
print(f"rt_prime_flat:\n{rts['prime_flat']}")
print('-'*50)

uts = {}
seqs = {'prime':[], 'prime_rev':[]}
uts['prime'] = UT.from_tree(rts['prime_flat'], tempo=bpm, beat=beat)
seqs['prime'].append(uts['prime'])
print('*'*50)

rts['prime_flat_rev'] = RhythmTree.from_ratios(rts['prime_flat'].ratios[::-1])
seqs['prime_rev'].append(UT.from_tree(rts['prime_flat_rev'], tempo=bpm, beat=beat))
print(f"rt_prime_flat_rev:\n{rts['prime_flat_rev']}")
print('-'*50)

output_dir = "/Users/ryanmillett/Klotho/examples"
os.makedirs(output_dir, exist_ok=True)

r = rts['prime_flat'].ratios
while len(r) > 1:
    r = r[1:]
    mRt = RhythmTree.from_ratios(r)
    mUt = UT.from_tree(mRt, tempo=bpm, beat=beat)
    seqs['prime'].append(mUt)

image_files = []
for i, ut in enumerate(seqs['prime']):
    output_file = os.path.join(output_dir, f"graph_{i}a.png")
    # plot_graph(graph_tree(ut.tempus, ut.prolationis), output_file)
    image_files.append(output_file)

gif_file = os.path.join(output_dir, 'graph_animation_A.gif')
duration_per_frame = 100
# create_gif(image_files, gif_file, duration_per_frame)

r_rev = rts['prime_flat_rev'].ratios
while len(r_rev) > 1:
    r_rev = r_rev[1:]
    mRt_rev = RhythmTree.from_ratios(r_rev)
    mUt_rev = UT.from_tree(mRt_rev, tempo=bpm, beat=beat)
    seqs['prime_rev'].append(mUt_rev)
    # plot_graph(graph_tree(mUt.tempus, mUt.prolationis))

seqs['prime_rev'] = seqs['prime_rev'][::-1]

image_files = []
for i, ut in enumerate(seqs['prime_rev']):
    output_file = os.path.join(output_dir, f"graph_{i}b.png")
    # plot_graph(graph_tree(ut.tempus, ut.prolationis), output_file)
    image_files.append(output_file)

gif_file = os.path.join(output_dir, 'graph_animation_B.gif')
# create_gif(image_files, gif_file, duration_per_frame)



# interleave seq and seq_rev
seqs['full'] = [val for pair in zip(seqs['prime'], seqs['prime_rev']) for val in pair]
print(seqs['full'])


utseq = UTSeq(seqs['full'])
print(utseq.duration)
glitch = Pattern(['random', 'glitch1', 'random', 'random'])
dnb = Pattern([['kick2', ['kick2', 'snare2'], 'ghostKick'], ['kick2', ['hat', 'hat2']], ['snare', ['perc', ['perc2', 'hatSoft']]]])
for i in range(30):
    print(next(dnb))

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------
seed = np.random.randint(1000)
for i, ut in enumerate(utseq):
    bias = 'r' if i % 2 == 0 else 'b'
    _ut = ut
    _ut.offset = 0
    animate_temporal_unit(_ut, save_mp4=True,file_name=f'interleave_animation_{i}', bias=bias)
#     min_dur = min(ut.durations)
#     if i % 2 == 0:
#         synth_cycle = glitch
#         pan = -1
#         ampMin = db_amp(-20)
#         ampMax = db_amp(np.interp(i, [0, len(utseq)], [-8, -12]))
#     else:
#         synth_cycle = dnb
#         pan = 1
#         ampMin = db_amp(-7)
#         ampMax = db_amp(np.interp(i, [0, len(utseq)], [-4, 1]))
    
#     for j, event in enumerate(ut):
#         if len(ut) > 1:
#             synth = next(synth_cycle)
#             amp = np.interp(j, [0, len(ut) - 1], [ampMin, ampMax])
#         else:
#             synth = 'glitch2' if i % 2 == 0 else 'kick'
#             amp = db_amp(-4) if i % 2 == 0 else db_amp(-8)
#         if j == len(ut) - 1 and i == len(utseq) - 1:
#             synth = 'crash'
#             amp = db_amp(-4)
#         scheduler.new_synth(synth, event['start'],
#                             duration=min_dur*0.43,
#                             seed=seed*i+j,
#                             amp=amp,
#                             freq=np.random.uniform(300,1000),
#                             brushFreq=np.random.uniform(0,1),
#                             isGhost=np.random.uniform(0,1),
#                             freqShift=np.random.uniform(50,3800),
#                             pan=pan,)
# # TODO: end with "crash"

# # print(utseq.size)
# print(seconds_to_hmsms(sum([ut_dur(ut) for ut in utseq])))
# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# # --------------------------------
# # scheduler.send_all_events()
# scheduler.run()