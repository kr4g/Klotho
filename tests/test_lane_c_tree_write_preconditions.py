"""Preconditions on the topos tree mutators that used to corrupt in silence.

Four verbs on :class:`~klotho.topos.graphs.trees.Tree` accepted a request they
could not honour and answered it with a plausible-looking tree instead of a
refusal:

* ``move_subtree(node, <descendant of node>)`` built a real cycle -- the graph
  stopped being a DAG and every traversal read silently returned a truncated
  answer.
* ``replace_node_data``/``update_node_data``/``set_node_data`` with an empty
  or non-mapping payload erased or mis-scoped the write, silently changing a
  leaf's ``metric_duration``.
* ``prune`` on a node that is not in the tree reported success while
  ``remove_subtree`` raised for the identical argument.
* ``add_subtree`` with a donor carrying parameter fields dropped the donor's
  registries and instruments and buried its overrides.

Every test here pins the raise, not the happy path -- but each guard also
carries a companion test proving valid input is untouched, because a guard
that narrows working behaviour is a worse bug than the one it fixes.
"""

import pytest
import rustworkx as rx

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.parameters.parameter_tree import ParameterTree
from klotho.topos.graphs import Graph
from klotho.topos.graphs.trees import Tree


class TestMoveSubtreeAcyclicity:
    """TREE-5 -- moving a node under its own descendant made a cyclic graph."""

    def test_move_into_own_child_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        child = list(rt.successors(1))[0]
        with pytest.raises(ValueError, match='descendant'):
            rt.move_subtree(1, child)

    def test_move_into_own_child_leaves_the_tree_intact(self):
        """The refusal must happen before the first edge write."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        child = list(rt.successors(1))[0]
        before = rt.durations
        with pytest.raises(ValueError):
            rt.move_subtree(1, child)
        assert rx.is_directed_acyclic_graph(rt._rx)
        assert rt.durations == before
        assert len(rt.durations) == 4

    def test_move_into_a_deeper_descendant_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, ((1, (1, 1)), 1)), 1))
        deep = rt.descendants(1)[-1]
        with pytest.raises(ValueError, match='descendant'):
            rt.move_subtree(1, deep)

    def test_move_into_itself_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        with pytest.raises(ValueError, match='the node itself'):
            rt.move_subtree(1, 1)
        assert rx.is_directed_acyclic_graph(rt._rx)

    def test_move_to_an_absent_parent_raises_the_membership_message(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        with pytest.raises(ValueError, match='Node 9999 not found in tree'):
            rt.move_subtree(1, 9999)

    def test_moving_an_absent_node_raises_the_membership_message(self):
        """Honest note: this is DEFENCE IN DEPTH, not a proven line.

        Deleting ``move_subtree``'s ``node not in self`` check leaves this
        test green (measured), because ``self.descendants(node)`` in the
        acyclicity clause raises the same message for an absent node. The
        explicit check is kept anyway so the precondition is stated rather
        than inherited from a helper's side effect -- but the test pins the
        CONTRACT, and nothing here would notice if the line went away.
        """
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        with pytest.raises(ValueError, match='Node 9999 not found in tree'):
            rt.move_subtree(9999, rt.root)

    def test_a_legal_sideways_move_still_works(self):
        """A guard that changed behaviour for valid input would be worse than
        the defect. Node 4 moves under node 1, which is not its ancestor."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        assert rt.parent(4) == rt.root
        rt.move_subtree(4, 1)
        assert rt.parent(4) == 1
        assert rx.is_directed_acyclic_graph(rt._rx)
        assert sum(rt.durations) == 1

    def test_a_legal_move_toward_the_root_still_works(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=((1, (1, 1)), 1, 1))
        assert rt.parent(2) == 1
        rt.move_subtree(2, rt.root)
        assert rt.parent(2) == rt.root
        assert rx.is_directed_acyclic_graph(rt._rx)


