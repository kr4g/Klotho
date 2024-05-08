EventScheduler {
	var <events, <synths;
	var oscDef;
	var <server;

	*new { |serverArg|
		^super.new.initialize(serverArg)
	}

	initialize { |serverArg|
		events = Array.new;
		synths = Dictionary.new;
		server = serverArg;
	}

	startOSCListening { |ipAddress = '127.0.0.1', oscAddress = '/storeEvent'|
		oscDef = OSCdef(ipAddress.asSymbol, { |msg, time, addr, recvPort|
			var eventType = msg[1];
			var eventArgs = msg[2..];
			this.addEvent(eventType, eventArgs);
		}, oscAddress);
	}

	stopOSCListening {
		oscDef.free;
	}

	// XXX - BROKEN
	clearAll {
		events.clear;
		"Events cleared.".postln;
		synths.values.do { |synth|
			if (synth.notNil) {
				synth.free;
				// "Freed synth with ID %".format(synth.nodeID).postln;
			}
		};
		synths.clear;
		"Synths cleared.".postln;
	}

	addEvent { |type, eventArgs|
		switch(type,
			\new, {
				events = events.add([\new, eventArgs]);
			},
			\new_id, {
				var id = eventArgs[0];
				var synthArgs = eventArgs[1..];
				events = events.add([\new_id, id, synthArgs]);
			},
			\set, {
				var id = eventArgs[0];
				var setArgs = eventArgs[1..];
				events = events.add([\set, id, setArgs]);
			}
		);
	}

	scheduleEvents {
		"Starting composition...".postln;
		events.do { |item|
			var type = item[0];
			switch(type,
				\new, {
					var args = item[1];
					this.scheduleSynth(args, nil);
				},
				\new_id, {
					var args = item[2];
					var id = item[1];
					this.scheduleSynth(args, id);
				},
				\set, {
					var args = item[2];
					var id = item[1];
					this.scheduleSet(args, id);
				}
			);
		};
	}

	scheduleSynth { |args, id|
		var synthName = args[0];
		var start = args[1].asFloat;
		var argsDict = args[2..];
		SystemClock.schedAbs(thisThread.seconds + start, {
			server.bind {
				var synth = Synth(synthName, argsDict);
				if(id.notNil) { synths.put(id, synth); }
			};
		});
	}

	scheduleSet { |args, id|
		var start = args[0].asFloat;
		var argsDict = args[1..];
		SystemClock.schedAbs(thisThread.seconds + start, {
			server.bind {
				var synth = synths.at(id);
				if (synth.notNil) { synth.set(*argsDict); }
			};
		});
	}
}