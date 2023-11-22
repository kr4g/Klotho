# examples/iso_examples.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy import tonos
from allopy.topos import topos
from allopy.aikous import aikous
from allopy.skora import skora

FILEPATH = skora.set_score_path()

import numpy as np
import pandas as pd
from IPython.display import display

# ---------------------------------------------------------------------------------------------

def materials(color: list, talea: list, acct: int = 0, end=True, kwargs=None):
    '''
    **iso_pairs** (from the Greek for "the same rhythm") is a musical technique using a 
    repeating rhythmic pattern, called a *talea*, in at least one voice part throughout 
    a composition. *Taleae* are typically applied to one or more melodic patterns of 
    pitches or *colores*, which may be of the same or a different length from the *talea*.
    
    see: https://en.wikipedia.org/wiki/iso_pairs
    
    Args:
        color (list): a list of pitches
        talea (list): a list of durations
    '''
    # color_len = len(color)
    talea_len = len(talea)
    
    min_amp = aikous.DYNAMICS.pp
    max_amp = aikous.DYNAMICS.mp

    acct = talea_len if acct == 0 else acct
    mult = len(color)
    
    start_time = 0.0
    rows_list = []
    _mult = False
    for i, (i_color, i_talea) in enumerate(topos.iso_pairs(color, talea)):
        # -----------
        amplitude = np.random.uniform(min_amp.min, min_amp.max)       # default amplitude
        if i % acct == 0:    # accent at each talea cycle
            amplitude = np.random.uniform(max_amp.min, max_amp.max)   # accent amplitude
        
        if i % mult == 0:
            _mult = not _mult
        
        color_mult = 3/2 if _mult else 1
        new_row = {
            'start'      : start_time,
            'dur'        : i_talea,
            'synthName'  : 'PluckedString',
            'amplitude'  : amplitude,
            'frequency'  : i_color * color_mult,
        }
        if kwargs:
            # kwargs['attackTime']  = talea[i_talea] * 0.05
            kwargs['releaseTime'] = i_talea * 3.47
            for key, value in kwargs.items():
                new_row[key] = value
        rows_list.append(new_row)
        # -----------
        start_time += i_talea

    # last note
    if end:
        new_row = {
            'start'      : start_time,
            'dur'        : max(talea),
            'synthName'  : 'PluckedString',
            'amplitude'  : amplitude,
            'frequency'  : color[0],
        }
        if kwargs:
            # kwargs['attackTime']  = talea[i_talea] * 0.01
            kwargs['releaseTime'] = i_talea * 6.23
            for key, value in kwargs.items():
                new_row[key] = value
        rows_list.append(new_row)
    
    return rows_list

def composition(color_ratios = (1/1, 9/8, 4/3),
             talea_ratios = (1/4, 1/8, 1/16, 1/16),
             root_freq    = 440,
             tempo        = 60,
             kwargs       = None):
    iso = materials(
        [root_freq * ratio for ratio in color_ratios],
        [chronos.beat_duration(t, tempo) for t in talea_ratios],
        kwargs=kwargs,
    )
    pfields_std = ['start', 'dur', 'synthName', 'amplitude', 'frequency']
    score_df = skora.make_score_df(pfields=pfields_std + list(kwargs.keys()))
    score_df = skora.concat_rows(score_df, iso)
    return score_df
    

if __name__ == '__main__':
    # --------------------------------------------------
    # ISO EXAMPLES
    # --------------------------------------------------
    
    # Example 00
    color_ratios = (1/1, 9/8, 5/4)
    talea_ratios = (1/4, 1/8, 1/12, 1/12, 1/12)
    root_freq    = 400
    tempo        = 54
    kwargs       = {
        'attackTime'  : 0.0833, 
        'releaseTime' : 10.0,
        'sustain'     : 0.9,  
        'Pan1'        : 0.0,
        'Pan2'        : 0.0,
        'PanRise'     : 0.0,
    }
    
    # score_df_00 = composition(kwargs=kwargs)
    score_df_00 = composition(color_ratios = color_ratios,
                           talea_ratios = talea_ratios,
                           root_freq    = root_freq,
                           tempo        = tempo,
                           kwargs       = kwargs)
    filename = 'iso_pairs_ex_00.synthSequence'
    skora.df_to_synthSeq(score_df_00, os.path.join(FILEPATH, filename))
    
    # --------------------------------------------------
    
    # Example 01
    # color_ratios = (1/1, 6/5, 10/9, 3/4, 15/16)
    color_ratios = (1/1, 7/4, 10/9, 3/4, 5/9)
    talea_ratios = (7/12, 3/13, 2/13, 11/12, 3/17, 5/17)
    root_freq    = 333 / 1.1667
    # root_freq    = 100
    tempo        = 28
    
    # attackTime = min(talea_ratios)
    kwargs       = {
        'attackTime'  : 0.167, 
        'releaseTime' : 9.0,
        'sustain'     : 0.9692,  
        'Pan1'        : -1.0,
        'Pan2'        : -1.0,
        'PanRise'     : 0.0,
    }
    score_df_01 = composition(color_ratios = color_ratios,
                           talea_ratios = talea_ratios,
                           root_freq    = root_freq,
                           tempo        = tempo,
                           kwargs       = kwargs)
    filename = 'iso_pairs_ex_01.synthSequence'
    skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))
    
    # --------------------------------------------------
    
    # Example 02
    color_ratios_inv = (1/cr for cr in color_ratios)
    # talea_ratios_comp = (1 - tr for tr in talea_ratios)
    color_ratios_rotated = color_ratios[-1:] + color_ratios[:-1]
    talea_ratios_rotated = talea_ratios[-4:] + talea_ratios[:-4]
    
    # attackTime = min(talea_ratios_comp)
    kwargs = {
        'attackTime'  : 0.23, 
        'releaseTime' : 9.0,
        'sustain'     : 0.833,  
        'Pan1'        : 1.0,
        'Pan2'        : 1.0,
        'PanRise'     : 0.0,
    }
    score_df_02 = composition(color_ratios = color_ratios_rotated,
                           talea_ratios = talea_ratios_rotated,
                           root_freq    = root_freq * tonos.cents_to_ratio(-33.333),
                           tempo        = tempo * 1,
                           kwargs       = kwargs)
    filename = 'iso_pairs_ex_02.synthSequence'
    skora.df_to_synthSeq(score_df_02, os.path.join(FILEPATH, filename))
    
    # --------------------------------------------------
    
    # Example 03 (merge Examples 01 and 02)
    # tempo = 33
    score_df_03 = skora.merge_parts_dfs([score_df_01, score_df_02])
    filename = 'iso_pairs_ex_combined.synthSequence'
    skora.df_to_synthSeq(score_df_03, os.path.join(FILEPATH, filename))
