import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from pythonosc import udp_client

from itertools import cycle
import numpy as np

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
from allopy.chronos import temporal_units as ut
from allopy.tonos.JI import combination_sets as cps
from allopy.tonos import fold_freq, fold_interval
from allopy.topos.sequences import Norg
from allopy.aikous import amp_freq_scale

client = udp_client.SimpleUDPClient('127.0.0.1', 57120)

tempus = '10/1'
duration = 1
bpm = 36
beat = '1/16'
hx = cps.Pentadekany()
factors = cycle(hx.factors)
rts = [r_trees.RT(duration=duration, time_signature=tempus, subdivisions=row) for row in rt_alg.autoref_rotmat((11,7,17,5,3,19))]
synths = cycle(['celeste', 'glockenspiel', 'vibraphone', 'syn'])
events = []
for i, rt in enumerate(rts):
    amps = cycle([np.random.uniform(0.005, 0.05) for _ in range(np.random.randint(3, 7))])
    f = next(factors)
    synth = next(synths)
    for j, (start, duration) in enumerate(ut.UT.from_tree(rt, tempo=bpm, beat=beat)):
        if duration < 0: continue
        if j == 0: continue
        partial = Norg.inf_num((j - 1) * 7 + 5)
        partial += 1 if partial >= 0 else -1
        ratio = fold_interval(partial if partial > 0 else 1/abs(partial), equave=2.0, n_equaves=1)
        freq = fold_freq(f * ratio * 166.5, lower=83.25, upper=2664.0)
        amp = next(amps) * amp_freq_scale(freq) * np.interp(freq, [83.25, 2664.0], [1.0, 0.3])
        events.append((synth, start, 'dur', duration*1.33, 'freq', freq, 'amp', amp))

for event in events:
    structured_event = [event[0], event[1]] + list(event[2:])
    client.send_message('/storeEvent', structured_event)

print('Events have been sent.')
