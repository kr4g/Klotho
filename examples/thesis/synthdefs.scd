(
var midSides;

midSides = { |snd|
	[snd[0] + snd[1], snd[0] - snd[1]] / sqrt(2);
};

SynthDef(\kick, {
	var snd;
	snd = SinOsc.ar(40 * (Env.perc(0.0, 0.1 * [1, 0.3, 0.1] * 4, curve: -8).ar * [30, 40, 10]).midiratio * [1, 2.1, 3.5]);
	snd = snd * [1, Env.perc(0, 0.03).ar, Env.perc(0, 0.01).ar];
	snd = snd * [0, -10, -20].dbamp;
	snd = snd.sum;
	snd = snd * (1 + (3 * Env.perc(0, 0.01).ar));
	snd = snd + HPF.ar(GVerb.ar(snd * -30.dbamp, 10), 300);
	snd = snd * Env([0, 2, 0.5, 0], [0.001, 0.03, 0.2], -4).ar(Done.freeSelf);
	snd = (snd * 1.3).clip2 + ((snd * 3.dbamp).fold2 * -7.dbamp);
	snd = snd * \amp.kr(-15.dbamp);
	OffsetOut.ar(\out.kr(0), snd);
}).add;

SynthDef(\kick2, {
	var snd;
	snd = SinOsc.ar(\freq.kr.linexp(0, 1, 45, 65) * (1 + (3 * Env.perc(0.001, \bend.kr.linexp(0, 1, 0.03, 0.2), curve: -8).ar)));
	snd = snd * (1 + (5 * Env.perc(0, 0.01).ar));
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 8320, 0.3) * Env.perc(0.001, 0.01).ar * -5.dbamp);
	snd = snd * \drive.kr.linexp(0, 1, 0.5, 3);
	snd = snd.tanh;
	snd = snd * -10.dbamp;
	snd = snd * \velocity.kr(1);
	snd = snd * (1 + Env.perc(0, 0.02).ar);
	snd = snd * Env.perc(0.001, \decay.kr.linexp(0, 1, 0.1, 0.7)).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\snare, {
	var snd;
	snd = SinOsc.ar(\freq.kr.linexp(0, 1, 200, 260) * (1 + (0.3 * Env.perc(0.001, 0.01, curve: -8).ar)) * [1, 2.3, 5.6, 8.9]);
	snd = snd * ([1] ++ Env.perc(0, [0.1, 0.03, 0.15] * \clankiness.kr.linexp(0, 1, 1, 3)).ar);
	snd = snd * [0, -8, -5, -15].dbamp * ([1] ++ (\clankiness.kr.linlin(0, 1, 0.1, 1) ! 3));
	snd = snd.sum;
	snd = snd * \velocity.kr(1);
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), \brushFreq.kr.linexp(0, 1, 1200, 3200), 0.3) * Env.perc(0.05, 0.1).ar * -1.dbamp * \drive.kr.linlin(0, 1, -3, 5).dbamp);
	snd = snd * (1 + (10 * Env.perc(0, 0.01).ar * \transient.kr.sqrt));
	snd = (snd * \drive.kr.linlin(0, 1, -2, 5).dbamp).tanh;
	snd = snd * -3.dbamp * \isGhost.kr.linlin(0, 1, 0, -7).dbamp;
	snd = snd * Env.perc(0.001, \decay.kr.linexp(0, 1, 0.09, 0.15) * \isGhost.kr.linexp(0, 1, 1, 0.2), curve: -1).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\hat, {
	var snd;
	snd = SinOsc.ar([1324, 2359, 4530, 4539] * 3) * [3425, 2485, 3492, 4728] * Env.perc(0.002, 0.01).ar;
	snd = SinOsc.ar(([5848, 4378, 4378, 2783] * 1) + snd);
	snd = snd.sum.fold2;
	snd = snd + (Hasher.ar(Sweep.ar));
	snd = snd.tanh;
	snd = RHPF.ar(snd, 3210 * \freq.kr.linexp(0, 1, 0.5, 2), 0.3);
	snd = BRF.ar(snd, 4329, 0.3);
	snd = snd * \velocity.kr(1);
	snd = snd * -16.dbamp;
	snd = snd * (1 + (3 * Env.perc(0, 0.01).ar)) / 3;
	snd = snd * Env.perc(\attack.kr.linexp(0, 1, 0.001, 0.01), \decay.kr.linexp(0, 1, 0.01, 0.05), curve: -1).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\perc, {
	var snd;
	snd = SinOsc.ar(\freq.kr(920) * (1.5 ** [0, 1, 2])).sum;
	snd = snd * (1 + (4 * Env.perc(0, 0.01).ar));
	snd = snd * Env.perc(0.001, 0.1).ar;
	snd = snd + GVerb.ar(snd * -15.dbamp, 10);
	snd = snd * Env.perc(0.0, 1).ar(Done.freeSelf);
	snd = Balance2.ar(snd[0], snd[1], \pan.kr(0));
	snd = snd * \amp.kr(1);
	snd = snd * -16.dbamp;
	Out.ar(\out.kr, snd);
}).add;

