"""Unit tests for UT/UC selector surface (`UTNodeSelector`, `UCNodeSelector`).

These cover the API spelling of the selector: construction from each
traversal method, fluent-verb delegation, indexing / slicing / fancy
indexing, filter / where / set algebra, equality spec, bool spec,
``make_rest`` iterable support, and the fluent-root idioms.

Behavior preservation (that the refactored delegation produces the same
downstream results as the verbose pre-refactor API) is covered separately
by ``test_parity_refactor.py`` against golden-master fixtures frozen
before the refactor.
"""

import numpy as np
import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.chronos.temporal_units.temporal import (
    NodeContext,
    UTNodeSelector,
)
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, SynthDefInstrument
from klotho.thetos.composition.compositional import UCNodeSelector
from klotho.topos.collections.sequences import Pattern


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _uc_simple():
    """UC with 4 sibling leaves at root (flat)."""
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120,
              inst=SynthDefInstrument.tri())


def _uc_nested():
    """UC with root -> 2 branches, each with sub-leaves.

    root
     |-- branch_A  (D=2)  -> 3 leaves
     |-- branch_B  (D=1)  -> 2 leaves (via 2-tuple S)
    """
    return UC(tempus='5/8', prolatio=((2, (1, 1, 1)), (1, (1, 1))),
              beat='1/8', bpm=120, inst=SynthDefInstrument.tri())


def _uc_single_leaf():
    """UC with a single-leaf 'duration' prolatio."""
    return UC(tempus='4/4', prolatio='d', bpm=120,
              inst=SynthDefInstrument.tri())


# ---------------------------------------------------------------------------
# Construction via traversal methods
# ---------------------------------------------------------------------------


