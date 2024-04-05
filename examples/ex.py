# examples/ex.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy.chronos import rhythm_trees as rt
from allopy.chronos import temporal_units as ut
from allopy import tonos
from allopy import topos
from allopy import aikous
from allopy import skora

import numpy as np

FILEPATH = skora.set_score_path()

def materials():
    material = {}
    prolationis = ut.rhythm_pair((3, 5, 7), True)
    material['prolationis'] = prolationis
    subdivisions = ((13, (1,)*7), (8, (1,)*7), (3, (1,)*7), (21, (1,)*7), (5, (1,)*7))
    material['subdivisions'] = subdivisions
    r_trees = []
    for div in prolationis:
        r_trees.append(rt.RT(duration=div, subdivisions=subdivisions))
    material['r_trees'] = r_trees
    hx = tonos.JI.combination_product_sets.CPS((3,5,7,11,13),3)
    material['hexany'] = hx
    material['set'] = []
    return material

def layer1(material: dict, bpm: float = 120, rubato=True):
    materials['root_freq_seq'] = []
    durs = [chronos.beat_duration(r, bpm) for r_tree in material['r_trees'] for r in r_tree.ratios]
    if rubato:
        # grab sublists of 7, apply rubato
        sublists = np.array([chronos.rubato(durs[i:i+7], accelerando=True, intensity=np.random.uniform(0.667,1.0)) for i in range(0, len(durs), 7)])
        durs = np.concatenate(sublists)

    start_time = 0.1
    row_list = []
    min_dur = min(durs)
    max_dur = max(durs)
    base_freq = 999.0
    root_freq = base_freq
    amFunc = 0
    amRatio = 1.0
    for i, dur in enumerate(durs):
        root_freq = base_freq * amRatio if i > 0 and i % len(material['hexany'].ratios) == 0 else root_freq
        ratio     = float(material['hexany'].ratios[i % len(material['hexany'].ratios)])
        ratio     = 1/ratio if np.random.choice([0,1]) == 1 else ratio
        freq      = tonos.wrap_freq(root_freq * ratio, 150, 2000)
        amp       = aikous.DYNAMICS.mp() * aikous.amp_freq_scale(freq)
        amFunc    = np.random.randint(3) if i > 0 and i % 11 == 0 else 0
        amRatio   = float(np.random.choice(material['hexany'].ratios))
        # attack    = np.interp(dur, [min_dur, max_dur], [min_dur * 0.01, min_dur * 0.1])
        release   = np.interp(dur, [min_dur, max_dur], [dur, max_dur])

        new_row = skora.instruments.PFIELDS.OscAM() if i % 7 != 0 else skora.instruments.PFIELDS.AddSyn()
        new_row['start']         = start_time
        new_row['dur']           = min_dur * 0.75
        new_row['amplitude']     = amp
        new_row['amp']           = aikous.DYNAMICS.mf()
        new_row['frequency']     = freq
        new_row['attackTime']    = 0.01
        new_row['releaseTime']   = release

        new_row['releaseStri']   = release * 0.5
        new_row['releaseLow']    = release * 2.0
        new_row['releaseUp']     = release * 1.5

        new_row['sustain']       = 0.75
        new_row['pan']           = np.random.uniform(-1, 1) if i % 7 != 0 else 0.0
        new_row['amFunc']        = amFunc
        new_row['am1']           = 1.0
        new_row['am2']           = 0.0
        new_row['amRise']        = new_row['dur'] * 0.33
        new_row['amRatio']       = amRatio

        new_row['freqStri1']     = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.25,0.5,1,2])
        new_row['freqStri2']     = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.25,0.5,1,2]) 
        new_row['freqStri3']     = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.25,0.5,1,2])
        new_row['freqLow1']      = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.25,0.5,1])
        new_row['freqLow2']      = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.25,0.5,1])
        new_row['freqUp1']       = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.5,1,2,4])
        new_row['freqUp2']       = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.5,1,2,4])
        new_row['freqUp3']       = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.5,1,2,4])
        new_row['freqUp4']       = float(np.random.choice(material['hexany'].ratios)) * np.random.choice([0.5,1,2,4])

        new_row['reverberation'] = np.interp(i % 7, [0,6], [0.66, 0.167])

        new_row['visualMode']    = np.random.randint(3)

        row_list.append(new_row)
        materials['freq_seq'].append({'start': start_time, 'root_freq': root_freq, 'ratio': ratio})
        start_time += dur

    return row_list

def layer2(material: dict, bpm: float = 120, rubato=True):
    start_time = 0.1
    base_freq = 999.0
    root_freq = base_freq / 8
    row_list = []
    for i, d in enumerate(material['prolationis']):
        dur = chronos.beat_duration(d, bpm)

        spread = 3
        ratios = np.random.choice(material['hexany'].ratios, spread)
        for j in range(spread):
            freq = root_freq * ratios[j]
            amp  = np.interp(i, [0, len(material['prolationis'])], [aikous.DYNAMICS.pppp(), aikous.DYNAMICS.mp()])

            new_row = skora.instruments.PFIELDS.OscTrm()
            new_row['start']         = start_time
            new_row['dur']           = dur * np.random.uniform(0.333, 0.53)
            new_row['amplitude']     = amp * aikous.amp_freq_scale(base_freq)
            new_row['frequency']     = freq
            new_row['attackTime']    = new_row['dur']
            new_row['releaseTime']   = (dur - new_row['dur']) * 0.333
            new_row['pan']           = np.interp(j, [0, spread - 1], [-1, 1])
            new_row['table']         = np.random.randint(0, 8)
            new_row['trm1']          = (base_freq / 1024) * np.random.choice(material['hexany'].ratios)
            new_row['trm2']          = (base_freq / 256)  * np.random.choice(material['hexany'].ratios)
            new_row['trmRise']       = new_row['attackTime'] #+ new_row['releaseTime']
            new_row['trmDepth']      = np.random.uniform(0.333, 0.667)

            row_list.append(new_row)

        start_time += dur
    
    return row_list
   

if __name__ == '__main__':    
    mats = materials()

    bpm = 84

    layer_1 = layer1(mats, bpm)
    layer_2 = layer2(mats, bpm)

    comp = layer_1 + layer_2

    skora.notelist_to_synthSeq(comp, os.path.join(FILEPATH, 'ex.synthSequence'))
