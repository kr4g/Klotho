from klotho.topos.sequences import Norg
from klotho.tonos import fold_interval, fold_freq
from klotho.chronos import seconds_to_hmsms
# from klotho.aikous.messaging import Scheduler
from utils.messaging import Scheduler
from klotho.tonos.combination_product_sets import NKany
from klotho.aikous.expression.enevelopes import *
from klotho.tonos import find_first_octave
from klotho.topos.graphs.networks import ComboNet
from klotho.topos.graphs.networks.algorithms import ComboNetTraversal
from klotho.topos import autoref_rotmat
from klotho.aikous.expression import amp_freq_scale, db_amp
from klotho.topos.sequences import Pattern
from klotho.chronos.rhythm_trees import auto_subdiv
from klotho.chronos.rhythm_pairs import RhythmPair as RP
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq, TemporalSequenceBlock as UTMat
import networkx as nx
import math
from fractions import Fraction

HARMONICS = [
    1, 129, 65, 131, 33, 133, 67, 135, 17, 137, 69, 139, 35, 141, 71, 143, 9,
    145, 73, 147, 37, 149, 75, 151, 19, 153, 77, 155, 39, 157, 79, 159, 5, 161,
    81, 163, 41, 165, 83, 167, 21, 169, 85, 171, 43, 173, 87, 175, 11, 177, 89,
    179, 45, 181, 91, 183, 23, 185, 93, 187, 47, 189, 95, 191, 3, 193, 97, 195,
    49, 197, 99, 199, 25, 201, 101, 203, 51, 205, 103, 207, 13, 209, 105, 211,
    53, 213, 107, 215, 27, 217, 109, 219, 55, 221, 111, 223, 7, 225, 113, 227,
    57, 229, 115, 231, 29, 233, 117, 235, 59, 237, 119, 239, 15, 241, 121, 243,
    61, 245, 123, 247, 31, 249, 125, 251, 63, 253, 127, 255
]

G = nx.Graph()
G.add_nodes_from(HARMONICS)
for i in range(len(HARMONICS)):
    for j in range(i + 1, len(HARMONICS)):
        harmonic1 = HARMONICS[i]
        harmonic2 = HARMONICS[j]

        gcd = math.gcd(harmonic1, harmonic2)

        if gcd > 1:# and gcd in HARMONICS:
            G.add_edge(harmonic1, harmonic2)

def get_connected_nodes(graph, node):
    if node in graph:
        connected_nodes = list(graph.neighbors(node))
        return connected_nodes
    else:
        print(f"Node {node} does not exist in the graph.")
        return []

