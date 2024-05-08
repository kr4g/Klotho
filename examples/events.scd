(
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
)

"/Users/ryanmillett/allolib_playground/AlloPy/examples/synthdefs.scd".load;

~synth = Synth(\lead, [\freq, 166.5, \amp, 0.05, \intenseRate, 3]);
~synth.set(\freq, 166.5, \freqLag, 25.0);
~synth.set(\amp, 0.05, \ampLag, 25.0);
~synth.set(\intenseRate, 3, \intenseLag, 10);
~synth.set(\gate, 1);

~synth = Synth(\choir, [\duration, 30, \freq, 83.25, \atk, 0.5, \rel, 3, \amp, 0.05]);
~synth.set(\freq, 83.25*(7/5), \freqLag, 10);
~synth.set(\amp, 0.25, \ampLag, 15);


~scheduler = EventScheduler.new(s);
~scheduler.startOSCListening();

~scheduler.scheduleEvents;

// ~scheduler.clearAll;
