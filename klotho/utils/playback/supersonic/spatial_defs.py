"""The ``__spatialDecodeN`` / ``__busRouterN`` / ``__spatialArrayOutN`` family.

Three SynthDef families, one def per supported width, compiled by
``assets/klotho_spatial_synthdefs.scd`` and bundled as
``assets/synthdefs/infra/*.scsyndef``:

``__busRouterN``        an ``N``-wide track/main router -- the ``N``-channel
                        twin of ``__busRouter``.  ``ReplaceOut`` onto its own
                        bus (so inserts and stem taps still see the post-gain
                        signal) plus ``Out`` to the next bus.
``__spatialArrayOutN``  mirrors the ``N``-wide private array bus to
                        consecutive HARDWARE channels, for array captures.
``__spatialDecodeN``    the binaural-lite decoder: interaural delay, level
                        difference and head shadow; ``N`` lanes in,
                        2 channels out.

A FAMILY rather than one def with a ``width`` control, because SuperCollider
fixes a SynthDef's channel count while the graph is being built:
``In.ar(bus, width)`` reads ``width`` at construction time, so a control
there raises ``MustBeBooleanError``.  Channel count is structure, not a
parameter.

Precompiled widths are :data:`PRECOMPILED_WIDTHS`, and today they are the
only widths that play.  The builders below can compile any width, and
sending one with ``/d_recv`` is how an unusual array would cost one compile
rather than being a missing feature -- but **that path is not wired**:
nothing in the live pipeline imports these builders, ``register_compiled``
has no ``'infra'`` kind to file the result under, and no lowering step emits
``/d_recv``.  Until it is,
:func:`klotho.utils.playback.supersonic.engine.needed_spatial_synthdefs`
refuses an off-family width in Python.  It has to: scsynth does not complain
about an ``/s_new`` naming a def it never received -- it creates nothing, and
the array plays silently.

(This paragraph used to say the runtime compile happened "at lowering time"
as a matter of course.  It never did, and that sentence is exactly why a
30-speaker rig felt supported all the way to the concert.)

**The failure this module exists to prevent is SILENCE.**  scsynth does not
refuse a SynthDef it cannot fit: past the interconnect ("wire") buffer
limit it prints ``exception in GraphDef_Load: exceeded number of
interconnect buffers``, SKIPS that def and carries on.  The later
``/s_new`` then does nothing, and the piece plays silently with no error
anywhere.  Every guard below therefore refuses BEFORE anything is compiled
or uploaded (Ruling Nine: refusal is a legitimate answer).

Everything numeric here is imported from :mod:`klotho.thetos.spatial` rather
than restated.  A constant written down twice is a constant that drifts, and
this family's cap has already been wrong once (an extrapolated "N + 4" wire
cost put it at 60 speakers instead of 32).

Supriya is imported lazily, inside the builders only: it is not a dependency
of Klotho, and every lookup and every guard in this module works without it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from klotho.thetos.spatial import (
    BINAURAL_FIELDS,
    BINAURAL_STRIDE,
    DECODER_MAX_DELAY_S,
    DECODER_WIRE_BUFS_PER_SPEAKER,
    MAX_DECODER_SPEAKERS,
    SCSYNTH_DEFAULT_MAX_WIRE_BUFS,
    decoder_wire_bufs,
)

__all__ = [
    # Re-exported, not restated: a caller sizing an array against the cap
    # should not have to import two modules to do it, and an alias cannot
    # drift from the thing it aliases.
    'MAX_DECODER_SPEAKERS',
    'PRECOMPILED_WIDTHS',
    'SPATIAL_FAMILIES',
    'SpatialDefs',
    'array_out_name',
    'build_bus_router',
    'build_spatial_array_out',
    'build_spatial_decoder',
    'check_coefficients',
    'check_width',
    'decoder_name',
    'defs_for_width',
    'is_precompiled',
    'parse_def_name',
    'precompiled_path',
    'router_name',
]

#: The widths ``klotho_spatial_synthdefs.scd`` precompiles, in the order it
#: writes them.  Keep in step with the ``widths`` list in that file: a width
#: here with no blob on disk reaches the engine as a missing SynthDef, which
#: is the silent failure this module exists to prevent.
PRECOMPILED_WIDTHS = (1, 2, 4, 6, 8, 12, 16, 24, 32)

#: The three family prefixes.  A def name is ``prefix + str(width)``.
SPATIAL_FAMILIES = ('__busRouter', '__spatialArrayOut', '__spatialDecode')

#: Where the precompiled blobs live.
_INFRA_DIR = Path(__file__).resolve().parent / 'assets' / 'synthdefs' / 'infra'

#: The coefficient layout the COMPILED defs hardcode.  ``__spatialDecodeN``
#: reads one ``BufRd.kr(6, bufnum, lane)`` per lane and indexes the result
#: ``c.at(0) .. c.at(5)`` positionally, so this order is baked into 9
#: compiled blobs and cannot be followed by re-reading a constant.  It is
#: checked against :data:`~klotho.thetos.spatial.BINAURAL_FIELDS` at every
#: point of use instead -- a reordering there would leave the Python side
#: agreeing with itself and disagreeing with the audio.
_COMPILED_FIELD_ORDER = ('delay_l', 'delay_r', 'gain_l', 'gain_r',
                         'shadow_l_hz', 'shadow_r_hz')


def _check_layout() -> None:
    """Refuse if ``spatial.py``'s buffer layout has moved out from under the
    compiled defs.  Called from every function that reads or writes the
    geometry buffer's field order."""
    if tuple(BINAURAL_FIELDS) != _COMPILED_FIELD_ORDER or BINAURAL_STRIDE != 6:
        raise RuntimeError(
            f"klotho.thetos.spatial's buffer layout is "
            f"{tuple(BINAURAL_FIELDS)} (stride {BINAURAL_STRIDE}) but the "
            f"compiled decoders index {_COMPILED_FIELD_ORDER} positionally "
            f"(stride 6). The .scsyndef blobs in assets/synthdefs/infra/ "
            f"would misread every lane -- a silent geometry error, not a "
            f"load failure. Recompile them from "
            f"assets/klotho_spatial_synthdefs.scd before changing this.")


