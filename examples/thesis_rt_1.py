import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from allopy.chronos.temporal_units import UTSeq, TemporalUnit as UT

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
meas_denom = 1
tempus = '4/4'
beat = '1/4'
bpm = 132

# ut = UT(tempus=tempus, prolatio=(3,1,2,1), tempo=bpm, beat=beat)
# print(ut)

utseq = UTSeq((
    UT(tempus=tempus, prolatio=(1,1,1,1), tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio=(3,1,1,1), tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio=(3,1,2,1), tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio=(3,5,2,1), tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
    UT(tempus=tempus, prolatio=((3, (3, (7, (5, 3, 2)))), (5, (3, 1, (2, ((5, (7, 5, 3)), 3)))), (2, (2, 1, 1, 2, 1)), (1, ((3, (5, 3, 2)), (3, (3, 2)), 2))), tempo=bpm, beat=beat),
    ))


# ------------------------------------------------------------------------------------
# COMPOSITIONAL MATERIAL -------------------------------------------------------------

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
for j, (ut_start, ut_duration) in enumerate(utseq):
    for i, (start, duration) in enumerate(utseq.uts[j]):
        if duration < 0: continue
        scheduler.add_new_event('glitchRandom2', start, duration=duration*0.5)
        # scheduler.add_new_event('bassDrum', start, duration=duration*0.25)
        scheduler.add_new_event('a1', start, duration=duration*0.25)

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()
