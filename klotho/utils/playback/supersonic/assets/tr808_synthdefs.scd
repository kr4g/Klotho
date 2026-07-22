// "tr808" kit — the sixteen classic drum machine voices.
// Adapted from Yoshinosuke Horiuchi's SC-808 (2020), released free to the
// SuperCollider community.
// Adaptation notes: gates removed (every voice is a self-freeing one-shot),
// out/velocity/pan args added, levels normalized to amp=1. The original's
// extreme-curve envelopes (e.g. the kick's 30 s nominal decay at curve -225)
// are renormalized to equivalent short ones — curve c over time T becomes
// curve -9.2 over T*9.2/|c| — the same audible shape truncated at -80 dB, so
// releaseTime args are in real (audible) seconds and nodes free promptly.
(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
var instDir = outputDir +/+ "instruments";
outputDir.mkdir;
instDir.mkdir;

// --- drums ---

SynthDef(\tr808_kick, { |out=0, freq=56, releaseTime=1.2, velocity=1.0, amp=1.0, pan=0|
    var env, trienv, fenv, pfenv, snd, sub, punch, limGain;
    env = EnvGen.kr(Env([1, 0], [releaseTime], -9.2), doneAction: 2);
    trienv = EnvGen.kr(Env([0.6, 0], [releaseTime], -9.2));
    fenv = Env([freq * 7, freq * 1.35, freq], [0.05, 0.6], -14).kr;
    pfenv = Env([freq * 7, freq * 1.35, freq], [0.03, 0.6], -10).kr;
    snd = SinOsc.ar(fenv, pi/2) * env;
    sub = LFTri.ar(fenv, pi/2) * trienv * 0.05;
    punch = HPF.ar(SinOsc.ar(pfenv, pi/2) * env * 2, 350);
    snd = (snd + sub + punch) * 2.5;
    // envelope-domain limiting: the compressed body plateau the original got
    // from Limiter.ar(sig, 0.5), without its 10 ms lookahead latency
    limGain = (0.5 / (2.5 * env).max(0.0001)).min(1);
    snd = (snd * limGain).clip2(0.5);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * 1.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_snare, { |out=0, tone=340, snappy=0.3, velocity=1.0, amp=1.0, pan=0|
    var noiseEnv, atkEnv, noise, osc1, osc2, snd;
    noiseEnv = EnvGen.kr(Env.perc(0.001, 0.34, 1, -9.2), doneAction: 2);
    atkEnv = EnvGen.kr(Env.perc(0.001, 0.078, curve: -9.2));
    noise = LPF.ar(HPF.ar(WhiteNoise.ar, 1800), 8850) * noiseEnv * snappy;
    osc1 = SinOsc.ar(tone * 0.556, pi/2) * 0.6;
    osc2 = SinOsc.ar(tone, pi/2) * 0.7;
    snd = ((osc1 + osc2) * atkEnv * snappy.linlin(0, 1, 1.0, 0.6)) + noise;
    snd = HPF.ar(snd, 340);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * 2.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_clap, { |out=0, verb=0.5, velocity=1.0, amp=1.0, pan=0|
    var atkenv, denv, atk, decay, verbenv, tail, snd;
    atkenv = EnvGen.kr(Env([0.5, 1, 0], [0, 0.017], -9.2));
    denv = EnvGen.kr(Env([0, 0, 1, 0], [0.026, 0, 0.35], [0, 0, -9.2]));
    atk = WhiteNoise.ar * atkenv * 1.4;
    decay = WhiteNoise.ar * denv;
    snd = BPF.ar(HPF.ar(atk + decay, 500), 1062, 0.5) * 1.5;
    verbenv = EnvGen.kr(Env.perc(0.02, 1.5, curve: -6), doneAction: 2);
    tail = LPF.ar(HPF.ar(WhiteNoise.ar, 500), 1000) * verbenv * (verb * 0.04);
    snd = snd + tail;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * 1.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_rim, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var env, tri1, tri2, punch, snd;
    env = EnvGen.kr(Env([1, 1, 0], [0.00272, 0.07], -42), doneAction: 2);
    tri1 = LFTri.ar(1667 * 1.1, 1) * env;
    tri2 = LFPulse.ar(455 * 1.1, width: 0.8) * env;
    punch = WhiteNoise.ar * env * 0.46;
    snd = tri1 + tri2 + punch;
    snd = BPeakEQ.ar(snd, 464, 0.44, 8);
    snd = LPF.ar(HPF.ar(snd, 315), 7300);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -10.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- toms & congas (one voice, six tunings; see SynthDefKit.tr808) ---

SynthDef(\tr808_tom, { |out=0, freq=80, releaseTime=0.74, sweep1=1.25, sweep2=1.125, velocity=1.0, amp=1.0, pan=0|
    var env, fenv, snd;
    env = EnvGen.kr(Env([1, 0], [releaseTime], -9.2), doneAction: 2);
    fenv = Env([freq * sweep1, freq * sweep2, freq], [0.1, 0.5], -4).kr;
    snd = SinOsc.ar(fenv, pi/2) * env;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -3.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- small percussion ---

SynthDef(\tr808_clave, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var env, snd;
    env = EnvGen.kr(Env([1, 1, 0], [0, 0.1], -20), doneAction: 2);
    snd = SinOsc.ar(2500, pi/2) * env;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -7.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_maracas, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var env, snd;
    env = EnvGen.kr(Env([0.3, 1, 0], [0.027, 0.07], -250), doneAction: 2);
    snd = HPF.ar(WhiteNoise.ar, 5500) * env;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -9.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_cowbell, { |out=0, velocity=1.0, amp=1.0, pan=0|
    var atkenv, env, pul1, pul2, atk, datk, snd;
    atkenv = EnvGen.kr(Env.perc(0, 0.043, 1, -9.2));
    env = EnvGen.kr(Env.perc(0.01, 0.97, 1, -9.2), doneAction: 2);
    pul1 = LFPulse.ar(811.16);
    pul2 = LFPulse.ar(538.75);
    atk = (pul1 + pul2) * atkenv * 6;
    datk = (pul1 + pul2) * env;
    snd = atk + datk;
    snd = LPF.ar(HPF.ar(snd, 250), 4500);
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -23.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- metallic bank (hats and cymbal share the 6-pulse-oscillator recipe) ---

SynthDef(\tr808_hat, { |out=0, releaseTime=0.42, velocity=1.0, amp=1.0, pan=0|
    var env, oscs, sighi, siglow, snd;
    env = EnvGen.kr(Env.perc(0.005, releaseTime, 1, -30), doneAction: 2);
    oscs = LFPulse.ar([203.52, 366.31, 301.77, 518.19, 811.16, 538.75]).sum;
    sighi = HPF.ar(BPF.ar(oscs, 8900, 1), 9000);
    siglow = BHiPass.ar(BBandPass.ar(oscs, 8900, 0.8), 9000, 0.3);
    snd = BPeakEQ.ar(sighi + siglow, 9700, 0.8, 0.7);
    snd = snd * env;
    snd = snd * velocity.linlin(0, 1, 0.5, 1);
    snd = snd * -9.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_hatOpen, { |out=0, releaseTime=0.5, velocity=1.0, amp=1.0, pan=0|
    var env1, env2, oscs, snd, siga, sigb, sum;
    env1 = EnvGen.kr(Env.perc(0.1, releaseTime, curve: -3), doneAction: 2);
    env2 = EnvGen.kr(Env([0, 1, 0], [0, releaseTime * 5], -150));
    oscs = (LFPulse.ar([203.52, 366.31, 301.77, 518.19, 811.16, 538.75]) * 0.6).sum;
    snd = BLowShelf.ar(oscs, 990, 2, -3);
    snd = BPF.ar(snd, 7700);
    snd = BPeakEQ.ar(snd, 7200, 0.5, 5);
    snd = BHiPass4.ar(snd, 8100, 0.7);
    snd = BHiShelf.ar(snd, 9400, 1, 5);
    siga = snd * env1 * 0.6;
    sigb = snd * env2;
    sum = LPF.ar(siga + sigb, 4000);
    sum = sum * velocity.linlin(0, 1, 0.5, 1);
    sum = sum * 13.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(sum, pan));
}).writeDefFile(instDir);

SynthDef(\tr808_cymbal, { |out=0, releaseTime=2, tone=0.5, velocity=1.0, amp=1.0, pan=0|
    var toneAmt, env1, env2, env2b, env3, oscs, sig1, sig2, sig2a, sig2b, sig3, sum;
    toneAmt = tone.linexp(0, 1, 0.0002, 0.02);  // 0..1 knob -> low-band level (0.5 = original default)
    env1 = EnvGen.kr(Env.perc(0.3, releaseTime, curve: -3), doneAction: 2);
    env2 = EnvGen.kr(Env([0, 0.6, 0], [0.1, releaseTime * 0.7], -5));
    env2b = EnvGen.kr(Env([0, 0.3, 0], [0.1, releaseTime * 20], -120));
    env3 = EnvGen.kr(Env([0, 1, 0], [0, releaseTime * 5], -150));
    oscs = (LFPulse.ar([203.52, 366.31, 301.77, 518.19, 811.16, 538.75]) * 0.6).sum;
    sig1 = BLowShelf.ar(oscs, 2000, 1, 5);
    sig1 = BPF.ar(sig1, 3000);
    sig1 = BPeakEQ.ar(sig1, 2400, 0.5, 5);
    sig1 = BHiPass.ar(sig1, 1550, 0.7);
    sig1 = LPF.ar(sig1, 3000);
    sig1 = BLowShelf.ar(sig1, 1000, 1, 0);
    sig1 = sig1 * env1 * toneAmt;
    sig2 = BLowShelf.ar(oscs, 990, 2, -5);
    sig2 = BPF.ar(sig2, 7400);
    sig2 = BPeakEQ.ar(sig2, 7200, 0.5, 5);
    sig2 = BHiPass4.ar(sig2, 6800, 0.7);
    sig2 = BHiShelf.ar(sig2, 10000, 1, -4);
    sig2a = sig2 * env2 * 0.3;
    sig2b = sig2 * env2b * 0.6;
    sig3 = BLowShelf.ar(oscs, 990, 2, -15);
    sig3 = BPF.ar(sig3, 6500);
    sig3 = BPeakEQ.ar(sig3, 7400, 0.35, 10);
    sig3 = BHiPass4.ar(sig3, 10500, 0.8) * 2;
    sig3 = sig3 * env3;
    sum = sig1 + sig2a + sig2b + sig3;
    sum = LPF.ar(sum, 4000);
    sum = sum * velocity.linlin(0, 1, 0.5, 1);
    sum = sum * 17.dbamp * amp;
    OffsetOut.ar(out, Pan2.ar(sum, pan));
}).writeDefFile(instDir);

"tr808 synthdefs compiled to: %".format(instDir).postln;
)
