# examples/generating_pre_compositional_materials.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy.chronos import rhythm_trees as rt
from allopy import tonos
from allopy import topos
from allopy.topos.random import rando
from allopy.topos import formal_grammars as frgr
from allopy import aikous
from allopy import skora
from tabulate import tabulate
import pprint
pp = pprint.PrettyPrinter(indent=4)

FILEPATH = skora.set_score_path()

import numpy as np
import pandas as pd
# from fractions import Fraction
from IPython.display import display


def materials():
    # l1, l2 = ('Π', 'Ξ', 'Σ'), ('ϕ', 'ϖ', 'Ϡ', 'ϗ')
    S1, S2 = [g.value for g in frgr.alphabets.ANCIENT_GREEK.upper], [g.value for g in frgr.alphabets.Mathematical]
    np.random.seed(616)
    np.random.shuffle(S1)
    np.random.shuffle(S2)
    l1, l2 = tuple(S1[:2]), tuple(S2[:3])
    print(f'l1 = {l1}, l2 = {l2}\n')
    
    iso = topos.iso_pairs(l1, l2)
    print(f'iso_pairs(l1, l2) = \n\n\t{iso}\n')
    
    # S3 = [g.value for g in frgr.alphabets.CUNEIFORM.Akkadian]
    # np.random.shuffle(S3)
    # l3_len = max(len(l1), len(l2)) + 1
    # l3 = tuple(S3[:l3_len])
    # iso = topos.iso_pairs(iso, l3)
    # print(f'iso_pairs(iso, l3) = {iso}\n')
    S4 = [s.value for s in frgr.alphabets.RUNIC.OLD_NORSE.Elder_Futhark] + [s.value for s in frgr.alphabets.RUNIC.OLD_NORSE.Younger_Futhark]+ [s.value for s in frgr.alphabets.RUNIC.OLD_NORSE.Anglo_Saxon_Futhorc]
    np.random.seed(919)
    np.random.shuffle(S4)
    kleis = tuple(S4[:len(iso)])
    print(f'kleis = {kleis}\n')
    
    print(f'homotopic_map(kleis, iso) = \n')
    h_map = topos.homotopic_map(kleis, iso)
    for e in h_map:
        print(f'\t{e}')
    print()    
    
    # print(f'homotopic_map(iso, kleis) = \n')
    # h_map = topos.homotopic_map(iso, kleis)
    # for e in h_map:
    #     print(f'\t{e}')
    # print()
    
    # synths_names = ['OscEnv', 'FMWT', 'OscAM', 'SineEnv', 'AddSyn', 'SubSyn']
    
    # enc_kleis = rando.rand_encode(kleis, synths_names)
    
    # synths = [enc_kleis[k] for k in kleis]
    # # print(synths)
    # h_map = topos.homotopic_map(synths, iso)
    # for e in h_map:
    #     print(f'\t{e}')
    # print()
    proportions = tuple([np.random.randint(1,8) for _ in range(len(l2))])
    # r_tree = rt.RT(('?', ((4, 4), proportions)))
    beat_ratios = rt.measure_ratios(rt.RT(('?', ((1, 1), proportions))))
    enc_l1 = rando.rand_encode(l1, tonos.PITCH_CLASSES.N_TET_12.names.as_sharps[::2])
    enc_l2 = rando.rand_encode(l2, [str(r) for r in beat_ratios])
    
    color = [enc_l1[k] for k in l1]
    talea = [enc_l2[k] for k in l2]
    
    # print(f'enc_l1 = {enc_l1}\nenc_l2 = {enc_l2}\n')
    for k, v in enc_l1.items():
        print(f'{k} : {v}')
    print()
    for k, v in enc_l2.items():
        print(f'{k} : {v}')
    print()
    
    iso_mel = topos.iso_pairs(color, talea)
    print(f'iso_pairs(l1, l2) = {iso}')
    print(f'iso_pairs(l1, l2) = {iso_mel}\n')
    
    iso_mel = topos.iso_pairs(color, [round(chronos.beat_duration(t, 66), 2) for t in talea])
    h_map = topos.homotopic_map(kleis, iso_mel)
    for e in h_map:
        print(f'\t{e}')
    print()
    iso_mel = topos.iso_pairs(color, talea)
    h_map = topos.homotopic_map(kleis, iso_mel)
    
    offsets = [0] + [topos.Fraction(r[1]) for r in h_map[0][1][:len(kleis) - 1]]
    offsets = [str(r) for r in np.cumsum(offsets)]
    print(f'offsets = {offsets}\n')
    
    enc_kleis = {k: v for k, v in zip(kleis, offsets)}
    for k, v in enc_kleis.items():
        print(f'{k} : {v}')
    print()
    
    h_map = topos.homotopic_map(offsets, iso_mel)
    for e in h_map:
        print(f'\t{e}')
        # print(tabulate(e, headers='firstrow', tablefmt='plain'))
    
    return h_map

def composition(musiplex):
    tempo = 66
    for line in musiplex:
        offset = topos.Fraction(line[0])
        start_time = chronos.beat_duration(ratio=offset, bpm=tempo)
        iso_mel = line[1]
        for pitch_name, m_ratio in iso_mel:
            duration = chronos.beat_duration(ratio=topos.Fraction(m_ratio), bpm=tempo)
            freq = tonos.pitchclass_to_freq(pitch_name)
            print(f'{start_time} : {freq} : {duration}')
            start_time += duration

if __name__ == '__main__':
    musiplex = materials()
    # score_df = composition(musiplex)
    # skora.synthSeq_to_df(score_df, FILEPATH)
