s = Server.local;
// ServerOptions.devices;
s.options.outDevice_(
	// "MacBook Pro Speakers"
	"External Headphones"
	// "Scarlett 4i4 USB"
);
s.options.inDevice_("Built-in Microph");
s.options.numOutputBusChannels_(2);
s.options.numInputBusChannels_(2);
s.options.sampleRate_(48000);
s.options.memSize_(2.pow(20));
/*s.newBusAllocators;
ServerBoot.removeAll;
ServerTree.removeAll;
ServerQuit.removeAll;*/
s.boot;

(
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
	snd = snd * \amp.kr(0.001);
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
	snd = snd * -15.dbamp;
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
	snd = snd * -15.dbamp;
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
	var snd, freq, n, intensity;
	freq = \freq.kr(440).lag(0.02);
	intensity = LFNoise2.kr(3).linlin(-1, 1, 0, 1) * Line.kr(0, 1, 10);
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
	snd = snd * Env.asr(0.5, 1.0, 3.0, curve: -4).ar(Done.freeSelf, \gate.kr(1));
	snd = snd * -25.dbamp;
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
)

Synth(\celeste, [\freq, 2999]);
Synth(\glockenspiel, [\freq, 2999]);
Synth(\vibraphone, [\freq, 166.5]);

Synth(\feedback2, [\duration, 30, \freq, 666]);

~synth = Synth(\theremin, [\freq, 440, \amp, 0.5, \dur, 30]);
~synth.set(\freq, 333, \amp, 0.5);

// ...SynthDefs defined elsewhere...
~events = Array.new;
~synths = Dictionary.new;

(
OSCdef(\storeEvent, { |msg, time, addr, recvPort|
    var eventType = msg[1];
    var event = msg[2..];
    switch(eventType,
        'new', {
            ~events = ~events.add(['new', event]);
        },
        'new_id', {
            var id = event[0];
            var synthArgs = event[1..];
            ~events = ~events.add(['new_id', id, synthArgs]);
        },
        'set', {
            var id = event[0];
            var setArgs = event[1..];
            ~events = ~events.add(['set', id, setArgs]);
        }
    );
}, '/storeEvent');

~startComposition = {
    "Starting composition...".postln;
    ~events.do { |item|
        var type = item[0];
        switch(type,
            'new', {
				var args = item[1];
                var synthName = args[0];
                var start = args[1].asFloat;
                var argsDict = args[2..];
				// argsDict.postln;
                SystemClock.schedAbs(thisThread.seconds + start, {
                    s.bind {
                        Synth(synthName, argsDict);
                    };
                });
            },
            'new_id', {
				var args = item[2];
				var id = item[1];
				var synthName = args[0];
				var start = args[1].asFloat;
				var argsDict = args[2..];
				// argsDict.postln;
				SystemClock.schedAbs(thisThread.seconds + start, {
					s.bind {
						var synth = Synth(synthName, argsDict);
						~synths.put(id, synth);
					};
				});
            },
            'set', {
				var args = item[2];
				var id = item[1];
				var start = args[0].asFloat;
				var argsDict = args[1..];
				SystemClock.schedAbs(thisThread.seconds + start, {
					s.bind {
						var synth = ~synths.at(id);
						if (synth.notNil) { synth.set(*argsDict); }
					};
				});
            }
        );
    };
};
)

~synths.value;
~events.value;
~startComposition.value;
