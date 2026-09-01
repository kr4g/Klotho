"""Tests: instrument/effect/infra kind split and the set_instrument guard."""

import json

import pytest

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments._shared import load_ss_kinds, ss_synth_kind
from klotho.thetos.instruments.synthdef import SynthDefFX, SynthDefInstrument
from klotho.utils.playback._converter_base import resolve_instrument
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly
from klotho.utils.playback.supersonic import spatial_defs as sd
from klotho.utils.playback.supersonic.scripts import regenerate_manifest as rm

FX_NAMES = [
    'fd_bandPassFilter', 'fd_bitcrush', 'fd_chop', 'fd_combDelay',
    'fd_distortion', 'fd_filterSwell', 'fd_formantFilter',
    'fd_highPassFilter', 'fd_lowPassFilter', 'fd_overdriveDistortion',
    'fd_reverb', 'fd_spinPan', 'fd_tremolo', 'fd_wavesShapeDistortion',
    'kl_bitcrush', 'kl_chop', 'kl_delay', 'kl_distortion', 'kl_hpf',
    'kl_lpf', 'kl_reverb', 'kl_tremolo',
    'lofi_tape', 'lofi_wowFlutter', 'lofi_tapeSat', 'lofi_hissDust',
    'chip_echo', 'chip_downSampler', 'chip_chorusLite', 'chip_pulseDuck',
]
#: The infra defs that are NOT members of a width family: the stock
#: 2-channel router, its monitoring twin, the chain limiter and the
#: control-envelope writer.  Note ``__busRouter`` is a different def from
#: ``__busRouter2`` -- same shape, separate blob, and the family's name
#: parser must not read the bare one as a width.
FIXED_INFRA_NAMES = ['__busRouter', '__busRouterMonitor', '__chainLimiter',
                     '__klEnvCtrl']
INFRA_NAMES = FIXED_INFRA_NAMES        # kept: older tests import this name

#: Every infra def the tree should hold, derived from the shipped width set
#: rather than counted by hand.  Written as a derivation so that adding a
#: width to ``PRECOMPILED_WIDTHS`` and forgetting to compile its three
#: blobs FAILS here, instead of the count merely being bumped to match
#: whatever happens to be on disk.
EXPECTED_INFRA = sorted(
    FIXED_INFRA_NAMES
    + [f'{prefix}{n}'
       for prefix in sd.SPATIAL_FAMILIES for n in sd.PRECOMPILED_WIDTHS]
)

_IO = json.loads(rm._IO_PATH.read_text())


class TestKindsMap:
    def test_counts(self):
        kinds = load_ss_kinds()
        from collections import Counter
        counts = Counter(kinds.values())
        assert counts['fx'] == 30
        assert counts['infra'] == len(EXPECTED_INFRA) == 4 + 3 * 9
        assert counts['inst'] >= 70

    def test_kind_lookups(self):
        assert ss_synth_kind('kl_tri') == 'inst'
        assert ss_synth_kind('kl_reverb') == 'fx'
        assert ss_synth_kind('__klEnvCtrl') == 'infra'
        assert ss_synth_kind('user_registered_something') == 'inst'


