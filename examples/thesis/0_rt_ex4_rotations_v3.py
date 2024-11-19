import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

# -------------------------------------------------------------------------------------
# IMPORTS -----------------------------------------------------------------------------
from klotho.topos import autoref
from klotho.topos.graphs.trees.algorithms import factor_children
from klotho.chronos.temporal_units import TemporalUnitSequence, TemporalSequenceBlock, TemporalUnit as UT
from klotho.chronos.rhythm_trees.rt import *
from klotho.chronos.rhythm_trees.algorithms.rt_algs import auto_subdiv
from klotho.chronos import seconds_to_hmsms, beat_duration
from klotho.tonos import fold_interval, fold_freq
from klotho.tonos.harmonic_trees.algorithms import measure_partials
from klotho.aikous.expression import db_amp

from klotho.skora.graphs import *
from klotho.skora.animation.animate import *

# from utils.data_structures import scheduler as sch
from klotho.aikous.messaging import Scheduler
scheduler = Scheduler()

import numpy as np
from math import gcd, lcm
from functools import reduce
from itertools import cycle
import os

def ut_dur(ut:UT):
    return beat_duration(str(ut.tempus), bpm=ut.tempo, beat_ratio=ut.beat)

def ut_seq_dur(utseq:TemporalUnitSequence):
    return sum(ut_dur(ut) for ut in utseq)

