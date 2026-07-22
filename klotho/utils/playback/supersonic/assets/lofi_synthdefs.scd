// MAT 111MC "lofi" kit — dusty percussion, tape glitches, pads, and tape FX.
// Adapted from Nathan Ho's 2023-10-13-tape.scd, 2023-12-01-rimshot.scd, and
// 2024-03-23-pads.scd, used with permission — nathanho.bandcamp.com
//
// Shared idiom: the "lofi room" — a quiet band-limited slapback tail:
//   snd + LPF(HPF(DelayC(snd * -27dB, [44ms, 23ms]), 200), 3000).sum
// The glitch family derives every internal value from a deterministic
// Hasher chain seeded by the `seed` control (same seed = same glitch).
(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
var instDir = outputDir +/+ "instruments";
var fxDir = outputDir +/+ "effects";
outputDir.mkdir;
instDir.mkdir;
fxDir.mkdir;

// --- percussion (self-freeing one-shots) ---

SynthDef(\lofi_dustKick, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, pitch;
    pitch = XLine.ar(200, 60, 0.05) * XLine.ar(10, 1, 0.001) * XLine.ar(1, 0.5, 0.3);
    snd = SinOsc.ar(pitch);
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 3310, 0.3) * EnvGen.ar(Env.perc(0.0, 0.01)));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.7));
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -7.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -4.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.3, 0.5, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_snare, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(XLine.ar(240, 220, 0.05) * XLine.ar(2, 1, 0.001));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.03));
    snd = snd + (EnvGen.ar(Env.perc(0.001, 0.02)) * SinOsc.ar(XLine.ar(8000, 100, 0.01)) * -12.dbamp);
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 510, 0.3) * EnvGen.ar(Env.perc(0.002, 0.01)));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar + 1), 2810 * XLine.ar(1, 1.3, 0.1), 0.3) * EnvGen.ar(Env.perc(0.02, 0.04)));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar + 2), 1310 * XLine.ar(1, 0.9, 0.1), 0.3) * EnvGen.ar(Env([0, 0, 1, 0], [0.01, 0.003, 0.0245])));
    snd = snd * (1 + (0.3 * EnvGen.ar(Env.perc(0.0, 0.1))));
    snd = snd.tanh;
    snd = snd + PitchShift.ar(snd * -5.dbamp, 0.023, 1.3);
    snd = snd + PitchShift.ar(snd * -5.dbamp, 0.013, 1.3);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -10.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.15, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_ghostSnare, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(XLine.ar(240, 220, 0.05) * XLine.ar(2, 1, 0.001));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.03));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 510, 0.3) * EnvGen.ar(Env.perc(0.002, 0.01)));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar + 1), 2810 * XLine.ar(1, 1.3, 0.1), 0.3) * EnvGen.ar(Env.perc(0.02, 0.04)));
    snd = snd * (1 + (0.3 * EnvGen.ar(Env.perc(0.0, 0.1))));
    snd = snd.tanh;
    snd = snd * XLine.ar(0.01, 1, 0.01);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -14.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.25, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_rim, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd;
    snd = SinOsc.ar(3220 * [0.8, 1.03, 2.02, 3.23, 4.45] * XLine.ar(1.1, 1, 0.003));
    snd = snd * EnvGen.ar(Env.perc(0.001, [0.0223, 0.01, 0.0045, 0.001, 0.034] * 0.5));
    snd = snd * [-5, 0, -5, -10, -15].dbamp;
    snd = snd * ({ Rand(0.5, 1) } ! 5);
    snd = snd.sum;
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 3310, 0.3) * EnvGen.ar(Env.perc(0.002, 0.02)) * 5.dbamp);
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -21.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * 2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.2, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_hushHat, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(20 * [1, 2.23, 3.45, 5.7, 7.8]).sum;
    snd = FreqShift.ar(snd, 41.2);
    snd = snd + (Hasher.ar(Sweep.ar) * -8.dbamp);
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.07));
    snd = BPF.ar(snd, [8923, 8923 * 1.5] * XLine.ar(1, 1.3, 0.1), 0.3).sum;
    snd = HPF.ar(snd, 6000);
    snd = snd * -9.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.0, 0.12, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_hushHatOpen, { |out=0, amp=1.0, pan=0|
    var snd;
    snd = Pulse.ar(32 * [1, 2.23, 3.45, 5.7, 7.8]).sum;
    snd = FreqShift.ar(snd, 51.2);
    snd = snd + (Hasher.ar(Sweep.ar) * -8.dbamp);
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.3));
    snd = BPF.ar(snd, 10923 * [1, 1.5, 1.8] * XLine.ar(1, 1.2, 0.1), 0.1).sum;
    snd = HPF.ar(snd, 9000);
    snd = snd * -10.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.4, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- tape/analog pops (self-freeing one-shots) ---

