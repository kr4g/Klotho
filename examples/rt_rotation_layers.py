# examples/rp_partitions.py
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from allopy.chronos import chronos
from allopy.chronos import rhythm_trees as rt
from AlloPy.allopy.chronos.temporal_units import temporal_units as ut
# from allopy import tonos
# from allopy.topos import topos
from allopy.topos import formal_grammars as fg
from allopy.topos.random import rando
from allopy.aikous import DYNAMICS as DYN
from allopy.skora import skora
from allopy.skora.instruments import PFIELDS

import numpy as np

FILEPATH = skora.set_score_path()

def time_materials():
    materials = {}
    subdivs_1 = ((55, ((13, (5, 3, 2)), 8, 3, 5)), (21, (5, 5, 3, 2)), (34, (5, 3, 8, (13, (3, 5)))))
    r_tree_1 = rt.RT(duration=18, subdivisions=subdivs_1)
    r_tree_1_rotations = [r_tree_1.rotate(i) for i in range(len(r_tree_1.ratios))]
    materials['r_tree_1_rotations'] = r_tree_1_rotations
    
    return materials

def composition(materials, init_bpm: float = 36):
    notelist = []
    # dur = chronos.beat_duration(1/4, init_bpm)
    rotations = materials['r_tree_1_rotations'][:8]
    for i, t in enumerate(rotations):
        pfields = getattr(PFIELDS, 'Vib', None).value.copy()  if i % 2 == 0 else getattr(PFIELDS, 'OscTrm', None).value.copy()
        start = 0.1
        for r in t.ratios:
            dur = chronos.beat_duration(r, init_bpm)
            freq_r = r
            while freq_r < 1.0: freq_r *= 2
            
            if i % 2 == 0:
                freq_r = 1 / freq_r
            
            new_row = pfields.copy()
            
            new_row['start'] = start
            new_row['dur'] = dur
            new_row['amplitude'] = np.interp(r, [min(t.ratios), max(t.ratios)], [DYN.ppp.min, DYN.pppp.min]) * 0.667
            new_row['frequency'] = 333 * float(freq_r)
            new_row['attackTime'] = dur * np.interp(i, (0, len(rotations)), (0.0, 0.5))
            new_row['vibeRate1'] = 3 * float(freq_r)
            new_row['vibeRate2'] = 3 * float(1 / freq_r)
            new_row['vibeRise'] = dur * np.interp(i, (0, len(rotations)), (0.0, 0.5))
            new_row['vibeDepth'] = np.random.uniform(0.0167, 0.033)
            new_row['trm1'] = 2 * float(freq_r)
            new_row['trm2'] = 2 * float(1 / freq_r)
            new_row['trmRise'] = dur * np.interp(i, (0, len(rotations)), (0.0, 0.5))
            new_row['trmDepth'] = np.random.uniform(0.167, 1.0)
            new_row['pan'] = np.interp(i, (0, len(rotations)), (-1, 1))
            
            notelist.append(new_row)
            start += dur
    
    return notelist

if __name__ == "__main__":
    comp = composition(time_materials(), 36)
    skora.notelist_to_synthSeq(comp, os.path.join(FILEPATH, 'test_layers.synthSequence'))