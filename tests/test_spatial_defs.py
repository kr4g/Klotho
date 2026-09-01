"""Tests: the ``__spatialDecodeN`` width family and its guards.

The claim this file exists to pin, in one sentence:

    A width either has a bundled SynthDef or is built at lowering time,
    and every width the engine could not load is REFUSED before anything
    is compiled or uploaded -- because the failure it prevents is silence.

That last clause is the whole point.  scsynth does not refuse a SynthDef
that needs more interconnect ("wire") buffers than the server has: it
prints ``exception in GraphDef_Load: exceeded number of interconnect
buffers``, skips that def and carries on.  The later ``/s_new`` then does
nothing and the piece plays silently, with no exception anywhere for a
composer to read.  Every refusal below is a Ruling Nine refusal: an error
that names the width is worth more than a decoder that quietly is not
there.

Deliberately NOT here: sclang or scsynth.  The defs were verified by
rendered audio (59 assertions per width against predicted arrival times,
interaural time difference, gain, the filter pole inverted back to Hz, and
mirror symmetry) at build time; re-rendering audio would put minutes into a
suite that runs in seconds.  What is checked here is everything that can go
wrong WITHOUT an audio engine: the name spelling, the width bookkeeping, and
the refusals.
"""

import glob
import os
from pathlib import Path

import pytest

from klotho.thetos.spatial import (
    BINAURAL_FIELDS,
    BINAURAL_STRIDE,
    DECODER_MAX_DELAY_S,
    MAX_DECODER_SPEAKERS,
    SCSYNTH_DEFAULT_MAX_WIRE_BUFS,
    decoder_wire_bufs,
)
from klotho.utils.playback.supersonic import spatial_defs as sd

_INFRA_DIR = (Path(sd.__file__).parent / 'assets' / 'synthdefs' / 'infra')

#: A geometry table one lane wide that the decoder can actually play:
#: 10 ms and 11 ms of delay, the near ear at unity, both cutoffs in band.
GOOD_LANE = [0.010, 0.011, 1.0, 0.9, 18000.0, 1400.0]

#: Infra defs whose names this family's prefixes shadow.  ``__busRouter``
#: is the stock 2-channel router and is NOT ``__busRouter2``.
NOT_FAMILY = ['__busRouter', '__busRouterMonitor', '__chainLimiter',
              '__klEnvCtrl']


#: Widths where Supriya's ``Mix`` folds its ``Sum4``/``Sum3`` tree with two
#: more UGens than sclang's.  Associative, so the sound is identical; the
#: per-lane wiring before the tree still has to match exactly.
MIX_FOLD_DIFFERS = (6, 24)

#: Control UGens.  Their outputs are the named parameters, in an order the
#: two compilers do not agree on, so a reference into one is normalized to
#: the parameter's NAME.
_CONTROL_UGENS = ('Control', 'TrigControl', 'AudioControl', 'LagControl')

#: UGens whose inputs may be reordered without changing the result.  sclang
#: emits ``Sum4``'s operands in the reverse of Supriya's order.
_COMMUTATIVE_UGENS = ('Sum3', 'Sum4')


def _normalized(synth):
    """A parsed synth as a compiler-independent graph.

    Folds away the two things sclang and Supriya legitimately disagree
    about -- constant-pool order (the parser already resolves each constant
    input to its VALUE) and control ordering -- and nothing else.  Every
    UGen's rate, operator, output widths and input connections survive, so
    a rewiring shows up as a difference.
    """
    names = list(synth['named_parameters'])
    controls = {i for i, u in enumerate(synth['ugens'])
                if u['name'] in _CONTROL_UGENS}

    def connection(inp):
        if 'output' in inp:
            ugen_index, output_index = inp['output']
            if ugen_index in controls:
                return ('param', names[output_index])
            return ('ugen', ugen_index, output_index)
        if 'constant' in inp:
            return ('const', round(inp['constant'], 6))
        return ('packed', tuple(sorted(inp.get('packed', {}).items())))

    out = []
    for ugen in synth['ugens']:
        if ugen['name'] in _CONTROL_UGENS:
            continue
        inputs = tuple(connection(i) for i in ugen['inputs'])
        if ugen['name'] in _COMMUTATIVE_UGENS:
            inputs = tuple(sorted(inputs))
        out.append((ugen['name'], ugen['calculation_rate'],
                    ugen['special_index'], inputs, tuple(ugen['outputs'])))
    return out


