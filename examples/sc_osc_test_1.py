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

duration = 2
meas = '10/1'
beat = '1/4'
bpm = 67
prolat = (11, 7, 3, 5, 2)
anacrus = (1, sum(prolat))
auto_mat = rt_alg.autoref_rotmat(lst=prolat, mode='S')

uts = {
    f'layer_{i}' : u_temp.UT(duration = duration,
                             tempus   = meas,
                             prolatio = row,
                             tempo    = bpm,
                             beat     = beat
    ) for i, row in enumerate(auto_mat)
}

uts['bd'] = u_temp.UT(duration = duration, tempus = meas, prolatio = prolat, tempo = bpm, beat = beat)

risers = cycle(['preScrape', 'swordReverse', 'riser', 'reverseCymbal'])
ratios = cycle([1, 7/10])

offset = u_temp.UT(duration = duration, tempus = meas, prolatio = anacrus, tempo = bpm, beat = beat).durations[0]

scheduler.add_new_event(next(risers), 0, duration=offset)

for i, (start, duration) in enumerate(uts['bd']):
    start = start + offset
    
    synth = next(risers)
    scheduler.add_new_event(synth, start, duration=abs(duration))
    
    if duration < 0: continue
    
    scheduler.add_new_event('bassDrum', start)
    
    if i < 3:
        n = 1 if synth == 'riser' else 2
        scheduler.add_new_event(f'feedback{n}', start, duration=duration, freq=333.0)
    else:
        if i < len(prolat) - 2:
            scheduler.add_new_event(f'rumble', start, duration=duration)
        else:
            r = next(ratios)
            scheduler.add_new_event('choir', start, freq=83.25 * r, duration=duration)

cp_set = cps.Hexany()
root_ratios = cycle([float(fold_interval(f, n_equaves=3)) for f in cp_set.factors])
for i, (k, v) in enumerate(uts.items()):
    if k == 'bd': continue
    ratios = cycle([float(fold_interval(r)) for r in cp_set.ratios])
    r = next(root_ratios)
    for j, (start, duration) in enumerate(uts[k]):
        start = start + offset
        ratio = next(ratios)
        if j % len(prolat) == 0: continue
        if uts[k].onsets[3 * len(prolat)] + offset < start < uts[k].onsets[4 * len(prolat)] + offset:
            synth = 'sword'
        else:
            synth = 'chime'
        scheduler.add_new_event(synth, start, duration=duration, freq=166.5 * r * ratio, amp=0.25)

scheduler.send_all_events()
