ServerOptions.devices;
(
s = Server.local;
s.options.outDevice_(
	// "MacBook Pro Speakers"
	// "External Headphones"
	// "Scarlett 4i4 USB"
	"Klipsch One II"
);
s.options.inDevice_("Built-in Microph");
s.options.numOutputBusChannels_(2);
s.options.numInputBusChannels_(0);
s.options.sampleRate_(48000);
s.options.memSize_(2.pow(20));
// s.newBusAllocators;
// ServerBoot.removeAll;
// ServerTree.removeAll;
// ServerQuit.removeAll;
s.reboot;
)
Synth(\default)

"/Users/ryanmillett/allolib_playground/AlloPy/examples/thesis/synthdefs.scd".load;

Synth(\random, [\seed, 435])
Synth(\hat)
Synth(\hatOpen)
Synth(\crash)
Synth(\perc, [\freq, exprand(220, 880)])

Synth(\glitch1, [\freqShift, rand(3800)]);

x = Synth(\flute, [\gate, 0]);
x.set(\gate, 1, \freq, 440, \freqLag, exprand(0.01, 0.5), \amp, rand(0.1, 1.0), \ampLag, 1);
x.set(\freq, exprand(200, 1000));

(
~rec = { |name, schdlr, dur|
	Routine({
		var path = "/Users/ryanmillett/Downloads/presentation_examples/audio/";
		var fileName = path ++ name ++ ".wav";
		var i = 1;
		while ({File.exists(fileName)}) {
			// name = name ++ "_" ++ i;
			fileName = path ++ name ++ "_" ++ i ++ ".wav";
			i = i + 1;
		};
		s.record(fileName, numChannels: 2, duration: dur);
		wait(0.02);
		schdlr.scheduleEvents;
	}).play;
}
)

(
SynthDef(\freeverb, {
	var sig;
	sig = In.ar(0, 2);
	sig = LPF.ar(sig, 2500);
	sig = FreeVerb.ar(sig, mix: 0.33, room: 0.25, damp: 0.5);
	Out.ar(\out.kr(0), sig);
}).add;

SynthDef(\hall, {
	var sig;
	sig = In.ar(0, 2);
	sig = GVerb.ar(sig, drylevel: 0.3);
	Out.ar(\out.kr(0), sig);
}).add;
)
~fx = Synth.tail(nil, \freeverb);

~scheduler = EventScheduler.new(s);
~scheduler.events.size;
~scheduler.scheduleEvents;

~rec.("0_rt_ex2_nesting", ~scheduler, 21);