def _per_lane_section(synth):
    """The normalized graph up to the first summing UGen.

    That prefix is the per-lane body -- the ``BufRd``, the two ``DelayN``
    delays, the two gain multiplies and the two shadow filters, eight UGens
    per lane -- and it is where a geometry error would live.  What follows
    is only the mix-down.
    """
    graph = _normalized(synth)
    for i, entry in enumerate(graph):
        if entry[0] in _COMMUTATIVE_UGENS:
            return graph[:i]
    return graph


def _blobs_on_disk():
    """``{family_prefix: {width, ...}}`` read off the bundled blobs."""
    found = {}
    for path in sorted(glob.glob(os.path.join(str(_INFRA_DIR), '*.scsyndef'))):
        parsed = sd.parse_def_name(Path(path).stem)
        if parsed:
            found.setdefault(parsed[0], set()).add(parsed[1])
    return found


class TestShippedWidths:
    def test_every_precompiled_width_has_all_three_blobs(self):
        """The family is COMPLETE: a rig needs a decoder, a router and an
        array-out at the same width, and a missing one reaches the engine
        as a name it silently drops."""
        for prefix in sd.SPATIAL_FAMILIES:
            for n in sd.PRECOMPILED_WIDTHS:
                name = f'{prefix}{n}'
                assert sd.precompiled_path(name) is not None, name

    def test_the_constant_lists_exactly_what_is_on_disk(self):
        """``PRECOMPILED_WIDTHS`` is a claim about the filesystem, so it is
        checked against the filesystem rather than against itself."""
        found = _blobs_on_disk()
        assert set(found) == set(sd.SPATIAL_FAMILIES)
        for prefix, widths in found.items():
            assert widths == set(sd.PRECOMPILED_WIDTHS), prefix

    def test_the_widest_shipped_width_is_the_cap(self):
        assert max(sd.PRECOMPILED_WIDTHS) == MAX_DECODER_SPEAKERS == 32

    def test_precompiled_widths_are_sorted_and_unique(self):
        assert list(sd.PRECOMPILED_WIDTHS) == sorted(set(sd.PRECOMPILED_WIDTHS))

    def test_precompiled_path_of_an_unshipped_width_is_none(self):
        assert sd.precompiled_path('__spatialDecode13') is None

    def test_precompiled_path_refuses_a_path_rather_than_a_name(self):
        """It joins onto a directory, so a name with a separator in it must
        not be able to walk out of ``assets/synthdefs/infra``.

        The traversal below RESOLVES TO A REAL FILE -- ``infra/../infra/``
        is ``infra`` -- so a missing guard answers with a path rather than
        with ``None``.  A traversal that pointed at nothing would be
        refused by the ``is_file()`` check whether the guard existed or
        not, and would prove nothing.
        """
        assert sd.precompiled_path('../infra/__spatialDecode24') is None
        assert sd.precompiled_path('../../../etc/passwd') is None
        assert sd.precompiled_path('') is None
        assert sd.precompiled_path(None) is None


class TestFamilyLookup:
    def test_names_for_a_shipped_width(self):
        got = sd.defs_for_width(24)
        assert got.width == 24
        assert got.decoder == '__spatialDecode24'
        assert got.router == '__busRouter24'
        assert got.array_out == '__spatialArrayOut24'
        assert got.precompiled is True
        assert got.wire_bufs == 48

    def test_names_for_an_unshipped_width_are_spelled_the_same_way(self):
        """The name does not record which compiler produced the def, so a
        caller never branches on width to know what to call.  Only
        ``precompiled`` differs, and that is the flag that says whether the
        bytes have to be ``/d_recv``-ed."""
        got = sd.defs_for_width(13)
        assert (got.decoder, got.router, got.array_out) == (
            '__spatialDecode13', '__busRouter13', '__spatialArrayOut13')
        assert got.precompiled is False
        assert got.wire_bufs == 26

    def test_names_property_is_the_three_names(self):
        got = sd.defs_for_width(8)
        assert got.names == (got.decoder, got.router, got.array_out)

    def test_individual_name_helpers_agree_with_defs_for_width(self):
        for n in sd.PRECOMPILED_WIDTHS:
            got = sd.defs_for_width(n)
            assert sd.decoder_name(n) == got.decoder
            assert sd.router_name(n) == got.router
            assert sd.array_out_name(n) == got.array_out

    def test_defs_are_frozen(self):
        with pytest.raises(Exception):
            sd.defs_for_width(8).width = 9

    def test_is_precompiled_matches_the_shipped_set(self):
        for n in range(1, MAX_DECODER_SPEAKERS + 1):
            assert sd.is_precompiled(n) == (n in sd.PRECOMPILED_WIDTHS), n

    def test_true_is_not_a_width(self):
        """``True == 1`` in Python, and 1 IS a shipped width, so a boolean
        would otherwise report itself precompiled."""
        assert sd.is_precompiled(True) is False
        assert sd.is_precompiled(False) is False


