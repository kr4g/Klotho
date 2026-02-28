"""
Exhaustive tests for core Klotho data structures: RhythmTree, TemporalUnit,
TemporalUnitSequence, TemporalBlock, CompositionalUnit, Pattern, PartitionSet.

These tests capture the CURRENT correct behavior of Klotho v4.0.0 so that
API refactoring (e.g., __getattr__ delegation, smart set_pfields dispatch,
sparsify, repeat, etc.) can be validated against known-good baselines.

Abbreviation note (from French musical terminology):
    RT  = RhythmTree
    UT  = TemporalUnit
    UTS = TemporalUnitSequence
    BT  = TemporalBlock
    UC  = CompositionalUnit
    PT  = ParameterTree
"""

import pytest
import numpy as np
import warnings
from fractions import Fraction


from klotho import RhythmTree as RT
from klotho.chronos import (
    TemporalUnit as UT,
    TemporalUnitSequence as UTS,
    TemporalBlock as BT,
)
from klotho.thetos import (
    CompositionalUnit as UC,
    JsInstrument as JsInst,
    ParameterTree,
)
from klotho.dynatos import Envelope
from klotho.topos import Pattern, PartitionSet as PS


class TestRhythmTreeBasic:

    def test_equal_divisions(self):
        rt = RT(subdivisions=(1, 1, 1, 1))
        assert rt.durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        assert rt.onsets == (0, Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
        assert rt.leaf_nodes == (1, 2, 3, 4)
        assert rt.depth == 1
        assert rt.k == 4
        assert rt.root == 0
        assert rt.span == 1
        assert str(rt.meas) == '1/1'
        assert rt.subdivisions == (1, 1, 1, 1)

    def test_equal_divisions_sum_to_one(self):
        rt = RT(subdivisions=(1, 1, 1, 1))
        assert sum(rt.durations) == 1

    def test_equal_divisions_node_data(self):
        rt = RT(subdivisions=(1, 1, 1, 1))
        for i, node in enumerate(rt.leaf_nodes):
            assert rt[node]['proportion'] == 1
            assert rt[node]['metric_duration'] == Fraction(1, 4)
            assert rt[node]['metric_onset'] == Fraction(i, 4)

    def test_weighted_divisions(self):
        rt = RT(subdivisions=(4, 2, 1, 1))
        assert rt.durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8))
        assert rt.onsets == (0, Fraction(1, 2), Fraction(3, 4), Fraction(7, 8))
        assert sum(rt.durations) == 1

    def test_weighted_node_data(self):
        rt = RT(subdivisions=(4, 2, 1, 1))
        expected = [
            (4, Fraction(1, 2), 0),
            (2, Fraction(1, 4), Fraction(1, 2)),
            (1, Fraction(1, 8), Fraction(3, 4)),
            (1, Fraction(1, 8), Fraction(7, 8)),
        ]
        for node, (prop, md, mo) in zip(rt.leaf_nodes, expected):
            assert rt[node]['proportion'] == prop
            assert rt[node]['metric_duration'] == md
            assert rt[node]['metric_onset'] == mo

    def test_various_equal_divisions_sum(self):
        for n in [3, 5, 7, 11, 13, 17]:
            rt = RT(subdivisions=(1,) * n)
            assert sum(rt.durations) == 1
            assert len(rt.durations) == n


class TestRhythmTreeNested:

    def test_nested_subdivisions(self):
        rt = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        assert rt.durations == (
            Fraction(1, 6), Fraction(1, 6), Fraction(1, 6),
            Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
        )
        assert rt.onsets == (
            0, Fraction(1, 6), Fraction(1, 3),
            Fraction(1, 2), Fraction(3, 4), Fraction(7, 8),
        )
        assert rt.depth == 2
        assert rt.leaf_nodes == (2, 3, 4, 5, 6, 7)

    def test_nested_inner_node_data(self):
        rt = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        assert rt[0]['metric_duration'] == Fraction(1, 1)
        assert rt[0]['proportion'] == 1
        assert rt[1]['metric_duration'] == Fraction(1, 2)
        assert rt[1]['proportion'] == 4

    def test_nested_all_nodes(self):
        rt = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        all_nodes = list(rt.nodes)
        assert len(all_nodes) == 8
        assert all_nodes == [0, 1, 2, 3, 4, 5, 6, 7]

    def test_deep_nesting(self):
        rt = RT(subdivisions=((4, (1, 1, (1, (1, 1)))), 2, 1, 1))
        assert rt.durations == (
            Fraction(1, 6), Fraction(1, 6),
            Fraction(1, 12), Fraction(1, 12),
            Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
        )
        assert rt.depth == 3
        assert rt.leaf_nodes == (2, 3, 5, 6, 7, 8, 9)

    def test_deep_nesting_sum(self):
        rt = RT(subdivisions=((4, (1, 1, (1, (1, 1)))), 2, 1, 1))
        assert sum(abs(d) for d in rt.durations) == 1


