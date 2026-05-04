(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
outputDir.mkdir;

// -------------------------------------------------------------------------------------------------------------------------------------
// Instruments
// -------------------------------------------------------------------------------------------------------------------------------------

// -------------------------------------------------------------------------------------------------------------------------------------
// Pads & drones
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_ambi, { |out=0, freq=440, amp=1, gate=1, brightness=1, pan=0, portamento=0.08, vibRate=3, vibDepth=0.07, attackTime=1, decayTime=0.5, sustainLevel=0.5, releaseTime=2, attackCurve=(0), decayCurve=(2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = freq + ( ampEnv.linexp(0, 1, freq * brightness.linexp(0.0, 1, 4, 8), freq + LFNoise2.ar(4, mul:1))  * SinOsc.ar(freq + LFNoise2.ar(4, mul:2)));

	osc=SinOsc.ar(freq + Rand(0.99,1.01), phase: pi/2);
	osc = RLPF.ar(osc, XLine.ar(freq * brightness.linexp(0.0, 1, 8, 16), freq * 2, attackTime + decayTime), Line.ar(0.05, 1, attackTime + decayTime));
	osc = osc * -20.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_dub, { |out=0, freq=110, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 2);
	osc=(LFTri.ar(freq, mul: 1) + SinOscFB.ar(freq, mul: 1));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_glass, { |out=0, freq=440, amp=1, gate=1, pan=0, spread=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=2, decayTime=0.3, sustainLevel=0.7, releaseTime=4, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 1.5);
	freq=(freq * [1, (1 + (0.005 * spread))]);
	osc=DynKlank.ar(`[[2, 4, 9, 16], [1, 1, 1, 1], [2, 2, 2, 2]], PinkNoise.ar(0.00025).dup + Crackle.ar(1.9, 0.00025) , freq);
	osc = Mix(osc);
	osc = LPF.ar(osc, freq * 8);
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_longsaw, { |out=0, freq=440, amp=1, gate=1, brightness=0.5, pan=0, portamento=0.08, vibRate=1.5, vibDepth=0.007, attackTime=1.25, decayTime=1.25, sustainLevel=0.5, releaseTime=1, attackCurve=(2), decayCurve=(2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;

	amp = (amp / 8);
	osc = Saw.ar([freq, freq * 1.001]);
	osc = LPF.ar(osc, ampEnv.linexp(0, 1, freq * 2, freq * 4), 0.5) + Splay.ar(BPF.ar(osc, LFNoise1.kr([0.9,1.1,1.2]).exprange(freq * 2, freq * brightness.linexp(0.0, 1, 8, 16)), 0.15, 0.4));
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_pads, { |out=0, freq=440, amp=1, gate=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=2, decayTime=0.5, sustainLevel=0.5, releaseTime=2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv, dur = attackTime + decayTime + releaseTime;
	rq = rq.clip(0.001, 2.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 2);
	freq = freq * [1, 1.01];
	osc = SinOsc.ar(Line.kr(freq * 4, freq, 0.01) + (Line.kr(10, (freq * 2), releaseTime) * Pulse.ar(freq, width: SinOsc.kr(0.225/dur, mul:1))), mul:0.5);
	osc = RHPF.ar(osc, [ampEnv.linexp(0, 1, 400, 1000, releaseTime), ampEnv.linexp(0, 1, 4000,900,releaseTime)], rq);
	osc = osc * Line.ar(0.001,1,releaseTime * 0.05);
	osc = Mix(osc) * -16.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_ripple, { |out=0, freq=440, amp=1, gate=1, brightness=0.5, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=2.5, decayTime=0.25, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv, dur = attackTime + decayTime + releaseTime;
	rq = rq.clip(0.001, 2.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp / 6);
	osc = (Pulse.ar(freq, 0.2, 0.25) + Pulse.ar((freq + 1), 0.5, 0.5));
	osc = (osc * SinOsc.ar(0.225 / dur, 0, 0.5, 1));
	osc = RLPF.ar(osc, ampEnv.linexp(0, 1, freq * 2, freq * brightness.linexp(0.0, 1, 4, 16)), rq);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_sinepad, { |out=0, freq=440, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=2, decayTime=1.5, sustainLevel=0.6, releaseTime=2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp * 1.5);
	freq = (freq + [0, LFNoise1.kr(0.01).range(1, 5)]);
	osc = SinOsc.ar(freq, mul: 1);
	osc = HPF.ar(osc, 1000);
	osc = Mix(osc) * -16.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_swell, { |out=0, freq=440, amp=1, gate=1, brightness = 0.5, pan=0, lfoRate=0.1, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=2, decayTime=1, sustainLevel=0.7, releaseTime=4, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	rq = rq.clip(0.001, 2.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp / 4);
	freq = (freq + [0, 1]);
	freq = (freq * [1, 0.5]);
	osc = VarSaw.ar(freq, width: SinOsc.ar(lfoRate.max(0.05), add: 0.5, mul: [0.5, 0.5]), mul: [1, 0.5]);
	osc = RLPF.ar(osc, SinOsc.kr(lfoRate/2, 3pi/2).exprange(freq * 4, freq * brightness.linexp(0.0, 1, 8, 16)), rq);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Keys & piano
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_keys, { |out=0, freq=440, amp=1, gate=1, pan=0, brightness=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	rq = rq.clip(0.001, 2.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq = freq * [1, 1.005];
	amp = amp / 4;
	osc = SinOsc.ar(freq + (brightness * 100) * XFade2.ar(LFPar.ar(freq * (1/2)), LFTri.ar(freq * 1)), phase: 0.2, mul: 0.8);
	osc = RHPF.ar(osc, 400, rq);
	osc = Mix(osc);
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_piano, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=1, attackCurve=(-4), releaseCurve=(-4)|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp * 0.7);
	osc = MdaPiano.ar((freq[0]), vel: (40 + (amp * 60)), decay: (releaseTime / 4));
	osc = osc * Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]).kr(Done.freeSelf);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Synth leads & classic voices
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_pasha, { |out=0, freq=440, amp=1, gate=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, env, lfo, ampEnv;
	rq = rq.clip(0.001, 2.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	lfo = LFPar.kr([1,1.04], mul:0.5);
	osc = Pulse.ar(freq, lfo);
	env = EnvGen.ar(Env([0,1,0.5,0.2,0], [0, 0.01, releaseTime / 1.5, releaseTime / 1.5], curve:'cub'), doneAction: 0);
	osc = osc * env;
	osc = Mix(osc) * 0.25;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_prophet, { |out=0, freq=440, amp=1, gate=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, lforate=6, lfowidth=0.5, cutoff=1200, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var lfo, pulse, filter, ampEnv;
	rq = rq.clip(0.001, 2.0);
	lforate = lforate.max(0.01);
	lfowidth = lfowidth.clip(0.0, 1.0);
	cutoff = cutoff.max(20.0);
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	amp = amp * 0.1;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	lfo = LFTri.kr(lforate * [1, 1.01], Rand(0, 2.0)!2);
	pulse = Pulse.ar(freq * [1, 1.01], lfo * lfowidth + 0.5);
	filter = RLPF.ar(pulse, cutoff, rq);
	filter = BHiPass.ar(filter, 200);
	Out.ar(out, Pan2.ar(Mix(filter) * 0.5, pan) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_razz, { |out=0, freq=440, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.125, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, env, ampEnv, freqAR;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq = (freq + [0, 1]);
	freqAR = K2A.ar(freq);
	osc = (Saw.ar((freqAR * [1, 0.5]), [1, 0.3333333333333333]) + Saw.ar((freqAR + LFNoise2.ar(4).range(0.5, 2.5)), 1));
	osc = BPF.ar(osc, (freq * 2.5), 0.3);
	osc = RLPF.ar(osc, 1300, 0.78);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_scatter, { |out=0, freq=440, amp=1, gate=1, pan=0, rate=0, width=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.05, decayTime=0.1, sustainLevel=0.7, releaseTime=0.8, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc = ((Saw.ar(freq, mul: (1/8)) + VarSaw.ar((freq + [2, 1]), width: width, mul: (1/8))) * LFNoise0.ar(rate));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_soprano, { |out=0, freq=440, amp=1, gate=1, pan=0, fmBias=0, portamento=0.08, vibRate=5, vibDepth=0.167, attackTime=0.25, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 2);
	freq = freq * SinOsc.kr((vibRate + fmBias + 4).max(0.01), mul: vibDepth).midiratio;
	osc=(SinOsc.ar((freq * 3), mul: 1) + SinOscFB.ar((freq * 3), mul: (1/2)));
	osc = Mix(osc) * -21.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_varsaw, { |out=0, freq=440, detune=0.083, amp=1, gate=1, pan=0, width=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.5, decayTime=0.25, sustainLevel=0.7, releaseTime=1, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq = (freq * [1, detune.midiratio]);
	osc = VarSaw.ar(freq, mul: (1/4), width: width);
	osc = Mix(osc) * -12.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Brass & ensemble
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_brass, { |out=0, freq=440, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.2, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	osc=(Saw.ar(freq, 0.4) + Saw.ar((freq + LFNoise2.ar(1).range(0.5, 1.1)), 0.4));
	osc=(osc + Resonz.ar(osc, (freq * XLine.ar(1, 5, 0.13)), 1));
	osc=BPF.ar(osc, (freq * 2.5), 0.3);
	osc=RLPF.ar(osc, 1300, 0.78);
	osc = Mix(osc);
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Strings (bowed / lyrical)
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_charm, { |out=0, freq=440, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=1, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq = (freq + [0, 2]);
	freq = (freq * [1, 2]);
	osc = (SinOsc.ar(freq, mul: (1/4)) + VarSaw.ar((freq * 8), 10, mul: (1/8)));
	osc = LPF.ar(osc, SinOsc.ar(freq.clip(55, 4186).explin(55, 4186, 2, 8), 0, (freq * 2), ((freq * 2) + 10)));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_viola, { |out=0, freq=440, amp=1, gate=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0.03, attackTime=0.25, decayTime=0.15, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, ampEnv;
	ampEnv = EnvGen.kr(
		Env([0, 1, sustainLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp / 2);
	osc = PMOsc.ar(freq, (freq * SinOsc.kr(vibRate.max(0.01), mul: (vibDepth + 0.008)).midiratio), 10, mul: (1/2));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * ampEnv * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Bass — sustained
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_sawbass, { |out=0, freq=110, amp=1, gate=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, cutoff=1200, attackTime=0.01, decayTime=0.0, sustainLevel=0.7, releaseTime=0.2, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc1, osc2, filter, filter2, env, filterenv, ab;
	rq = rq.clip(0.001, 2.0);
	cutoff = cutoff.max(20.0);

	amp = amp * 0.2;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	osc1 = Saw.ar(freq);
	osc2 = Mix(Saw.ar(freq * [0.25,1,1.5], [0.5,0.4,0.1]));
	filterenv = EnvGen.kr(Env.adsr(0.0, 0.5, 0.2, releaseTime), gate);
	filter =  RLPF.ar(osc1 + osc2, cutoff * filterenv + 100, rq);
	ab = abs(filter);
	filter2 = (filter * (ab + 2) / (filter ** 2 + 1 * ab + 1));
	filter2 = BLowShelf.ar(filter2, 300, 1.0, -12);
	filter2 = BPeakEQ.ar(filter2, 1600, 1.0, -6);
	env = EnvGen.kr(Env.adsr(attackTime, decayTime, sustainLevel, releaseTime, curve: [attackCurve, decayCurve, releaseCurve]), gate, doneAction: 2);
	Out.ar(out, Pan2.ar((filter + filter2) * env, pan) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Bass — punchy & distorted
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_bass, { |out=0, freq=110, amp=1, pan=0, width=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.02, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 0.8);
	osc=((LFTri.ar(freq, mul: 1) + VarSaw.ar(freq, width: width, mul: 1)) + SinOscFB.ar(freq, mul: (1/2)));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * -26.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_dab, { |out=0, freq=110, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.05, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=(HPF.ar(Saw.ar(freq, mul: (1/2)), 2000) + VarSaw.ar(freq, mul: 1, width: EnvGen.ar(Env.perc(attackTime: (releaseTime / 20),releaseTime: (releaseTime / 4),level: 0.5,curve: -5), doneAction: 0)));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_dbass, { |out=0, freq=110, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.02, decayTime=0.01, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq] * Line.ar(Rand(0.5,1.5),1,0.02);
	amp=(amp * 0.8);
	osc=( VarSaw.ar(freq, width: LFTri.ar((0.5 * rate)/releaseTime, iphase:0.9, add:0.8, mul: 0.2), mul: 1));
	env=EnvGen.ar(Env([0,1,0.8,0.8,0], [attackTime, decayTime, releaseTime/2, releaseTime/2]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_dirt, { |out=0, freq=110, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 2);
	osc=((LFSaw.ar(freq, mul: 1) + VarSaw.ar((freq + 1), width: 0.85, mul: 1)) + SinOscFB.ar((freq - 1), mul: (1/2)));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_fuzz, { |out=0, freq=110, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 6);
	osc=LFSaw.ar(LFSaw.kr(freq, 0, freq, (freq * 2)));
	env=EnvGen.ar(Env(times: [(releaseTime * 0.8), 0.01],levels: [1, 1, 0.01],curve: 'step'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_growl, { |out=0, freq=110, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=(SinOsc.ar((freq + SinOsc.kr(0.5, add: 1, mul: 2)), mul: 1) * Saw.ar(((releaseTime / 1.5) * 32)));
	env=EnvGen.ar(Env(times: [(releaseTime / 2), (releaseTime / 2)],levels: [0, 1, 0],curve: 'lin'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.95;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_jbass, { |out=0, freq=110, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.02, releaseTime=0.35, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 0.8);
	osc=LFTri.ar(freq, mul: 1);
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Plucked strings & resonators
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_karp, { |out=0, freq=440, amp=1, pan=0, coef=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0, releaseTime=5, attackCurve=(-4), releaseCurve=(-4)|
	var burst, dt, dlMax, sig, freqMono;
	freqMono = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freqMono = freqMono * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	dt = freqMono.reciprocal.clip(2 / SampleRate.ir, 0.5);
	dlMax = (dt * 1.2) + SampleRate.ir.reciprocal;
	burst = WhiteNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02), doneAction: 0);

	sig = CombC.ar(burst, dlMax, dt, coef.clip(0.05, 0.999) * releaseTime);
	sig = sig * 0.15 * Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]).kr(Done.freeSelf);
	sig = Pan2.ar(sig * amp, pan);
	Out.ar(out, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_nylon, { |out=0, freq=440, amp=1, pan=0, rate=1, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.000125, releaseTime=3, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc = (LFPulse.ar(freq, 0.5, (0.33 * rate), 0.25) + LFPar.ar((freq + 0.5), 1, 0.1, 0.25));
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = (osc * env);
	osc = Mix(osc) * -12.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_pluck, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp + 1e-05);
	freq = (freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	osc = ((SinOsc.ar((freq * 1.002), phase: VarSaw.ar(freq, width: Line.ar(1, 0.2, 2))) * 0.3) + (SinOsc.ar(freq, phase: VarSaw.ar(freq, width: Line.ar(1, 0.2, 2))) * 0.3));
	osc = ((osc * XLine.kr(1, 1e-04, (releaseTime * 4), doneAction: 2)) * 0.3);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_sitar, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 0.75);
	osc=LFNoise0.ar([8400, 8500], amp);
	osc=(osc * XLine.ar(1, 1e-06, (releaseTime * 0.1)));
	freq=((265 / (freq * [0.666, 0.669])) * 0.005);
	osc=CombL.ar(osc, delaytime: freq, maxdelaytime: 2);
	env=EnvGen.ar(Env(times: [releaseTime],levels: [1, 1],curve: 'step'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_twang, { |out=0, freq=440, amp=1, pan=0, stretch=1, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq = (freq + [0, 2]);
	osc = LPF.ar(Impulse.ar(freq, 0.1), 4000);
	osc = (EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf) * CombL.ar(osc, delaytime: (stretch.max(0.001) / freq), maxdelaytime: 0.25));
	osc = Mix(osc) * -20.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Bells, mallets & metallic resonators
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_angel, { |out=0, freq=440, amp=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.05, releaseTime=2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	rq = rq.clip(0.001, 2.0);
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp = (amp * 2);
	freq = freq * [1, 1.01];
	osc = Ringz.ar(ClipNoise.ar(0.001).dup / 2, freq * 3);
	osc = RHPF.ar(osc, freq * 2.5, rq);
	osc = Mix(osc);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = osc * env;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_bell, { |out=0, freq=880, amp=1, pan=0, decayScale=4, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=5, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	var imp = WhiteNoise.ar(0.1) * Env.perc(0.01, 0.05).kr(Done.none);
	decayScale = decayScale.max(0.1);
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	decayScale = decayScale.clip(0.0, 10);
	amp = (amp * 4) * decayScale.linlin(0, 10, 1, 0.35);
	osc = (Klank.ar(`[[0.501, 1, 0.7, 2.002, 3, 9.6, 2.49, 11, 2.571, 3.05, 6.242, 12.49, 13, 16, 24], [0.002, 0.1, 0.001, 0.008, 0.02, 0.004, 0.02, 0.04, 0.02, 0.005, 0.05, 0.05, 0.02, 0.03, 0.04], [1.2, 1.2, 1.2, 0.9, 0.9, 0.9, 0.25, 0.25, 0.25, 0.14, 0.14, 0.14, 0.07, 0.07, 0.07]], imp, freq, 0, decayScale));
	osc = LeakDC.ar(osc);
	osc = Mix(osc) * 0.5;
	osc = osc * env * -8.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_feel, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 3);
	freq=(freq * [1, 1.005]);
	osc=Klank.ar(`[[1, 2, 3, (3 + ((rate - 1) / 10))], [1, 1, 1, 1], [2, 2, 2, 2]], (Impulse.ar(0.0005) * Saw.ar(freq, add: 1)), freq);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_gong, { |out=0, freq=440, amp=1, pan=0, rate=0, decayScale=5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=10, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 2.5);
	freq=(freq * 2);
	osc=(Klank.ar(`[[0.501, 1, 0.8, 2.002, 3, 9.6, 2.49, 11, 2.571, 3.05, 6.242, 12.49, 13, 16, 24], [0.002, 0.02, 0.001, 0.008, 0.02, 0.004, 0.02, 0.04, 0.02, 0.005, 0.05, 0.05, 0.02, 0.03, 0.04], [1.2, 1.2, 1.2, 0.9, 0.9, 0.9, 0.25, 0.25, 0.25, 0.14, 0.14, 0.14, 0.07, 0.07, 0.07]], SinOscFB.ar(20, 0, 10), freq, (freq * rate), decayScale));
	osc=HPF.ar(osc, 440);
	osc = Mix(osc) * 0.5;
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = osc * env;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_klank, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=Klank.ar(`[[1, 2, 3, 4], [1, 1, 1, 1], [2, 2, 2, 2]], ClipNoise.ar(0.0005).dup, freq);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_marimba, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=Klank.ar(`[[0.5, 1, 4, 9], [0.5, 1, 1, 1], [1, 1, 1, 1]], PinkNoise.ar([0.007, 0.007]), freq, [0, 2]);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_quin, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq=(freq * [1, 1.01]);
	osc=(Klank.ar(`[[1, 2, 4, 2], [100, 50, 0, 10], [1, 5, 0, 1]], Impulse.ar(freq).dup, freq) / 5000);
	osc=(osc * LFSaw.ar((freq * (1 + rate))));
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_soft, { |out=0, freq=440, amp=1, pan=0, exciterHz=4, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / (200 * (1 + exciterHz)));
	osc=Klank.ar(`[[7, 5, 3, 1], [8, 4, 2, 1], [2, 4, 8, 16]], LFNoise0.ar(exciterHz.max(0.05)), freq);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Drums & kicks
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_donk, { |out=0, freq=110, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.001, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq=(freq + [0, 2]);
	amp=(amp / 1.25);
	osc=Ringz.ar((Impulse.ar(0, phase: rate) / (rate + 1)), freq, releaseTime, 1);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = osc * env;
	osc = Mix(osc) * -18.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_donk1, { |out=0, freq=110, amp=1, pan=0, vibRate=5, vibDepth=0, attackTime=0.001, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	amp=(amp * 9);
	osc=Ringz.ar(Impulse.ar(0), [freq, (freq + 2)], releaseTime, 1);
	osc=osc.tanh;
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = osc * env;
	osc = osc * [min(1, (1-pan)/2), min(1, (pan+1)/2)];
	Out.ar(out, (osc) * amp * -18.dbamp);
}).writeDefFile(outputDir);

SynthDef(\fd_donk2, { |out=0, freq=110, amp=1, pan=0, vibRate=5, vibDepth=0, attackTime=0.001, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	amp=(amp * 9);
	osc=Ringz.ar(Impulse.ar(0), [freq, (freq + 2)], releaseTime, 1);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = osc * env;
	osc = osc * [min(1, (1-pan)/2), min(1, (pan+1)/2)];
	Out.ar(out, (osc) * amp * -23.dbamp);
}).writeDefFile(outputDir);

SynthDef(\fd_squish, { |out=0, freq=110, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=Ringz.ar(Pulse.ar((4 * rate)), freq, releaseTime, 1);
	osc=(osc * XLine.ar(0.5, 1e-06, releaseTime, doneAction: 2));
	osc=osc.cos;
	amp=(amp * 4);
	osc = Mix(osc) * -38.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Noise & glitch
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_crunch, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.1, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 0.5);
	osc=LFNoise0.ar(((Crackle.kr(1.95) * freq) * 15), mul: 1);
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_noise, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq=(freq * 2);
	osc=LFNoise0.ar(freq, 1);
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_rave, { |out=0, freq=440, amp=1, pan=0, chaos=(-1), portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=Gendy1.ar(chaos, mul: (1/2), minfreq: freq, maxfreq: (freq * 2));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_scrap, { |out=0, freq=440, amp=1, pan=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.001, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env, body;
	rq = rq.clip(0.001, 2.0);
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	body = WhiteNoise.ar(1) + Crackle.ar(1.75);
	body = BPF.ar(body, (freq * [1, 1.5]).clip(40, 16000), rq);
	env = EnvGen.ar(Env.perc(attackTime, releaseTime.max(0.001), 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = Mix(body) * env;
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_scratch, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 4);
	freq=(freq * Crackle.ar(1.5));
	osc=SinOsc.ar((freq * SinOsc.kr((vibRate + rate.abs).max(0.01), mul: (vibDepth + 0.008)).midiratio), mul: 1);
	env=EnvGen.ar(Env(times: [(releaseTime / 2), (releaseTime / 2)],levels: [0, 1, 0],curve: 'lin'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// Synth hooks & percussive voices
// -------------------------------------------------------------------------------------------------------------------------------------

SynthDef(\fd_arpy, { |out=0, freq=220, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.05, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp * 2);
	freq=(freq + [0, 0.5]);
	osc=LPF.ar(Impulse.ar(freq), 3000);
	env=EnvGen.ar(Env.perc(attackTime, (releaseTime * 0.25), 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_blip, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=1, attackCurve=(-4), releaseCurve=(-4)|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp + 1e-05);
	freq=(freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	osc=((LFCub.ar((freq * 1.002), iphase: 1.5) + (LFTri.ar(freq, iphase: Line.ar(2, 0, 0, 2)) * 0.3)) * Blip.ar(freq, rate.max(1)));
	osc=((osc * XLine.ar(1, 1e-04, (releaseTime * 2))) * 0.3);
	osc = Mix(osc) * 0.5 * EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_bug, { |out=0, freq=440, amp=1, pan=0, tremHz=8, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=1, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 5);
	freq=(freq * [1, 1.0001]);
	osc=(Pulse.ar(freq, width: [0.09, 0.16, 0.25]) * SinOsc.ar(tremHz.max(0.05), mul:0.5));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_creep, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 4);
	osc=PMOsc.ar(freq, (freq * 2), 10);
	env=EnvGen.ar(Env(times: [releaseTime, 0.001],levels: [0.0001, 1, 0],curve: 'exp'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_lazer, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.1, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	freq=(freq * [1, 1.005]);
	amp=(amp * 0.1);
	osc=(VarSaw.ar(freq, width: ((rate - 1) / 4)) + LFSaw.ar(LFNoise0.ar((rate * 20), add: (freq * Pulse.ar(((rate - 2) + 0.1), add: 1)), mul: 0.5)));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_orient, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=2, attackCurve=(-4), releaseCurve=(-8)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=(LFPulse.ar(freq, 0.5, 0.25, 0.25) + LFPulse.ar(freq, 1, 0.1, 0.25));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_pulse, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 8);
	osc=Pulse.ar(freq);
	env=EnvGen.ar(Env(times: [attackTime, ((releaseTime - attackTime).max(0.001)), attackTime],levels: [0, 1, 1, 0],curve: 'lin'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_saw, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 8);
	osc=Saw.ar(freq);
	env=EnvGen.ar(Env(times: [attackTime, ((releaseTime - attackTime).max(0.001)), attackTime],levels: [0, 1, 1, 0],curve: 'lin'), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_siren, { |out=0, freq=440, amp=1, pan=0, rate=0, vibRate=5, vibDepth=0, attackTime=0.1, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	amp=(amp * 0.1);
	osc=(VarSaw.ar([freq, (freq * 1.005)], width: ((rate - 1) / 4)) + LFSaw.ar(LFNoise0.ar((rate * 20), mul: 0.5, add: (freq * Pulse.ar(((rate - 2) + 0.1), add: 1)))));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_snick, { |out=0, freq=440, amp=1, pan=0, rate=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=1, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	osc=(LFPar.ar(freq, mul: 1) * Blip.ar(((rate + 1) * 4)));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_space, { |out=0, freq=440, amp=1, pan=0, rate=0, rq=0.5, sus=1|
	var osc, env;
	rq = rq.clip(0.001, 2.0);
	freq = freq.max(0.001);
	freq = [freq, freq];
	amp = (amp * 2);
	freq = freq * [1, 1.01];
	osc = Ringz.ar(ClipNoise.ar(0.001).dup / 2 + Impulse.ar(0.01, mul: 0.02 * rate), freq * 3);
	osc = RHPF.ar(osc, freq * 2.5, rq);
	env = EnvGen.ar(Env([1, 0.8, 0.5, 0], [0.2 * sus, 0.5 * sus, 0.7 * sus]), doneAction: Done.freeSelf);
	osc = Mix(osc) * env;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, osc * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_spark, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp + 1e-05);
	freq=(freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	osc=((LFSaw.ar((freq * 1.002), iphase: Saw.ar(0.1)) * 0.3) + (LFSaw.ar(freq, iphase: Saw.ar(0.1)) * 0.3));
	osc=osc * EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc = Mix(osc) * -16.dbamp;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_spick, { |out=0, freq=440, amp=1, pan=0, vibRate=5, vibDepth=0, attackTime=0.1, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	amp=(amp / 4);
	osc=(LFPulse.ar(freq).distort + Impulse.ar((freq + 1)).tan);
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_star, { |out=0, freq=220, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, releaseTime=0.2|
	var osc;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=((amp * 2) + 1e-05);
	osc=((LFSaw.ar((freq * 1.002), iphase: VarSaw.kr(freq, width: Line.kr(1, 0.2, releaseTime))) * 0.3) + (LFSaw.ar(((freq + LFNoise2.ar(50).range(-2, 2)) + 2), iphase: VarSaw.kr((freq + 2), width: Line.kr(1, 0.2, releaseTime))) * 0.3));
	osc=((osc * XLine.ar(1, 1e-04, (releaseTime * 3), doneAction: 2)) * Line.ar(0.01, 0.5, 0.07));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);

SynthDef(\fd_zap, { |out=0, freq=440, amp=1, pan=0, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.025, releaseTime=0.2, attackCurve=(-4), releaseCurve=(-4)|
	var osc, env;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(vibRate.max(0.01), mul: vibDepth).midiratio;
	freq = [freq, freq];
	amp=(amp / 10);
	osc=(Saw.ar(((freq * [1, 1.01]) + LFNoise2.ar(50).range(-2, 2))) + VarSaw.ar((freq + LFNoise2.ar(50).range(-2, 2)), 1));
	env=EnvGen.ar(Env.perc(attackTime, releaseTime, 1, [attackCurve, releaseCurve]), doneAction: Done.freeSelf);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
	Out.ar(out, (osc) * amp);
}).writeDefFile(outputDir);
// -------------------------------------------------------------------------------------------------------------------------------------
// FX
// -------------------------------------------------------------------------------------------------------------------------------------


SynthDef(\fd_reverb, { |inBus=0, outBus=0, room=0.5, mix=0.3, damp=0.5, gain=1.0|
	var sig = In.ar(inBus, 2);
	sig = FreeVerb.ar(sig, mix.clip(0, 1), room.clip(0, 1), damp.clip(0, 1));
	sig = sig * gain.max(0.0);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_combDelay, { |inBus=0, outBus=0, echo=0.5, beatDur=1.0, echoTime=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var d = echo.max(0.0) * beatDur.max(0.001);
	var t = echoTime.max(0.0) * beatDur.max(0.001);
	sig = sig + CombL.ar(sig, maxdelaytime: (2 * beatDur.max(0.001)).max(d + 0.001), delaytime: d.max(0.001), decaytime: t);
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_distortion, { |inBus=0, outBus=0, dist=0.5, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = CrossoverDistortion.ar(sig, amp: 0.2, smooth: 0.01);
	sig = sig + (0.1 * dist.clip(0, 1) * DynKlank.ar(
		`[[60, 61, 240, 3000 + SinOsc.ar(62, mul: 100)], nil, [0.1, 0.1, 0.05, 0.01]], sig
	));
	sig = (sig.cubed * 8).softclip * 0.5;
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_overdriveDistortion, { |inBus=0, outBus=0, drive=0.4, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = (sig * (drive.max(0.0) * 50)).clip(0, 0.2).fold2(2);
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_bitcrush, { |inBus=0, outBus=0, bits=8, crush=4, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = Decimator.ar(sig, rate: (44100 / crush.max(1)).max(100), bits: bits.clip(1, 24));
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_chop, { |inBus=0, outBus=0, chop=4.0, segmentDur=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var rate = (chop.max(0.01) / segmentDur.max(0.001)).max(0.01);
	sig = sig * LFPulse.kr(rate, add: 0.01);
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_tremolo, { |inBus=0, outBus=0, tremolo=4.0, beatDur=1.0, depth=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var rate = (tremolo.max(0.01) / beatDur.max(0.001)).max(0.01);
	var d = depth.clip(0, 1);
	sig = sig * SinOsc.kr(rate, mul: d * 0.5, add: 1 - (d * 0.5));
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_highPassFilter, { |inBus=0, outBus=0, hpf=200, hpr=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = RHPF.ar(sig, hpf.clip(20, 20000), hpr.clip(0.01, 2.0));
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_lowPassFilter, { |inBus=0, outBus=0, lpf=1200, lpr=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = RLPF.ar(sig, lpf.clip(20, 20000), lpr.clip(0.01, 2.0));
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_bandPassFilter, { |inBus=0, outBus=0, bpf=1200, bpr=0.6, bpnoise=2.0, segmentDur=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var n = bpnoise.max(0.01) / segmentDur.max(0.001);
	var f = LFNoise1.kr(n).exprange((bpf.clip(40, 18000) * 0.5).max(20), (bpf.clip(40, 18000) * 2).min(20000));
	var r = LFNoise1.kr(n).exprange((bpr.clip(0.01, 2.0) * 0.5).max(0.01), (bpr.clip(0.01, 2.0) * 2).min(2.0));
	sig = BPF.ar(sig, f, r);
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_filterSwell, { |inBus=0, outBus=0, swell=1.0, segmentDur=1.0, hpr=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var env = EnvGen.kr(Env([0, 1, 0], [segmentDur * 0.25, segmentDur * 0.25], \sin));
	sig = RHPF.ar(sig, (env * swell.max(0.0) * 2000).clip(20, 20000), hpr.clip(0.01, 2.0));
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_formantFilter, { |inBus=0, outBus=0, formant=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var f = (formant % 8) + 1;
	sig = Formlet.ar(sig, f * 200, ((f % 5) + 1) / 1000, (f * 1.5) / 600).tanh;
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_spinPan, { |inBus=0, outBus=0, spin=1.0, segmentDur=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	var r = spin.max(0.01) / segmentDur.max(0.001);
	sig = sig * [
		FSinOsc.kr(r / 2, iphase: 1, mul: 0.5, add: 0.5),
		FSinOsc.kr(r / 2, iphase: 3, mul: 0.5, add: 0.5)
	];
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_wavesShapeDistortion, { |inBus=0, outBus=0, shape=1.0, mix=1.0, gain=1.0|
	var dry = In.ar(inBus, 2);
	var sig = dry;
	sig = (sig * (shape.max(0.0) * 50)).fold2(1).distort / 5;
	sig = sig * gain.max(0.0);
	sig = SelectX.ar(mix.clip(0, 1), [dry, sig]);
	ReplaceOut.ar(outBus, sig);
}).writeDefFile(outputDir);

"All FoxDot-adapted synthdefs compiled to: %".format(outputDir).postln;
)
