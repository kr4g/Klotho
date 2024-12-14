from klotho.topos.graphs.fields import *
from klotho.topos.graphs.fields.algorithms import *
from klotho.skora.visualization.field_plots import *
from klotho.topos.sets import CombinationSet as CS
from klotho.tonos import cents_to_ratio
from klotho.aikous.expression import db_amp
from time import sleep


# f1 = load_field('/Users/ryanmillett/Klotho/examples/thesis/field_A_B_interaction.pkl')
# print(f1)
# plot_field_heatmap(f1, path=path)

f_a = load_field('/Users/ryanmillett/Klotho/examples/thesis/quantum_fluid_field.pkl')
f_b = load_field('/Users/ryanmillett/Klotho/examples/thesis/brain_wave_fluid_field.pkl')
f_c = load_field('/Users/ryanmillett/Klotho/examples/thesis/gravitational_distortion_field.pkl')
f_ab = load_field('/Users/ryanmillett/Klotho/examples/thesis/field_A_B_interaction.pkl')
f_ac = load_field('/Users/ryanmillett/Klotho/examples/thesis/field_A_C_interaction.pkl')
f_bc = load_field('/Users/ryanmillett/Klotho/examples/thesis/field_B_C_interaction.pkl')

fields = {
    'A': f_a,
    'B': f_b,
    'C': f_c,
    ('A', 'B'): f_ab,
    ('A', 'C'): f_ac,
    ('B', 'C'): f_bc
}

cs = CS(('A', 'B', 'C'), 2)
# for combo in cs.combos:
#     print(combo)

# ------------------------------

# path = find_navigation_path(f_a, 4000, 616)
# for pos in path:
#     if pos[1] > 0:
#         print(pos[0], pos[1])
#     # print(pos[0], pos[1])
# plot_field_heatmap(f_a, path=path)

a = [f_a[node] for node in f_a.nodes]
b = [f_b[node] for node in f_b.nodes]
c = [f_c[node] for node in f_c.nodes]
ab = [f_ab[node] for node in f_ab.nodes]
ac = [f_ac[node] for node in f_ac.nodes]
bc = [f_bc[node] for node in f_bc.nodes]

lam = lambda f_vals: (min(f_vals), max(f_vals))

# print(lam(a))
# print(lam(b))
# print(lam(c))
# print(lam(ab))
# print(lam(ac))
# print(lam(bc))

from klotho.aikous.messaging import Scheduler

sch = Scheduler()
path_step = 2000
path = find_navigation_path(f_ab, path_step, 0.6)
step = 10
# print(path[:50])
# plot_field_heatmap(f_ab, path=path[::step])
# plot_path_color_bar(path[::step])
import numpy as np
import random

field_sources = ['fa_val', 'fb_val', 'fc_val', 'fab_val', 'fac_val', 'fbc_val']
# n = 3
t_scale = 3

'''
    var freq = \freq.kr(440).lag(\freqLag.kr(0.2));
    var amp = \amp.kr(0.5).lag(\ampLag.kr(0.2));
    var fold_amount = \fold_amount.kr(1).lag(\foldLag.kr(0.1));
    var fold_mod_freq = \fold_mod_freq.kr(0.5).lag(\foldModFreqLag.kr(0.1));
    var am_freq = \am_freq.kr(2).lag(\amFreqLag.kr(0.2));
    var am_amount = \am_amount.kr(0.5).lag(\amAmountLag.kr(0.2));
    var fm_index = \fm_index.kr(1).lag(\fmIndexLag.kr(0.2));
    var fm_mod_freq = \fm_mod_freq.kr(2).lag(\fmModFreqLag.kr(0.2));
    var pan = \pan.kr(0).lag(\panLag.kr(0.2));

    var detune = \detune.kr(0.1).lag(\detuneLag.kr(0.2));
    var filter_freq = \filterFreq.kr(2000).lag(\filterFreqLag.kr(0.2));
    var filter_q = \filterQ.kr(0.5).lag(\filterQLag.kr(0.2));

    var lfo1_freq = \lfo1Freq.kr(0.1).lag(\lfo1FreqLag.kr(0.2));
    var lfo1_amount = \lfo1Amount.kr(50).lag(\lfo1AmountLag.kr(0.2));
    var lfo2_freq = \lfo2Freq.kr(0.2).lag(\lfo2FreqLag.kr(0.2));
    var lfo2_amount = \lfo2Amount.kr(0.5).lag(\lfo2AmountLag.kr(0.2));

    var mod_index = \modIndex.kr(1).lag(\modIndexLag.kr(0.2));
    var mod_freq = \modFreq.kr(1).lag(\modFreqLag.kr(0.2));
'''
mappings = {
    'freq': random.choice(field_sources),
    'amp': random.choice(field_sources),
    'fold_amount': random.choice(field_sources),
    'am_freq': random.choice(field_sources),
    'am_amount': random.choice(field_sources),
    'fm_index': random.choice(field_sources),
    'fm_mod_freq': random.choice(field_sources),
    'pan': random.choice(field_sources),
    'detune': random.choice(field_sources),
    'filter_freq': random.choice(field_sources),
    'filter_q': random.choice(field_sources),
    'lfo1_freq': random.choice(field_sources),
    'lfo1_amount': random.choice(field_sources),
    'lfo2_freq': random.choice(field_sources),
    'lfo2_amount': random.choice(field_sources),
    'mod_index': random.choice(field_sources),
    'mod_freq': random.choice(field_sources)
}