class TestNameParsing:
    def test_round_trips_every_shipped_name(self):
        for prefix in sd.SPATIAL_FAMILIES:
            for n in sd.PRECOMPILED_WIDTHS:
                assert sd.parse_def_name(f'{prefix}{n}') == (prefix, n)

    def test_round_trips_an_unshipped_width(self):
        assert sd.parse_def_name('__spatialDecode13') == ('__spatialDecode', 13)

    def test_the_defs_whose_names_it_shadows_are_not_family_members(self):
        for name in NOT_FAMILY:
            assert sd.parse_def_name(name) is None, name

    def test_a_leading_zero_is_refused_not_read_as_the_number(self):
        """``'__spatialDecode024'`` is not a name this module would ever
        produce, so its meaning would be a guess."""
        assert sd.parse_def_name('__spatialDecode024') is None
        assert sd.parse_def_name('__spatialDecode24 ') is None

    def test_zero_width_is_not_a_width(self):
        assert sd.parse_def_name('__spatialDecode0') is None

    def test_non_family_names(self):
        for name in ('kl_saw', 'kl_reverb', '__spatialDecode',
                     '__spatialDecodeRT24', '__spatialDecode-4', '', 'spatialDecode4'):
            assert sd.parse_def_name(name) is None, name

    def test_non_strings(self):
        for value in (None, 24, 24.0, ['__spatialDecode24']):
            assert sd.parse_def_name(value) is None


class TestWidthRefusal:
    def test_thirty_two_fits_with_no_headroom(self):
        sd.check_width(32)
        assert decoder_wire_bufs(32) == SCSYNTH_DEFAULT_MAX_WIRE_BUFS

    def test_thirty_three_is_refused(self):
        with pytest.raises(ValueError, match='SILENTLY'):
            sd.check_width(33)

    def test_the_boundary_is_exactly_max_decoder_speakers(self):
        """``check_width`` and ``spatial.py``'s cap are the same number,
        found by walking the boundary rather than by reading a literal."""
        accepted = []
        for n in range(1, MAX_DECODER_SPEAKERS + 9):
            try:
                sd.check_width(n)
            except ValueError:
                continue
            accepted.append(n)
        assert accepted == list(range(1, MAX_DECODER_SPEAKERS + 1))

    def test_a_bigger_engine_moves_the_boundary(self):
        """The cap is derived from the engine's budget, not hardcoded."""
        sd.check_width(40, max_wire_bufs=80)
        with pytest.raises(ValueError):
            sd.check_width(41, max_wire_bufs=80)

    def test_zero_and_negative(self):
        for n in (0, -1, -32):
            with pytest.raises(ValueError, match='at least one speaker'):
                sd.check_width(n)

    def test_non_integers(self):
        for n in (2.0, '24', None, [24]):
            with pytest.raises(TypeError, match='must be an int'):
                sd.check_width(n)

    def test_bool_is_refused_even_though_it_is_an_int(self):
        with pytest.raises(TypeError, match='bool'):
            sd.check_width(True)

    def test_the_message_says_what_to_do_instead(self):
        with pytest.raises(ValueError) as exc:
            sd.check_width(40)
        message = str(exc.value)
        assert '40-lane' in message and '80 interconnect buffers' in message
        assert 'fold_to_stereo' in message and 'maxWireBufs' in message
        assert '32 speakers' in message

    def test_the_name_helpers_refuse_an_unloadable_width(self):
        """Naming a def that scsynth would skip is the first step toward
        the silence this module exists to prevent."""
        for helper in (sd.decoder_name, sd.router_name, sd.array_out_name):
            with pytest.raises(ValueError, match='SILENTLY'):
                helper(40)
            with pytest.raises(TypeError):
                helper(4.0)

    def test_defs_for_width_refuses_before_naming_anything(self):
        with pytest.raises(ValueError, match='SILENTLY'):
            sd.defs_for_width(40)


