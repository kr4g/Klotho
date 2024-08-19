import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# -------
from klotho.topos.sets import CombinationSet as CPS
from klotho.topos.graphs import ComboNet
from klotho.topos.graphs.networks.algorithms import ComboNetTraversal
from klotho.tonos.combination_product_sets import nkany as NKany
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
print(f'CPS: {cps}')

comb_net = ComboNet(cps)
print(f'{len(comb_net.graph)} nodes in the network.\n')
# for combo in cps.combos:
#     print(f"Node: {combo}\nEdges: {comb_net.graph[combo]}\n{'-'*20}")

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
partials = tuple(nth_odd(i + 1) for i in range(len(variables)))
insts = ['perc', 'drone', 'horn', 'ping']
aliases = {
    'partials': { k: v for k, v in zip(variables, partials) },
    'dynamics': { k: v for k, v in zip(variables, np.random.choice(DYNAMIC_MARKINGS, len(variables), False)) },
    'insts': { k: v for k, v in zip(variables, insts) }
}

hx = NKany.Hexany(partials)
print(hx)

n = 11
cg = ComboNetTraversal(comb_net)
start_node = random.choice(list(cps.combos))
path = cg.play(start_node, n)
# print(path)

# vtp = lambda v, p: (v[p[0]], v[p[1]], v[p[2]])
vtp = lambda v, p: (v[p[0]], v[p[1]])

bpm = 92
beat = '1/4'
root_freq = 333.0

utseq = TemporalUnitSequence()
for i, combo in enumerate(path):
    ratio = hx.combo_to_ratio[vtp(aliases['partials'], combo)]
    # print(f'{combo} -> {product}: {ratio}')
    utseq.append(UT(tempus=ratio, prolatio='p', tempo=bpm, beat=beat))

print(utseq.time)
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------

dyn_ranges = {
    'ping2': DynamicRange(-25, -10)
}

seen_partials = set()
for i, (combo, ut) in enumerate(zip(path, utseq)):
    root_partial = hx.combo_to_product[vtp(aliases['partials'], combo)]
    synths = vtp(aliases['insts'], combo)
    if combo in seen_partials:
        root_partial = 1 / root_partial
    else:
        seen_partials.add(root_partial)
    
    # list of the synths that are not perc or glitch
    for drone in [synth for synth in synths if synth not in ['perc', 'ping']]:
        dur = sum(ut.durations)
        atk = np.random.uniform(0.167, 0.833) * dur
        f_scale = np.random.choice([0.5, 1.0]) if drone == 'drone' else np.random.choice([2.0, 1.0, 0.5])
        sch.add_new_event(drone, ut.onsets[0],
                        duration = dur,
                        atk = atk,
                        rel = dur * np.interp(atk, [dur*0.167, dur*0.833], [0.33, 1.33]),
                        freq = f_scale * root_freq * fold_interval(root_partial),
                        amp = db_amp(-16) if drone == 'drone' else np.random.uniform(0.002,0.2))
    # list of the synths that are perc or glitch
    short_insts = {
        'perc': ['zerpPerc', 'pitchPerc', 'kick', 'snare', 'perc', 'perc2'],
        'ping': ['ping2']
    }
    for short in [synth for synth in synths if synth in ['perc', 'ping']]:
        sub_path = ComboNetTraversal(comb_net).play(combo, ut.tempus.numerator)
        ratios = cycle([hx.combo_to_ratio[vtp(aliases['partials'], cp)] for cp in sub_path])
        amps = cycle(envs.line(len(ut), -11, 0))
        seen_ratios = set()
        synth_cyc = cycle(np.random.choice(short_insts[short], len(ut), True))
        for j, event in enumerate(ut):
            if np.random.rand() < 0.5:
                continue
            ratio = next(ratios)
            if ratio in seen_ratios:
                ratio = 1 / ratio
            else:
                seen_ratios.add(ratio)
            freq = root_freq * fold_interval(root_partial) * ratio
            if short == 'ping':
                freq = fold_freq(freq, 333.0)
            syn = next(synth_cyc)
            sch.add_new_event(syn, event['start'],
                            duration = event['duration'] * 0.25,
                            freq = freq,
                            ratio = float(fold_interval(root_partial) * ratio),
                            seed = np.random.randint(0, 1000) * float(ratio),
                            amp = db_amp(next(amps)) * (0.08 if short == 'perc' else 1.0))

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# --------------------------------
sch.run()
