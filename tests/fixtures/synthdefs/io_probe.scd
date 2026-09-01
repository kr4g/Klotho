// Source for the .scsyndef fixtures beside this file. Regenerate with:
//
//   /Applications/SuperCollider.app/Contents/MacOS/sclang \
//       tests/fixtures/synthdefs/io_probe.scd
//
// It writes beside itself, so it needs no path editing when the tree moves.
//
// These exist because io.json's generator enumerates two UGens that NO
// bundled def uses -- XOut (a writer whose second argument is a crossfade
// level, not a channel) and InFeedback (a reader). Deleting either from the
// generator's tables, or getting XOut's channel arithmetic wrong, left the
// whole suite green, because nothing on disk compiles to one. Real compiled
// bytes, rather than hand-written parser dicts, so the pin survives a change
// in what the parser emits.
(
var dir = thisProcess.nowExecutingPath.dirname;
SynthDef(\io_probe_xout2, { |inBus=0, outBus=0, xfade=0.5|
    var sig = InFeedback.ar(inBus, 2);
    XOut.ar(outBus, xfade, sig * 0.1);
}).writeDefFile(dir);
// Four channels as well, so the arithmetic is pinned by two points: one
// width alone cannot tell "inputs - 2" from "inputs / 2".
SynthDef(\io_probe_xout4, { |inBus=0, outBus=0, xfade=0.5|
    var sig = InFeedback.ar(inBus, 4);
    XOut.ar(outBus, xfade, sig * 0.1);
}).writeDefFile(dir);
"WROTE".postln;
0.exit;
)
