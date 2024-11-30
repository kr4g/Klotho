from klotho.topos.graphs.trees import Tree
from klotho.topos.graphs.trees.algorithms import rotate_children
from klotho.tonos.harmonic_trees import HarmonicTree as HT
from klotho.tonos.harmonic_trees.algorithms import measure_partials
from klotho.tonos import fold_interval, fold_freq
from fractions import Fraction
S = ((5, ((3, (4, 3)), 2)), (7, ((5, (5, 4)), (3, (7, 9)), 2)), (11, ((7, ((5, (7, 5)), (3, (5, 7)), 2)), (5, (3, 2)), (3, (5, 7)), 2)))
# ht1 = HT(children=S)
# ht2 = HT(children=rotate_children(S))
# print([str(r) for r in ht.harmonics])
# print([str(r) for r in measure_partials(S)])
# print('-' * 10)
# print([str(r) for r in ht.ratios])
# print([str(fold_interval(Fraction(r))) for r in measure_partials(S)])

import numpy as np
from klotho.chronos.temporal_units import TemporalUnit as UT
from klotho.aikous.expression.dynamics import db_amp, amp_freq_scale
# ut1 = UT(span=8, tempus='4/4', prolatio=S, tempo=60, beat='1/4')
# ut2 = UT(span=8, tempus='4/4', prolatio=rotate_children(S), tempo=60, beat='1/4')

from utils.messaging import Scheduler
scheduler = Scheduler()
fund = 55.0
tree = Tree(1, children=S)
for i in range(len(tree.leaf_nodes)):
    _S = rotate_children(S, i)
    ht = HT(children=_S)

    # seen_ratios = set()
    for k, elem in enumerate(UT(span=12, tempus='4/4', prolatio=_S, tempo=36, beat='1/8')):
        ratio = ht.ratios[k]
        # if ratio in seen_ratios:
        #     ratio = (1 / ratio) * 2
        # seen_ratios.add(ratio)
        freq = fold_freq(fund * ratio * 2**i, fund, 12_000)
        base_amp = np.interp(i, [0, len(tree.leaf_nodes) - 1], [db_amp(-15), db_amp(-80)])
        scheduler.new_event(
            synth_name='pingSine',
            start=elem['start'],
            attackTime=elem['duration'] * 0.033,
            releaseTime=elem['duration'] * 1.083,
            amp=base_amp * amp_freq_scale(freq),
            amAmt=np.random.uniform(0.1, 0.9),
            amFreq=np.random.uniform(3, 17),
            freq=freq, 
            pan=np.sin(np.pi * freq + elem['start'])
        )

scheduler.run()
