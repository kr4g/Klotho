// MAT 111MC "chip" kit — console-era voices, accents, percussion, and insert FX.
// Adapted from Nathan Ho's chiptune studies (2022-12-31-chiptune.scd,
// 2023-09-22-chip.scd, 2025-08-28-chipbreak.scd, 2026-03-03-chip.scd),
// used with permission — nathanho.bandcamp.com
(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
var instDir = outputDir +/+ "instruments";
var fxDir = outputDir +/+ "effects";
outputDir.mkdir;
instDir.mkdir;
fxDir.mkdir;

// --- gated voices (hold at sustain until the score releases the gate) ---

SynthDef(\chip_pulseChord, { |out=0, freq=440, amp=1.0, gate=1, pan=0,
    width=0.5, pwmRate=0.7, pwmDepth=0.15, octaveMix=0.25,
    attackTime=0.01, decayTime=0.08, sustainLevel=0.85, releaseTime=0.2,
    peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, w;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    w = (width + (LFTri.kr(pwmRate) * pwmDepth)).clip(0.1, 0.9);
    snd = Pulse.ar(freq, w);
    snd = snd + (Pulse.ar(freq * 2, 0.5) * octaveMix);
    snd = LPF.ar(snd, (freq * 6).clip(500, 9000));
    snd = LeakDC.ar(snd);
    snd = snd * -12.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_bass, { |out=0, freq=110, amp=1.0, gate=1, pan=0,
    steps=16, drive=1.3, portamento=0.02,
    attackTime=0.005, decayTime=0.05, sustainLevel=0.9, releaseTime=0.15,
    peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    snd = Latch.ar(LFTri.ar(f), Impulse.ar(f * steps));
    snd = (snd * drive.clip(1.0, 4.0)).tanh;
    snd = LeakDC.ar(snd);
    snd = LPF.ar(snd, (f * 8).clip(200, 3000));
    snd = snd * -8.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_lead, { |out=0, freq=440, amp=1.0, gate=1, pan=0,
    width=0.35, portamento=0.03, vibRate=5.5, vibDepth=0.12, vibDelay=0.15,
    attackTime=0.005, decayTime=0.06, sustainLevel=0.8, releaseTime=0.12,
    peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, f, vibOn;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    f = Lag3.kr(freq, portamento);
    vibOn = EnvGen.kr(Env([0, 0, 1], [vibDelay, 0.2]));
    f = f * (SinOsc.kr(vibRate) * vibDepth * vibOn).midiratio;
    snd = Pulse.ar(f, width);
    snd = LPF.ar(snd, (f * 8).clip(800, 10000));
    snd = LeakDC.ar(snd);
    snd = snd * -10.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_glassPad, { |out=0, freq=440, amp=1.0, gate=1, pan=0,
    ratio=3.0, brightness=0.8, detune=0.05, shimmerRate=0.35,
    attackTime=0.5, decayTime=0.4, sustainLevel=0.75, releaseTime=1.4,
    peakLevel=1.0, attackCurve=3.0, decayCurve=(-2), releaseCurve=(-4)|
    var snd, env, index, fa, fb, va, vb;
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    index = brightness * EnvGen.kr(Env([1, 1, 0.35], [0.08, 1.2], -3));
    fa = freq * detune.midiratio;
    fb = freq * (detune * -1).midiratio;
    va = SinOsc.ar(fa, SinOsc.ar(fa * ratio) * index);
    vb = SinOsc.ar(fb, SinOsc.ar(fb * ratio) * index);
    snd = (va + vb) * 0.5;
    snd = snd * (0.92 + (SinOsc.kr(shimmerRate) * 0.08));
    snd = LeakDC.ar(snd);
    snd = snd * -2.dbamp * amp * env;
    Out.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_fmBell, { |out=0, freq=880, amp=1.0, pan=0,
    ratio=3.5, brightness=1.4, hold=0.35, release=1.2|
    var snd, index, mod;
    index = brightness * EnvGen.kr(Env.perc(0.002, release));
    mod = SinOsc.ar(freq * ratio) * index;
    snd = SinOsc.ar(freq, mod);
    snd = snd * -9.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, hold, release, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- accents (self-freeing one-shots; pitch moves are octave-only) ---

SynthDef(\chip_coinBlip, { |out=0, freq=880, amp=1.0, pan=0,
    octaves=1.0, jumpTime=0.06, width=0.5, tone=8.0, sparkle=0.0,
    hold=0.25, release=0.3|
    var snd, step, f;
    step = EnvGen.kr(Env([0, 0, 1], [jumpTime, 0.005]));
    f = freq * (2 ** (step * octaves));
    snd = Pulse.ar(f, width);
    snd = snd + (SinOsc.ar(f * 2) * sparkle);
    snd = LPF.ar(snd, (freq * tone).clip(800, 12000));
    snd = snd * -10.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, hold, release, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_blipLead, { |out=0, freq=440, amp=1.0, pan=0,
    chirpTime=0.02, width=0.4, hold=0.05, release=0.12|
    var snd, sweep;
    sweep = EnvGen.kr(Env([0.5, 1, 1], [chirpTime, 0.01], -2));
    snd = Pulse.ar(freq * sweep, width);
    snd = LPF.ar(snd, (freq * 10).clip(1000, 10000));
    snd = snd * -10.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, hold, release, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_powerArp, { |out=0, freq=440, amp=1.0, pan=0,
    stepTime=0.05, width=0.5, hold=0.16, release=0.35|
    var snd, ladder;
    ladder = EnvGen.kr(Env([0, 0, 1, 1, 2, 2], [stepTime, 0, stepTime, 0, stepTime], 0));
    snd = Pulse.ar(freq * (2 ** ladder), width);
    snd = LPF.ar(snd, (freq * 12).clip(1500, 12000));
    snd = snd * -10.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, hold, release, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_zapDown, { |out=0, freq=1200, amp=1.0, pan=0,
    fall=0.25, zapTime=0.18, width=0.5|
    var snd, pitch;
    pitch = XLine.kr(freq, freq * fall, zapTime);
    snd = Pulse.ar(pitch, width);
    snd = LPF.ar(snd, (pitch * 6).clip(400, 9000));
    snd = snd * EnvGen.ar(Env.perc(0.002, zapTime));
    snd = snd * -12.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.02, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_riser, { |out=0, freq=440, amp=1.0, pan=0, duration=2.0,
    octaves=3.0, width=0.4, sizzle=0.35, release=0.5|
    var snd, rise;
    rise = XLine.kr(freq * (0.5 ** octaves), freq, duration);
    snd = Pulse.ar(rise, width);
    snd = snd + (Pulse.ar(rise * 2, 0.5) * 0.3);
    snd = snd + (HPF.ar(Hasher.ar(Sweep.ar), XLine.kr(8000, 2000, duration)) * sizzle);
    snd = LPF.ar(snd, (rise * 8).clip(400, 10000));
    snd = LeakDC.ar(snd);
    snd = snd * EnvGen.kr(Env([0, 1], [duration], 4));
    snd = snd * -12.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.001, duration, release), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_powerDown, { |out=0, freq=440, amp=1.0, pan=0, duration=2.5,
    octaves=2.0, stepRate=12.0, flicker=0.3, width=0.5, release=0.9|
    var snd, fall, step, dying;
    fall = XLine.kr(freq, freq * (0.5 ** octaves), duration);
    step = Latch.kr(fall, Impulse.kr(XLine.kr(stepRate, 2.0, duration)));
    snd = Pulse.ar(step, width);
    snd = snd + (Pulse.ar(step * 0.5, 0.5) * 0.6);
    snd = LPF.ar(snd, (step * 6).clip(150, 6000));
    snd = LeakDC.ar(snd);
    dying = (LFPulse.kr(XLine.kr(9.0, 2.0, duration), 0, 0.8) * flicker) + (1 - flicker);
    snd = snd * dying;
    snd = snd * -9.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.005, duration, release, curve: -3), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- percussion (self-freeing one-shots) ---

SynthDef(\chip_gridKick, { |out=0, amp=1.0, pan=0, baseFreq=52, punch=1.0|
    var snd, pitch, click;
    pitch = XLine.ar(baseFreq * 6, baseFreq, 0.045);
    snd = SinOsc.ar(pitch);
    snd = (snd * (2 + punch)).tanh;
    click = BPF.ar(Hasher.ar(Sweep.ar), 3500, 0.5);
    click = click * EnvGen.ar(Env.perc(0.0005, 0.012));
    snd = snd + (click * -8.dbamp);
    snd = snd * EnvGen.ar(Env.perc(0.001, 0.35));
    snd = snd * -6.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.12, 0.3, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_bitSnare, { |out=0, amp=1.0, pan=0, tone=1800, crackle=0.6|
    var snd, body, hiss, grit;
    body = SinOsc.ar(XLine.ar(330, 180, 0.04));
    body = body * EnvGen.ar(Env.perc(0.001, 0.06));
    hiss = BPF.ar(Hasher.ar(Sweep.ar), tone, 0.8);
    hiss = hiss * EnvGen.ar(Env.perc(0.002, 0.16));
    grit = Latch.ar(Hasher.ar(Sweep.ar + 1), Impulse.ar(5500)) * crackle;
    grit = HPF.ar(grit, 1200);
    grit = grit * EnvGen.ar(Env.perc(0.001, 0.09));
    snd = (body * 0.7) + hiss + (grit * 0.5);
    snd = snd.tanh;
    snd = snd * -8.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.08, 0.22, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

SynthDef(\chip_tickHat, { |out=0, amp=1.0, pan=0, openness=0.0, tone=7000|
    var snd, closed, open;
    snd = HPF.ar(Hasher.ar(Sweep.ar), tone.clip(2000, 12000));
    closed = EnvGen.ar(Env.perc(0.0005, 0.035));
    open = EnvGen.ar(Env.perc(0.001, 0.3)) * openness.clip(0.0, 1.0);
    snd = snd * (closed + open).clip(0.0, 1.0);
    snd = snd * -14.dbamp * amp;
    snd = snd * EnvGen.ar(Env.linen(0.0, 0.02, 0.35, curve: -4), doneAction: 2);
    OffsetOut.ar(out, Pan2.ar(snd, pan));
}).writeDefFile(instDir);

// --- insert FX (stereo: In -> process -> ReplaceOut) ---

SynthDef(\chip_echo, { |inBus=0, outBus=0, delayTime=0.25, decayTime=1.2,
    tone=3500, mix=0.25, gain=1.0|
    var dry, wet, m, snd;
    dry = In.ar(inBus, 2);
    wet = CombC.ar(LPF.ar(dry, tone), 1.0, Lag.kr(delayTime, 0.1).clip(0.02, 1.0), decayTime);
    wet = LPF.ar(wet, tone);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    snd = (dry * (1 - m)) + (wet * m);
    ReplaceOut.ar(outBus, snd * gain);
}).writeDefFile(fxDir);

SynthDef(\chip_downSampler, { |inBus=0, outBus=0, rate=5500, grit=0.3, mix=1.0, gain=1.0|
    var dry, held, m, snd;
    dry = In.ar(inBus, 2);
    held = Latch.ar(dry, Impulse.ar(rate.clip(300, 22050)));
    held = (held * (1 + (grit * 4))).tanh;
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    snd = (dry * (1 - m)) + (held * m);
    ReplaceOut.ar(outBus, snd * gain);
}).writeDefFile(fxDir);

SynthDef(\chip_chorusLite, { |inBus=0, outBus=0, rate=0.6, depth=3.5, mix=0.4, gain=1.0|
    var dry, wet, m, snd, lfoL, lfoR;
    dry = In.ar(inBus, 2);
    lfoL = SinOsc.kr(rate, 0);
    lfoR = SinOsc.kr(rate, 0.5pi);
    wet = DelayC.ar(dry, 0.05, [
        (0.012 + (lfoL * depth * 0.001)).clip(0.001, 0.045),
        (0.012 + (lfoR * depth * 0.001)).clip(0.001, 0.045)
    ]);
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    snd = (dry * (1 - m)) + (wet * m);
    ReplaceOut.ar(outBus, snd * gain);
}).writeDefFile(fxDir);

SynthDef(\chip_pulseDuck, { |inBus=0, outBus=0, rate=2.0, depth=0.5, shape=4.0, mix=1.0, gain=1.0|
    var dry, wet, m, snd, ramp, duck;
    dry = In.ar(inBus, 2);
    ramp = (LFSaw.kr(rate, 1) + 1) * 0.5;
    duck = 1 - (depth.clip(0.0, 1.0) * ((1 - ramp) ** shape));
    wet = dry * duck;
    m = Lag.kr(mix, 0.1).clip(0.0, 1.0);
    snd = (dry * (1 - m)) + (wet * m);
    ReplaceOut.ar(outBus, snd * gain);
}).writeDefFile(fxDir);

"All chip synthdefs compiled to: %".format(outputDir).postln;
)
