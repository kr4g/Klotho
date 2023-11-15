# examples/rhythm_pairs_examples.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

import numpy as np
from math import prod
import pandas as pd
from IPython.display import display

from allopy import chronos
from allopy.chronos.rhythm_pairs import rhythm_pair as RP
from allopy import tonos
from allopy.topos import topos
from allopy.aikous import aikous
from allopy.skora import skora

FILEPATH = skora.set_score_path()

def rp_layer_1_bass(proportions: list):
    p_scale = 0.23
    prolats_MM = RP(proportions, True)
    prolats_MM = np.array(prolats_MM) * p_scale
    
    start_time = 0.0
    rows_list = []
    for i, prol_MM in enumerate(prolats_MM):
        dur = prol_MM
        frequency = 55# * (6/5)**i
        min_amp   = np.interp(i, [0, len(prolats_MM)], [aikous.Dynamics.mf, aikous.Dynamics.p])
        max_amp   = np.interp(i, [0, len(prolats_MM)], [aikous.Dynamics.f, aikous.Dynamics.fff])
        amplitude = np.interp(i, [0, len(prolats_MM)], [min_amp, max_amp])
        vibDepth  = np.interp(i, [0.0, len(prolats_MM)], [0.0, 0.667])**2.167
        
        reverb_min = np.interp(i, [0, len(prolats_MM)], [0.3, 0.05])
        reverb_max = np.interp(i, [0, len(prolats_MM)], [0.45, reverb_min])
        reverberation = np.interp(i, [0, len(prolats_MM)], [reverb_min, reverb_max])
        new_row = {
            'start_time'   : start_time,
            'dur'          : dur,
            'synthName'    : 'FMWT',
            'frequency'    : frequency * tonos.cents_to_ratio(16.167)**i,
            'amplitude'    : amplitude,
            'attackTime'   : dur,
            'releaseTime'  : 0.0,
            'sustain'      : 0.9692,
            'idx1'         : 0.01,
            'idx2'         : 9,
            'idx3'         : 3,
            'carMul'       : 1,
            'modMul'       : 1.0007,
            'vibRate1'     : 0.0,
            'vibRate2'     : 3.0,
            'vibRise'      : dur,
            'vibDepth'     : vibDepth,
            'pan'          : 0.0,
            'table'        : 1,
            'reverberation': reverberation,
        }
        rows_list.append(new_row)
        start_time += prol_MM

    pfields = ['start_time', 'dur', 'synthName', 'frequency', 'amplitude', 'attackTime', 'releaseTime', 'sustain', 'idx1', 'idx2', 'idx3', 'carMul', 'modMul', 'vibRate1', 'vibRate2', 'vibRise', 'vibDepth', 'pan', 'table', 'reverberation']
    score_df = skora.make_score_df(pfields=pfields)
    score_df = skora.concat_rows(score_df, rows_list)
    return score_df

def rp_layer_2_rhy(proportions: list):
    p_scale = 0.23
    prolats = RP(proportions, False)
    prolats = np.array(prolats) * p_scale
    
    start_time = 0.0
    rows_list = []
    for i, prol in enumerate(prolats):
        dur = prol
        max_oct = int(np.interp(i, [0, len(prolats)], [3.0, 11.0]))
        frequency = 55 * (6/5)#**(i % max_oct)
        min_amp   = np.interp(i, [0, len(prolats)], [aikous.Dynamics.pp, aikous.Dynamics.mf])
        max_amp   = np.interp(i, [0, len(prolats)], [aikous.Dynamics.f, aikous.Dynamics.fff])
        amplitude = np.interp(i, [0, len(prolats)], [min_amp, max_amp])
        vibDepth  = 0.0
        reverb_min = np.interp(i, [0, len(prolats)], [0.05, 0.01])
        reverb_max = np.interp(i, [0, len(prolats)], [0.1, reverb_min])
        reverberation = np.interp(i, [0, len(prolats)], [reverb_min, reverb_max])
        
        new_row = {
            'start_time'   : start_time,
            'dur'          : dur,
            'synthName'    : 'FMWT',
            'frequency'    : frequency * tonos.cents_to_ratio(33)**i,
            'amplitude'    : amplitude,
            'attackTime'   : 0.005,
            'releaseTime'  : dur * 0.667,
            'sustain'      : 0.9692,
            'idx1'         : 9.0,
            'idx2'         : 3.0,
            'idx3'         : 0.0,
            'carMul'       : 1,
            'modMul'       : 1.0007,
            'vibRate1'     : 0.0,
            'vibRate2'     : 3.0,
            'vibRise'      : dur,
            'vibDepth'     : vibDepth,
            'pan'          : 0.0,
            'table'        : 0,
            'reverberation': reverberation,
        }
        rows_list.append(new_row)
        start_time += prol

    pfields = ['start_time', 'dur', 'synthName', 'frequency', 'amplitude', 'attackTime', 'releaseTime', 'sustain', 'idx1', 'idx2', 'idx3', 'carMul', 'modMul', 'vibRate1', 'vibRate2', 'vibRise', 'vibDepth', 'pan', 'table', 'reverberation']
    score_df = skora.make_score_df(pfields=pfields)
    score_df = skora.concat_rows(score_df, rows_list)
    return score_df

