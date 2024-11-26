from klotho.chronos.temporal_units import TemporalUnit as UT
from klotho.topos import autoref, autoref_rotmat
import numpy as np

from utils.messaging import Scheduler

scheduler = Scheduler()

S = (7,5,4,3)
S = autoref_rotmat(S)
ut = UT(duration=4, tempus='4/4', prolatio=S[0], tempo=54, beat='1/4')
print(ut)

uid = None
for k, event in enumerate(ut):
    if uid is None:
        uid = scheduler.new_event(
            synth_name  = 'triTher',
            start       = event['start'],
            freq        = 220,
            amp         = 0.25,
            lag         = event['duration'] * 0.333,
        )
    else:
        scheduler.set_event(
            uid         = uid,
            start       = event['start'],
            freq        = 220 * np.random.uniform(0.9, 1.5),
            lag         = event['duration'] * 0.333,
        )
scheduler.set_event(
    uid         = uid,
    start       = ut.time[1],
    gate        = 0,
)

scheduler.run()