_DELAY_FIELDS = (0, 1)
_GAIN_FIELDS = (2, 3)
_SHADOW_FIELDS = (4, 5)


# ------------------------------------------------------------------ guards


def check_width(n: int, max_wire_bufs: int = SCSYNTH_DEFAULT_MAX_WIRE_BUFS) -> None:
    """Refuse a width the engine could not load, before anything is compiled.

    Ruling Nine: refusal is the answer here, because the failure it prevents
    is silent.  scsynth does not raise when a SynthDef needs more
    interconnect buffers than the server has -- it prints one line, skips
    that def and keeps going.  The later ``/s_new`` then does nothing at
    all, and the composer hears nothing with no error to read.

    The cost is exactly :func:`~klotho.thetos.spatial.decoder_wire_bufs`
    per decoder -- two buffers per speaker, measured at every width from 1
    to 64 -- so on stock boot options the ceiling is
    :data:`~klotho.thetos.spatial.MAX_DECODER_SPEAKERS` (32), with no
    headroom at all at 32.
    """
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError(
            f"speaker count must be an int, got {n!r} ({type(n).__name__}).")
    if n < 1:
        raise ValueError(
            f"a decoder needs at least one speaker lane, got n={n}.")
    need = decoder_wire_bufs(n)
    if need > max_wire_bufs:
        fits = max_wire_bufs // DECODER_WIRE_BUFS_PER_SPEAKER
        raise ValueError(
            f"a {n}-lane binaural decoder needs {need} interconnect buffers "
            f"and the engine has {max_wire_bufs}, which fits {fits} speakers. "
            f"scsynth would not refuse this: it prints one line, skips the "
            f"SynthDef, and the score then plays SILENTLY. Fold this array "
            f"offline instead (klotho.thetos.spatial.fold_to_stereo has no "
            f"delay-line or wire-buffer limit -- though it takes a "
            f"SpeakerArray, which itself refuses more than "
            f"{MAX_DECODER_SPEAKERS} speakers, so a wider rig must be split "
            f"before it can be folded), or boot the engine with "
            f"maxWireBufs >= "
            f"{need} -- one wire buffer is bufLength * 4 bytes, so {need} of "
            f"them is {need * 128 * 4 // 1024} KiB.")


