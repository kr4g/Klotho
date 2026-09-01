"""Tests: the ``io.json`` bus-I/O sidecar.

``manifest.json`` records control names and defaults but neither channel
count nor rate, and its shape is frozen (the widget consumes it verbatim as
``__klothoManifest``).  ``io.json`` is the sidecar that records how wide each
compiled SynthDef's bus I/O is, so a caller can tell a 2-channel insert from
a 24-channel one without booting an audio engine.

Three things are pinned here:

1. **The two sidecars stay in step.**  Every ``manifest.json`` key has an
   ``io.json`` record and vice versa.  A missing key must mean "the sidecar
   is stale", never "this def has no width" -- so the absence of a key is a
   failure, not a shrug.
2. **The exceptions.**  Six defs write twice and one writes at control rate.
   They are named individually, because they are exactly what a future
   width validator trips on, and an asset rebuild that changes one should
   say so loudly rather than quietly widening a def.
3. **Regeneration is deterministic.**  A generated file that reorders itself
   produces noisy diffs forever.
"""

import json

import pytest

from klotho.utils.playback.supersonic.scripts import regenerate_manifest as rm

# Tolerated so a missing sidecar fails as ``test_io_json_exists_and_parses``
# rather than as a collection error naming nothing in particular.
_IO = json.loads(rm._IO_PATH.read_text()) if rm._IO_PATH.exists() else {}
_MANIFEST = json.loads(rm._MANIFEST_PATH.read_text())
_KINDS = json.loads(rm._KINDS_PATH.read_text())

#: Defs that emit more than one bus-writer UGen.  The three ``__*`` routers
#: write 2 channels to two *different* buses (``ReplaceOut(inBus)`` clears
#: the source, ``Out(outBus)`` emits); the three ``fd_*`` are sclang
#: multichannel-expanding one ``Out.ar`` into two 2-channel writes to the
#: *same* bus, which sum.  Both are 2 channels wide.
MULTI_WRITER = [
    '__busRouter', '__busRouterMonitor', '__chainLimiter',
    'fd_glass', 'fd_longsaw', 'fd_quin',
]

#: The only def in the tree that does not write 2 audio channels.
CONTROL_RATE_WRITER = '__klEnvCtrl'


def _names(kind):
    return sorted(n for n, k in _KINDS.items() if k == kind)


class TestSidecarContract:
    def test_io_json_exists_and_parses(self):
        assert rm._IO_PATH.exists(), rm._IO_PATH
        assert isinstance(_IO, dict) and _IO

    def test_covers_manifest_exactly(self):
        missing = sorted(set(_MANIFEST) - set(_IO))
        extra = sorted(set(_IO) - set(_MANIFEST))
        assert not missing, f"in manifest.json but not io.json: {missing}"
        assert not extra, f"in io.json but not manifest.json: {extra}"

    def test_record_shape(self):
        for name, rec in _IO.items():
            assert list(rec) == ['ins', 'outs', 'reads', 'writes'], name
            for width in (rec['ins'], rec['outs']):
                assert width is None or isinstance(width, int), name
            for side in ('reads', 'writes'):
                for entry in rec[side]:
                    assert list(entry) == ['ugen', 'rate', 'channels'], name
                    assert isinstance(entry['ugen'], str), name
                    assert entry['rate'] in ('audio', 'control', 'scalar', 'demand'), name

    def test_scalar_widths_agree_with_the_entry_lists(self):
        """``ins``/``outs`` are the widest single read/write, 0 for none."""
        for name, rec in _IO.items():
            assert rec['ins'] == max(
                (e['channels'] for e in rec['reads']), default=0), name
            assert rec['outs'] == max(
                (e['channels'] for e in rec['writes']), default=0), name

    def test_no_underivable_widths_in_the_bundled_assets(self):
        unknown = sorted(n for n, r in _IO.items()
                         if r['ins'] is None or r['outs'] is None)
        assert not unknown, f"recorded as null (refuse, do not guess): {unknown}"

    def test_disk_matches_freshly_built(self):
        """The checked-in asset is what the generator produces today."""
        _, _, io = rm.build_manifest()
        assert rm._IO_PATH.read_text() == json.dumps(io, indent=2) + "\n"

    def test_frozen_sidecars_unperturbed(self):
        """Adding io.json must not have moved manifest.json or kinds.json."""
        manifest, kinds, _ = rm.build_manifest()
        assert rm._MANIFEST_PATH.read_text() == json.dumps(manifest, indent=2) + "\n"
        assert rm._KINDS_PATH.read_text() == json.dumps(kinds, indent=2) + "\n"