SynthDef(\perc2, {
	var snd;
	snd = SinOsc.ar(\freq.kr(420) * (1.5 ** [0, 1, 2])).sum;
	snd = snd * (1 + (4 * Env.perc(0, 0.01).ar));
	snd = snd * Env.perc(0.001, 0.05).ar;
	snd = snd + Latch.ar(GVerb.ar(snd * -15.dbamp, 3), Impulse.ar(8320));
	snd = snd * Env.perc(0.0, 0.5).ar(Done.freeSelf);
	snd = Balance2.ar(snd[0], snd[1], \pan.kr(0));
	snd = snd * \amp.kr(1);
	snd = snd * -16.dbamp;
	Out.ar(\out.kr, snd);
}).add;

SynthDef(\glitch1, {
	var snd;
	snd = Hasher.ar(Sweep.ar(Impulse.ar(7235)) + [0, 1]);
	snd = snd * Env([0, 5, 0.1, 0], [0, 0.1, 1]).ar(Done.freeSelf);
	snd = snd.clip2;
	snd = FreqShift.ar(snd, \freqShift.kr(310));
	snd = HPF.ar(snd, 1120);
	snd = Balance2.ar(snd[0], snd[1], \pan.kr(0));
	snd = snd * \amp.kr(1);
	snd = snd * -15.dbamp;
	Out.ar(\out.kr, snd);
}).add;

SynthDef(\glitch2, {
	var snd;
	snd = SinOsc.ar(60);
	snd = snd - Latch.ar(snd, Impulse.ar(3213 * [1, 1.5]));
	snd = snd * 10.dbamp;
	snd = snd * Env([0, 5, 1, 1, 5, 0], [0.001, 0.001, 0.2, 0.001, 0.001]).ar(Done.freeSelf);
	snd = snd.clip2;
	snd = Balance2.ar(snd[0], snd[1], \pan.kr(0));
	snd = snd * \amp.kr(1);
	snd = snd * -8.dbamp;
	Out.ar(\out.kr, snd);
}).add;

SynthDef(\fx, {
	var snd, trigger;
	trigger = \trigger.tr;
	snd = In.ar(\out.kr, 2);
	snd = midSides.(snd);
	5.do {
		snd = snd + DelayC.ar(snd * -8.dbamp, 0.2, { TRand.kr(1e-3, 20e-3, trigger) } ! 2);
	};
	snd = snd * ((Impulse.ar(TExpRand.ar(100, 16000, T2A.ar(trigger))) * 2) - 1);
	snd = snd.collect { |snd|
		snd = FFT(LocalBuf(1024), snd);
		snd = PV_MagAbove(snd, TRand.kr(0.5, 5, trigger));
		snd = IFFT.ar(snd);
	};
	snd = midSides.(snd);
	snd = BHiShelf.ar(snd, 3201, 1, -5);
	snd = Limiter.ar(snd);
	ReplaceOut.ar(\out.kr, snd);
}).add;