class TestRhythmTreeRests:

    def test_rests_in_subdivisions(self):
        rt = RT(subdivisions=(1, (1, (1, 1)), (1, (1, 1, -1, 1)), (1, (1, 3))))
        assert rt.durations == (
            Fraction(1, 4), Fraction(1, 8), Fraction(1, 8),
            Fraction(1, 16), Fraction(1, 16), Fraction(-1, 16), Fraction(1, 16),
            Fraction(1, 16), Fraction(3, 16),
        )

    def test_rest_node_data(self):
        rt = RT(subdivisions=(1, (1, (1, 1)), (1, (1, 1, -1, 1)), (1, (1, 3))))
        rest_nodes = [n for n in rt.leaf_nodes if rt[n]['proportion'] < 0]
        assert len(rest_nodes) == 1
        assert rt[rest_nodes[0]]['metric_duration'] == Fraction(-1, 16)

    def test_nested_rests(self):
        rt = RT(subdivisions=(1, (1, (1, (1, (-1, 1)))), (1, (1, 1, -1, 1)), (1, (-1, 2, 1))))
        rest_nodes = [n for n in rt.leaf_nodes if rt[n]['proportion'] < 0]
        assert len(rest_nodes) == 3

    def test_nested_rests_data(self):
        rt = RT(subdivisions=(1, (1, (1, (1, (-1, 1)))), (1, (1, 1, -1, 1)), (1, (-1, 2, 1))))
        expected_rests = {5, 10, 13}
        actual_rests = {n for n in rt.leaf_nodes if rt[n]['proportion'] < 0}
        assert actual_rests == expected_rests


class TestRhythmTreeMakeRest:

    def test_make_rest(self):
        rt = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        before = rt.durations
        assert before == (Fraction(1, 6), Fraction(1, 6), Fraction(1, 6), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8))
        rt.make_rest(5)
        after = rt.durations
        assert after == (Fraction(1, 6), Fraction(1, 6), Fraction(1, 6), Fraction(-1, 4), Fraction(1, 8), Fraction(1, 8))
        assert rt[5]['proportion'] == -2


class TestRhythmTreeTraversal:

    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))

    def test_successors_root(self, rt):
        assert list(rt.successors(0)) == [1, 5, 6, 7]

    def test_successors_inner(self, rt):
        assert list(rt.successors(1)) == [2, 3, 4]

    def test_at_depth(self, rt):
        assert rt.at_depth(0) == [0]
        assert rt.at_depth(1) == [1, 5, 6, 7]
        assert rt.at_depth(2) == [2, 3, 4]

    def test_parent(self, rt):
        assert rt.parent(2) == 1
        assert rt.parent(5) == 0

    def test_ancestors(self, rt):
        assert rt.ancestors(4) == (0, 1)

    def test_descendants_root(self, rt):
        assert list(rt.descendants(0)) == [1, 2, 3, 4, 5, 6, 7]

    def test_descendants_inner(self, rt):
        assert list(rt.descendants(1)) == [2, 3, 4]

    def test_subtree_leaves_root(self, rt):
        assert rt.subtree_leaves(0) == (2, 3, 4, 5, 6, 7)

    def test_subtree_leaves_inner(self, rt):
        assert rt.subtree_leaves(1) == (2, 3, 4)

    def test_out_degree(self, rt):
        assert rt.out_degree(0) == 4
        assert rt.out_degree(1) == 3
        assert rt.out_degree(2) == 0

    def test_all_nodes_descendants_successors_subtree_leaves(self, rt):
        for node in rt.nodes:
            _ = list(rt.descendants(node))
            _ = list(rt.successors(node))
            _ = rt.subtree_leaves(node)
            if node != rt.root:
                _ = rt.ancestors(node)

    def test_all_nodes_appear_in_exactly_one_depth(self, rt):
        seen = set()
        for d in range(rt.depth + 1):
            for n in rt.at_depth(d):
                assert n not in seen, f"Node {n} appears in multiple depths"
                seen.add(n)
        assert seen == set(rt.nodes), "at_depth does not cover all nodes"


