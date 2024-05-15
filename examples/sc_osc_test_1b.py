import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from itertools import cycle
import numpy as np

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
from allopy.chronos import temporal_units as u_temp
from allopy.tonos.JI import combination_sets as cps
from allopy.tonos import fold_freq, fold_interval
from allopy.aikous import amp_freq_scale, db_amp

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

meas_denom = 2
beat = '1/8'
bpm = 76
prolat = (11, 7, 3, 5, 2)
anacrus = u_temp.UT(tempus=f'1/{meas_denom}', prolatio='r', tempo=bpm, beat=beat)
auto_mat = rt_alg.autoref_rotmat(lst=prolat, mode='S')

tb = u_temp.TB()
for i, row in enumerate(auto_mat):
    seq = u_temp.UTSeq()
    for e in row:
        # D, S = e[0], (-e[1][0],) + e[1][1:]
        D, S = e[0], rt_alg.subdivide_tree(e[1], i + 1)
        seq += u_temp.UT(tempus   = r_trees.Meas((D, meas_denom)),
                         prolatio = S,
                         tempo    = bpm,
                         beat     = beat)
    tb += seq

perc_synths = [
    cycle(['a1', 'a3', 'a5', 'a2', 'hiss2']),
    cycle(['reverseTwang', 'reverseTwang2', 'glitch1', 'glitch2', 'glitch3'])
]
impacts = cycle(['bassDrum', 'impact'])
sweeps = cycle(['feedback1', 'feedback2'])
chimes = cycle(['chime', 'glockenspiel', 'celeste', 'vibraphone'])

offset = anacrus.duration
scheduler.add_new_event('preScrape', 0, duration=offset)
scheduler.add_new_event('swordReverse', 0, duration=offset)
scheduler.add_new_event('reverseCymbal', 0, duration=offset)
hx = cps.Hexany()
factors = cycle(hx.factors)
for i, utseq in enumerate(tb): # for each UTSeq in the TB
    ratios = cycle(hx.ratios)
    f = fold_interval(next(factors), n_equaves=4)
    perc_synth = next(perc_synths[i % 2])
    impact = next(impacts)
    for j, (ut_onset, ut_dur) in enumerate(utseq): # for each UT in the UTSeq
        ut_onset += offset
        scheduler.add_new_event('reverseCymbal', ut_onset, duration=ut_dur)
        scheduler.add_new_event('preScrape', ut_onset, duration=ut_dur)
        scheduler.add_new_event(next(sweeps), ut_onset, duration=ut_dur, amp=0.15)
        scheduler.add_new_event(impact, ut_onset, amp=0.15)
        chime = next(chimes)
        for k, (start, duration) in enumerate(utseq.uts[j]): # for each event in the UT
            start += ut_onset
            if duration < 0 or k == 0: continue
            ratio = next(ratios)
            freq = fold_freq(333.0 * ratio * f, lower=333.0, upper=1332.0)
            if j == 0:
                scheduler.add_new_event('glitchRandom2', start, duration=0.05, freq=freq, amp=0.2)
            elif j in {1,3}:
                chime = 'chime' if j == 1 else chime
                scheduler.add_new_event(chime, start, duration=duration, freq=freq, amp=0.1)
            else:
                freq = np.interp(freq, [333.0, 1332.0], [10.406, 41.625])
                scheduler.add_new_event(perc_synth, start, duration=0.05, freq=freq, amp=0.2)

scheduler.send_all_events()