def check_coefficients(flat, n: int, *,
                       max_delay: float = DECODER_MAX_DELAY_S) -> None:
    """Refuse a geometry table the decoder cannot survive, before uploading it.

    *flat* is :meth:`~klotho.thetos.spatial.BinauralCoefficients.flat` --
    ``6 * n`` floats, lane-major, ``index = lane * 6 + field``.

    The SynthDef has no clamp on the shadow cutoff, deliberately: a clamp
    silently CORRECTS a bad table where a refusal NAMES the lane.  Three
    things were measured about what the graph does with a bad table, by
    rendering audio through scsynth, and they decide what is checked here:

    * **every field zero** renders SILENCE.  ``OnePole``'s input gain is
      ``1 - |coef|``, and a 0 Hz cutoff gives ``coef = 1``, so the lane is
      muted rather than unstable.  Refused: a table of zeros arriving here
      means the caller built one wrong, and a silent array is the failure
      this module exists to prevent.  (This is NOT the same thing as the
      asynchronous ``/b_alloc`` race, where the BUFFER is transiently zero
      before its fill lands; that one self-heals and is handled by the
      ``/sync`` fence on the control-buffer path, not here.  This function
      sees the table Python is about to send, never the buffer.)
    * **a negative cutoff** gives ``coef = exp(+x) > 1`` and the filter
      diverges: measured peak 8.0e17 in a two-second render, finite but
      ruinous, and it poisons the shared output bus rather than one lane.
      No arithmetic in ``spatial.py`` can produce it -- ``shadow_*_hz`` is
      bounded to ``[SHADOW_LO_HZ, SHADOW_HI_HZ]`` by construction -- so it
      means the buffer was written by hand.
    * **a delay past the delay line** neither errors nor clamps to the
      line's length, as one might assume: measured, the lane goes
      completely SILENT.  0.330 s arrives at sample 15840 exactly; 0.400 s
      produces nothing at all, with no message from scsynth.  One speaker
      quietly dropping out of a 24-speaker array is the worst of the three,
      because it is the one nobody notices.
    """
    _check_layout()
    flat = list(flat)
    if len(flat) != n * BINAURAL_STRIDE:
        raise ValueError(
            f"a {n}-lane geometry table is {n * BINAURAL_STRIDE} floats "
            f"({BINAURAL_STRIDE} per lane), got {len(flat)}. Upload "
            f"BinauralCoefficients.flat() verbatim into a buffer allocated "
            f"as {n} frames of {BINAURAL_STRIDE} CHANNELS -- "
            f"'{n * BINAURAL_STRIDE} frames of 1' holds the same floats in "
            f"an order the decoder misreads.")
    for lane in range(n):
        base = lane * BINAURAL_STRIDE
        for f in _SHADOW_FIELDS:
            hz = flat[base + f]
            if not (hz > 0.0):
                raise ValueError(
                    f"lane {lane}'s {BINAURAL_FIELDS[f]} is {hz!r}. The "
                    f"decoder turns it into a one-pole coefficient "
                    f"exp(-2*pi*fc/sr): at 0 Hz that is 1.0 and the lane goes "
                    f"SILENT, and below 0 Hz it is greater than 1 and the "
                    f"filter diverges (measured peak 8.0e17). "
                    f"SpeakerArray.binaural_coefficients cannot produce "
                    f"either; this table was not built by it.")
        for f in _DELAY_FIELDS:
            s = flat[base + f]
            if not (0.0 <= s <= max_delay):
                raise ValueError(
                    f"lane {lane}'s {BINAURAL_FIELDS[f]} is {s} s, outside "
                    f"the decoder's 0..{max_delay} s delay line. DelayN "
                    f"neither raises nor clamps: measured, that lane goes "
                    f"SILENT and scsynth says nothing, so one speaker would "
                    f"drop out of the array unnoticed. Pass "
                    f"max_delay=DECODER_MAX_DELAY_S to binaural_coefficients "
                    f"so the refusal happens there with the listener position "
                    f"in hand, or fold this array offline with "
                    f"klotho.thetos.spatial.fold_to_stereo, which has no "
                    f"delay limit.")
        for f in _GAIN_FIELDS:
            g = flat[base + f]
            if not (0.0 <= g <= 1.0):
                raise ValueError(
                    f"lane {lane}'s {BINAURAL_FIELDS[f]} is {g}. Gains are "
                    f"linear and normalized so the near ear is exactly 1.0.")