# freq_range = (83.25, 666)
freq_range = (166.5, 999)

uid = sch.new_event_with_id('droon', 0, gate=1, freq=freq_range[0], amp=0.0)

# save each iteration as a line in a text file
with open('pfields.txt', 'w') as f:
    for i, pos in enumerate(path[::-1][::step]):
        fa_val = np.interp(f_a[pos[0]], lam(a), (-1, 1))
        fb_val = np.interp(f_b[pos[0]], lam(b), (-1, 1))
        fc_val = np.interp(f_c[pos[0]], lam(c), (-1, 1))
        fab_val = np.interp(f_ab[pos[0]], lam(ab), (-1, 1))
        fac_val = np.interp(f_ac[pos[0]], lam(ac), (-1, 1))
        fbc_val = np.interp(f_bc[pos[0]], lam(bc), (-1, 1))
        
        freq = np.interp(eval(mappings['freq']), (-1, 1), (np.interp(fb_val * fac_val, (-1, 1), (freq_range[0] * cents_to_ratio(-167), freq_range[0])), np.interp(fc_val * fbc_val, (-1, 1), (freq_range[1], freq_range[1] * 1.3))))
        pfields = {
            'freq': freq,
            'freqLag': t_scale,
            'amp': np.interp(eval(mappings['amp']), (-1, 1), (db_amp(-22), db_amp(-56))) * np.interp(freq, (freq_range[0] * cents_to_ratio(-167), freq_range[1] * 1.3), (1.0, 0.5)),
            'ampLag': t_scale,
            'fold_amount': np.interp(eval(mappings['fold_amount']), (-1, 1), (1, 4)),
            'foldLag': t_scale,
            'am_freq': np.interp(eval(mappings['am_freq']), (-1, 1), (0.15, 330)),
            'amFreqLag': t_scale,
            'am_amount': np.interp(eval(mappings['am_amount']), (-1, 1), (0.01, 0.75)),
            'amAmountLag': t_scale,
            'fm_index': np.interp(eval(mappings['fm_index']), (-1, 1), (0.01, 7)),
            'fmIndexLag': t_scale,
            'fm_mod_freq': np.interp(eval(mappings['fm_mod_freq']), (-1, 1), (0.5, 250)),
            'fmModFreqLag': t_scale,
            'pan': np.interp(eval(mappings['pan']), (-1, 1), (-1, 1)),
            'panLag': t_scale,
            'detune': np.interp(eval(mappings['detune']), (-1, 1), (0.01, 0.75)),
            'detuneLag': t_scale,
            'filter_freq': np.interp(eval(mappings['filter_freq']), (-1, 1), (200, 2000)),
            'filterFreqLag': t_scale,
            'filter_q': np.interp(eval(mappings['filter_q']), (-1, 1), (0.01, 0.75)),
            'filterQLag': t_scale,
            'lfo1_freq': np.interp(eval(mappings['lfo1_freq']), (-1, 1), (0.1, 3.75)),
            'lfo1FreqLag': t_scale,
            'lfo1_amount': np.interp(eval(mappings['lfo1_amount']), (-1, 1), (0.3, 50.5)),
            'lfo1AmountLag': t_scale,
            'lfo2_freq': np.interp(eval(mappings['lfo2_freq']), (-1, 1), (0.2, 8.15)),
            'lfo2FreqLag': t_scale,
            'lfo2_amount': np.interp(eval(mappings['lfo2_amount']), (-1, 1), (0.1, 17.5)),
            'lfo2AmountLag': t_scale,
            'mod_index': np.interp(eval(mappings['mod_index']), (-1, 1), (0.1, 45.5)),
            'modIndexLag': t_scale,
            'mod_freq': np.interp(eval(mappings['mod_freq']), (-1, 1), (0.1, 9.7)),
            'modFreqLag': t_scale
        }
        
        # f.write(f"synth droon freq {pfields['freq']} amp {pfields['amp']} fold_amount {pfields['fold_amount']} am_freq {pfields['am_freq']} am_amount {pfields['am_amount']} fm_index {pfields['fm_index']} fm_mod_freq {pfields['fm_mod_freq']} pan {pfields['pan']} detune {pfields['detune']} filter_freq {pfields['filter_freq']} filter_q {pfields['filter_q']} lfo1_freq {pfields['lfo1_freq']} lfo1_amount {pfields['lfo1_amount']} lfo2_freq {pfields['lfo2_freq']} lfo2_amount {pfields['lfo2_amount']} mod_index {pfields['mod_index']} mod_freq {pfields['mod_freq']}\n")
        # make this round all the numbers to 4 decimal places
        # line = f"{pfields['freq']} {pfields['amp']} {pfields['fold_amount']} {pfields['am_freq']} {pfields['am_amount']} {pfields['fm_index']} {pfields['fm_mod_freq']} {pfields['pan']} {pfields['detune']} {pfields['filter_freq']} {pfields['filter_q']} {pfields['lfo1_freq']} {pfields['lfo1_amount']} {pfields['lfo2_freq']} {pfields['lfo2_amount']} {pfields['mod_index']} {pfields['mod_freq']}\n"
        line = (
                f"{pfields['freq']:.4f} {pfields['amp']:.4f} {pfields['fold_amount']:.4f} "
                f"{pfields['am_freq']:.4f} {pfields['am_amount']:.4f} {pfields['fm_index']:.4f} "
                f"{pfields['fm_mod_freq']:.4f} {pfields['pan']:.4f} {pfields['detune']:.4f} "
                f"{pfields['filter_freq']:.4f} {pfields['filter_q']:.4f} {pfields['lfo1_freq']:.4f} "
                f"{pfields['lfo1_amount']:.4f} {pfields['lfo2_freq']:.4f} {pfields['lfo2_amount']:.4f} "
                f"{pfields['mod_index']:.4f} {pfields['mod_freq']:.4f}\n"
            )
        # line = f" freq amp fold_amount am_freq am_amount fm_index fm_mod_freq pan detune filter_freq filter_q lfo1_freq lfo1_amount lfo2_freq lfo2_amount mod_index mod_freq\n"
        print(line)
        # sleep for a second
        # sleep(0.16)
        # f.write(line)
        sch.set_synth(uid, start=(i + 1) * t_scale, **pfields)

    sch.set_synth(uid, start=(len(path[::step]) + 1) * t_scale, gate=0)
