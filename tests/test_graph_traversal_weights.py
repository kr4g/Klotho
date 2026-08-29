"""The eight weighted graph traversals (charter WL-43, coverage NEW-07).

All eight read edge weights through ``G[u][v].get(weight, 1.0)``. ``G[u]`` is
the *node data* mapping, not an adjacency row, so ``[v]`` raised ``KeyError``
on every graph ever built, the swallowing ``except`` handed back 1.0, and all
eight silently degraded to "visit in whatever order you meet them". Nothing
caught it because the module had no tests at all since the 10.0 rustworkx
migration.

The shape of every weight test below: node 0's *lowest-numbered* neighbour is
also its *most expensive* one, so a weight-blind traversal and a weight-aware
one disagree on the very first step.
"""

import pytest

from klotho.topos.graphs import Graph
from klotho.utils.algorithms import graphs as graphs_mod
from klotho.utils.algorithms.graphs import (
    greedy_tsp,
    minimum_cost_path,
    greedy_random_walk,
    probabilistic_random_walk,
    deterministic_greedy_walk,
    prim_order_traversal,
    greedy_nearest_unvisited,
    dijkstra_order_traversal,
    weighted_dfs_traversal,
)

#: Everything that reads an edge weight. ``minimum_cost_path`` dispatches.
TRAVERSALS = [
    greedy_tsp,
    greedy_random_walk,
    probabilistic_random_walk,
    deterministic_greedy_walk,
    prim_order_traversal,
    greedy_nearest_unvisited,
    dijkstra_order_traversal,
    weighted_dfs_traversal,
]


def _trap():
    """0's cheap way out is node 2; node 1 is adjacent but costs 100."""
    G = Graph()
    for _ in range(4):
        G.add_node()
    G.add_edge(0, 1, weight=100.0)
    G.add_edge(0, 2, weight=1.0)
    G.add_edge(0, 3, weight=1.0)
    G.add_edge(1, 2, weight=1.0)
    G.add_edge(2, 3, weight=1.0)
    return G


def _call(fn, G, **kw):
    """``greedy_tsp`` names its start ``source=``; the walks take it positionally."""
    if fn is greedy_tsp:
        return fn(G, source=0, **kw)
    return fn(G, 0, **kw)


class TestWeightsAreRead:
    @pytest.mark.parametrize("fn", TRAVERSALS, ids=lambda f: f.__name__)
    def test_the_expensive_neighbour_is_not_visited_first(self, fn):
        G = _trap()
        kw = {'seed': 0} if fn in (greedy_random_walk, probabilistic_random_walk) else {}
        path = _call(fn, G, **kw)
        assert path[1] != 1, f"{fn.__name__} took the 100-cost edge over a 1-cost one"

    @pytest.mark.parametrize("fn", [f for f in TRAVERSALS
                                    if f not in (greedy_random_walk,
                                                 probabilistic_random_walk)],
                             ids=lambda f: f.__name__)
    def test_a_custom_weight_key_is_honoured(self, fn):
        """Under 'cost' the cheap spoke wins; under the absent 'weight' key
        every edge is default-priced and plain node order returns."""
        G = Graph()
        for _ in range(3):
            G.add_node()
        G.add_edge(0, 1, cost=100.0)
        G.add_edge(0, 2, cost=1.0)
        assert _call(fn, G, weight='cost')[1] == 2
        assert _call(fn, G, weight='weight')[1] == 1

    @pytest.mark.parametrize("fn", [greedy_random_walk, probabilistic_random_walk],
                             ids=lambda f: f.__name__)
    def test_a_custom_weight_key_is_honoured_by_the_random_walks(self, fn):
        """These two draw, so the claim is distributional: under 'cost' the
        cheap spoke dominates; under the absent 'weight' key it does not."""
        G = Graph()
        for _ in range(3):
            G.add_node()
        G.add_edge(0, 1, cost=100.0)
        G.add_edge(0, 2, cost=1.0)
        by_cost = [fn(G, 0, steps=1, weight='cost', seed=s)[1] for s in range(200)]
        flat = [fn(G, 0, steps=1, weight='weight', seed=s)[1] for s in range(200)]
        assert by_cost.count(2) > by_cost.count(1)
        assert flat.count(1) > by_cost.count(1)

    def test_greedy_tsp_orders_the_whole_tour_by_cost(self):
        assert greedy_tsp(_trap(), source=0) == [0, 2, 1, 3]

    def test_dijkstra_visits_in_distance_order(self):
        """3 is two cheap hops away; 1 is one 100-cost hop away."""
        assert dijkstra_order_traversal(_trap(), 0) == [0, 2, 3, 1]

    def test_prim_follows_the_minimum_spanning_tree(self):
        assert prim_order_traversal(_trap(), 0) == [0, 2, 3, 1]

    def test_weighted_dfs_descends_the_cheap_branch(self):
        assert weighted_dfs_traversal(_trap(), 0) == [0, 2, 1, 3]

    def test_greedy_nearest_takes_the_cheap_neighbour(self):
        assert greedy_nearest_unvisited(_trap(), 0) == [0, 2, 1, 3]

    def test_an_edge_without_the_key_costs_the_default(self):
        G = Graph()
        for _ in range(3):
            G.add_node()
        G.add_edge(0, 1)
        G.add_edge(0, 2, weight=5.0)
        assert deterministic_greedy_walk(G, 0, steps=1) == [0, 1]

    def test_probabilistic_walk_prefers_cheap_edges(self):
        """Not a determinism claim -- a distribution claim, over 200 draws."""
        G = _trap()
        firsts = [probabilistic_random_walk(G, 0, steps=1, seed=s)[1]
                  for s in range(200)]
        assert firsts.count(1) < firsts.count(2)


