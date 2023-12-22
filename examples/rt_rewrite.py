# examples/rt_rewrite.py
import sys
import os
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from allopy import chronos
from allopy.chronos import rhythm_trees as rt
from allopy import tonos
from allopy import topos
from allopy import aikous
from allopy.topos.random import rando
from allopy.topos import formal_grammars as fg
from allopy.aikous import DYNAMICS as DYN
from allopy import skora
from allopy.skora.instruments import PFIELDS
from tabulate import tabulate
import pprint
pp = pprint.PrettyPrinter(indent=4)

FILEPATH = skora.set_score_path()

import numpy as np

def materials(r_tree: rt.RT, pitch_contour: tuple = (0, -1, 2, 1, 0, -1, 3, -3)):
    rt_rotations = tuple(r_tree.rotate(i) for i in range(len(r_tree.ratios)))
    freq_ratios = tuple(tonos.cents_to_ratio(c * 100) for c in pitch_contour)
    return rt_rotations, freq_ratios

def layer_1(rt_rotations, max_rotations: int = 6, init_bpm: float = 36.0, root_freq: float = tonos.pitchclass_to_freq('F#4'), freq_ratios: tuple = (1.0,)):
    notelist = []
    bpm = init_bpm
    max_rotations = min(max_rotations, len(rt_rotations))
    synths = ['SineEnv', 'OscAM', 'OscTrm', 'Vib']
    amps = list(np.linspace(DYN.ppp.max, DYN.p.max, 5))
    for j, rt_r in enumerate(rt_rotations[:max_rotations]):
        start = 0.2
        synth = synths[j % len(synths)]
        amp_scale = (1 / max_rotations**2)
        transpose = 100/81
        for i, r in enumerate(rt_r.ratios):
            new_row = getattr(PFIELDS, synth, None).value.copy()  # get default pfields for current synth
            
            # DO CALCULATIONS...
            duration = chronos.beat_duration(r, bpm)
            dc       = np.random.uniform(0.167, 1.167)  # duty cycle
            dur      = duration * dc
            freq     = root_freq * freq_ratios[i % len(freq_ratios)]
            amp      = amps[i % len(amps)] if i > 0 else DYN.mp.min
            amp      = amp * aikous.amp_freq_scale(freq)
            pan      = np.random.uniform(-1, 1)
            
            # BUILD NOTELIST ROW...
            new_row['start']       = start
            new_row['dur']         = dur
            new_row['frequency']   = freq * transpose**(j)
            new_row['amplitude']   = amp * amp_scale + amp * (1 / new_row['frequency'])
            new_row['attackTime']  = np.random.uniform(dur * (1.167 - dc), dur)
            new_row['releaseTime'] = np.random.uniform(dur * 0.333, duration)
            new_row['pan']         = pan
            
            if synth == 'OscAM':
                new_row['amplitude'] *= 1.0833
                new_row['amFunc']  = np.random.choice([0, 3])
                new_row['am1']     = np.random.uniform(0.0, 1.0)
                new_row['am2']     = np.random.uniform(0.123, 0.91)
                new_row['amRise']  = dur * np.random.uniform(0.667, 1.0)
                new_row['amRatio'] = np.random.uniform(0.0, 2.0)
            
            if synth in ['OscAM', 'FMWT']:
                new_row['reverberation'] = np.interp(amp, [DYN.pppp.min, DYN.p.max], [0.0, 0.9692])
                
            if synth in ['OscTrm', 'Vib', 'FMWT']:
                new_row['amplitude'] *= 0.333
                new_row['table']    = np.random.randint(8)
                new_row['vibRate1'] = np.random.uniform(0.167, 13.3)
                new_row['vibRate2'] = np.random.uniform(0.125, 17.1)
                new_row['vibRise']  = dur * np.random.uniform(0.667, 1.0)
                new_row['vibDepth'] = np.random.uniform(0.00167, 0.023)
            
            if synth == 'OscTrm':
                new_row['table']    = np.random.randint(8)
                new_row['trm1']     = np.random.uniform(0.667, 33.667)
                new_row['trm2']     = np.random.uniform(0.125, 37.833)
                new_row['trmRise']  = dur * np.random.uniform(0.667, 1.0)
                new_row['trmDepth'] = np.random.uniform(0.0167, 0.667)
            
            notelist.append(new_row) # ADD ROW TO NOTELIST
            start += duration        # ADVANCE TIME...
    return notelist