# ------------------------------------------------------------- the family


def _family_name(prefix: str, n: int) -> str:
    """``prefix + str(n)``, refusing a width the family cannot carry.

    The cap is the DECODER's -- a router or an array-out of the same width
    is a cheaper graph -- but it binds all three names, because a rig uses
    the three at ONE width and a router whose decoder cannot load routes
    into silence.  ``SpeakerArray`` refuses more than
    ``MAX_DECODER_SPEAKERS`` for the same reason.
    """
    if prefix not in SPATIAL_FAMILIES:
        raise ValueError(
            f"{prefix!r} is not a spatial family; expected one of "
            f"{list(SPATIAL_FAMILIES)}.")
    check_width(n)
    return _compose(prefix, n)


def _compose(prefix: str, n: int) -> str:
    """The unchecked spelling.  The single place a family name is built, so
    a name and :func:`parse_def_name` can never disagree about the form."""
    return f"{prefix}{n}"


def decoder_name(n: int) -> str:
    """``'__spatialDecode24'`` for ``n = 24``.

    The name does NOT record which compiler produced the def: a width the
    ``.scd`` precompiled and one built here at lowering time are the same
    graph and answer to the same name, so a caller never has to branch on
    the width to know what to call.  Use :func:`is_precompiled` (or
    :func:`defs_for_width`) to learn whether the bytes are already on disk
    or have to be ``/d_recv``-ed.
    """
    return _family_name('__spatialDecode', n)


def router_name(n: int) -> str:
    """``'__busRouter24'`` for ``n = 24``.

    Note ``__busRouter`` with no digits is a DIFFERENT def -- the stock
    2-channel router that predates this family -- and is not what
    ``router_name(2)`` returns.
    """
    return _family_name('__busRouter', n)


def array_out_name(n: int) -> str:
    """``'__spatialArrayOut24'`` for ``n = 24``."""
    return _family_name('__spatialArrayOut', n)


def is_precompiled(n) -> bool:
    """Whether width *n* has a blob bundled in ``assets/synthdefs/infra/``.

    A pure membership test against :data:`PRECOMPILED_WIDTHS`.  It is
    deliberately NOT a validity check: ``is_precompiled(40)`` is ``False``
    because 40 is not in the family, not because 40 is loadable -- it is
    not, and :func:`check_width` is what says so.  Every builder calls
    :func:`check_width` itself, so a caller who trusts this ``False`` and
    goes on to build still gets the refusal before anything is compiled.
    """
    if isinstance(n, bool):      # True == 1 would otherwise report precompiled
        return False
    return n in PRECOMPILED_WIDTHS


def parse_def_name(name: str):
    """``('__spatialDecode', 24)`` for ``'__spatialDecode24'``; else ``None``.

    ``None`` for anything not a member of the width family, including the
    three defs whose names it shadows: ``'__busRouter'`` (the stock
    2-channel router -- no digits, not a family member),
    ``'__busRouterMonitor'`` and ``'__chainLimiter'``.

    The parse must ROUND-TRIP -- ``prefix + str(width) == name`` -- so
    ``'__spatialDecode024'`` is refused rather than silently read as 24.
    A name that is not one this module would ever generate is a name whose
    meaning is a guess.
    """
    if not isinstance(name, str):
        return None
    for prefix in SPATIAL_FAMILIES:
        if not name.startswith(prefix):
            continue
        tail = name[len(prefix):]
        if not tail.isdigit():
            continue
        width = int(tail)
        if width >= 1 and _compose(prefix, width) == name:
            return (prefix, width)
    return None


