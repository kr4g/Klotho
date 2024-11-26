from klotho.topos.sequences import Norg
from klotho.tonos import fold_interval, fold_freq
from klotho.chronos import seconds_to_hmsms
# from klotho.aikous.messaging import Scheduler
from utils.messaging import Scheduler
from klotho import topos
from klotho.aikous.expression import amp_freq_scale, db_amp
from klotho.topos.sequences import Pattern
from klotho.chronos.rhythm_trees import auto_subdiv
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq, TemporalUnitSequenceBlock as UTMat

mat = topos.autoref_rotmat((3,5,7,11,13), mode='G')

utmat = UTMat().from_tree_mat(mat, subdiv=True, tempo=36, beat='1/4')

# for utseq in utmat:
#     print(utseq.uts, end='\n\n')
#     print(seconds_to_hmsms(utseq.duration), end='\n\n')
#     print('-' * 10)

scheduler = Scheduler()

import numpy as np
def create_patterns(list1, list2, n):
    len1, len2 = len(list1), len(list2)
    nested_lists = []
    for i in range(n):
        proportion1 = 1 - (i / (n - 1))
        proportion2 = i / (n - 1)
        num1 = int(round(proportion1 * len1))
        num2 = int(round(proportion2 * len2))
        nested_lists.append(Pattern(list1[:num1] + list2[:num2]))
    return nested_lists

MAJ_3RDS = [83, 165, 41, 163, 81, 161, 5, 159, 79, 157]
MAJ_2NDS = [73, 145, 9, 143, 71, 141, 35]
intervals = create_patterns(MAJ_3RDS, MAJ_2NDS, utmat.size)

fund = 166.5
for i, utseq in enumerate(utmat):
    interval = fold_interval(next(intervals[i]))
    octave = fold_interval(63)**i
    idx = 0
    all_durs = [d for _ut in utseq.uts for d in _ut.durations]
    min_dur, max_dur = min(all_durs), max(all_durs)
    for j, ut in enumerate(utseq.uts):
        for k, event in enumerate(ut):
            start = event['start']
            dur = event['duration']
            
            norg_num = Norg.inf_num(idx)
            idx += 1
            if norg_num == 0:
                interval = fold_interval(next(intervals[i]))
            freq = fold_freq(fund * octave * (interval**norg_num), lower=66.0, upper=5000.0)
            
            base_amp = np.interp(k, [0, len(ut) - 1], [0.0001, 0.25])
            freq_scale = amp_freq_scale(freq)**2 * np.interp(freq, [66.0, 5000.0], [1.5, 0.00001])
            activity_scale = np.interp(dur, [min_dur, max_dur], [1.5, 0.0005])
            amp = base_amp * freq_scale**2 * activity_scale * 0.667
            
            atk = np.interp(amp, [0.0001, 0.25 * 1.5], [dur * 0.25, 0.001])
            rel = dur * np.interp(atk, [dur * 0.25, 0.001], [0.167, 1.667])
            
            pan_mult = np.interp(dur, [min_dur, max_dur], [6.667, 1.333])
            pan = np.sin(np.pi * start * pan_mult)
            
            scheduler.new_event('test', start=start, freq=freq, amp=amp, attackTime=atk, releaseTime=rel, pan=pan)
scheduler.run()
