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

def materials(metric_ratios: list, pulses: list, bpm: float = 60) -> list:
    '''
    Given a list of metric beat ratios and a list of pulses, generates a sequence of 
    events that cycles through combinations of each metric ratio repeated for each
    pulse in the pulse list.
    '''
    duration_pulse_pairs = []
    CPS = topos.cartesian_iso_pairs(metric_ratios, pulses)
    current_bpm = bpm
    temp_map  = np.append(np.linspace(bpm, bpm*6.33, len(metric_ratios)**2),                          # Section I
                          np.linspace(bpm / 1.167, bpm*9.66, len(metric_ratios)**2 - len(pulses)*3))  # Section II    
    for i, ((ratio_1, ratio_2), nPulse) in enumerate(CPS):
        tempo    = chronos.metric_modulation(current_bpm, ratio_1, ratio_2)
        duration = chronos.beat_duration(1/13, tempo)
        duration_pulse_pairs.append((duration, nPulse))
        if i < len(temp_map):
            current_bpm = temp_map[i]
        else:  # Section III to the end
            current_bpm = np.interp(i, [0, len(CPS)], [bpm * 3, bpm * 1.167])
    return duration_pulse_pairs
    # borked
    # return [(chronos.beat_duration(1/10, chronos.metric_modulation(bpm,
    #                                                                ratio_1,
    #                                                                ratio_2)),
    #          nPulse
    #     ) for ((ratio_1, ratio_2), nPulse) in CPS]