def precompiled_path(name: str):
    """Path to a bundled blob, or ``None`` if the name is not on disk.

    Accepts any infra def name, not only this family's, because that is the
    directory it looks in.
    """
    if not isinstance(name, str) or '/' in name or name in ('', '.', '..'):
        return None
    p = _INFRA_DIR / f"{name}.scsyndef"
    return p if p.is_file() else None


@dataclass(frozen=True)
class SpatialDefs:
    """The three def names an ``N``-wide spatial rig needs, and their source.

    ``precompiled`` says where the bytes come from, and it is the only
    thing a caller has to branch on: ``True`` means all three blobs are
    already bundled and the engine embeds them by name; ``False`` means
    they must be built (:func:`build_spatial_decoder` and friends) and sent
    with ``/d_recv`` before the first ``/s_new`` that names them.
    """

    width: int
    decoder: str
    router: str
    array_out: str
    precompiled: bool
    wire_bufs: int

    @property
    def names(self) -> tuple:
        """The three names, decoder first."""
        return (self.decoder, self.router, self.array_out)


def defs_for_width(n: int, *,
                   max_wire_bufs: int = SCSYNTH_DEFAULT_MAX_WIRE_BUFS
                   ) -> SpatialDefs:
    """What an ``n``-wide rig needs, refusing a width that would go silent.

    This is the one call a lowering path should make: it validates the
    width against the engine's wire-buffer budget FIRST (so an over-wide
    array is refused here rather than discovered as silence at the
    concert), then reports the three def names and whether their bytes are
    bundled.
    """
    check_width(n, max_wire_bufs)
    return SpatialDefs(
        width=n,
        decoder=_compose('__spatialDecode', n),
        router=_compose('__busRouter', n),
        array_out=_compose('__spatialArrayOut', n),
        precompiled=is_precompiled(n),
        wire_bufs=decoder_wire_bufs(n),
    )


# ------------------------------------------------- runtime (Supriya) builds


def _builder():
    """Supriya's ``SynthDefBuilder`` and ``ugens``, imported on use.

    Supriya is not a Klotho dependency; only a caller who actually needs an
    off-family width has to have it installed, and every lookup and guard
    above works without it.
    """
    try:
        from supriya import SynthDefBuilder, ugens
    except ImportError as exc:            # pragma: no cover - env-dependent
        raise ImportError(
            f"building an off-family spatial SynthDef needs Supriya, which "
            f"Klotho does not depend on ({exc}). Install supriya, or use one "
            f"of the precompiled widths {list(PRECOMPILED_WIDTHS)}, which "
            f"need nothing installed.") from exc
    return SynthDefBuilder, ugens


