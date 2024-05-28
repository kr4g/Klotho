import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
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

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
meas_denom = 2
beat = '1/8'
bpm = 82
prolat = (11, 7, 3, 5, 2)
anacrus = u_temp.UT(tempus=f'1/{meas_denom}', prolatio='r', tempo=bpm, beat=beat)
auto_mat = rt_alg.autoref_rotmat(lst=prolat, mode='S')
tb = u_temp.TB.from_tree_mat(matrix     = auto_mat,
                             meas_denom = meas_denom,
                             subdiv     = True,
                             tempo      = bpm,
                             beat       = beat)
hx = cps.Hexany()
factors = cycle(hx.factors)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL MATERIAL -------------------------------------------------------------
perc_synths = cycle([
    cycle(['a1', 'a2', 'a3', 'a5', 'glitchRandom2']),
    cycle(['reverseTwang', 'reverseTwang2', 'glitch1', 'glitch2', 'glitch3'])
])
impacts = cycle(['bassDrum', 'impact'])
sweeps = cycle(['feedback1', 'feedback2', 'riser'])
chimes = cycle(['chime', 'glockenspiel', 'celeste', 'vibraphone'])

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
offset = anacrus.duration
scheduler.add_new_event('preScrape', 0, duration=offset)
scheduler.add_new_event('swordReverse', 0, duration=offset)
scheduler.add_new_event('reverseCymbal', 0, duration=offset)
for i, utseq in enumerate(tb): # for each UTSeq in the TB
    ratios = cycle(hx.ratios)
    f = fold_interval(next(factors), n_equaves=4)
    perc_synth = next(next(perc_synths))
    impact = next(impacts)
    for j, (ut_onset, ut_dur) in enumerate(utseq): # for each UT in the UTSeq
        ut_onset += offset
        if i == 0:
            scheduler.add_new_event('reverseCymbal', ut_onset, duration=ut_dur)
            scheduler.add_new_event('preScrape', ut_onset, duration=ut_dur)
            scheduler.add_new_event(next(sweeps), ut_onset, duration=ut_dur, amp=db_amp(-19))
            scheduler.add_new_event(impact, ut_onset, amp=db_amp(-8))
        chime = next(chimes)
        for k, (start, duration) in enumerate(utseq.uts[j]): # for each event in the UT
            start += offset
            if duration < 0 or k == 0: continue
            ratio = next(ratios)
            freq = fold_freq(333.0 * ratio * f, lower=333.0, upper=1332.0)
            if j == 0:
                scheduler.add_new_event('glitchRandom2', start, duration=0.05, freq=freq, amp=db_amp(-20))
            elif j in {1,3}:
                chime = 'chime' if j == 1 else chime
                scheduler.add_new_event(chime, start, duration=duration, freq=freq, amp=db_amp(-19))
            else:
                freq = np.interp(freq, [333.0, 1332.0], [10.406, 41.625])
                perc_synth = 'sonar' if i == 4 else perc_synth
                dur = duration if i == 4 else 0.1
                scheduler.add_new_event(perc_synth, start, duration=dur, amp=db_amp(-24))

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()
