import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from itertools import cycle
import numpy as np
from sympy import prime

from utils.data_structures import scheduler as sch

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
from allopy.chronos import temporal_units as u_temp
from allopy.tonos.JI import combination_sets as cps
from allopy.tonos import fold_freq, fold_interval
from allopy.topos.sequences import Norg
from allopy.aikous import amp_freq_scale, db_amp

scheduler = sch.Scheduler()

tempus = '13/1'
duration = 5
bpm = 36
beat = '1/16'
S = (5,17,7,11,3,13)
rts = [
    r_trees.RT(duration       = duration,
               time_signature = tempus,
               subdivisions   = row) for row in rt_alg.autoref_rotmat(S)
]

factors = cycle([1] + [prime(n + 2) for n in range(len(rts) - 1)])
synths = cycle(['celeste', 'glockenspiel', 'vibraphone', 'chime', 'syn'])
for i, rt in enumerate(rts):
    amps = cycle([np.random.uniform(0.009, 0.07) for _ in range(np.random.randint(3, 7))])
    f = next(factors)
    synth = next(synths)
    ut = u_temp.UT.from_tree(rt, tempo=bpm, beat=beat)
    min_dur, max_dur = min(ut.durations), max(ut.durations)
    for j, (start, duration) in enumerate(ut):
        if duration < 0 or j == 0: continue
        partial = Norg.inf_num(j - 1)
        partial += 1 if partial >= 0 else -1
        ratio = fold_interval(partial if partial > 0 else 1/abs(partial), equave=2.0, n_equaves=1)
        freq = fold_freq(f * ratio * 166.5, lower=83.25, upper=2664.0)
        amp = next(amps) * amp_freq_scale(freq) * np.interp(freq, [83.25, 2664.0], [1.0, 0.45])
        dur_scale = np.interp(amp, [0.005*0.35, 0.05], [1.833, 1.167])
        scheduler.add_new_event(synth, start, dur=duration*dur_scale, freq=freq, amp=amp)

cp_set = cps.Hexany()
r_pair = rt_alg.rhythm_pair(S)
prolat = tuple((s, S) for s in r_pair)
ut = u_temp.UT(tempus   = tempus,
               prolatio = prolat,
               tempo    = bpm,
               beat     = beat)
uid = None
min_dur, max_dur = min(ut.durations), max(ut.durations)
roots = cycle(333.0 * fold_interval(r, n_equaves=1) for r in cp_set.factors)
for i, (start, duration) in enumerate(ut):
    if i < len(S): continue
    idx = Norg.inf_num(i * 7 + 13) % len(cp_set.ratios)
    ratio = fold_interval(cp_set.ratios[idx] if idx > 0 else 1/cp_set.ratios[abs(idx)], n_equaves=1)
    if i % len(S) == 0:
        root = next(roots)
    freq = fold_freq(ratio * root, lower=166.5, upper=2664.0)
    if uid is None:
        uid = scheduler.add_new_event_with_id('theremin', start, dur=ut.duration, freq=freq, amp=0.05, ampLag=0, atk=duration*0.667)
    else:
        lag_scale = np.interp(duration, [min_dur, max_dur], [0.33, 0.833])
        amp = np.random.uniform(0.02, 0.35) * amp_freq_scale(freq) * np.interp(freq, [166.5, 2664.0], [1.0, 0.25])
        scheduler.add_set_event(uid, start, freq=freq, freqLag=duration*lag_scale, amp=amp**1.25, ampLag=duration*(lag_scale**0.5))
    if i == len(ut.durations) - 1:
        scheduler.add_set_event(uid, start, amp=0.0, ampLag=duration*0.833)
scheduler.send_all_events()