def _rt_node_data_tuple(rt, node):
    d = rt[node]
    return (d.get('proportion'), Fraction(d['metric_duration']), Fraction(d['metric_onset']))


def _assert_rt_structurally_equivalent(a, b):
    """Assert two RTs have identical structure and node values. Compares all nodes
    and traversals (descendants, successors, subtree_leaves, at_depth) via DFS."""
    assert len(list(a.nodes)) == len(list(b.nodes)), "Node count mismatch"
    assert a.depth == b.depth, "Depth mismatch"
    for d in range(a.depth + 1):
        a_vals = {_rt_node_data_tuple(a, n) for n in a.at_depth(d)}
        b_vals = {_rt_node_data_tuple(b, n) for n in b.at_depth(d)}
        assert a_vals == b_vals, f"at_depth({d}) mismatch"
    def _dfs(ta, tb, na, nb):
        assert _rt_node_data_tuple(ta, na) == _rt_node_data_tuple(tb, nb), (
            f"Node data mismatch at {na} vs {nb}"
        )
        sa = list(ta.successors(na))
        sb = list(tb.successors(nb))
        assert len(sa) == len(sb), f"Successor count mismatch at {na} vs {nb}"
        for ca, cb in zip(sa, sb):
            _dfs(ta, tb, ca, cb)
        da = {_rt_node_data_tuple(ta, n) for n in ta.descendants(na)}
        db = {_rt_node_data_tuple(tb, n) for n in tb.descendants(nb)}
        assert da == db, f"Descendants mismatch at {na} vs {nb}"
        la = {_rt_node_data_tuple(ta, n) for n in ta.subtree_leaves(na)}
        lb = {_rt_node_data_tuple(tb, n) for n in tb.subtree_leaves(nb)}
        assert la == lb, f"Subtree leaves mismatch at {na} vs {nb}"
    _dfs(a, b, a.root, b.root)


class TestRhythmTreePruneAndRemoveSubtree:
    def test_prune_matches_built_structure(self):
        rt = RT(subdivisions=((2, (1, 1)), (2, (1, 1))))
        inner = rt.at_depth(1)[0]
        rt.prune(inner)
        expected = RT(subdivisions=(1, 1, (2, (1, 1))))
        assert rt.durations == expected.durations
        assert rt.onsets == expected.onsets
        assert len(rt.leaf_nodes) == len(expected.leaf_nodes)

    def test_prune_all_nodes_and_traversals(self):
        rt = RT(subdivisions=((2, (1, 1)), (2, (1, 1))))
        inner = rt.at_depth(1)[0]
        rt.prune(inner)
        expected = RT(subdivisions=(1, 1, (2, (1, 1))))
        _assert_rt_structurally_equivalent(rt, expected)

    def test_remove_subtree_matches_built_structure(self):
        rt = RT(subdivisions=((2, (1, 1)), (2, (1, 1))))
        inner = rt.at_depth(1)[0]
        rt.remove_subtree(inner)
        expected = RT(subdivisions=((2, (1, 1)),))
        assert rt.durations == expected.durations
        assert rt.onsets == expected.onsets
        assert len(rt.leaf_nodes) == len(expected.leaf_nodes)

    def test_remove_subtree_all_nodes_and_traversals(self):
        rt = RT(subdivisions=((2, (1, 1)), (2, (1, 1))))
        inner = rt.at_depth(1)[0]
        rt.remove_subtree(inner)
        expected = RT(subdivisions=((2, (1, 1)),))
        _assert_rt_structurally_equivalent(rt, expected)


class TestRhythmTreeSpanAndMeas:

    def test_span_2(self):
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2), Fraction(1, 2), Fraction(1, 2))
        assert rt.onsets == (0, Fraction(1, 2), Fraction(1, 1), Fraction(3, 2))

    def test_meas_3_8(self):
        rt = RT(meas='3/8', subdivisions=(2, 3, 1))
        assert str(rt.meas) == '3/8'
        assert rt.durations == (Fraction(1, 8), Fraction(3, 16), Fraction(1, 16))
        assert rt.onsets == (0, Fraction(1, 8), Fraction(5, 16))