class TestSpatialWidthFamily:
    """The ``__spatialDecodeN`` / ``__busRouterN`` / ``__spatialArrayOutN``
    families, pinned by what their names MEAN rather than by a total.

    Three claims, each of which fails differently:

    * every family member is classified ``infra`` -- so nothing routes one
      into ``set_instrument`` and no ``SynthDefInstrument`` shortcut appears
      for it;
    * the width in a def's NAME is the width of its bus I/O -- a
      ``__spatialDecode24`` that reads 16 lanes would drop eight speakers
      silently, and the name is the only thing the lowering path has to go
      on;
    * the family is COMPLETE for every shipped width -- a rig uses all
      three defs at one width, and a missing one reaches the engine as a
      name it drops without a word.
    """

    def test_the_infra_set_is_exactly_the_fixed_defs_plus_the_families(self):
        kinds = load_ss_kinds()
        assert sorted(n for n, k in kinds.items() if k == 'infra') == EXPECTED_INFRA

    def test_every_family_member_is_infra(self):
        for name in load_ss_kinds():
            if sd.parse_def_name(name):
                assert ss_synth_kind(name) == 'infra', name

    def test_no_infra_name_is_an_unrecognized_family_member(self):
        """An infra def is either one of the four fixed ones or parses as a
        family member.  A name that is neither means the parser and the
        assets have drifted apart."""
        for name, kind in load_ss_kinds().items():
            if kind != 'infra':
                continue
            assert name in FIXED_INFRA_NAMES or sd.parse_def_name(name), name

    def test_the_width_in_the_name_is_the_width_of_the_bus_io(self):
        checked = 0
        for name, record in _IO.items():
            parsed = sd.parse_def_name(name)
            if not parsed:
                continue
            prefix, width = parsed
            # The decoder folds N lanes down to a stereo pair; the router
            # and the array mirror stay N wide.
            expected_outs = 2 if prefix == '__spatialDecode' else width
            assert record['ins'] == width, name
            assert record['outs'] == expected_outs, name
            checked += 1
        assert checked == len(sd.SPATIAL_FAMILIES) * len(sd.PRECOMPILED_WIDTHS)

    def test_every_decoder_writes_a_stereo_pair(self):
        for n in sd.PRECOMPILED_WIDTHS:
            record = _IO[sd.decoder_name(n)]
            assert record['reads'] == [
                {'ugen': 'In', 'rate': 'audio', 'channels': n}], n
            assert record['writes'] == [
                {'ugen': 'Out', 'rate': 'audio', 'channels': 2}], n

    def test_every_router_clears_its_source_bus_then_emits(self):
        """``ReplaceOut(inBus)`` then ``Out(outBus)``, at full width -- the
        same shape as the stock ``__busRouter``, which is what lets an
        insert or a stem tap see the post-gain signal."""
        for n in sd.PRECOMPILED_WIDTHS:
            record = _IO[sd.router_name(n)]
            assert [w['ugen'] for w in record['writes']] == ['ReplaceOut', 'Out'], n
            assert all(w['channels'] == n for w in record['writes']), n

    def test_every_array_out_mirrors_its_width_once(self):
        for n in sd.PRECOMPILED_WIDTHS:
            record = _IO[sd.array_out_name(n)]
            assert record['writes'] == [
                {'ugen': 'Out', 'rate': 'audio', 'channels': n}], n

    def test_the_bare_bus_router_is_not_the_two_wide_family_member(self):
        """Same shape, separate defs.  If these ever collapsed into one the
        family's name parser would start reading ``__busRouter`` as a
        width, and the stock router would be reachable by a spatial
        lookup."""
        assert '__busRouter' in _IO and '__busRouter2' in _IO
        assert sd.parse_def_name('__busRouter') is None
        assert sd.router_name(2) == '__busRouter2'

    def test_the_widest_family_member_is_the_decoder_cap(self):
        from klotho.thetos.spatial import MAX_DECODER_SPEAKERS
        widths = {sd.parse_def_name(n)[1] for n in _IO if sd.parse_def_name(n)}
        assert max(widths) == MAX_DECODER_SPEAKERS

    def test_a_family_member_cannot_be_used_as_an_instrument(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)
        for name in ('__spatialDecode24', '__busRouter24', '__spatialArrayOut24'):
            with pytest.raises(TypeError, match="internal engine"):
                uc.set_instrument(uc._rt.root, name)
            with pytest.raises(TypeError, match="internal engine"):
                resolve_instrument(name)

    def test_no_shortcut_classmethod_appeared_for_a_family_member(self):
        for m in ('spatialDecode24', 'busRouter24', 'spatialArrayOut24',
                  'spatialDecode', 'busRouter24_'):
            assert not hasattr(SynthDefInstrument, m), m
            assert not hasattr(SynthDefFX, m), m


