"""Provenance for the ``spatial_probe_*.scsyndef`` fixtures.

Not a test (pytest collects ``test_*.py`` only) and not run by the suite.
It records how the checked-in blobs beside it were produced, so a future
reader can rebuild or extend them instead of guessing.

Why these exist: every bundled SynthDef in the tree is 2 channels wide, so
nothing shipped can exercise a 1-channel point source, a 4-wide insert, or
a 24-wide one -- which is most of what the multichannel width contract is
about.  Compiled blobs are checked in rather than built at test time so the
suite needs neither Supriya nor sclang.

Rebuild from the repo root, with an interpreter that has Supriya::

    python tests/fixtures/synthdefs/spatial_probe_build.py

The three defs, and what each is for:

``spatial_probe_mono``   ``Out.ar(out, monoSig)`` -- ``outs == 1``.
                         A point source: occupies exactly the one speaker
                         its ``speaker`` names, and has no stereo image to
                         pan.
``spatial_probe_fx4``    ``In.ar(inBus, 4)`` -> ``ReplaceOut.ar(outBus, ...)``.
                         A correctly-sized insert for a 4-speaker track,
                         and a wrongly-sized one for any other width.
``spatial_probe_fx24``   the same at 24, the Sonic Pavilion width.
``spatial_probe_fx4in2out``
                         reads 4, writes 2. ASYMMETRIC on purpose: with only
                         symmetric probes, a width check that tested ``ins``
                         and ignored ``outs`` passed every test. A chain
                         whose halves disagree is a chain that drops lanes.
"""

from pathlib import Path

OUT_DIR = Path(__file__).parent


def build_mono():
    from supriya import SynthDefBuilder
    from supriya.ugens import Line, Out, SinOsc

    with SynthDefBuilder(out=0.0, freq=440.0, amp=0.1, duration=1.0) as b:
        sig = SinOsc.ar(frequency=b['freq']) * b['amp']
        env = Line.kr(start=1.0, stop=0.0, duration=b['duration'],
                      done_action=2)
        Out.ar(bus=b['out'], source=sig * env)
    return b.build(name='spatial_probe_mono')


def build_fx(width, name, out_width=None):
    from supriya import SynthDefBuilder
    from supriya.ugens import In, ReplaceOut

    with SynthDefBuilder(inBus=0.0, outBus=0.0, gain=1.0) as b:
        sig = In.ar(bus=b['inBus'], channel_count=width)
        if out_width is None:
            ReplaceOut.ar(bus=b['outBus'], source=sig * b['gain'])
        else:
            ReplaceOut.ar(bus=b['outBus'],
                          source=[sig[i] * b['gain'] for i in range(out_width)])
    return b.build(name=name)


def main():
    for sd in (build_mono(),
               build_fx(4, 'spatial_probe_fx4'),
               build_fx(24, 'spatial_probe_fx24'),
               build_fx(4, 'spatial_probe_fx4in2out', out_width=2)):
        path = OUT_DIR / f"{sd.name}.scsyndef"
        path.write_bytes(sd.compile())
        print(f"wrote {path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