node = 13
connected_nodes = get_connected_nodes(G, node)
# print(connected_nodes)
pairs = {n: n // node for n in connected_nodes}

hx = NKany(connected_nodes, 2, normalized=False)
combnet = ComboNet(hx)
# print(hx)
from itertools import cycle
path = cycle(ComboNetTraversal(combnet).play(list(hx.combos)[0], 32))
# print(path)

import random
def assign_harmonic_to_duration(duration, dur_range, available_harmonics):
    min_event_dur, max_event_dur = dur_range
    normalized_duration = (duration - min_event_dur) / (max_event_dur - min_event_dur) if max_event_dur != min_event_dur else 0.5
    
    harmonic_weights = []
    for h in available_harmonics:
        octave = find_first_octave(h)
        # Shorter durations increase probability of higher harmonics
        weight = abs(1 - normalized_duration) * (octave + 1) + normalized_duration * (1 / (octave + 1))
        harmonic_weights.append((h, weight))
    
    total_weight = sum(w for _, w in harmonic_weights)
    probabilities = [w/total_weight for _, w in harmonic_weights]
    
    return random.choices(available_harmonics, weights=probabilities, k=1)[0]


import numpy as np
scheduler = Scheduler()

# for i, p in enumerate(path):
#     # print(p)
#     # print(Fraction(p[0], p[1]))
#     start = i * 3
#     fund = 333.0
#     freqs = [
#         fund * fold_interval(hx.combo_to_ratio[p]) * 2,
#         fund * fold_interval(hx.combo_to_product[p]) * 0.25,
#         fund * fold_interval(p[0]),
#         fund * fold_interval(p[1])
#     ]
#     for freq in freqs:
#         amp = 0.025 * amp_freq_scale(freq) * np.interp(freq, [333, 1332], [1, 0.25])
#         scheduler.new_event(
#             synth_name  = 'test',
#             start       = start,
#             freq        = freq,
#             amp         = amp,
#             attackTime  = 2,
#             releaseTime = 1,
#             pan         = np.sin(start * freq)
#         )

def process_utmat(utmat, **kwargs):
    for i, utseq in enumerate(utmat):
        root = kwargs['fund'] * kwargs['registers'][i]        
        min_ut_dur, max_ut_dur = min(d for d in utseq.durations), max(d for d in utseq.durations)
        process_utseq(utseq, utseq_index=i, utseq_dur=utseq.duration,
                      min_ut_dur=min_ut_dur, max_ut_dur=max_ut_dur,
                      root=root,
                      **kwargs)

def process_utseq(utseq, **kwargs):
    for j, ut in enumerate(utseq):
        ut_index = j
        min_event_dur, max_event_dur = min(d for d in ut.durations), max(d for d in ut.durations)
        match kwargs['utseq_index']:
            case 0:
                if True:#ut.duration < kwargs['max_ut_dur']:
                    process_ut_pluck(ut, ut_index=ut_index, utseq_len=len(utseq),
                                    min_event_dur=min_event_dur, max_event_dur=max_event_dur,
                                    **kwargs)
                # elif ut.duration == kwargs['max_ut_dur']:
                #     process_ut_vosim(ut, ut_index=ut_index,
                #                     min_event_dur=min_event_dur, max_event_dur=max_event_dur,
                #                     **kwargs)

def process_ut_pluck(ut, **kwargs):
    for k, event in enumerate(ut):
        if k == 0:
            continue 
        
        duration = event['duration']
        dur_scale = np.interp(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), (0, 1))
        
        # harmonic = assign_harmonic_to_duration(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), HARMONICS)
        interval = 1
        freq = kwargs['root'] * interval
        freq_scale = map_curve(freq, [kwargs['fund'], kwargs['fund'] * kwargs['registers'][-1] * 2], [0, 1])
        
        base_amp = map_curve(kwargs['ut_index'], (0, kwargs['utseq_len']-1), (0.25, 0.5), -4)
        amp_swell = map_curve(k, (0, len(ut)-1), (0.25, 1), 0)
        amp_freq = map_curve(freq_scale, (0, 1), (1, 0.75), -2)
        amp_dur = map_curve(dur_scale, (0, 1), (1, 0.5))
        amp = base_amp * amp_swell * amp_freq * amp_dur
        amp = np.clip(amp, 0, 1)
        
        attack_time = map_curve(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), (duration * 0.05, duration * 0.333), 2)
        release_time = map_curve(attack_time, (0.001, duration * 0.333), (duration * 0.667, duration), 2)
        
        base_mod_curve = map_curve(freq_scale, (0, 1), (-8, -2), -2) + map_curve(dur_scale, (0, 1), (-8, 0), 2)
        mod_curve = base_mod_curve + map_curve(amp, (0, 1), (0, -8), -4)
        mod_curve += np.random.uniform(-4, 2)
        
        scheduler.new_event(
            synth_name  = 'pingSine',
            start       = event['start'],
            freq        = freq,
            amp         = amp,
            attackTime  = attack_time,
            releaseTime = release_time,
            modCurve    = mod_curve,
            pan         = np.sin(event['start'] * freq)
        )

def process_ut_vosim(ut, **kwargs):
    uid = None
    for k, event in enumerate(ut):
        duration = event['duration']
        harmonic = assign_harmonic_to_duration(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), HARMONICS)
        interval = fold_interval(harmonic)
        freq = kwargs['root'] * interval
        lag = event['duration'] * 0.5
        if uid is None:
            uid = scheduler.new_event(
                synth_name  = 'vosim',
                start       = event['start'],
                trigFreq    = kwargs['fund'],
                freq        = freq,
                amp         = 0.005,
                pan         = np.sin(event['start'] * freq),
                lag         = lag
            )
        elif k == len(ut) - 1:
            scheduler.set_event(uid, start=event['start'] + duration, gate=0)
        else:
            scheduler.set_event(uid, start=event['start'], freq=freq)
        

s_mat = autoref_rotmat((3,5,7,11))
utmat = UTMat.from_tree_mat(s_mat, subdiv=True, tempo=62, beat='1/4')
equave = fold_interval(interval=31)
registers = [equave**i for i in range(utmat.size)]
fund = 66.0

print('=' * 40, end='\n\n')
for n, utseq in enumerate(utmat):
    print(f'Row {n} UTSeq:\n')
    for m, ut in enumerate(utseq):
        print(f'UT{m}:\n{ut}', end='')
    print()
    print('=' * 40, end='\n\n')

# process_utmat(utmat, fund=fund, equave=equave, registers=registers)

# scheduler.run()
