"""Validate that the SC/SuperSonic assembly output conforms to the event
format expected by the browser-side scheduler.

Every ``new`` event must have: type, id, defName, start, pfields.
Every ``release`` event must have: type, id, start.
Every ``set`` event must have: type, id, start, pfields.

Pfields must be a dict of str->numeric (no leaked meta like ``voice``,
``group``, or ``_slur_*``).  ``id`` must be a non-empty hex string.
``start`` must be numeric and >= 0.
"""

import pytest

from klotho.thetos.instruments.base import Kit
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefFX, SynthDefKit
from klotho.thetos.instruments.ensemble import Ensemble
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.composition.score import Score
from klotho.topos.collections.sequences import Pattern
from klotho.dynatos.envelopes import Envelope
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly

FORBIDDEN_PFIELD_KEYS = {'group', '_slur_id', '_slur_start', '_slur_end'}


def _inst(name, defName='kl_tri', **pf):
    d = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
    d.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=d)


def _validate_assembly(events):
    assert isinstance(events, list)
    assert len(events) > 0, "Assembly produced no events"

    ids_seen = {}
    for i, e in enumerate(events):
        assert isinstance(e, dict), f"Event {i} is not a dict"
        etype = e.get('type')
        assert etype in ('new', 'release', 'set'), f"Event {i}: unknown type '{etype}'"

        eid = e.get('id')
        assert isinstance(eid, str) and len(eid) > 0, f"Event {i}: id must be non-empty str"

        start = e.get('start')
        assert isinstance(start, (int, float)), f"Event {i}: start must be numeric, got {type(start)}"
        assert start >= 0, f"Event {i}: start must be >= 0, got {start}"

        if etype == 'new':
            assert 'defName' in e, f"Event {i}: 'new' event missing defName"
            assert isinstance(e['defName'], str), f"Event {i}: defName must be str"
            assert e['defName'] != '', f"Event {i}: defName must be non-empty"
            assert 'pfields' in e, f"Event {i}: 'new' event missing pfields"
            pf = e['pfields']
            assert isinstance(pf, dict), f"Event {i}: pfields must be dict"
            for k, v in pf.items():
                assert isinstance(k, str), f"Event {i}: pfield key must be str, got {type(k)}"
                assert k not in FORBIDDEN_PFIELD_KEYS, f"Event {i}: forbidden pfield '{k}' leaked"
                assert isinstance(v, (int, float)), f"Event {i}: pfield '{k}' must be numeric, got {type(v).__name__}={v!r}"
            ids_seen[eid] = 'new'

        elif etype == 'set':
            assert 'pfields' in e, f"Event {i}: 'set' event missing pfields"
            pf = e['pfields']
            assert isinstance(pf, dict), f"Event {i}: pfields must be dict"
            for k, v in pf.items():
                assert isinstance(k, str), f"Event {i}: pfield key must be str"
                assert k not in FORBIDDEN_PFIELD_KEYS, f"Event {i}: forbidden pfield '{k}' leaked"

        elif etype == 'release':
            assert eid in ids_seen, f"Event {i}: release for unknown id '{eid[:12]}'"


class TestBasicAssemblyFormat:
    def test_single_instrument_format(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120, inst=_inst('tri'))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)

    def test_with_rests_produces_no_rest_events(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, -1, 1, -1), bpm=120, inst=_inst('tri'))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 2

    def test_new_release_pairing(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120, inst=_inst('tri'))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        new_ids = {e['id'] for e in events if e['type'] == 'new'}
        rel_ids = {e['id'] for e in events if e['type'] == 'release'}
        assert new_ids == rel_ids

    def test_events_sorted_by_start(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120, inst=_inst('tri'))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        starts = [e['start'] for e in events]
        assert starts == sorted(starts)


