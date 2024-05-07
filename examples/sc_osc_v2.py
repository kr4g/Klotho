import sys
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from pythonosc import udp_client, osc_message_builder
from uuid import uuid4

from itertools import cycle
import numpy as np

from allopy.chronos import rhythm_trees as r_trees
from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
from allopy.chronos import temporal_units as u_temp
from allopy.tonos.JI import combination_sets as cps
from allopy.tonos import fold_freq, fold_interval
from allopy.topos.sequences import Norg
from allopy.aikous import amp_freq_scale

client = udp_client.SimpleUDPClient('127.0.0.1', 57120)

events = []

def add_new_synth(synth_name, start, **params):
    args = [synth_name, start] + [item for sublist in params.items() for item in sublist]
    events.append(('new', args))

def add_new_synth_with_id(synth_name, start, **params):
    uid = '\\' + str(uuid4())
    args = [uid, synth_name, start] + [item for sublist in params.items() for item in sublist]
    events.append(('new_id', args))
    return uid

def add_set_event(uid, start, **params):
    args = [uid, start] + [item for sublist in params.items() for item in sublist]
    events.append(('set', args))

def send_all_events():
    for event_type, content in events:
        msg = osc_message_builder.OscMessageBuilder(address='/storeEvent')
        msg.add_arg(event_type)
        for item in content:
            msg.add_arg(item)
        client.send(msg.build())
    events.clear()
    print('Events have been sent.')

# tempus = '10/1'
# duration = 3
# bpm = 36
# beat = '1/16'
# hx = cps.Pentadekany()
# factors = cycle(hx.factors)
# rts = [
#     r_trees.RT(duration       = duration,
#                time_signature = tempus,
#                subdivisions   = row) for row in rt_alg.autoref_rotmat((11,7,17,5,3,19))
# ]
# synths = cycle(['celeste', 'glockenspiel', 'syn'])
# for i, rt in enumerate(rts):
#     amps = cycle([np.random.uniform(0.005, 0.05) for _ in range(np.random.randint(3, 7))])
#     f = next(factors)
#     synth = next(synths)
#     ut = u_temp.UT.from_tree(rt, tempo=bpm, beat=beat)
#     min_dur, max_dur = min(ut.durations), max(ut.durations)
#     for j, (start, duration) in enumerate(ut):
#         if duration < 0: continue
#         if j == 0: continue
#         partial = Norg.inf_num(j - 1)
#         partial += 1 if partial >= 0 else -1
#         ratio = fold_interval(partial if partial > 0 else 1/abs(partial), equave=2.0, n_equaves=1)
#         freq = fold_freq(f * ratio * 166.5, lower=83.25, upper=2664.0)
#         amp = next(amps) * amp_freq_scale(freq) * np.interp(freq, [83.25, 2664.0], [1.0, 0.35])
#         dur_scale = np.interp(amp, [0.005*0.35, 0.05], [1.333, 0.667])
#         add_new_synth(synth, start, dur=duration*dur_scale, freq=freq, amp=amp)


uid = add_new_synth_with_id('theremin', 0, dur=15, freq=220, amp=0.05)
add_set_event(uid, 5, freq=880)
add_set_event(uid, 10, freq=440)

send_all_events()