def build_spatial_decoder(n: int, *,
                          max_delay: float = DECODER_MAX_DELAY_S,
                          name: str | None = None):
    """The ``n``-lane binaural-lite decoder, as a compilable SynthDef.

    Reads a geometry buffer holding
    :meth:`~klotho.thetos.spatial.BinauralCoefficients.flat` verbatim,
    allocated as ``n`` frames of **6 channels** -- so one
    ``BufRd.kr(6, buf, lane)`` returns that lane's six coefficients as a
    single UGen.  ``n * 6`` frames of 1 channel holds the same floats and
    is read as six CONSECUTIVE lanes' worth of numbers: a silent geometry
    error, not a load failure.

    The head shadow is a ONE-POLE, matching the offline fold's ``_one_pole``
    (``lfilter([1 - a], [1, -a])`` with ``a = exp(-2 pi fc / sr)``) in slope
    as well as corner; ``OnePole.ar(in, coef)`` is
    ``out(i) = (1 - |coef|) * in(i) + coef * out(i-1)``, the same filter
    when ``coef == a``.  An ``LPF`` would be two poles and 12 dB/octave, so
    the live preview and the offline fold would disagree about everything
    above the corner.  ``SampleDur.ir`` supplies ``1/sr`` at synth start,
    hoisted once for the whole graph, so the def is correct at whatever
    rate the engine actually booted.

    Not byte-identical to the sclang def of the same width, and byte
    equality is the wrong bar: the two compilers order the CONSTANT POOL
    differently.  What is identical is the UGen sequence, the constant set,
    and -- proven by rendered audio -- the sound.
    """
    check_width(n)
    _check_layout()
    SynthDefBuilder, ugens = _builder()
    with SynthDefBuilder(inBus=0, outBus=0, bufnum=0, gain=1.0) as builder:
        lanes = ugens.In.ar(bus=builder['inBus'], channel_count=n)
        if n == 1:                  # a bare OutputProxy, not a sequence
            lanes = [lanes]
        # The constant on the LEFT, as ``-2pi * SampleDur.ir`` is written in
        # the .scd.  Multiplication is commutative and the sound is the
        # same either way, but both compilers emit the operands in source
        # order, so writing it the other way round leaves the two graphs
        # differing in one input pair for no reason -- and that difference
        # is noise a structural comparison then has to be taught to ignore.
        neg_tau = (-2.0 * math.pi) * ugens.SampleDur.ir()
        ls, rs = [], []
        for k in range(n):
            c = ugens.BufRd.kr(buffer_id=builder['bufnum'],
                               channel_count=BINAURAL_STRIDE,
                               phase=k, loop=0, interpolation=1)
            lane = lanes[k]
            wet_l = ugens.DelayN.ar(source=lane, maximum_delay_time=max_delay,
                                    delay_time=c[0]) * c[2]
            wet_r = ugens.DelayN.ar(source=lane, maximum_delay_time=max_delay,
                                    delay_time=c[1]) * c[3]
            ls.append(ugens.OnePole.ar(
                source=wet_l, coefficient=(c[4] * neg_tau).exponential()))
            rs.append(ugens.OnePole.ar(
                source=wet_r, coefficient=(c[5] * neg_tau).exponential()))
        # Mix, not the builtin sum: Mix folds with Sum4/Sum3 (8 UGens per
        # ear at n = 24) where a left fold of BinaryOpUGens costs 23.
        ugens.Out.ar(bus=builder['outBus'],
                     source=[ugens.Mix.new(ls) * builder['gain'],
                             ugens.Mix.new(rs) * builder['gain']])
    return builder.build(name=name or decoder_name(n))


def build_bus_router(n: int, *, name: str | None = None):
    """The ``n``-wide track/main router -- the ``N``-channel twin of
    ``__busRouter``.  ``ReplaceOut`` onto its own bus so inserts and stem
    taps still see the post-gain signal, plus ``Out`` to the next bus."""
    check_width(n)
    SynthDefBuilder, ugens = _builder()
    with SynthDefBuilder(inBus=0, outBus=0, gain=1.0) as builder:
        sig = ugens.In.ar(bus=builder['inBus'], channel_count=n) * builder['gain']
        ugens.ReplaceOut.ar(bus=builder['inBus'], source=sig)
        ugens.Out.ar(bus=builder['outBus'], source=sig)
    return builder.build(name=name or router_name(n))


def build_spatial_array_out(n: int, *, name: str | None = None):
    """Mirror the ``n``-wide private array bus to consecutive hardware
    channels, for ``export='array'`` captures."""
    check_width(n)
    SynthDefBuilder, ugens = _builder()
    with SynthDefBuilder(inBus=0, outBus=2, gain=1.0) as builder:
        sig = ugens.In.ar(bus=builder['inBus'], channel_count=n) * builder['gain']
        ugens.Out.ar(bus=builder['outBus'], source=sig)
    return builder.build(name=name or array_out_name(n))
