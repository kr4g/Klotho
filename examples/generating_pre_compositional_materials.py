# examples/generating_pre_compositional_materials.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy import tonos
from allopy import topos
from allopy.topos.random import rando
from allopy import aikous
from allopy import skora

FILEPATH = skora.set_score_path()

import numpy as np
import pandas as pd
from IPython.display import display

from allopy.topos import formal_grammars as frgr
def materials():
    l1, l2 = ('Π', 'Ξ'), ('ϕ', 'ϖ', 'Ϡ')
    
    print(f'l1 = {l1}\nl2 = {l2}\n')
    
    iso = topos.iso_pairs(l1, l2)
    print(f'iso_pairs(l1, l2) = {iso}\n')
    kleis = ('𒋫', '𒌦', '𒆬', '𒊒', '𒍑', '𒅋')
    print(kleis)
    
    h_map = topos.homotopic_map(kleis, iso)
    for e in h_map:
        print(e)
    
    synths_names = ['OscEnv', 'FMWT', 'OscAM', 'PluckedString', 'SineEnv', 'AddSyn', 'SubSyn', 'PluckedString']
    
    enc_kleis = rando.rand_encode(kleis, synths_names)
    
    synths = [enc_kleis[k] for k in kleis]
    print(synths)
    h_map = topos.homotopic_map(synths, iso)
    for e in h_map:
        print(e)
    
    beat_ratios = ['1/4', '1/8', '1/8']
    enc_l1 = rando.rand_encode(l1, tonos.PITCH_CLASSES.N_TET_12.names.as_sharps)
    enc_l2 = rando.rand_encode(l2, beat_ratios)
    
    color = [enc_l1[k] for k in l1]
    talea = [enc_l2[k] for k in l2]
    
    iso = topos.iso_pairs(color, talea)
    print(iso)
    h_map = topos.homotopic_map(synths, iso)
    for e in h_map:
        print(e)

if __name__ == '__main__':
    materials()
