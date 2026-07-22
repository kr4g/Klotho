"""Tests: path-style SynthDef names ('edm/kick' -> 'edm_kick').

The alias layer is a pure syntactic transform (``canonical_def_name``)
applied at every resolution choke point; underscore names are untouched.
"""

import pytest

from klotho.thetos.instruments._shared import (
    canonical_def_name,
    ss_synth_controls,
    synth_has_gate,
)
from klotho.thetos.instruments.synthdef import (
    SynthDefFX,
    SynthDefInstrument,
    SynthDefKit,
)
from klotho.utils.playback._converter_base import resolve_instrument
from klotho.utils.playback._sc_assembly import _resolve_event_synth


class TestCanonicalDefName:
    def test_transforms_path(self):
        assert canonical_def_name('edm/kick') == 'edm_kick'
        assert canonical_def_name('kl/saw') == 'kl_saw'
        assert canonical_def_name('lofi/glitchZap') == 'lofi_glitchZap'

    def test_idempotent(self):
        assert canonical_def_name(canonical_def_name('edm/kick')) == 'edm_kick'
        assert canonical_def_name('edm_kick') == 'edm_kick'

    def test_plain_names_pass_through(self):
        assert canonical_def_name('kl_tri') == 'kl_tri'
        assert canonical_def_name('default') == 'default'
        assert canonical_def_name('__klEnvCtrl') == '__klEnvCtrl'

    def test_non_strings_pass_through(self):
        assert canonical_def_name(None) is None
        assert canonical_def_name(3) == 3


class TestResolveInstrumentPaths:
    def test_edm_path(self):
        def_name, controls, has_gate = resolve_instrument('edm/kick')
        assert def_name == 'edm_kick'
        assert 'velocity' in controls
        assert has_gate is False

    def test_kl_path_sugar(self):
        assert resolve_instrument('kl/saw')[0] == 'kl_saw'

    def test_fd_path_sugar(self):
        assert resolve_instrument('fd/blip')[0] == 'fd_blip'

    def test_unknown_path_raises(self):
        with pytest.raises(ValueError, match="Unknown SynthDef name"):
            resolve_instrument('nope/thing')

    def test_fx_path_rejected(self):
        with pytest.raises(TypeError, match="effect SynthDef"):
            resolve_instrument('lofi/tapeSat')

    def test_underscore_names_still_work(self):
        assert resolve_instrument('fd_saw')[0] == 'fd_saw'
        assert resolve_instrument('kl_tri')[0] == 'kl_tri'


class TestConstructorPaths:
    def test_from_manifest_canonicalizes(self):
        assert SynthDefInstrument.from_manifest('fd/saw').defName == 'fd_saw'
        assert SynthDefInstrument.from_manifest('lofi/hazePad').defName == 'lofi_hazePad'

    def test_fx_canonicalizes(self):
        assert SynthDefFX('lofi/tape', mix=0.5).defName == 'lofi_tape'
        assert SynthDefFX('chip/echo').defName == 'chip_echo'


class TestAssemblyPaths:
    def test_string_instrument_canonicalized(self):
        assert _resolve_event_synth('chip/bass', 'default') == 'chip_bass'

    def test_instrument_object_defname_canonicalized(self):
        inst = SynthDefInstrument.from_manifest('edm/tom')
        assert _resolve_event_synth(inst, 'default') == 'edm_tom'


class TestKitFactories:
    def test_edm_drums_members(self):
        kit = SynthDefKit.edm_drums()
        assert kit._resolve('snare').defName == 'edm_snare'
        assert kit._resolve('deepKick').defName == 'edm_deepKick'

    def test_int_selector_wraps(self):
        kit = SynthDefKit.edm_drums()
        n = len(kit._members)
        assert kit._resolve(0).defName == 'edm_kick'
        assert kit._resolve(n).defName == 'edm_kick'

    def test_default_member(self):
        assert SynthDefKit.chip_drums().defName == 'chip_gridKick'
        assert SynthDefKit.lofi_glitch().defName == 'lofi_glitchZap'

    def test_tr808_members(self):
        kit = SynthDefKit.tr808()
        assert len(kit._members) == 16
        assert kit.defName == 'tr808_kick'
        assert kit._resolve('snare').defName == 'tr808_snare'
        assert kit._resolve(0).defName == 'tr808_kick'
        assert kit._resolve(16).defName == 'tr808_kick'

    def test_tr808_tom_tunings(self):
        kit = SynthDefKit.tr808()
        toms = ['lowTom', 'midTom', 'hiTom', 'lowConga', 'midConga', 'hiConga']
        assert all(kit._resolve(k).defName == 'tr808_tom' for k in toms)
        assert [kit._resolve(k).pfields['freq'] for k in toms] == [80, 120, 165, 165, 250, 370]


class TestManifestIntrospectionPaths:
    def test_gate_via_path(self):
        assert synth_has_gate('lofi/hazePad') is True
        assert synth_has_gate('edm/kick') is False

    def test_duration_control_via_path(self):
        assert 'duration' in ss_synth_controls('edm/sweep')
        assert 'duration' in ss_synth_controls('chip/riser')