SynthDef(\lofi_tapePop, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, thump, click;
    thump = SinOsc.ar(XLine.ar(130, 42, 0.04));
    thump = thump * EnvGen.ar(Env.perc(0.001, 0.09, curve: -6));
    click = LPF.ar(Hasher.ar(Sweep.ar), 1300) * EnvGen.ar(Env.perc(0.0005, 0.009));
    snd = thump + (click * -8.dbamp);
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -10.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.2, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_tapeTick, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, tick, tock, knock;
    tick = LPF.ar(HPF.ar(Hasher.ar(Sweep.ar), 400), 1900) * EnvGen.ar(Env.perc(0.0003, 0.007));
    tock = LPF.ar(HPF.ar(Hasher.ar(Sweep.ar + 1), 250), 1100) * EnvGen.ar(Env([0, 0, 1, 0], [0.019, 0.0004, 0.005]));
    knock = SinOsc.ar(XLine.ar(240, 190, 0.02)) * EnvGen.ar(Env.perc(0.0005, 0.02)) * -8.dbamp;
    snd = tick + (tock * -5.dbamp) + knock;
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.4, 1);
    snd = snd * -11.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.03, 0.12, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_tapeSnap, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, crack, body, knock;
    crack = HPF.ar(Hasher.ar(Sweep.ar), 1500) * EnvGen.ar(Env.perc(0.0002, 0.004));
    body = BPF.ar(Hasher.ar(Sweep.ar + 1), 1250 * XLine.ar(1.3, 1.0, 0.03), 0.7) * EnvGen.ar(Env.perc(0.001, 0.05));
    knock = SinOsc.ar(XLine.ar(330, 200, 0.025)) * EnvGen.ar(Env.perc(0.0005, 0.045)) * -4.dbamp;
    snd = (crack * -3.dbamp) + body + knock;
    snd = LPF.ar(snd, 6200);
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.4, 1);
    snd = snd * -10.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.05, 0.18, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_dustCrackle, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var snd, ticks;
    ticks = Decay2.ar(Dust.ar(XLine.kr(110, 6, 0.5)), 0.0004, 0.008);
    snd = ticks * Hasher.ar(Sweep.ar);
    snd = LPF.ar(HPF.ar(snd, 350), 6300);
    snd = snd * EnvGen.ar(Env.perc(0.01, 0.5, curve: -3));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -11.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.3, 0.35, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- deterministic glitches: every value hashes off `seed` ---

