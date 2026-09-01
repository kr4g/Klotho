(
// klotho_spatial_synthdefs.scd -- the N-wide spatial infrastructure.
//
// Three FAMILIES, one def per supported width.  A family, and not one def with
// a \width control, because SuperCollider fixes a SynthDef's channel count
// during graph construction: In.ar(bus, width) reads `width` while the graph
// is being built, so a control there raises MustBeBooleanError.  Channel count
// is structure, not a parameter.
//
//   __busRouterN       an N-wide track/main router: the N-channel twin of
//                      __busRouter in klotho_synthdefs.scd.  ReplaceOut back
//                      onto its own bus so inserts and stem taps still see the
//                      post-gain signal, plus Out to the next bus.
//   __spatialArrayOutN mirrors the N-wide private array bus to consecutive
//                      HARDWARE channels, for export='array' captures.
//   __spatialDecodeN   the binaural-lite decoder: ITD + ILD + head shadow,
//                      N lanes in, 2 channels out.
//
// THE GEOMETRY BUFFER
// -------------------
// __spatialDecodeN reads its coefficients from a control buffer holding
// BinauralCoefficients.flat() (klotho/thetos/spatial.py) VERBATIM.  flat() is
// lane-major with stride 6 --
//
//     index = lane * 6 + field
//     field 0 delay_l  1 delay_r  2 gain_l  3 gain_r  4 shadow_l_hz  5 shadow_r_hz
//
// -- and a SuperCollider buffer allocated as `/b_alloc <buf> N 6` (N frames,
// 6 channels) is interleaved in exactly that order.  So ONE BufRd.kr(6, buf,
// lane) returns all six coefficients for a lane as a single UGen.  Six
// Index.kr calls read the same bytes and sound identical but cost five more
// UGens per lane (at N=24: 335 UGens against 287).
//
// Allocate the buffer with SIX CHANNELS.  `/b_alloc <buf> (N*6) 1` holds the
// same floats and BufRd.kr(6, ...) would then read six CONSECUTIVE frames per
// phase step -- lane k's delay_l plus five numbers belonging to other lanes.
// That is a silent geometry error, not a load failure.
//
// HEAD SHADOW: OnePole, and the coefficient conversion
// ----------------------------------------------------
// The far ear's shadow is a ONE-POLE lowpass -- 6 dB/octave -- because that is
// what the offline fold is (spmock/gesture/preview.py `_one_pole`, which is
// scipy lfilter([1-a], [1, -a]) with a = exp(-2*pi*fc/sr)).  LPF would be two
// poles and 12 dB/octave: same corner frequency, wrong slope, and the live
// preview and the offline fold would then disagree about everything above the
// corner.  Matching the reference is worth the UGens (at N=24: 287 against
// 190).
//
// OnePole.ar takes a COEFFICIENT, not a frequency:
//
//     out(i) = ((1 - abs(coef)) * in(i)) + (coef * out(i-1))
//
// which is lfilter([1-a], [1, -a]) exactly when coef == a.  So the conversion
// from the buffer's Hz to OnePole's coefficient is
//
//     coef = exp(-2pi * fc / sr) = exp(fc * negTau),   negTau = -2pi/sr
//
// and negTau is hoisted OUT of the lane loop -- one SampleDur.ir for the whole
// graph, not two per lane.
//
// A cutoff of 0 Hz would give coef = 1 (a pure integrator) and a NEGATIVE
// cutoff would give coef > 1 (an exponential blowup that poisons the main
// output with NaN and never recovers).  There is deliberately NO clamp here.
// spatial.py bounds every cutoff to [SHADOW_LO_HZ, SHADOW_HI_HZ] = [1400,
// 18000] by construction, a clamp would cost 2 UGens per lane, and -- the
// deciding reason -- a clamp SILENTLY CORRECTS a bad geometry table instead of
// reporting it.  The refusal belongs in Python, where it can say which lane
// and why.  See the note on the uploader in the design record.
//
// maxdelaytime is 0.33 s, not 0.5 s: scsynth rounds each delay line up to the
// next power of two frames, so at 48 kHz 0.33 s lands in the 16384-frame
// bucket while 0.5 s lands in the 32768-frame one -- exactly twice the memory
// for headroom nothing uses.  0.33 s still covers 275.3 ms, the worst ear
// delay for a listener one foot inside a corner of the 250 x 180 ft Pavilion.
// Keep this in step with DECODER_MAX_DELAY_S in klotho/thetos/spatial.py.
// Measured, by binary search on scsynth's -m: N = 24 needs 3163 KB, of which
// 2 * 24 * 16384 * 4 B = 3072 KB is delay lines and 91 KB is everything else.
// At 0.5 s the delay lines alone would be 6144 KB.
//
// DelayN, not DelayL or DelayC: the delay never moves after the synth starts,
// so interpolation buys nothing, and its fractional-delay filter measurably
// dulls the UNSHADOWED ear -- an 18 kHz corner reads back near 16 kHz through
// DelayC and near 13 kHz through DelayL.  That is a head shadow the geometry
// did not ask for.
//
// THE WIDTH SET
// -------------
// Precompiled: 1, 2, 4, 6, 8, 12, 16, 24, 32.  Everything else is compiled at
// lowering time and sent with /d_recv (see runtime_decoder.py) -- the decoder
// graph is fully described by N, so an off-family width costs one compile, not
// a missing feature.
//
// 32 IS THE CEILING, AND IT HAS NO HEADROOM.  This decoder needs exactly 2N
// interconnect ("wire") buffers -- measured at every width from 1 to 64 -- and
// the browser engine boots with maxWireBufs 64 (cdn.py:
// SUPERSONIC_DEFAULT_MAX_WIRE_BUFS) with no override from Klotho.  So N = 32
// needs 64 of 64, and N = 40 needs 80 and does not load.
//
// 2N, not the N + 4 an LPF decoder costs, and OnePole is not to blame: an LPF
// fed through the same exp() chain also measures 48 at N = 24, while OnePole
// with a constant coefficient, or reading the buffer with no arithmetic at
// all, measures 28.  The extra buffers are the coefficient arithmetic itself,
// and no reordering inside the lane body avoids them.
//
// scsynth does NOT refuse a def that does not fit.  It prints "exception in
// GraphDef_Load: exceeded number of interconnect buffers", skips that one def
// and carries on; the later /s_new then does nothing.  The symptom is SILENCE
// with no exception anywhere, so validate N before compiling rather than
// discovering it at the concert.
var outDir = thisProcess.nowExecutingPath.dirname +/+ "synthdefs";
var infraDir = outDir +/+ "infra";
var widths = [1, 2, 4, 6, 8, 12, 16, 24, 32];
var maxDelay = 0.33;

outDir.mkdir;
infraDir.mkdir;

widths.do { |n|

    SynthDef(("__busRouter" ++ n).asSymbol, { |inBus=0, outBus=0, gain=1.0|
        var sig = In.ar(inBus, n);
        sig = sig * gain;
        ReplaceOut.ar(inBus, sig);
        Out.ar(outBus, sig);
    }).writeDefFile(infraDir);

    SynthDef(("__spatialArrayOut" ++ n).asSymbol, { |inBus=0, outBus=2, gain=1.0|
        var sig = In.ar(inBus, n);
        sig = sig * gain;
        Out.ar(outBus, sig);
    }).writeDefFile(infraDir);

    SynthDef(("__spatialDecode" ++ n).asSymbol, { |inBus=0, outBus=0, bufnum=0, gain=1.0|
        // .asArray: In.ar(bus, 1) returns a bare OutputProxy rather than an
        // array, so n = 1 would raise 'at not understood' without it.
        var lanes = In.ar(inBus, n).asArray;
        var negTau = -2pi * SampleDur.ir;   // hoisted: ONE per graph
        var ls = Array.newClear(n), rs = Array.newClear(n);
        n.do { |k|
            var c = BufRd.kr(6, bufnum, k, loop: 0, interpolation: 1);
            var lane = lanes.at(k);
            var wetL = DelayN.ar(lane, maxDelay, c.at(0)) * c.at(2);
            var wetR = DelayN.ar(lane, maxDelay, c.at(1)) * c.at(3);
            ls[k] = OnePole.ar(wetL, exp(c.at(4) * negTau));
            rs[k] = OnePole.ar(wetR, exp(c.at(5) * negTau));
        };
        // Mix, not sum: Mix folds with Sum4/Sum3 (8 UGens per ear at n = 24)
        // where a left fold of BinaryOpUGens costs 23.
        Out.ar(outBus, [Mix(ls), Mix(rs)] * gain);
    }).writeDefFile(infraDir);
};

("klotho_spatial_synthdefs: wrote % defs for widths %".format(
    widths.size * 3, widths)).postln;
0.exit;
)