class TestSelectorConstruction:
    def test_leaves_returns_uc_selector(self):
        uc = _uc_simple()
        sel = uc.leaves
        assert isinstance(sel, UCNodeSelector)
        assert isinstance(sel, UTNodeSelector)
        assert sel.owner is uc

    def test_root_returns_one_element_selector(self):
        uc = _uc_simple()
        sel = uc.root
        assert isinstance(sel, UCNodeSelector)
        assert len(sel) == 1
        assert sel.first == uc._rt.root

    def test_at_depth_returns_selector(self):
        uc = _uc_nested()
        sel = uc.at_depth(1)
        assert isinstance(sel, UCNodeSelector)
        assert len(sel) == 2   # two branches

    def test_leaves_of_returns_selector(self):
        uc = _uc_nested()
        branches = uc.at_depth(1)
        sub = uc.leaves_of(branches.first)
        assert isinstance(sub, UCNodeSelector)
        assert set(sub.ids).issubset(set(uc.leaves.ids))

    def test_successors_returns_selector(self):
        uc = _uc_nested()
        sel = uc.successors(uc._rt.root)
        assert isinstance(sel, UCNodeSelector)
        assert len(sel) == 2

    def test_select_varargs(self):
        uc = _uc_simple()
        leaf_ids = uc._rt.leaf_nodes
        sel = uc.select(leaf_ids[0], leaf_ids[2])
        assert sel.ids == (leaf_ids[0], leaf_ids[2])

    def test_select_single_iterable(self):
        uc = _uc_simple()
        leaf_ids = uc._rt.leaf_nodes
        sel = uc.select([leaf_ids[1], leaf_ids[3]])
        assert sel.ids == (leaf_ids[1], leaf_ids[3])

    def test_ut_traversal_returns_ut_selector(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        sel = ut.leaves
        assert type(sel) is UTNodeSelector   # NOT UCNodeSelector
        assert sel.owner is ut

    def test_dropped_methods_raise_attribute_error(self):
        uc = _uc_simple()
        for attr in ('parent', 'ancestors', 'descendants', 'predecessors',
                     'siblings', 'branch', 'lowest_common_ancestor',
                     'leaf_nodes', 'subtree_leaves'):
            with pytest.raises(AttributeError):
                getattr(uc, attr)

    def test_scalar_forwards_unchanged(self):
        uc = _uc_nested()
        assert uc.depth == uc._rt.depth
        assert uc.k == uc._rt.k
        assert uc.depth_of(uc._rt.root) == 0
        assert uc.out_degree(uc._rt.root) == uc._rt.out_degree(uc._rt.root)


# ---------------------------------------------------------------------------
# Sequence protocol
# ---------------------------------------------------------------------------


class TestSequenceProtocol:
    def test_iter_yields_ints(self):
        uc = _uc_simple()
        sel = uc.leaves
        ids = list(sel)
        assert all(isinstance(n, int) for n in ids)
        assert tuple(ids) == uc._rt.leaf_nodes

    def test_len(self):
        uc = _uc_simple()
        assert len(uc.leaves) == 4
        assert len(uc.root) == 1

    def test_contains(self):
        uc = _uc_simple()
        first = uc.leaves.first
        assert first in uc.leaves
        assert (first + 999) not in uc.leaves

    def test_bool_empty_is_false(self):
        uc = _uc_simple()
        empty = uc.leaves.filter(lambda c: False)
        assert bool(empty) is False
        assert not empty

    def test_bool_nonempty_is_true(self):
        uc = _uc_simple()
        assert bool(uc.leaves) is True
        assert uc.leaves

    def test_set_over_selector(self):
        uc = _uc_simple()
        assert set(uc.leaves) == set(uc._rt.leaf_nodes)

    def test_list_over_selector(self):
        uc = _uc_simple()
        assert list(uc.leaves) == list(uc._rt.leaf_nodes)


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


class TestIndexing:
    def test_int_index_returns_one_element_selector(self):
        uc = _uc_simple()
        sel = uc.leaves
        first_sel = sel[0]
        assert isinstance(first_sel, UCNodeSelector)
        assert len(first_sel) == 1
        assert first_sel.first == sel._ids[0]

    def test_negative_int_index(self):
        uc = _uc_simple()
        sel = uc.leaves
        last_sel = sel[-1]
        assert last_sel.first == sel.last

    def test_slice_index(self):
        uc = _uc_simple()
        sel = uc.leaves
        sliced = sel[1:3]
        assert isinstance(sliced, UCNodeSelector)
        assert sliced.ids == sel.ids[1:3]

    def test_fancy_list_index(self):
        uc = _uc_simple()
        sel = uc.leaves
        fancy = sel[[0, 2]]
        assert isinstance(fancy, UCNodeSelector)
        assert fancy.ids == (sel.ids[0], sel.ids[2])

    def test_fancy_tuple_index(self):
        uc = _uc_simple()
        sel = uc.leaves
        fancy = sel[(1, 3)]
        assert fancy.ids == (sel.ids[1], sel.ids[3])

    def test_invalid_index_raises(self):
        uc = _uc_simple()
        with pytest.raises(TypeError):
            uc.leaves['foo']


# ---------------------------------------------------------------------------
# Raw access
# ---------------------------------------------------------------------------


class TestRawAccess:
    def test_ids_is_tuple(self):
        uc = _uc_simple()
        assert isinstance(uc.leaves.ids, tuple)
        assert uc.leaves.ids == uc._rt.leaf_nodes

    def test_first_last_are_ints(self):
        uc = _uc_simple()
        sel = uc.leaves
        assert isinstance(sel.first, int)
        assert isinstance(sel.last, int)
        assert sel.first == sel._ids[0]
        assert sel.last == sel._ids[-1]

    def test_owner_property(self):
        uc = _uc_simple()
        assert uc.leaves.owner is uc


# ---------------------------------------------------------------------------
# Composition: filter / where / set algebra
# ---------------------------------------------------------------------------


class TestComposition:
    def test_filter_receives_node_context(self):
        uc = _uc_simple()
        contexts = []
        _ = uc.leaves.filter(lambda c: contexts.append(c) or True)
        assert all(isinstance(c, NodeContext) for c in contexts)
        total = len(uc.leaves)
        for i, c in enumerate(contexts):
            assert c.index == i
            assert c.total == total
            assert c.node == uc.leaves._ids[i]

    def test_filter_preserves_subclass(self):
        uc = _uc_simple()
        filtered = uc.leaves.filter(lambda c: c.index % 2 == 0)
        assert isinstance(filtered, UCNodeSelector)

    def test_where_mask(self):
        uc = _uc_simple()
        mask = [True, False, True, False]
        filtered = uc.leaves.where(mask)
        assert len(filtered) == 2
        assert filtered.ids == (uc.leaves._ids[0], uc.leaves._ids[2])

    def test_where_mask_length_mismatch(self):
        uc = _uc_simple()
        with pytest.raises(ValueError, match="mask length mismatch"):
            uc.leaves.where([True, False])

    def test_union_preserves_order_and_dedups(self):
        uc = _uc_simple()
        a = uc.leaves[[0, 1]]
        b = uc.leaves[[1, 2]]
        result = a | b
        assert result.ids == (uc.leaves._ids[0], uc.leaves._ids[1], uc.leaves._ids[2])

    def test_intersection(self):
        uc = _uc_simple()
        a = uc.leaves[[0, 1, 2]]
        b = uc.leaves[[1, 2, 3]]
        result = a & b
        assert set(result.ids) == {uc.leaves._ids[1], uc.leaves._ids[2]}

    def test_difference(self):
        uc = _uc_simple()
        a = uc.leaves[[0, 1, 2]]
        b = uc.leaves[[1, 2]]
        result = a - b
        assert result.ids == (uc.leaves._ids[0],)

    def test_set_algebra_cross_owner_returns_not_implemented(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        sel1 = uc1.leaves
        sel2 = uc2.leaves
        # NotImplemented returned from __or__ causes Python to return NotImplemented
        # overall from `sel1 | sel2`; with reflected method same result.
        with pytest.raises(TypeError):
            sel1 | sel2
        with pytest.raises(TypeError):
            sel1 & sel2
        with pytest.raises(TypeError):
            sel1 - sel2


# ---------------------------------------------------------------------------
# .leaves sub-expansion
# ---------------------------------------------------------------------------


class TestLeavesSubExpansion:
    def test_leaves_of_multi_branch_selection_expands(self):
        uc = _uc_nested()
        branches = uc.at_depth(1)
        result = branches.leaves
        # Expansion should include all leaves (union of each branch's subtree)
        assert set(result.ids) == set(uc.leaves.ids)

    def test_leaves_of_single_branch(self):
        uc = _uc_nested()
        first_branch = uc.at_depth(1)[0]
        result = first_branch.leaves
        expected = set(uc._rt.subtree_leaves(first_branch.first))
        assert set(result.ids) == expected

    def test_leaves_on_leaf_selection_is_identity(self):
        uc = _uc_simple()
        assert uc.leaves.leaves.ids == uc.leaves.ids

    def test_leaves_preserves_order_and_dedups(self):
        uc = _uc_nested()
        # two overlapping subtrees via ad-hoc selection
        branches = uc.at_depth(1)
        # Union the branches twice - dedup should kick in
        dup = uc.select(branches.first, branches.last, branches.first)
        result = dup.leaves
        # no duplicate ids
        assert len(result.ids) == len(set(result.ids))


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------


class TestEqualityAndHash:
    def test_equal_to_tuple_with_same_ids(self):
        uc = _uc_simple()
        sel = uc.leaves
        assert sel == tuple(uc._rt.leaf_nodes)

    def test_equal_to_list_with_same_ids(self):
        uc = _uc_simple()
        sel = uc.leaves
        assert sel == list(uc._rt.leaf_nodes)

    def test_not_equal_to_bare_int(self):
        uc = _uc_simple()
        assert uc.root != uc._rt.root   # selector vs int -> False loudly
        assert not (uc.root == 0)

    def test_equal_to_1_tuple_when_single_element(self):
        uc = _uc_simple()
        assert uc.root == (uc._rt.root,)

    def test_same_owner_same_ids_equal(self):
        uc = _uc_simple()
        assert uc.leaves == uc.leaves

    def test_cross_owner_not_equal(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        # Same ids (identical shape) but different owners
        assert uc1.leaves.ids == uc2.leaves.ids
        assert uc1.leaves != uc2.leaves

    def test_hash_differs_across_owners(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        assert hash(uc1.leaves) != hash(uc2.leaves)

    def test_hash_equal_for_same_selector(self):
        uc = _uc_simple()
        s1 = uc.leaves
        s2 = uc.leaves
        assert hash(s1) == hash(s2)


# ---------------------------------------------------------------------------
# Fluent verb delegation
# ---------------------------------------------------------------------------


class TestFluentVerbDelegation:
    def test_set_pfields_static_on_each_leaf(self):
        uc = _uc_simple()
        uc.leaves.set_pfields(amp=0.3)
        for leaf in uc._rt.leaf_nodes:
            assert uc.get_pfield(leaf, 'amp') == 0.3

    def test_set_pfields_pattern_cycles_per_leaf(self):
        uc = _uc_simple()
        uc.leaves.set_pfields(freq=Pattern([100.0, 200.0, 300.0]))
        vals = [uc.get_pfield(leaf, 'freq') for leaf in uc._rt.leaf_nodes]
        # 4 leaves, Pattern of length 3: cycles 100, 200, 300, 100
        assert vals == [100.0, 200.0, 300.0, 100.0]

    def test_set_pfields_tuple_is_poly_event_static(self):
        uc = _uc_simple()
        chord = (440.0, 550.0, 660.0)
        uc.leaves.set_pfields(freq=chord)
        for leaf in uc._rt.leaf_nodes:
            assert uc.get_pfield(leaf, 'freq') == chord

    def test_set_mfields_pattern_cycles(self):
        uc = _uc_simple()
        uc.leaves.set_mfields(strum=Pattern([0.0, 0.5, -0.5]))
        vals = [uc.get_mfield(leaf, 'strum') for leaf in uc._rt.leaf_nodes]
        assert vals == [0.0, 0.5, -0.5, 0.0]

    def test_set_instrument(self):
        uc = _uc_simple()
        tri = SynthDefInstrument.tri()
        uc.leaves[0].set_instrument(tri)
        assert uc.get_instrument(uc.leaves[0].first) is tri

    def test_root_set_pfields_equivalent_to_raw(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        uc1.root.set_pfields(amp=0.25)
        uc2.set_pfields(uc2._rt.root, amp=0.25)
        assert uc1.get_pfield(uc1._rt.root, 'amp') == uc2.get_pfield(uc2._rt.root, 'amp')
        for leaf in uc1._rt.leaf_nodes:
            # Cascade: all leaves inherit
            assert uc1.get_pfield(leaf, 'amp') == 0.25

    def test_root_set_instrument_equivalent_to_raw(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        tri = SynthDefInstrument.tri()
        uc1.root.set_instrument(tri)
        uc2.set_instrument(uc2._rt.root, tri)
        for leaf in uc1._rt.leaf_nodes:
            assert type(uc1.get_instrument(leaf)) is type(uc2.get_instrument(leaf))

    def test_root_apply_envelope_equivalent_to_raw(self):
        uc1 = _uc_simple()
        uc2 = _uc_simple()
        env = Envelope([0.1, 0.5, 0.1], times=[0.5, 0.5])
        uc1.root.apply_envelope(env, 'amp')
        uc2.apply_envelope(env, 'amp', node=uc2._rt.root)
        for leaf in uc1._rt.leaf_nodes:
            assert uc1.get_pfield(leaf, 'amp') == uc2.get_pfield(leaf, 'amp')

    def test_root_apply_slur_slurs_all_leaves(self):
        uc = _uc_simple()
        uc.root.apply_slur()
        assert len(uc._slur_specs) == 1
        (slur_id, spec), = uc._slur_specs.items()
        assert set(spec['leaf_nodes']) == set(uc._rt.leaf_nodes)

    def test_apply_slur_single_leaf_uc_raises(self):
        uc = _uc_single_leaf()
        with pytest.raises(ValueError):
            uc.root.apply_slur()

    def test_slice_apply_slur(self):
        uc = _uc_simple()
        uc.leaves[1:3].apply_slur()
        assert len(uc._slur_specs) == 1
        (slur_id, spec), = uc._slur_specs.items()
        assert spec['leaf_nodes'] == uc._rt.leaf_nodes[1:3]

    def test_at_depth_apply_envelope_per_node_returns_list(self):
        uc = _uc_nested()
        env = Envelope([0.1, 0.5, 0.1], times=[0.5, 0.5])
        result = uc.at_depth(1).apply_envelope(env, 'amp',
                                               scope='per_node', control=True)
        assert isinstance(result, list)
        assert len(result) == len(uc.at_depth(1))

    def test_clear_parameters_on_selector(self):
        uc = _uc_simple()
        uc.leaves.set_pfields(amp=0.3)
        uc.leaves.clear_parameters()
        # after clearing, leaves have no overrides; inherited defaults differ
        # per instrument, but direct pfield overrides should be gone
        for leaf in uc._rt.leaf_nodes:
            # pt.get_pfield returns None when no override at this node and
            # no ancestor has one either.
            raw = uc._pt.get_pfield(leaf, 'amp')
            assert raw is None


# ---------------------------------------------------------------------------
# make_rest iterable support
# ---------------------------------------------------------------------------


class TestMakeRestIterable:
    def test_make_rest_int_still_works(self):
        uc = _uc_simple()
        leaf = uc._rt.leaf_nodes[1]
        uc.make_rest(leaf)
        assert uc._rt[leaf]['proportion'] < 0

    def test_make_rest_iterable(self):
        uc = _uc_simple()
        targets = [uc._rt.leaf_nodes[0], uc._rt.leaf_nodes[2]]
        uc.make_rest(targets)
        for leaf in targets:
            assert uc._rt[leaf]['proportion'] < 0
        # untouched leaves are still sounding
        untouched = [uc._rt.leaf_nodes[1], uc._rt.leaf_nodes[3]]
        for leaf in untouched:
            assert uc._rt[leaf]['proportion'] > 0

    def test_make_rest_via_selector(self):
        uc = _uc_simple()
        uc.leaves[[0, 2]].make_rest()
        for leaf in [uc._rt.leaf_nodes[0], uc._rt.leaf_nodes[2]]:
            assert uc._rt[leaf]['proportion'] < 0

    def test_make_rest_iterable_heals_slurs_once(self):
        uc = _uc_simple()
        uc.leaves[0:3].apply_slur()   # slur over leaves 0,1,2
        # rest 1 & 2 (both inside the slur) via iterable call
        uc.make_rest([uc._rt.leaf_nodes[1], uc._rt.leaf_nodes[2]])
        # Original slur split; remaining segment must be >= 2 leaves to survive.
        # Leaves 1 and 2 are rested; only leaf 0 remains in original span ->
        # segment <2 -> slur removed entirely.
        assert len(uc._slur_specs) == 0


# ---------------------------------------------------------------------------
# __repr__ smoke
# ---------------------------------------------------------------------------


class TestRepr:
    def test_repr_contains_class_and_ids(self):
        uc = _uc_simple()
        r = repr(uc.leaves)
        assert 'UCNodeSelector' in r
        assert str(list(uc._rt.leaf_nodes)) in r