SynthDef(\lofi_glitchZap, { |out=0, seed=0, velocity=1.0, amp=1.0, pan=0, toneLPF=4500|
    var h, r1, r2, r3, r4, r5, r6, r7, snd;
    h = Hasher.kr(seed + 1234); r1 = h;
    h = Hasher.kr(h + 534); r2 = h;
    h = Hasher.kr(h + 7575); r3 = h;
    h = Hasher.kr(h + 7535); r4 = h;
    h = Hasher.kr(h + 12534); r5 = h;
    h = Hasher.kr(h + 5533); r6 = h;
    h = Hasher.kr(h + 55333); r7 = h;
    snd = SinOsc.ar(r1.linexp(-1, 1, 400, 5000)) * 600;
    snd = SinOsc.ar(snd + r2.linexp(-1, 1, 150, 1800));
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.09));
    snd = RLPF.ar(snd, XLine.ar(r3.linexp(-1, 1, 200, 1600), r4.linexp(-1, 1, 200, 2400), 0.05), 0.3) * -2.dbamp;
    snd = snd * (1 + (SinOsc.ar(r5.linexp(-1, 1, 500, 4000)) * 0.5));
    snd = snd.tanh;
    snd = Latch.ar(snd, Impulse.ar(r6.linexp(0, 1, 2500, 8000)));
    snd = HPF.ar(snd, r7.linexp(0, 1, 250, 1200));
    snd = LPF.ar(snd, toneLPF.clip(500, 10000));
    snd = snd * EnvGen.ar(Env.linen(0.005, 0.06, 0.03, curve: -4));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -13.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.1, 0.15, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_glitchBlip, { |out=0, seed=0, duration=0.08, velocity=1.0, amp=1.0, pan=0, toneLPF=3800|
    var h, r1, r2, r3, r4, r5, snd;
    h = Hasher.kr(seed); r1 = h;
    h = Hasher.kr(h); r2 = h;
    h = Hasher.kr(h); r3 = h;
    h = Hasher.kr(h); r4 = h;
    h = Hasher.kr(h); r5 = h;
    snd = SinOsc.ar(r1.linexp(-1, 1, 80, 3500)) * 2000
        * EnvGen.ar(Env.perc(0.01, r2.linexp(-1, 1, 0.05, 0.4))).linexp(-1, 1, 0.03, 0.3);
    snd = SinOsc.ar(r3.linexp(-1, 1, 80, 3500) + snd) * 4000
        * EnvGen.ar(Env.perc(0.01, r4.linexp(-1, 1, 0.05, 0.4))).linexp(-1, 1, 0.03, 0.3);
    snd = SinOsc.ar(r5.linexp(-1, 1, 300, 1600) + snd);
    snd = LPF.ar(snd, toneLPF.clip(500, 10000));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -12.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.001, duration, 0.06), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_glitchBurst, { |out=0, seed=0, velocity=1.0, amp=1.0, pan=0, toneLPF=4200|
    var h, snd, fbase, fmEnv, voices;
    var rFmAmt, rFmRel, rSemis, rAtk, rRel, rCurve, rBoostRel, rBoostAmt;
    var rDrive, rVerbSend, rRoom, rDamp, rPsWin, rPsRatio, rEndRel;
    h = Hasher.kr(seed); fbase = h.linexp(-1, 1, 30, 1000);
    h = Hasher.kr(h); rFmAmt = h.linlin(-1, 1, 0, 10);
    h = Hasher.kr(h); rFmRel = h.linlin(-1, 1, 0.001, 0.05);
    fmEnv = 1 + (rFmAmt * EnvGen.ar(Env.perc(0.0, rFmRel)));
    voices = [0, -10, -20].collect { |gain|
        h = Hasher.kr(h);
        SinOsc.ar(fbase * h.linlin(-1, 1, 0, 12).midiratio * fmEnv) * gain.dbamp;
    };
    snd = voices.sum;
    h = Hasher.kr(h); rAtk = h.linexp(-1, 1, 1e-4, 1e-2);
    h = Hasher.kr(h); rRel = h.linexp(-1, 1, 0.03, 0.5);
    h = Hasher.kr(h); rCurve = h.linlin(-1, 1, 1, -4);
    snd = snd * EnvGen.ar(Env.perc(rAtk, rRel, curve: rCurve));
    h = Hasher.kr(h); rBoostRel = h.linexp(-1, 1, 0.003, 0.01);
    h = Hasher.kr(h); rBoostAmt = h.linlin(-1, 1, 0, 5);
    snd = snd * (1 + (EnvGen.ar(Env.perc(0.0, rBoostRel)) * rBoostAmt));
    h = Hasher.kr(h); rDrive = h.linlin(-1, 1, 10, -8).dbamp;
    snd = (snd * rDrive).tanh;
    snd = LPF.ar(snd, toneLPF.clip(500, 10000));
    h = Hasher.kr(h); rVerbSend = h.linlin(-1, 1, -15, -30).dbamp;
    h = Hasher.kr(h); rRoom = h.linlin(-1, 1, 0.3, 0.95);
    h = Hasher.kr(h); rDamp = h.linlin(-1, 1, 0.5, 0.9);
    snd = snd + FreeVerb.ar(snd * rVerbSend, 1.0, rRoom, rDamp);
    h = Hasher.kr(h); rPsWin = h.linexp(-1, 1, 0.002, 0.05);
    h = Hasher.kr(h); rPsRatio = h.linexp(-1, 1, 0.5, 2);
    snd = snd + PitchShift.ar(snd * 3.dbamp, rPsWin, rPsRatio);
    snd = LPF.ar(snd, 5500);
    h = Hasher.kr(h); rEndRel = h.linexp(-1, 1, 0.25, 0.7);
    snd = snd * EnvGen.ar(Env.perc(0.0, rEndRel));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -14.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.6, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- pads (gated) ---

SynthDef(\lofi_hazePad, { |out=0, freq=440, amp=1.0, gate=1, pan=0, portamento=0.1,
    vibRate=5, vibDepth=0, detune=0.07, tone=2.5, wow=0.3,
    attackTime=1.5, decayTime=1.0, sustainLevel=0.8, releaseTime=2.5, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    f = f * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    f = f * (LFNoise2.kr(0.12) * (0.04 * wow)).midiratio;
    snd = LFTri.ar([f * detune.midiratio, f * (detune * -1).midiratio]).sum * 0.5;
    snd = snd + (SinOsc.ar(f) * -7.dbamp);
    snd = HPF.ar(snd, 85);
    snd = LPF.ar(snd, (f * tone).clip(300, 4500));
    snd = snd * -8.dbamp;
    snd = snd * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_driftPad, { |out=0, freq=440, amp=1.0, gate=1, pan=0, portamento=0.1,
    vibRate=5, vibDepth=0, drift=0.5, tone=3.0,
    attackTime=2.0, decayTime=1.0, sustainLevel=0.75, releaseTime=3.0, peakLevel=1.0,
    attackCurve=0.0, decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    f = f * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    snd = SinOsc.ar(f * [0.5, 1.0, 1.5, 2.0, 3.0]
            * (LFNoise2.kr([0.11, 0.127, 0.144, 0.161, 0.178]) * (0.08 * drift)).midiratio)
        * [-9, 0, -14, -7, -19].dbamp
        * LFNoise2.kr([0.07, 0.083, 0.096, 0.109, 0.122]).linlin(-1, 1, 0.35, 1.0);
    snd = snd.sum;
    snd = LPF.ar(snd, (f * tone).clip(200, 6000));
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), (f * 4).clip(400, 8000), 0.3) * -34.dbamp);
    snd = snd * -11.dbamp;
    snd = snd * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- leads (gated) ---

SynthDef(\lofi_lead, { |out=0, freq=440, amp=1.0, gate=1, pan=0, portamento=0.06,
    vibRate=4.5, vibDepth=0.15, vibDelay=0.6, tone=3.5, drive=1.6,
    attackTime=0.03, decayTime=0.15, sustainLevel=0.85, releaseTime=0.6, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f, vibAmt, d;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    vibAmt = vibDepth * Line.kr(0, 1, vibDelay.max(0.01));
    f = f * (SinOsc.kr(vibRate) * vibAmt).midiratio;
    snd = LFTri.ar(f) + (SinOsc.ar(f) * -4.dbamp) + (SinOsc.ar(f * 2) * -16.dbamp);
    snd = LPF.ar(snd, (f * tone).clip(300, 6500));
    d = drive.clip(1.0, 8.0);
    snd = (snd * d).tanh * d.sqrt.reciprocal;
    snd = snd * -12.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_glassLead, { |out=0, freq=440, amp=1.0, gate=1, pan=0, portamento=0.05,
    vibRate=5, vibDepth=0, shimmer=0.4, tone=4.0,
    attackTime=0.01, decayTime=0.4, sustainLevel=0.6, releaseTime=0.9, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-3), releaseCurve=(-4)|
    var snd, env, f, index, mod;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    f = f * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    index = shimmer * 3 * EnvGen.kr(Env.perc(0.002, 1.2, curve: -4));
    mod = SinOsc.ar(f * 2.001) * index;
    snd = SinOsc.ar(f, mod);
    snd = snd + (SinOsc.ar(f * 1.004, mod * 0.7) * -7.dbamp);
    snd = LPF.ar(snd, (f * tone).clip(300, 7500));
    snd = snd * -12.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- basses (gated) ---

SynthDef(\lofi_subBass, { |out=0, freq=110, amp=1.0, gate=1, pan=0, portamento=0.08,
    vibRate=5, vibDepth=0, harm=0.25, drive=1.3,
    attackTime=0.02, decayTime=0.1, sustainLevel=0.9, releaseTime=0.3, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    f = f * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    snd = SinOsc.ar(f) + (SinOsc.ar(f * 2) * harm);
    snd = (snd * drive.clip(1.0, 8.0)).tanh;
    snd = LPF.ar(snd, (f * 4).clip(80, 1200));
    snd = snd * -8.dbamp;
    snd = snd * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_tapeBass, { |out=0, freq=110, amp=1.0, gate=1, pan=0, portamento=0.08,
    vibRate=5, vibDepth=0, width=0.4, tone=2.8, wow=0.5,
    attackTime=0.01, decayTime=0.12, sustainLevel=0.75, releaseTime=0.25, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f, cutoff;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    f = f * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    snd = Pulse.ar(f, width.clip(0.1, 0.9)) * -2.dbamp;
    snd = snd + LFTri.ar(f);
    snd = snd + (SinOsc.ar(f * 0.5) * -10.dbamp);
    cutoff = (f * tone * ((LFNoise2.kr(0.4) * 0.3 * wow) + 1)).clip(100, 3000);
    snd = LPF.ar(snd, cutoff);
    snd = (snd * 1.5).tanh;
    snd = LeakDC.ar(snd);
    snd = snd * -9.dbamp;
    snd = snd * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- plucks / beeps (self-freeing, pitched) ---

SynthDef(\lofi_beep, { |out=0, freq=880, velocity=1.0, amp=1.0, pan=0, releaseTime=0.35|
    var snd;
    snd = SinOsc.ar([freq, freq * 1.004]).sum * 0.5;
    snd = snd + (SinOsc.ar(freq * 2) * -24.dbamp);
    snd = LPF.ar(snd, (freq * 4).clip(400, 7000));
    snd = snd * EnvGen.ar(Env([0, 1, 0.65, 0], [0.004, 0.05, releaseTime], [-4, -2, -4]));
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -14.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, releaseTime, 0.2, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_dustPluck, { |out=0, freq=440, velocity=1.0, amp=1.0, pan=0, releaseTime=0.5,
    vibRate=5, vibDepth=0|
    var snd, damp, f;
    f = freq * (SinOsc.kr(vibRate) * vibDepth).midiratio;
    snd = LFTri.ar(f) + (Pulse.ar(f * 1.002, 0.3) * -7.dbamp);
    snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), (freq * 2).clip(200, 6000), 0.5)
        * EnvGen.ar(Env.perc(0.0005, 0.015)) * -10.dbamp);
    damp = EnvGen.ar(Env.perc(0.001, releaseTime * 0.6, curve: -5));
    snd = LPF.ar(snd, (freq * (1.2 + (damp * 5))).clip(150, 8000));
    snd = snd * EnvGen.ar(Env.perc(0.002, releaseTime, curve: -4));
    snd = snd.tanh;
    snd = snd * velocity.linlin(0, 1, 0.45, 1);
    snd = snd * -13.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, releaseTime, 0.25, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- risers / sweeps (duration-driven) ---

SynthDef(\lofi_wash, { |out=0, freq=440, duration=2.0, amp=1.0, pan=0|
    var snd, sweepFreq;
    sweepFreq = XLine.ar(freq * 0.25, freq * 4, duration);
    snd = BPF.ar(Hasher.ar(Sweep.ar), sweepFreq, 0.2);
    snd = snd + (CombC.ar(snd * -3.dbamp, 0.1, 1.0 / freq, duration) * -3.dbamp);
    snd = (snd * 9.dbamp).tanh;
    snd = snd + DelayC.ar(snd, 0.2, SinOsc.ar(0.3).linlin(-1, 1, 0, 1) * 1e-3);
    snd = snd + FreeVerb.ar(snd * -9.dbamp, 0.6, 0.9, 0.4);
    snd = snd * EnvGen.ar(Env([0, 1, 0], [duration * 0.75, duration * 0.25], [3, -4]), doneAction: 2);
    snd = snd * -16.dbamp * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_cresc, { |out=0, duration=3.0, freq=1320, amp=1.0, pan=0|
    var snd, env;
    env = EnvGen.ar(Env([0, 1, 0], [duration - 0.02, 0.02], [8, -4]), doneAction: 2);
    snd = PinkNoise.ar;
    snd = BPF.ar(snd, freq, 0.3);
    snd = snd * (1 + SinOsc.ar(30)) * 10.dbamp;
    snd = CombC.ar(snd, 0.2, 1.0 / XLine.ar(90, 30, duration), 2.0);
    snd = snd + PitchShift.ar(snd, 0.3, 1.2 + env);
    snd = snd * -14.dbamp * amp;
    snd = snd * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_tapeRise, { |out=0, freq=330, duration=2.0, amp=1.0, pan=0|
    var snd, lift, air, hum, crackle;
    lift = EnvGen.ar(Env([0, 1, 0], [duration * 0.96, duration * 0.04], [5, -4]), doneAction: 2);
    air = LPF.ar(HPF.ar(Hasher.ar(Sweep.ar), 200), 4800);
    air = air * (1 + (LFNoise2.kr(XLine.kr(6, 24, duration)) * 0.5));
    hum = CombC.ar(air * -8.dbamp, 0.03, 1.0 / freq.clip(40, 2000), 0.4);
    crackle = Decay2.ar(Dust.ar(XLine.kr(3, 60, duration)), 0.0005, 0.01) * Hasher.ar(Sweep.ar + 1);
    snd = (air * -6.dbamp) + (hum * -2.dbamp) + (crackle * -12.dbamp);
    snd = LPF.ar(snd, 600 + (lift * 4400));
    snd = snd + FreeVerb.ar(snd * -9.dbamp, 0.6, 0.85, 0.5);
    snd = snd * lift * -13.dbamp * amp;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\lofi_tapeCrash, { |out=0, freq=220, duration=2.0, amp=1.0, pan=0|
    var snd, thump, splash, hum;
    thump = SinOsc.ar(XLine.ar(90, 55, 0.06)) * EnvGen.ar(Env.perc(0.001, 0.25));
    splash = LPF.ar(HPF.ar(Hasher.ar(Sweep.ar), 250), 4200);
    splash = splash * (1 + (LFNoise2.kr(7) * 0.4));
    splash = splash * EnvGen.ar(Env.perc(0.002, duration * 0.85, curve: -4));
    hum = CombC.ar(splash * -10.dbamp, 0.03, 1.0 / freq.clip(40, 2000), duration * 0.6);
    snd = thump + (splash * -6.dbamp) + (hum * -4.dbamp);
    snd = (snd * 4.dbamp).tanh;
    snd = LPF.ar(snd, 500 + (EnvGen.ar(Env.perc(0.001, duration, curve: -3)) * 4000));
    snd = snd * -13.dbamp;
    snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -27.dbamp, 0.1, [0.044, 0.023]), 200), 3000).sum;
    snd = snd * -2.dbamp * amp;
    snd = snd * EnvGen.ar(Env([0, 1, 1, 0], [0.002, duration * 0.8, duration * 0.2], [-2, 0, -4]), doneAction: 2);
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- lo-fi tape FX (stereo inserts: In -> process -> ReplaceOut) ---

SynthDef(\lofi_tape, { |inBus=0, outBus=0, drive=1.5, bias=0.1,
    wowRate=0.4, wowDepth=1.2, flutterRate=6.0, flutterDepth=0.12,
    stereoDrift=0.15, lowCut=35, highCut=5500,
    bumpFreq=85, bumpDb=2.5, hiss=0.0012, hissFollow=0.4,
    wear=0.0, mix=1.0, gain=1.0|
    var dry, snd, d, m, base, wow, flut, shared, driftAmt, hc, w, trig, ev, level, hs, bed, dryAligned;
    dry = In.ar(inBus, 2);
    d = Lag.kr(drive, 0.1).clip(0.5, 8.0);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    base = 0.012;
    snd = ((dry * d) + bias.clip(0.0, 0.3)).tanh * d.sqrt.reciprocal;
    snd = LeakDC.ar(snd);
    wow = ((SinOsc.kr(wowRate) * 0.6) + (LFNoise2.kr(wowRate * 1.7) * 0.4)) * (wowDepth * 1e-3);
    flut = ((SinOsc.kr(flutterRate * ((LFNoise2.kr(0.4) * 0.12) + 1)) * 0.5)
        + (LFNoise2.kr(flutterRate * 2.0) * 0.5)) * (flutterDepth * 1e-3);
    shared = wow + flut;
    driftAmt = (wowDepth * 1e-3) * stereoDrift.clip(0.0, 1.0);
    snd = DelayC.ar(snd, 0.035, [
        (base + shared + (LFNoise2.kr(0.30) * driftAmt)).clip(0.0005, 0.03),
        (base + shared + (LFNoise2.kr(0.33) * driftAmt)).clip(0.0005, 0.03)
    ]);
    hc = highCut.clip(500, 16000);
    snd = HPF.ar(snd, lowCut.clip(15, 400));
    snd = LPF.ar(snd, hc);
    snd = BPeakEQ.ar(snd, bumpFreq.clip(40, 200), 1.0, bumpDb);
    w = wear.clip(0.0, 1.0);
    trig = Dust.kr(w * 1.2);
    ev = EnvGen.kr(Env.perc(0.06, 0.25, curve: -2), trig);
    ev = ev * TRand.kr(0.3, 1.0, trig) * w;
    snd = snd * (1 - (ev * 0.75));
    snd = LPF.ar(snd, (hc * (1 - (ev * 0.8))).max(400));
    level = Amplitude.kr(dry.sum * 0.5, 0.05, 0.3);
    hs = hiss.max(0.0) * (1 + (level * hissFollow * 4));
    bed = LPF.ar(HPF.ar({ (PinkNoise.ar * 0.7) + (WhiteNoise.ar * 0.3) } ! 2, 250), 7500);
    snd = snd + (bed * hs);
    dryAligned = DelayN.ar(dry, 0.02, base);
    snd = XFade2.ar(dryAligned, snd, (m * 2) - 1);
    snd = LeakDC.ar(snd);
    snd = snd * Lag.kr(gain, 0.1);
    ReplaceOut.ar(outBus, snd);
}).writeDefFile(fxDir);

SynthDef(\lofi_wowFlutter, { |inBus=0, outBus=0, wowRate=0.35, wowDepth=2.0,
    flutterRate=7.0, flutterDepth=0.15, stereoDrift=0.2, tone=6500, mix=1.0, gain=1.0|
    var sig, wet, snd, m, base, wow, flut, shared, driftAmt, dryAligned;
    sig = In.ar(inBus, 2);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    base = 0.012;
    wow = ((SinOsc.kr(wowRate) * 0.6) + (LFNoise2.kr(wowRate * 1.7) * 0.4)) * (wowDepth * 1e-3);
    flut = ((SinOsc.kr(flutterRate * ((LFNoise2.kr(0.4) * 0.12) + 1)) * 0.5)
        + (LFNoise2.kr(flutterRate * 2.0) * 0.5)) * (flutterDepth * 1e-3);
    shared = wow + flut;
    driftAmt = (wowDepth * 1e-3) * stereoDrift.clip(0.0, 1.0);
    wet = DelayC.ar(sig, 0.035, [
        (base + shared + (LFNoise2.kr(0.30) * driftAmt)).clip(0.0005, 0.03),
        (base + shared + (LFNoise2.kr(0.33) * driftAmt)).clip(0.0005, 0.03)
    ]);
    wet = LPF.ar(wet, tone.clip(500, 16000));
    dryAligned = DelayN.ar(sig, 0.02, base);
    snd = XFade2.ar(dryAligned, wet, (m * 2) - 1);
    snd = snd * Lag.kr(gain, 0.1);
    ReplaceOut.ar(outBus, snd);
}).writeDefFile(fxDir);

SynthDef(\lofi_tapeSat, { |inBus=0, outBus=0, drive=2.0, bias=0.1, tone=7500, lowCut=30, mix=1.0, gain=1.0|
    var sig, wet, snd, d, m;
    sig = In.ar(inBus, 2);
    d = Lag.kr(drive, 0.1).clip(0.5, 12.0);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    wet = ((sig * d) + bias.clip(0.0, 0.3)).tanh * d.sqrt.reciprocal;
    wet = LeakDC.ar(wet);
    wet = LPF.ar(wet, tone.clip(500, 16000));
    wet = HPF.ar(wet, lowCut.clip(15, 400));
    snd = XFade2.ar(sig, wet, (m * 2) - 1);
    snd = snd * Lag.kr(gain, 0.1);
    ReplaceOut.ar(outBus, snd);
}).writeDefFile(fxDir);

SynthDef(\lofi_hissDust, { |inBus=0, outBus=0, hiss=0.0015, hissLPF=7000, crackle=1.5, crackleAmp=0.006, mix=1.0, gain=1.0|
    var sig, snd, m, bed, ticks;
    sig = In.ar(inBus, 2);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    bed = HPF.ar({ (PinkNoise.ar * 0.7) + (WhiteNoise.ar * 0.3) } ! 2, 220);
    bed = LPF.ar(bed, hissLPF.clip(1000, 16000));
    ticks = Decay2.ar(Dust.ar([crackle, crackle]), 0.0004, 0.009);
    ticks = LPF.ar(ticks * Hasher.ar(Sweep.ar), 6000);
    snd = sig + (((bed * hiss.max(0.0)) + (ticks * crackleAmp.max(0.0))) * m);
    snd = snd * Lag.kr(gain, 0.1);
    ReplaceOut.ar(outBus, snd);
}).writeDefFile(fxDir);

"All lofi synthdefs compiled to: %".format(outputDir).postln;
)