class TestTraversalContracts:
    """The coverage this module never had (NEW-07)."""

    @pytest.mark.parametrize("fn", TRAVERSALS, ids=lambda f: f.__name__)
    def test_an_absent_source_raises(self, fn):
        G = _trap()
        with pytest.raises(ValueError, match="not in graph"):
            fn(G, 99) if fn is not greedy_tsp else fn(G, source=99)

    @pytest.mark.parametrize("fn", TRAVERSALS, ids=lambda f: f.__name__)
    def test_the_path_starts_at_the_source(self, fn):
        assert _call(fn, _trap())[0] == 0

    @pytest.mark.parametrize("fn", TRAVERSALS, ids=lambda f: f.__name__)
    def test_only_real_nodes_are_returned(self, fn):
        G = _trap()
        assert set(_call(fn, G)) <= set(G.nodes)

    @pytest.mark.parametrize("fn", [
        prim_order_traversal,
        greedy_nearest_unvisited,
        dijkstra_order_traversal,
        weighted_dfs_traversal,
    ], ids=lambda f: f.__name__)
    def test_the_covering_traversals_reach_every_node(self, fn):
        G = _trap()
        assert sorted(fn(G, 0)) == sorted(G.nodes)

    @pytest.mark.parametrize("fn", [
        prim_order_traversal,
        dijkstra_order_traversal,
        weighted_dfs_traversal,
    ], ids=lambda f: f.__name__)
    def test_no_node_is_visited_twice(self, fn):
        path = fn(_trap(), 0)
        assert len(path) == len(set(path))

    @pytest.mark.parametrize("fn", [
        greedy_random_walk,
        probabilistic_random_walk,
        deterministic_greedy_walk,
    ], ids=lambda f: f.__name__)
    def test_an_isolated_source_goes_nowhere(self, fn):
        G = Graph()
        G.add_node()
        G.add_node()
        assert fn(G, 0, steps=5) == [0]

    @pytest.mark.parametrize("fn", [
        greedy_random_walk,
        probabilistic_random_walk,
        deterministic_greedy_walk,
    ], ids=lambda f: f.__name__)
    def test_steps_bounds_the_path(self, fn):
        assert len(fn(_trap(), 0, steps=3)) <= 4

    @pytest.mark.parametrize("fn", [greedy_random_walk, deterministic_greedy_walk],
                             ids=lambda f: f.__name__)
    def test_a_target_stops_the_walk(self, fn):
        assert fn(_trap(), 0, steps=10, target=2)[-1] == 2

    def test_weighted_dfs_sweeps_a_disconnected_component(self):
        G = Graph()
        for _ in range(4):
            G.add_node()
        G.add_edge(0, 1, weight=1.0)
        G.add_edge(2, 3, weight=1.0)
        assert sorted(weighted_dfs_traversal(G, 0)) == [0, 1, 2, 3]

    def test_greedy_tsp_on_an_empty_graph(self):
        assert greedy_tsp(Graph()) == []

    def test_greedy_tsp_defaults_its_source(self):
        assert greedy_tsp(_trap())[0] == 0


class TestMinimumCostPath:
    def test_it_defaults_to_greedy_tsp(self):
        G = _trap()
        assert minimum_cost_path(G, source=0) == greedy_tsp(G, source=0)

    def test_it_forwards_the_weight_key(self):
        G = Graph()
        for _ in range(3):
            G.add_node()
        G.add_edge(0, 1, cost=100.0)
        G.add_edge(0, 2, cost=1.0)
        assert minimum_cost_path(G, source=0, weight='cost') == [0, 2, 1]

    def test_it_delegates_to_a_supplied_traversal(self):
        G = _trap()
        assert minimum_cost_path(G, traversal_func=dijkstra_order_traversal,
                                 source=0) == [0, 2, 3, 1]


def test_every_public_traversal_is_exported():
    """``greedy_tsp`` was the documented default of ``minimum_cost_path`` and
    was still missing from ``__all__`` (charter WL-43)."""
    for fn in TRAVERSALS + [minimum_cost_path]:
        assert fn.__name__ in graphs_mod.__all__
