import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.topos import autoref
from klotho.chronos.temporal_units import TemporalUnitSequence, TemporalUnit as UT
from klotho.tonos.combination_product_sets import nkany as NKany
from klotho.chronos.rhythm_trees import rhythm_pair as rp

from klotho.skora.animation import animate

from utils.data_structures import scheduler as sch
scheduler = sch.Scheduler()

from itertools import cycle
import numpy as np
from math import prod

# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
def rhythm_pair(lst:tuple, is_MM:bool=True) -> tuple:
    total_product = prod(lst)
    if is_MM:
        sequences = [np.arange(0, total_product + 1, total_product // x) for x in lst]
    else:
        sequences = [np.arange(0, total_product + 1, x) for x in lst]
    combined_sequence = np.unique(np.concatenate(sequences))
    deltas = np.diff(combined_sequence)
    return tuple(deltas)

meas_denom = 1
tempus = '4/4'
beat = '1/4'
bpm = 132

# ut = UT(tempus=tempus, prolatio=(3,1,2,1), tempo=bpm, beat=beat)
# print(ut)

utseq = TemporalUnitSequence(
    (
        UT(tempus=tempus, prolatio=(1,1,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(1,2,1,1), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(1,2,1,5), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,2,1,5), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio=(3,2,7,5), tempo=bpm, beat=beat),
        UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
    )
)
# utseq = TemporalUnitSequence(
#     (
#         UT(tempus=tempus, prolatio=(3,2,7,5), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=(3,2,(7,(3,1,1)),5), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=(3,2,(7,(3,(1,(1,1)),1)),5), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=((3,(2,1,1)),2,(7,(3,(1,(1,1)),1)),5), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=((3,(2,1,1)),2,(7,(3,(1,(1,1)),1)),(5,(2,2,3,5))), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=((3,(2,1,1)),2,(7,(3,(1,(1,(1,(3,1,1)))),1)),(5,(2,2,3,5))), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio=((3,(2,1,1)),2,(7,(3,(1,(1,(1,(3,1,1)))),1)),(5,(2,2,(3,(1,1)),5))), tempo=bpm, beat=beat),
#         UT(tempus=tempus, prolatio='r', tempo=bpm, beat=beat),
#     )
# )

ek = NKany.Pentadekany()
# print(ek)

# ------------------------------------------------------------------------------------
# COMPOSITIONAL MATERIAL -------------------------------------------------------------

# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
print(utseq.duration)
for j, ut in enumerate(utseq):
    # min_dur = min(ut.durations)
    # max_dur = max(ut.durations)
    dur_scale = np.interp(j, [0, utseq.size], [0.167, 0.667])
    for i, event in enumerate(ut):
        if event['duration'] < 0: continue
        duration = event['duration'] * dur_scale
        scheduler.new_synth('random', event['start'], duration=duration, seed=np.random.randint(1000))
        # scheduler.new_synth('bassDrum', event['start'])

# ------------

# ut_0 = UT(tempus=tempus, duration=16, prolatio=autoref(rp((3,5,7,11), True)), tempo=28, beat='1/8')
# print(ut_0.duration)
# ratios = list(ek.ratios)
# np.random.shuffle(ratios)
# rat_seq = cycle(ratios)
# synth_cycle = cycle(['glockenspiel', 'vibraphone', 'celeste', 'chime'])
# for i, event in enumerate(ut_0):
#     r = next(rat_seq)
#     synth = next(synth_cycle)
#     root = 666.0 * 2.0
#     root = root * 2.0 if synth == 'chime' else root
#     amp_scale = 0.5
#     if np.random.uniform() < 0.5:
#         r = 1 / r
#         synth = 'syn'
#         root = 666.0 * np.random.choice([0.5, 1.0, 1.0, 2.0, 4.0])
#         amp_scale = np.interp(root, [333.0, 1332.0], [1.167, 0.83])
#     freq = root * r
#     amp = np.random.uniform(0.005, 0.1)
#     dur_scale = np.interp(amp, [0.005, 0.1], [13.0, 3.0])
#     scheduler.new_synth(synth, event['start'], duration=event['duration']*dur_scale, freq=freq, amp=amp*amp_scale)

# # ------------------------------------------------------------------------------------
# # SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
scheduler.send_all_events()