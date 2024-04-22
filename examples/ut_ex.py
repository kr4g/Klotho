# examples/ut_ex.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

# from allopy import chronos
from allopy.chronos.rhythm_trees import RT
from AlloPy.allopy.chronos.temporal_units.temporal_units import UT
from allopy import tonos
# from allopy import topos
from allopy.aikous import DYNAMICS, amp_freq_scale
from allopy import skora

from AlloPy.allopy.chronos.rhythm_trees import rt_algorithms as alg

import numpy as np
import random
from fractions import Fraction
from itertools import cycle

SCORE_FILEPATH = skora.set_score_path()
INST_FILEPATH = '/Users/ryanmillett/allolib_playground/tutorials/audiovisual/_instrument_classes.cpp'

# some helper code
attk_max  = lambda d: d * 0.1667
amp_scale = lambda freq, amt=0.45: amp_freq_scale(freq) * amt

def pre_compositional_materials(G:tuple = (3, 5, 7, 11, 13)) -> dict:
    materials = {}

    S = G
    materials['S'] = S
    
    meas = Fraction('17/1')
    bpm  = 54
    beat = '1/8'

    autoref_G = alg.autoref_rotmat(S, 'G')
    materials['autoref_G'] = autoref_G
    autoref_rotmat_G = [
        UT(tempus   = meas,
           prolatio = RT.from_tuple(autoref_G[i]),
           tempo    = bpm,
           beat     = beat) for i in range(len(autoref_G))
    ]
    materials['autoref_rotmat_G'] = autoref_rotmat_G

    autoref_S = alg.autoref_rotmat(S, 'S')
    materials['autoref_S'] = autoref_S
    autoref_rotmat_S = [
        UT(tempus   = meas,
           prolatio = RT.from_tuple(autoref_S[i]),
           tempo    = bpm,
           beat     = beat) for i in range(len(autoref_S))
    ]
    materials['autoref_rotmat_S'] = autoref_rotmat_S

    hx = tonos.JI.combination_product_sets.CPS(S, 2)
    materials['hexany'] = hx
    materials['hx_ratio_cycle'] = cycle(np.random.permutation(hx.ratios))
    materials['hx_prods_cycle'] = cycle(np.random.permutation(hx.products))
    return materials

def layer1(materials:dict, start_offset:float=0.05) -> list:
    note_list = []
    for i, ut in enumerate(materials['autoref_rotmat_G']): # for each layer in the Group...
        root_freq = tonos.pitchclass_to_freq('F#2') * tonos.fold_interval(interval = next(materials['hx_prods_cycle']),
                                                                          equave   = 2,
                                                                          equaves  = 3)
        pan = np.interp(i, [0, len(materials['autoref_rotmat_G'])], [-1, 1])
        amFunc = np.random.choice((0,1,2,3), size=1, replace=False, p=(0.65,0.15,0.1,0.1))[0]
        amRatio = 1.0
        for j, (onset, duration) in enumerate(ut):  # for each note event in the UT...
            if j == 0: continue # rest for the first note event

            # 1) create a new row from the instrument pfields
            new_row = skora.get_pfields(INST_FILEPATH, 'OscAM')

            # 2) perform any compositional logic
            dur         = np.random.uniform(duration * 0.0667, duration * 0.667)
            frequency   = root_freq * next(materials['hx_ratio_cycle'])
            attackTime  = np.random.uniform(0.0, attk_max(dur))
            releaseTime = np.interp(attackTime,            # map this value
                                    [0.0, attk_max(dur)],  # from this range
                                    [duration - dur, 0.0]) # to this range
            sustain     = np.random.uniform(0.75, 0.95)
            amplitude   = np.interp(attackTime, 
                                    [0.0, attk_max(dur)],
                                    [DYNAMICS.f(), DYNAMICS.pp()])
            am1         = np.random.randint(1)
            am2         = 0.0 if am1 == 1 else 1
            amRise      = dur * 0.25
            if j % len(materials['hexany'].ratios) == 0:
                amRatio = float(random.choice(materials['hexany'].ratios))
                amRatio = 1.0 / amRatio if frequency > 900 else amRatio
            reverb      = np.interp(attackTime, [0.0, attk_max(dur)], [0.07, 0.25])

            # 3) set the pfields for the note event
            new_row['start']         = onset + start_offset
            new_row['dur']           = dur
            new_row['amplitude']     = amplitude * amp_scale(frequency, 1.0 if amFunc != 0 else 0.75)
            new_row['frequency']     = tonos.fold_freq(frequency, 55, 2000)
            new_row['attackTime']    = attackTime
            new_row['releaseTime']   = releaseTime
            new_row['sustain']       = sustain if amFunc == 0 else 0.125
            new_row['pan']           = pan
            new_row['amFunc']        = amFunc
            new_row['am1']           = am1
            new_row['am2']           = am2
            new_row['amRise']        = amRise
            new_row['amRatio']       = amRatio
            new_row['reverberation'] = reverb if amFunc == 0 else reverb ** 0.45
            new_row['visualMode']    = amFunc

            # 4) add the new row to the note list
            note_list.append(new_row)

    return note_list

def layer2(materials:dict, start_offset:float=0.05) -> list:
    note_list = []
    for i, ut in enumerate(materials['autoref_rotmat_S']):
        root_freq = tonos.pitchclass_to_freq('F#2')
        trnsp_cyc = cycle([1] + materials['hexany'].ratios)
        min_dur = min(ut.durations)
        max_dur = max(ut.durations)
        for j, (onset, duration) in enumerate(ut):
            if j % len(materials['S']) == 0: continue

            new_row = skora.get_pfields(INST_FILEPATH, 'PluckedString')

            dur       = min_dur
            frequency = root_freq * np.random.uniform(0.96,1.04)#next(materials['hx_ratio_cycle'])
            
            if j % len(materials['S']) + 1 == 0:
                frequency *= next(trnsp_cyc)
            
            new_row['start']      = onset + start_offset
            new_row['dur']        = dur
            new_row['amplitude']  = DYNAMICS.p()
            new_row['frequency']  = tonos.fold_freq(frequency, 55, 2000)
            new_row['attackTime'] = np.interp(duration, [min_dur, max_dur], [min_dur*0.1, min_dur*0.3])

            note_list.append(new_row)

    return note_list

if __name__ == '__main__':

    G = (13, 17, 19, 23, 29)
    # G = (3, 4, 5, 7)
    # G = tuple(np.random.permutation(G))
    
    lyr1 = layer1(pre_compositional_materials(G))
    # lyr2 = layer2(pre_compositional_materials(G))

    comp = lyr1 #+ lyr2

    skora.notelist_to_synthSeq(comp,
                               os.path.join(SCORE_FILEPATH, 'ut_ex.synthSequence'))
