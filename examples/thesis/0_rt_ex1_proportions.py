import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from allopy.chronos.temporal_units import UTSeq, TemporalUnit as UT
from allopy.aikous import db_amp
from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
tempus = '4/4'
tempus_rest = '2/4'
beat = '1/4'
bpm = 92

# ut = UT(tempus=tempus, prolatio=(3,1,2,1), tempo=bpm, beat=beat)
# print(ut)

utseq = UTSeq(
    (
        UT(tempus=tempus, prolatio=(1,1,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(1,2,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(1,2,1,5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,2,1,5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,2,7,5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
    )
)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
print(utseq.duration)
seed = np.random.randint(1000)
for j, ut in enumerate(utseq):
    dur_scale = np.interp(j, [0, utseq.size], [0.167, 0.667])
    for i, event in enumerate(ut):
        if event['duration'] < 0: continue
        duration = event['duration'] * dur_scale
        scheduler.add_new_event('random', event['start'], duration=duration, amp=db_amp(-11), seed=seed*ut.prolationis[i])
        scheduler.add_new_event('random', event['start'], duration=duration, amp=db_amp(-17), seed=seed*duration)
        scheduler.add_new_event('kick', event['start'], amp=db_amp(-3))

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()