import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from itertools import cycle
import numpy as np
from sympy import prime

from utils.data_structures import scheduler as sch

from fractions import Fraction
from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
from allopy.chronos import temporal_units as u_temp
from allopy.tonos.JI import combination_sets as cps
from allopy.tonos import fold_freq, fold_interval
from allopy.topos.sequences import Norg
from allopy.aikous import amp_freq_scale, db_amp

scheduler = sch.Scheduler()

meas_denom = 2
beat = '1/4'
bpm = 67
prolat = (11, 7, 3, 5, 2)
anacrus = u_temp.UT(tempus=f'1/{meas_denom}', prolatio='r', tempo=bpm, beat=beat)
auto_mat = rt_alg.autoref_rotmat(lst=prolat, mode='S')

tb = u_temp.TB()
for i, row in enumerate(auto_mat):
    seq = u_temp.UTSeq()
    for e in row:
        D, S = e[0], (-e[1][0],) + e[1][1:]
        seq += u_temp.UT(tempus   = r_trees.Meas((D, meas_denom)),
                         prolatio = S,
                         tempo    = bpm,
                         beat     = beat)
    tb += seq

offset = anacrus.duration
scheduler.add_new_event('preScrape', 0, duration=offset)
scheduler.add_new_event('swordReverse', 0, duration=offset)
scheduler.add_new_event('reverseCymbal', 0, duration=offset)
hx = cps.Hexany()
factors = cycle(hx.factors)
for i, utseq in enumerate(tb): # for each UTSeq in the TB
    ratios = cycle(hx.ratios)
    f = fold_interval(next(factors), n_equaves=4)
    for j, (onset, _) in enumerate(utseq): # for each UT in the UTSeq
        onset += offset
        scheduler.add_new_event('bassDrum', onset, amp=0.15)
        for k, (start, duration) in enumerate(utseq.uts[j]): # for each event in the UT
            start += onset
            if duration < 0: continue
            ratio = next(ratios)
            freq = fold_freq(333.0 * ratio * f, lower=333.0, upper=1332.0)
            scheduler.add_new_event('chime', start, duration=duration, freq=freq, amp=0.2)

scheduler.send_all_events()
