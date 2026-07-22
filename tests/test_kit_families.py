"""Tests: Kit families, family views/accessor, pick/cycle, selector errors."""

import random

import pytest

from klotho.thetos.instruments.base import Instrument, Kit, KitFamilyView
from klotho.thetos.instruments.synthdef import SynthDefKit
from klotho.topos.collections.sequences import Pattern

KICK = Instrument('kick', {'amp': 0.5})
SNARE = Instrument('snare', {'amp': 0.4})
HAT = Instrument('hat', {'amp': 0.3})


def _kit(**kwargs):
    return Kit({'kick': KICK, 'snare': SNARE, 'hat': HAT}, **kwargs)


class TestFamilyConstruction:
    def test_flat_kit_has_no_families(self):
        kit = _kit()
        assert kit.families == []

    def test_families_stored_in_order(self):
        kit = _kit(families={'drums': ['kick', 'snare'], 'hats': ['hat']})
        assert kit.families == ['drums', 'hats']

    def test_families_may_overlap(self):
        kit = _kit(families={'a': ['kick', 'hat'], 'b': ['hat', 'snare']})
        assert list(kit.family['a']) == ['kick', 'hat']
        assert list(kit.family['b']) == ['hat', 'snare']

    def test_family_name_colliding_with_member_raises(self):
        with pytest.raises(ValueError, match="collides with a member key"):
            _kit(families={'kick': ['snare']})

    def test_family_name_colliding_with_attribute_raises(self):
        for name in ('members', 'pick', 'cycle', 'family', 'default'):
            with pytest.raises(ValueError, match="collides with a .* attribute"):
                _kit(families={name: ['kick']})

    def test_unknown_family_member_raises(self):
        with pytest.raises(KeyError, match="unknown members"):
            _kit(families={'drums': ['kick', 'nope']})

    def test_empty_family_raises(self):
        with pytest.raises(ValueError, match="no members"):
            _kit(families={'drums': []})

    def test_non_string_family_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            _kit(families={3: ['kick']})