class TestSpotChecks:
    """Hand-verified against the ``.scd`` sources in ``assets/``."""

    def test_kl_saw(self):
        # ``sig = Pan2.ar(sig, pan); Out.ar(out, sig);`` -- no bus read.
        assert _IO['kl_saw'] == {
            'ins': 0, 'outs': 2, 'reads': [],
            'writes': [{'ugen': 'Out', 'rate': 'audio', 'channels': 2}],
        }

    def test_bus_router(self):
        # ``In.ar(inBus, 2)`` ... ``ReplaceOut.ar(inBus, sig); Out.ar(outBus, sig);``
        # -- the ReplaceOut clears the source bus, the Out emits.  Order is
        # graph order, so the clear precedes the emit.
        assert _IO['__busRouter'] == {
            'ins': 2, 'outs': 2,
            'reads': [{'ugen': 'In', 'rate': 'audio', 'channels': 2}],
            'writes': [
                {'ugen': 'ReplaceOut', 'rate': 'audio', 'channels': 2},
                {'ugen': 'Out', 'rate': 'audio', 'channels': 2},
            ],
        }

    def test_kl_reverb(self):
        # ``In.ar(inBus, 2)`` ... ``ReplaceOut.ar(outBus, sig);`` -- one
        # writer, so a processor rather than a router.
        assert _IO['kl_reverb'] == {
            'ins': 2, 'outs': 2,
            'reads': [{'ugen': 'In', 'rate': 'audio', 'channels': 2}],
            'writes': [{'ugen': 'ReplaceOut', 'rate': 'audio', 'channels': 2}],
        }

    def test_kl_env_ctrl(self):
        # ``Out.kr(bus, BufRd.kr(1, ...))`` -- one control channel.
        assert _IO[CONTROL_RATE_WRITER] == {
            'ins': 0, 'outs': 1, 'reads': [],
            'writes': [{'ugen': 'Out', 'rate': 'control', 'channels': 1}],
        }

    def test_fd_glass_expands_to_two_writes_of_the_same_width(self):
        # One ``Out.ar`` in the source; sclang multichannel-expands it.
        assert _IO['fd_glass']['outs'] == 2
        assert [w['channels'] for w in _IO['fd_glass']['writes']] == [2, 2]

    def test_offset_out_instrument(self):
        # ``OffsetOut.ar(out, Pan2.ar(snd, pan));`` -- 54 defs write this
        # way; sample-accurate onset, same 2-channel occupancy as ``Out``.
        assert _IO['chip_coinBlip'] == {
            'ins': 0, 'outs': 2, 'reads': [],
            'writes': [{'ugen': 'OffsetOut', 'rate': 'audio', 'channels': 2}],
        }


class TestKindInvariants:
    def test_every_instrument_writes_two_audio_channels_and_reads_none(self):
        for name in _names('inst'):
            rec = _IO[name]
            assert rec == {**rec, 'ins': 0, 'outs': 2}, name
            assert rec['reads'] == [], name
            for w in rec['writes']:
                assert w['ugen'] in ('Out', 'OffsetOut'), name
                assert (w['rate'], w['channels']) == ('audio', 2), name

    def test_every_effect_is_two_in_two_out_replace_out(self):
        names = _names('fx')
        assert len(names) == 30
        for name in names:
            assert _IO[name] == {
                'ins': 2, 'outs': 2,
                'reads': [{'ugen': 'In', 'rate': 'audio', 'channels': 2}],
                'writes': [{'ugen': 'ReplaceOut', 'rate': 'audio', 'channels': 2}],
            }, name

    def test_infra_is_three_routers_plus_the_envelope_writer(self):
        assert _names('infra') == [
            '__busRouter', '__busRouterMonitor', '__chainLimiter',
            '__klEnvCtrl',
        ]


