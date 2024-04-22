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
# from allopy.aikous import aikous
from allopy.skora import skora

import numpy as np

FILEPATH = skora.set_score_path()

def time_materials():
    subdivs_1 = ut.rhythm_pair((3,7,11), True)
    r_tree_1 = rt.RT(duration=9, subdivisions=subdivs_1)
    print(r_tree_1)
    
    subdivs_2 = ut.rhythm_pair((5,7,9), True)
    r_tree_2 = rt.RT(duration=9, subdivisions=subdivs_2)
    print(r_tree_2)
    
    comp = [str(r) for r in rt.superimpose_durations(r_tree_1.ratios, r_tree_2.ratios)]
    print(comp)
    
    notelist = []
    bpm = 36
    
    durs = [chronos.beat_duration(r, bpm) for r in r_tree_1.ratios]
    for _ in range(3):
        dc = [np.random.uniform(0.083, 1.167) for _ in range(len(durs))]
        freqs = [333 * np.random.uniform(1, 100/81) for _ in range(len(durs))]
        attks = [np.random.uniform(0.33, 1) * d for d in durs]
        rels = [np.random.uniform(0,1.67) * d for d in durs]
        tables = [np.random.randint(8) for _ in range(len(durs))]
        pans = [np.random.uniform(-1,0) for _ in range(len(durs))]
        notelist += skora.make_notelist(pfields={'synthName': 'FMWT', 'table': tables, 'dur': durs, 'dc': dc, 'amplitude': [0.1], 'frequency': freqs, 'attackTime': attks, 'releaseTime': rels, 'pan': pans, 'reverberation': 0.667})
    
    # durs = [chronos.beat_duration(r, 54) for r in comp]
    # freqs = [333 * np.random.uniform(1, 16/15) for _ in range(len(durs))]
    # attks = [0.1 * d for d in durs]
    # notelist += skora.make_notelist(pfields={'dur': durs, 'dc': 0.1, 'frequency': freqs, 'attackTime': attks, 'pan': 0})
    
    durs = [chronos.beat_duration(r, bpm) for r in r_tree_2.ratios]
    for i in range(3):
        dc = [np.random.uniform(0.083, 1.167) for _ in range(len(durs))]
        freqs = [333 * np.random.uniform(1, 100/81) for _ in range(len(durs))]
        attks = [np.random.uniform(0.33, 1) * d for d in durs]
        rels = [np.random.uniform(0,1.67) * d for d in durs]
        tables = [np.random.randint(8) for _ in range(len(durs))]
        pans = [np.random.uniform(0,1) for _ in range(len(durs))]
        notelist += skora.make_notelist(pfields={'synthName': 'FMWT', 'table': tables, 'dur': durs, 'dc': dc, 'amplitude': [0.1], 'frequency': freqs, 'attackTime': attks, 'releaseTime': rels, 'pan': pans, 'reverberation': 0.667})
    
    skora.notelist_to_synthSeq(notelist, os.path.join(FILEPATH, 'rp_super.synthSequence'))

if __name__ == "__main__":
    time_materials()