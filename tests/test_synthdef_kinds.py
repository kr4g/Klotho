"""Tests: instrument/effect/infra kind split and the set_instrument guard."""

import pytest

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments._shared import load_ss_kinds, ss_synth_kind
from klotho.thetos.instruments.synthdef import SynthDefFX, SynthDefInstrument
from klotho.utils.playback._converter_base import resolve_instrument
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly

FX_NAMES = [
    'fd_bandPassFilter', 'fd_bitcrush', 'fd_chop', 'fd_combDelay',
    'fd_distortion', 'fd_filterSwell', 'fd_formantFilter',
    'fd_highPassFilter', 'fd_lowPassFilter', 'fd_overdriveDistortion',
    'fd_reverb', 'fd_spinPan', 'fd_tremolo', 'fd_wavesShapeDistortion',
    'kl_bitcrush', 'kl_chop', 'kl_delay', 'kl_distortion', 'kl_hpf',
    'kl_lpf', 'kl_reverb', 'kl_tremolo',
]
INFRA_NAMES = ['__busRouter', '__busRouterMonitor', '__chainLimiter', '__klEnvCtrl']


class TestKindsMap:
    def test_counts(self):
        kinds = load_ss_kinds()
        from collections import Counter
        counts = Counter(kinds.values())
        assert counts['fx'] == 22
        assert counts['infra'] == 4
        assert counts['inst'] >= 70

    def test_kind_lookups(self):
        assert ss_synth_kind('kl_tri') == 'inst'
        assert ss_synth_kind('kl_reverb') == 'fx'
        assert ss_synth_kind('__klEnvCtrl') == 'infra'
        assert ss_synth_kind('user_registered_something') == 'inst'


class TestClassmethodSplit:
    def test_instrument_shortcuts_survive(self):
        for m in ['tri', 'sqr', 'saw', 'kicktone', 'sine', 'jbass',
                  'noisebpf', 'ambi']:
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
