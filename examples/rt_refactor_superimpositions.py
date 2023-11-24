# examples/iso_examples.py
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from allopy import chronos
from allopy.chronos import rhythm_trees as rt
from allopy import tonos
from allopy.topos import topos
from allopy.aikous import aikous
from allopy.skora import skora

FILEPATH = skora.set_score_path()

import numpy as np

lfo_sin = lambda f, n: np.sin(2 * np.pi * f * np.linspace(0, 1, n))

def materials(rhythm_tree: rt.RT) -> list:
    '''
    '''
    return [rhythm_tree.rotate(i) for i in range(len(rhythm_tree.factors))]

def example(r_trees: list, init_bpm: float = 66):
    '''
    '''
    rows_list = []
    pan = -1.0
    rand_oct = 1
    for i, r_tree in enumerate(r_trees):
        start_time = np.random.uniform(0.167, 0.333)
        r_ratios = r_tree.ratios
        freq_min = np.random.uniform(313.0, 327.0) / 2
        amp_curve = lfo_sin(np.random.uniform(freq_min/16, freq_min/17), len(r_ratios)) * 0.5 + 0.5
        for j, r in enumerate(r_ratios):
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.167, 1.0])
            dur = chronos.beat_duration(r, init_bpm)
            amplitude = np.random.uniform(aikous.DYNAMICS.pppp.max, aikous.DYNAMICS.pp.min) * 0.9692
            if j > len(r_ratios) // 3:
                rand_oct = 2**np.random.choice([0.25, 0.5, 0, 1])
                if j > len(r_ratios) // 1.5:
                    freq_min = freq_min * rand_oct
            amp_max = np.interp(j, [0.0, len(r_ratios)], [amplitude, aikous.DYNAMICS.mf.min])
            amplitude = aikous.DYNAMICS.ppp.min*0.833 if j == 0 else amp_max * amp_curve[j] * cresc
            frequency = np.interp(j, [0, len(r_ratios)], [333.0 / 2, freq_min])
            frequency = frequency * rand_oct if j > len(r_ratios) // 1.25 else frequency
            attackTime = min(max(0.009692, dur * np.random.uniform(0.167, 0.333)), 0.0667)
            new_row = {
                'start'       : start_time,
                'dur'         : dur*0.963 + 0.037*(1 - cresc),
                'synthName'   : 'PluckedString',
                'amplitude'   : amplitude,
                'frequency'   : frequency,
                'attackTime'  : attackTime,
                'releaseTime' : attackTime,
                'sustain'     : 0.9692,
                'Pan1'        : pan,
                'Pan2'        : pan,
                'PanRise'     : 0.0,
            }
            rows_list.append(new_row)
            start_time += dur
        pan *= -1.0
    return rows_list