class TestCoefficientRefusal:
    def test_a_real_table_is_accepted(self):
        sd.check_coefficients(GOOD_LANE, 1)
        sd.check_coefficients(GOOD_LANE * 24, 24)

    def test_all_zero_is_refused(self):
        """Measured: every field zero renders SILENCE -- ``OnePole``'s input
        gain is ``1 - |coef|``, which is 0 when a 0 Hz cutoff makes ``coef``
        1.  A table of zeros reaching the uploader means the caller built
        one wrong."""
        with pytest.raises(ValueError, match='SILENT'):
            sd.check_coefficients([0.0] * 6, 1)
        with pytest.raises(ValueError, match='SILENT'):
            sd.check_coefficients([0.0] * 144, 24)

    def test_a_negative_cutoff_is_refused(self):
        """Measured: ``coef = exp(+x) > 1`` and the filter diverges to a
        peak of 8.0e17, poisoning the shared output rather than one lane."""
        table = list(GOOD_LANE)
        table[5] = -1400.0
        with pytest.raises(ValueError, match='diverges'):
            sd.check_coefficients(table, 1)
        table = list(GOOD_LANE)
        table[4] = -1.0
        with pytest.raises(ValueError, match='shadow_l_hz'):
            sd.check_coefficients(table, 1)

    def test_a_bad_cutoff_names_its_lane(self):
        """A refusal that cannot say WHICH lane is barely better than a
        clamp, which is why the SynthDef has no clamp."""
        table = GOOD_LANE * 24
        table[17 * BINAURAL_STRIDE + 5] = 0.0
        with pytest.raises(ValueError, match='lane 17'):
            sd.check_coefficients(table, 24)

    def test_a_delay_past_the_line_is_refused(self):
        """Measured: DelayN neither raises nor clamps -- the lane goes
        silent, and one speaker dropping out of 24 is the failure nobody
        notices."""
        table = list(GOOD_LANE)
        table[0] = DECODER_MAX_DELAY_S + 0.001
        with pytest.raises(ValueError, match='delay line'):
            sd.check_coefficients(table, 1)

    def test_a_negative_delay_is_refused(self):
        table = list(GOOD_LANE)
        table[1] = -0.001
        with pytest.raises(ValueError, match='delay_r'):
            sd.check_coefficients(table, 1)

    def test_the_delay_bound_is_the_decoders_line_length(self):
        table = list(GOOD_LANE)
        table[0] = DECODER_MAX_DELAY_S
        sd.check_coefficients(table, 1)          # exactly on the line: fine
        with pytest.raises(ValueError):
            sd.check_coefficients(table, 1, max_delay=DECODER_MAX_DELAY_S / 2)

    def test_a_gain_outside_zero_to_one_is_refused(self):
        for field in (2, 3):
            for value in (1.5, -0.1):
                table = list(GOOD_LANE)
                table[field] = value
                with pytest.raises(ValueError, match='Gains are linear'):
                    sd.check_coefficients(table, 1)

    def test_the_wrong_length_is_refused(self):
        with pytest.raises(ValueError, match='6 per lane'):
            sd.check_coefficients(GOOD_LANE * 2, 1)
        with pytest.raises(ValueError, match='6 per lane'):
            sd.check_coefficients(GOOD_LANE * 23, 24)

    def test_the_length_message_warns_about_the_buffer_shape(self):
        """``n*6`` frames of 1 channel holds the same floats in an order the
        decoder misreads -- a silent geometry error, not a load failure."""
        with pytest.raises(ValueError) as exc:
            sd.check_coefficients(GOOD_LANE * 2, 1)
        assert 'CHANNELS' in str(exc.value)

    def test_it_accepts_any_iterable_not_only_a_list(self):
        sd.check_coefficients(tuple(GOOD_LANE), 1)
        sd.check_coefficients(iter(GOOD_LANE), 1)


