# examples/iso_examples.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

import pandas as pd
from IPython.display import display

from allopy import chronos
from allopy.topos import topos
from allopy.skora import skora

FILEPATH = skora.set_score_path()

# ---------------------------------------------------------------------------------------------

def iso_test(color_ratios = (1/1, 9/8, 4/3),
             talea_ratios = (1/4, 1/8, 1/16, 1/16),
             root_freq    = 440,
             tempo        = 60,
             kwargs       = None):
    iso = topos.isorhythm(
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
    color_ratios = (1/1, 9/8, 4/3)
    talea_ratios = (1/4, 1/8, 1/12, 1/12, 1/12)
    root_freq    = 440
    tempo        = 60
    kwargs       = {
        'attackTime'  : 0.05, 
        'releaseTime' : 10.0,
        'sustain'     : 0.9,  
        'Pan1'        : 0.0,
        'Pan2'        : 0.0,
        'PanRise'     : 0.0,
    }
    
    # score_df_00 = iso_test(kwargs=kwargs)
    score_df_00 = iso_test(color_ratios = color_ratios,
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
    tempo        = 54
    
    # attackTime = min(talea_ratios)
    kwargs       = {
        'attackTime'  : 9.0, 
        'releaseTime' : 9.0,
        'sustain'     : 0.833,  
        'Pan1'        : -1.0,
        'Pan2'        : -1.0,
        'PanRise'     : 0.0,
    }
    score_df_01 = iso_test(color_ratios = color_ratios,
                           talea_ratios = talea_ratios,
                           root_freq    = root_freq,
                           tempo        = tempo,
                           kwargs       = kwargs)
    filename = 'iso_pairs_ex_01.synthSequence'
    skora.df_to_synthSeq(score_df_01, os.path.join(FILEPATH, filename))
    
    # --------------------------------------------------
    
    # Example 02
    color_ratios_inv = (1/cr for cr in color_ratios)
    talea_ratios_comp = (1 - tr for tr in talea_ratios)
    
    # attackTime = min(talea_ratios_comp)
    kwargs = {
        'attackTime'  : 6.0, 
        'releaseTime' : 9.0,
        'sustain'     : 0.9296,  
        'Pan1'        : 1.0,
        'Pan2'        : 1.0,
        'PanRise'     : 0.0,
    }
    score_df_02 = iso_test(color_ratios = color_ratios_inv,
                           talea_ratios = talea_ratios_comp,
                           root_freq    = root_freq * 2,
                           tempo        = tempo * 2,
                           kwargs       = kwargs)
    filename = 'iso_pairs_ex_02.synthSequence'
    skora.df_to_synthSeq(score_df_02, os.path.join(FILEPATH, filename))
    
    # --------------------------------------------------
    
    # Example 03 (merge Examples 01 and 02)
    # tempo = 33
    score_df_03 = skora.merge_parts_dfs([score_df_01, score_df_02])
    filename = 'iso_pairs_ex_03.synthSequence'
    skora.df_to_synthSeq(score_df_03, os.path.join(FILEPATH, filename))