class TestKitAssemblyFormat:
    def test_kit_format_valid(self):
        kick = _inst('kick', 'kl_kicktone', freq=60.0)
        snare = _inst('snare', 'kl_noisebpf', freq=200.0)
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves, voice=Pattern(['kick', 'snare', 'kick', 'snare']))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)

    def test_kit_selector_never_in_pfields(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='snare')
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        for e in events:
            if 'pfields' in e:
                assert 'voice' not in e['pfields'], "selector 'voice' leaked to assembly"

    def test_kit_custom_selector_never_in_pfields(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare}, selector='patch')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], patch='snare')
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        for e in events:
            if 'pfields' in e:
                assert 'patch' not in e['pfields'], "selector 'patch' leaked to assembly"

    def test_kit_defName_resolved_correctly(self):
        kick = _inst('kick', 'kl_kicktone')
        snare = _inst('snare', 'kl_noisebpf')
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='kick')
        uc.set_pfields(leaves[1], voice='snare')
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['defName'] == 'kl_kicktone'
        assert new_events[1]['defName'] == 'kl_noisebpf'

    def test_kit_pfield_values_match_resolved_member(self):
        kick = _inst('kick', 'kl_kicktone', freq=60.0, amp=0.5)
        snare = _inst('snare', 'kl_noisebpf', freq=200.0, amp=0.3)
        kit = SynthDefKit({'kick': kick, 'snare': snare})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='kick')
        uc.set_pfields(leaves[1], voice='snare')
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0]['pfields']['freq'] == 60.0
        assert new_events[1]['pfields']['freq'] == 200.0
        assert new_events[0]['pfields']['amp'] == 0.5
        assert new_events[1]['pfields']['amp'] == 0.3


class TestEnsembleAssemblyFormat:
    def test_ensemble_autoroute_produces_valid_group(self):
        ens = Ensemble()
        ens.add('lead', _inst('lead'), family='melody')
        ens.add('bass', _inst('bass', 'kl_saw'), family='low')
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_instrument(leaves[0], ens.melody['lead'])
        uc.set_instrument(leaves[1], ens.low['bass'])
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        new_events = [e for e in events if e['type'] == 'new']
        assert new_events[0].get('group') == 'melody'
        assert new_events[1].get('group') == 'low'

    def test_score_from_ensemble_events_valid(self):
        ens = Ensemble('Band')
        ens.add('lead', _inst('lead'), family='melody')
        ens.set_inserts('melody', [SynthDefFX('kl_reverb', mix=0.3)])
        s = Score()
        s.from_ensemble(ens)
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, ens.melody['lead'])
        s.add(uc)
        assert s.total_events > 0


class TestInsertFXAssemblyFormat:
    def test_insert_automation_produces_set_events(self):
        verb = SynthDefFX('kl_reverb', mix=0.3)
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, verb)
        uc.set_pfields(list(uc.rt.leaf_nodes), mix=Pattern([0.2, 0.8]))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        set_events = [e for e in events if e['type'] == 'set']
        assert len(set_events) == 2
        for e in set_events:
            assert e['id'] == verb.uid
            assert 'pfields' in e


class TestSlurAssemblyFormat:
    def test_slur_shares_node_id(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120, inst=_inst('tri'))
        leaves = list(uc.rt.leaf_nodes)
        uc.apply_slur(node=leaves[:2])
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        new_events = [e for e in events if e['type'] == 'new']
        set_events = [e for e in events if e['type'] == 'set']
        assert len(new_events) == 3
        slur_id = new_events[0]['id']
        slur_sets = [e for e in set_events if e['id'] == slur_id]
        assert len(slur_sets) == 1


class TestMixedReleaseModeAssemblyFormat:
    def test_free_release_no_release_event(self):
        free_inst = SynthDefInstrument(
            name='free_synth', defName='kl_sine', release_mode='free',
            pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'out': 0, 'sustainTime': 1.0}
        )
        kit = SynthDefKit({'gated': _inst('gated'), 'free': free_inst})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='gated')
        uc.set_pfields(leaves[1], voice='free')
        events = lower_compositional_ir_to_sc_assembly(
            uc, sort_output=True, include_ungated_release=False
        )
        _validate_assembly(events)
        new_events = [e for e in events if e['type'] == 'new']
        release_events = [e for e in events if e['type'] == 'release']
        gated_id = new_events[0]['id']
        free_id = new_events[1]['id']
        assert any(r['id'] == gated_id for r in release_events)
        assert not any(r['id'] == free_id for r in release_events)
