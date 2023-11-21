# examples/iso_examples.py
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from allopy import chronos
from allopy import tonos
from allopy.topos import topos
from allopy.aikous import aikous
from allopy.skora import skora

FILEPATH = skora.set_score_path()

import numpy as np
import pandas as pd
from IPython.display import display
from sympy.utilities.iterables import cartes

def ratio_pulse_pairs(metric_ratios: list, pulses: list, bpm: float = 60) -> list:
    '''
    Given a list of metric beat ratios and a list of pulses, generates a sequence of 
    events that cycles through combinations of each metric ratio repeated for each
    pulse in the pulse list.
    '''
    duration_pulse_pairs = []
    CPS = topos.cartesian_iso_pairs(metric_ratios, pulses)
    for i, ((ratio_1, ratio_2), nPulse) in enumerate(CPS):
        tempo    = chronos.metric_modulation(bpm, ratio_1, ratio_2)
        duration = chronos.beat_duration(1/10, tempo)
        duration_pulse_pairs.append((duration, nPulse))
    return duration_pulse_pairs
    # borked
    # return [(chronos.beat_duration(1/10, chronos.metric_modulation(bpm,
    #                                                                ratio_1,
    #                                                                ratio_2)),
    #          nPulse
    #     ) for ((ratio_1, ratio_2), nPulse) in CPS]

def metric_modulation_ex(metric_ratios: list, pulses: list, bpm: float = 60):
    '''
    '''
    duration_pulse_pairs = ratio_pulse_pairs(metric_ratios, pulses, bpm)
    start_time = 0.0
    rows_list = []
    freq_ratios = [tonos.cents_to_ratio(pc * 100) for pc in [6, 0, -7, -1]]
    # octaves = [0.5, 1.0, 2.0, 3.0]
    octaves = [0.25, 0.5, 1.0, 2.0]
    np.random.seed(999)
    np.random.shuffle(octaves)
    i_freq = 0
    np.random.seed(999)
    attackTime = min([p[0] for p in duration_pulse_pairs])
    for i, (duration, n) in enumerate(duration_pulse_pairs):
        dur        = duration * 0.667
        amplitude  = np.random.choice([aikous.DYNAMICS.pp.max, aikous.DYNAMICS.mp.min,
                                       aikous.DYNAMICS.mf.min, aikous.DYNAMICS.f.max]) * 0.96
        root_freq  = (999 * 1.9692**-2) * tonos.cents_to_ratio(1067)**octaves[i % 4]
        pan        = np.random.uniform(-1.0, 1.0)
        amFunc     = np.random.randint(0, 3)
        reverb_min = np.interp(i, [0, len(duration_pulse_pairs)], [0.0, 0.03])
        reverb_max = np.interp(i, [0, len(duration_pulse_pairs)], [reverb_min, 0.11])
        for j in range(n):
            amRatio = np.random.uniform(0.9692, 1.167)
            # amRatio = np.random.uniform(0.333, 1.9692)
            reverberation = np.interp(j, [0, n], [reverb_min, reverb_max])
            new_row = {
                'start'         : start_time,
                'dur'           : dur,
                'synthName'     : 'OscAM',
                'amplitude'     : amplitude * np.interp(j, [0, n], [0.0833, 1.0]),
                'frequency'     : root_freq * freq_ratios[i_freq % len(freq_ratios)],
                'attackTime'    : dur * 0.25,
                'releaseTime'   : dur * 0.13 + (n * 0.37),
                'sustain'       : 0.833,
                'pan'           : pan,
                'amFunc'        : amFunc,
                'am1'           : 0.0,
                'am2'           : 1.0,
                'amRise'        : dur,
                'amRatio'       : amRatio,
                'reverberation' : reverberation,
                'visualMode'    : amFunc,
            }
            rows_list.append(new_row)
            start_time += duration
            i_freq += 1
    pfields = ['start', 'dur', 'synthName', 'amplitude', 'frequency', 'attackTime', 'releaseTime', 'sustain', 'pan', 'amFunc', 'am1', 'am2', 'amRise', 'amRatio', 'reverberation', 'visualMode']
    score_df = skora.make_score_df(pfields=pfields)
    score_df = skora.concat_rows(score_df, rows_list)
    return score_df

if __name__ == '__main__':
    # Example 00
    # metric_ratios = (1/5, 1/7, 1/4, 1/11, 1/3, 1/13)
    metric_ratios = (1/5, 1/7, 1/3)
    pulses = (5, 3, 13, 7)
    tempo = 66
    score_df_00 = metric_modulation_ex(metric_ratios, pulses, tempo)
    filename = 'metric_modulation_ex_01.synthSequence'
    skora.df_to_synthSeq(score_df_00, os.path.join(FILEPATH, filename))
