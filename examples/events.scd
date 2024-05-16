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
// s.newBusAllocators;
// ServerBoot.removeAll;
// ServerTree.removeAll;
// ServerQuit.removeAll;
s.boot;
)

"/Users/ryanmillett/allolib_playground/AlloPy/examples/synthdefs.scd".load;
// "/Users/ryanmillett/MAT276IA/allolib_playground/AlloPy/examples/synthdefs.scd".load;

~scheduler = EventScheduler.new(s);

~scheduler.scheduleEvents;