class TestCoefficientsFromTheRealBuilder:
    """``spatial.py`` must not be able to build a table this refuses."""

    def test_a_generated_array_passes(self):
        from klotho.thetos.spatial import SpeakerArray
        array = SpeakerArray.grid(6, 4, col_spacing=50.0, row_spacing=60.0)
        flat = array.binaural_coefficients(
            max_delay=DECODER_MAX_DELAY_S).flat()
        assert len(flat) == len(array) * BINAURAL_STRIDE == 144
        sd.check_coefficients(flat, len(array))

    def test_the_field_order_is_the_one_the_compiled_defs_index(self):
        """``__spatialDecodeN`` reads one ``BufRd.kr(6, ...)`` per lane and
        indexes ``c.at(0)..c.at(5)`` positionally, so this order is baked
        into nine compiled blobs and cannot be followed by re-reading a
        constant."""
        assert tuple(BINAURAL_FIELDS) == (
            'delay_l', 'delay_r', 'gain_l', 'gain_r',
            'shadow_l_hz', 'shadow_r_hz')
        assert BINAURAL_STRIDE == 6
        assert sd._COMPILED_FIELD_ORDER == tuple(BINAURAL_FIELDS)

    def test_a_moved_layout_is_refused_rather_than_misread(self, monkeypatch):
        monkeypatch.setattr(
            sd, '_COMPILED_FIELD_ORDER',
            ('gain_l', 'gain_r', 'delay_l', 'delay_r',
             'shadow_l_hz', 'shadow_r_hz'))
        with pytest.raises(RuntimeError, match='misread every lane'):
            sd.check_coefficients(GOOD_LANE, 1)


class TestSupriyaIsOptional:
    """Supriya is not a Klotho dependency, so every lookup and every guard
    has to work without it -- only an off-family width needs it installed.
    """

    @staticmethod
    def _without_supriya(monkeypatch):
        import builtins
        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name == 'supriya' or name.startswith('supriya.'):
                raise ImportError('no supriya (blocked by the test)')
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, '__import__', blocked)

    def test_lookups_and_guards_work_without_it(self, monkeypatch):
        self._without_supriya(monkeypatch)
        assert sd.defs_for_width(24).decoder == '__spatialDecode24'
        assert sd.is_precompiled(24) and not sd.is_precompiled(13)
        assert sd.parse_def_name('__busRouter24') == ('__busRouter', 24)
        sd.check_width(32)
        sd.check_coefficients(GOOD_LANE, 1)
        with pytest.raises(ValueError):
            sd.check_width(40)

    def test_building_without_it_says_what_is_missing(self, monkeypatch):
        self._without_supriya(monkeypatch)
        with pytest.raises(ImportError, match='needs Supriya'):
            sd.build_spatial_decoder(13)

    def test_the_module_does_not_import_supriya_at_module_scope(self):
        """Read off the source, because the two tests above cannot see it:
        the module is imported at collection time, long before they block
        ``__import__``, so a module-scope ``import supriya`` would already
        have succeeded and they would both still pass.  Break-tested --
        moving the import to module scope reddens this test and only this
        test.
        """
        source = Path(sd.__file__).read_text()
        header = source.split('def _builder', 1)[0]
        assert 'import supriya' not in header
        assert 'from supriya' not in header


