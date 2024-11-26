from klotho.topos.sequences import Norg
from klotho.tonos import fold_interval, fold_freq
from klotho.chronos import seconds_to_hmsms, cycles_to_frequency
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
from klotho.chronos.temporal_units import TemporalUnit as UT, TemporalUnitSequence as UTSeq, TemporalUnitSequenceBlock as UTMat
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

node = 5
connected_nodes = get_connected_nodes(G, node)
# print(connected_nodes)
pairs = {n: n // node for n in connected_nodes}

hx = NKany(connected_nodes, 2, normalized=False)
combnet = ComboNet(hx)

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
            case _:
                if True:#ut.duration < kwargs['max_ut_dur']:
                    process_ut_ping(ut, ut_index=ut_index, utseq_len=len(utseq),
                                    min_event_dur=min_event_dur, max_event_dur=max_event_dur,
                                    **kwargs)

def process_ut_ping(ut, **kwargs):
    for k, event in enumerate(ut):
        if kwargs['utseq_index'] == 0 and k == 0:
            continue 
        
        duration = event['duration']
        dur_scale = np.interp(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), (0, 1))
        
        interval = hx.combo_to_ratio[next(kwargs['path'])]
        if np.random.uniform() > 0.5:
            interval = (1 / interval) * 2
        freq = kwargs['root'] * interval
        freq_scale = map_curve(kwargs['root'], [kwargs['fund'], kwargs['fund'] * kwargs['registers'][-1]], [0, 1])
        
        base_amp = map_curve(kwargs['ut_index'], (0, kwargs['utseq_len']-1), (0.65, 0.95), 0)
        amp_swell = map_curve(k, (0, len(ut)-1), (0.5, 1), -2)
        amp_freq = map_curve(freq_scale, (0, 1), (1, 0.25), -2)
        amp_dur = map_curve(dur_scale, (0, 1), (1, 0.5), 0)
        amp = base_amp * amp_swell * amp_freq * amp_dur
        amp = np.clip(amp, 0, 1) * amp_freq_scale(freq)
        
        attack_time = map_curve(duration, (kwargs['min_event_dur'], kwargs['max_event_dur']), (duration * 0.001, duration * 0.167), 2)
        release_time = map_curve(attack_time, (duration * 0.001, duration * 0.167), (duration * 0.667, duration * 3.167), 2)
        
        amFreq = np.random.uniform(3, 13)
        amAmt = np.random.uniform(0.15, 0.95)
        
        scheduler.new_event(
            synth_name  = 'pingSine',
            start       = event['start'],
            freq        = freq,
            amp         = amp,
            attackTime  = attack_time,
            releaseTime = release_time,
            amFreq      = amFreq,
            amAmt       = amAmt,
            pan         = np.sin(event['start'] * kwargs['root'])
        )

s_mat = autoref_rotmat((11,9,7,5,4))
utmat = UTMat.from_tree_mat(s_mat, subdiv=True, tempo=66, beat='1/4')
equave = fold_interval(63)
registers = [equave**i for i in range(utmat.size)]
fund = 166.5

from itertools import cycle
path = cycle(ComboNetTraversal(combnet).play(list(hx.combos)[0], utmat.utseqs[0].size))

print('=' * 40, end='\n\n')
for n, utseq in enumerate(utmat):
    print(f'Row {n} UTSeq: {seconds_to_hmsms(utseq.time[0])} - {seconds_to_hmsms(utseq.time[1])} ({seconds_to_hmsms(utseq.duration)})\n')
    for m, ut in enumerate(utseq):
        print(f'UT{m}:\n{ut}', end='')
    print()
    print('=' * 40, end='\n\n')

process_utmat(utmat, fund=fund, equave=equave, registers=registers, path=path)

print(seconds_to_hmsms(utmat.utseqs[0].duration), end='\n\n')

scheduler.run()