class TestFamilyAccess:
    def test_accessor_subscript(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        view = kit.family['drums']
        assert isinstance(view, KitFamilyView)
        assert view.name == 'drums'

    def test_accessor_iteration_and_contains(self):
        kit = _kit(families={'drums': ['kick', 'snare'], 'hats': ['hat']})
        assert list(kit.family) == ['drums', 'hats']
        assert 'hats' in kit.family and len(kit.family) == 2

    def test_dot_access(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        assert list(kit.drums) == ['kick', 'snare']

    def test_dot_access_unknown_raises_attribute_error(self):
        kit = _kit(families={'drums': ['kick']})
        with pytest.raises(AttributeError):
            kit.nope

    def test_accessor_unknown_family_raises(self):
        kit = _kit(families={'drums': ['kick']})
        with pytest.raises(KeyError, match="not a family"):
            kit.family['nope']

    def test_view_protocol(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        view = kit.drums
        assert len(view) == 2
        assert 'kick' in view and 'hat' not in view
        assert view['kick'] is KICK

    def test_view_getitem_outside_family_raises(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        with pytest.raises(KeyError, match="not a member of family"):
            kit.drums['hat']

    def test_getitem_member_precedence_unchanged(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        assert kit['kick'] is KICK
        assert kit[0] is KICK and kit[4] is SNARE


class TestPickAndCycle:
    def test_pick_all_members(self):
        kit = _kit()
        assert kit.pick(rng=random.Random(0)) in kit.members

    def test_pick_family_only_yields_family_keys(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        picks = {kit.pick('drums', rng=random.Random(i)) for i in range(20)}
        assert picks == {'kick', 'snare'}

    def test_view_pick(self):
        kit = _kit(families={'hats': ['hat']})
        assert kit.hats.pick() == 'hat'

    def test_pick_unknown_family_raises(self):
        kit = _kit(families={'drums': ['kick']})
        with pytest.raises(KeyError, match="not a family"):
            kit.pick('nope')

    def test_cycle_returns_pattern_of_keys(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        p = kit.cycle('drums')
        assert isinstance(p, Pattern)
        assert [next(p) for _ in range(4)] == ['kick', 'snare', 'kick', 'snare']

    def test_cycle_all_members(self):
        p = _kit().cycle()
        assert [next(p) for _ in range(3)] == ['kick', 'snare', 'hat']

    def test_cycle_unknown_family_raises(self):
        with pytest.raises(KeyError, match="not a family"):
            _kit().cycle('nope')


class TestSelectorErrors:
    def test_unknown_string_selector_raises(self):
        with pytest.raises(KeyError, match="Unknown voice 'typo'"):
            _kit()._resolve('typo')

    def test_family_name_selector_raises_with_hint(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        with pytest.raises(KeyError, match="'drums' is a family"):
            kit._resolve('drums')

    def test_none_and_int_selectors_unchanged(self):
        kit = _kit(families={'drums': ['kick', 'snare']})
        assert kit._resolve(None) is KICK
        assert kit._resolve(1) is SNARE
        assert kit._resolve(-1) is HAT


class TestPerLeafDistribution:
    def test_bound_pick_distributes_per_leaf(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly

        kit = SynthDefKit.tabla()
        uc = CompositionalUnit(tempus='4/4', prolatio=(1,) * 8, bpm=120, inst=kit)
        uc.set_pfields(uc.leaves, voice=kit.tas.pick)
        voices = [leaf.pfields['voice'] for leaf in uc.leaves]
        assert all(v.startswith('tabla_tas') for v in voices)
        events = [e for e in lower_compositional_ir_to_sc_assembly(uc) if e['type'] == 'new']
        assert len(events) == 8
        for e in events:
            assert str(e['pfields']['buf']).startswith('tabla_tas')


class TestBuiltinFamilies:
    def test_tabla(self):
        kit = SynthDefKit.tabla()
        assert kit.families == ['open', 'tas', 'te', 'tun']
        assert list(kit.open) == ['tabla1', 'tabla2', 'tabla3', 'tabla4']
        assert list(kit.tas) == ['tabla_tas1', 'tabla_tas2', 'tabla_tas3']
        assert list(kit.te) == ['tabla_te1', 'tabla_te2', 'tabla_te_m', 'tabla_te_ne']
        assert list(kit.tun) == ['tabla_tun1', 'tabla_tun2', 'tabla_tun3']

    def test_beatbox(self):
        kit = SynthDefKit.beatbox()
        assert kit.families == ['drums', 'hats', 'vox']
        assert list(kit.drums) == ['bb_kick', 'bb_big_kick', 'bb_snare', 'bb_snare2']
        assert list(kit.hats) == ['bb_hihat', 'bb_openhihat', 'bb_shake']

    def test_tr808(self):
        kit = SynthDefKit.tr808()
        assert kit.families == ['drums', 'toms', 'congas', 'perc', 'cymbals']
        assert list(kit.toms) == ['lowTom', 'midTom', 'hiTom']

    def test_edm_and_lofi_drums(self):
        assert SynthDefKit.edm_drums().families == ['kicks', 'snares']
        assert SynthDefKit.lofi_drums().families == ['snares', 'hats']

    def test_member_order_unchanged_by_families(self):
        kit = SynthDefKit.tabla()
        assert list(kit.members)[:4] == ['tabla1', 'tabla2', 'tabla3', 'tabla4']
        assert len(kit) == 14


class TestKitReprHtml:
    def test_smoke(self):
        html = SynthDefKit.tr808()._repr_html_()
        assert 'toms' in html and 'lowTom' in html and '<table' in html

    def test_flat_kit(self):
        html = Kit({'a': KICK})._repr_html_()
        assert 'members' in html