class TestRuntimeBuilds:
    """The off-family path.  Supriya-only, so it skips where it is absent."""

    @pytest.fixture(autouse=True)
    def _needs_supriya(self):
        pytest.importorskip('supriya')

    def _graph(self, blob):
        from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
            parse_synthdef,
        )
        (synth,) = parse_synthdef(bytes(blob))['synths'].values()
        return synth

    def _shipped(self, name):
        from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
            parse_synthdef_file,
        )
        (synth,) = parse_synthdef_file(
            str(sd.precompiled_path(name)))['synths'].values()
        return synth

    def test_an_off_family_width_builds_under_the_expected_name(self):
        built = sd.build_spatial_decoder(13)
        assert built.name == '__spatialDecode13'
        synth = self._graph(built.compile())
        reads = [u for u in synth['ugens'] if u['name'] == 'In']
        writes = [u for u in synth['ugens'] if u['name'] == 'Out']
        assert len(reads[0]['outputs']) == 13
        assert len(writes[0]['inputs']) - 1 == 2

    def test_all_three_families_build_off_family(self):
        assert sd.build_bus_router(13).name == '__busRouter13'
        assert sd.build_spatial_array_out(13).name == '__spatialArrayOut13'

    def test_a_runtime_build_matches_the_shipped_blob_at_a_shipped_width(self):
        """The runtime build is the SAME GRAPH as the audio-verified blob.

        Not byte equality, and byte equality is the wrong bar: sclang and
        Supriya order the CONSTANT POOL differently, and Supriya sorts
        control names where sclang keeps declaration order.  What is
        compared is the graph after :func:`_normalized` folds both of those
        away -- every UGen, its rate, its operator, its OUTPUT WIDTHS and
        every one of its INPUT CONNECTIONS.

        Comparing only the UGen NAME SEQUENCE would not be enough, and this
        is not a hypothetical: swapping which buffer field feeds
        ``DelayN``'s delay time and which feeds the gain leaves the name
        sequence and the constant set untouched, and only moves two input
        references.  That mutation walked past a name-sequence check.
        """
        for n in [w for w in sd.PRECOMPILED_WIDTHS if w not in MIX_FOLD_DIFFERS]:
            for family, build in (
                    ('__spatialDecode', sd.build_spatial_decoder),
                    ('__busRouter', sd.build_bus_router),
                    ('__spatialArrayOut', sd.build_spatial_array_out)):
                shipped = self._shipped(f'{family}{n}')
                built = self._graph(build(n).compile())
                assert _normalized(shipped) == _normalized(built), f'{family}{n}'
                # Control DEFAULTS live outside the normalized graph -- it
                # resolves control references to names and drops the
                # Control UGen -- so they are compared here.  They matter:
                # ``__spatialArrayOut`` defaults ``outBus`` to 2, past the
                # stereo main, and a 0 there would mirror the array on top
                # of the main output.
                assert (shipped['named_parameters']
                        == built['named_parameters']), f'{family}{n}'

    def test_the_two_widths_where_mix_folds_differently_still_agree(self):
        """At ``n = 6`` and ``n = 24`` Supriya's ``Mix`` builds its
        ``Sum4``/``Sum3`` tree with two more UGens than sclang's.  Addition
        is associative, so the sound is the same -- verified by rendered
        audio, not by reading the graph -- and the wire-buffer count does
        not move.  What must still match exactly is everything BEFORE the
        summing tree: the per-lane delay, gain and shadow wiring, which is
        where a geometry error would live.
        """
        for n in MIX_FOLD_DIFFERS:
            shipped = self._shipped(f'__spatialDecode{n}')
            built = self._graph(sd.build_spatial_decoder(n).compile())
            assert len(built['ugens']) - len(shipped['ugens']) == 2, n
            assert sorted(shipped['constants']) == sorted(built['constants']), n
            section = _per_lane_section(shipped)
            assert section == _per_lane_section(built), n
            # One coefficient read per lane, and it is the whole lane's six
            # fields in a single UGen -- six Index.kr reads would sound the
            # same and cost five more UGens each.
            assert sum(1 for u in section if u[0] == 'BufRd') == n

    def test_the_controls_are_the_same_set_as_the_shipped_def(self):
        """Supriya sorts control names, sclang keeps declaration order --
        measured, ``inBus, outBus, bufnum, gain`` against ``bufnum, gain,
        inBus, outBus``.  ``/s_new`` addresses controls BY NAME, so the set
        and the defaults are what has to match, and the order is not
        compared (dict equality here does not compare it either).
        """
        shipped = self._shipped('__spatialDecode24')
        built = self._graph(sd.build_spatial_decoder(24).compile())
        assert shipped['named_parameters'] == built['named_parameters']
        assert set(shipped['named_parameters']) == {
            'inBus', 'outBus', 'bufnum', 'gain'}

    def test_an_unloadable_width_is_refused_before_it_is_compiled(self):
        for build in (sd.build_spatial_decoder, sd.build_bus_router,
                      sd.build_spatial_array_out):
            with pytest.raises(ValueError, match='SILENTLY'):
                build(40)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
