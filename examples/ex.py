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
    subdivisions = ((13, (1,)*7), (8, (1,)*7), (21, (1,)*7), (5, (1,)*7))
    material['subdivisions'] = subdivisions
    r_trees = []
    for div in prolationis:
        r_trees.append(rt.RT(duration=div, subdivisions=subdivisions))
    material['r_trees'] = r_trees
    hx = tonos.scales.CPS((3,5,7,11,13),3)
    material['hexany'] = hx
    material['set'] = []
    return material

def composition(material: dict, bpm: float = 120):
    durs = [chronos.beat_duration(r, bpm) for r_tree in material['r_trees'] for r in r_tree.ratios]
    start_time = 0.1
    row_list = []
    min_dur = min(durs)
    max_dur = max(durs)
    base_freq = 999.0
    root_freq = base_freq
    amFunc = 0
    for i, dur in enumerate(durs):
        root_freq = base_freq * new_row['amRatio'] if i > 0 and i % len(material['hexany'].ratios) == 0 else root_freq
        ratio     = float(material['hexany'].ratios[i % len(material['hexany'].ratios)])
        ratio     = 1/ratio if np.random.choice([0,1]) == 1 else ratio
        amFunc    = np.random.choice([0,1,2,3]) if i > 0 and i % 7 == 0 else amFunc
        amRatio   = float(np.random.choice(material['hexany'].ratios))

        new_row = skora.instruments.PFIELDS.OscAM()
        new_row['start']         = start_time
        new_row['dur']           = min_dur * 0.75
        new_row['frequency']     = root_freq * ratio
        new_row['attackTime']    = 0.01
        new_row['releaseTime']   = max_dur * 2.0
        new_row['sustain']       = 0.5
        new_row['amFunc']        = amFunc
        new_row['amRatio']       = amRatio
        new_row['amRise']        = 0.0
        new_row['reverberation'] = 0.05

        row_list.append(new_row)
        start_time += dur

    return row_list

if __name__ == '__main__':
    filename = 'ex.synthSequence'
    skora.notelist_to_synthSeq(composition(materials()), os.path.join(FILEPATH, filename))
