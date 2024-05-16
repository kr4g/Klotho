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
from allopy.topos.sequences import Norg

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
meas_denom = 2
beat = '1/16'
bpm = 72
prolat = (11, 7, 3, 5, 2)
anacrus = u_temp.UT(tempus=f'1/{meas_denom}', prolatio='r', tempo=bpm, beat=beat)
auto_mat = rt_alg.autoref_rotmat(lst=prolat, mode='D')
tb = u_temp.TB.from_tree_mat(matrix     = auto_mat,
                             meas_denom = meas_denom,
                             subdiv     = True,
                             tempo      = bpm,
                             beat       = beat)
ek = cps.Eikosany()
factors = cycle(ek.factors)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL MATERIAL -------------------------------------------------------------
synths = cycle(['chime', 'glockenspiel', 'celeste', 'vibraphone', 'syn'])
risers = cycle(['preScrape', 'feedback2', 'swordReverse', 'reverseCymbal'])

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
for i, utseq in enumerate(tb):
    synth = next(synths)
    riser = next(risers)
    n = 0
    for j, (ut_onset, ut_dur) in enumerate(utseq):
        f = fold_interval(next(factors), n_equaves=2)
        f = 1 / f if j % 2 == 0 else f
        p = fold_interval(i + 1 if j % 2 == 0 else 1 / (i + 1), n_equaves=1)
        riser_freq = 666.0 * p * f
        scheduler.add_new_event(riser, ut_onset, duration=ut_dur, freq=riser_freq, amp=db_amp(-38), atk=ut_dur*0.833)
        for k, (start, duration) in enumerate(utseq.uts[j]):
            if k == 0: continue
            n += 1
            idx = Norg.inf_num(n) % len(ek.ratios)
            ratio = ek.ratios[idx] if idx >= 0 else 1 / ek.ratios[abs(idx)]
            # idx = Norg.inf_num(n * 53 + n * 27)
            # ratio = fold_interval(idx + 1 if idx >= 0 else 1/(abs(idx) + 1), n_equaves=1)
            freq = f * 1332.0 * ratio
            scheduler.add_new_event(synth, start,
                                    duration = duration*1.333,
                                    freq     = freq,
                                    amp      = db_amp(-19)),

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()