def layer_2(rt_rotations, max_rotations: int = 1, init_bpm: float = 36.0, root_freq: float = tonos.pitchclass_to_freq('F#3'), freq_ratios: tuple = (1.0,)):
    notelist = []
    bpm = init_bpm
    max_rotations = min(max_rotations, len(rt_rotations))
    synths = ['FMWT']
    amps = list(np.linspace(DYN.mf.min, DYN.pp.min, 7))
    for j, rt_r in enumerate(rt_rotations[:max_rotations]):
        start = 0.2
        synth = synths[j % len(synths)]
        amp_scale = (1 / max_rotations**1.6)
        transpose = 100/81
        t_pow = 0
        for i, r in enumerate(rt_r.ratios):
            new_row = getattr(PFIELDS, synth, None).value.copy()  # get default pfields for current synth
            
            duration = chronos.beat_duration(r, bpm)
            dc = np.random.uniform(0.333, 1.0833)
            dur = duration * dc
            
            amp = amps[i % len(amps)] if i > 0 else DYN.mp.min
            freq = root_freq * freq_ratios[i % len(freq_ratios)]
            amp = amp * aikous.amp_freq_scale(freq)
            
            t_pow += 1 if i % len(freq_ratios) == 0 else 0
            
            pan = np.random.uniform(-1, 1)
            
            # BUILD NOTELIST ROW
            new_row['start']       = start
            new_row['dur']         = dur
            new_row['frequency']   = freq * transpose**t_pow
            new_row['amplitude']   = amp * amp_scale + amp * (1 / new_row['frequency'])
            new_row['attackTime']  = np.random.uniform(dur * 0.1, dur * 0.3)
            new_row['releaseTime'] = np.random.uniform(dur * 0.167, duration)
            new_row['pan']         = pan
            
            if synth in ['OscAM', 'FMWT']:
                new_row['reverberation'] = np.interp(amp, [DYN.mf.min, DYN.pp.min], [0.9692, 0.01])
                
            if synth in ['OscTrm', 'Vib', 'FMWT']:
                # new_row['amplitude'] *= 0.333
                new_row['table']    = np.random.randint(8)
                new_row['vibRate1'] = np.random.uniform(0.833, 6.33)
                new_row['vibRate2'] = np.random.uniform(0.167, 9.33)
                new_row['vibRise']  = dur * np.random.uniform(0.667, 1.0)
                new_row['vibDepth'] = np.random.uniform(0.0, 0.023)
                if synth == 'FMWT':
                    new_row['idx1']   = np.random.randint(1, 5)
                    new_row['idx2']   = np.random.randint(new_row['idx2'], new_row['idx2'] + 3)
                    new_row['idx3']   = 1
                    new_row['carMul'] = 1#np.random.uniform(1, 5/4)
                    new_row['modMul'] = 0

            notelist.append(new_row) # ADD ROW TO NOTELIST
            start += duration        # ADVANCE TIME
    return notelist

if __name__ == '__main__':
    
    subdivisions = ((8, (5, 3)), (13, (3, 2, (5, (3, 1, 1, 2)))), (5, (2, 1, 1, (3, (3, 5, 2, 1)))), 2, (3, ((3, (3, 5, 2, 1)), (3, (3, 5, 2, 1)), 2, (8, ((5, (2, 1, 1, (3, (3, 5, 2, 1)))), (3, (3, (5, (2, 1, 1, (3, (3, 5, 2, 1)))), (2, (3, (2, (3, 2)))), (1, (1, 1, 1, 1, (1, (1, 1)), (1, (1, 1, 1)))))))))))
    r_tree = rt.RT(duration=13, subdivisions=subdivisions)
    rt_rotations, freq_ratios = materials(r_tree)
    init_bpm = 18
    
    notelists = []
    notelists += layer_1(rt_rotations=rt_rotations[3:], max_rotations=9, init_bpm=init_bpm, freq_ratios=freq_ratios)
    notelists += layer_2(rt_rotations=rt_rotations, max_rotations=3, init_bpm=init_bpm, freq_ratios=freq_ratios)
    
    skora.notelist_to_synthSeq(notelists, os.path.join(FILEPATH, 'rt_layers.synthSequence'))
