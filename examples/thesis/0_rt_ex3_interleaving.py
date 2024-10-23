import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.topos import autoref
from klotho.chronos.temporal_units import TemporalUnitSequence, TemporalUnit as UT
from klotho.chronos.rhythm_trees.rt import *
from klotho.chronos.rhythm_trees.algorithms.rts import flatten_tree, ratios_to_tree
from klotho.chronos.rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.aikous import db_amp

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np
from math import gcd, lcm
from functools import reduce
from itertools import cycle

def ut_dur(ut:UT):
    return beat_duration(str(ut.tempus), bpm=ut.tempo, beat_ratio=ut.beat)

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
tempus = '2/4'
tempus_rest = '1/4'
beat = '1/8'
bpm = 76

S = autoref((5, 2, 3))
# S = autoref((7, 3, 5))
# print(S)
# print('-'*50)

mS = []
for d in S:
    mS.append((d[0], auto_subdiv(d[1])))
mS = tuple(mS)
# print(mS)

rt_prime = RhythmTree(meas=tempus, subdivisions=(mS))
print(rt_prime)
rt_prime_flat = flatten_tree(rt_prime)
# print(rt_prime_flat)
ut_prime = UT.from_tree(rt_prime_flat, tempo=bpm, beat=beat)
seq = []
seq.append(ut_prime)
print(ut_prime)
# print(ut_dur(ut_prime))
# print('*'*50)

rt_flat_rev = ratios_to_tree(rt_prime_flat.ratios[::-1])
seq_rev = []
seq_rev.append(UT.from_tree(rt_flat_rev, tempo=bpm, beat=beat))
# print(rt_flat_rev)

r = rt_prime_flat.ratios
while len(r) > 1:
    r = r[1:]
    mRt = ratios_to_tree(r)
    mUt = UT.from_tree(mRt, tempo=bpm, beat=beat)
    seq.append(mUt)
    
r_rev = rt_flat_rev.ratios
while len(r_rev) > 1:
    r_rev = r_rev[1:]
    mRt_rev = ratios_to_tree(r_rev)
    mUt_rev = UT.from_tree(mRt_rev, tempo=bpm, beat=beat)
    seq_rev.append(mUt_rev)

# reverse the seq_rev list
seq_rev = seq_rev[::-1]

# interleave seq and seq_rev
full_seq = [val for pair in zip(seq, seq_rev) for val in pair]
# print(full_seq)

utseq = TemporalUnitSequence(full_seq)
# print(utseq.duration)
glitch = cycle(['random', 'glitch1', 'random', 'random'])
dnb = cycle(['kick2', 'kick2', 'snare', 'kick2', 'kick2', 'perc', 'kick2', 'hat', 'perc2'])
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
seed = np.random.randint(1000)
for i, ut in enumerate(utseq):
    min_dur = min(ut.durations)
    if i % 2 == 0:
        synth_cycle = glitch
        pan = -1
        ampMin = db_amp(-20)
        ampMax = db_amp(np.interp(i, [0, len(utseq)], [-8, -12]))
    else:
        synth_cycle = dnb
        pan = 1
        ampMin = db_amp(-7)
        ampMax = db_amp(np.interp(i, [0, len(utseq)], [-4, 1]))
    
    for j, event in enumerate(ut):
        if len(ut) > 1:
            synth = next(synth_cycle)
            amp = np.interp(j, [0, len(ut)], [ampMin, ampMax])
        else:
            synth = 'glitch2' if i % 2 == 0 else 'kick'
            amp = db_amp(-4) if i % 2 == 0 else db_amp(0)
        scheduler.new_event(synth, event['start'],
                                duration=min_dur*0.43,
                                seed=seed*i+j,
                                amp=amp,
                                freq=np.random.uniform(300,1000),
                                freqShift=np.random.uniform(50,3800),
                                pan=pan,)

print(utseq.size)
print(seconds_to_hmsms(sum([ut_dur(ut) for ut in utseq])))
# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()