f.close()
# ------------------------------

# '''
#     var snd, position, detuneRatio, baseFreq, amDepth, foldAmount;
#     position = LFNoise1.kr(LFNoise1.kr(\positionRate.kr(0.2, 0.2)).range(0.1, 1.7)).range(\positionMin.kr(0, 0.1), \positionMax.kr(1, 0.1));
#     detuneRatio = (\detuneCents.kr(10, \dtLag.kr(0.1)) * 0.01).midiratio;
#     baseFreq = \freq.kr(110, 0.1);
#     amDepth = \amDepth.kr(0.5, 0.2);
#     foldAmount = LFNoise1.kr(\foldRate.kr(0.1, 0.2)).range(\foldMin.kr(0.5, 0.1), \foldMax.kr(2, 0.1));

#     snd = VOsc3.ar(
#         \bufnum.kr(0) + (position.clip(0, 1) * (\bufferCount.kr(12) - 1) - 0.5),
#         baseFreq / detuneRatio,
#         baseFreq,
#         baseFreq * detuneRatio,
#         [1, 1, 1] / 3
#     );

#     snd = snd * (1 - (amDepth * SinOsc.kr(\amRate.kr(6.5, 0.2))));

#     snd = LPF.ar(snd, LFNoise1.kr(\filterRate.kr(0.1, 0.2)).range(\filterMin.kr(200, 0.1), \filterMax.kr(2500, 0.1)));

