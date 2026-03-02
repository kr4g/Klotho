(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
outputDir.mkdir;

// Default melodic instrument -- gated, triangle osc
SynthDef(\kl_tri, { |out=0, freq=440, amp=0.5, gate=1, pan=0, portamento=0.1,
    vibRate=5, vibDepth=0, toneLPFRatio=2, filterEnvAmt=0.2, softDrive=1.1, softMix=0.08,
    attackTime=0.05, decayTime=0.08, sustainLevel=0.75, releaseTime=0.25, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var sig, env, f, vib, vibRateSm, vibDepthSm, ampSm, panSm, cutoff, ratioSm, filterEnvAmtSm, softDriveSm, softMixSm;
    vibRateSm = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
    vibDepthSm = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
    f = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
    vib = SinOsc.kr(vibRateSm, mul: vibDepthSm).midiratio;
    f = f * vib;
    ampSm = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
    panSm = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
    ratioSm = Lag.kr(toneLPFRatio.max(0.25), \toneLPFRatioLag.kr(0.1).max(0.0));
    filterEnvAmtSm = Lag.kr(filterEnvAmt.clip(0.0, 2.0), \filterEnvAmtLag.kr(0.1).max(0.0));
    softDriveSm = Lag.kr(softDrive.max(0.1), \softDriveLag.kr(0.1).max(0.0));
    softMixSm = Lag.kr(softMix.clip(0.0, 1.0), \softMixLag.kr(0.1).max(0.0));
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    cutoff = (f * ratioSm * (1 + (filterEnvAmtSm * env))).clip(40, (f * 8).min(12000));
    sig = LFTri.ar(f);
    sig = LPF.ar(sig, cutoff);
    sig = XFade2.ar(sig, tanh(sig * softDriveSm), (softMixSm * 2) - 1);
    sig = sig * env * ampSm;
    sig = Pan2.ar(sig, panSm);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

// Spectral / sine instrument -- gated, slow release
SynthDef(\kl_sine, { |out=0, freq=440, amp=0.3, gate=1, pan=0, portamento=0.1,
    vibRate=5, vibDepth=0,
    attackTime=0.05, decayTime=0.15, sustainLevel=0.8, releaseTime=0.8, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var sig, env, f, vib, vibRateSm, vibDepthSm, ampSm, panSm;
    vibRateSm = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
    vibDepthSm = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
    f = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
    vib = SinOsc.kr(vibRateSm, mul: vibDepthSm).midiratio;
    f = f * vib;
    ampSm = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
    panSm = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    sig = SinOsc.ar(f);
    sig = sig * env * ampSm;
    sig = Pan2.ar(sig, panSm);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

SynthDef(\kl_sqr, { |out=0, freq=440, amp=0.4, gate=1, pan=0, width=0.5, portamento=0.1,
    vibRate=5, vibDepth=0, toneLPFRatio=2, filterEnvAmt=0.2, softDrive=1.1, softMix=0.08,
    attackTime=0.05, decayTime=0.07, sustainLevel=0.65, releaseTime=0.2, peakLevel=1.0,
    attackCurve=(-3), decayCurve=(-2), releaseCurve=(-4)|
    var sig, env, f, vib, vibRateSm, vibDepthSm, ampSm, panSm, widthSm, cutoff, ratioSm, filterEnvAmtSm, softDriveSm, softMixSm;
    vibRateSm = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
    vibDepthSm = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
    f = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
    vib = SinOsc.kr(vibRateSm, mul: vibDepthSm).midiratio;
    f = f * vib;
    ampSm = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
    panSm = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
    widthSm = Lag.kr(width.clip(0.01, 0.99), \widthLag.kr(0.1).max(0.0));
    ratioSm = Lag.kr(toneLPFRatio.max(0.25), \toneLPFRatioLag.kr(0.1).max(0.0));
    filterEnvAmtSm = Lag.kr(filterEnvAmt.clip(0.0, 2.0), \filterEnvAmtLag.kr(0.1).max(0.0));
    softDriveSm = Lag.kr(softDrive.max(0.1), \softDriveLag.kr(0.1).max(0.0));
    softMixSm = Lag.kr(softMix.clip(0.0, 1.0), \softMixLag.kr(0.1).max(0.0));
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    cutoff = (f * ratioSm * (1 + (filterEnvAmtSm * env))).clip(40, (f * 8).min(12000));
    sig = Pulse.ar(f, widthSm);
    sig = LPF.ar(sig, cutoff);
    sig = XFade2.ar(sig, tanh(sig * softDriveSm), (softMixSm * 2) - 1);
    sig = sig * env * ampSm;
    sig = LeakDC.ar(sig);
    sig = Pan2.ar(sig, panSm);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

SynthDef(\kl_saw, { |out=0, freq=440, amp=0.35, gate=1, pan=0, portamento=0.1,
    vibRate=5, vibDepth=0, toneLPFRatio=2, filterEnvAmt=0.2, softDrive=1.1, softMix=0.08,
    attackTime=0.05, decayTime=0.1, sustainLevel=0.7, releaseTime=0.25, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var sig, env, f, vib, vibRateSm, vibDepthSm, ampSm, panSm, cutoff, ratioSm, filterEnvAmtSm, softDriveSm, softMixSm;
    vibRateSm = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
    vibDepthSm = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
    f = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
    vib = SinOsc.kr(vibRateSm, mul: vibDepthSm).midiratio;
    f = f * vib;
    ampSm = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
    panSm = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
    ratioSm = Lag.kr(toneLPFRatio.max(0.25), \toneLPFRatioLag.kr(0.1).max(0.0));
    filterEnvAmtSm = Lag.kr(filterEnvAmt.clip(0.0, 2.0), \filterEnvAmtLag.kr(0.1).max(0.0));
    softDriveSm = Lag.kr(softDrive.max(0.1), \softDriveLag.kr(0.1).max(0.0));
    softMixSm = Lag.kr(softMix.clip(0.0, 1.0), \softMixLag.kr(0.1).max(0.0));
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    cutoff = (f * ratioSm * (1 + (filterEnvAmtSm * env))).clip(40, (f * 8).min(12000));
    sig = Saw.ar(f);
    sig = LPF.ar(sig, cutoff);
    sig = XFade2.ar(sig, tanh(sig * softDriveSm), (softMixSm * 2) - 1);
    sig = sig * env * ampSm;
    sig = Pan2.ar(sig, panSm);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

SynthDef(\kl_noisebpf, { |out=0, freq=440, amp=0.2, gate=1, pan=0, portamento=0.1,
    rq=0.001,
    attackTime=0.05, decayTime=0.12, sustainLevel=0.85, releaseTime=0.35, peakLevel=1.0,
    attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
    var sig, env, f, ampSm, panSm, rqSm, bpfMul;
    f = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
    ampSm = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
    panSm = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
    rqSm = Lag.kr(rq.clip(0.001, 1.0), \rqLag.kr(0.1).max(0.0));
    env = EnvGen.kr(
        Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
        gate,
        doneAction: 2
    );
    bpfMul = rqSm.linexp(0.001, 1.0, 16.0, 0.5);
    sig = BPF.ar(WhiteNoise.ar(1), f.clip(40, 18000), rqSm, bpfMul);
    sig = sig * env * ampSm;
    sig = Pan2.ar(sig, panSm);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

SynthDef(\kl_kicktone, { |out=0, amp=0.85, pan=0,
    dur=0.6, baseFreq=110, pitchDrop=2.0, pitchDropTime=0.04, pitchCurve=(-6),
    clickAmp=0.004, clickHPF=1800, clickLPF=6500, clickAtk=0.001, clickDec=0.01, clickCurve=(-2),
    bodyAtk=0.001, bodyDec=0.16, bodyCurve=(-5),
    sustainAtk=0.004, sustainRel=0.1, sustainCurve=(-3), sustainMix=0.45,
    sustainLPF=1800, drive=1.03|
    var clickEnv, bodyEnv, sustainEnv, pitchEnv;
    var click, body, sustain, sig, sustainHold;
    sustainHold = (dur - sustainAtk - sustainRel).max(0.01);
    pitchEnv = EnvGen.kr(Env([pitchDrop, 1], [pitchDropTime], [pitchCurve]));
    clickEnv = EnvGen.kr(Env.perc(clickAtk, clickDec, curve: clickCurve));
    bodyEnv = EnvGen.kr(Env.perc(bodyAtk, bodyDec.min(dur), curve: bodyCurve));
    sustainEnv = EnvGen.kr(Env([0, 1, 1, 0], [sustainAtk, sustainHold, sustainRel], [sustainCurve, 0, sustainCurve]), doneAction: 2);

    click = LPF.ar(HPF.ar(WhiteNoise.ar(1), clickHPF.max(80)), clickLPF.max(200)) * clickEnv * clickAmp;
    body = SinOsc.ar(baseFreq.max(20) * pitchEnv) * bodyEnv;
    sustain = SinOsc.ar(baseFreq.max(20)) * sustainEnv * sustainMix;
    sustain = LPF.ar(sustain, sustainLPF.max(80));

    sig = (body + sustain + click) * amp;
    sig = tanh(sig * drive.max(0.1));
    sig = Pan2.ar(sig, pan);
    Out.ar(out, sig);
}).writeDefFile(outputDir);

// Infrastructure: bus router
SynthDef(\__busRouter, { |inBus=0, outBus=0, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = sig * gain;
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Infrastructure: bus router with level monitoring
SynthDef(\__busRouterMonitor, { |inBus=0, outBus=0, gain=1.0, id=0|
    var amp, peak;
    var sig = In.ar(inBus, 2);
    sig = sig * gain;
    amp = Amplitude.kr(sig, 0.01, 0.1);
    peak = amp.sum * 0.5;
    SendReply.kr(Impulse.kr(20), '/trackLevel', [peak, id]);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\__chainLimiter, { |inBus=0, outBus=0, gain=1.0, preGain=1.0, limitLevel=0.95, lookAhead=0.01|
    var sig = In.ar(inBus, 2);
    sig = sig * preGain.max(0.0);
    sig = Limiter.ar(sig, limitLevel.clip(0.01, 1.0), lookAhead.max(0.001));
    sig = sig * gain.max(0.0);
    sig = LeakDC.ar(sig);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Control envelope reader: sweeps through a buffer region and writes to a control bus.
// Voice synths or insert FX are mapped to that bus via /n_map for continuous automation.
SynthDef(\__klEnvCtrl, { |bufnum=0, bus=0, dur=1, startFrame=0, numFrames=512|
    var phase = Line.kr(startFrame, startFrame + numFrames - 1, dur, doneAction: 2);
    Out.kr(bus, BufRd.kr(1, bufnum, phase, interpolation: 2));
}).writeDefFile(outputDir);

// ── Insert effects ──────────────────────────────────────────────

// Reverb (FreeVerb wrapper)
SynthDef(\__klReverb, { |inBus=0, outBus=0, mix=0.3, room=0.7, damp=0.5, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = FreeVerb.ar(sig, mix.clip(0, 1), room.clip(0, 1), damp.clip(0, 1));
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Comb delay
SynthDef(\__klDelay, { |inBus=0, outBus=0, delayTime=0.25, decayTime=1.0, maxDelay=2.0, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = sig + CombL.ar(sig, maxDelay.max(delayTime), delayTime.max(0.001), decayTime);
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Multi-stage distortion with resonant body (adapted from FoxDot)
SynthDef(\__klDistortion, { |inBus=0, outBus=0, dist=0.5, gain=1.0|
	var sig, dry;
	sig = In.ar(inBus, 2);
	dry = sig;
	sig = CrossoverDistortion.ar(sig, amp: 0.2, smooth: 0.01);
	sig = sig + (0.1 * dist * DynKlank.ar(
		`[[60, 61, 240, 3000 + SinOsc.ar(62, mul: 100)], nil, [0.1, 0.1, 0.05, 0.01]], sig));
	sig = (sig.cubed * 8).softclip * 0.5;
	sig = SelectX.ar(dist.clip(0, 1), [dry, sig]);
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Bit crusher / sample rate reducer
SynthDef(\__klBitcrush, { |inBus=0, outBus=0, bits=8, crush=4, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = Decimator.ar(sig, rate: (44100 / crush.max(1)).max(100), bits: bits.clip(1, 24));
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Resonant low-pass filter
SynthDef(\__klLPF, { |inBus=0, outBus=0, freq=1200, rq=1.0, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = RLPF.ar(sig, freq.clip(20, 20000), rq.clip(0.01, 2));
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Resonant high-pass filter
SynthDef(\__klHPF, { |inBus=0, outBus=0, freq=200, rq=1.0, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = RHPF.ar(sig, freq.clip(20, 20000), rq.clip(0.01, 2));
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Tremolo (sinusoidal amplitude modulation)
SynthDef(\__klTremolo, { |inBus=0, outBus=0, rate=4.0, depth=0.5, gain=1.0|
	var sig, mod;
	sig = In.ar(inBus, 2);
	mod = SinOsc.kr(rate.max(0.01), mul: depth.clip(0, 1) * 0.5, add: 1 - (depth.clip(0, 1) * 0.5));
	sig = sig * mod;
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

// Rhythmic gate (pulse-wave chopper)
SynthDef(\__klChop, { |inBus=0, outBus=0, rate=4.0, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = sig * LFPulse.kr(rate.max(0.01), add: 0.01);
	sig = sig * gain;
	ReplaceOut.ar(inBus, sig);
	Out.ar(outBus, sig);
}).writeDefFile(outputDir);

"All synthdefs compiled to: %".format(outputDir).postln;
)
