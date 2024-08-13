import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from allopy.chronos.temporal_units import UTSeq, TemporalUnit as UT
from allopy.chronos import seconds_to_hmsms
from allopy.aikous import db_amp

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

import numpy as np

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
tempus = '4/4'
tempus_rest = '1/4'
beat = '1/4'
bpm = 92

utseq = UTSeq(
    (
        UT(tempus=tempus, prolatio=(3,2,7,5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,2,(7,(3,1,1)),5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,1)),2,(7,(3,1,1)),5), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,1)),(2,(3,3,2)),(7,(3,1,1)),(5,(3,5))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,(1,(1,1,1)))),(2,(3,(3,(1,1,1,1)),2)),(7,(3,1,1)),(5,(3,(5,(3,5))))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,(1,(1,1,(1,(1,1,1)))))),(2,(3,(3,((2,(5,4)),1,1)),2)),(7,(3,(1,(1,1)),1)),(5,(3,(5,(3,5))))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,(1,(1,1,(1,(1,1,(1,(7,(5,(3,5)))))))))),(2,(3,(3,((2,((5,(3,5)),4)),1,1)),2)),(7,(3,(1,(1,(1,(1,1,1)))),1)),(5,(3,(5,(3,5))))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=((3,(1,(1,(1,1,(1,(1,1,(1,(7,(5,((3,(1,(1,(1,1,1)))),5)))))))))),(2,(3,(3,((2,((5,(3,(5,(1,1,1)))),4)),1,1)),2)),(7,(3,(1,(1,(1,(1,1,1)))),1)),(5,((3,(1,1)),(5,(3,5))))), tempo=bpm, beat=beat),
        UT(tempus=tempus_rest, prolatio='r', tempo=bpm, beat=beat),
    )
)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
print(f'{utseq.size} UTs, {len(utseq)} events\nDur: {seconds_to_hmsms(utseq.duration)}')
seed = np.random.randint(1000)
for j, ut in enumerate(utseq):
    min_dur = min(ut.durations)
    max_dur = max(ut.durations)
    for i, event in enumerate(ut):
        if event['duration'] < 0: continue
        # dur_scale = np.interp(event['duration'], [min_dur, max_dur], [1.0, 0.667])
        duration = np.interp(event['duration'], [min_dur, max_dur], [min_dur*0.833, max_dur*0.333])
        scheduler.add_new_event('random', event['start'], duration=duration, amp=db_amp(0), seed=seed*event['duration'])
        # scheduler.add_new_event('kick', event['start'], amp=db_amp(-8))

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()