def composition(metric_ratios: list, pulses: list, bpm: float = 60):
    '''
    '''
    duration_pulse_pairs = materials(metric_ratios, pulses, bpm)
    start_time = 0.0
    rows_list = []
    pitch_contour = [6, 0, -7, -1]
    freq_ratios     = [tonos.cents_to_ratio(sc * 100) for sc in pitch_contour]
    freq_ratios_inv = [tonos.cents_to_ratio(-1 * sc * 100) for sc in pitch_contour]
    octaves = np.array([0.25, 2.0, 0.5, 1.0])
    oct_warp = 1.0
    # octaves = [0.25, 0.5, 1.0, 2.0]
    # np.random.seed(999)
    # np.random.shuffle(octaves)

    start_time_II = sum([d*p for d, p in duration_pulse_pairs[:len(metric_ratios)**2 + 1]])

    i_freq = 0
    np.random.seed(616)
    attackTime = min([p[0] for p in duration_pulse_pairs])
    for i, (duration, n_Pulses) in enumerate(duration_pulse_pairs):
        CONDITION_I  = i <= len(metric_ratios)**2# or i >= len(duration_pulse_pairs) - len(pulses)*3
        CONDITION_II = i >= len(duration_pulse_pairs) - len(pulses)*3
        CONDITION_III = not CONDITION_I and not CONDITION_II

        dur        = duration * 0.667
        dynamic    = np.random.choice([aikous.DYNAMICS.ppp, aikous.DYNAMICS.p, aikous.DYNAMICS.mf, aikous.DYNAMICS.ff]) # * 0.9692
        freqs      = freq_ratios # freq_ratios_inv if i % len(pulses) == 0 else freq_ratios
        root_freq  = (999 * 1.9692**-2) * freqs[i % len(freqs)] * tonos.cents_to_ratio(1133)**(octaves[i % 4] * oct_warp)
        pan        = np.random.uniform(-1.0, 1.0)
        amFunc     = np.random.choice((0, 2))
        amRatio    = np.random.uniform(0.9692, 1.167)
        reverb_min = np.interp(i, [0, len(duration_pulse_pairs)], [0.0, 0.09])
        reverb_max = np.interp(i, [0, len(duration_pulse_pairs)], [reverb_min, 0.31])
        # MAKE PULSES
        for n_pulse in range(n_Pulses):
            frequency = root_freq
            if CONDITION_I or CONDITION_II:  
                # the pitch sequence cycles per pulse and we use 'OscAM'
                amplitude  = np.random.uniform(dynamic.min, dynamic.max) * np.interp(n_pulse, [0, n_Pulses], [0.0833, 1.0])
                frequency  = root_freq * freq_ratios[i_freq % len(freq_ratios)]

            else: # implicit CONDITION_III
                # the pitch sequence cycles per new pulse set and we use 'AddSyn'
                amplitude  = np.random.uniform(dynamic.min, dynamic.max) * np.interp(n_pulse, [0, n_Pulses], [1.0, 0.0833])
                freqs      = freq_ratios_inv
                amFunc     = np.random.choice((1, 3))
                np.random.shuffle(octaves)
                oct_warp   = np.random.uniform(0.9692, 1.167)
                amRatio    = np.random.uniform(0.9692, 1.167)
            # amRatio = np.random.uniform(0.333, 1.9692)
            reverberation = np.interp(n_pulse, [0, n_Pulses], [reverb_min, reverb_max])
            new_row = {
                'start'         : start_time,
                'dur'           : dur,
                'synthName'     : 'OscAM',
                'amplitude'     : amplitude,
                'frequency'     : frequency,
                'attackTime'    : np.interp(n_pulse, [0, n_Pulses], [dur * 0.0333, dur * 0.167]),
                # 'releaseTime'   : dur * 0.13 + (n_pulse * 0.37),
                'releaseTime'   : np.interp(n_pulse, [0, n_Pulses], [dur * 0.13, dur * 6.667]),
                'sustain'       : 0.833,
                'pan'           : pan,
                'amFunc'        : amFunc,
                'am1'           : 1.0,
                'am2'           : 0.0,
                'amRise'        : dur,
                'amRatio'       : amRatio,
                'reverberation' : reverberation,
                # 'visualMode'    : amFunc,
            }
            rows_list.append(new_row)
            start_time += duration
            i_freq += 1

        if CONDITION_III:  # add rhythm trees across pulse cycle meters (use temporal units to slice total duration space of COND_III)
            dur       = duration * n_Pulses
            amplitude = np.random.uniform(dynamic.min, dynamic.max) * 0.667
            frequency = root_freq * (2 * oct_warp) + np.random.uniform(-99.999, 66.667)*np.random.randint(0,i)
            # if start_time_II == 0:
            #     start_time_II += dur
            #     continue # we can do this here because this is the last condition before the next iteration
            # reverberation = np.interp(n_pulse, [0, n_Pulses], [reverb_min, reverb_max])
            # TODO:
            # if total duration is from the longer durations in the cycle, iteratively compose a rhythm tree
            # else, add a cresc accent
            new_row = {
                'start'         : start_time_II,
                'dur'           : dur,
                'synthName'     : 'OscAM',
                'amplitude'     : amplitude,
                'frequency'     : frequency,
                'attackTime'    : dur,
                # 'releaseTime'   : dur * 0.13 + (n_pulse * 0.37),
                'releaseTime'   : dur * 3,
                'sustain'       : 0.9692,
                'pan'           : pan,
                'amFunc'        : amFunc,
                'am1'           : 0.0,
                'am2'           : 1.0,
                'amRise'        : dur,
                'amRatio'       : amRatio,
                'reverberation' : reverberation,
                # 'visualMode'    : amFunc,
            }
            rows_list.append(new_row)
            start_time_II += dur
            i_freq += 1

    pfields = ['start', 'dur', 'synthName', 'amplitude', 'frequency', 'attackTime', 'releaseTime', 'sustain', 'pan', 'amFunc', 'am1', 'am2', 'amRise', 'amRatio', 'reverberation']#, 'visualMode']
    score_df = skora.make_score_df(pfields=pfields)
    score_df = skora.concat_rows(score_df, rows_list)
    return score_df

if __name__ == '__main__':
    # Example 00
    metric_ratios = (1/5, 1/7, 1/16, 1/3, 1/13)
    # metric_ratios = (1/5, 1/7, 1/3)
    pulses = (11, 7, 13)
    init_tempo = 33
    score_df_00 = composition(metric_ratios, pulses, init_tempo)
    filename = 'metric_modulation_ex_01_v4.synthSequence'
    skora.df_to_synthSeq(score_df_00, os.path.join(FILEPATH, filename))
