import copy
import warnings

import pytest

from klotho.thetos.instruments.base import Instrument, Effect
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefFX
from klotho.thetos.instruments.base import Kit
from klotho.thetos.instruments.synthdef import SynthDefKit
from klotho.thetos.instruments.ensemble import Ensemble, _FamilyView
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.composition.score import Score
from klotho.topos.collections.sequences import Pattern
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


def _inst(name, defName='kl_tri'):
    return SynthDefInstrument(name=name, defName=defName, pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0})


# ---- Construction ----

class TestEnsembleConstruction:
    def test_empty(self):
        ens = Ensemble('Test')
        assert ens.name == 'Test'
        assert len(ens) == 0
        assert ens.families == []
        assert ens.ungrouped == []

    def test_unnamed(self):
        ens = Ensemble()
        assert ens.name is None

    def test_add_with_family(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert len(ens) == 1
        assert 'strings' in ens.families
        assert 'vln' in ens

    def test_add_ungrouped(self):
        ens = Ensemble()
        ens.add('solo', _inst('solo'))
        assert len(ens) == 1
        assert ens.ungrouped == ['solo']
        assert ens.families == []

    def test_add_chaining(self):
        ens = Ensemble()
        result = ens.add('a', _inst('a'), family='f').add('b', _inst('b'), family='f')
        assert result is ens
        assert len(ens) == 2

    def test_add_multiple_families(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.add('fl', _inst('fl'), family='winds')
        ens.add('tpt', _inst('tpt'), family='brass')
        assert set(ens.families) == {'strings', 'winds', 'brass'}

    def test_add_duplicate_name_raises(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        with pytest.raises(ValueError, match="already exists"):
            ens.add('vln', _inst('vln2'), family='strings')

    def test_add_member_name_collides_with_family(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        with pytest.raises(ValueError, match="already a family name"):
            ens.add('strings', _inst('strings'))

    def test_add_family_name_collides_with_member(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'))
        with pytest.raises(ValueError, match="already a member name"):
            ens.add('cello', _inst('cello'), family='vln')

    def test_add_reserved_family_name_raises(self):
        for name in ('add', 'remove', 'name', 'families', 'members'):
            ens = Ensemble()
            with pytest.raises(ValueError, match="reserved"):
                ens.add('x', _inst('x'), family=name)

    def test_add_non_instrument_raises(self):
        ens = Ensemble()
        with pytest.raises(TypeError, match="Expected Instrument"):
            ens.add('x', 'not_an_instrument', family='f')

    def test_add_empty_name_raises(self):
        ens = Ensemble()
        with pytest.raises(ValueError, match="non-empty string"):
            ens.add('', _inst('x'))

    def test_add_non_string_name_raises(self):
        ens = Ensemble()
        with pytest.raises(ValueError, match="non-empty string"):
            ens.add(123, _inst('x'))


class TestEnsembleDualSignature:
    def test_single_arg_uses_instrument_name(self):
        ens = Ensemble()
        inst = _inst('vln_I')
        ens.add(inst, family='strings')
        assert 'vln_I' in ens

    def test_single_arg_non_instrument_raises(self):
        ens = Ensemble()
        with pytest.raises(TypeError, match="Single-argument"):
            ens.add('just_a_string')

    def test_two_arg_overrides_instrument_name(self):
        ens = Ensemble()
        ens.add('my_name', _inst('original'), family='f')
        assert 'my_name' in ens
        assert 'original' not in ens

    def test_single_arg_with_default_name_works(self):
        ens = Ensemble()
        inst = SynthDefInstrument(name='default', defName='kl_tri')
        ens.add(inst, family='f')
        assert 'default' not in ens.families


# ---- Remove ----

class TestEnsembleRemove:
    def test_remove_from_family(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.add('b', _inst('b'), family='f')
        ens.remove('a')
        assert 'a' not in ens
        assert 'f' in ens.families
        assert len(ens) == 1

    def test_remove_last_in_family_removes_family(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.remove('a')
        assert 'f' not in ens.families

    def test_remove_ungrouped(self):
        ens = Ensemble()
        ens.add('solo', _inst('solo'))
        ens.remove('solo')
        assert 'solo' not in ens
        assert ens.ungrouped == []

    def test_remove_nonexistent_raises(self):
        ens = Ensemble()
        with pytest.raises(KeyError, match="not found"):
            ens.remove('nope')

    def test_remove_cleans_up_inserts(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.set_inserts('f', [SynthDefFX('kl_reverb')])
        ens.remove('a')
        assert 'f' not in ens.families
        assert ens.inserts('f') == []


# ---- Family Access ----

class TestEnsembleFamilyAccess:
    def test_dot_access(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert isinstance(ens.strings, _FamilyView)
        assert 'vln' in ens.strings

    def test_subscript_family_access(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert isinstance(ens['strings'], _FamilyView)

    def test_explicit_family_method(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert isinstance(ens.family('strings'), _FamilyView)

    def test_all_three_access_paths_return_same_tagged_instrument(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        t1 = ens.strings['vln']
        t2 = ens['strings']['vln']
        t3 = ens.family('strings')['vln']
        assert t1._ensemble_family == t2._ensemble_family == t3._ensemble_family == 'strings'
        assert t1.name == t2.name == t3.name == 'vln'

    def test_family_view_getitem_returns_tagged(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        tagged = ens.strings['vln']
        assert tagged._ensemble_family == 'strings'
        assert tagged._ensemble_member == 'vln'
        assert isinstance(tagged, SynthDefInstrument)

    def test_direct_getitem_returns_untagged(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        direct = ens['vln']
        assert not hasattr(direct, '_ensemble_family')

    def test_family_view_iter(self):
        ens = Ensemble()
        ens.add('vln_I', _inst('vln_I'), family='strings')
        ens.add('vln_II', _inst('vln_II'), family='strings')
        assert list(ens.strings) == ['vln_I', 'vln_II']

    def test_family_view_len(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.add('b', _inst('b'), family='f')
        assert len(ens.f) == 2

    def test_family_view_contains(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        assert 'a' in ens.f
        assert 'c' not in ens.f

    def test_family_view_getitem_wrong_member_raises(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f1')
        ens.add('b', _inst('b'), family='f2')
        with pytest.raises(KeyError, match="not a member"):
            ens.f1['b']

    def test_nonexistent_family_dot_raises(self):
        ens = Ensemble()
        with pytest.raises(AttributeError):
            ens.nonexistent

    def test_nonexistent_family_subscript_raises(self):
        ens = Ensemble()
        with pytest.raises(KeyError):
            ens['nonexistent']

    def test_nonexistent_family_method_raises(self):
        ens = Ensemble()
        with pytest.raises(KeyError):
            ens.family('nonexistent')

    def test_each_family_access_returns_fresh_copy(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        t1 = ens.strings['vln']
        t2 = ens.strings['vln']
        assert t1 is not t2
        assert t1._ensemble_family == t2._ensemble_family


# ---- Auto-Routing ----

class TestEnsembleAutoRouting:
    def test_family_access_tags_instrument(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        tagged = ens.strings['vln']
        assert tagged._ensemble_family == 'strings'

    def test_direct_access_no_tag(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        direct = ens['vln']
        assert not hasattr(direct, '_ensemble_family')

    def test_set_instrument_autosets_group_from_family_view(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.strings['vln'])
        assert uc.get_mfield(uc.rt.root, 'group') == 'strings'

    def test_set_instrument_direct_does_not_autoset(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens['vln'])
        assert uc.get_mfield(uc.rt.root, 'group') == 'default'

    def test_autoroute_override_with_set_mfields(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.strings['vln'])
        uc.set_mfields(uc.rt.root, group='custom')
        assert uc.get_mfield(uc.rt.root, 'group') == 'custom'

    def test_autoroute_flows_through_assembly(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.strings['vln'])

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        for e in events:
            if e['type'] == 'new':
                assert e.get('group') == 'strings'

    def test_tagged_instrument_is_independent_copy(self):
        ens = Ensemble()
        inst = _inst('vln')
        ens.add('vln', inst, family='strings')
        tagged = ens.strings['vln']
        assert tagged is not inst
        assert not hasattr(inst, '_ensemble_family')

    def test_autoroute_via_pattern(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.add('fl', _inst('fl'), family='winds')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        leaves = list(uc.rt.leaf_nodes)
        pat = Pattern([ens.strings['vln'], ens.winds['fl']])
        uc.set_instrument(leaves, pat)
        assert uc.get_mfield(leaves[0], 'group') == 'strings'
        assert uc.get_mfield(leaves[1], 'group') == 'winds'

    def test_autoroute_per_leaf_different_families(self):
        ens = Ensemble()
        ens.add('mel', _inst('mel'), family='melody')
        ens.add('bass', _inst('bass'), family='low')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1), bpm=120)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_instrument(leaves[0], ens.melody['mel'])
        uc.set_instrument(leaves[1], ens.low['bass'])
        uc.set_instrument(leaves[2], ens.melody['mel'])
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0].get('group') == 'melody'
        assert new_events[1].get('group') == 'low'
        assert new_events[2].get('group') == 'melody'


# ---- Inserts ----

class TestEnsembleInserts:
    def test_set_inserts(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        fx = SynthDefFX('kl_reverb', mix=0.3)
        ens.set_inserts('strings', [fx])
        result = ens.inserts('strings')
        assert len(result) == 1
        assert result[0].defName == 'kl_reverb'

    def test_set_inserts_replaces(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.set_inserts('strings', [SynthDefFX('kl_reverb')])
        ens.set_inserts('strings', [SynthDefFX('kl_lpf')])
        result = ens.inserts('strings')
        assert len(result) == 1
        assert result[0].defName == 'kl_lpf'

    def test_set_inserts_multiple_fx(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.set_inserts('strings', [SynthDefFX('kl_reverb'), SynthDefFX('kl_lpf')])
        assert len(ens.inserts('strings')) == 2

    def test_set_inserts_bad_family_raises(self):
        ens = Ensemble()
        with pytest.raises(KeyError, match="not found"):
            ens.set_inserts('nope', [])

    def test_set_inserts_bad_type_raises(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        with pytest.raises(TypeError, match="Expected Effect"):
            ens.set_inserts('strings', ['not_an_effect'])

    def test_inserts_returns_empty_for_no_fx(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert ens.inserts('strings') == []

    def test_inserts_unknown_family_returns_empty(self):
        ens = Ensemble()
        assert ens.inserts('nope') == []

    def test_set_inserts_empty_list_clears(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.set_inserts('strings', [SynthDefFX('kl_reverb')])
        ens.set_inserts('strings', [])
        assert ens.inserts('strings') == []


# ---- Include ----

class TestEnsembleInclude:
    def test_include_default_prefix(self):
        inner = Ensemble('Strings')
        inner.add('vln', _inst('vln'), family='high')
        outer = Ensemble('Orchestra')
        outer.include(inner)
        assert 'strings_high' in outer.families
        assert 'strings_vln' in outer

    def test_include_explicit_prefix(self):
        inner = Ensemble('Strings')
        inner.add('vln', _inst('vln'), family='high')
        outer = Ensemble()
        outer.include(inner, prefix='str')
        assert 'str_high' in outer.families

    def test_include_unnamed_ensemble_uses_fallback(self):
        inner = Ensemble()
        inner.add('vln', _inst('vln'), family='high')
        outer = Ensemble()
        outer.include(inner)
        assert 'ensemble_high' in outer.families

    def test_include_collision_auto_numbers(self):
        inner1 = Ensemble('Strings')
        inner1.add('vln1', _inst('vln1'), family='high')
        inner2 = Ensemble('Strings')
        inner2.add('vln2', _inst('vln2'), family='high')
        outer = Ensemble()
        outer.include(inner1)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            outer.include(inner2)
            assert len(w) == 1
            assert 'collision' in str(w[0].message).lower()
        assert 'strings_2_high' in outer.families

    def test_include_explicit_prefix_collision_raises(self):
        inner1 = Ensemble('A')
        inner1.add('x', _inst('x'), family='f')
        inner2 = Ensemble('B')
        inner2.add('y', _inst('y'), family='f')
        outer = Ensemble()
        outer.include(inner1, prefix='same')
        with pytest.raises(ValueError, match="collision"):
            outer.include(inner2, prefix='same')

    def test_include_copies_inserts_with_fresh_uids(self):
        inner = Ensemble('FX')
        inner.add('a', _inst('a'), family='f')
        fx = SynthDefFX('kl_reverb', mix=0.5)
        inner.set_inserts('f', [fx])
        outer = Ensemble()
        outer.include(inner)
        copied = outer.inserts('fx_f')
        assert len(copied) == 1
        assert copied[0].defName == 'kl_reverb'
        assert copied[0].uid != fx.uid

    def test_include_ungrouped(self):
        inner = Ensemble('Solo')
        inner.add('click', _inst('click'))
        outer = Ensemble()
        outer.include(inner)
        assert 'solo_click' in outer
        assert 'solo_click' in outer.ungrouped

    def test_include_chaining(self):
        a = Ensemble('A')
        a.add('x', _inst('x'), family='f')
        b = Ensemble('B')
        b.add('y', _inst('y'), family='g')
        outer = Ensemble()
        result = outer.include(a).include(b)
        assert result is outer
        assert len(outer) == 2

    def test_include_preserves_family_routing_in_outer(self):
        inner = Ensemble('Str')
        inner.add('vln', _inst('vln'), family='high')
        outer = Ensemble()
        outer.include(inner)
        tagged = outer.str_high['str_vln']
        assert tagged._ensemble_family == 'str_high'


# ---- Dunder Protocol ----

class TestEnsembleDunderProtocol:
    def test_contains(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        assert 'vln' in ens
        assert 'nope' not in ens

    def test_iter(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.add('b', _inst('b'))
        items = list(ens)
        names = [name for name, _ in items]
        assert 'a' in names and 'b' in names

    def test_len(self):
        ens = Ensemble()
        ens.add('a', _inst('a'))
        ens.add('b', _inst('b'), family='f')
        assert len(ens) == 2

    def test_str(self):
        ens = Ensemble('Test')
        ens.add('a', _inst('a'), family='f')
        s = str(ens)
        assert 'Test' in s and 'f' in s

    def test_dir_includes_families(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='my_family')
        assert 'my_family' in dir(ens)


# ---- Ensemble + Kit ----

class TestEnsembleWithKit:
    def test_kit_in_ensemble(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        ens = Ensemble()
        ens.add('drums', kit, family='perc')
        assert isinstance(ens['drums'], Kit)

    def test_kit_from_family_view_tagged(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        ens = Ensemble()
        ens.add('drums', kit, family='perc')
        tagged = ens.perc['drums']
        assert tagged._ensemble_family == 'perc'
        assert isinstance(tagged, Kit)

    def test_kit_in_ensemble_assembly_with_autoroute(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        ens = Ensemble()
        ens.add('drums', kit, family='perc')

        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.perc['drums'])
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='kick')
        uc.set_pfields(leaves[1], voice='snare')

        assert uc.get_mfield(uc.rt.root, 'group') == 'perc'

        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_noisebpf'
        assert new_events[0].get('group') == 'perc'
        assert new_events[1].get('group') == 'perc'


# ---- Score.from_ensemble ----

class TestScoreFromEnsemble:
    def test_creates_tracks(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        ens.add('bass', _inst('bass'), family='low')
        s = Score()
        s.from_ensemble(ens)
        assert 'strings' in s.tracks
        assert 'low' in s.tracks

    def test_creates_tracks_with_inserts(self):
        ens = Ensemble()
        ens.add('vln', _inst('vln'), family='strings')
        fx = SynthDefFX('kl_reverb', mix=0.3)
        ens.set_inserts('strings', [fx])
        s = Score()
        s.from_ensemble(ens)
        track_inserts = s.tracks['strings']['inserts']
        assert len(track_inserts) == 1
        assert track_inserts[0].defName == 'kl_reverb'
        assert track_inserts[0].uid != fx.uid

    def test_from_ensemble_chaining(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        s = Score()
        assert s.from_ensemble(ens) is s

    def test_ungrouped_members_dont_create_tracks(self):
        ens = Ensemble()
        ens.add('solo', _inst('solo'))
        s = Score()
        s.from_ensemble(ens)
        assert 'solo' not in s.tracks

    def test_two_scores_from_same_ensemble_get_independent_fx_uids(self):
        ens = Ensemble()
        ens.add('a', _inst('a'), family='f')
        ens.set_inserts('f', [SynthDefFX('kl_reverb')])
        s1 = Score().from_ensemble(ens)
        s2 = Score().from_ensemble(ens)
        uid1 = s1.tracks['f']['inserts'][0].uid
        uid2 = s2.tracks['f']['inserts'][0].uid
        assert uid1 != uid2

    def test_full_integration(self):
        ens = Ensemble('Band')
        ens.add('lead', _inst('lead', 'kl_tri'), family='melody')
        ens.add('bass', _inst('bass', 'kl_saw'), family='low')
        ens.set_inserts('melody', [SynthDefFX('kl_reverb', mix=0.3)])

        s = Score()
        s.from_ensemble(ens)

        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.melody['lead'])
        s.add(uc)
        from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events
        payload = convert_score_to_sc_events(s)
        assert len(payload["events"]) > 0
        assert 'melody' in s.tracks
        assert 'low' in s.tracks
