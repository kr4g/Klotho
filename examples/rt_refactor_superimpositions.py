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
    tempo = init_bpm
    pan = -1.0
    rand_oct = 1
    rows_list = []
    for i, r_tree in enumerate(r_trees):
        start_time = np.random.uniform(0.167, 0.333)
        r_ratios = r_tree.ratios
        freq_min = np.random.uniform(313.0, 327.0) / 2
        amp_curve = lfo_sin(np.random.uniform(freq_min/16, freq_min/17), len(r_ratios)) * 0.5 + 0.5
        for j, r in enumerate(r_ratios):
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.333, 1.0])
            # tempo = np.interp(j, [0, len(r_ratios)], [init_bpm, init_bpm*(8/5)])
            dur = chronos.beat_duration(r, tempo)
            amplitude = np.random.uniform(aikous.DYNAMICS.ppp.max, aikous.DYNAMICS.p.min)
            if j > len(r_ratios) // 3:
                rand_oct = 2**np.random.choice([0.25, 0.5, 0, 1])
                if j > len(r_ratios) // (5/3):
                    freq_min = freq_min * rand_oct * 0.5
            amp_max = np.interp(j, [0.0, len(r_ratios)], [amplitude, aikous.DYNAMICS.mp.max])
            amplitude = aikous.DYNAMICS.mp.max*0.43 if j == 0 else amp_max * amp_curve[j] * cresc
            frequency = np.interp(j, [0, len(r_ratios)], [333.0 / 2, freq_min])
            frequency = frequency * rand_oct if j > len(r_ratios) // (8/5) else frequency
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