class TestClassmethodSplit:
    def test_instrument_shortcuts_survive(self):
        for m in ['tri', 'sqr', 'saw', 'kicktone', 'sine', 'jbass',
                  'noisebpf', 'ambi', 'tr808_kick', 'tr808_tom']:
            inst = getattr(SynthDefInstrument, m)()
            assert isinstance(inst, SynthDefInstrument)

    def test_fx_shortcuts_removed_from_instrument_class(self):
        for m in ['reverb', 'lpf', 'hpf', 'delay', 'tremolo', 'bitcrush',
                  'chop', 'distortion', 'spinPan', 'combDelay']:
            assert not hasattr(SynthDefInstrument, m), m

    def test_infra_shortcuts_nowhere(self):
        for m in ['busRouter', 'busRouterMonitor', 'chainLimiter', 'klEnvCtrl']:
            assert not hasattr(SynthDefInstrument, m), m
            assert not hasattr(SynthDefFX, m), m

    def test_fx_shortcuts_on_fx_class(self):
        fx = SynthDefFX.reverb(mix=0.35, room=0.8)
        assert fx.defName == 'kl_reverb'
        assert fx.args == {'mix': 0.35, 'room': 0.8}
        assert SynthDefFX.reverb_fd().defName == 'fd_reverb'
        assert SynthDefFX.lpf(freq=800).defName == 'kl_lpf'

    def test_fx_shortcut_instances_are_unique_nodes(self):
        assert SynthDefFX.reverb().uid != SynthDefFX.reverb().uid


class TestSetInstrumentGuard:
    def _uc(self):
        return CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=60)

    def test_fx_name_rejected(self):
        uc = self._uc()
        with pytest.raises(TypeError, match="effect SynthDef"):
            uc.set_instrument(uc._rt.root, 'kl_reverb')

    def test_infra_name_rejected(self):
        uc = self._uc()
        with pytest.raises(TypeError, match="internal engine"):
            uc.set_instrument(uc._rt.root, '__klEnvCtrl')

    def test_fx_wrapped_instrument_rejected(self):
        uc = self._uc()
        wolf = SynthDefInstrument(name='sneaky', defName='kl_reverb')
        with pytest.raises(TypeError, match="effect SynthDef"):
            uc.set_instrument(uc._rt.root, wolf)

    def test_pattern_resolved_fx_name_rejected(self):
        from klotho.topos.collections.sequences import Pattern
        uc = self._uc()
        with pytest.raises(TypeError, match="effect SynthDef"):
            uc.set_instrument(uc.leaves, Pattern(['kl_tri', 'kl_reverb']))

    def test_instrument_names_still_accepted(self):
        uc = self._uc()
        uc.set_instrument(uc._rt.root, 'kl_tri')
        uc.set_instrument(uc._rt.root, SynthDefInstrument.tri())

    def test_effect_instance_still_accepted_for_automation(self):
        uc = self._uc()
        fx = SynthDefFX.tremolo(rate=2.0, depth=0.5)
        uc.set_instrument(uc._rt.root, fx)
        uc.leaves.set_pfields(depth=0.8)
        events = lower_compositional_ir_to_sc_assembly(uc)
        set_events = [e for e in events if e['type'] == 'set']
        assert len(set_events) == 2
        assert all(e['id'] == fx.uid for e in set_events)


class TestResolveInstrumentGuard:
    def test_fx_string_rejected(self):
        with pytest.raises(TypeError, match="effect SynthDef"):
            resolve_instrument('kl_reverb')

    def test_infra_string_rejected(self):
        with pytest.raises(TypeError, match="internal engine"):
            resolve_instrument('__klEnvCtrl')

    def test_instrument_string_accepted(self):
        def_name, controls, has_gate = resolve_instrument('kl_tri')
        assert def_name == 'kl_tri'
        assert 'freq' in controls


class TestRuntimeRegistryKinds:
    def test_register_compiled_kind_roundtrip(self):
        from klotho.utils.playback.supersonic import registry
        registry.register_compiled('zz_test_fx', b'\x00', {'inBus': 0.0}, kind='fx')
        try:
            assert ss_synth_kind('zz_test_fx') == 'fx'
        finally:
            registry._RUNTIME.pop('zz_test_fx', None)

    def test_register_compiled_rejects_bad_kind(self):
        from klotho.utils.playback.supersonic import registry
        with pytest.raises(ValueError, match="kind"):
            registry.register_compiled('zz_bad', b'\x00', {}, kind='infra')
