"""Bind's read set (charter WL-30 + NEW-20).

Both items are one mechanism. A Bind's ``ctx.index``/``ctx.total`` are its
position among the leaf descendants of *the node holding the raw override*.
So whenever the raw Bind ends up on a leaf, that leaf is its own read set and
every node reads index 0 of 1 -- a pan spread resolves to a constant 0.

Two routes put it there. Writing through a leaf selector, which is the
docstring's own example (WL-30). And ``subdivide``, which copied the node's
EFFECTIVE parameters onto each new child, materializing an inherited Bind as
a raw override on nodes that should merely have inherited it (NEW-20).
"""

import random

import pytest

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.parameters.bind import Bind


def spread(i, n):
    return round(i / max(n - 1, 1), 3)


def _uc(prolatio=(1, 1, 1, 1)):
    return CompositionalUnit(tempus='4/4', prolatio=prolatio, bpm=120)


def _pans(uc):
    return [uc.pt[leaf.id].get('pan') for leaf in uc.leaves]


class TestTheReadSetSpansTheWholeSelection:
    def test_a_root_stored_bind_spreads_across_every_leaf(self):
        uc = _uc()
        uc.root.set_pfields(pan=Bind.index(map=spread))
        assert _pans(uc) == [0.0, 0.333, 0.667, 1.0]

    def test_a_leaf_stored_bind_is_refused_rather_than_constant(self):
        uc = _uc()
        uc.leaves.set_pfields(pan=Bind.index(map=spread))
        with pytest.raises(ValueError, match="read set is that single node"):
            _pans(uc)

    def test_the_error_names_the_way_out(self):
        uc = _uc()
        uc.leaves.set_pfields(pan=Bind.index(map=spread))
        with pytest.raises(ValueError, match="common ancestor"):
            _pans(uc)

    def test_a_single_leaf_tree_is_not_a_collapse(self):
        """One leaf legitimately reads index 0 of 1; that must not raise."""
        uc = _uc(prolatio=(1,))
        uc.leaves.set_pfields(pan=Bind.index(map=spread))
        assert _pans(uc) == [0.0]

    def test_a_bare_index_bind_is_guarded_too(self):
        uc = _uc()
        uc.leaves.set_pfields(pan=Bind.index())
        with pytest.raises(ValueError):
            _pans(uc)

    def test_a_bind_that_does_not_read_the_selection_is_unaffected(self):
        uc = _uc()
        uc.leaves.set_pfields(pan=Bind(lambda c: 0.5))
        assert _pans(uc) == [0.5] * 4


class TestSubdivideDoesNotCopyBindsDown:
    def test_new_children_inherit_rather_than_own_the_bind(self):
        uc = _uc()
        uc.root.set_pfields(pan=Bind.index(map=spread))
        uc.subdivide(1, (1, 1))
        root = uc._rt.root
        assert all(uc._bind_origin(leaf.id, 'pan') == root for leaf in uc.leaves)

    def test_the_spread_stays_coherent_after_a_structural_edit(self):
        uc = _uc()
        uc.root.set_pfields(pan=Bind.index(map=spread))
        assert _pans(uc) == [0.0, 0.333, 0.667, 1.0]
        uc.subdivide(1, (1, 1))
        assert _pans(uc) == [0.0, 0.25, 0.5, 0.75, 1.0]

    def test_a_plain_inherited_value_is_still_carried(self):
        uc = _uc()
        uc.root.set_pfields(amp=0.9)
        uc.subdivide(1, (1, 1))
        assert all(uc.pt[leaf.id].get('amp') == 0.9 for leaf in uc.leaves)

    def test_a_node_own_plain_override_is_still_carried(self):
        uc = _uc()
        uc.set_pfields(1, amp=0.3)
        uc.subdivide(1, (1, 1))
        assert [uc.pt[leaf.id].get('amp') for leaf in uc.leaves][:2] == [0.3, 0.3]


class TestMemoization:
    def test_a_stochastic_bind_still_memoizes(self):
        """The memo exists so stochastic functions are stable across reads;
        that must survive the selection-reading carve-out."""
        uc = _uc()
        uc.root.set_pfields(amp=Bind(lambda c: random.random()))
        first = [uc.pt[leaf.id].get('amp') for leaf in uc.leaves]
        assert first == [uc.pt[leaf.id].get('amp') for leaf in uc.leaves]

    def test_a_stochastic_bind_keeps_existing_values_across_a_subdivide(self):
        uc = _uc()
        uc.root.set_pfields(amp=Bind(lambda c: random.random()))
        before = {leaf.id: uc.pt[leaf.id].get('amp') for leaf in uc.leaves}
        uc.subdivide(1, (1, 1))
        after = {leaf.id: uc.pt[leaf.id].get('amp') for leaf in uc.leaves}
        for node, value in before.items():
            if node in after:
                assert after[node] == value

    def test_a_selection_reading_bind_recomputes_instead(self):
        uc = _uc()
        uc.root.set_pfields(pan=Bind.index(map=spread))
        _pans(uc)
        uc.subdivide(1, (1, 1))
        assert _pans(uc)[1] == 0.25


class TestBindConstruction:
    def test_index_marks_itself_as_selection_reading(self):
        assert Bind.index().reads_selection is True
        assert Bind.index(map=spread).reads_selection is True

    def test_a_plain_bind_does_not(self):
        assert Bind(lambda c: 1).reads_selection is False

    def test_mfield_does_not(self):
        assert Bind.mfield('chord').reads_selection is False

    def test_a_non_callable_is_still_refused(self):
        with pytest.raises(TypeError, match="callable"):
            Bind(3)