def composition(r_trees: list, hexany: tonos.scales.Hexany = tonos.scales.Hexany(), equaves: list = [0, 1, 2, 3], dyn_range: list = [aikous.DYNAMICS.ppp, aikous.DYNAMICS.pp], init_bpm: float = 60):
    '''
    '''
    rows_list = []
    for i, r_tree in enumerate(r_trees[:len(r_trees) // 1]):
        start_time = np.random.uniform(0.167, 0.23)
        r_ratios = r_tree.ratios
        min_r, max_r = min(r_ratios), max(r_ratios)
        sus_range = [0.4753, 0.9692]
        np.random.shuffle(sus_range)
        np.random.shuffle(equaves)
        ratio_mult = 1 / (r_tree.duration)**(i % 7)
        freq_mod_sign = [-1.0, 1.0][i % 2]
        freq_min = np.random.uniform(313.0, 327.0)
        # rand_oct = 2**equaves[i % len(equaves)]
        rand_oct = (list(hexany.products) + [1/p for p in hexany.products])[i % len(hexany.products)*2]
        amp_curve = lfo_sin(np.random.uniform(1.667, 3.333), len(r_ratios)) * 0.5 + 0.5
        attk_curve = lfo_sin(np.random.uniform(1.667, 3.333), len(r_ratios)) * 0.5 + 0.5
        for j, r in enumerate(r_ratios):
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.963, 1.0])
            dur = chronos.beat_duration(r, init_bpm)
            amplitude = np.random.uniform(dyn_range[0].min, dyn_range[1].max) * amp_curve[j] * cresc
            if j == 0:
                amplitude = np.random.uniform(dyn_range[0].max, dyn_range[1].min) * 0.9692
            freq = np.interp(j, [0, len(r_ratios)], [freq_min, 666.0]) * rand_oct
            freq = tonos.midicents_to_freq(tonos.freq_to_midicents(freq) + freq_mod_sign * tonos.ratio_to_cents(r * ratio_mult))
            frequency = abs(freq)
            # frequency = freq
            while frequency < 144.0:
                frequency *= 2.0
            while frequency > 1600.0:
                frequency /= 2.0
            attackTime = min(max(0.0833, dur * np.random.uniform(min_r * ratio_mult, r * ratio_mult)), 0.19)
            attackTime = 0.0833 if j == 0 else 0.667*attackTime + 0.333*attk_curve[j]
            # attackTime = 0.0833
            releaseTime = dur*0.333
            sustain = np.interp(r, [min_r, max_r], sus_range)
            sustain = 0.9692 if j == 0 else sustain
            pan1 = -1.0
            pan2 = 1.0
            new_row = {
                'start'       : start_time,
                'dur'         : dur * (1 - cresc*0.03),
                'synthName'   : 'PluckedString',
                'amplitude'   : amplitude,
                'frequency'   : frequency,
                'attackTime'  : attackTime,
                'releaseTime' : releaseTime * (1 - cresc),
                'sustain'     : sustain,  
                'Pan1'        : pan1,
                'Pan2'        : pan2,
                'PanRise'     : dur * r,
            }
            rows_list.append(new_row)
            start_time += dur
            pan1 *= -1.0
            pan2 *= -1.0        
    return rows_list

def composition_ii(r_trees: list, equaves: list = [0.125, 0.25, 0.5, 0, 1], dyn_range: list = [aikous.DYNAMICS.ppp, aikous.DYNAMICS.p], init_bpm: float = 60):
    '''
    '''
    rows_list = []
    freq_ratios = [1.0] + [f for f in tonos.scales.Hexany((1, 3, 5, 7), 2).ratios]
    for i, r_tree in enumerate(r_trees[:len(r_trees) // 1]):
        start_time = np.random.uniform(0.167, 0.23)
        i_freq = 0
        r_ratios = r_tree.ratios
        min_r, max_r = min(r_ratios), max(r_ratios)
        sus_range = [0.667, 0.833]
        np.random.shuffle(sus_range)
        np.random.shuffle(equaves)
        ratio_mult = 1 / (r_tree.duration)**(i % 3)
        freq_mod_sign = [-1.0, 1.0][i % 2]
        rand_freq_mod = 1 / freq_ratios[np.random.randint(0, len(freq_ratios))]
        # cresc_min = np.interp(i, [0.0, len(r_trees)], [0.131, 0.636])
        for j, r in enumerate(r_ratios):
            root_freq = 333 * 2**equaves[np.random.randint(0, len(equaves))] if j > 0 else 333
            dur = chronos.beat_duration(r, init_bpm)
            amplitude = np.random.uniform(dyn_range[0].max, dyn_range[1].min) * 0.9692
            amplitude = dyn_range[0].min*0.833 if i_freq == 0 else amplitude
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.667, 1.0])
            # freq = np.random.uniform(660.0, 666.0) * rand_freq_mod
            frequency = root_freq * freq_ratios[-i_freq]
            frequency = frequency * 2**equaves[np.random.randint(0, len(equaves))] if i_freq > 0 else frequency
            # frequency = freq
            while frequency < 55.0:
                frequency *= 2.0
            while frequency > 1311.0:
                frequency /= 2.0
            attackTime = min(max(0.092, dur * np.random.uniform(min_r * ratio_mult, r * ratio_mult)), 0.23)
            attackTime = min(r_ratios) * ratio_mult if j == 0 else attackTime
            sustain = 0.9692 if j == 0 else np.interp(r, [min_r, max_r], sus_range) * cresc
            pan1 = -1.0
            pan2 = 1.0
            new_row = {
                'start'       : start_time,
                'dur'         : dur*0.99 + 0.11*(1 - cresc)*dur,
                'synthName'   : 'PluckedString',
                'amplitude'   : amplitude * cresc,
                'frequency'   : frequency,
                'attackTime'  : 0.96*attackTime + 0.04*attackTime * cresc,
                'releaseTime' : (dur*0.333 + 0.667*dur*cresc) + dur * (1 - cresc),
                'sustain'     : sustain,
                'Pan1'        : pan1,
                'Pan2'        : pan2,
                'PanRise'     : dur * r,
            }
            rows_list.append(new_row)
            start_time += dur
            i_freq = (i_freq + 1) % len(freq_ratios)
            pan1 *= -1.0
            pan2 *= -1.0        
    return rows_list

