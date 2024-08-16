import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.topos import autoref
from klotho.chronos.temporal_units import TemporalUnitSequence as UTSeq, TemporalUnit as UT
from klotho.chronos.rhythm_trees.rt import *
from klotho.chronos.rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.topos.sequences import NestedCycle
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
# ---------------------------
tempus = '2/4'
beat = '1/8'
bpm = 84

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

r = rts['prime_flat'].ratios
while len(r) > 1:
    r = r[1:]
    mRt = RhythmTree.from_ratios(r)
    mUt = UT.from_tree(mRt, tempo=bpm, beat=beat)
    seqs['prime'].append(mUt)

r_rev = rts['prime_flat_rev'].ratios
while len(r_rev) > 1:
    r_rev = r_rev[1:]
    mRt_rev = RhythmTree.from_ratios(r_rev)
    mUt_rev = UT.from_tree(mRt_rev, tempo=bpm, beat=beat)
    seqs['prime_rev'].append(mUt_rev)

seqs['prime_rev'] = seqs['prime_rev'][::-1]

# interleave seq and seq_rev
seqs['full'] = [val for pair in zip(seqs['prime'], seqs['prime_rev']) for val in pair]
print(seqs['full'])

utseq = UTSeq(seqs['full'])
print(utseq.duration)
glitch = NestedCycle(['random', 'glitch1', 'random', 'random'])
dnb = NestedCycle([['kick2', ['kick2', 'snare2'], 'ghostKick'], ['kick2', ['hat', 'hat2']], ['snare', ['perc', ['perc2', 'hatSoft']]]])
for i in range(30):
    print(next(dnb))
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------
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
            amp = np.interp(j, [0, len(ut) - 1], [ampMin, ampMax])
        else:
            synth = 'glitch2' if i % 2 == 0 else 'kick'
            amp = db_amp(-4) if i % 2 == 0 else db_amp(-8)
        if j == len(ut) - 1 and i == utseq.size - 1:
            synth = 'crash'
            amp = db_amp(-4)
        scheduler.add_new_event(synth, event['start'],
                                duration=min_dur*0.43,
                                seed=seed*i+j,
                                amp=amp,
                                freq=np.random.uniform(300,1000),
                                brushFreq=np.random.uniform(0,1),
                                isGhost=np.random.uniform(0,1),
                                freqShift=np.random.uniform(50,3800),
                                pan=pan,)
# TODO: end with "crash"

# print(utseq.size)
print(seconds_to_hmsms(sum([ut_dur(ut) for ut in utseq])))
# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# --------------------------------
scheduler.send_all_events()