# examples/ut_ex.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy.chronos.rhythm_trees import RT
from allopy.chronos.temporal_units import UT
from allopy import tonos
from allopy import topos
from allopy import aikous
from allopy import skora

from utils.algorithms import algorithms as alg

import numpy as np
from fractions import Fraction
from itertools import cycle

SCORE_FILEPATH = skora.set_score_path()
INST_FILEPATH = '/Users/ryanmillett/allolib_playground/tutorials/audiovisual/_instrument_classes.cpp'

def pre_compositional_materials(G:tuple = (3, 5, 7, 11, 13)) -> dict:
    materials = {}
    S = G
    materials['S'] = S
    group = alg.autoref_rotmat(S)
    materials['group'] = group
    meas = Fraction('21/1')
    ut_seq = [
        UT(tempus   = meas,
           prolatio = RT.from_tuple(group[i]),
           tempo    = 48,
           beat     = '1/16') for i in range(len(group))
    ]
    materials['ut_seq'] = ut_seq
    hx = tonos.scales.CPS(S, 2)
    materials['hexany'] = hx
    return materials

def layer1(material:dict, start_offset:float=0.05) -> list:
    dyn = aikous.DYNAMICS
    attk_max = lambda d: d * 0.1667
    amp_scale = lambda freq: aikous.amp_freq_scale(freq) * 0.45
    ratio_seq = material['hexany'].ratios
    np.random.shuffle(ratio_seq)
    ratio_seq = cycle(ratio_seq)

    note_list = []
    for i, ut in enumerate(material['ut_seq']):
        # if i != 2: continue
        root_freq = tonos.pitchclass_to_freq('F#2') * material['hexany'].ratios[i]
        pan = np.interp(i, [0, len(material['ut_seq'])], [-1, 1])
        # amFunc = np.random.choice([0,1,3])
        amRatio = 1.0
        for j, (onset, dur) in enumerate(ut):  # for each note event in the UT...
            if j == 0: continue # rest for the first note event

            # 1) create a new row from the instrument pfields
            new_row = skora.get_pfields(INST_FILEPATH, 'OscAM')

            # 2) perform any compositional logic
            duration    = np.random.uniform(dur * 0.0667, dur * 0.833)
            frequency   = root_freq * next(ratio_seq)
            attackTime  = np.random.uniform(0.0, attk_max(duration))
            releaseTime = np.interp(attackTime,                # map this value
                                    [0.0, attk_max(duration)], # from this range  
                                    [dur - duration, 0.0])     # to this range
            sustain     = np.random.uniform(0.5, 0.95)
            amplitude   = np.interp(attackTime, 
                                    [0.0, attk_max(duration)],
                                    [dyn.mp(), dyn.pppp() * 0.1]) * amp_scale(frequency)
            am1         = np.random.randint(1)
            am2         = 0.0 if am1 == 1 else 1
            amRise      = duration * 0.25
            if j % len(material['hexany'].ratios) == 0:
                amRatio = tonos.fold_interval(interval = float(np.random.choice(material['hexany'].products)),
                                              equave   = 2,
                                              equaves  = 2) * np.random.choice([2, 1, 0.5])
            reverb      = np.interp(attackTime, [0.0, attk_max(duration)], [0.07, 0.25])

            # 3) set the pfields for the note event
            new_row['start']         = onset + start_offset
            new_row['dur']           = duration
            new_row['amplitude']     = amplitude
            new_row['frequency']     = frequency
            new_row['attackTime']    = attackTime
            new_row['releaseTime']   = releaseTime
            new_row['sustain']       = sustain
            new_row['pan']           = pan
            new_row['amFunc']        = 0
            new_row['am1']           = am1
            new_row['am2']           = am2
            new_row['amRise']        = amRise
            new_row['amRatio']       = amRatio
            new_row['reverberation'] = reverb
            new_row['visualMode']    = i % 4

            # 4) add the new row to the note list
            note_list.append(new_row)

    return note_list

if __name__ == '__main__':

    G = (3, 5, 7, 11, 13, 17, 19, 23)
    # G = (13, 17, 19, 23)
    
    comp = layer1(pre_compositional_materials(G))

    skora.notelist_to_synthSeq(comp,
                               os.path.join(SCORE_FILEPATH, 'ut_ex.synthSequence'))
