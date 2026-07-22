// MAT 111MC "edm" kit — beats, sweeps, and wubs.
// Adapted from Nathan Ho's 2025-08-14-mobius.scd and 2025-11-09-dnb.scd,
// used with permission — nathanho.bandcamp.com
(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
var instDir = outputDir +/+ "instruments";
var fxDir = outputDir +/+ "effects";
outputDir.mkdir;
instDir.mkdir;
fxDir.mkdir;

SynthDef(\edm_deepKick, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, impact;
    snd = SinOsc.ar(EnvGen.ar(Env.perc(0, 3, curve: -8)).linexp(0, 1, 40, 120)
        * XLine.ar(2, 1, 0.03) * XLine.ar(4, 1, 0.013));
    snd = snd * (1 + (0.3 * EnvGen.ar(Env.perc(0, 0.1))));
    snd = (snd * -3.dbamp).tanh * 3.dbamp;
    snd = snd ! 2;
    impact = SinOsc.ar(EnvGen.ar(Env.perc(0, 0.1)).linexp(0, 1, 50, 300) * XLine.ar(3, 1, 0.01) * [1, 2.3]);
    impact = impact * [1, EnvGen.ar(Env.perc(0, 0.2))];
    impact = impact.sum;
    impact = impact + (BPF.ar(Hasher.ar(Sweep.ar), 6240, 0.3) * EnvGen.ar(Env.perc(0.01, 0.02)) * -4.dbamp);
    impact = impact + (BPF.ar(Hasher.ar(Sweep.ar), 3240, 0.3) * EnvGen.ar(Env.perc(0.01, 0.02)) * -3.dbamp);
    impact = impact * EnvGen.ar(Env.perc(0.001, 0.4));
    impact = (impact * 5.dbamp).tanh;
    impact = BLowShelf.ar(impact, 200, 0.3, 3);
    impact = BHiShelf.ar(impact, 2300, 0.3, 3);
    impact = impact + LPF.ar(HPF.ar(DelayC.ar(impact * -20.dbamp, 0.1, [23e-3, 45e-3]), 300), 3000);
    impact = impact * 4.dbamp;
    snd = snd + impact;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * EnvGen.ar(Env.perc(0.001, 5, curve: -1), doneAction: 2);
    snd = snd * -10.dbamp * amp;
    OffsetOut.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_kick, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(EnvGen.ar(Env.perc(0, 0.06)).linexp(0, 1, 60, velocity.linexp(0, 1, 500, 3320))
        * XLine.ar(2, 1, 0.01) * XLine.ar(1, 0.5, 0.5));
    snd = snd * EnvGen.ar(Env.perc(0.01, 0.5));
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.03)) * BPF.ar(Hasher.ar(Sweep.ar), 6520, 0.3));
    snd = snd + (EnvGen.ar(Env.perc(0.03, 0.03).delay(0.01)) * BPF.ar(Hasher.ar(Sweep.ar + 1), 9520, 0.3) * -5.dbamp);
    snd = snd * (1 + (10 * EnvGen.ar(Env.perc(0.001, 0.01))));
    snd = snd * 5.dbamp;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = BHiShelf.ar(snd, 3000, 0.3, -3);
    snd = snd.tanh;
    snd = BLowShelf.ar(snd, 200, 0.3, 5);
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -30.dbamp, 0.1, [33.3e-3, 41e-3]), 300), 3000);
    snd = snd * -10.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.3, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_kickSoft, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(EnvGen.ar(Env.perc(0, 0.05, curve: -5)).linexp(0, 1, 55, velocity.linexp(0, 1, 100, 400))
        * XLine.ar(3, 1, 0.01) * XLine.ar(1, 0.7, 0.6));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.7));
    snd = snd + (Hasher.ar(Sweep.ar + [0, 1]) * EnvGen.ar(Env.perc(0.001, 0.01)) * -10.dbamp);
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar + [2, 3]), 3000, 0.3) * EnvGen.ar(Env.perc(0.01, 0.05)) * -9.dbamp);
    snd = snd + (SinOsc.ar(XLine.ar(3000, 1000, 0.007)) * EnvGen.ar(Env.perc(0.001, 0.005)));
    snd = snd * (1 + (2 * EnvGen.ar(Env.perc(0, 0.1))));
    snd = snd.tanh;
    snd = snd * (1 + EnvGen.ar(Env.perc(0, 0.05)));
    snd = BLowShelf.ar(snd, 200, 0.3, 5);
    snd = LPF.ar(snd, 200);
    snd = snd * -7.dbamp;
    snd = snd.sum;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.3, 0.3, curve: -4), doneAction: 2);
    snd = snd * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_snare, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([800, 1034] * XLine.ar(1.3, 1.0, 0.01)).sum;
    snd = snd * EnvGen.ar(Env.perc(0.0001, 0.05));
    snd = snd + (FreqShift.ar(Pulse.ar(XLine.ar(600, 140, 0.03)) * EnvGen.ar(Env.perc(0.001, 0.03)), 34) * 9.dbamp);
    snd = snd + HPF.ar(SinOsc.ar(XLine.ar(500, 100, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.02)), 200);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.2)) * BPF.ar(Hasher.ar(Sweep.ar), 1520, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.03, 0.1)) * BPF.ar(Hasher.ar(Sweep.ar + 1), 820, 0.1) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.4)) * BPF.ar(Hasher.ar(Sweep.ar + 2), 1120, 0.1) * 2.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.01, 0.05)) * BPF.ar(Hasher.ar(Sweep.ar + 3), 3520, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.1, 0.2)) * BPF.ar(Hasher.ar(Sweep.ar + 4), XLine.ar(2120, 500, 0.4), 0.2) * -3.dbamp);
    snd = snd + PitchShift.ar(snd, 0.01, 1.1);
    snd = snd * (1 + EnvGen.ar(Env.perc(0.001, 0.03)));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd.tanh;
    snd = snd + CombC.ar(snd * -15.dbamp, 0.1, 1 / 126, -0.3);
    snd = snd + GVerb.ar(snd * -18.dbamp, 30, 1);
    snd = snd + PitchShift.ar(snd, 0.03, 1.2);
    snd = snd * (1 + EnvGen.ar(Env.perc(0.001, 0.05)));
    snd = snd * -9.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.2, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_snare2, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([900, 1334] * XLine.ar(1.3, 1.0, 0.01)).sum;
    snd = snd * EnvGen.ar(Env.perc(0.0001, 0.05));
    snd = snd + (FreqShift.ar(Pulse.ar(XLine.ar(600, 120, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.05)), 94) * 9.dbamp);
    snd = snd + HPF.ar(SinOsc.ar(XLine.ar(500, 100, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.02)), 200);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.2)) * BPF.ar(Hasher.ar(Sweep.ar), 1520, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.03, 0.1)) * BPF.ar(Hasher.ar(Sweep.ar + 1), 1320, 0.1) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.4)) * BPF.ar(Hasher.ar(Sweep.ar + 2), 1220, 0.1) * 2.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.01, 0.3)) * BPF.ar(Hasher.ar(Sweep.ar + 3), 2520, 0.2) * 3.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.03)) * BPF.ar(Hasher.ar(Sweep.ar + 4), 3520, 0.2) * 8.dbamp);
    snd = snd * (1 + EnvGen.ar(Env.perc(0.001, 0.03)));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd.tanh;
    snd = snd + CombC.ar(snd * -10.dbamp, 0.1, 1 / 96, -0.3);
    snd = snd + GVerb.ar(snd * -20.dbamp, 20, 3);
    snd = snd * (1 + EnvGen.ar(Env.perc(0.001, 0.05)));
    snd = snd * -9.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.25, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_ghostSnare, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([800, 1034] * XLine.ar(1.3, 1.0, 0.01)).sum;
    snd = snd * EnvGen.ar(Env.perc(0.01, 0.02));
    snd = snd + (FreqShift.ar(Pulse.ar(XLine.ar(600, 300, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.05)), 34) * 9.dbamp);
    snd = snd + HPF.ar(SinOsc.ar(XLine.ar(300, 100, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.02)), 200);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.05)) * BPF.ar(Hasher.ar(Sweep.ar), 1520, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.03, 0.05)) * BPF.ar(Hasher.ar(Sweep.ar + 1), 820, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.1)) * BPF.ar(Hasher.ar(Sweep.ar + 2), 1120, 0.3) * 2.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.01, 0.05)) * BPF.ar(Hasher.ar(Sweep.ar + 3), 3520, 0.2) * 8.dbamp);
    snd = snd + (EnvGen.ar(Env.perc(0.1, 0.2)) * BPF.ar(Hasher.ar(Sweep.ar + 4), XLine.ar(2120, 500, 0.4), 0.2) * -3.dbamp);
    snd = snd + PitchShift.ar(snd, 0.01, 1.1);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd.tanh;
    snd = snd * EnvGen.ar(Env.perc(0.02, 0.05));
    snd = snd + GVerb.ar(snd * -20.dbamp, 30, 1);
    snd = snd + PitchShift.ar(snd, 0.03, 1.2);
    snd = snd * (1 + EnvGen.ar(Env.perc(0.001, 0.05)));
    snd = LPF.ar(snd, 6000);
    snd = snd * -15.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.15, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_hat, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(31 * [1, 1.2, 2.4, 3.4, 6.7, 8.9]);
    snd = snd.sum * -10.dbamp;
    snd = LeakDC.ar(snd);
    snd = FreqShift.ar(snd, 165);
    snd = snd + (Hasher.ar(Sweep.ar) * -20.dbamp);
    snd = BPF.ar(snd, (0..3).normalize.linexp(0, 1, 6000, 9000), 0.02).sum;
    3.do { snd = HPF.ar(snd, 3000) };
    snd = snd * 30.dbamp;
    snd = snd + (HPF.ar(SinOsc.ar(XLine.ar(16e3, 1e3, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.01)), 200) * -10.dbamp);
    snd = snd * EnvGen.ar(Env.linen(0.001, 0.01, 0.02, curve: -4));
    snd = snd * (1 + EnvGen.ar(Env.perc(0, 0.01)));
    snd = Pan2.ar(snd, pan) + GVerb.ar(snd * -10.dbamp, 10, 2);
    snd = snd * -10.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.0, 0.08, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_hat2, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(41 * [1, 1.2, 2.4, 3.4, 6.7, 8.9]);
    snd = snd.sum * -10.dbamp;
    snd = LeakDC.ar(snd);
    snd = FreqShift.ar(snd, 165);
    snd = snd + (Hasher.ar(Sweep.ar) * -20.dbamp);
    snd = BPF.ar(snd, (0..3).normalize.linexp(0, 1, 5000, 9000), 0.02).sum;
    3.do { snd = HPF.ar(snd, 3000) };
    snd = snd * 30.dbamp;
    snd = snd + (HPF.ar(SinOsc.ar(XLine.ar(16e3, 1e3, 0.01)) * EnvGen.ar(Env.perc(0.001, 0.01)), 200) * -10.dbamp);
    snd = snd * EnvGen.ar(Env.linen(0.001, 0.01, 0.02, curve: -4));
    snd = snd * (1 + EnvGen.ar(Env.perc(0, 0.01)));
    snd = Pan2.ar(snd, pan) + GVerb.ar(snd * -25.dbamp, 30, 2);
    snd = snd * -9.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.0, 0.1, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_hatLong, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Hasher.ar(Sweep.ar + [0, 1, 2, 3, 4]);
    snd = LeakDC.ar(snd);
    snd = FreqShift.ar(snd, [234, 122, 273, 912, 234]);
    snd = snd.sum;
    snd = BPF.ar(snd, [9934, 12234], 0.1).sum;
    snd = HPF.ar(snd, 6000);
    snd = LPF.ar(snd, XLine.ar(16000, 1000, 0.3));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.3));
    snd = snd * -6.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 1.0, 0.01, curve: -4), doneAction: 2);
    snd = snd * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_hatShort, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Hasher.ar(Sweep.ar + [0, 1, 2, 3, 4]);
    snd = LeakDC.ar(snd);
    snd = FreqShift.ar(snd, [234, 122, 273, 912, 234]);
    snd = snd.sum;
    snd = BPF.ar(snd, [9934, 12234], 0.1).sum;
    snd = HPF.ar(snd, 6000);
    snd = LPF.ar(snd, XLine.ar(16000, 1000, 0.1));
    snd = snd + (SinOsc.ar(XLine.ar(16000, 8000, 0.005)) * EnvGen.ar(Env.perc(0.001, 0.005)));
    snd = snd * EnvGen.ar(Env([0, 1, 0.5, 0], [0.001, 0.05, 0.05], -4));
    snd = snd * -5.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 1.0, 0.01, curve: -4), doneAction: 2);
    snd = snd * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_woodblock, { |out=0, velocity=1.0, amp=1.0, ratio=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([1200, 1934, 3340] * 0.9 * ratio * XLine.ar(2.3, 1.0, 0.001));
    snd = snd * [0, 0, -9].dbamp;
    snd = snd.sum;
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.05));
    snd = snd * (1 + (3 * EnvGen.ar(Env.perc(0, 0.01))));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd.tanh;
    snd = Pan2.ar(snd * 3.dbamp, pan) + GVerb.ar(snd * -20.dbamp, 50, 1);
    snd = snd * -7.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.25, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_clank, { |out=0, velocity=1.0, ratio=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([2534, 2440, 5520] * 0.7 * ratio);
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.1 * [1, 0.3, 0.5]));
    snd = snd.sum;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * (1 + (EnvGen.ar(Env.perc(0.01, 0.3)) * SinOsc.ar(4000)));
    snd = snd + BPF.ar(Hasher.ar(Sweep.ar) * EnvGen.ar(Env.perc(0.001, 0.03)), 2340, 0.1);
    snd = snd + PitchShift.ar(snd, 0.03, 1.3);
    snd = Pan2.ar(snd * 3.dbamp, pan) + GVerb.ar(snd * -15.dbamp, 30, 2);
    snd = snd * -13.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.6, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_blip, { |out=0, amp=1.0, ratio=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(EnvGen.ar(Env([0, 1, 0.3, 0.7], [1, 1, 1].normalizeSum * 0.05, \hold)).linexp(0, 1, 5000, 16e3) * ratio);
    snd = BHiShelf.ar(snd, 6000, 0.3, -5);
    snd = snd * EnvGen.ar(Env.linen(0.001, 0.05, 0.001, curve: -4));
    snd = snd * -20.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.2, curve: -4), doneAction: 2);
    snd = snd * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_clap, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Hasher.ar(Sweep.ar);
    snd = BPF.ar(snd, 1350, 0.3);
    snd = snd * EnvGen.ar(Env([0, 5, 0.2, 2, 0.2, 3, 0], [0.001, 0.01, 0.001, 0.015, 0.001, 0.05]));
    snd = snd * 5.dbamp;
    snd = snd.clip2;
    snd = Pan2.ar(snd * 3.dbamp, pan) + GVerb.ar(snd * -20.dbamp, 30, 1);
    snd = snd * -5.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.08, 0.2, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_rubber1, { |out=0, amp=1.0, ratio=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(SinOsc.ar(60, 0.3pi).linexp(-1, 1, 600, 3000) * ratio);
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.02, 0.01, curve: -4));
    snd = snd * -15.dbamp;
    snd = Pan2.ar(snd * 3.dbamp, pan) + GVerb.ar(snd * -25.dbamp, 30, 1);
    snd = snd * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_rubber2, { |out=0, amp=1.0, ratio=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(EnvGen.ar(Env.perc(0, 0.1)).linexp(0, 1, 100, 9000) * ratio);
    snd = snd * EnvGen.ar(Env.perc(0.01, 0.1, curve: -4));
    snd = snd * -10.dbamp;
    snd = Pan2.ar(snd * 3.dbamp, pan) + GVerb.ar(snd * -25.dbamp, 30, 1);
    snd = snd * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.6, curve: -4), doneAction: 2);
    OffsetOut.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_ping, { |out=0, freq=440, amp=1.0, pan=0|
    var snd;
    snd = Pluck.ar(PinkNoise.ar + SinOsc.ar(XLine.ar(ExpRand(2000, 4000), 100, 0.003)),
        Impulse.ar(0), 0.01, 1 / (freq + 6), 8.0, 0.2);
    snd = snd + CombC.ar(snd * -8.dbamp, 0.23, 1 / ExpRand(30, 90), 0.1);
    snd = snd + CombC.ar(snd * -8.dbamp, 0.23, 1 / ExpRand(30, 90), 0.1);
    snd = LPF.ar(snd, XLine.ar(6e3, 500, 0.1));
    snd = snd * EnvGen.ar(Env.perc(0.01, 8, curve: -1), doneAction: 2);
    snd = snd * -23.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_sweep, { |out=0, duration=2.3, release=2.0, amp=1.0, pan=0|
    var snd;
    snd = Hasher.ar(Sweep.ar + [0, 1]);
    snd = BPF.ar(snd, XLine.ar(6000, 100, 2.3), 0.3);
    snd = snd * SinOsc.ar(XLine.ar(30, 3, 2.3)).linlin(-1, 1, 0, 1);
    snd = snd * EnvGen.ar(Env.linen(0.05, 2.3, 1.0, curve: -4));
    snd = PitchShift.ar(snd, 0.23, 1.34, 0.001, 0.001) * 15.dbamp;
    snd = snd + GVerb.ar(snd.mean * -10.dbamp, 60, 9);
    snd = HPF.ar(snd, 800);
    snd = snd * -22.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, duration, release, curve: -4), doneAction: 2);
    Out.ar(out, Balance2.ar(snd[0], snd[1], pan));
}).writeDefFile(instDir);

