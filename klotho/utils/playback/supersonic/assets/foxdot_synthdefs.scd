(
var outputDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
outputDir.mkdir;

SynthDef(\fd_ambi, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, filter;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = freq + fmod;
			freq = freq + ( (XLine.kr(freq * rate, freq + LFNoise2.ar(4, mul:1), sus))  * SinOsc.ar(freq + LFNoise2.ar(4, mul:2)));
			osc=SinOsc.ar(freq + Rand(0.99,1.01), phase:Rand(0,2));
			env = 1;
			filter = BHiPass.ar(osc, 200);
			osc = osc * env * 0.25;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_angel, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, filter;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod];
			amp=(amp * 2);
			freq = freq * [1, 1.01];
			osc = Ringz.ar(ClipNoise.ar(0.001).dup / 2, freq * 3);
			osc = RHPF.ar(osc, freq * 2.5, rq);
			env = 1;
			osc = Mix(osc) * env * amp;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_arpy, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 2);
	amp=(amp * 2);
	freq=(freq + [0, 0.5]);
	osc=LPF.ar(Impulse.ar(freq), 3000);
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: (sus * 0.25),level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_bass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 4);
	amp=(amp * 0.8);
	osc=((LFTri.ar(freq, mul: amp) + VarSaw.ar(freq, width: (rate / 10), mul: amp)) + SinOscFB.ar(freq, mul: (amp / 2)));
	env=EnvGen.ar(Env.perc(attackTime: 0.02,releaseTime: sus,level: amp,curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_bell, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, decayScale=1, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	decayScale = Lag.kr(decayScale.max(0.1), \decayScaleLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 4);
	osc=(Klank.ar(`[[0.501, 1, 0.7, 2.002, 3, 9.6, 2.49, 11, 2.571, 3.05, 6.242, 12.49, 13, 16, 24], [0.002, 0.1, 0.001, 0.008, 0.02, 0.004, 0.02, 0.04, 0.02, 0.005, 0.05, 0.05, 0.02, 0.03, 0.04], [1.2, 1.2, 1.2, 0.9, 0.9, 0.9, 0.25, 0.25, 0.25, 0.14, 0.14, 0.14, 0.07, 0.07, 0.07]], Impulse.ar(0.01), freq, 0, (4 * decayScale)) * amp);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_blip, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp + 1e-05);
	freq=(freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	freq=(freq * 2);
	osc=((LFCub.ar((freq * 1.002), iphase: 1.5) + (LFTri.ar(freq, iphase: Line.ar(2, 0, 0, 2)) * 0.3)) * Blip.ar((freq / 2), rate));
	osc=((osc * XLine.ar(amp, (amp / 10000), (sus * 2))) * 0.3);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_brass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = freq + fmod;
	rate=Lag.kr(freq, rate);
	osc=(Saw.ar(rate, 0.4) + Saw.ar((rate + LFNoise2.ar(1).range(0.5, 1.1)), 0.4));
	osc=(osc + Resonz.ar(osc, (freq * XLine.ar(1, 5, 0.13)), 1));
	osc=BPF.ar(osc, (freq * 2.5), 0.3);
	osc=RLPF.ar(osc, 1300, 0.78);
	env=EnvGen.ar(Env.perc(level: amp,curve: 0,attackTime: 0.01,releaseTime: sus), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_bug, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 5);
	freq=(freq * [1, 1.0001]);
	osc=(Pulse.ar(freq, width: [0.09, 0.16, 0.25]) * SinOsc.ar((rate * 4)));
	env=EnvGen.ar(Env.perc(attackTime: (sus * 1.5),releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_charm, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq + [0, 2]);
	freq=(freq * [1, 2]);
	osc=(SinOsc.ar(freq, mul: (amp / 4)) + VarSaw.ar((freq * 8), 10, mul: (amp / 8)));
	osc=LPF.ar(osc, SinOsc.ar(Line.ar(1, (rate * 4), (sus / 8)), 0, (freq * 2), ((freq * 2) + 10)));
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_creep, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 4);
	osc=PMOsc.ar(freq, (freq * 2), 10);
	env=EnvGen.ar(Env(times: [sus, 0.001],levels: [0.0001, amp, 0],curve: 'exp'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_crunch, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 0.5);
	osc=LFNoise0.ar(((Crackle.kr(1.95) * freq) * 15), mul: amp);
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: 0.1,level: (amp / 4),curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_dab, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=(HPF.ar(Saw.ar((freq / 4), mul: (amp / 2)), 2000) + VarSaw.ar((freq / 4), mul: amp, width: EnvGen.ar(Env.perc(attackTime: (sus / 20),releaseTime: (sus / 4),level: 0.5,curve: -5), doneAction: 0)));
	env=EnvGen.ar(Env(times: [(sus * 0.25), (sus * 1)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_dbass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod] * Line.ar(Rand(0.5,1.5),1,0.02);
			freq=(freq / 4);
			amp=(amp * 0.8);
			osc=( VarSaw.ar(freq, width: LFTri.ar((0.5 * rate)/sus, iphase:0.9, add:0.8, mul: 0.2), mul: amp));
			env=EnvGen.ar(Env([0,1,0.8,0.8,0], [0.02, 0.01, sus/2, sus/2]), doneAction: 0);
			osc=(osc * env);
			osc = Mix(osc) * 0.5;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_dirt, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 4);
	amp=(amp / 2);
	osc=((LFSaw.ar(freq, mul: amp) + VarSaw.ar((freq + 1), width: 0.85, mul: amp)) + SinOscFB.ar((freq - 1), mul: (amp / 2)));
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_donk, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=((freq / 2) + [0, 2]);
	amp=(amp / 1.25);
	osc=Ringz.ar((Impulse.ar(0, phase: rate) / (rate + 1)), freq, sus, amp);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_donk1, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = freq + fmod;
	freq = freq * SinOsc.kr(fdVRate.max(0.01), mul: fdVDepth).midiratio;
	amp=(amp * 9);
	freq=(freq / 4);
	osc=Ringz.ar(Impulse.ar(0), [freq, (freq + 2)], sus, amp);
	osc=osc.tanh;
	osc = osc * [min(1, (1-pan)/2), min(1, (pan+1)/2)];
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_donk2, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = freq + fmod;
	freq = freq * SinOsc.kr(fdVRate.max(0.01), mul: fdVDepth).midiratio;
	amp=(amp * 9);
	freq=(freq / 4);
	osc=Ringz.ar(Impulse.ar(0), [freq, (freq + 2)], sus, amp);
	osc = osc * [min(1, (1-pan)/2), min(1, (pan+1)/2)];
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_dub, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 4);
	amp=(amp * 2);
	osc=(LFTri.ar(freq, mul: amp) + SinOscFB.ar(freq, mul: amp));
	env=EnvGen.ar(Env.sine(dur: sus,level: amp), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_feel, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	sus=(sus * 1.5);
	amp=(amp / 3);
	freq=(freq * [1, 1.005]);
	osc=Klank.ar(`[[1, 2, 3, (3 + ((rate - 1) / 10))], [1, 1, 1, 1], [2, 2, 2, 2]], (Impulse.ar(0.0005) * Saw.ar(freq, add: 1)), freq);
	env=EnvGen.ar(Env(times: (sus * 2),levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_fuzz, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 2);
	amp=(amp / 6);
	osc=LFSaw.ar(LFSaw.kr(freq, 0, freq, (freq * 2)));
	env=EnvGen.ar(Env(times: [(sus * 0.8), 0.01],levels: [(amp * 1), (amp * 1), (amp * 0.01)],curve: 'step'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_glass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	sus=(sus * 1.5);
	amp=(amp * 1.5);
	freq=(freq * [1, (1 + (0.005 * rate))]);
	osc=Klank.ar(`[[2, 4, 9, 16], [1, 1, 1, 1], [2, 2, 2, 2]], (PinkNoise.ar(0.0005).dup * SinOsc.ar((freq / 4), add: 1, mul: 0.5)), freq);
	env = 1;
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_gong, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 2.5);
	freq=(freq * 2);
	osc=(Klank.ar(`[[0.501, 1, 0.8, 2.002, 3, 9.6, 2.49, 11, 2.571, 3.05, 6.242, 12.49, 13, 16, 24], [0.002, 0.02, 0.001, 0.008, 0.02, 0.004, 0.02, 0.04, 0.02, 0.005, 0.05, 0.05, 0.02, 0.03, 0.04], [1.2, 1.2, 1.2, 0.9, 0.9, 0.9, 0.25, 0.25, 0.25, 0.14, 0.14, 0.14, 0.07, 0.07, 0.07]], SinOscFB.ar(20, 0, 10), freq, (freq * rate), 4) * amp);
	osc=HPF.ar(osc, 440);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_growl, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	sus=(sus * 1.5);
	osc=(SinOsc.ar((freq + SinOsc.kr(0.5, add: 1, mul: 2)), mul: amp) * Saw.ar(((sus / 1.5) * 32)));
	env=EnvGen.ar(Env(times: [(sus / 2), (sus / 2)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_jbass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 4);
	amp=(amp * 0.8);
	osc=LFTri.ar(freq, mul: amp);
	env=EnvGen.ar(Env([0, peakLevel, level, level, 0], [attackTime, decayTime, max((attackTime + decayTime + releaseTime), sus - (attackTime + decayTime + releaseTime)), releaseTime], curve:\sin), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_karp, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 0.75);
	osc=LFNoise0.ar((400 + (400 * rate)), amp);
	osc=(osc * XLine.ar(1, 1e-06, (sus * 0.1)));
	freq=((265 / (freq * 0.666)) * 0.005);
	osc=CombL.ar(osc, delaytime: freq, maxdelaytime: 2);
	env=EnvGen.ar(Env(times: [sus],levels: [(amp * 1), (amp * 1)],curve: 'step'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_keys, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod];
			freq = freq * [1, 1.005];
			amp = amp / 4;
			osc = SinOsc.ar(freq + (rate * 100) * XFade2.ar(LFPar.ar(freq * (1/2)), LFTri.ar(freq * 1)), phase: 0.2, mul: 0.8);
			osc = RHPF.ar(osc, 400, 3);
			env = EnvGen.ar(Env([0, 1, 0.9, 0.5, 0],[0.01, 0, 0.5 * sus, 1 * sus]));
			osc = Mix(osc) * env * amp;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_klank, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	sus=(sus * 1.5);
	osc=Klank.ar(`[[1, 2, 3, 4], [1, 1, 1, 1], [2, 2, 2, 2]], ClipNoise.ar(0.0005).dup, freq);
	env=EnvGen.ar(Env(times: (sus * 2),levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_lazer, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq * [1, 1.005]);
	amp=(amp * 0.1);
	osc=(VarSaw.ar(freq, width: ((rate - 1) / 4)) + LFSaw.ar(LFNoise0.ar((rate * 20), add: (freq * Pulse.ar(((rate - 2) + 0.1), add: 1)), mul: 0.5)));
	env=EnvGen.ar(Env.perc(attackTime: 0.1,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_longsaw, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4)|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = freq + fmod;
	amp=(amp / 8);
	osc=Saw.ar(freq);
	osc=(osc * amp);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_marimba, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=Klank.ar(`[[0.5, 1, 4, 9], [0.5, 1, 1, 1], [1, 1, 1, 1]], PinkNoise.ar([0.007, 0.007]), freq, [0, 2]);
	sus=1;
	env=EnvGen.ar(Env.perc(attackTime: 0.001,releaseTime: sus,level: amp,curve: -6), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_noise, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq * 2);
	osc=LFNoise0.ar(freq, amp);
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_nylon, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=(LFPulse.ar(freq, 0.5, (0.33 * rate), 0.25) + LFPar.ar((freq + 0.5), 1, 0.1, 0.25));
	env=EnvGen.ar(Env.perc(attackTime: 0.000125,releaseTime: (sus * 3),level: amp,curve: -4), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_orient, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=(LFPulse.ar(freq, 0.5, 0.25, 0.25) + LFPulse.ar(freq, 1, 0.1, 0.25));
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_pads, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, filter;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod];
			amp=(amp * 2);
			freq = freq * [1, 1.01];
			osc = SinOsc.ar(Line.kr(freq * 4, freq, 0.01) + (Line.kr(10, (freq * 2), sus) * Pulse.ar(freq * rate, width: SinOsc.kr(0.225/sus))), mul:0.5);
			env = 1;
			osc = RHPF.ar(osc, [Line.kr(400, 1000, sus), Line.kr(4000,900,sus)], 0.5);
			osc = osc * env * amp * Line.ar(0.001,1,sus * 0.05);
			osc = Mix(osc) * 0.5;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_pasha, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, lfo;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod];
			lfo = LFPar.kr([1,1.04], mul:0.5);
			osc = Pulse.ar(freq, lfo);
			env = EnvGen.ar(Env([0,1,0.5,0.2,0], [0, 0.01, sus / 1.5, sus / 1.5], curve:'cub'), doneAction:3);
			osc = osc * env * amp;
			osc = Mix(osc) * 0.25;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_piano, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 0.7);
	osc=MdaPiano.ar((freq[0]), vel: (40 + (amp * 60)), decay: (sus / 4));
	env=EnvGen.ar(Env(times: [sus],levels: [(amp * 1), (amp * 1)],curve: 'step'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_pluck, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp + 1e-05);
	freq=(freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	osc=((SinOsc.ar((freq * 1.002), phase: VarSaw.ar(freq, width: Line.ar(1, 0.2, 2))) * 0.3) + (SinOsc.ar(freq, phase: VarSaw.ar(freq, width: Line.ar(1, 0.2, 2))) * 0.3));
	osc=((osc * XLine.kr(amp, (amp / 10000), (sus * 4), doneAction: 2)) * 0.3);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_prophet, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, lforate=6, lfowidth=0.5, cutoff=1200, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var lfo, pulse, filter, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	lforate = Lag.kr(lforate.max(0.01), \lforateLag.kr(0.1).max(0.0));
	lfowidth = Lag.kr(lfowidth.clip(0.0, 1.0), \lfowidthLag.kr(0.1).max(0.0));
	cutoff = Lag.kr(cutoff.max(20.0), \cutoffLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

			// Amp is way too much for foxdot
			amp = amp * 0.1;
			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
			freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = freq + [0, fmod];
			lfo = LFTri.kr(lforate * [1, 1.01], Rand(0, 2.0)!2);
			pulse = Pulse.ar(freq * [1, 1.01], lfo * lfowidth + 0.5);
			filter = RLPF.ar(pulse, cutoff, rq);
			filter = BHiPass.ar(filter, 200);
			env = EnvGen.ar(Env([0,1,0.8,0.8,0], [0.01, 0, sus, sus]), doneAction:3);
			Out.ar(out, (Pan2.ar(Mix(filter) * env * amp * 0.5, pan)) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_pulse, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 8);
	osc=Pulse.ar(freq);
	osc=(osc * amp);
	env=EnvGen.ar(Env(times: [0.01, (sus - 0.01), 0.01],levels: [0, 1, 1, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_quin, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq * [1, 1.01]);
	osc=(Klank.ar(`[[1, 2, 4, 2], [100, 50, 0, 10], [1, 5, 0, 1]], Impulse.ar(freq).dup, freq) / 5000);
	osc=(osc * LFSaw.ar((freq * (1 + rate))));
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 1), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_rave, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=Gendy1.ar((rate - 1), mul: (amp / 2), minfreq: freq, maxfreq: (freq * 2));
	env = 1;
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_razz, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq + [0, 1]);
	rate=Lag.ar(K2A.ar(freq), rate);
	osc=(Saw.ar((rate * [1, 0.5]), [1, 0.3333333333333333]) + Saw.ar((rate + LFNoise2.ar(4).range(0.5, 2.5)), 1));
	osc=BPF.ar(osc, (freq * 2.5), 0.3);
	osc=RLPF.ar(osc, 1300, 0.78);
	env=EnvGen.ar(Env.perc(attackTime: 0.125,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_ripple, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 6);
	osc=(Pulse.ar((freq / 4), 0.2, 0.25) + Pulse.ar((freq + 1), 0.5, 0.5));
	osc=(osc * SinOsc.ar((rate / sus), 0, 0.5, 1));
	env=EnvGen.ar(Env(times: [(0.55 * sus), (0.55 * sus)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_saw, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 8);
	osc=Saw.ar(freq);
	osc=(osc * amp);
	env=EnvGen.ar(Env(times: [0.01, (sus - 0.01), 0.01],levels: [0, 1, 1, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_sawbass, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, cutoff=1200, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc1, osc2, filter, filter2, env, filterenv, ab;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	cutoff = Lag.kr(cutoff.max(20.0), \cutoffLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

			amp = amp * 0.2;
			freq = VarLag.kr((freq / 4).max(0.001), portamento.max(0.0), warp: \exp);
			freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = freq + fmod;
			osc1 = Saw.ar(freq);
			osc2 = Mix(Saw.ar(freq * [0.25,1,1.5], [0.5,0.4,0.1]));
			filterenv = EnvGen.ar(Env.adsr(0.0, 0.5, 0.2, sus), 1, doneAction: 2);
			filter =  RLPF.ar(osc1 + osc2, cutoff * filterenv + 100, rq);
			ab = abs(filter);
			filter2 = (filter * (ab + 2) / (filter ** 2 + 1 * ab + 1));
			filter2 = BLowShelf.ar(filter2, 300, 1.0, -12);
			filter2 = BPeakEQ.ar(filter2, 1600, 1.0, -6);
			//env = EnvGen.ar(Env.adsr(0.01, 0.0, sus / 2, 0.05), 1, doneAction:3);
			env = EnvGen.ar(Env([0,1,0.8,0.8,0], [0.01, 0, sus, 0.05]), doneAction:3);
			Out.ar(out, (Pan2.ar((filter + filter2) * env * amp, pan)) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_scatter, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=((Saw.ar(freq, mul: (amp / 8)) + VarSaw.ar((freq + [2, 1]), mul: (amp / 8))) * LFNoise0.ar(rate));
	env=EnvGen.ar(Env.linen(attackTime: 0.01,releaseTime: (sus / 2),level: (sus / 2),curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_scrap, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, body;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
	freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = freq + fmod;
	body = WhiteNoise.ar(1) + Crackle.ar(1.75);
	body = BPF.ar(body, (freq * [1, 1.5]).clip(40, 16000), rq.clip(0.05, 1.0));
	env = EnvGen.ar(Env.perc(0.001, sus.max(0.001), amp, -4), doneAction: 0);
	osc = Mix(body) * env;
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_scratch, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 4);
	freq=(freq * Crackle.ar(1.5));
	osc=SinOsc.ar((freq * SinOsc.kr((fdVRate + rate.abs).max(0.01), mul: (fdVDepth + 0.008)).midiratio), mul: amp);
	env=EnvGen.ar(Env(times: [(sus / 2), (sus / 2)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_sinepad, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 1.5);
	freq=(freq + [0, 2]);
	osc=SinOsc.ar(freq, mul: amp);
	osc=HPF.ar(osc, 1000);
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_siren, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = freq + fmod;
	freq = freq * SinOsc.kr(fdVRate.max(0.01), mul: fdVDepth).midiratio;
	amp=(amp * 0.1);
	osc=(VarSaw.ar([freq, (freq * 1.005)], width: ((rate - 1) / 4)) + LFSaw.ar(LFNoise0.ar((rate * 20), mul: 0.5, add: (freq * Pulse.ar(((rate - 2) + 0.1), add: 1)))));
	env=EnvGen.ar(Env.perc(level: amp,curve: 0,attackTime: 0.1,releaseTime: sus), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_sitar, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp * 0.75);
	sus=(sus * 4);
	osc=LFNoise0.ar([8400, 8500], amp);
	osc=(osc * XLine.ar(1, 1e-06, (sus * 0.1)));
	freq=((265 / (freq * [0.666, 0.669])) * 0.005);
	osc=CombL.ar(osc, delaytime: freq, maxdelaytime: 2);
	env=EnvGen.ar(Env(times: [sus],levels: [(amp * 1), (amp * 1)],curve: 'step'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_snick, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	osc=(LFPar.ar(freq, mul: 1) * Blip.ar(((rate + 1) * 4)));
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_soft, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 2);
	amp=(amp / (200 * (1 + rate)));
	osc=Klank.ar(`[[7, 5, 3, 1], [8, 4, 2, 1], [2, 4, 8, 16]], LFNoise0.ar((rate / sus)), freq);
	env=EnvGen.ar(Env(times: sus,levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_soprano, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	sus=(sus * 1.75);
	amp=(amp / 2);
	freq = freq * SinOsc.kr((fdVRate + rate + 4).max(0.01), mul: fdVDepth).midiratio;
	osc=(SinOsc.ar((freq * 3), mul: amp) + SinOscFB.ar((freq * 3), mul: (amp / 2)));
	env=EnvGen.ar(Env(times: [(sus / 2), (sus / 2)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_space, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1|
	var osc, env, filter;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

			freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
			freq = [freq, freq+fmod];
			amp=(amp * 2);
			freq = freq * [1, 1.01];
			osc = Ringz.ar(ClipNoise.ar(0.001).dup / 2 + Impulse.ar(0.01, mul:0.02 * rate,), freq * 3);
			osc = RHPF.ar(osc, freq * 2.5, rq);
			env = 1;
			osc = Mix(osc) * env * amp;
			osc = Pan2.ar(osc, pan);
			Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_spark, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp + 1e-05);
	freq=(freq + [0, LFNoise2.ar(50).range(-2, 2)]);
	osc=((LFSaw.ar((freq * 1.002), iphase: Saw.ar(0.1)) * 0.3) + (LFSaw.ar(freq, iphase: Saw.ar(0.1)) * 0.3));
	osc=(((osc * Line.ar(amp, (amp / 10000), (sus * 1.5))) * 0.3) * Line.ar(0.01, 1, (sus * 0.033)));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_spick, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	freq = freq + fmod;
	freq = freq * SinOsc.kr(fdVRate.max(0.01), mul: fdVDepth).midiratio;
	amp=(amp / 4);
	sus=(sus * 1.25);
	osc=(LFPulse.ar(freq).distort + Impulse.ar((freq + 1)).tan);
	env=EnvGen.ar(Env.perc(level: amp,curve: 0,attackTime: 0.1,releaseTime: sus), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_squish, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 4);
	osc=Ringz.ar(Pulse.ar((4 * rate)), freq, sus, amp);
	osc=(osc * XLine.ar(0.5, 1e-06, sus, doneAction: 2));
	osc=osc.cos;
	amp=(amp * 4);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_star, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=((amp * 2) + 1e-05);
	freq=(freq / 2);
	osc=((LFSaw.ar((freq * 1.002), iphase: VarSaw.kr(freq, width: Line.kr(1, 0.2, sus))) * 0.3) + (LFSaw.ar(((freq + LFNoise2.ar(50).range(-2, 2)) + 2), iphase: VarSaw.kr((freq + 2), width: Line.kr(1, 0.2, sus))) * 0.3));
	osc=((osc * XLine.ar(amp, (amp / 10000), (sus * 3), doneAction: 2)) * Line.ar(0.01, 0.5, 0.07));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_swell, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 4);
	freq=(freq + [0, 1]);
	freq=(freq * [1, 0.5]);
	osc=VarSaw.ar(freq, width: SinOsc.ar((rate / ((2 * sus) / 1.25)), add: 0.5, mul: [0.5, 0.5]), mul: [1, 0.5]);
	env=EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_twang, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq / 8);
	freq=(freq + [0, 2]);
	osc=LPF.ar(Impulse.ar(freq, 0.1), 4000);
	osc=(EnvGen.ar(Env.perc(attackTime: 0.01,releaseTime: sus,level: amp,curve: 0), doneAction: 0) * CombL.ar(osc, delaytime: (rate / (freq * 8)), maxdelaytime: 0.25));
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_varsaw, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		gate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	freq=(freq * [1, 1.005]);
	osc=VarSaw.ar(freq, mul: (amp / 4), width: rate);
	env=EnvGen.ar(Env(times: [(sus / 2), (sus / 2)],levels: [0, amp, 0],curve: 'lin'), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_viola, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 2);
	osc=PMOsc.ar(freq, (freq * SinOsc.kr(fdVRate.max(0.01), mul: (fdVDepth + 0.008)).midiratio), 10, mul: (amp / 2));
	env=EnvGen.ar(Env.perc(attackTime: (0.25 * sus),releaseTime: (0.75 * sus),level: amp,curve: 0), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_zap, { |out=0, freq=440, amp=1, gate=1, pan=0, fmod=0, rate=0, rq=0.5, portamento=0.08, vibRate=5, vibDepth=0, attackTime=0.01, decayTime=0.1, sustainLevel=0.7, releaseTime=0.2, peakLevel=1.0, attackCurve=(-4), decayCurve=(-2), releaseCurve=(-4), sus=1, blur=1, level=0.8|
	var osc, env;
	var fdEnv, fdAmp, fdPan, fdVRate, fdVDepth, fdAutoGate;
	fdAmp = Lag.kr(amp, \ampLag.kr(0.1).max(0.0));
	fdPan = Lag.kr(pan, \panLag.kr(0.1).max(0.0));
	fdVRate = Lag.kr(vibRate.max(0.01), \vibRateLag.kr(0.1).max(0.0));
	fdVDepth = Lag.kr(vibDepth, \vibDepthLag.kr(0.1).max(0.0));
	fmod = Lag.kr(fmod, \fmodLag.kr(0.1).max(0.0));
	rate = Lag.kr(rate, \rateLag.kr(0.1).max(0.0));
	rq = Lag.kr(rq.clip(0.001, 2.0), \rqLag.kr(0.1).max(0.0));
	amp = fdAmp;
	pan = fdPan;
	fdAutoGate = gate * EnvGen.kr(Env([1, 1, 0], [sus.max(0.001), 0.001], \lin));
	fdEnv = EnvGen.kr(
		Env([0, peakLevel, sustainLevel * peakLevel, 0], [attackTime, decayTime, releaseTime], [attackCurve, decayCurve, releaseCurve], 2),
		fdAutoGate,
		doneAction: 2
	);

	sus = sus * blur;
	freq = VarLag.kr(freq.max(0.001), portamento.max(0.0), warp: \exp);
		freq = freq * SinOsc.kr(fdVRate, mul: fdVDepth).midiratio;
	freq = [freq, freq+fmod];
	amp=(amp / 10);
	osc=(Saw.ar(((freq * [1, 1.01]) + LFNoise2.ar(50).range(-2, 2))) + VarSaw.ar((freq + LFNoise2.ar(50).range(-2, 2)), 1));
	env=EnvGen.ar(Env.perc(attackTime: 0.025,releaseTime: sus,level: amp,curve: -10), doneAction: 0);
	osc=(osc * env);
	osc = Mix(osc) * 0.5;
	osc = Pan2.ar(osc, pan);
		Out.ar(out, (osc) * fdEnv);
}).writeDefFile(outputDir);

SynthDef(\fd_reverb, { |inBus=0, outBus=0, room=0.5, mix=0.3, damp=0.5, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = FreeVerb.ar(sig, Lag.kr(mix.clip(0, 1), 0.1), Lag.kr(room.clip(0, 1), 0.1), Lag.kr(damp.clip(0, 1), 0.1));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_combDelay, { |inBus=0, outBus=0, echo=0.5, beatDur=1.0, echoTime=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var d = Lag.kr(echo.max(0.0), 0.1) * Lag.kr(beatDur.max(0.001), 0.1);
    var t = Lag.kr(echoTime.max(0.0), 0.1) * Lag.kr(beatDur.max(0.001), 0.1);
    sig = sig + CombL.ar(sig, maxdelaytime: (2 * Lag.kr(beatDur.max(0.001), 0.1)).max(d + 0.001), delaytime: d.max(0.001), decaytime: t);
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_distortion, { |inBus=0, outBus=0, dist=0.5, gain=1.0|
    var sig = In.ar(inBus, 2);
    var dry = sig;
    sig = CrossoverDistortion.ar(sig, amp: 0.2, smooth: 0.01);
    sig = sig + (0.1 * Lag.kr(dist.clip(0, 1), 0.1) * DynKlank.ar(
        `[[60, 61, 240, 3000 + SinOsc.ar(62, mul: 100)], nil, [0.1, 0.1, 0.05, 0.01]], sig
    ));
    sig = (sig.cubed * 8).softclip * 0.5;
    sig = SelectX.ar(Lag.kr(dist.clip(0, 1), 0.1), [dry, sig]);
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_overdriveDistortion, { |inBus=0, outBus=0, drive=0.4, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = (sig * (Lag.kr(drive.max(0.0), 0.1) * 50)).clip(0, 0.2).fold2(2);
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_bitcrush, { |inBus=0, outBus=0, bits=8, crush=4, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = Decimator.ar(sig, rate: (44100 / Lag.kr(crush.max(1), 0.1)).max(100), bits: Lag.kr(bits.clip(1, 24), 0.1));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_chop, { |inBus=0, outBus=0, chop=4.0, sus=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var rate = (Lag.kr(chop.max(0.01), 0.1) / Lag.kr(sus.max(0.001), 0.1)).max(0.01);
    sig = sig * LFPulse.kr(rate, add: 0.01);
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_tremolo, { |inBus=0, outBus=0, tremolo=4.0, beatDur=1.0, depth=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var rate = (Lag.kr(tremolo.max(0.01), 0.1) / Lag.kr(beatDur.max(0.001), 0.1)).max(0.01);
    var d = Lag.kr(depth.clip(0, 1), 0.1);
    sig = sig * SinOsc.kr(rate, mul: d * 0.5, add: 1 - (d * 0.5));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_highPassFilter, { |inBus=0, outBus=0, hpf=200, hpr=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = RHPF.ar(sig, Lag.kr(hpf.clip(20, 20000), 0.1), Lag.kr(hpr.clip(0.01, 2.0), 0.1));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_lowPassFilter, { |inBus=0, outBus=0, lpf=1200, lpr=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = RLPF.ar(sig, Lag.kr(lpf.clip(20, 20000), 0.1), Lag.kr(lpr.clip(0.01, 2.0), 0.1));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_bandPassFilter, { |inBus=0, outBus=0, bpf=1200, bpr=0.6, bpnoise=2.0, sus=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var n = Lag.kr(bpnoise.max(0.01), 0.1) / Lag.kr(sus.max(0.001), 0.1);
    var f = LFNoise1.kr(n).exprange((Lag.kr(bpf.clip(40, 18000), 0.1) * 0.5).max(20), (Lag.kr(bpf.clip(40, 18000), 0.1) * 2).min(20000));
    var r = LFNoise1.kr(n).exprange((Lag.kr(bpr.clip(0.01, 2.0), 0.1) * 0.5).max(0.01), (Lag.kr(bpr.clip(0.01, 2.0), 0.1) * 2).min(2.0));
    sig = BPF.ar(sig, f, r);
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);





SynthDef(\fd_filterSwell, { |inBus=0, outBus=0, swell=1.0, sus=1.0, hpr=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var env = EnvGen.kr(Env([0, 1, 0], [sus * 0.25, sus * 0.25], \sin));
    sig = RHPF.ar(sig, (env * Lag.kr(swell.max(0.0), 0.1) * 2000).clip(20, 20000), Lag.kr(hpr.clip(0.01, 2.0), 0.1));
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

SynthDef(\fd_formantFilter, { |inBus=0, outBus=0, formant=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var f = (Lag.kr(formant, 0.1) % 8) + 1;
    sig = Formlet.ar(sig, f * 200, ((f % 5) + 1) / 1000, (f * 1.5) / 600).tanh;
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);







SynthDef(\fd_spinPan, { |inBus=0, outBus=0, spin=1.0, sus=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    var r = Lag.kr(spin.max(0.01), 0.1) / Lag.kr(sus.max(0.001), 0.1);
    sig = sig * [
        FSinOsc.kr(r / 2, iphase: 1, mul: 0.5, add: 0.5),
        FSinOsc.kr(r / 2, iphase: 3, mul: 0.5, add: 0.5)
    ];
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);



SynthDef(\fd_wavesShapeDistortion, { |inBus=0, outBus=0, shape=1.0, gain=1.0|
    var sig = In.ar(inBus, 2);
    sig = (sig * (Lag.kr(shape.max(0.0), 0.1) * 50)).fold2(1).distort / 5;
    sig = sig * Lag.kr(gain.max(0.0), 0.1);
    ReplaceOut.ar(inBus, sig);
    Out.ar(outBus, sig);
}).writeDefFile(outputDir);

"All FoxDot-adapted synthdefs compiled to: %".format(outputDir).postln;
)