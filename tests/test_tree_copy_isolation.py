"""``Tree.copy()`` promises a deep copy, so the twins must not share payloads.

``GraphCore.copy`` is documented as "Create a deep copy of this graph" and is
implemented as ``copy.deepcopy(self)``. ``Tree.__deepcopy__`` clones the
backing rustworkx graph with ``self._rx.copy()``, which duplicates the node
table but keeps the payload dicts by REFERENCE -- so both trees pointed at one
dict per node.

That is silent corruption in both directions, because the internal writers
(``RhythmTree._evaluate`` above all) mutate payload dicts IN PLACE rather than
replacing them: recomputing one tree rewrites the other tree's cached
``metric_duration`` / ``metric_onset``. The channel is any verb whose recompute
changes a value on a SURVIVING node -- today ``prune`` and ``remove_subtree``.

``structural_clone`` already got this right and says why in its docstring;
``__deepcopy__`` just skipped the freshening loop. These tests pin the fix and,
separately, pin the deliberate SHALLOWNESS of that freshening: fresh dict per
node, values shared.
"""

from fractions import Fraction

import copy

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.dynatos import Envelope
from klotho.thetos.parameters.parameter_tree import ParameterTree as PT
from klotho.topos.graphs.trees import Tree


def _bar():
    """A 1/1 bar of four sixteenths, nested two deep."""
    return RT(span=1, meas='1/1', subdivisions=((2, (1, 1)), (2, (1, 1))))


class TestPayloadsAreNotShared:
    """The identity assertion behind every symptom below.

    These reach ``_rx`` on purpose: ``tree.nodes[n]`` hands back a fresh
    ``MappingProxyType`` per call, so it can never show the aliasing.
    """

    def test_every_node_gets_its_own_payload_dict(self):
        a = _bar()
        b = a.copy()

        for n in a.nodes:
            assert a._rx.get_node_data(n) is not b._rx.get_node_data(n), (
                f"node {n} payload is shared between the copy and the original")

    def test_plain_tree_copy_also_freshens_payloads(self):
        a = Tree('root', ((1, (2, 3)), 4))
        b = a.copy()

        for n in a.nodes:
            assert a._rx.get_node_data(n) is not b._rx.get_node_data(n)

    def test_explicit_deepcopy_freshens_payloads(self):
        a = _bar()
        b = copy.deepcopy(a)

        for n in a.nodes:
            assert a._rx.get_node_data(n) is not b._rx.get_node_data(n)


class TestMutatingOneTwinLeavesTheOtherIntact:
    """The reported symptom: a 1/1 bar whose events sum to 5/4."""

    def test_pruning_the_copy_leaves_the_original_intact(self):
        a = _bar()
        before = a.durations
        b = a.copy()

        b.prune(list(b.leaf_nodes)[0])

        assert a.durations == before
        assert sum(a.durations) == Fraction(1, 1)

    def test_pruning_the_original_leaves_a_kept_copy_intact(self):
        a = _bar()
        b = a.copy()
        before = b.durations

        a.prune(list(a.leaf_nodes)[0])

        assert b.durations == before
        assert sum(b.durations) == Fraction(1, 1)

    def test_remove_subtree_on_the_copy_leaves_the_original_intact(self):
        a = _bar()
        before = a.durations
        b = a.copy()

        b.remove_subtree(list(b.nodes)[1])

        assert a.durations == before
        assert sum(a.durations) == Fraction(1, 1)

    def test_onsets_do_not_drift_across_the_copy_boundary(self):
        a = _bar()
        before = a.onsets
        b = a.copy()

        b.prune(list(b.leaf_nodes)[0])

        assert a.onsets == before


class TestFreshDictsShareTheirValues:
    """Deliberate shallowness -- guards against over-correcting to a recursive
    deepcopy, which would clone shared Instrument/Envelope/Bind objects.

    Only ``test_payload_values_stay_shared`` is green before and after the
    payload fix: it pins the choice, not the bug.
    ``test_copy_matches_structural_clone_aliasing`` DOES go red pre-fix --
    ``structural_clone`` already handed out fresh payload dicts and
    ``__deepcopy__`` did not, so the two sides of its ``is`` comparison
    disagreed. A red result there means the aliasing is back, not that the
    shallowness convention changed.
    """

    def test_payload_values_stay_shared(self):
        pt = PT(1, ((1, (1, 1)), 1))
        leaf = list(pt.leaf_nodes)[0]
        env = Envelope([0, 1])
        pt.set_node_data(leaf, amp=env)

        c = pt.copy()

        assert c.nodes[leaf]['amp'] is env

    def test_copy_matches_structural_clone_aliasing(self):
        a = _bar()
        deep = a.copy()
        structural = a.structural_clone()

        for n in a.nodes:
            assert (a._rx.get_node_data(n) is not deep._rx.get_node_data(n)) is (
                a._rx.get_node_data(n) is not structural._rx.get_node_data(n))
