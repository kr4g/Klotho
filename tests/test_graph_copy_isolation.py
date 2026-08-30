"""``GraphCore.copy()`` promises a deep copy, so no payload may be shared.

This is the non-Tree twin of ``tests/test_tree_copy_isolation.py``.
``Tree.__deepcopy__`` was given a payload-freshening loop in ``b5be431``; the
base class it inherits from was left exactly as it was, so every graph that is
NOT a tree -- :class:`~klotho.topos.graphs.graphs.Graph` above all -- still got
a "deep copy" that shared one dict per node with the original.

The mechanism is rustworkx, not Klotho: ``PyGraph.copy()`` duplicates the node
and edge tables but keeps the payloads BY REFERENCE. Writing through a payload
dict therefore reaches both twins at once, in both directions, with nothing
raised.

Two properties are pinned here, and they pull against each other on purpose:

* the dicts are FRESH -- one per node and one per edge, per copy;
* the VALUES inside them stay SHARED -- the freshening is one level deep, and
  a recursive ``deepcopy`` would clone the Instrument / Envelope / Bind objects
  that a copy is supposed to hand back identical.

These tests reach into ``_rx`` deliberately. ``graph.nodes[n]`` hands back a
new ``MappingProxyType`` on every call, so no public accessor can show whether
the dict behind it is shared.
"""

import copy

import pytest

import rustworkx as rx

from klotho.topos.graphs import Graph
from klotho.topos.graphs.trees import Tree


def _graph(directed=False):
    """Three nodes, two attributed edges, one attribute per node."""
    g = Graph(directed=directed)
    a = g.add_node(w=1, tag='a')
    b = g.add_node(w=2, tag='b')
    c = g.add_node(w=3, tag='c')
    g.add_edge(a, b, weight=10)
    g.add_edge(b, c, weight=20)
    return g, (a, b, c)


class TestNodePayloadsAreNotShared:
    """The identity assertion behind every symptom below."""

    def test_copy_gives_every_node_its_own_payload_dict(self):
        g, _ = _graph()
        h = g.copy()

        for n in g.nodes:
            assert g._rx.get_node_data(n) is not h._rx.get_node_data(n), (
                f"node {n} payload is shared between the copy and the original")

    def test_directed_copy_gives_every_node_its_own_payload_dict(self):
        g, _ = _graph(directed=True)
        h = g.copy()

        for n in g.nodes:
            assert g._rx.get_node_data(n) is not h._rx.get_node_data(n)

    def test_explicit_deepcopy_freshens_payloads(self):
        g, _ = _graph()
        h = copy.deepcopy(g)

        for n in g.nodes:
            assert g._rx.get_node_data(n) is not h._rx.get_node_data(n)

    def test_writing_the_original_in_place_does_not_reach_the_copy(self):
        g, (a, _, _) = _graph()
        h = g.copy()

        g._rx[a]['w'] = 999

        assert h.nodes[a]['w'] == 1

    def test_writing_the_copy_in_place_does_not_reach_the_original(self):
        g, (a, _, _) = _graph()
        h = g.copy()

        h._rx[a]['w'] = 999

        assert g.nodes[a]['w'] == 1

    def test_a_key_added_to_one_twin_does_not_appear_on_the_other(self):
        g, (_, b, _) = _graph()
        h = g.copy()

        h._rx[b]['added'] = True

        assert 'added' not in g.nodes[b]


class TestEdgePayloadsAreNotShared:
    """Edges carry dicts too, and ``copy()`` aliased them by the same route.

    ``Tree`` never noticed: its edges are built with no attributes, so the
    shared dict is an empty one nothing writes to. A plain ``Graph`` puts
    real data there.
    """

    def test_copy_gives_every_edge_its_own_payload_dict(self):
        g, (a, b, c) = _graph()
        h = g.copy()

        for u, v in ((a, b), (b, c)):
            assert g._rx.get_edge_data(u, v) is not h._rx.get_edge_data(u, v), (
                f"edge {u}->{v} payload is shared between the copy and the original")

    def test_writing_an_edge_in_place_does_not_reach_the_copy(self):
        g, (a, b, _) = _graph()
        h = g.copy()

        g._rx.get_edge_data(a, b)['weight'] = 999

        assert h._rx.get_edge_data(a, b)['weight'] == 10


class TestWrappingARustworkxGraphAlsoFreshens:
    """``copy_graph=True`` is a copy request, and it took the same aliasing.

    ``copy_graph=False`` is the documented opt-out and must keep sharing.
    """

    def test_from_rustworkx_copy_does_not_alias_the_source_payloads(self):
        src = rx.PyGraph()
        n = src.add_node({'w': 1})

        g = Graph.from_rustworkx(src, copy_graph=True)
        src[n]['w'] = 999

        assert g.nodes[n]['w'] == 1

    def test_from_rustworkx_without_copy_still_shares(self):
        src = rx.PyGraph()
        n = src.add_node({'w': 1})

        g = Graph.from_rustworkx(src, copy_graph=False)
        src[n]['w'] = 999

        assert g.nodes[n]['w'] == 999

    def test_subgraph_does_not_alias_the_parent_payloads(self):
        g, (a, _, _) = _graph(directed=True)

        sub = g.subgraph(a)

        parent_payloads = {id(g._rx.get_node_data(n)) for n in g.nodes}
        for n in sub.nodes:
            assert id(sub._rx.get_node_data(n)) not in parent_payloads, (
                "the subgraph shares a payload dict with the graph it came from")


class TestFreshDictsShareTheirValues:
    """Deliberate shallowness -- guards against over-correcting to a recursive
    deepcopy of the payloads, which would clone the objects a copy is meant to
    hand back identical.

    This one is green before and after the fix: it pins the choice, not the
    bug.
    """

    def test_payload_values_stay_shared(self):
        marker = object()
        g = Graph()
        n = g.add_node(obj=marker)

        assert g.copy().nodes[n]['obj'] is marker


class TestTreeStillFreshens:
    """``Tree.__deepcopy__`` now defers to the base class instead of carrying
    its own copy of the loop. These pin that the delegation kept the behaviour
    ``b5be431`` installed.
    """

    def test_tree_copy_still_gives_every_node_its_own_payload(self):
        a = Tree('root', ((1, (2, 3)), 4))
        b = a.copy()

        for n in a.nodes:
            assert a._rx.get_node_data(n) is not b._rx.get_node_data(n)

    def test_tree_copy_keeps_its_own_class_and_root(self):
        a = Tree('root', ((1, (2, 3)), 4))
        b = a.copy()

        assert type(b) is Tree
        assert b.root == a.root
        assert b.group == a.group
