(
var lfo1;

lfo1 = { |rate|
	(LFNoise2.ar(rate) + (LFNoise2.ar(rate * 3) / 3) + TRand.ar(-1, 1, Dust.ar(rate))).wrap2
};

SynthDef(\a1, {
	var snd, duration;
	duration = \duration.kr(2.0);
	snd = {
		SinOsc.ar((ExpRand(1000, 8000) * XLine.kr(1, 0.7, ExpRand(0.3, 2.0)) * XLine.kr(8, 1, 0.01)) + (SinOsc.ar(ExpRand(1000, 8000)) * Rand(300, 8000)))
	} ! 20;
	snd = Splay.ar(snd);
	snd = snd + Splay.ar({
		SinOsc.ar(lfo1.(ExpRand(0.5, 8)).linexp(-1, 1, 500, 16000));
	} ! 5);
	snd = snd * (1 + (5 * Env.perc(0, 0.07).ar));
	snd = (snd * -5.dbamp).clip2;
	snd = snd * Env.linen(0, duration, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(-17.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\a2, {
	var snd, duration, wobble;
	duration = \duration.kr(1.5);
	wobble = BPF.ar(BrownNoise.ar, Env([120, 50, 90, 60].cpsmidi, [2, 1, 1, 1].normalizeSum * duration, curve: -4).ar.midicps * (LFNoise2.kr(3) * 3).midiratio, 0.1) * 20.dbamp * (1 + lfo1.(16).lag(0.02));
	wobble = (wobble * -3.dbamp).tanh;
	wobble = RLPF.ar(wobble, lfo1.(8).lag(0.1).linexp(-1, 1, 100, 8000), 0.5);
	snd = FreqShift.ar(CombC.ar(WhiteNoise.ar, 0.2, 1 / [30, 54, 178, 232], 3.0).sum.tanh, -60) * (1 + lfo1.(16).lag(0.02));
	snd = BPeakEQ.ar(snd, 2400, 0.3, 10);
	snd = snd + PitchShift.ar(snd, 0.2, 1.3);
	snd = snd * -6.dbamp;
	snd = RHPF.ar(snd, LFNoise2.kr(32).linexp(-1, 1, 1000, 16e3), 1.2) * 7.dbamp;
	snd = (snd * (1 + LFNoise2.kr(8))) + (wobble.tanh * 10.dbamp * (1 + LFNoise2.kr(8)));
	snd = LeakDC.ar(snd);
	snd = snd + DelayC.ar(snd, 0.2, SinOsc.ar(1 / 3, [0, pi]).linlin(-1, 1, 0, 1) * 1e-3);
	snd = Limiter.ar(snd * 40.dbamp, 1.0, 0.01);
	snd = snd * Env.linen(0, duration, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(3.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\a3, {
	var snd, duration;
	duration = \duration.kr(1.5);
	snd = 3.collect { SinOsc.ar(LFNoise2.ar(\freq.kr(400)).linexp(-1, 1, 100, 16e3)) * LFNoise2.ar(300).pow(3) };
	snd = Splay.ar(snd);
	snd = (snd * 3).tanh;
	snd = snd * LFPulse.ar(XLine.kr(3, 16, duration), width: 0.7);
	snd = snd + CombC.ar(({ WhiteNoise.ar * (1 + lfo1.(62)) } ! 2) * -15.dbamp * XLine.kr(-10.dbamp, 0.dbamp, duration), 0.1, 1 / 60, 0.3);
	snd = snd * Env.linen(0, duration, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(-10.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\a4, {
	var snd, duration, trigger, wash;
	duration = \duration.kr(1.5);
	trigger = Impulse.ar(0) + Dust.ar(\dustRate.kr(4));
	snd = SinOsc.ar(Env.perc(0.0, 0.3, curve: -4).ar(Done.none, gate: trigger).linexp(0, 1, 40, TExpRand.ar(100, 4000, trigger))) * Env.perc(0.001, 0.3).ar(Done.none, gate: trigger);
	snd = (snd * 2).fold2;
	snd = BPF.ar(snd, [60, 83, 92, 312, 230], 0.5).sum;
	snd = (snd * 1).tanh;
	snd = snd + BPF.ar(DelayC.ar(snd, 0.1, 1e-3), [40, 73, 122, 112, 430], 0.3).sum;
	snd = (snd * 2).tanh;
	snd = LPF.ar(snd, 510 * (1 + (2 * Env.perc(0, 0.1).ar(Done.none, gate: trigger))));
	snd = snd * 10.dbamp;
	snd = Limiter.ar(snd, 1, 0.001) * 5.dbamp;

	wash = { WhiteNoise.ar } ! 2;
	wash = BPF.ar([wash], ((0..20) ** 0.8).normalize.linexp(0, 1, 500, 8000), 0.03);
	wash = wash * (0..20) / 20;
	wash = wash.sum;
	wash = wash * (1 - Env.perc(0.001, 0.1, curve: 4).ar(Done.none, gate: trigger));

	snd = snd + wash;

	snd = snd * Env.linen(0, duration, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(-2.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\a5, {
	var snd, duration, trigger, wash;
	duration = \duration.kr(1.5);

	snd = SinOsc.ar([260, 340, 730, 1220, 2320, 3340]) * Env.perc(0, [1.0, 7.0, 3.0, 1.0, 7.0, 0.1]).ar;
	snd = snd * [0, -5, -7, -10, -10, -11, -12].dbamp;
	snd = snd * (1 + LFNoise2.kr((32 ! 2) ! snd.size));
	snd = snd.sum;
	snd = snd + (HPF.ar({ (PinkNoise.ar * 3.dbamp).pow(2) * 3.dbamp } ! 2, 730) * Env.perc(0, 30.0).ar);
	snd = snd * -10.dbamp + (snd * 10.dbamp).clip2;

	snd = snd * Env.linen(0, duration, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(-17.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\glitch1, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = Hasher.ar(Sweep.ar(Impulse.ar(60)) + [0, 1]);
	snd = FreqShift.ar(snd, 32);
	snd = snd * Env([1, 0, 1], duration * [1, 1].normalizeSum, [-4, 4]).ar;
	snd = snd * Env.linen(0, duration, 0.005, curve: -4).ar(Done.freeSelf);
	snd = snd * -8.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\glitch2, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = Hasher.ar(Sweep.ar(Impulse.ar(42)) + [0, 1]);
	snd = RHPF.ar(snd, XLine.kr(700, 2000, duration), 0.3);
	snd = snd * (1 + (3 * Env.perc(0, 0.01).ar));
	snd = snd * Env.linen(0, duration, 0.005, curve: -4).ar(Done.freeSelf);
	snd = snd * -15.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\glitch3, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = Hasher.ar(Sweep.ar(Impulse.ar(90)) + [0, 1]);
	snd = RLPF.ar(snd, [3210, 1440], 0.3).sum * -5.dbamp;
	snd = (snd * 3).fold2;
	snd = snd * Env([1, 0.5, 1], duration * [1, 1].normalizeSum, [-4, 4]).ar;
	snd = snd * Env.linen(0, duration, 0.005, curve: -4).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * -8.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\glitchRandom, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = Saw.ar(Env({ Rand(0, 1) } ! 3, [0.5, 0.5] * duration).ar.linexp(0, 1, 100, 8000));
	snd = RLPF.ar(snd, ExpRand(1000, 8000) * XLine.ar(1, 0.5, duration), 0.1);
	snd = (snd * 2).fold2;
	snd = Latch.ar(snd, Impulse.ar(ExpRand(3000, 15e3)));
	snd = BPF.ar(snd, (0..20).normalize.linexp(0, 1, ExpRand(100, 200), ExpRand(8000, 16e3)), 0.2).sum;
	snd = snd * (1 + (1 * Env.perc(0, 0.01).ar));
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * Env.linen(0, duration, 0.005, curve: -4).ar(Done.freeSelf);
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\glitchRandom2, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = SinOsc.ar(ExpRand(100, 8000)) * Rand(8000, 16e3);
	snd = SinOsc.ar(ExpRand(1000, 8000) + snd);
	snd = snd * (1 + (1 * Env.perc(0, 0.01).ar));
	snd = snd + PitchShift.ar(snd, ExpRand(0.005, 0.05), ExpRand(1.5, 3));
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * Env.linen(0, duration, 0.005, curve: -4).ar(Done.freeSelf);
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\preScrape, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = Hasher.ar(Sweep.ar);
	snd = CombC.ar(snd, 0.2, 1 / 120) * -8.dbamp;
	snd = FreqShift.ar(snd, \freq.kr(2234));
	snd = HPF.ar(snd, XLine.ar(8e3, 100, duration));
	snd = LPF.ar(snd, XLine.ar(1e3, 16e3, duration));
	snd = snd ! 2;
	snd = snd * \amp.kr(-23.dbamp);
	snd = snd * Env.perc(duration, 0.01, curve: 8).ar(Done.freeSelf);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\delaySnap, {
	var snd, fb;
	snd = Hasher.ar(Sweep.ar) * Env.perc(0.001, 0.1).ar;
	snd = BPF.ar(snd, XLine.ar([8120, 3340], [1000, 2320], 0.02), 0.3).sum;
	snd = snd + CombC.ar(snd, 0.2, 1 / 60, 0.2);
	snd = FreqShift.ar(snd, 742);
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 8120, 0.1) * Env([0, 1, 0, 1, 0], [0.001, 0.01, 0.001, 0.01], curve: -4).ar * 5.dbamp);
	snd = snd.tanh;

	snd = snd + GVerb.ar(snd * -10.dbamp, 20, 4);

	fb = snd + LocalIn.ar(2);
	fb = DelayC.ar(fb, 0.9, [0.5, 0.3]);
	fb = fb * -1.dbamp;
	fb = LPF.ar(fb, 4000);
	fb = HPF.ar(fb, 200);
	fb = fb + PitchShift.ar(fb * -3.dbamp, 0.23, 1.2);
	fb = fb + DelayC.ar(fb.reverse * -10.dbamp, 0.2, [0.04, 0.1]);
	fb = fb.tanh;
	LocalOut.ar(fb);

	snd = snd + fb;
	snd = snd * Env.linen(0, \duration.kr(10), 0.1, curve: -4).ar(Done.freeSelf);

	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\choir, {
	var snd, freq, duration, env;
	freq = \freq.kr(70).lag(\freqLag.kr(0.02));
	duration = \duration.kr(10.0);
	env = Env([0, 1, 1, 0], [\atk.kr(0.1), duration, \rel.kr(0.1)], curve: -4).ar(Done.freeSelf);
	snd = 8.collect {
		var formants, snd;
		formants = [800, 1200, 2420, 4420];
		snd = BPF.ar(
			Pulse.ar(freq * (LFNoise2.kr(8) * 0.3).midiratio * (SinOsc.kr(ExpRand(3, 6)) * 0.3).midiratio, 0.2),
			formants * formants.size.collect { (LFNoise2.kr(3) * 1).midiratio * ExpRand(0.9, 1.2) },
			[0.05, 0.05, 0.05, 0.05],
		);
		snd = snd * [0, -5, -15, -20].dbamp;
		snd = snd.sum;
		snd = snd * 25.dbamp;
		snd = snd * (1 + (0.5 * LFNoise2.ar(8)));
		snd = BLowShelf.ar(snd, 500, 0.3, -5);
		snd = snd.tanh;
		snd = BLowShelf.ar(snd, 500, 0.3, 5);
	};
	snd = Splay.ar(snd);
	snd = snd + ((SinOsc.ar(freq / 2)).tanh * -5.dbamp);
	snd = snd + ((SinOsc.ar(freq)).tanh * -5.dbamp);

	snd = snd * env;
	snd = snd * \amp.kr(-10.dbamp).lag(\ampTime.kr(0));
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\sines, {
	var snd, duration, env;
	duration = \duration.kr(1);
	env = Env.perc(duration, 0.01, curve: 4).ar(Done.freeSelf);

	snd = SinOsc.ar({ ExpRand(100, 8000) } ! 30);
	snd = Splay.ar(snd) * -10.dbamp;

	snd = snd * env;
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\crash, {
	var snd, fb;
	snd = Hasher.ar(Sweep.ar) * Env.perc(0.001, 1.0).ar;
	snd = BPF.ar(snd, XLine.ar([3120, 6340], [1200, 920], 0.02), 0.3).sum;
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 8120, 0.1) * Env([0, 1, 0, 1, 0], [0.001, 0.01, 0.001, 0.01], curve: -4).ar * 5.dbamp);
	snd = snd.tanh;

	snd = snd + GVerb.ar(snd * -10.dbamp, 10, 10);
	snd = snd * (1 + (0.5 * LFNoise2.ar(20 ! 2)));
	snd = snd * (1 + (0.5 * LFNoise2.ar(60 ! 2)));
	snd = snd + PitchShift.ar(snd, 0.23, 2.45);
	snd = snd + PitchShift.ar(snd, 0.13, 3.45);
	snd = snd + GVerb.ar(snd.sum * -10.dbamp, 23, 10);
	snd = snd * -10.dbamp;

	snd = snd * Env.linen(0, \duration.kr(10), 0.1, curve: -4).ar(Done.freeSelf);

	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\chime, {
	var snd, freq;
	freq = \freq.kr(2340);
	snd = SinOsc.ar(freq * ([0.56, 1, 3.034, 6.445] ** (freq / 2000)) * XLine.ar(2, 1, 0.005));
	snd = snd * Env.perc(0, [0.1, 5.3, 0.05, 0.01] * 10 * (1000 / freq)).ar;
	snd = snd * ({ Rand(0, -10).dbamp } ! snd.size);
	snd = snd.sum;
	snd = snd * (1 + (2 * Env.perc(0, 0.05).ar));
	snd = snd * (1 + (0.5 * SinOsc.ar(0.5, [0, pi])));
	snd = snd + (BPF.ar(WhiteNoise.ar, 8320, 0.3) * Env.perc(0, 0.1).ar);
	snd = snd.tanh;
	snd = snd * (1 + (SinOsc.ar(4230) * Env.perc(0.0, 0.5).ar));
	snd = snd + PitchShift.ar(snd * -5.dbamp, 0.03, 1.5);
	snd = snd + PitchShift.ar(snd * -5.dbamp, 0.023, 1.4);
	snd = snd * -10.dbamp;
	snd = snd * (1000 / freq);
	snd = LPF.ar(snd, ExpRand(3000, 8000));
	snd = snd * Rand(-10, 0).dbamp;
	snd = AllpassC.ar(snd, 0.2, 0.01, 0.5);
	snd = snd + GVerb.ar(snd.sum * -5.dbamp, 60, 3);

	snd = snd * Env.perc(0, 10.4).ar(Done.freeSelf);

	snd = snd * \amp.kr(-5.dbamp);

	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\bassDrum, {
	var snd;
	snd = SinOsc.ar(Env.perc(0, [0.4, 0.015, 0.02, 0.03, 0.1], curve: -8).ar.linexp(0,1,50,300) * XLine.ar(1, 0.7, 1) * [1, 2.3, 2.5, 3.2, 3.3]);
	snd = snd * Env.perc([0.001, 0.02, 0.03, 0.01, 0.02], [1.0, 0.5, 0.1, 0.02, 0.03]).ar;
	snd = snd.sum;
	snd = snd ! 2;
	snd = snd * Env.linen(0, 5.0, 1.0, curve: -4).ar(Done.freeSelf);
	snd = (snd * (1 + Env.perc(0, 0.1).ar)).tanh;
	snd = snd + GVerb.ar(snd * -5.dbamp, 60, 3);
	snd = snd.tanh;
	snd = snd * Env.linen(0, 5.0, 1.0, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(-10.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\rumble, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = SinOsc.ar(60 * (LFNoise2.ar(5 ! 12) * 12).midiratio);
	snd = Splay.ar(snd);
	snd = snd.tanh;
	snd = snd + PitchShift.ar(snd * Env([0, 1, 0], [1, 1].normalizeSum * duration, \sin).ar, 0.03, 4);
	snd = snd + PitchShift.ar(snd, 0.013, 2);
	snd = snd + DelayC.ar(snd, 0.2, SinOsc.ar(0.3, [0, pi]).linlin(-1, 1, 0, 1) * 1e-3);
	snd = snd * Line.ar(0, 1, 0.1);
	snd = snd * Env.linen(0, duration, 1.0, curve: -4).ar(Done.freeSelf);
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\syn, {
	var env = EnvGen.kr(Env.perc(0.01, \dur.kr(1), \amp.kr(0.5), -4), doneAction: 2);
	Out.ar(0, SinOsc.ar(\freq.kr(440)) * env);
}).add;

SynthDef(\feedback1, {
	var snd, duration, env, rate;
	rate = \rate.kr(1.0);
	duration = \duration.kr(10.0);
	env = Env([0, 1, 0], [1, 1].normalizeSum * duration, curve: -4).ar(Done.freeSelf);
	snd = SinOsc.ar(\freq.kr(520)) * Env.perc(0.1, 0.2).ar;

	snd = snd + LocalIn.ar(2);
	snd = (snd * 5.dbamp).tanh;
	snd = DelayC.ar(snd, 0.3, 8.collect {
		Rand(0.05, 0.2) + (LFNoise2.ar(0.3 * (1 + env)) * 1e-2 * rate) + (LFNoise2.ar(1 * (1 + env)) * 1e-4 * rate)
	});
	snd = snd * (1 + (0.5 * LFNoise2.ar(1 ! snd.size)));
	snd = Splay.ar(snd);
	snd = snd + PitchShift.ar(snd, [0.1, 0.2], 1.1);
	snd = LeakDC.ar(snd);
	LocalOut.ar(snd.reverse);

	snd = LPF.ar(snd, env.linexp(0, 1, 2000, 8000));

	snd = snd * env;
	snd = snd * \amp.kr(-15.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\feedback2, {
	var snd, duration, env, rate;
	rate = \rate.kr(1.0);
	duration = \duration.kr(10.0);
	env = Env([0, 1, 0], [1, 1].normalizeSum * duration, curve: -4).ar(Done.freeSelf);
	snd = Saw.ar(\freq.kr(60)) * Env.perc(0.1, 0.2).ar;

	snd = snd + LocalIn.ar(2);
	snd = (snd * 5.dbamp).tanh;
	snd = DelayC.ar(snd, 0.3, 8.collect {
		Rand(0.05, 0.2) + (LFNoise2.ar(3 * (1 + env)) * 1e-3 * rate) + (LFNoise2.ar(4 * (1 + env)) * rate * 1e-4)
	});
	snd = BHiShelf.ar(snd, 1320, 0.3, -5);
	snd = snd * (1 + (0.5 * LFNoise2.ar(1 ! snd.size)));
	snd = Splay.ar(snd);
	snd = snd + PitchShift.ar(snd, [0.03, 0.045], 0.5);
	snd = LeakDC.ar(snd);
	LocalOut.ar(snd.reverse);

	snd = LPF.ar(snd, env.linexp(0, 1, 2000, 8000));

	snd = snd * env;
	snd = snd * \amp.kr(-15.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\theremin, {
	var snd;
	snd = SinOsc.ar(\freq.kr(440).cpsmidi.lag(\freqLag.kr(2.0)).midicps * ((SinOsc.ar(5) + LFNoise2.kr(3)) * 0.2).midiratio);
	snd = LeakDC.ar((snd + 0.1).tanh);
	snd = snd ! 2;
	// snd = snd * -20.dbamp;
	// snd = snd * Env.asr(1, 1, 1, curve: \sin).ar(Done.freeSelf, \gate.kr(1));
	snd = snd * Env.linen(\atk.kr(0.1), \dur.kr(1.0), 0.1, curve: -4).ar(Done.freeSelf);
	snd = snd * \amp.kr(0.5).lag(\ampLag.kr(0));
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\organ, {
	var snd, duration;
	duration = \duration.kr(1.0);
	snd = SinOsc.ar(\freq.kr(440) * [1, 2, 4] * (LFNoise2.kr(10 ! 3) * 0.1).midiratio);
	snd = snd * Env.perc(0, [5, 10, 1]).ar;
	snd = snd * [-5, 0, -9].dbamp;
	snd = snd * (1 + (0.3 * LFNoise2.kr(16 ! snd.size)));
	snd = snd.sum;
	snd = LPF.ar(snd, XLine.ar(8000, 100, 3.0));
	snd = snd * Select.ar(Sweep.ar > 0.02, [ToggleFF.ar(Dust.ar(200)), DC.ar(1)]);
	snd = snd + GVerb.ar(snd * -20.dbamp, 10, 3, damping: 0.2);
	snd = snd * Env.linen(0.0, duration, 0.0, curve: -4).ar(Done.freeSelf);
	snd = snd * -24.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\lead, {
	var snd, freq, amp, n, intensity;
	freq = \freq.kr(440).lag(\freqLag.kr(0.02));
	amp = \amp.kr(-25.dbamp).lag(\ampLag.kr(0));
	intensity = LFNoise2.kr(\intenseRate.kr(3).lag(\intenseLag.kr(0.02))).linlin(-1, 1, 0, 1) * Line.kr(0, 1, 10);
	n = (1..32);
	snd = SinOsc.ar(freq * n * (LFNoise2.kr(8 * (1 + intensity)) * 0.5 * intensity).midiratio);
	snd = snd * (n.pow(1.3) * (LFNoise2.kr(1).linexp(-1, 1, 1, 1.1)) + (3 * LFNoise2.ar(intensity.linexp(0, 1, 1, 2)))).cos.pow(10);
	snd = snd * (1 + LFNoise2.ar(3 * n.sqrt));
	snd = snd / n;
	snd = snd.sum;
	snd = LPF.ar(snd, intensity.linexp(0, 1, 1000, 16e3));
	snd = snd * (1 + (LFNoise2.ar(LFNoise2.ar(3).linexp(-1, 1, 1, 16)) * 0.5));
	snd = snd * intensity.linlin(-1, 1, 0.2, 1);
	snd = snd * 10.dbamp;
	snd = snd.tanh;
	snd = PitchShift.ar(snd, 0.3, 0.5) * 10.dbamp;
	snd = snd + GVerb.ar(snd * -10.dbamp, 10, 3, damping: 0.2);
	snd = snd * Env.asr(\atk.kr(0.5), 1.0, \rel.kr(3.0), curve: -4).ar(Done.freeSelf, \gate.kr(1));
	snd = snd * amp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\celeste, {
	var freq = \freq.kr(440);
	var env = EnvGen.kr(Env.perc(0.01, \dur.kr(1), \amp.kr(0.5), -4), doneAction: 2);
	var snd = Mix.fill(5, { |i|
		var baseRatio = [1.0, 2.01, 2.99, 4.01, 4.99].wrapAt(i);
		var randRatio = if(i == 0, baseRatio, baseRatio * Rand(0.99, 1.01));
		var ampScale = if(i == 0, 1, 1 / (i + 1) * Rand(0.9, 1.1));
		SinOsc.ar(freq * (i + 1) * randRatio, 0, env * ampScale)
	});
	Out.ar(0, snd);
}).add;

SynthDef(\glockenspiel, {
	var freq = \freq.kr(440);
	var env = EnvGen.kr(Env.perc(0.01, \dur.kr(1), \amp.kr(0.5), -4), doneAction: 2);
	var tones = Mix.fill(3, { |i|
		var baseRatio = [1.0, 2.56, 4.08].wrapAt(i);
		var randRatio = if(i == 0, baseRatio, baseRatio * Rand(0.99, 1.01));
		var ampScale = if(i == 0, 1, 1 / (i + 1) * Rand(0.9, 1.1));
		SinOsc.ar(freq * (i + 1) * randRatio, 0, env * ampScale)
	});
	Out.ar(0, tones);
}).add;

SynthDef(\vibraphone, {
	var freq = \freq.kr(440);
	var env = EnvGen.kr(Env.perc(0.05, \dur.kr(1), \amp.kr(0.5), -4), doneAction: 2);
	var tones = Mix.fill(4, { |i|
		var baseRatio = [1.0, 1.42, 2.00, 2.92].wrapAt(i);
		var randRatio = if(i == 0, baseRatio, baseRatio * Rand(0.99, 1.01));
		var ampScale = if(i == 0, 1, 1 / (i + 1) * Rand(0.9, 1.1));
		SinOsc.ar(freq * (i + 1) * randRatio, 0, env * ampScale)
	});
	Out.ar(0, tones);
}).add;

SynthDef(\sub, {
	var snd, freq, duration;
	duration = \duration.kr(1);
	freq = \freq.kr(60);
	snd = SinOsc.ar(freq);
	snd = snd.tanh;
	snd = snd ! 2;
	snd = snd * Env.linen(0.001, duration, 0.01, curve: -4).ar(Done.freeSelf, \gate.kr(1));
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\reverseCymbal, {
	var snd, duration;
	duration = \duration.kr(3.0);
	snd = WhiteNoise.ar;
	snd = LeakDC.ar(snd);
	snd = CombC.ar(snd, 0.2, 1 / ExpRand(500, 2000 ! 8), 0.6) * -25.dbamp;
	snd = FreqShift.ar(snd, 534);
	snd = Splay.ar(snd);
	snd = LPF.ar(snd, XLine.ar(300, 16e3, duration));
	snd = snd + PitchShift.ar(snd, 0.03, 1.5);
	snd = snd * -5.dbamp;
	snd = snd * Env.perc(duration, 0.01, curve: 6).ar(Done.freeSelf);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\impact, {
	var snd, duration;
	duration = \duration.kr(3.0);
	snd = SinOsc.ar(Env.perc(0, 0.1).ar.linexp(0, 1, 60, 1000) * XLine.ar(1, 0.5, 3));
	snd = snd * (1 + Env.perc(0, 0.1).ar);
	snd = snd.tanh;
	snd = snd + (BPF.ar(WhiteNoise.ar, 8320, 0.3) * Env.perc(0.05, 0.3).ar * -5.dbamp);
	snd = snd + GVerb.ar(snd * -10.dbamp, 30, 7);
	snd = snd.tanh;
	snd = snd + PitchShift.ar(snd, 0.3, 2);
	snd = snd * -7.dbamp;
	snd = snd * Env.perc(0.001, 7, curve: -4).ar(Done.freeSelf);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\crash2, {
	var snd;
	snd = WhiteNoise.ar;
	snd = LeakDC.ar(snd);
	snd = CombC.ar(snd, 0.2, 1 / ExpRand(500, 2000 ! 20), 0.6) * -35.dbamp;
	snd = LeakDC.ar(snd);
	snd = FreqShift.ar(snd, 534);
	snd = LeakDC.ar(snd);
	snd = snd * Env.perc(0.01, Rand(1.0, 8.0 ! snd.size)).ar;
	snd = Splay.ar(snd);
	snd = snd * 10.dbamp;
	snd = snd.tanh;
	snd = snd * Env.perc(0.01, 3.0).ar(Done.freeSelf);
	Out.ar(\out.kr(0), snd);
}).add;

/*
Exponential FM with two sine wave operators. Some EQ, distortion, frequency shifting, and a fixed-filter bank (BPF) to put it in a room a bit.
*/
SynthDef(\squiggle, {
	var snd;
	snd = SinOsc.ar(SinOsc.ar(\freq.kr(43)).linexp(-1, 1, [100, 300], 16000)) * -8.dbamp;
	snd = snd.sum;
	snd = RHPF.ar(snd, 720, 0.9);
	snd = snd.tanh;
	snd = FreqShift.ar(snd, 73);
	snd = HPF.ar(snd, 120);
	snd = BPF.ar(snd, (0..16).normalize.linexp(0, 1, 100, 8000), 0.07).sum;
	snd = snd * Env.linen(0.001, \duration.kr(1), 0.03, curve: -4).ar(Done.freeSelf);
	snd = Pan2.ar(snd, 0);
	snd = snd * \amp.kr(-10.dbamp);
	Out.ar(\out.kr(0), snd);
}).add;

/* Sine wave ping, random quivery frequency modulation and amplitude modulation too, and some reverb. */
SynthDef(\sonar, {
	var snd;
	snd = SinOsc.ar(740 * (LFNoise2.kr(100) * 0.06).midiratio) * -5.dbamp;
	snd = snd * LFNoise2.kr(16).linlin(-1, 1, 0.5, 1);
	snd = snd + GVerb.ar(snd, 60, 1);
	snd = snd * Env.perc(0.01, 1, curve: -4).ar(Done.freeSelf);
	snd = snd * -23.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/* Tremolo'd white noise with some EQ. */
SynthDef(\wash2, {
	var snd;
	snd = Hasher.ar(Sweep.ar + [0, 1]);
	snd = snd * SinOsc.ar(30).linlin(-1, 1, 0.5, 1);
	snd = LPF.ar(snd, XLine.kr(8000, 3000, 0.5));
	snd = (snd * 3).clip2;
	snd = snd * -27.dbamp;
	snd = snd * Env.linen(0.03, 1.0, 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * Env.linen(0.0, \duration.kr(1.0), 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * -5.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/*
Uh... let's see. White noise put into two bandpass filters that move outward to mimic formants in the human voice. A little comb filtering to add some nice resonances, then sine wave chirps to enhance the transient, then another bit of colored noise also to enhance the transient, then distortion and parallel pitch shifting and slapback delay. Simple!
*/
SynthDef(\snarey, {
	var snd, ratio;
	ratio = \bend.kr(0).midiratio;
	snd = Hasher.ar(Sweep.ar);
	snd = BPF.ar(snd, [820, 1320] * XLine.kr(1, [0.7, 1.3], 0.5) * ratio, 0.1) * 10.dbamp;
	snd = (snd * [0, -5].dbamp).sum;
	snd = snd + CombC.ar(snd, 0.1, 1 / (90 * ratio), 0.05);
	snd = snd + (SinOsc.ar(XLine.ar(3000, 100, 0.04) * ratio) * Env.perc(0.001, 0.04).ar * 3.dbamp);
	snd = snd + (SinOsc.ar(XLine.ar(8000, 100, 0.01) * ratio) * Env.perc(0.01, 0.01).ar * 3.dbamp);
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 1320 * ratio, 0.3) * Env.perc(0.01, 0.02).ar * 3.dbamp);
	snd = snd.tanh;
	snd = snd + PitchShift.ar(snd, 0.03, 1.2);
	snd = snd * Env.perc(0.001, 0.3, curve: -4).ar(Done.freeSelf);
	snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -30.dbamp, 0.2, [60e-3, 74e-3]), 300), 1000);
	snd = snd * Env.linen(0.0, \duration.kr(1.0), 0.001, curve: -4).ar(Done.freeSelf);
	snd = snd * -17.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/*
Similar to above but with many parameters randomized.
*/
SynthDef(\snarey2, {
	var snd;
	snd = Hasher.ar(Sweep.ar);
	snd = BPF.ar(snd, ({ ExpRand(100, 8000) } ! 2) * XLine.kr(1, [0.7, 1.3], 0.3), 0.1) * 10.dbamp;
	snd = (snd * [0, -5].dbamp).sum;
	snd = snd + CombC.ar(snd, 0.1, 1 / ExpRand(30, 120), 0.05);
	snd = snd + (SinOsc.ar(XLine.ar(ExpRand(3000, 8000), 100, 0.04)) * Env.perc(0.001, 0.04).ar * 3.dbamp);
	snd = snd + (SinOsc.ar(XLine.ar(8000, 100, 0.01)) * Env.perc(0.01, 0.01).ar * 3.dbamp);
	snd = snd + (BPF.ar(Hasher.ar(Sweep.ar), 1320, 0.3) * Env.perc(0.01, 0.02).ar * 3.dbamp);
	snd = snd.tanh;
	snd = snd + PitchShift.ar(snd, 0.03, 1.2);
	snd = snd * Env.linen(0.001, Rand(0.01, 0.07), 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd + LPF.ar(HPF.ar(DelayC.ar(snd * -30.dbamp, 0.2, [60e-3, 74e-3]), 300), 1000);
	snd = snd * Env.linen(0.0, \duration.kr(1.0), 0.001, curve: -4).ar(Done.freeSelf);
	snd = snd * -21.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/* Just sine chirps, nothing crazy. */
SynthDef(\laser1, {
	var snd;
	snd = SinOsc.ar(XLine.ar(5000, 100, 0.05));
	snd = snd * Env.perc(0.02, 0.03).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\laser2, {
	var snd;
	snd = SinOsc.ar(XLine.ar(4000, 100, 0.01));
	snd = snd * Env.perc(0.001, 0.01).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * -5.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\laser3, {
	var snd;
	snd = SinOsc.ar(XLine.ar(8000, 100, 0.03));
	snd = snd * Env.perc(0.001, 0.03).ar(Done.freeSelf);
	snd = Pan2.ar(snd, 0.67);
	snd = snd * -10.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/*
Multiple sine chirps created using an LFSaw. LFSaw goes from -1 to 1, then I map it so it goes from 1 to 0, then I use pow to curve it towards 0, then remap it back to the frequencies I want. Bandpassed white noise adds some gesture.
*/
SynthDef(\lasers, {
	var snd;
	snd = SinOsc.ar(LFSaw.ar(XLine.kr(10, 60, 0.5)).linlin(-1, 1, 1, 0).pow(3).linlin(0, 1, 200, 8000)) * -5.dbamp;
	snd = snd + (BPF.ar(WhiteNoise.ar, XLine.kr(1320, 7320, 0.3), 0.5) * Env.perc(0, 0.5).ar);
	snd = snd.tanh;
	snd = RHPF.ar(snd, 320, 0.7);
	snd = snd * Env.linen(0.001, \duration.kr(1), 0.03, curve: -4).ar(Done.freeSelf);
	snd = Pan2.ar(snd, 0);
	snd = snd * -17.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/* Triangle wave with inharmonic detuning and alternate L/R panning. I had to lag the pan signal a bit to avoid clicks. */
SynthDef(\ring, {
	var snd;
	snd = LFTri.ar(4000);
	snd = FreqShift.ar(snd, -120);
	snd = HPF.ar(snd, 3000);
	snd = Pan2.ar(snd, LFPulse.ar(16).linlin(0, 1, -0.6, 0.6).lag(0.001));
	snd = snd * Env.linen(0.001, \duration.kr(1.0), 0.001).ar(Done.freeSelf);
	snd = snd * -37.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/* Throwing various effects at stereo white noise to try to make it interesting. */
SynthDef(\wash, {
	var snd;
	snd = Hasher.ar(Sweep.ar + [0, 1]);
	snd = CombC.ar(snd, 0.2, 1 / 60, 0.3);
	snd = FreqShift.ar(snd, 33.4);
	snd = HPF.ar(snd, 600);
	snd = LPF.ar(snd, 8000);
	snd = BRF.ar(snd, 1320, 0.1);
	snd = BRF.ar(snd, 6320, 0.1);
	snd = BRF.ar(snd, 3320, 0.1);
	snd = BPeakEQ.ar(snd, 620 * Latch.ar(XLine.ar(1, 3, 0.3), Impulse.ar(8)), 0.3, 6);
	snd = LPF.ar(snd, XLine.kr(1000, 8000, 0.01));
	snd = snd * -17.dbamp;
	snd = snd * Env.linen(0.03, 1.0, 0.01, curve: -4).ar(Done.freeSelf);
	snd = Balance2.ar(snd[0], snd[1], \pan.kr(0));
	snd = snd * Env.linen(0.0, \duration.kr(1.0), 0.01, curve: -4).ar(Done.freeSelf);
	snd = snd * -5.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/* Bandpassed white noise. Bandpass cutoff is modulated. Many parameters randomized including pan. */
SynthDef(\scratch, {
	var snd;
	snd = WhiteNoise.ar;
	snd = BPF.ar(snd, ExpRand(2320, 8320) * XLine.kr(1, Rand(0.7, 1.3), ExpRand(0.01, 0.1)), ExpRand(0.1, 0.3));
	snd = Pan2.ar(snd, Rand(-0.9, 0.9));
	snd = snd * Env.perc(0.001, ExpRand(0.005, 0.07)).ar(Done.freeSelf);
	snd = snd * -12.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

/*
Additive synthesis with different envelopes for every partial, so that in general the lower partials come in slower than the higher ones, making a sort of "shing" sound. To fatten up the partials I use alternating layers of distortion and frequency shifting. I just sort of came up with that idea on the spot and was kind of surprised at how well it worked.
*/
SynthDef(\sword, {
	var snd, ratios;
	ratios = [1.0, 2.3, 4.6, 9.3, 7.4];
	snd = SinOsc.ar(3220 * ratios);
	snd = snd / ratios;
	snd = snd * Env.perc([0.3, 0.02, 0.05, 0.1, 0.003], 0.05).ar;
	snd = snd.sum;
	snd = (snd * 10.dbamp).tanh;
	snd = FreqShift.ar(snd, -30);
	snd = (snd * 10.dbamp).tanh;
	snd = FreqShift.ar(snd, 64);
	snd = snd * -7.dbamp;
	snd = snd * Env.perc(0.005, 0.1).ar;
	snd = snd + GVerb.ar(snd * -7.dbamp, 30, 1);
	snd = snd * Env.perc(0.005, 2.0).ar(Done.freeSelf);
	snd = snd * -17.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\swordReverse, {
	var snd, ratios, duration;
	duration = \duration.kr(0.05);
	ratios = [1.0, 2.3, 4.6, 9.3, 7.4];
	snd = SinOsc.ar(4320 * ratios);
	snd = snd.sum;
	snd = (snd * 20.dbamp).tanh;
	snd = FreqShift.ar(snd, -30);
	snd = (snd * 10.dbamp).tanh;
	snd = FreqShift.ar(snd, 64);
	snd = snd * -25.dbamp;
	snd = snd + GVerb.ar(snd * -7.dbamp, 30, 1);
	snd = snd * Env.perc(duration, 0.01, curve: 4).ar(Done.freeSelf);
	snd = snd * -12.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\riser, {
	var snd, duration;
	duration = \duration.kr(3.0);
	snd = SinOsc.ar(610) * 2300;
	snd = SinOsc.ar(220 + snd);
	snd = MoogFF.ar(snd, LFNoise2.kr(32).linexp(-1, 1, 1000, 16000), 3.5);
	snd = (snd * 10.dbamp).tanh;
	snd = snd * Env.perc(duration - 0.1, 0.03, curve: 4).ar(Done.freeSelf);
	snd = snd * -20.dbamp;
	snd = snd ! 2;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\clickRandom, {
	var snd, ratios;
	ratios = ExpRand(1, 8 ! 3);
	snd = SinOsc.ar(XLine.ar(ExpRand(5e3, 16e3) ! 3, ExpRand(400, 1000) ! 3, ExpRand(1e-4, 1e-2) ! 3) * ratios) * Env.perc(0, ExpRand(0.001, 0.02) / ratios).ar;
	snd = snd.sum;
	snd = snd * LPF.ar(PinkNoise.ar * 17.dbamp, 500);
	snd = (snd * Rand(0, 10).dbamp).fold2;
	snd = snd + CombC.ar(snd, 0.2, 1 / ExpRand(50, 300), ExpRand(0.01, 0.03));
	snd = FreqShift.ar(HPF.ar(snd, 20), Rand(-200, 1000));
	snd = snd * Rand(-2, 5).dbamp;
	snd = LPF.ar(snd, ExpRand(1000, 16000));
	snd = Pan2.ar(snd, Rand(-0.8, 0.8)) + GVerb.ar(snd * -5.dbamp, ExpRand(5, 30), ExpRand(1, 3), 0.3);
	3.do {
		snd = snd + PitchShift.ar(snd, ExpRand(0.01, 0.04), ExpRand(0.5, 3));
	};
	snd = snd * Env([0, 1, 0.3, 1, 0], [ExpRand(1e-3, 1e-2), ExpRand(0.001, 0.03), 0.001, ExpRand(0.05, 0.3)], curve: -8).ar(Done.freeSelf);
	snd = snd * -16.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\hiss, {
	var snd;
	snd = CombC.ar(WhiteNoise.ar, 0.2, 1 / 50, 0.3);
	snd = BPF.ar(snd, [10120, 14230] * XLine.kr(0.5, 1, 2), 0.3).sum;
	snd = HPF.ar(snd, 1000);
	snd = snd ! 2;
	snd = snd * Env([0, 1, 1, 0.1, 0], [0.5, 0.3, 0.03, 1], curve: [4, 0.1, -4]).ar(Done.freeSelf);
	snd = snd * -18.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\hiss2, {
	var snd;
	snd = CombC.ar(WhiteNoise.ar, 0.2, 1 / 200, 0.3);
	snd = BPF.ar(snd, [8120, 9230] * XLine.kr(1.2, 0.7, 0.3), 0.3).sum;
	snd = HPF.ar(snd, 1000);
	snd = snd ! 2;
	snd = snd * Env([0, 1, 0.1, 0], [0.08, 0.3, 0.1], curve: -4).ar(Done.freeSelf);
	snd = snd * -22.dbamp;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\quack, {
	var snd, duration;
	duration = 0.1;
	snd = SinOsc.ar(2030) * 2300;
	snd = SinOsc.ar(220 + snd);
	snd = MoogFF.ar(snd, XLine.ar(100, 3000, duration), 3.5);
	snd = (snd * 20.dbamp).tanh;
	snd = snd * Env.linen(0.001, duration, 0.03, curve: -8).ar(Done.freeSelf);
	snd = Pan2.ar(snd, \pan.kr(0));
	snd = snd * -9.dbamp;
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\warble, {
	var snd, freq, detune, rate, velocity;
	freq = \freq.kr(440);
	velocity = \velocity.kr(1) * Rand(0.7, 1);
	rate = XLine.kr(1, 2, 1);
	detune = ((LFNoise2.kr(3 * rate) * 0.3) + (LFNoise2.kr(8) * 0.1) + Line.kr(10, 0, 0.003)).midiratio;
	snd = SinOsc.ar(freq * IRand(5, 8 ! 8) * (LFNoise2.kr(3 ! 8 * rate) * 0.7).midiratio * detune) * Rand(3000, 8300 ! 8) * (1 + Env.perc(0.05 * ExpRand(0.5, 2.0), 0.3 * ExpRand(0.5, 2.0)).ar);
	snd = SinOsc.ar((freq * (LFNoise2.kr(3 ! 8 * rate) * 0.4).midiratio * detune) + snd);
	snd = snd * (1 + LFNoise2.ar(3 ! snd.size));
	snd = Splay.ar(snd);
	snd = LPF.ar(snd, XLine.kr(1000, 8000, 0.03) * ExpRand(0.9, 1.1));
	snd = snd * (1 + (Rand(0.5, 3) * Env.perc(0.01 * ExpRand(0.5, 2.0), 0.3 * ExpRand(0.5, 2.0)).ar));
	snd = (snd * 10.dbamp).tanh;
	snd = (snd * 2.dbamp).fold2;
	snd = BPeakEQ.ar(snd, 820 * ExpRand(0.9, 1.1), 0.1, 3);
	snd = BPeakEQ.ar(snd, 1220 * ExpRand(0.9, 1.1), 0.05, 5);
	snd = BPeakEQ.ar(snd, 3220 * ExpRand(0.9, 1.1), 0.06, 5);
	snd = MoogFF.ar(snd, XLine.kr(500, 8000, 0.003) * ExpRand(0.9, 1.1) * XLine.kr(1, 0.1, 3), 0) * 5.dbamp;
	snd = BHiShelf.ar(snd, 2300, 1, -10);
	snd = LPF.ar(snd, velocity.linexp(0, 1, 3000, 16e3));
	snd = snd * freq.explin(200, 600, -10, 0).dbamp;
	snd = snd * Env.perc(0.05 * ExpRand(0.5, 2.0), 8.0 * velocity.sqrt, curve: -23).ar(Done.freeSelf);
	snd = snd * -17.dbamp;
	snd = snd * \amp.kr(1) * velocity.sqrt;
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\reverseTwang, {
	var snd, freq, duration;
	duration = \duration.kr(0.8);
	freq = \freq.kr(440) * (LFNoise2.kr(3) * 0.1).midiratio;
	snd = Saw.ar(freq);
	snd = CombC.ar(snd, 1 / 90, 1 / 90, 0.3);
	snd = LPF.ar(snd, XLine.kr(10, 3000, duration));
	snd = snd * -27.dbamp;
	snd = snd * Env.perc(duration, 0.001, curve: 3).ar;
	snd = Pan2.ar(snd, -0.5) + GVerb.ar(snd, 60, 8, damping: 0.9);
	snd = snd * Env.linen(0, 5, 0.3).ar(Done.none);
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\reverseTwang2, {
	var snd, freq, duration;
	duration = 0.09;
	freq = \freq.kr(440) * (LFNoise2.kr(3) * 0.1).midiratio;
	snd = SinOsc.ar(freq) * 3000;
	snd = SinOsc.ar(freq + snd);
	snd = CombC.ar(snd, 1 / 90, 1 / 90, 0.3);
	snd = LPF.ar(snd, XLine.kr(100, 8000, duration));
	snd = snd * -30.dbamp;
	snd = snd * Env.perc(duration, 0.001, curve: 3).ar;
	snd = Pan2.ar(snd, 0.5) + GVerb.ar(snd, 100, 3, damping: 0.9);
	snd = snd * Env.linen(0, 5, 0.3).ar(Done.none);
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;

SynthDef(\reverseTwang3, {
	var snd, freq, duration;
	duration = 0.09;
	freq = \freq.kr(440) * (LFNoise2.kr(3) * 0.1).midiratio;
	snd = SinOsc.ar(freq * 2.3) * 4230;
	snd = SinOsc.ar(freq + snd);
	snd = CombC.ar(snd, 1 / 70, 1 / 70, 0.3);
	snd = LPF.ar(snd, XLine.kr(10, 8000, duration));
	snd = snd * -30.dbamp;
	snd = snd * Env.perc(duration, 0.001, curve: 3).ar;
	snd = snd + GVerb.ar(snd * -5.dbamp, 100, 3, damping: 0.9);
	snd = snd * Env.linen(0, 5, 0.3).ar(Done.none);
	snd = snd * \amp.kr(1);
	Out.ar(\out.kr(0), snd);
}).add;
)