def compositions():
    pfields = ['start', 'dur', 'synthName', 'amplitude', 'frequency', 'attackTime', 'releaseTime', 'sustain', 'Pan1', 'Pan2', 'PanRise']

    # ----------------------------------------------------------------------------------------------------------------
    # Example 00
    # ----------------------------------------------------------------------------------------------------------------
    subdivisions = ((34, (13, 8, 5)), (13, ((13, 8, 5))), (21, ((13, (3, 2)), 8, (5, (3, 2, 1)))))
    # subdivisions = (1, 1, 1, 1, 1)
    r_tree = rt.RT((3, ((1, 1), subdivisions)))
    # print(r_tree)
    # print(f'Factors {r_tree.factors}\n')
    r_tree_rotations = materials(r_tree)
    exmpl = example(r_trees=r_tree_rotations, init_bpm=18)
    # for r_tree in r_tree_rotations:
    #     print(r_tree.subdivisions)
    score_df_00 = skora.make_score_df(pfields=pfields)
    score_df_00 = skora.concat_rows(score_df_00, exmpl)
    filename = 'rt_refactoring_ex_00.synthSequence'
    skora.df_to_synthSeq(score_df_00, os.path.join(FILEPATH, filename))

    # ----------------------------------------------------------------------------------------------------------------
    # Example 01
    # ----------------------------------------------------------------------------------------------------------------
    subdivisions = (8, (13, (21, 13, 13)), (5, (8, (8, (8, 8, 3, 5)), (21, ((13, (21, 13, 8)), 13, 5, 8)))))
    r_tree = rt.RT((8, ((1, 1), subdivisions)))
    r_tree_rotations = materials(r_tree)
    comp = composition(r_trees=r_tree_rotations[:len(r_tree_rotations)//2], init_bpm=27)
    score_df_01 = skora.concat_rows(skora.make_score_df(pfields=pfields), comp)
    filename = 'rt_refactoring_ex_01_lfo.synthSequence'
    skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))    

    # ----------------------------------------------------------------------------------------------------------------
    # Example 02
    # ----------------------------------------------------------------------------------------------------------------
    # subdivisions = (1, ((21, (13, (8, (5, 3, 2)), 5, 3)), 13, (8, (5, 3, 2)), (5, (3, 2, 1)), 3))
    subdivisions = ((21, (13, (8, (5, 3, 2)), 5, 3)), (13, (3, 2, 1)), 8)
    r_tree = rt.RT((17, ((1, 1), subdivisions)))
    r_tree_rotations = materials(r_tree)
    comp = composition_ii(r_trees=r_tree_rotations, init_bpm=33)
    score_df_01 = skora.concat_rows(skora.make_score_df(pfields=pfields), comp)
    filename = 'rt_refactoring_ex_02_hexany.synthSequence'
    skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))

if __name__ == '__main__':
    compositions()
