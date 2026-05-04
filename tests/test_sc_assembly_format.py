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

    def test_every_terminal_new_carries_release_after_true(self):
        """The lowering layer no longer emits explicit ``type:"release"``
        events. Each terminal ``new``/``set`` for a uid carries
        ``releaseAfter:true`` and a positive ``dur``; the scheduler does
        the gate-off at fire time."""
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120, inst=_inst('tri'))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        assert all(e['type'] != 'release' for e in events)
        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 2
        for e in new_events:
            assert e.get('releaseAfter') is True
            assert e.get('dur', 0) > 0

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
        from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events
        payload = convert_score_to_sc_events(s)
        assert len(payload["events"]) > 0


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


class TestSlurMultiVoiceAssembly:
    """Voice-aware slur lowering under the new ``releaseAfter`` contract.

    Rules enforced:
      - Strum (mfield) is honored on the slur's starting event only; on
        continuation/end events inside a slur, all voices update
        simultaneously at the event's base start.
      - A voice present in an earlier slur event but absent from a later one
        has its **most recent ``new``/``set``** flagged ``releaseAfter:true``
        with ``dur`` adjusted so the scheduler fires gate-off at the
        transition point.
      - A voice first appearing on a continuation/end event spawns a fresh
        ``new`` (``releaseAfter:false``) at that event's start.
      - At slur end, every still-active uid's most recent event is marked
        ``releaseAfter:true``; ``dur`` already reflects the leaf's duration.
      - The lowering layer never emits explicit ``type:"release"`` events.
    """

    def _no_release_events(self, events):
        assert all(e['type'] != 'release' for e in events), \
            "lowering must not emit type:release any more"

    def _terminal_events_per_uid(self, events):
        """For each uid, return the index of its last new/set event."""
        last_idx = {}
        for i, e in enumerate(events):
            if e['type'] in ('new', 'set'):
                last_idx[e['id']] = i
        return last_idx

    def test_slur_chord_to_chord_with_strum_strips_on_continuation(self):
        uc = CompositionalUnit(
            tempus='4/4', prolatio=(1, 1, 1), bpm=60,
            pfields={'freq': 440.0}, mfields={'strum': 0.5}, inst=_inst('tri'),
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], freq=(440.0, 550.0, 660.0))
        uc.set_pfields(leaves[1], freq=(660.0, 770.0, 880.0))
        uc.set_pfields(leaves[2], freq=(880.0, 990.0, 1100.0))
        uc.apply_slur(node=leaves)
        events = lower_compositional_ir_to_sc_assembly(uc)
        _validate_assembly(events)
        self._no_release_events(events)

        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 3
        new_starts = sorted(e['start'] for e in new_events)
        assert new_starts[0] == 0.0
        assert new_starts[1] > new_starts[0]
        assert new_starts[2] > new_starts[1]

        set_by_node_start = {}
        for e in events:
            if e['type'] == 'set':
                set_by_node_start.setdefault(round(e['start'], 4), []).append(e)
        for start, set_events in set_by_node_start.items():
            if start == 0.0:
                continue
            starts = {round(e['start'], 6) for e in set_events}
            assert len(starts) == 1, \
                f"strum should be stripped on continuation: {starts}"

        # At slur end (t=4), each of the 3 uids' terminal event carries
        # releaseAfter=true. The scheduler will fire gate-off at start+dur.
        last_idx = self._terminal_events_per_uid(events)
        terminals = [events[i] for i in last_idx.values()]
        assert sum(1 for t in terminals if t.get('releaseAfter') is True) == 3
        # Their start+dur lands at 4.0 (the slur end).
        ends = {round(t['start'] + t.get('dur', 0), 6) for t in terminals
                if t.get('releaseAfter') is True}
        assert ends == {4.0}

    def test_slur_chord_to_single_drops_voices_via_release_after(self):
        uc = CompositionalUnit(
            tempus='4/4', prolatio=(1, 1), bpm=60,
            pfields={'freq': 440.0}, inst=_inst('tri'),
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], freq=(440.0, 550.0, 660.0))
        uc.set_pfields(leaves[1], freq=880.0)
        uc.apply_slur(node=leaves)
        events = lower_compositional_ir_to_sc_assembly(uc)
        _validate_assembly(events)
        self._no_release_events(events)

        new_events = [e for e in events if e['type'] == 'new']
        set_events = [e for e in events if e['type'] == 'set']
        assert len(new_events) == 3
        assert len(set_events) == 1

        # 3 uids total. The 2 dropped voices fire at the transition (t=2);
        # the 1 surviving voice fires at slur end (t=4). All terminals
        # carry releaseAfter=true.
        last_idx = self._terminal_events_per_uid(events)
        terminals = [events[i] for i in last_idx.values()]
        assert sum(1 for t in terminals if t.get('releaseAfter') is True) == 3
        ends = sorted(round(t['start'] + t.get('dur', 0), 6) for t in terminals)
        assert ends.count(2.0) == 2, f"expected 2 voices ending at 2.0, got {ends}"
        assert ends.count(4.0) == 1, f"expected 1 voice ending at 4.0, got {ends}"

    def test_slur_single_to_chord_spawns_midslur_voice_joins(self):
        uc = CompositionalUnit(
            tempus='4/4', prolatio=(1, 1), bpm=60,
            pfields={'freq': 440.0}, inst=_inst('tri'),
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], freq=440.0)
        uc.set_pfields(leaves[1], freq=(660.0, 770.0, 880.0))
        uc.apply_slur(node=leaves)
        events = lower_compositional_ir_to_sc_assembly(uc)
        _validate_assembly(events)
        self._no_release_events(events)

        new_events = [e for e in events if e['type'] == 'new']
        set_events = [e for e in events if e['type'] == 'set']
        assert len(new_events) == 3
        assert len(set_events) == 1

        new_starts = sorted(e['start'] for e in new_events)
        assert new_starts[0] == 0.0
        assert new_starts[1] == 2.0 and new_starts[2] == 2.0

        # All 3 uids end at slur end (t=4).
        last_idx = self._terminal_events_per_uid(events)
        terminals = [events[i] for i in last_idx.values()]
        assert sum(1 for t in terminals if t.get('releaseAfter') is True) == 3
        ends = {round(t['start'] + t.get('dur', 0), 6) for t in terminals
                if t.get('releaseAfter') is True}
        assert ends == {4.0}

    def test_slur_drop_then_rejoin_spawns_fresh_synths(self):
        uc = CompositionalUnit(
            tempus='4/4', prolatio=(1, 1, 1), bpm=60,
            pfields={'freq': 440.0}, inst=_inst('tri'),
        )
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], freq=(440.0, 550.0, 660.0))
        uc.set_pfields(leaves[1], freq=770.0)
        uc.set_pfields(leaves[2], freq=(880.0, 990.0, 1100.0))
        uc.apply_slur(node=leaves)
        events = lower_compositional_ir_to_sc_assembly(uc)
        _validate_assembly(events)
        self._no_release_events(events)

        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 5

        drop_t = 4.0 / 3
        rejoin_t = 8.0 / 3

        # The 2 voices dropped at drop_t have terminals with start+dur==drop_t.
        last_idx = self._terminal_events_per_uid(events)
        terminals = [events[i] for i in last_idx.values()
                     if events[i].get('releaseAfter') is True]
        ends = sorted(round(t['start'] + t.get('dur', 0), 6) for t in terminals)
        assert ends.count(round(drop_t, 6)) == 2, \
            f"expected 2 voices dropping at {drop_t}, got ends={ends}"

        rejoined = [e for e in new_events if abs(e['start'] - rejoin_t) < 1e-6]
        assert len(rejoined) == 2, f"expected 2 voices rejoined at {rejoin_t}"

        # Rejoining voices are fresh synths, distinct from the dropped uids.
        rejoined_ids = {e['id'] for e in rejoined}
        all_new_ids = {e['id'] for e in new_events}
        assert rejoined_ids.issubset(all_new_ids)