class TestNodeDataWritePayload:
    """S0 -- the payload was coerced to ``{}`` and the write mis-scoped.

    NOTE FOR A LATER READER: this is a SANDBOX OVER AN UNFIXED ROOT CAUSE.
    See the comment on ``Tree._validate_node_data_payload`` -- the underlying
    ``data_scope``-returns-``None`` confusion in ``_resolve_write_scope`` is
    still open. These tests pin the door, not the room behind it.
    """

    def test_replace_with_empty_dict_raises_and_does_not_write(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = dict(rt[leaf])
        with pytest.raises(ValueError, match='empty attribute dict'):
            rt.replace_node_data(leaf, {})
        assert dict(rt[leaf]) == before
        assert 'metric_duration' in rt[leaf]

    def test_replace_with_empty_dict_leaves_durations_readable(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = rt.durations
        with pytest.raises(ValueError):
            rt.replace_node_data(leaf, {})
        assert rt.durations == before
        assert sum(rt.durations) == 1

    def test_update_with_a_list_of_pairs_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        with pytest.raises(TypeError, match='mapping of node attributes'):
            rt.update_node_data(leaf, [('proportion', 3)])

    def test_update_with_a_list_of_pairs_does_not_change_durations(self):
        """The corrupting half: it used to triple the leaf's duration."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = rt.durations
        with pytest.raises(TypeError):
            rt.update_node_data(leaf, [('proportion', 3)])
        assert rt.durations == before
        assert rt[leaf]['metric_duration'] == before[0]

    def test_update_with_an_empty_dict_raises(self):
        """An empty write is not a no-op on this path -- it re-scopes the
        recompute onto the leaf and rewrites its metric_duration."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = rt.durations
        with pytest.raises(ValueError, match='empty attribute dict'):
            rt.update_node_data(leaf, {})
        assert rt.durations == before

    def test_set_node_data_with_no_keywords_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = rt.durations
        with pytest.raises(ValueError, match='empty attribute dict'):
            rt.set_node_data(leaf)
        assert rt.durations == before

    def test_set_node_attributes_with_an_empty_dict_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = rt.durations
        with pytest.raises(ValueError, match='empty attribute dict'):
            rt.set_node_attributes(leaf, {})
        assert rt.durations == before

    def test_a_node_view_is_a_valid_payload(self):
        """``tree[other]`` is a ``mappingproxy``, not a ``dict``. It used to
        fail ``isinstance(attrs, dict)`` and be coerced to ``{}``; a mapping
        is a mapping."""
        t = Tree(1, (1, 1))
        a, b = t.leaf_nodes[0], t.leaf_nodes[1]
        t.update_node_data(b, {'label': 'target'})
        t.replace_node_data(a, t[b])
        assert t[a]['label'] == 'target'

    def test_a_node_view_on_a_rhythm_tree_is_refused_loudly_not_silently(self):
        """A RhythmTree node view carries derived keys, so the rhythm layer
        refuses it -- which is the point. It used to be discarded in silence
        and take the target node's whole payload with it."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        a, b = rt.leaf_nodes[0], rt.leaf_nodes[1]
        before = dict(rt[a])
        with pytest.raises(ValueError, match='Illegal RhythmTree node attribute'):
            rt.replace_node_data(a, rt[b])
        assert dict(rt[a]) == before
        assert sum(rt.durations) == 1

    def test_a_valid_dict_write_is_unaffected(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        rt.update_node_data(leaf, {'proportion': 5})
        assert rt[leaf]['proportion'] == 5
        assert sum(rt.durations) == 1

    def test_the_established_illegal_key_contract_is_unchanged(self):
        """``replace_node_data(leaf, {'foo': 1})`` already refused with the
        node intact. The new guards restore that contract, not replace it."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(3, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        before = dict(rt[leaf])
        with pytest.raises(ValueError, match='Illegal RhythmTree node attribute'):
            rt.replace_node_data(leaf, {'foo': 1})
        assert dict(rt[leaf]) == before

    def test_a_plain_tree_still_accepts_a_dict_write(self):
        t = Tree(1, (1, 1))
        leaf = t.leaf_nodes[0]
        t.update_node_data(leaf, {'label': 'x'})
        assert t[leaf]['label'] == 'x'


class TestGraphNodeDataPayload:
    """The same coercion, mirrored on the plain ``Graph`` write path.

    ``Graph`` has no layer pipeline, so its writers reach
    ``GraphCore._write_node_data`` directly and used to hit the identical
    ``isinstance(attrs, dict) else {}`` line there.
    """

    def test_update_with_a_list_of_pairs_raises_instead_of_vanishing(self):
        g = Graph()
        node = g.add_node(label='A', value=1)
        with pytest.raises(TypeError, match='mapping of attributes'):
            g.update_node_data(node, [('value', 99)])

    def test_the_discarded_write_used_to_leave_no_trace(self):
        """Regression note: this call returned normally and changed nothing,
        so a caller had no way to learn the write had not happened."""
        g = Graph()
        node = g.add_node(label='A', value=1)
        with pytest.raises(TypeError):
            g.update_node_data(node, [('value', 99)])
        assert g[node]['value'] == 1

    def test_replace_with_a_non_mapping_raises(self):
        g = Graph()
        node = g.add_node(label='A')
        with pytest.raises(TypeError, match='mapping of attributes'):
            g.replace_node_data(node, ['label', 'B'])
        assert g[node]['label'] == 'A'

    def test_valid_graph_writes_are_unaffected(self):
        g = Graph()
        node = g.add_node(label='A', value=1)
        g.update_node_data(node, {'value': 2, 'extra': 'ok'})
        assert g[node]['value'] == 2
        g.replace_node_data(node, {'label': 'B'})
        assert set(g[node].keys()) == {'label'}

    def test_an_empty_dict_is_still_legal_on_a_plain_graph(self):
        """No empty-payload guard here: ``Graph`` has no derived data to
        mis-scope, and ``clear_node_attributes`` legitimately writes ``{}``."""
        g = Graph()
        node = g.add_node(label='A')
        g.replace_node_data(node, {})
        assert dict(g[node]) == {}
        g.clear_node_attributes()
        assert dict(g[node]) == {}


class TestPruneMembership:
    """LAYER-9 -- ``prune`` and ``remove_subtree`` gave different answers."""

    def test_prune_absent_node_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='Node 9999 not found in tree'):
            rt.prune(9999)

    def test_prune_and_remove_subtree_agree(self):
        """The programmer lens of R12: two verbs, one argument, one answer."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError) as prune_err:
            rt.prune(9999)
        with pytest.raises(ValueError) as remove_err:
            rt.remove_subtree(9999)
        assert str(prune_err.value) == str(remove_err.value)

    def test_prune_absent_node_mutates_nothing(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        before = rt.durations
        with pytest.raises(ValueError):
            rt.prune(9999)
        assert rt.durations == before
        assert len(list(rt.nodes)) == 3

    def test_prune_on_a_compositional_unit_also_refuses(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                               beat='1/4', bpm=60)
        with pytest.raises(ValueError, match='Node 9999 not found in tree'):
            uc.prune(9999)

    def test_pruning_a_real_node_still_works(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
        rt.prune(2)
        assert sum(rt.durations) == 1
        assert len(rt.durations) == 4

    def test_pruning_the_root_still_raises_its_own_message(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='Cannot prune the root node'):
            rt.prune(rt.root)


class TestAddSubtreeDonorState:
    """S2 -- ``add_subtree`` copies node payloads verbatim and nothing else."""

    def test_donor_with_pfields_is_refused(self):
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1,),
                                  beat='1/4', bpm=60)
        donor.set_pfields(list(donor._rt.leaf_nodes)[0], cutoff=1200.0)
        with pytest.raises(ValueError, match='graft_subtree'):
            host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor._rt)

    def test_refusal_happens_before_any_node_is_copied(self):
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1,),
                                  beat='1/4', bpm=60)
        donor.set_pfields(list(donor._rt.leaf_nodes)[0], cutoff=1200.0)
        before = list(host._rt.nodes)
        with pytest.raises(ValueError):
            host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor._rt)
        assert list(host._rt.nodes) == before
        assert host.pfields == []

    def test_donor_with_an_instrument_is_refused(self):
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1,),
                                  beat='1/4', bpm=60)
        donor.set_instrument(list(donor._rt.leaf_nodes)[0], 'kl_saw')
        with pytest.raises(ValueError, match='instrument bindings'):
            host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor._rt)

    def test_a_donor_whose_keys_the_host_already_knows_is_accepted(self):
        """The guard is scoped to what is actually LOST. Every
        CompositionalUnit registers ``group``, and per-node values ride along
        in the payloads this verb does copy -- so a donor whose only registry
        entries the host already has must not be refused."""
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1, 1),
                                  beat='1/4', bpm=60)
        assert donor._rt.mfields == host._rt.mfields
        assert donor._rt.pfields == []
        before = len(list(host._rt.nodes))
        host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor._rt)
        assert len(list(host._rt.nodes)) > before

    def test_a_donor_key_the_host_already_registered_survives_the_copy(self):
        """The reason the above is safe, pinned: the VALUE is in the node
        payload, which add_subtree copies."""
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1,),
                                  beat='1/4', bpm=60)
        host.set_pfields(list(host._rt.leaf_nodes)[0], cutoff=500.0)
        donor.set_pfields(list(donor._rt.leaf_nodes)[0], cutoff=1200.0)
        host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor._rt)
        grafted_leaf = list(host._rt.leaf_nodes)[-1]
        assert host._rt.get_pfield(grafted_leaf, 'cutoff') == 1200.0
        assert 'cutoff' in host.pfields

    def test_an_unparameterized_donor_is_still_accepted(self):
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        before = len(list(host._rt.nodes))
        host._rt.add_subtree(list(host._rt.leaf_nodes)[-1], donor)
        assert len(list(host._rt.nodes)) > before

    def test_a_plain_tree_donor_is_still_accepted(self):
        t1 = Tree(1, (1, 1))
        t2 = Tree(1, (1, 1))
        before = len(list(t1.nodes))
        t1.add_subtree(t1.root, t2)
        assert len(list(t1.nodes)) > before

    def test_an_empty_parameter_tree_donor_is_still_accepted(self):
        """A ``ParameterTree`` with nothing registered has nothing to lose."""
        host = Tree(1, (1, 1))
        donor = ParameterTree(1, (1, 1))
        assert donor.pfields == []
        before = len(list(host.nodes))
        host.add_subtree(host.root, donor)
        assert len(list(host.nodes)) > before

    def test_graft_subtree_is_the_verb_that_carries(self):
        """Regression pin on the alternative the refusal points at."""
        host = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                                 beat='1/4', bpm=60)
        donor = CompositionalUnit(tempus='4/4', prolatio=(1, 1),
                                  beat='1/4', bpm=60)
        donor.set_pfields(list(donor._rt.leaf_nodes)[0], cutoff=1200.0)
        target = list(host._rt.leaf_nodes)[-1]
        host._rt.graft_subtree(target, donor._rt, mode='replace')
        assert 'cutoff' in host.pfields