#     snd = SelectX.ar(
#         \foldAmount.kr(0, 0.2),
#         [
#             snd,
#             Fold.ar(snd * foldAmount, -1, 1)
#         ]
#     );

#     snd = Pan2.ar(snd, \pan.kr(0, 0.1));
# '''

# mappings = {
#     'positionRate': random.choice(field_sources),
#     'positionMin': random.choice(field_sources),
#     'positionMax': random.choice(field_sources),
#     'detuneCents': random.choice(field_sources),
#     'dtLag': t_scale,
#     'freq': random.choice(field_sources),
#     'amp': random.choice(field_sources),
#     'amDepth': random.choice(field_sources),
#     'foldRate': random.choice(field_sources),
#     'foldMin': random.choice(field_sources),
#     'foldMax': random.choice(field_sources),
#     'amRate': random.choice(field_sources),
#     'filterRate': random.choice(field_sources),
#     'filterMin': random.choice(field_sources),
#     'filterMax': random.choice(field_sources),
#     'foldAmount': random.choice(field_sources),
#     'pan': random.choice(field_sources)
# }

# fund = 83.25 * 2**0
# freq_range = (fund, fund * cents_to_ratio(67))

# uid = sch.new_event_with_id('hypergrowl', 0, gate=1, freq=freq_range[0], amp=0.0, attack=t_scale, filterMax=166.5, lag=t_scale)

# # path = find_navigation_path(f_a, path_step, 0.16)
# for i, pos in enumerate(path[::step]):
#     fa_val = np.interp(f_a[pos[0]], lam(a), (-1, 1))
#     fb_val = np.interp(f_b[pos[0]], lam(b), (-1, 1))
#     fc_val = np.interp(f_c[pos[0]], lam(c), (-1, 1))
#     fab_val = np.interp(f_ab[pos[0]], lam(ab), (-1, 1))
#     fac_val = np.interp(f_ac[pos[0]], lam(ac), (-1, 1))
#     fbc_val = np.interp(f_bc[pos[0]], lam(bc), (-1, 1))
    
#     positionRate = np.interp(eval(mappings['positionRate']), (-1, 1), (0.1, 3.7))
#     positionMin = np.interp(eval(mappings['positionMin']), (-1, 1), (0, 0.33))
#     positionMax = np.interp(eval(mappings['positionMax']), (-1, 1), (0.67, 1))
#     detuneCents = np.interp(eval(mappings['detuneCents']), (-1, 1), (0.0, 16.7))
#     # lag = t_scale
#     amp = np.interp(eval(mappings['amp']), (-1, 1), (db_amp(-12), db_amp(-3)))
#     freq = np.interp(eval(mappings['freq']), (-1, 1), (fund, np.interp(fab_val * fc_val, (-1, 1), (fund * cents_to_ratio(-16), fund * cents_to_ratio(16)))))
#     amDepth = np.interp(eval(mappings['amDepth']), (-1, 1), (0.1, 0.9))
#     foldRate = np.interp(eval(mappings['foldRate']), (-1, 1), (0.1, 0.2))
#     foldMin = np.interp(eval(mappings['foldMin']), (-1, 1), (1, 2))
#     foldMax = np.interp(eval(mappings['foldMax']), (-1, 1), (1, 2))
#     foldAmount = np.interp(eval(mappings['foldAmount']), (-1, 1), (0, 0.25))
#     amRate = np.interp(eval(mappings['amRate']), (-1, 1), (0.33, np.interp(foldMax, (1, 2), (6, 33.33))))
#     filterRate = np.interp(eval(mappings['filterRate']), (-1, 1), (0.1, np.interp(foldAmount, (0, 0.25), (1.67, 3.33))))
#     filterMin = np.interp(eval(mappings['filterMin']), (-1, 1), (166.5, 333))
#     filterMax = np.interp(eval(mappings['filterMax']), (-1, 1), (999, np.interp(foldMin, (1, 2), (1332, 1332*2))))
#     pan = np.interp(eval(mappings['pan']), (-1, 1), (-1, 1))
    