SynthDef(\edm_chipSweep1, { |out=0, duration=0.5, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(XLine.ar(3000, 100, duration));
    snd = snd * -15.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.001, duration, 0.01), doneAction: 2);
    snd = snd * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_chipSweep2, { |out=0, duration=0.5, amp=1.0, pan=0|
    var snd;
    snd = Saw.ar(XLine.ar(1000, 4000, duration));
    snd = snd * -20.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.001, duration, 0.01), doneAction: 2);
    snd = snd * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_chipSweep3, { |out=0, duration=3.0, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(Latch.ar(XLine.ar(3000, 100, duration), Impulse.ar(16)));
    snd = (snd * 3).wrap2;
    snd = snd * -20.dbamp;
    snd = snd * EnvGen.ar(Env.linen(0.001, duration, 0.01), doneAction: 2);
    snd = snd * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_revCymbal, { |out=0, duration=1.0, amp=1.0, pan=0|
    var snd;
    snd = { WhiteNoise.ar } ! 4;
    snd = CombC.ar(snd, 0.1, 1 / [230, 323, 123, 525], 0.5);
    snd = LeakDC.ar(snd);
    snd = FreqShift.ar(snd, [23, 54, 62, 34]);
    snd = snd.sum;
    snd = BPF.ar(snd, (0..5).normalize.linexp(0, 1, 3000, 12000), 0.1);
    snd = snd.sum;
    snd = Pan2.ar(snd, pan) + GVerb.ar(snd, 20, 3);
    snd = LPF.ar(snd, XLine.ar(1000, 16000, duration));
    snd = snd * EnvGen.ar(Env.perc(duration - 0.005, 0.005, curve: 8), doneAction: 2);
    snd = snd * -29.dbamp * amp;
    Out.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_wub1, { |out=0, duration=1.5, freq=200, amp=1.0|
    var snd, auto, f, freqs;
    auto = EnvGen.ar(Env([0, 0.9, 0.7, 1, 0, 0.1, 1, 0.1, 0.9, 0], [1, 1, 1, 1, 3, 1, 1, 1, 3].normalizeSum * duration, \sin));
    f = EnvGen.ar(Env.perc(0, duration, curve: -1)).linexp(0, 1, 60, 200);
    freqs = f * [-0.05, 0, 0.05].midiratio;
    snd = SinOsc.ar(freqs) * auto * 100;
    snd = SinOsc.ar(freqs + snd);
    snd = snd * (1 + (5 * auto.lag(0.3)));
    snd = ((snd * 3).tanh * 4).fold2;
    snd = RLPF.ar([snd], auto.linexp(0, 1, [300, 1230], [2000, 9400]), 0.1).sum;
    snd = snd * (1 + auto);
    snd = snd.tanh;
    snd = LPF.ar(snd, auto.pow(0.9).lag(0.03).linexp(0, 1, 100, 8000));
    snd = snd * 1.dbamp;
    snd = Splay.ar(snd, 0.5);
    snd = snd + CombC.ar(snd, 0.23, 1 / XLine.ar(74, 94, duration), 0.01);
    snd = snd + (SinOsc.ar(f) * -4.dbamp * auto.linlin(0, 1, 0.1, 1));
    snd = snd + DelayC.ar(snd, 0.2, SinOsc.ar(0.5, [0, pi]).linlin(-1, 1, 0, 1) * 2e-3);
    snd = snd * EnvGen.ar(Env.linen(0.2, duration - 0.2, 0.1, curve: -4));
    snd = snd + LPF.ar(GVerb.ar(snd.sum * -10.dbamp * Line.ar(-10.dbamp, 0.dbamp, duration), 50, 3, damping: 0.6), 1500);
    snd = snd * EnvGen.ar(Env.linen(0.0, duration + 3, 0.1, curve: -4), doneAction: 2);
    snd = snd * -15.dbamp * amp;
    Out.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_wub2, { |out=0, duration=1.5, freq=60, amp=1.0|
    var snd, auto, freqs;
    auto = EnvGen.ar(Env([0, 0.05, 0.5, 0.1, 0.2, 0.1, 0.3, 0, 0.1, 0, 0.9], [1, 1, 2, 1, 3, 1, 1, 1, 1, 3].normalizeSum * duration, \sin));
    freqs = freq * [-0.01, 0.01].midiratio;
    snd = SinOsc.ar(freqs, 0.5pi) * auto * 100;
    snd = SinOsc.ar(freqs + snd);
    snd = snd * (1 + (5 * auto));
    snd = LPF.ar(snd, auto.linexp(0, 1, 500, 900));
    snd = snd.tanh + (snd * 3).sin;
    snd = snd * (1 + (auto * 20));
    snd = snd.tanh;
    snd = Splay.ar(snd, 0.9);
    30.do {
        var k = Rand(0.5, 0.9);
        snd = FOS.ar(snd, k * -1, 1.0, k);
    };
    snd = snd + CombC.ar(snd, 0.23, 1 / XLine.ar(74, 94, duration), 0.01);
    snd = LPF.ar(snd, auto.linexp(0, 1, 100, 900)) + HPF.ar(snd * -1.dbamp, 3000);
    snd = (snd * 10.dbamp).tanh;
    snd = BLowShelf.ar(snd, 200, 0.3, 4);
    snd = BHiShelf.ar(snd, 2000, 0.3, 4);
    snd = snd + DelayC.ar(snd * -10.dbamp, 0.2, LFNoise2.ar(0.5 ! 2).linlin(-1, 1, 0, 1) * 2e-3);
    snd = snd + HPF.ar(LPF.ar(GVerb.ar(snd.sum * -20.dbamp, 50, 1, damping: 0.6), 3500), 300);
    snd = snd * EnvGen.ar(Env.linen(0.01, duration - 0.01, 0.01, curve: -4), doneAction: 2);
    snd = snd * -15.dbamp * amp;
    Out.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_wub3, { |out=0, duration=1.5, freq=60, amp=1.0|
    var snd, auto, freqs;
    auto = EnvGen.ar(Env([0, 0.7, 0.1, 0, 0.9, 0.1], [1, 1, 2, 1, 3].normalizeSum * duration, \sin));
    freqs = freq * [-0.05, 0, 0.05].midiratio;
    snd = Pulse.ar(freqs);
    snd = Splay.ar(snd);
    snd = RLPF.ar(snd, auto.linexp(0, 1, 100, 3000), 0.1);
    snd = BLowShelf.ar(snd, 200, 0.3, -3);
    snd = BHiShelf.ar(snd, 2300, 0.3, -3);
    snd = snd * (1 + auto);
    snd = (snd * 10).tanh;
    snd = BPeakEQ.ar(snd, auto.linexp(0, 1, 500, 2000), 0.1, 5);
    snd = BPeakEQ.ar(snd, auto.linexp(0, 1, 100, 3000), 0.1, -5);
    snd = LPF.ar(snd, auto.linexp(0, 1, 100, 3000));
    snd = BLowShelf.ar(snd, 200, 0.3, 5);
    snd = BHiShelf.ar(snd, 2300, 0.3, 3);
    snd = snd + HPF.ar(GVerb.ar(snd.sum * -20.dbamp, 30, 3), 300);
    snd = snd * EnvGen.ar(Env.linen(0.01, duration - 0.01, 0.01, curve: -4), doneAction: 2);
    snd = snd * -10.dbamp * amp;
    Out.ar(out, snd);
}).writeDefFile(instDir);

SynthDef(\edm_tom, { |out=0, freq=180, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(freq * XLine.ar(1.5, 1.0, 0.08));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 1200, 0.3) * EnvGen.ar(Env.perc(0.001, 0.03)) * -8.dbamp);
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.35, curve: -4));
    snd = snd * velocity.linlin(0, 1, 0.4, 1);
    snd = snd.tanh;
    snd = snd * -8.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.35, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\edm_subBass, { |out=0, duration=1.0, freq=55, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar([freq, freq * 1.005]);
    snd = snd.sum * 0.5;
    snd = (snd * 3).tanh;
    snd = LPF.ar(snd, 300);
    snd = snd * EnvGen.ar(Env.linen(0.01, duration, 0.2, curve: -2), doneAction: 2);
    snd = snd * -8.dbamp * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

"All edm synthdefs compiled to: %".format(outputDir).postln;
)
