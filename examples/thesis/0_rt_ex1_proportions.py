# import sys
# from pathlib import Path

# root_path = Path(__file__).parent.parent.parent
# sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
# --------
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq, TemporalSequenceBlock as UTBlock
from klotho.chronos import seconds_to_hmsms
from klotho.tonos import fold_interval
from klotho.aikous.expression import db_amp
from klotho.tonos.harmonic_trees import *
# from klotho.skora.graphs import *
# from klotho.skora.animation.animate import *

# from utils.data_structures import scheduler as sch
from klotho.aikous.messaging import Scheduler
scheduler = Scheduler()

import numpy as np

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
tempus = '4/4'
beat = '1/4'
bpm = 72

_S = (
    # (1,1,1,1),
    # (1,2,1,1),
    # (1,2,1,5),
    # (3,2,1,5),
    # (3,2,7,5),
    # (3,2,(7,(3,1,1)),5),
    ((3,(2,3,1)),2,(7,(3,1,(1,(1,1,1)))),(5,(5,3,(4,(5,3,2))))),
)

# utblock = UTBlock(

utseq = UTSeq(
    [UT(tempus=tempus, prolatio=s, tempo=bpm, beat=beat) for s in _S]
)

h_trees = [
    HarmonicTree(root=1, children=s, equave=2, n_equave=1) for s in _S
]


# for i, ut in enumerate(utseq):
#     if len(ut.ratios) == 1: continue
#     ut.offset = 0
#     animate_temporal_unit(ut, True, False, file_name=f'ut_{i}c')
# animate_temporal_units(utseq.uts, True, False, file_name='utblock')
# print(seconds_to_hmsms(utseq.time))
# plot_graph(graph_tree(utseq.uts[-2].tempus, utseq.uts[-2].prolationis))

# _ut = UT(tempus=tempus, prolatio=(3,2,(7,(3,1,1)),5), tempo=bpm, beat=beat)
# animate_temporal_unit(_ut, True, False, file_name='ut6')

synths = {
    1: 'kick',
    2: 'snare',
    3: 'perc2',
    5: 'hat',
    7: 'crash',
}

def process_ut(ut, ht):
    for j, event in enumerate(ut):
        # print(event)
        if event['duration'] < 0: continue
        duration = event['duration']
        freq1 = 333.0 * ht.partials[j]
        freq2 = 5 * 333.0 * (1 / ht.partials[j])
        scheduler.new_event('test', event['start'], freq=freq1, amp=db_amp(-8))
        scheduler.new_event('test', event['start'], freq=freq2, amp=db_amp(-16))

def process_utseq(utseq, h_trees):
    for i, ut in enumerate(utseq):
        process_ut(ut, h_trees[i])


print(seconds_to_hmsms(utseq.time))
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------
seed = np.random.randint(1000)
process_utseq(utseq, h_trees)

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# --------------------------------
scheduler.run()
