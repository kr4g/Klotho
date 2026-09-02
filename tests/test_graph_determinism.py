"""Determinism of graph and lattice traversals (charter WL-14 + NEW-06).

Two defect classes, one batch:

* **Arbitrary iteration order.** ``GraphCore.neighbors`` returned rustworkx's
  internal adjacency order, and several traversals iterated raw ``set``\\ s.
  Both are stable within a process but carry no meaning, so a walk's answer
  depended on how the graph happened to be built.
* **Global RNG pollution.** The seeded walks called ``random.seed(seed)``,
  which reseeds the interpreter-wide stream: asking for one reproducible
  walk silently made every later ``random`` call in the caller's program a
  continuation of that seed.
"""

import random

import pytest

from klotho.topos.graphs import Graph
from klotho.topos.graphs.lattices import Lattice
from klotho.topos.graphs.lattices.algorithms import (
    random_walk,
    directed_walk,
    boundary_walk,
)
from klotho.utils.algorithms.graphs import (
    greedy_tsp,
    greedy_random_walk,
    probabilistic_random_walk,
    deterministic_greedy_walk,
    prim_order_traversal,
    greedy_nearest_unvisited,
    weighted_dfs_traversal,
)


def _diamond():
    """A graph whose raw adjacency order is not ascending."""
    G = Graph()
    for _ in range(4):
        G.add_node()
    G.add_edge(0, 1, weight=100.0)
    G.add_edge(0, 2, weight=1.0)
    G.add_edge(0, 3, weight=1.0)
    G.add_edge(1, 2, weight=1.0)
    G.add_edge(2, 3, weight=1.0)
    return G


class TestNeighborOrder:
    def test_neighbors_are_sorted(self):
        """rustworkx hands back ``[2, 1, 3]`` for node 0 of this construction,
        so the assertion is not a tautology; the pre-fix break test is the
        permanent record of that (API-2 handoff)."""
        G = _diamond()
        for node in G.nodes:
            assert G.neighbors(node) == sorted(G.neighbors(node))

    def test_neighbors_mirror_successors(self):
        """``successors`` has sorted since it grew its sorted-order contract
        in ``klotho/topos/graphs/core.py`` :: ``successors()``; ``neighbors``
        now agrees.

        AUD-135: this said ``core.py:229``, which is not that function and
        has not been for some time -- ``successors`` is nowhere near line
        229. Cite the function, never the line: line numbers in this repo
        demonstrably drift, and a citation pointing at unrelated code reads
        as a fabricated one.
        """
        G = Graph.directed()
        for _ in range(4):
            G.add_node()
        for u, v in [(0, 3), (0, 1), (0, 2)]:
            G.add_edge(u, v, weight=1.0)
        assert list(G.successors(0)) == list(G.neighbors(0))

    def test_lattice_neighbors_are_stable(self):
        lat = Lattice(dimensionality=2, resolution=3)
        coord = lat.neighbors((0, 0))
        assert coord == lat.neighbors((0, 0))
        assert coord == sorted(coord)


class TestTraversalsAreOrderIndependent:
    """No traversal may take its answer from ``set`` iteration order."""

    @pytest.mark.parametrize("fn", [
        prim_order_traversal,
        greedy_nearest_unvisited,
        weighted_dfs_traversal,
        deterministic_greedy_walk,
    ])
    def test_repeatable_across_calls(self, fn):
        G = _diamond()
        first = fn(G, 0)
        for _ in range(5):
            assert fn(G, 0) == first

    def test_deterministic_greedy_walk_breaks_ties_by_lowest_index(self):
        """Every edge here costs the same, so only the tie-break decides."""
        G = Graph()
        for _ in range(4):
            G.add_node()
        for u, v in [(0, 3), (0, 2), (0, 1)]:
            G.add_edge(u, v, weight=1.0)
        assert deterministic_greedy_walk(G, 0, steps=1) == [0, 1]

    def test_greedy_tsp_jump_target_is_the_lowest_unvisited(self):
        """The disconnected branch used to be ``set.pop()``."""
        G = Graph()
        for _ in range(4):
            G.add_node()
        G.add_edge(0, 1, weight=1.0)
        tour = greedy_tsp(G, source=0)
        assert tour == [0, 1, 2, 3]


class TestSeededWalksDoNotTouchTheGlobalStream:
    """A seed must scope to the call, not to the interpreter."""

    @pytest.mark.parametrize("call", [
        lambda lat: random_walk(lat, (0, 0), 8, seed=42),
        lambda lat: directed_walk(lat, (0, 0), [1.0, 2.0, 1.0, 2.0], 8, seed=42),
        lambda lat: boundary_walk(lat, (0, 0), 8, seed=42),
    ])
    def test_lattice_walks_leave_global_random_alone(self, call):
        lat = Lattice(dimensionality=2, resolution=3)
        random.seed(1234)
        expected = [random.random() for _ in range(3)]

        random.seed(1234)
        call(lat)
        assert [random.random() for _ in range(3)] == expected

    @pytest.mark.parametrize("fn", [greedy_random_walk, probabilistic_random_walk])
    def test_graph_walks_leave_global_random_alone(self, fn):
        G = _diamond()
        random.seed(1234)
        expected = [random.random() for _ in range(3)]

        random.seed(1234)
        fn(G, 0, steps=5, seed=42)
        assert [random.random() for _ in range(3)] == expected

    def test_find_generator_basis_leaves_global_random_alone(self):
        from klotho.tonos.systems.tone_lattices.basis import find_generator_basis

        random.seed(1234)
        expected = [random.random() for _ in range(3)]

        random.seed(1234)
        find_generator_basis([2, 3, 5], mode="random", random_samples=50, seed=7,
                             candidate_cap=12, top_k=3)
        assert [random.random() for _ in range(3)] == expected


class TestSeedsReproduce:
    @pytest.mark.parametrize("call", [
        lambda lat, s: random_walk(lat, (0, 0), 8, seed=s),
        lambda lat, s: directed_walk(lat, (0, 0), [1.0, 2.0, 1.0, 2.0], 8, seed=s),
        lambda lat, s: boundary_walk(lat, (0, 0), 8, seed=s),
    ])
    def test_lattice_walk_is_reproducible(self, call):
        lat = Lattice(dimensionality=2, resolution=3)
        assert call(lat, 5) == call(lat, 5)

    @pytest.mark.parametrize("fn", [greedy_random_walk, probabilistic_random_walk])
    def test_graph_walk_is_reproducible(self, fn):
        G = _diamond()
        assert fn(G, 0, steps=6, seed=5) == fn(G, 0, steps=6, seed=5)

    @pytest.mark.parametrize("fn", [greedy_random_walk, probabilistic_random_walk])
    def test_a_random_random_instance_is_accepted(self, fn):
        G = _diamond()
        a = fn(G, 0, steps=6, seed=random.Random(11))
        b = fn(G, 0, steps=6, seed=random.Random(11))
        assert a == b