class TestExceptions:
    """Everything that is not 0-in/2-out audio, named.

    A future asset rebuild that changes any of these widths fails here
    rather than surfacing as a silent routing bug.
    """

    def test_shape_distribution(self):
        counts = {}
        for rec in _IO.values():
            key = (rec['ins'], rec['outs'])
            counts[key] = counts.get(key, 0) + 1
        assert counts == {(0, 2): 149, (2, 2): 33, (0, 1): 1}
        assert sum(counts.values()) == len(_MANIFEST) == 183

    def test_multi_writer_defs_are_exactly_these_six(self):
        assert sorted(n for n, r in _IO.items() if len(r['writes']) > 1) == MULTI_WRITER

    def test_routers_write_two_buses_and_the_fd_trio_writes_one_twice(self):
        for name in ('__busRouter', '__busRouterMonitor', '__chainLimiter'):
            assert [w['ugen'] for w in _IO[name]['writes']] == ['ReplaceOut', 'Out'], name
        for name in ('fd_glass', 'fd_longsaw', 'fd_quin'):
            assert [w['ugen'] for w in _IO[name]['writes']] == ['Out', 'Out'], name

    def test_only_non_audio_writer_is_kl_env_ctrl(self):
        assert sorted(n for n, r in _IO.items()
                      if any(w['rate'] != 'audio' for w in r['writes'])) == [
            CONTROL_RATE_WRITER]

    def test_only_def_that_is_not_two_channels_out_is_kl_env_ctrl(self):
        assert sorted((n, r['outs']) for n, r in _IO.items() if r['outs'] != 2) == [
            (CONTROL_RATE_WRITER, 1)]

    def test_every_reader_reads_exactly_two_audio_channels(self):
        for name, rec in _IO.items():
            for r in rec['reads']:
                assert (r['ugen'], r['rate'], r['channels']) == ('In', 'audio', 2), name

    def test_no_def_reads_a_bus_without_also_writing_one(self):
        assert not [n for n, r in _IO.items() if r['reads'] and not r['writes']]


class TestDeterminism:
    def test_two_runs_are_byte_identical(self, tmp_path):
        outputs = []
        for run in ('a', 'b'):
            d = tmp_path / run
            d.mkdir()
            assert rm.main(['--out', str(d / 'manifest.json')]) == 0
            outputs.append({p.name: p.read_bytes() for p in sorted(d.iterdir())})
        assert set(outputs[0]) == {'io.json', 'kinds.json', 'manifest.json'}
        assert outputs[0] == outputs[1]

    def test_a_run_reproduces_the_checked_in_assets(self, tmp_path):
        assert rm.main(['--out', str(tmp_path / 'manifest.json')]) == 0
        for name in ('manifest.json', 'kinds.json', 'io.json'):
            fresh = (tmp_path / name).read_bytes()
            shipped = (rm._ASSETS_DIR / name).read_bytes()
            assert fresh == shipped, name

    def test_generated_file_ends_in_a_newline(self):
        assert rm._IO_PATH.read_text().endswith('}\n')


class TestWidthDerivation:
    """Unit tests for the refusal paths, which no bundled def exercises.

    Defence in depth: these cannot be broken by an asset rebuild, only by
    editing the generator, and they are what stops an underivable width
    from silently becoming ``2``.
    """

    def test_packed_input_writer_is_refused_not_guessed(self):
        ugen = {'name': 'Out', 'calculation_rate': 'audio',
                'inputs': [{'output': [0, 0]},
                           {'packed': {'ugen_index': 3, 'num_inputs': 4}}],
                'outputs': []}
        assert rm._writer_channels(ugen) is None

    def test_plain_writer_channels_is_inputs_minus_the_bus(self):
        ugen = {'name': 'Out', 'calculation_rate': 'audio',
                'inputs': [{'output': [0, 0]}] + [{'constant': 0.0}] * 5,
                'outputs': []}
        assert rm._writer_channels(ugen) == 5

    def test_one_underivable_entry_poisons_the_aggregate(self):
        entries = [{'channels': 2}, {'channels': None}]
        assert rm._aggregate_width(entries) is None

    def test_no_entries_is_zero_not_none(self):
        """0 = touches no bus (a fact); None = width underivable (refuse)."""
        assert rm._aggregate_width([]) == 0

    def test_aggregate_is_the_widest_single_entry_not_the_sum(self):
        assert rm._aggregate_width([{'channels': 2}, {'channels': 2}]) == 2

    def test_synth_with_no_bus_ugens_records_zero_widths(self):
        rec = rm._io_for_synth({'ugens': [
            {'name': 'SinOsc', 'calculation_rate': 'audio',
             'inputs': [], 'outputs': [2]}]})
        assert rec == {'ins': 0, 'outs': 0, 'reads': [], 'writes': []}

    def test_underivable_widths_are_reported_for_a_human_read(self):
        io = {'zz_broken': {'ins': 0, 'outs': None, 'reads': [],
                            'writes': [{'ugen': 'Out', 'rate': 'audio',
                                        'channels': None}]}}
        refusals, _ = rm._io_review_notes(io)
        assert len(refusals) == 1 and 'zz_broken' in refusals[0]


class TestGeneratorGuards:
    def test_missing_synthdefs_dir_yields_empty_not_a_partial_file(self, tmp_path):
        manifest, kinds, io = rm.build_manifest(tmp_path / 'nope')
        assert (manifest, kinds, io) == ({}, {}, {})

    def test_dry_run_writes_nothing(self, tmp_path):
        assert rm.main(['--dry-run', '--out', str(tmp_path / 'manifest.json')]) == 0
        assert list(tmp_path.iterdir()) == []


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-q']))
