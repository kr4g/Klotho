import random

import pytest

from klotho.thetos import CompositionalUnit as UC, Bind
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.tonos import Chord, Pitch
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


def _inst(name='tri', defName='kl_tri', **pf):
    d = {'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0}
    d.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=d)


class TestBindBasics:
    def test_bind_requires_callable(self):
        with pytest.raises(TypeError):
            Bind(42)

    def test_bind_stored_raw_not_evaluated_at_set(self):
        calls = []
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: calls.append(c.id) or 440.0))
        assert calls == []
        raw = uc._rt.get_pfield(uc._rt.root, 'freq')
        assert isinstance(raw, Bind)

    def test_resolves_per_reading_node(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: float(c.id * 100)))
        leaves = list(uc._rt.leaf_nodes)
        values = [uc.get_pfield(n, 'freq') for n in leaves]
        assert values == [float(n * 100) for n in leaves]

    def test_zero_arity_callable(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: 123.0))
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == 123.0

    def test_index_total_relative_to_origin_leaves(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: (c.index, c.total)))
        leaves = list(uc._rt.leaf_nodes)
        values = [uc.get_pfield(n, 'freq') for n in leaves]
        assert values == [(0, 4), (1, 4), (2, 4), (3, 4)]

    def test_bind_reads_mfields(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        for node, chord in zip(uc._rt.leaf_nodes, [(100.0,), (200.0,)]):
            uc.set_mfields(node, chord=chord)
        uc.root.set_pfields(freq=Bind(lambda c: c.mfields['chord']))
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == (100.0,)
        assert uc.get_pfield(uc._rt.leaf_nodes[1], 'freq') == (200.0,)

    def test_bind_on_mfields(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_mfields(strum=Bind(lambda c: 0.1 * (c.index + 1)))
        values = [uc.get_mfield(n, 'strum') for n in uc._rt.leaf_nodes]
        assert values == [pytest.approx(0.1), pytest.approx(0.2)]

    def test_bind_via_unified_set(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.set(uc._rt.root, freq=Bind(lambda: 111.0), strum=Bind(lambda: 0.5))
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == 111.0
        assert uc.get_mfield(uc._rt.leaf_nodes[0], 'strum') == 0.5
        assert 'strum' in uc._rt.mfield_names


class TestBindMemoStability:
    def test_repeated_reads_stable_for_stochastic_fn(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: random.random()))
        leaves = list(uc._rt.leaf_nodes)
        first = [uc.get_pfield(n, 'freq') for n in leaves]
        second = [uc.get_pfield(n, 'freq') for n in leaves]
        assert first == second
        assert len(set(first)) == 3

    def test_subdivide_keeps_existing_fresh_new(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: random.random()))
        leaves = list(uc._rt.leaf_nodes)
        before = [uc.get_pfield(n, 'freq') for n in leaves]

        uc.subdivide(leaves[0], (1, 1, 1))
        new_leaves = list(uc._rt.successors(leaves[0]))

        after = [uc.get_pfield(n, 'freq') for n in leaves[1:]]
        assert after == before[1:]
        fresh = [uc.get_pfield(n, 'freq') for n in new_leaves]
        assert len(set(fresh)) == 3
        assert not set(fresh) & set(before)

    def test_plain_callable_subdivide_still_freezes(self):
        uc = UC(tempus='4/4', prolatio=(4, 2, 1, 1), beat='1/4', bpm=120, pfields=['freq'])
        uc.set_pfields(uc._rt.leaf_nodes[0], freq=lambda: random.random())
        leaf = uc._rt.leaf_nodes[0]
        frozen = uc.get_pfield(leaf, 'freq')
        uc.subdivide(leaf, (1, 1, 1))
        for node in uc._rt.successors(leaf):
            assert uc.get_pfield(node, 'freq') == frozen

    def test_reassign_same_field_invalidates(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        node = uc._rt.leaf_nodes[0]
        uc.root.set_pfields(freq=Bind(lambda: 111.0))
        assert uc.get_pfield(node, 'freq') == 111.0
        uc.root.set_pfields(freq=Bind(lambda: 222.0))
        assert uc.get_pfield(node, 'freq') == 222.0
        uc.set_pfields(node, freq=333.0)
        assert uc.get_pfield(node, 'freq') == 333.0

    def test_ancestor_reassign_invalidates_descendants(self):
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), 1), beat='1/4', bpm=120)
        branch = list(uc._rt.successors(uc._rt.root))[0]
        leaf = list(uc._rt.successors(branch))[0]
        uc.set_pfields(branch, freq=Bind(lambda: 1.0))
        assert uc.get_pfield(leaf, 'freq') == 1.0
        uc.root.set_pfields(freq=Bind(lambda: 2.0))
        # the branch's own Bind still governs (nearer override)
        assert uc.get_pfield(leaf, 'freq') == 1.0
        uc.set_pfields(branch, freq=Bind(lambda: 3.0))
        assert uc.get_pfield(leaf, 'freq') == 3.0

    def test_clear_parameters_invalidates(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        node = uc._rt.leaf_nodes[0]
        uc.root.set_pfields(freq=Bind(lambda: random.random()))
        _ = uc.get_pfield(node, 'freq')
        uc.clear_parameters()
        assert uc._bind_memo == {}

    def test_removed_nodes_dropped_from_memo(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: random.random()))
        leaves = list(uc._rt.leaf_nodes)
        _ = [uc.get_pfield(n, 'freq') for n in leaves]
        uc.remove_subtree(leaves[-1])
        assert all(node != leaves[-1] for node, _key in uc._bind_memo)

    def test_copy_carries_bind_with_fresh_memo(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: random.random()))
        _ = [uc.get_pfield(n, 'freq') for n in uc._rt.leaf_nodes]
        clone = uc.copy()
        assert clone._bind_memo == {}
        values = [clone.get_pfield(n, 'freq') for n in clone._rt.leaf_nodes]
        assert all(isinstance(v, float) for v in values)