class TestTemporalUnit:

    def test_basic_4_4(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        assert ut.duration == 2.0
        assert ut.metric_durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4))
        assert ut.metric_onsets == (0, Fraction(1, 4), Fraction(1, 2), Fraction(3, 4))
        assert ut.time == (0, 2.0)
        assert len(ut) == 4

    def test_events(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        events = list(ut)
        assert len(events) == 4
        assert events[0].start == 0.0
        assert events[0].duration == 0.5
        assert events[0].is_rest is False
        assert events[0].node_id == 1
        assert events[3].start == 1.5
        assert events[3].duration == 0.5

    def test_nested_subdivisions(self):
        ut = UT(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=60)
        assert ut.duration == 4.0
        assert len(ut) == 6
        events = list(ut)
        assert abs(events[0].start - 0.0) < 1e-9
        assert abs(events[0].duration - 2/3) < 1e-9
        assert abs(events[3].start - 2.0) < 1e-9
        assert abs(events[3].duration - 1.0) < 1e-9

    def test_make_rest(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        before = [(round(e.start, 6), e.is_rest) for e in ut]
        assert before == [(0.0, False), (0.5, False), (1.0, False), (1.5, False)]
        ut.make_rest(2)
        after = [(round(e.start, 6), e.is_rest) for e in ut]
        assert after == [(0.0, False), (0.5, True), (1.0, False), (1.5, False)]

    def test_10_16_complex(self):
        ut = UT(tempus='10/16', prolatio=((3, (1,)*4), (4, (1,)*6), (3, (1,)*4)), beat='1/16', bpm=140)
        assert abs(ut.duration - 4.285714285714286) < 1e-9
        assert len(ut) == 14


class TestTemporalUnitSequence:

    def test_basic_sequence(self):
        ut_a = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        ut_b = UT(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uts = UTS()
        uts.extend([ut_a, ut_b, ut_a])
        assert uts.size == 11
        assert uts.duration == 5.5
        assert uts.durations == (2.0, 1.5, 2.0)
        assert len(uts.seq) == 3

    def test_unit_offsets(self):
        ut_a = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        ut_b = UT(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uts = UTS()
        uts.extend([ut_a, ut_b, ut_a])
        assert uts[0].offset == 0
        assert uts[1].offset == 2.0
        assert uts[2].offset == 3.5

    def test_copies_are_independent(self):
        uc = UC(tempus='10/16', prolatio=((3, (1,)*4), (4, (1,)*6), (3, (1,)*4)), beat='1/16', bpm=140)
        uts = UTS()
        uts.extend([uc] * 2)
        leaf0 = uts[0].rt.leaf_nodes[0]
        uts[0].set_pfields(leaf0, freq=100)
        assert uts[0].get_parameter(leaf0, 'freq') == 100
        assert uts[1].get_parameter(uts[1].rt.leaf_nodes[0], 'freq') is None


class TestTemporalBlock:

    def test_basic_block(self):
        ut_a = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        ut_b = UT(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
        uts1 = UTS()
        uts1.extend([ut_a, ut_b, ut_a])
        uts2 = UTS([ut_a, ut_b])
        bt = BT([uts1, uts2])
        assert bt.duration == 5.5
        rows = list(bt)
        assert len(rows) == 2
        assert rows[0].duration == 5.5
        assert rows[1].duration == 3.5


class TestCompositionalUnit:

    def test_basic(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        assert uc.duration == 2.0
        assert len(uc) == 4
        assert uc.pfields == []
        assert 'group' in uc.mfields

    def test_basic_events(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        events = list(uc)
        for e in events:
            assert e.mfields == {'group': 'default'}

    def test_with_instrument(self):
        uc = UC(tempus='4/4', prolatio=((3, (1,)*3), (2, (1,)*2)), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        assert len(uc) == 5
        assert 'freq' in uc.pfields
        assert 'vel' in uc.pfields
        events = list(uc)
        for e in events:
            assert e.pfields.get('freq') == 440.0
            assert e.pfields.get('vel') == 0.6

    def test_set_pfields_root(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        uc.set_pfields(0, freq=440)
        for e in uc:
            assert e.pfields.get('freq') == 440

    def test_set_pfields_per_leaf(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        freqs = [262, 330, 392, 523]
        for i, leaf in enumerate(uc.rt.leaf_nodes):
            uc.set_pfields(leaf, freq=freqs[i])
        for e, expected_freq in zip(uc, freqs):
            assert e.pfields.get('freq') == expected_freq

    def test_set_instrument_per_leaf_with_pattern(self):
        np.random.seed(42)
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        inst_pat = Pattern([JsInst.Kick(), JsInst.Snare(), JsInst.HatClosed()])
        for leaf in uc.rt.leaf_nodes:
            uc.set_instrument(leaf, next(inst_pat))
            uc.set_pfields(leaf, vel=np.random.uniform(0.5, 0.9))
        events = list(uc)
        expected_synths = ['Kick', 'Snare', 'HatClosed', 'Kick']
        expected_vels = [0.6498, 0.8803, 0.7928, 0.7395]
        for e, synth, vel in zip(events, expected_synths, expected_vels):
            assert (e.pfields.get('synth_name') or e.pfields.get('synthName')) == synth
            assert abs(e.pfields.get('vel') - vel) < 0.001

    def test_set_mfields_inheritance(self):
        uc = UC(tempus='4/4', prolatio=((3, (1,)*3), (2, (1,)*2)), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        limbs = uc.rt.at_depth(1)
        uc.set_mfields(limbs[0], idx=0, drct=1)
        uc.set_mfields(limbs[1], idx=5, drct=-1)
        limb0_leaves = list(uc.rt.subtree_leaves(limbs[0]))
        limb1_leaves = list(uc.rt.subtree_leaves(limbs[1]))
        for leaf in limb0_leaves:
            assert uc.get_parameter(leaf, 'idx') == 0
            assert uc.get_parameter(leaf, 'drct') == 1
        for leaf in limb1_leaves:
            assert uc.get_parameter(leaf, 'idx') == 5
            assert uc.get_parameter(leaf, 'drct') == -1

    def test_make_rest(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        before = [(e.node_id, e.is_rest) for e in uc]
        assert before == [(1, False), (2, False), (3, False), (4, False)]
        uc.make_rest(2)
        after = [(e.node_id, e.is_rest) for e in uc]
        assert after == [(1, False), (2, True), (3, False), (4, False)]

    def test_copy_preserves_state(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.set_pfields(1, freq=100)
        uc.make_rest(3)
        uc_copy = uc.copy()
        orig_data = [(e.node_id, e.is_rest, e.pfields.get('freq')) for e in uc]
        copy_data = [(e.node_id, e.is_rest, e.pfields.get('freq')) for e in uc_copy]
        assert orig_data == copy_data

    def test_copy_is_independent(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
        uc_copy = uc.copy()
        uc.set_pfields(1, freq=999)
        assert uc.get_parameter(1, 'freq') == 999
        assert uc_copy.get_parameter(1, 'freq') != 999


class TestCompositionalUnitUseCases:

    def test_chronostasis_pattern(self):
        np.random.seed(99)
        inst_pat = Pattern([JsInst.Kick(), JsInst.Snare(), JsInst.HatClosed()])
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
        uts = UTS()
        uts.extend([uc] * 2)
        for unit in uts:
            for leaf in unit.rt.leaf_nodes:
                unit.set_instrument(leaf, next(inst_pat))
                unit.set_pfields(leaf, vel=np.random.uniform(0.5, 0.9))

        unit0_events = list(uts[0])
        expected_synths_0 = ['Kick', 'Snare', 'HatClosed', 'Kick']
        expected_vels_0 = [0.768911, 0.695231, 0.830198, 0.512579]
        for e, synth, vel in zip(unit0_events, expected_synths_0, expected_vels_0):
            assert (e.pfields.get('synth_name') or e.pfields.get('synthName')) == synth
            assert abs(e.pfields.get('vel') - vel) < 0.001

        unit1_events = list(uts[1])
        expected_synths_1 = ['Snare', 'HatClosed', 'Kick', 'Snare']
        expected_vels_1 = [0.823220, 0.726247, 0.619049, 0.518678]
        for e, synth, vel in zip(unit1_events, expected_synths_1, expected_vels_1):
            assert (e.pfields.get('synth_name') or e.pfields.get('synthName')) == synth
            assert abs(e.pfields.get('vel') - vel) < 0.001

    def test_multi_voice_block(self):
        tempus = '10/16'
        beat = '1/16'
        bpm = 140
        S1 = ((3, (1,)*4), (4, (1,)*6), (3, (1,)*4))
        S2 = ((5, (1,)*5),)*2

        uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
        uts1 = UTS()
        uts1.extend([uc1] * 2)

        uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
        uts2 = UTS()
        uts2.extend([uc2] * 2)

        bt = BT([uts1, uts2])
        assert abs(bt.duration - 8.571428571428571) < 1e-9
        rows = list(bt)
        assert len(rows) == 2
        assert rows[0].size == 28
        assert rows[1].size == 20


class TestCompositionalUnitArticulations:

    def _make_uc(self):
        return UC(
            tempus='4/4',
            prolatio=((2, (1, 1)), (2, (1, 1))),
            beat='1/4',
            bpm=120,
            inst=JsInst.Kick(),
            pfields={'amp': 0.0}
        )

    def test_parameter_tree_has_instrument_api_not_slur(self):
        pt = ParameterTree(4, (1, 1, 1, 1))
        assert hasattr(pt, 'set_instrument')
        assert pt.get(0, 'instrument') is None
        assert not hasattr(pt, 'add_slur')

    def test_apply_slur_overlap_raises(self):
        uc = self._make_uc()
        inner_nodes = uc.rt.at_depth(1)
        uc.apply_slur(node=inner_nodes[0])
        with pytest.raises(ValueError):
            uc.apply_slur(node=inner_nodes[0])

    def test_apply_slur_with_rests_returns_empty_when_no_segment(self):
        uc = self._make_uc()
        inner_nodes = uc.rt.at_depth(1)
        uc.make_rest(uc.rt.subtree_leaves(inner_nodes[0])[0])
        result = uc.apply_slur(node=inner_nodes[0])
        assert result == []

    def test_make_rest_splits_overlapping_slur(self):
        uc = self._make_uc()
        inner_nodes = uc.rt.at_depth(1)
        slur_id = uc.apply_slur(node=inner_nodes[0])
        assert slur_id in uc._slur_specs
        uc.make_rest(uc.rt.subtree_leaves(inner_nodes[0])[0])
        assert slur_id not in uc._slur_specs

    def test_apply_envelope_same_pfield_overwrite(self):
        uc = self._make_uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        inner_nodes = uc.rt.at_depth(1)
        uc.apply_envelope(envelope=env, pfields='amp', node=inner_nodes[0])
        uc.apply_envelope(envelope=env, pfields='amp', node=inner_nodes[0])
        _ = uc.events

    def test_apply_envelope_different_pfields_can_overlap(self):
        uc = self._make_uc()
        uc.set_pfields(uc.rt.root, vel=0.0)
        env = Envelope([0.0, 1.0], times=[1.0])
        inner_nodes = uc.rt.at_depth(1)
        uc.apply_envelope(envelope=env, pfields='amp', node=inner_nodes[0])
        uc.apply_envelope(envelope=env, pfields='vel', node=inner_nodes[0])
        ev = uc.events
        assert ev['pfields'].apply(lambda d: 'amp' in d).all()
        assert ev['pfields'].apply(lambda d: 'vel' in d).all()

    def test_apply_envelope_skips_rests_without_error(self):
        uc = self._make_uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        inner_nodes = uc.rt.at_depth(1)
        first_leaf = uc.rt.subtree_leaves(inner_nodes[0])[0]
        uc.make_rest(first_leaf)
        uc.apply_envelope(envelope=env, pfields='amp', node=inner_nodes[0])
        _ = uc.events

    def test_offset_take_overflow_raises(self):
        uc = self._make_uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        inner_nodes = uc.rt.at_depth(1)
        with pytest.raises(ValueError):
            uc.apply_envelope(envelope=env, pfields='amp', node=inner_nodes[0], offset=1, take=3)

    def test_mixed_node_selection_must_be_contiguous(self):
        uc = self._make_uc()
        leaves = list(uc.rt.leaf_nodes)
        with pytest.raises(ValueError):
            uc.apply_slur(node=[leaves[0], leaves[2]])

    def test_slur_single_leaf_raises(self):
        uc = self._make_uc()
        leaf = uc.rt.leaf_nodes[0]
        with pytest.raises(ValueError, match="at least two leaves"):
            uc.apply_slur(node=leaf)

    def test_per_node_mode_bakes_to_all_groups(self):
        uc = self._make_uc()
        inner_nodes = uc.rt.at_depth(1)
        uc.apply_envelope(
            envelope=Envelope([0.0, 1.0], times=[1.0]),
            pfields='amp',
            node=inner_nodes,
            mode="per_node"
        )
        ev = uc.events
        assert ev['pfields'].apply(lambda d: 'amp' in d).all()

    def test_slur_per_node_mode_is_atomic_on_failure(self):
        uc = self._make_uc()
        inner_nodes = uc.rt.at_depth(1)
        uc.apply_slur(node=inner_nodes[0])
        before = len(uc._slur_specs)
        with pytest.raises(ValueError):
            uc.apply_slur(node=inner_nodes, mode="per_node")
        after = len(uc._slur_specs)
        assert before == after

    def test_uc_pt_snapshot_reflects_envelope(self):
        uc = self._make_uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(envelope=env, pfields='amp', node=uc.rt.root)
        pt_snapshot = uc.pt
        leaves = list(uc.rt.leaf_nodes)
        values = [pt_snapshot.get(leaf, 'amp') for leaf in leaves]
        assert values[0] == 0.0
        assert values[-1] > values[0]


def _assert_rt_pt_same_structure_and_ids(uc):
    rt, pt = uc._rt, uc._pt
    rt_nodes = set(rt.nodes)
    pt_nodes = set(pt.nodes)
    assert rt_nodes == pt_nodes, f"Node sets differ: RT {rt_nodes} vs PT {pt_nodes}"
    assert rt.root == pt.root
    for n in rt_nodes:
        rt_succ = set(rt.successors(n))
        pt_succ = set(pt.successors(n))
        assert rt_succ == pt_succ, f"Successors of {n} differ: RT {rt_succ} vs PT {pt_succ}"
    assert rt.leaf_nodes == pt.leaf_nodes


class TestCompositionalUnitRT_PTSync:
    def test_initial_uc_rt_pt_same_structure_and_ids(self):
        uc = UC(tempus='4/4', prolatio=(4, 2, 1, 1), beat='1/4', bpm=120)
        _assert_rt_pt_same_structure_and_ids(uc)

    def test_subdivide_keeps_rt_pt_same_structure_and_ids(self):
        uc = UC(tempus='4/4', prolatio=(4, 2, 1, 1), beat='1/4', bpm=120)
        leaf = uc._rt.leaf_nodes[0]
        uc.subdivide(leaf, (1, 1, 1))
        _assert_rt_pt_same_structure_and_ids(uc)
        assert len(uc._rt.nodes) == 8
        assert uc._rt.leaf_nodes == uc._pt.leaf_nodes

    def test_subdivide_cascades_pfields_to_new_nodes(self):
        uc = UC(tempus='4/4', prolatio=(4, 2, 1, 1), beat='1/4', bpm=120, pfields=['freq'])
        uc.set_pfields(uc._rt.leaf_nodes[0], freq=100)
        leaf = uc._rt.leaf_nodes[0]
        uc.subdivide(leaf, (1, 1, 1))
        new_leaves = list(uc._rt.successors(leaf))
        for n in new_leaves:
            assert uc.get_parameter(n, 'freq') == 100

    def test_add_child_keeps_rt_pt_same_structure_and_ids(self):
        uc = UC(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=120)
        new_id = uc.add_child(uc._rt.root, label=1)
        _assert_rt_pt_same_structure_and_ids(uc)
        assert new_id in uc._rt.nodes
        assert new_id in uc._pt.nodes
        assert new_id in uc._rt.successors(uc._rt.root)
        assert new_id in uc._pt.successors(uc._pt.root)

    def test_prune_keeps_rt_pt_same_structure_and_ids(self):
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120)
        inner = uc._rt.at_depth(1)[0]
        uc.prune(inner)
        _assert_rt_pt_same_structure_and_ids(uc)

    def test_remove_subtree_keeps_rt_pt_same_structure_and_ids(self):
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120)
        inner = uc._rt.at_depth(1)[0]
        uc.remove_subtree(inner)
        _assert_rt_pt_same_structure_and_ids(uc)

    def test_subdivide_then_events_use_pt_node_ids(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1), beat='1/4', bpm=120, pfields=['freq'])
        leaf = uc._rt.leaf_nodes[0]
        uc.subdivide(leaf, (1, 1))
        events_df = uc.events
        event_node_ids = events_df['node_id'].tolist()
        assert set(event_node_ids) <= set(uc._rt.nodes)
        assert set(event_node_ids) <= set(uc._pt.nodes)
        assert len(event_node_ids) == 4

    def test_prune_uc_matches_fresh_built_structure(self):
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120)
        inner = uc._rt.at_depth(1)[0]
        uc.prune(inner)
        expected = UC(tempus='4/4', prolatio=(1, 1, (2, (1, 1))), beat='1/4', bpm=120)
        _ = uc.events
        _ = expected.events
        assert uc.durations == expected.durations
        assert uc.onsets == expected.onsets
        assert len(uc.leaf_nodes) == len(expected.leaf_nodes)
        _assert_rt_structurally_equivalent(uc._rt, expected._rt)
        _assert_rt_pt_same_structure_and_ids(uc)

    def test_remove_subtree_uc_matches_fresh_built_structure(self):
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), (2, (1, 1))), beat='1/4', bpm=120)
        inner = uc._rt.at_depth(1)[0]
        uc.remove_subtree(inner)
        expected = UC(tempus='4/4', prolatio=((2, (1, 1)),), beat='1/4', bpm=120)
        _ = uc.events
        _ = expected.events
        assert uc.durations == expected.durations
        assert uc.onsets == expected.onsets
        assert len(uc.leaf_nodes) == len(expected.leaf_nodes)
        _assert_rt_structurally_equivalent(uc._rt, expected._rt)
        _assert_rt_pt_same_structure_and_ids(uc)


class TestPattern:

    def test_basic_cycling(self):
        pat = Pattern([1, 2, 3])
        assert len(pat) == 3
        vals = [next(pat) for _ in range(9)]
        assert vals == [1, 2, 3, 1, 2, 3, 1, 2, 3]

    def test_nested_pattern(self):
        pat = Pattern([1, [2, 3]])
        vals = [next(pat) for _ in range(6)]
        assert vals == [1, 2, 1, 3, 1, 2]

    def test_end_truthy(self):
        pat = Pattern([10, 20], end=-999)
        vals = [next(pat) for _ in range(5)]
        assert vals == [10, 20, -999, -999, -999]

    def test_end_false_default_loops(self):
        pat = Pattern([10, 20, 30], end=False)
        vals = [next(pat) for _ in range(6)]
        assert vals == [10, 20, 30, 10, 20, 30]

    def test_end_none_is_falsy_loops(self):
        pat = Pattern([10, 20, 30], end=None)
        vals = [next(pat) for _ in range(6)]
        assert vals == [10, 20, 30, 10, 20, 30]

    def test_end_zero_is_falsy_loops(self):
        pat = Pattern([10, 20, 30], end=0)
        vals = [next(pat) for _ in range(6)]
        assert vals == [10, 20, 30, 10, 20, 30]

    def test_end_with_sentinel(self):
        STOP = object()
        pat = Pattern([10, 20, 30], end=STOP)
        vals = [next(pat) for _ in range(5)]
        assert vals[:3] == [10, 20, 30]
        assert vals[3] is STOP
        assert vals[4] is STOP


class TestPartitionSet:

    def test_ps_8_3(self):
        ps = PS(8, 3)
        assert ps.partitions == ((6, 1, 1), (5, 2, 1), (4, 3, 1), (4, 2, 2), (3, 3, 2))
        assert len(ps.partitions) == 5

    def test_ps_5_2(self):
        ps = PS(5, 2)
        assert ps.partitions == ((4, 1), (3, 2))

    def test_partitions_as_rt_subdivisions(self):
        for partition in PS(8, 3).partitions:
            rt = RT(subdivisions=partition)
            assert sum(abs(d) for d in rt.durations) == 1


class TestConverters:

    def test_rt_converter(self):
        from klotho.utils.playback.tonejs.converters import rhythm_tree_to_events
        rt = RT(subdivisions=(1, 1, 1, 1))
        result = rhythm_tree_to_events(rt, beat='1/4', bpm=120)
        events = result['events']
        assert len(events) == 4
        assert events[0]['instrument'] == 'membrane'
        assert abs(events[0]['start'] - 0.0) < 1e-9
        assert abs(events[0]['duration'] - 0.5) < 1e-9
        assert abs(events[3]['start'] - 1.5) < 1e-9

    def test_ut_converter(self):
        from klotho.utils.playback.tonejs.converters import temporal_unit_to_events
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        result = temporal_unit_to_events(ut)
        events = result['events']
        assert len(events) == 4
        for ev in events:
            assert ev['instrument'] == 'membrane'

    def test_uc_converter(self):
        from klotho.utils.playback.tonejs.converters import convert_to_events
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kalimba())
        uc.set_pfields(1, freq=262)
        uc.set_pfields(2, freq=330)
        uc.set_pfields(3, freq=392)
        uc.set_pfields(4, freq=523)
        result = convert_to_events(uc)
        events = result['events']
        assert len(events) == 4
        assert events[0]['instrument'] == 'Kalimba'
        assert events[0]['pfields']['freq'] == 262
        assert events[3]['pfields']['freq'] == 523
        assert 'Kalimba' in result.get('instruments', {})