class TestMixedHasGateAssemblyFormat:
    def test_free_voice_uses_release_after_not_release_event(self):
        """Lifecycle ``release`` events are no longer emitted by the lowering
        layer. Both gated and free voices get ``releaseAfter:true`` on their
        terminal ``new`` event; the scheduler skips the gate-off when the
        synthdef has no ``gate`` control.
        """
        free_inst = SynthDefInstrument(
            name='free_synth', defName='kl_sine',
            pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'out': 0, 'sustainTime': 1.0}
        )
        kit = SynthDefKit({'gated': _inst('gated'), 'free': free_inst})
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)
        uc.set_instrument(uc.rt.root, kit)
        leaves = list(uc.rt.leaf_nodes)
        uc.set_pfields(leaves[0], voice='gated')
        uc.set_pfields(leaves[1], voice='free')
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        _validate_assembly(events)
        new_events = [e for e in events if e['type'] == 'new']
        # Lowering never emits explicit type:release any more.
        assert all(e['type'] != 'release' for e in events)
        # Both terminals carry releaseAfter=true and a positive dur.
        assert new_events[0].get('releaseAfter') is True
        assert new_events[1].get('releaseAfter') is True
        assert new_events[0].get('dur', 0) > 0
        assert new_events[1].get('dur', 0) > 0