class TestBindNeverLeaks:
    def test_events_dataframe_resolved(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: float(c.id)), amp=0.3)
        df = uc.events
        assert not any(isinstance(v, Bind) for v in df['freq'])
        assert all(isinstance(v, float) for v in df['freq'])

    def test_pt_snapshot_resolved(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: float(c.id)))
        snapshot = uc.pt
        for node in snapshot.nodes:
            assert not isinstance(snapshot.get_pfield(node, 'freq'), Bind)
            assert not isinstance(snapshot.items(node).get('freq'), Bind)

    def test_sc_assembly_resolved(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120, inst=_inst())
        uc.root.set_pfields(freq=Bind(lambda c: 100.0 + c.index * 50.0))
        events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
        new_events = [e for e in events if e['type'] == 'new']
        assert len(new_events) == 4
        freqs = sorted(e['pfields']['freq'] for e in new_events)
        assert freqs == [100.0, 150.0, 200.0, 250.0]
        for e in new_events:
            for value in e['pfields'].values():
                assert isinstance(value, (int, float))

    def test_parametron_reads_resolved(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: 440.0))
        event = uc[0]
        assert event.get_pfield('freq') == 440.0
        assert event['freq'] == 440.0
        assert not isinstance(event.pfields['freq'], Bind)

    def test_node_handle_reads_resolved(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: 440.0))
        handle = uc.leaves[0]
        assert handle.get_pfield('freq') == 440.0
        assert handle.pfields['freq'] == 440.0


class TestBindCoercion:
    def test_chord_result_lowered_to_pitch_tuple(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: Chord(['1/1', '5/4', '3/2'],
                                                    reference_pitch='A3')))
        value = uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')
        assert isinstance(value, tuple)
        assert all(isinstance(p, Pitch) for p in value)

    def test_pitch_name_string_result_parsed(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda: 'A4'))
        value = uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')
        assert isinstance(value, Pitch)
        assert value.freq == pytest.approx(440.0)


class TestBindCycles:
    def test_self_reference_detected(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: c.pfields['freq']))
        with pytest.raises(ValueError, match='cycle'):
            uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')

    def test_cross_field_cycle_detected(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(freq=Bind(lambda c: c.pfields['amp']),
                            amp=Bind(lambda c: c.pfields['freq']))
        with pytest.raises(ValueError, match='cycle'):
            uc.get_pfield(uc._rt.leaf_nodes[0], 'freq')

    def test_acyclic_cross_field_read_allowed(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(amp=0.25,
                            freq=Bind(lambda c: c.pfields['amp'] * 1000))
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == 250.0

    def test_bind_reading_other_bind_field(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        uc.root.set_pfields(amp=Bind(lambda: 0.5),
                            freq=Bind(lambda c: c.pfields['amp'] * 200))
        assert uc.get_pfield(uc._rt.leaf_nodes[0], 'freq') == 100.0
