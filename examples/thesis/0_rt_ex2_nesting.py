import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq
from klotho.chronos import seconds_to_hmsms
from klotho.aikous.expression import db_amp
from klotho.skora.graphs import *
from klotho.skora.animation.animate import *

# from utils.data_structures import scheduler as sch
from klotho.aikous.messaging import Scheduler
scheduler = Scheduler()

import numpy as np

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
tempus = '4/4'
tempus_rest = '1/2'
beat = '1/4'
bpm = 72

utseq = UTSeq(
    (
        # UT(tempus=tempus, prolatio=(3,2,7,5), tempo=bpm, beat=beat),
        # UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        # UT(tempus=tempus, prolatio=(3,2,(7,(3,1,1)),5), tempo=bpm, beat=beat),
        # UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        # UT(tempus=tempus, prolatio=((3,(1,1)),2,(7,((3,(5,4,3)),1,1)),(5,(3,5))), tempo=bpm, beat=beat),
        # UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        # UT(tempus=tempus, prolatio=((3,(1,1)),(2,(3,3,2)),(7,((3,(5,4,3)),1,(1,(1,)*4))),(5,(3,5))), tempo=bpm, beat=beat),
        # UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,((1,(1,1,(1,(3,4)),1)),1)),(2,(3,(3,(5,4,3)),2)),(7,((3,(5,(4,(1,)*5),(3,((1,(1,)*5),1)))),(1,(7,5,(8,(7,2,3)),3)),(1,(1,)*4))),(5,(3,(5,(3,5))))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
    )
)

# print(f'{utseq.size} UTs, {len(utseq)} events\nDur: {seconds_to_hmsms(utseq.duration)}')
print(utseq.time)
# plot_graph(graph_tree(utseq.uts[-2].tempus, utseq.uts[-2].prolationis))
_ut = utseq.uts[-2]
# _ut.tempo = bpm
# _ut.offset = 0
animate_temporal_unit(utseq.uts[-2], save_mp4=True, file_name='ut_complex')
# # ------------------------------------------------------------------------------------
# # COMPOSITIONAL PROCESS --------------------------------------------------------------
# seed = np.random.randint(1000)
# for j, ut in enumerate(utseq):
#     min_dur = min(ut.durations)
#     max_dur = max(ut.durations)
#     for i, event in enumerate(ut):
#         if event['duration'] < 0: continue
#         # dur_scale = np.interp(event['duration'], [min_dur, max_dur], [1.0, 0.667])
#         duration = min_dur#np.interp(event['duration'], [min_dur, max_dur], [min_dur, min_dur*3])
#         scheduler.new_synth('random', event['start'], duration=duration, amp=db_amp(-6), seed=seed*event['duration'])
#         # scheduler.new_synth('kick', event['start'], amp=db_amp(-8))

# # # ------------------------------------------------------------------------------------
# # # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# scheduler.run()