def swell(n, min_val=0.0, max_val=1.0):
    up = np.linspace(min_val, max_val, n//2, endpoint=False)
    down = np.linspace(max_val, min_val, n//2 + n % 2, endpoint=True)
    result = np.concatenate([up, down])
    return result

from PIL import Image, ImageDraw, ImageFont
import textwrap

def save_tuple_as_image(t, output_file, font_size=100):
    # Convert the tuple to a string with commas replaced by spaces
    text = str(t).replace(',', ' ')
    
    # Create a Matplotlib figure
    plt.figure(figsize=(len(text) * 0.1, 2))  # Width depends on text length; adjust as needed
    plt.text(0.5, 0.5, text, fontsize=font_size, ha='center', va='center')
    
    # Remove axes and padding
    plt.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    # Save the image
    plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
    plt.close()



# -------------------------------------------------------------------------------------
# PRE-COMPOSITIONAL MATERIAL ----------------------------------------------------------
# ---------------------------
tempus = '11/1'
# tempus = '1/1'
beat = '1/8'
# bpm = 48/11
bpm = 48

S = ((17, ((15, ((13, (13, 9, 5, 2)), 7)), (13, (7, 5, 2)))), (13, (6, 9)))

rt_prime = RhythmTree(meas=tempus, subdivisions=S)
# print(rt_prime)
# print(len(rt_prime))
# print('-' * 80)

rots = []
ani = []
for i in range(len(factor_children(rt_prime.subdivisions))):
# for i in range(5):
    # print(rotate_tree(rt_prime, i))
    rots.append(TemporalUnitSequence((UT.from_tree(rotate_tree(rt_prime, i), tempo=bpm, beat=beat),)))
    # ani.append(UT.from_tree(rotate_tree(rt_prime, i), tempo=bpm, beat=beat))
    # t = ani[-1].prolationis
    # save_tuple_as_image(t, f'/Users/ryanmillett/Klotho/examples/thesis/S_rot_{i}.png')

# create_gif([f'/Users/ryanmillett/Klotho/examples/thesis/S_rot_{i}.png' for i in range(len(rots))], '/Users/ryanmillett/Klotho/examples/thesis/S_rotations.gif', 500)

animate_temporal_units(ani, save_mp4=True, file_name='rt_prime_rotations_stack_real')
tb = TemporalSequenceBlock(tuple(rots))
# utseq = TemporalUnitSequence(rots)
# print(f'{ut_seq_dur(utseq)} ({seconds_to_hmsms(ut_seq_dur(utseq))})')

# output_dir = "/Users/ryanmillett/Klotho/examples"
# os.makedirs(output_dir, exist_ok=True)
# image_files = []
# image_files2 = []
# for i, utseq in enumerate(tb):
#     ut = utseq.uts[0]
#     # print(i, utseq.uts[0])
#     output_file = os.path.join(output_dir, f"graph_rot_{i}.png")
#     plot_graph(graph_tree(ut.tempus, ut.prolationis), output_file)
#     image_files.append(output_file)
    
#     prop_file = os.path.join(output_dir, f"prop_rot_{i}")
#     animate_temporal_unit(ut, save_mp4=False, save_png=True, file_name=prop_file) # this saves a png file in the same dir
#     image_files2.append(f"{prop_file}.png")

# duration_per_frame = 500
# gif_file = os.path.join(output_dir, 'graph_rot_animation.gif')
# create_gif(image_files, gif_file, duration_per_frame)
# gif_file = os.path.join(output_dir, 'graph_rot__props_animation.gif')
# create_gif(image_files2, gif_file, duration_per_frame)
    
# freqs = cycle([np.random.uniform(333.0, 666.0)*0.2 for _ in range(len(rt_prime))])
# freqs = cycle([333.0 * 0.167 * fold_interval(Fraction(p)) for p in measure_partials(S)])

print(tb.duration)
# ------------------------------------------------------------------------------------
# COMPOSITIONAL PROCESS --------------------------------------------------------------
# ----------------------
u_ids = {}
synths = cycle(['bassoon', 'frenchhorn', 'clarinet', 'oboe', 'flute'])
min_freqs = {'flute': 300, 'oboe': 300, 'clarinet': 120, 'bassoon': 50, 'frenchhorn': 250}
max_freqs = {'flute': 3500, 'oboe': 1200, 'clarinet': 1000, 'bassoon': 350, 'frenchhorn': 700}
max_amps = {'flute': -8, 'oboe': -25, 'clarinet': -12, 'bassoon': -15, 'frenchhorn': -3}
for i, utseq in enumerate(tb):
    synth = next(synths)
    seed = np.random.randint(0, 1000)
    pan = np.interp(i, [0, tb.size], [-1, 1])
    u_ids[i] = scheduler.new_event_with_id(synth, -0.1, gate=0, amp=db_amp(-80), pan=pan)
    for j, ut in enumerate(utseq):
        freqs = cycle([13.0 * fold_interval(Fraction(p), n_equaves=3) for p in measure_partials(ut.prolationis)])
        vibDepth_seq = swell(len(ut), 0.0, np.interp(i, [0, tb.size], [0.001, 0.01]))
        vibRate_seq = swell(len(ut), 5.0, np.interp(i, [0, tb.size], [8.0, 11.0]))
        brightness = swell(len(ut), 1.0, 10.0)
        breathiness = swell(len(ut), 0.8, 0.1)
        min_dur = min(ut.durations)
        max_dur = max(ut.durations)
        for k, event in enumerate(ut):
            if k == 0: continue
            duration = np.interp(event['duration'], [min_dur, max_dur], [min_dur, max_dur*0.67])
            freq = next(freqs) * fold_interval((i + 1), n_equaves=4)
            freq = fold_freq(freq, min_freqs[synth], max_freqs[synth])
            
            scheduler.set_event(u_ids[i], event['start'], gate=1,
                                freq=freq, freqLag=np.interp(i, [0, tb.size], [0.0, min_dur*0.4]),
                                amp=db_amp(max_amps[synth] - i*0.33)*1.067, ampLag=duration,
                                vibDepth=np.random.uniform(0.0, vibDepth_seq[k]), vibRate=np.random.uniform(0.0, vibRate_seq[k]),
                                brightness=brightness[k],
                                breathiness=breathiness[k])
            
            alpha = np.interp(i, [0, tb.size], [0.667, 0.969])
            scheduler.set_event(u_ids[i], event['start'] + duration*alpha, gate=1,
                                amp=db_amp(-80), ampLag=duration*(1-alpha))
            
            if k == len(ut) - 1:
                scheduler.set_event(u_ids[i], event['start'] + duration, gate=0)

# ------------------------------------------------------------------------------------
# SEND COMPOSITION TO SYNTHESIZER ----------------------------------------------------
# --------------------------------
scheduler.run()