def composition(r_trees: list, hexany: tonos.scales.Hexany = tonos.scales.Hexany((1, 3, 5, 13), 2), equaves: list = [0, 1, 2, 3], dyn_range: list = [aikous.DYNAMICS.pp, aikous.DYNAMICS.mp], init_bpm: float = 60, start_offset: float = 0.0):    
    '''
    '''
    tempo = init_bpm
    rows_list = []
    for i, r_tree in enumerate(r_trees[:len(r_trees) // 1]):
        start_time = start_offset + np.random.uniform(0.167, 0.23)
        tempo = init_bpm
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
            # tempo = np.interp(j, [0, len(r_ratios)], [init_bpm, init_bpm*(13/8)])
            dur = chronos.beat_duration(r, tempo)
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.963, 1.0])
            amplitude = np.random.uniform(dyn_range[0].min, dyn_range[1].min) * amp_curve[j] * cresc
            amplitude = np.random.uniform(aikous.DYNAMICS.mp.max, aikous.DYNAMICS.mf.min) if j == 0 else amplitude
            freq = np.interp(j, [0, len(r_ratios)], [freq_min, 666.0]) * rand_oct
            freq = tonos.midicents_to_freq(tonos.freq_to_midicents(freq) + freq_mod_sign * tonos.ratio_to_cents(r * ratio_mult))
            frequency = abs(freq)
            # frequency = freq
            attackTime = min(max(0.0833, dur * np.random.uniform(min_r * ratio_mult, r * ratio_mult)), 0.19)
            attackTime = 0.0833 if j == 0 else 0.667*attackTime + 0.333*attk_curve[j]
            # attackTime = 0.0833
            releaseTime = dur*0.167
            sustain = np.interp(r, [min_r, max_r], sus_range)
            sustain = 0.9692 if j == 0 else sustain
            pan1 = -1.0
            pan2 = 1.0
            while frequency > 2300.0:
                frequency /= 2.0
            while frequency < 54.0:
                frequency *= 2.0
            # if 89.0 < frequency < 1313.0:
            if i % 3 != 0:
                new_row = {
                    'start'       : start_time,
                    'dur'         : dur * (1 - cresc*0.03),
                    'synthName'   : 'PluckedString',
                    'amplitude'   : amplitude,
                    'frequency'   : frequency,
                    'attackTime'  : attackTime,
                    'releaseTime' : releaseTime*0.667 + 0.333*releaseTime*(1 - cresc),
                    'sustain'     : sustain,  
                    'Pan1'        : pan1,
                    'Pan2'        : pan2,
                    'PanRise'     : dur * r,
                }
                pan1 *= -1.0
                pan2 *= -1.0
            else:
                # pfield("amp", 0.01, 0.0, 0.3);
                # pfield("frequency", 60, 20, 5000);
                # pfield("ampStri", 0.5, 0.0, 1.0);
                # pfield("attackStri", 0.1, 0.01, 3.0);
                # pfield("releaseStri", 0.1, 0.1, 10.0);
                # pfield("sustainStri", 0.8, 0.0, 1.0);
                # pfield("ampLow", 0.5, 0.0, 1.0);
                # pfield("attackLow", 0.001, 0.01, 3.0);
                # pfield("releaseLow", 0.1, 0.1, 10.0);
                # pfield("sustainLow", 0.8, 0.0, 1.0);
                # pfield("ampUp", 0.6, 0.0, 1.0);
                # pfield("attackUp", 0.01, 0.01, 3.0);
                # pfield("releaseUp", 0.075, 0.1, 10.0);
                # pfield("sustainUp", 0.9, 0.0, 1.0);
                # pfield("freqStri1", 1.0, 0.1, 10);
                # pfield("freqStri2", 2.001, 0.1, 10);
                # pfield("freqStri3", 3.0, 0.1, 10);
                # pfield("freqLow1", 4.009, 0.1, 10);
                # pfield("freqLow2", 5.002, 0.1, 10);
                # pfield("freqUp1", 6.0, 0.1, 10);
                # pfield("freqUp2", 7.0, 0.1, 10);
                # pfield("freqUp3", 8.0, 0.1, 10);
                # pfield("freqUp4", 9.0, 0.1, 10);
                # pfield("pan", 0.0, -1.0, 1.0);
                amp = amplitude * 0.0043
                ampStri = np.random.uniform(0.5, 1.0)
                attackStri = attackTime#np.random.uniform(0.1, 3.0)
                releaseStri = np.random.uniform(0.1, dur*cresc)
                sustainStri = np.random.uniform(0.0, 1.0)
                ampLow = np.random.uniform(0.5, 1.0)
                attackLow = attackTime#np.random.uniform(0.01, 3.0)
                releaseLow = np.random.uniform(0.1, dur*cresc)
                sustainLow = np.random.uniform(0.0, 1.0)
                ampUp = np.random.uniform(0.6, dur*cresc)
                attackUp = attackTime#np.random.uniform(0.01, 3.0)
                releaseUp = np.random.uniform(0.1, dur*cresc)
                sustainUp = np.random.uniform(0.0, 1.0)
                freqStri1 = np.random.uniform(0.1, 10.0)
                freqStri2 = np.random.uniform(0.1, 10.0)
                freqStri3 = np.random.uniform(0.1, 10.0)
                freqLow1 = np.random.uniform(0.1, 10.0)
                freqLow2 = np.random.uniform(0.1, 10.0)
                freqUp1 = np.random.uniform(0.1, 10.0)
                freqUp2 = np.random.uniform(0.1, 10.0)
                freqUp3 = np.random.uniform(0.1, 10.0)
                freqUp4 = np.random.uniform(0.1, 10.0)
                pan = np.random.uniform(-1.0, 1.0)                
                new_row = {
                    'start'       : start_time,
                    'dur'         : dur * cresc,
                    'synthName'   : 'AddSyn',
                    'amp'         : amp,
                    'frequency'   : frequency,
                    'ampStri'     : ampStri,
                    'attackStri'  : attackStri,
                    'releaseStri' : releaseStri,
                    'sustainStri' : sustainStri,
                    'ampLow'      : ampLow,
                    'attackLow'   : attackLow,
                    'releaseLow'  : releaseLow,
                    'sustainLow'  : sustainLow,
                    'ampUp'       : ampUp,
                    'attackUp'    : attackUp,
                    'releaseUp'   : releaseUp,
                    'sustainUp'   : sustainUp,
                    'freqStri1'   : freqStri1,
                    'freqStri2'   : freqStri2,
                    'freqStri3'   : freqStri3,
                    'freqLow1'    : freqLow1,
                    'freqLow2'    : freqLow2,
                    'freqUp1'     : freqUp1,
                    'freqUp2'     : freqUp2,
                    'freqUp3'     : freqUp3,
                    'freqUp4'     : freqUp4,
                    'pan'         : pan,
                }
            rows_list.append(new_row)
            start_time += dur
    return rows_list

