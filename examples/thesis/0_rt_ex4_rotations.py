import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.topos import autoref
from klotho.topos.graphs.graph_algorithms import factor_children
from klotho.chronos.temporal_units import TemporalUnitSequence, TemporalUnitMatrix, TemporalUnit as UT
from klotho.chronos.rhythm_trees.rt import *
from klotho.chronos.rhythm_trees.algorithms.rts import flatten_tree, ratios_to_tree, rotate_tree
from klotho.chronos.rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.tonos import fold_interval, fold_freq
from klotho.aikous import db_amp

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np
from math import gcd, lcm
from functools import reduce
from itertools import cycle

def ut_dur(ut:UT):
    return beat_duration(str(ut.tempus), bpm=ut.tempo, beat_ratio=ut.beat)

def ut_seq_dur(utseq:TemporalUnitSequence):
    return sum(ut_dur(ut) for ut in utseq)

def swell(n, min_val=0.0, max_val=1.0):
    up = np.linspace(min_val, max_val, n//2, endpoint=False)
    down = np.linspace(max_val, min_val, n//2 + n % 2, endpoint=True)
    result = np.concatenate([up, down])
    return result

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
tempus = '13/1'
beat = '1/8'
bpm = 54

S = ((17, ((15, ((13, (13, 9, 5, 2)), 7)), (13, (7, 5, 2)))), (13, (6, 9)))

rt_prime = RhythmTree(meas=tempus, subdivisions=S)
# print(rt_prime)
# print(len(rt_prime))
# print('-' * 80)

rots = []
for i in range(len(factor_children(rt_prime.subdivisions))):
# for i in range(5):
    # print(rotate_tree(rt_prime, i))
    rots.append(TemporalUnitSequence((UT.from_tree(rotate_tree(rt_prime, i), tempo=bpm, beat=beat),)))

tb = TemporalUnitMatrix(tuple(rots))
# utseq = TemporalUnitSequence(rots)
# print(f'{ut_seq_dur(utseq)} ({seconds_to_hmsms(ut_seq_dur(utseq))})')

for i, utseq in enumerate(tb):
    print(i, utseq.uts[0])
    
freqs = cycle([np.random.uniform(333.0, 666.0)*0.25 for _ in range(len(rt_prime))])

print(tb.duration)
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
u_ids = {}
synths = cycle(['bassoon', 'frenchhorn', 'clarinet', 'oboe', 'flute'])
min_freqs = {'flute': 600, 'oboe': 500, 'clarinet': 150, 'bassoon': 100, 'frenchhorn': 350}
max_freqs = {'flute': 4000, 'oboe': 2000, 'clarinet': 900, 'bassoon': 500, 'frenchhorn': 1500}
max_amps = {'flute': -8, 'oboe': -20, 'clarinet': -15, 'bassoon': -7, 'frenchhorn': -7}
for i, utseq in enumerate(tb):
    synth = next(synths)
    seed = np.random.randint(0, 1000)
    pan = np.interp(i, [0, tb.size], [-1, 1])
    u_ids[i] = scheduler.add_new_event_with_id(synth, 0, gate=0, amp=db_amp(-80), pan=pan)
    for j, ut in enumerate(utseq):
        vibDepth_seq = swell(len(ut), 0.0, np.interp(i, [0, tb.size], [0.001, 0.005]))
        vibRate_seq = swell(len(ut), 5.0, np.interp(i, [0, tb.size], [8.0, 13.0]))
        brightness = swell(len(ut), 1.0, 10.0)
        breathiness = swell(len(ut), 0.8, 0.1)
        min_dur = min(ut.durations)
        max_dur = max(ut.durations)
        for k, event in enumerate(ut):
            if k == 0: continue
            duration = np.interp(event['duration'], [min_dur, max_dur], [min_dur, max_dur*0.67])
            freq = next(freqs) * fold_interval((i + 1), n_equaves=4)
            freq = fold_freq(freq, min_freqs[synth], max_freqs[synth])
            
            scheduler.add_set_event(u_ids[i], event['start'], gate=1,
                                    freq=freq, freqLag=np.interp(i, [0, tb.size], [0.0, min_dur*0.167]),
                                    amp=db_amp(max_amps[synth] - i*0.5), ampLag=duration,
                                    vibDepth=np.random.uniform(0.0, vibDepth_seq[k]), vibRate=np.random.uniform(0.0, vibRate_seq[k]),
                                    brightness=brightness[k],
                                    breathiness=breathiness[k])
            
            alpha = np.interp(i, [0, tb.size], [0.667, 0.969])
            scheduler.add_set_event(u_ids[i], event['start'] + duration*alpha, gate=1,
                                    amp=db_amp(-80), ampLag=duration*(1-alpha))
            
            if k == len(ut) - 1:
                scheduler.add_set_event(u_ids[i], event['start'] + duration, gate=0)

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()