#     pfields = {
#         'positionRate': positionRate,
#         'positionMin': 0,
#         'positionMax': 1,
#         'detuneCents': detuneCents,
#         # 'lag': lag,
#         'freq': freq,
#         'amp': amp,
#         'amDepth': 0,
#         'foldRate': foldRate,
#         'foldMin': foldMin,
#         'foldMax': foldMax,
#         'foldAmount': 0,
#         'amRate': 0,
#         'filterRate': filterRate,
#         'filterMin': 666,
#         'filterMax': 1332*2,
#         'pan': pan
#     }
    
#     sch.set_synth(uid, start=(i + 1) * t_scale, **pfields)
    
# sch.set_synth(uid, start=(len(path[::step]) + 1) * t_scale, gate=0)

# --------------------
# '''
# 	lag = \lag.kr(1);
# 	freq = \freq.kr(220, lag);
# 	rate = \rate.kr(3, lag);
# 	sig = SinOsc.ar(freq * (1..4)).lincurve(-1,1,-1,1,\curve.kr(0, lag));
# 	env = EnvGen.ar(Env.perc(attackTime: 0.03, releaseTime: 1 / rate), gate: Impulse.ar(rate));
# 	sig = Fold.ar(sig * \od.kr(1, lag), -1, 1);
# 	sig = sig * env;
# 	sig = sig * EnvGen.kr(Env.asr(2, 1, 2), \gate.kr(1), doneAction: 2);
# 	sig = Pan2.ar(sig, \pan.kr(0)) * \amp.kr(0.5, lag);
# '''

# path = find_navigation_path(f_a, path_step, 0.33)

# mappings = {
#     'lag': t_scale,
#     'freq': random.choice(field_sources),
#     'rate': random.choice(field_sources),
#     'curve': random.choice(field_sources),
#     'od': random.choice(field_sources),
#     'width': random.choice(field_sources),
#     'amp': random.choice(field_sources),
#     'panRate': random.choice(field_sources)
# }

# uid = sch.new_event_with_id('pulsr', 0, gate=1, freq=166.5, rate=3, curve=0, od=1, amp=0.0, pan=0)

# # from opensimplex import OpenSimplex

# for i, pos in enumerate(path[::step]):
#     fa_val = np.interp(f_a[pos[0]], lam(a), (-1, 1))
#     fb_val = np.interp(f_b[pos[0]], lam(b), (-1, 1))
#     fc_val = np.interp(f_c[pos[0]], lam(c), (-1, 1))
#     fab_val = np.interp(f_ab[pos[0]], lam(ab), (-1, 1))
#     fac_val = np.interp(f_ac[pos[0]], lam(ac), (-1, 1))
#     fbc_val = np.interp(f_bc[pos[0]], lam(bc), (-1, 1))
    
#     lag = t_scale
#     np.random.seed(int(eval(mappings['freq'])**2 * 1000))
#     freq = np.random.uniform(333, np.interp(eval(mappings['freq']), (-1, 1), (333, 666)))
#     rate = np.interp(eval(mappings['rate']), (-1, 1), (3, 15))
#     width = 1/rate#np.interp(eval(mappings['width']), (-1, 1), (1/rate, 1/(rate * 0.9692)))
#     curve = np.interp(eval(mappings['curve']), (-1, 1), (0, 32))
#     od = np.interp(eval(mappings['od']), (-1, 1), (1, np.interp(fab_val * fac_val, (-1, 1), (1, 1.1))))
#     amp = np.interp(eval(mappings['amp']), (-1, 1), (db_amp(-46), db_amp(-21))) * np.interp(freq, (166.5, 666), (1.0, 0.5))
#     pan = np.interp(eval(mappings['panRate']), (-1, 1), (0.5, 5))
    
#     pfields = {
#         'lag': lag,
#         'freq': freq,
#         'rate': rate,
#         'curve': curve,
#         'od': od,
#         'width': 0,
#         'amp': amp,
#         'panRate': pan
#     }
    
#     sch.set_synth(uid, start=(i + 1) * t_scale, **pfields)

# sch.set_synth(uid, start=(len(path[::step]) + 1) * t_scale, gate=0)

# sch.run()