def composition_ii(r_trees: list, equaves: list = [0.125, 0.25, 0.5, 0, 1], dyn_range: list = [aikous.DYNAMICS.ppp, aikous.DYNAMICS.p], init_bpm: float = 60, start_offset: float = 0.0):
    '''
    '''
    tempo = init_bpm
    rows_list = []
    freq_ratios = [1.0] + [f for f in tonos.scales.Hexany((1, 3, 5, 13), 2).ratios]
    for i, r_tree in enumerate(r_trees[:len(r_trees) // 1]):
        start_time = start_offset + np.random.uniform(0.167, 0.23)
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
            # tempo = np.interp(j, [0, len(r_ratios)], [init_bpm, init_bpm*(21/13)])
            dur = chronos.beat_duration(r, tempo)
            amplitude = np.random.uniform(dyn_range[0].max, dyn_range[1].min) * 0.9692
            amplitude = dyn_range[0].max if i_freq == 0 else amplitude
            cresc = np.interp(j, [0.0, len(r_ratios)], [0.667, 1.0])
            frequency = 666 if j <= 9 or j >= len(r_ratios) - 6 else 333
            frequency = frequency * 2**equaves[np.random.randint(0, len(equaves))] if j > 3 else frequency * freq_ratios[-i_freq]
            frequency = frequency * rand_freq_mod if 6 < j < 9 else frequency
            # freq = np.random.uniform(660.0, 666.0) * rand_freq_mod
            # frequency = freq
            while frequency < 89.0:
                frequency *= 2.0
            while frequency > 1600.0:
                frequency /= 2.0
            attackTime = min(max(0.167, dur * np.random.uniform(min_r * ratio_mult, r * ratio_mult)), 0.23)
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
            i_freq = (i_freq + 1) % len(freq_ratios) if j >= 6 else i_freq
            pan1 *= -1.0
            pan2 *= -1.0        
    return rows_list

def compositions():
    pfields = ['start', 'dur', 'synthName', 'amplitude', 'frequency', 'attackTime', 'releaseTime', 'sustain', 'Pan1', 'Pan2', 'PanRise']
    start_offset = lambda notes: (lambda max_note: max_note['start'] + max_note['dur'])(max(notes, key=lambda x: x['start']))
    
    # ----------------------------------------------------------------------------------------------------------------
    # Example 00
    # ----------------------------------------------------------------------------------------------------------------
    subdivisions = ((34, (13, 8, 5)), (13, ((13, 8, 5))), (21, ((13, (3, 2)), 8, (5, (3, 2, (1, (3, 2, 1, (1, (13, 8, 5)))))))))
    # subdivisions = (1, 1, 1, 1, 1)
    r_tree = rt.RT((5, ((1, 1), subdivisions)))
    # print(r_tree)
    # print(f'Factors {r_tree.factors}\n')
    r_tree_rotations = materials(r_tree)
    exmpl = example(r_trees=r_tree_rotations, init_bpm=8 * (8/5))
    # for r_tree in r_tree_rotations:
    #     print(r_tree.subdivisions)

    filename = 'rt_refactoring_ex_00_rand_detune.synthSequence'
    # score_df_00 = skora.concat_rows(skora.make_score_df(pfields=pfields), exmpl)
    # skora.df_to_synthSeq(score_df_00, os.path.join(FILEPATH, filename))
    skora.notelist_to_synthSeq(exmpl, os.path.join(FILEPATH, filename))

    # ----------------------------------------------------------------------------------------------------------------
    # Example 01
    # ----------------------------------------------------------------------------------------------------------------
    subdivisions_i = (8, (13, (21, 13, 13)), (5, (8, (8, (8, 8, 3, 5)), (21, ((13, (21, 13, 8)), 5, (8, ((13, (21, 13, 13)), 8, (5, (3, 2, 1)))))))))
    r_tree_i = rt.RT((8, ((1, 1), subdivisions_i)))
    r_tree_rotations_i = materials(r_tree_i)
    comp_i = composition(r_trees=r_tree_rotations_i[:len(r_tree_rotations_i)//2], init_bpm=13 * (13/8))

    filename = 'rt_refactoring_ex_01_rt_ratios.synthSequence'
    # score_df_01 = skora.concat_rows(skora.make_score_df(pfields=pfields), comp)
    # skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))    
    skora.notelist_to_synthSeq(comp_i, os.path.join(FILEPATH, filename))

    # ----------------------------------------------------------------------------------------------------------------
    # Example 02
    # ----------------------------------------------------------------------------------------------------------------
    # subdivisions = (1, ((21, (13, (8, (5, 3, 2)), 5, 3)), 13, (8, (5, 3, 2)), (5, (3, 2, 1)), 3))
    # subdivisions = ((34, (13, (8, (5, 3, 2)), 5, 3)), (21, ((3, (13, 8, 5)), 2, 1)), 8)
    subdivisions_ii = ((34, (13, (8, ((5, (3, 2, 1)), 3, 2)), 5, 3)), 13, (21, (1, 1, 2, 3, 5, 8, 13)))
    r_tree_ii = rt.RT((13, ((1, 1), subdivisions_ii)))
    r_tree_rotations_ii = materials(r_tree_ii)
    comp_ii = composition_ii(r_trees=r_tree_rotations_ii, init_bpm=21 * (21/13))

    filename = 'rt_refactoring_ex_02_hexany.synthSequence'
    # score_df_01 = skora.concat_rows(skora.make_score_df(pfields=pfields), comp)
    # skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))
    skora.notelist_to_synthSeq(comp_ii, os.path.join(FILEPATH, filename))

    # ----------------------------------------------------------------------------------------------------------------
    # Merge Examples 00, 01, 02
    # ----------------------------------------------------------------------------------------------------------------
    exmpl = example(r_trees=r_tree_rotations, init_bpm=8 * (8/5))
    offset_time = start_offset(exmpl)
    
    comp_i = composition(r_trees=r_tree_rotations_i[:len(r_tree_rotations_i)//2], init_bpm=13 * (13/8), start_offset=offset_time)
    offset_time = start_offset(comp_i)

    comp_ii = composition_ii(r_trees=r_tree_rotations_ii, init_bpm=21 * (21/13), start_offset=offset_time)
    offset_time = start_offset(comp_ii)

    comp = exmpl + comp_i + comp_ii
    filename = 'rt_refactoring_ex_03_merged.synthSequence'
    skora.notelist_to_synthSeq(comp, os.path.join(FILEPATH, filename))
            

if __name__ == '__main__':
    compositions()
