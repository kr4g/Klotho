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

bpm = 36
duration = 36
tempus = '13/1'
beat = '1/16'

p_mat = rt_alg.autoref_rotmat((5,17,7,13,3,11), 'G')
rts = [r_trees.RT(duration=duration, time_signature=tempus, subdivisions=row) for row in p_mat]

hx = cps.Pentadekany()
factors = cycle(hx.factors)
events = []
synths = cycle(['vibraphone', 'celeste', 'glockenspiel', 'syn'])
for i, rt in enumerate(rts):
    amps = cycle([np.random.uniform(0.005, 0.07) for _ in range(np.random.randint(3, 7))])
    for j, (start, duration) in enumerate(ut.UT.from_tree(rt, tempo=bpm, beat=beat)):
        # if duration < 0: continue
        if j == 0:
            # if i == 0: 
            #     events.append(('bassDrum', start, 'amp', 0.05))
            continue
        # idx = Norg.inf_num(j - 1) % len(hx.ratios)
        # ratio = fold_interval(hx.ratios[idx] if idx >= 0 else 1/hx.ratios[abs(idx)], equave=2.0, n_equaves=1)
        partial = Norg.inf_num((j - 1) * 3 + 7)
        partial += 1 if partial >= 0 else -1
        ratio = fold_interval(partial if partial > 0 else 1/abs(partial), equave=2.0, n_equaves=1)
        f = next(factors)
        freq = fold_freq(f * 166.5 * ratio, lower=83.25, upper=5328)
        amp = next(amps) * amp_freq_scale(freq) * np.interp(freq, [83.25, 5328], [1.0, 0.35])
        synth = next(synths)
        events.append((synth, start, 'dur', duration*1.33, 'freq', freq, 'amp', amp))

# m_freq = cycle([fold_freq(666.0 * hx.ratios[Norg.inf_num(i) % len(hx.ratios)], lower=166.5, upper=999.0) for i in range(11)])
# for i, (start, duration) in enumerate(ut.UT.from_tree(rt_mel, tempo=36, beat='1/16')):
#     if duration < 0 or i < 5: continue
#     freq = next(m_freq)
#     events.append(('theremin', start, 'dur', duration, 'freq', freq, 'amp', 0.03))

for event in events:
    structured_event = [event[0], event[1]] + list(event[2:])
    client.send_message("/storeEvent", structured_event)

print("Events have been sent.")
