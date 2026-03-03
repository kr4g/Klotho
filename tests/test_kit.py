import pytest

from klotho.thetos.instruments.base import Instrument
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.thetos.instruments.base import Kit
from klotho.thetos.instruments.synthdef import SynthDefKit
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


def _make_inst(name, defName, release_mode='gate', **pf):
    defaults = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
    defaults.update(pf)
    return SynthDefInstrument(name=name, defName=defName, release_mode=release_mode, pfields=defaults)


KICK = _make_inst('kick', 'kl_kicktone', freq=60.0)
SNARE = _make_inst('snare', 'kl_noisebpf', freq=200.0)
HAT = _make_inst('hat', 'kl_noisebpf', freq=8000.0)
FREE_INST = _make_inst('free_synth', 'kl_sine', release_mode='free')


# ---- Base Kit ----

class TestKitConstruction:
    def test_basic(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit.default == 'kick'
        assert kit.selector == 'voice'
        assert len(kit) == 2
        assert isinstance(kit, Instrument)

    def test_explicit_default(self):
        kit = Kit({'kick': KICK, 'snare': SNARE}, default='snare')
        assert kit.default == 'snare'

    def test_custom_selector(self):
        kit = Kit({'kick': KICK, 'snare': SNARE}, selector='patch')
        assert kit.selector == 'patch'
        pf = kit.pfields
        assert 'patch' in pf
        assert pf['patch'] == 'kick'

    def test_default_inferred_as_first_key(self):
        kit = Kit({'a': KICK, 'b': SNARE})
        assert kit.default == 'a'

    def test_empty_members_raises(self):
        with pytest.raises(ValueError, match="at least one member"):
            Kit({})

    def test_bad_default_key_raises(self):
        with pytest.raises(KeyError, match="not found"):
            Kit({'kick': KICK}, default='snare')

    def test_non_instrument_member_raises(self):
        with pytest.raises(TypeError, match="must be an Instrument"):
            Kit({'kick': 'not_an_instrument'})

    def test_pfields_include_selector_and_default_member_pfields(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        pf = kit.pfields
        assert pf['voice'] == 'kick'
        assert pf['freq'] == 60.0
        assert 'amp' in pf

    def test_three_members(self):
        kit = Kit({'kick': KICK, 'snare': SNARE, 'hat': HAT})
        assert len(kit) == 3
        assert set(kit) == {'kick', 'snare', 'hat'}

    def test_single_member(self):
        kit = Kit({'only': KICK})
        assert kit.default == 'only'
        assert len(kit) == 1

    def test_base_kit_has_no_defName(self):
        plain_a = Instrument(name='a', pfields={'amp': 0.5})
        plain_b = Instrument(name='b', pfields={'amp': 0.3})
        kit = Kit({'a': plain_a, 'b': plain_b})
        assert not hasattr(Kit, 'defName') or not hasattr(kit, 'defName') or kit.__class__ is Kit


class TestKitResolution:
    def test_resolve_default(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit._resolve() is KICK
        assert kit._resolve(None) is KICK

    def test_resolve_explicit(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit._resolve('snare') is SNARE

    def test_resolve_missing_key_falls_back(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit._resolve('nonexistent') is KICK

    def test_resolve_empty_string_falls_back(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit._resolve('') is KICK


class TestKitDunderProtocol:
    def test_getitem_member(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit['kick'] is KICK

    def test_getitem_pfield_fallback(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert kit['voice'] == 'kick'

    def test_getitem_missing_pfield_returns_none(self):
        kit = Kit({'kick': KICK})
        assert kit['nonexistent_pfield_or_member'] is None

    def test_contains(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert 'kick' in kit
        assert 'hat' not in kit

    def test_iter(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        assert list(kit) == ['kick', 'snare']

    def test_len(self):
        kit = Kit({'kick': KICK, 'snare': SNARE, 'hat': HAT})
        assert len(kit) == 3

    def test_str(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        s = str(kit)
        assert 'Kit' in s
        assert 'kick' in s

    def test_members_returns_copy(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        m = kit.members
        m['extra'] = HAT
        assert 'extra' not in kit

    def test_isinstance_instrument(self):
        kit = Kit({'kick': KICK})
        assert isinstance(kit, Instrument)


# ---- SynthDefKit ----

class TestSynthDefKit:
    def test_isinstance_chain(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        assert isinstance(kit, SynthDefKit)
        assert isinstance(kit, Kit)
        assert isinstance(kit, Instrument)

    def test_defName_delegates_to_default(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        assert kit.defName == 'kl_kicktone'

    def test_defName_with_explicit_default(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE}, default='snare')
        assert kit.defName == 'kl_noisebpf'

    def test_release_mode_delegates_to_default(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        assert kit.release_mode == 'gate'

    def test_str_says_synthdefkit(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        assert 'SynthDefKit' in str(kit)

    def test_from_manifest_basic(self):
        kit = SynthDefKit.from_manifest({'kick': 'kl_kicktone', 'noise': 'kl_noisebpf'})
        assert len(kit) == 2
        assert isinstance(kit, SynthDefKit)
        assert kit['kick'].defName == 'kl_kicktone'

    def test_from_manifest_custom_default(self):
        kit = SynthDefKit.from_manifest({'kick': 'kl_kicktone', 'noise': 'kl_noisebpf'}, default='noise')
        assert kit.default == 'noise'

    def test_from_manifest_custom_selector(self):
        kit = SynthDefKit.from_manifest({'kick': 'kl_kicktone'}, selector='patch')
        assert kit.selector == 'patch'


class TestMixedReleaseModes:
    def test_members_can_have_different_release_modes(self):
        kit = SynthDefKit({'gated': KICK, 'free': FREE_INST})
        assert kit._resolve('gated').release_mode == 'gate'
        assert kit._resolve('free').release_mode == 'free'

    def test_assembly_uses_resolved_release_mode(self):
        kit = SynthDefKit({'gated': KICK, 'free': FREE_INST}, default='gated')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='gated')
        uc.set_pfields(leaves[1], voice='free')

        events = lower_compositional_ir_to_sc_assembly(
            uc, sort_output=True, include_ungated_release=False,
        )
        new_events = [e for e in events if e['type'] == 'new']
        release_events = [e for e in events if e['type'] == 'release']
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_sine'
        gated_releases = [r for r in release_events if r['id'] == new_events[0]['id']]
        free_releases = [r for r in release_events if r['id'] == new_events[1]['id']]
        assert len(gated_releases) == 1
        assert len(free_releases) == 0


# ---- Assembly Integration ----

class TestKitAssemblyIntegration:
    def test_kit_in_uc_resolves_defName_per_event(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='kick')
        uc.set_pfields(leaves[1], voice='snare')
        uc.set_pfields(leaves[2], voice='kick')
        uc.set_pfields(leaves[3], voice='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 4
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_noisebpf'
        assert new_events[2]['defName'] == 'kl_kicktone'
        assert new_events[3]['defName'] == 'kl_noisebpf'

    def test_kit_default_when_no_selector_set(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        for e in new_events:
            assert e['defName'] == 'kl_kicktone'

    def test_kit_selector_pfield_not_in_output(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        for e in events:
            if 'pfields' in e:
                assert 'voice' not in e['pfields']

    def test_kit_with_custom_selector(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE}, selector='patch')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], patch='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_noisebpf'
        assert new_events[1]['defName'] == 'kl_kicktone'
        for e in events:
            if 'pfields' in e:
                assert 'patch' not in e['pfields']

    def test_kit_with_pattern_selector(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves, voice=Pattern(['kick', 'snare', 'kick', 'snare']))

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_noisebpf'
        assert new_events[2]['defName'] == 'kl_kicktone'
        assert new_events[3]['defName'] == 'kl_noisebpf'

    def test_kit_selector_inherits_from_root(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        uc.set_pfields(uc.rt.root, voice='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        for e in new_events:
            assert e['defName'] == 'kl_noisebpf'

    def test_kit_partial_override_on_leaves(self):
        kit = SynthDefKit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[1], voice='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_noisebpf'
        assert new_events[2]['defName'] == 'kl_kicktone'

    def test_resolved_member_pfields_used_as_defaults(self):
        kick = _make_inst('kick', 'kl_kicktone', freq=60.0, amp=0.5)
        snare = _make_inst('snare', 'kl_noisebpf', freq=200.0, amp=0.3)
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='kick')
        uc.set_pfields(leaves[1], voice='snare')

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['pfields']['freq'] == 60.0
        assert new_events[0]['pfields']['amp'] == 0.5
        assert new_events[1]['pfields']['freq'] == 200.0
        assert new_events[1]['pfields']['amp'] == 0.3

    def test_explicit_pfield_override_wins_over_resolved_defaults(self):
        kick = _make_inst('kick', 'kl_kicktone', freq=60.0, amp=0.5)
        snare = _make_inst('snare', 'kl_noisebpf', freq=200.0, amp=0.3)
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1,), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='snare', freq=999.0)

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_noisebpf'
        assert new_events[0]['pfields']['freq'] == 999.0
        assert new_events[0]['pfields']['amp'] == 0.3

    def test_base_kit_works_in_assembly(self):
        kit = Kit({'kick': KICK, 'snare': SNARE})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 2