def rp_layer_3_tb(proportions: list):
    # proportions = np.array(proportions) * 0.23
    multiples = {}
    rows_list = []
    for n, prop in enumerate(proportions):
        start_time = 0.0
        multiples[prop] = prod([p for i, p in enumerate(proportions) if i != n])
        
        dur = prop * 0.23
        # tritone = 45/32 
        frequency = (55 * 0.5) * (45/32)**(n % 6)
        table = np.random.choice(list(range(2,9)))
        
        reverb_min = np.interp(n, [0, len(proportions)], [0.0, 0.05])
        reverb_max = np.interp(n, [0, len(proportions)], [reverb_min, 0.15])
        
        repeats = int(multiples[prop] + 1)
        for i in range(1, repeats):
            # print(f'{prop} * {i} = {prop * i}')
            min_amp   = np.interp(i, [0, repeats], [aikous.Dynamics.ppp, aikous.Dynamics.mp])**2
            max_amp   = np.interp(i, [0, repeats], [aikous.Dynamics.mf, aikous.Dynamics.ff])**2
            amplitude = np.interp(i, [0, repeats], [min_amp, max_amp])
            vibRate2  = np.interp(i, [0, repeats], [0.0, 1.0])**2.167
            vibDepth  = np.interp(i, [0, repeats], [0.0, 0.0667])
            pan = np.random.uniform(-1.0, 1.0)
            reverberation = np.interp(i, [0, repeats], [reverb_min, reverb_max])
            new_row = {
                'start_time'   : start_time,
                'dur'          : dur,
                'synthName'    : 'FMWT',
                'frequency'    : frequency * tonos.cents_to_ratio(66)**i,
                'amplitude'    : amplitude,
                'attackTime'   : dur,
                'releaseTime'  : 0.0,
                'sustain'      : 0.9692,
                'idx1'         : 9.0,
                'idx2'         : 3.0,
                'idx3'         : 0.0,
                'carMul'       : 1,
                'modMul'       : 1.0007,
                'vibRate1'     : 0.0,
                'vibRate2'     : vibRate2 * 1.0,
                'vibRise'      : dur,
                'vibDepth'     : vibDepth,
                'pan'          : pan,
                'table'        : table,
                'reverberation': 0.0,
            }
            rows_list.append(new_row)
            start_time += dur

    pfields = ['start_time', 'dur', 'synthName', 'frequency', 'amplitude', 'attackTime', 'releaseTime', 'sustain', 'idx1', 'idx2', 'idx3', 'carMul', 'modMul', 'vibRate1', 'vibRate2', 'vibRise', 'vibDepth', 'pan', 'table', 'reverberation']
    score_df = skora.make_score_df(pfields=pfields)
    score_df = skora.concat_rows(score_df, rows_list)
    return score_df


if __name__ == '__main__':
    proportions = [3,5,7]
    
    parts = []
    
    # Example 00
    part_df_00 = rp_layer_1_bass(proportions)
    parts.append(part_df_00)
    
    filename = 'rhythm_pairs_ex_00_mm.synthSequence'
    skora.df_to_synthSeq(part_df_00, os.path.join(FILEPATH, filename))
    
    # Example 01
    part_df_01 = rp_layer_2_rhy(proportions)
    parts.append(part_df_01)
    
    filename = 'rhythm_pairs_ex_01_std.synthSequence'
    skora.df_to_synthSeq(part_df_01, os.path.join(FILEPATH, filename))
    
    # Example 02
    part_df_02 = rp_layer_3_tb(proportions)
    parts.append(part_df_02)
    filename = 'rhythm_pairs_ex_02_time_blocks.synthSequence'
    skora.df_to_synthSeq(part_df_02, os.path.join(FILEPATH, filename))
    
    # Example xx
    score_df = skora.merge_parts_dfs(parts)
    filename = 'rhythm_pairs_ex_combined.synthSequence'
    skora.df_to_synthSeq(score_df, os.path.join(FILEPATH, filename))