SynthDef(\honk, {
	var snd, dry, wet;
	snd = VarSaw.ar(\freq.kr(440) * (LFNoise2.kr(16) * 0.1).midiratio, width: 0.95);
	snd = MoogFF.ar(snd, XLine.kr(700, 3300, 0.03), 0.6) * 5.dbamp;
	dry = snd * Env([0, 1, 0.7, 0], [0.01, 0.07, 0.06], -4).ar * (1 + (0.3 * Env.perc(0.01, 0.05).ar));
	dry = dry * -5.dbamp;
	dry = dry.tanh;
	wet = snd;
	wet = wet + DelayC.ar(wet, 0.2, LFNoise2.kr(7 ! 2).linlin(-1, 1, 0, 1) * 5e-3);
	wet = MoogFF.ar(wet, 2000) * 3.dbamp;
	wet = wet * Env.perc(0.05, 1.6, curve: -8).ar(Done.freeSelf, \gate.kr(1));
	wet = wet * -12.dbamp;
	snd = dry + wet;
	snd = snd * -6.dbamp;
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\ping, {
	var snd;
	snd = SinOsc.ar(\freq.kr(440));
	snd = snd * Env.perc(0.001, 1.0).ar;
	snd = snd * (1 + Env.perc(0.0, 0.1).ar);
	snd = Latch.ar(snd, Impulse.ar(3000));
	snd = LPF.ar(snd, 3000);
	snd = snd + GVerb.ar(DelayC.ar(snd, 0.2, LFNoise2.ar(3).linlin(-1, 1, 0, 1) * 5e-3) * -5.dbamp, 30, 10);
	snd = snd * Env.perc(0.0, 15.0).ar(Done.freeSelf);
	snd = snd * \amp.kr(-35.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

// Flute SynthDef (updated)
SynthDef(\flute, {
    var snd, freq, vib, breathNoise;
    freq = \freq.kr(1000).varlag(\freqLag.kr(0.1), 1.5) * (1 + (SinOsc.kr(\vibRate.kr(5), 0, \vibDepth.kr(0.02))));
    freq = freq * (Env([0, 0, -1, -1], [3, 1, 3], \sine).ar * \bend.kr(0)).midiratio;
    breathNoise = HPF.ar(PinkNoise.ar, 500) * EnvGen.ar(Env([0, 1, 0.4, 0.2], [0.01, 0.1, 0.4]));
    snd = SinOsc.ar(freq) * (1 + (LFNoise2.ar(60) * \breathiness.kr(0.1)));
    snd = (snd * 0.8) + (breathNoise * 0.2);
    snd = snd * -12.dbamp;
    snd = snd + DelayC.ar(snd * Line.kr(0, 1, 0.1), 0.02, LFNoise2.kr(1).linlin(-1, 1, 0, 0.01));
    snd = snd * Env.asr(0.1, 1.0, \decay.kr(0.3)).ar(Done.freeSelf, \gate.kr(1));
    snd = Pan2.ar(snd, \pan.kr(0));
    snd = snd * \amp.kr(1).varlag(\ampLag.kr(0.3), 2.5);
    Out.ar(\out.kr(0), snd);
}).add;

// Oboe SynthDef (updated)
SynthDef(\oboe, {
    var snd, freq, vib, harmonics;
    freq = \freq.kr(440).varlag(\freqLag.kr(0.1), 1.5) * (1 + (SinOsc.kr(\vibRate.kr(5.5), 0, \vibDepth.kr(0.015))));
    freq = freq * (Env([0, 0, -0.5, -0.5], [2, 0.5, 2], \sine).ar * \bend.kr(0)).midiratio;
    harmonics = Array.fill(4, {|i| Saw.ar(freq * (i+1)) * (0.7 ** i)});
    snd = Mix(harmonics);
    snd = RLPF.ar(snd, freq * \brightness.kr(8), 0.7);
    snd = snd * -10.dbamp;
    snd = snd * Env.asr(0.05, 1, \decay.kr(0.2)).ar(Done.freeSelf, \gate.kr(1));
    snd = Pan2.ar(snd, \pan.kr(0));
    snd = snd * \amp.kr(1).varlag(\ampLag.kr(0.2), 2);
    Out.ar(\out.kr(0), snd);
}).add;

// Clarinet SynthDef (updated)
SynthDef(\clarinet, {
    var snd, freq, vib, breathNoise;
    freq = \freq.kr(220).varlag(\freqLag.kr(0.1), 1.5) * (1 + (SinOsc.kr(\vibRate.kr(5), 0, \vibDepth.kr(0.01))));
    freq = freq * (Env([0, 0, -0.7, -0.7], [2.5, 0.7, 2.5], \sine).ar * \bend.kr(0)).midiratio;
    breathNoise = LPF.ar(PinkNoise.ar, 2000) * EnvGen.ar(Env([0, 1, 0.3, 0.1], [0.01, 0.1, 0.5]));
    snd = Pulse.ar(freq, \pulseWidth.kr(0.5)) * 0.6 + Pulse.ar(freq * 3, 0.5) * 0.1;
    snd = (snd * 0.9) + (breathNoise * \breathiness.kr(0.1));
    snd = LPF.ar(snd, freq * \brightness.kr(6));
    snd = snd * -8.dbamp;
    snd = snd * Env.asr(0.08, 1, \decay.kr(0.3)).ar(Done.freeSelf, \gate.kr(1));
    snd = Pan2.ar(snd, \pan.kr(0));
    snd = snd * \amp.kr(1).varlag(\ampLag.kr(0.25), 2.2);
    Out.ar(\out.kr(0), snd);
}).add;

// Bassoon SynthDef (updated)
SynthDef(\bassoon, {
    var snd, freq, vib, harmonics;
    freq = \freq.kr(110).varlag(\freqLag.kr(0.15), 1.5) * (1 + (SinOsc.kr(\vibRate.kr(4.5), 0, \vibDepth.kr(0.012))));
    freq = freq * (Env([0, 0, -0.3, -0.3], [3, 1, 3], \sine).ar * \bend.kr(0)).midiratio;
    harmonics = Array.fill(5, {|i| Saw.ar(freq * (i+1)) * (0.6 ** i)});
    snd = Mix(harmonics);
    snd = RLPF.ar(snd, freq * \brightness.kr(4), 0.8);
    snd = snd * -6.dbamp;
    snd = snd * Env.asr(0.1, 1, \decay.kr(0.4)).ar(Done.freeSelf, \gate.kr(1));
    snd = Pan2.ar(snd, \pan.kr(0));
    snd = snd * \amp.kr(1).varlag(\ampLag.kr(0.3), 2.8);
    Out.ar(\out.kr(0), snd);
}).add;

// French Horn SynthDef (updated)
SynthDef(\frenchhorn, {
    var snd, freq, vib;
    freq = \freq.kr(165).varlag(\freqLag.kr(0.12), 1.5) * (1 + (SinOsc.kr(\vibRate.kr(4.8), 0, \vibDepth.kr(0.01))));
    freq = freq * (Env([0, 0, -0.8, -0.8], [2.2, 0.8, 2.2], \sine).ar * \bend.kr(0)).midiratio;
    snd = Saw.ar(freq) * 0.7 + SinOsc.ar(freq) * 0.3;
    snd = BPF.ar(snd, freq * \resonance.kr(2), \q.kr(0.8));
    snd = snd * -7.dbamp;
    snd = snd * Env.asr(0.06, 1, \decay.kr(0.25)).ar(Done.freeSelf, \gate.kr(1));
    snd = Pan2.ar(snd, \pan.kr(0));
    snd = snd * \amp.kr(1).varlag(\ampLag.kr(0.2), 2.3);
    Out.ar(\out.kr(0), snd);
}).add;



SynthDef(\random, {
	var snd, random, randomState;
	randomState = \seed.kr(0);
	random = {
		randomState = Hasher.kr(randomState);
		randomState;
	};
	snd = SinOsc.ar(random.().linexp(-1, 1, 100, 8000)) * 3000 * Env.perc(0.01, random.()).ar.linexp(-1, 1, 0.03, 0.3);
	snd = SinOsc.ar(random.().linexp(-1, 1, 100, 8000) + snd) * 8000 * Env.perc(0.01, random.()).ar.linexp(-1, 1, 0.03, 0.3);
	snd = SinOsc.ar(random.().linexp(-1, 1, 1200, 3000) + snd);
	snd = snd * Env.linen(0.001, \duration.kr(0.03), 0.01).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * \amp.kr(1) * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;


)
