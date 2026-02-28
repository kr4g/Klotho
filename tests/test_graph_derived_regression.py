import rustworkx as rx
from functools import reduce
from operator import mul
from fractions import Fraction
import warnings
import pytest

from klotho.topos.graphs import Graph, Lattice, Tree
from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice, ToneLatticeLookupWarning
from klotho.thetos.parameters.parameter_fields.parameter_field import ParameterField
from klotho.utils.algorithms.factors import (
    ratio_to_coordinate,
    ratios_to_coordinates,
)


def test_tree_initialization_still_builds_directed_structure():
    tree = Tree("root", ("left", "right"))

    assert tree.is_directed() is True
    assert tree.root == 0
    assert tree[tree.root]["label"] == "root"
    assert tuple(tree.successors(tree.root)) == (1, 2)


def test_tree_from_graph_accepts_rustworkx_input():
    graph = rx.PyDiGraph()
    root = graph.add_node({"label": "R"})
    child_a = graph.add_node({"label": "A"})
    child_b = graph.add_node({"label": "B"})
    graph.add_edge(root, child_a, {})
    graph.add_edge(root, child_b, {})

    tree = Tree._from_graph(graph, node_attr="label")

    assert isinstance(tree, Tree)
    assert tree[tree.root]["label"] == "R"
    child_labels = {tree[n]["label"] for n in tree.successors(tree.root)}
    assert child_labels == {"A", "B"}


def test_lattice_eager_initialization_still_populates_coordinates():
    lattice = Lattice(dimensionality=2, resolution=2, bipolar=False, periodic=False)

    assert lattice._is_lazy is False
    assert lattice.number_of_nodes() == 9
    assert (0, 0) in lattice
    assert lattice.get_node((0, 0)) is not None


def test_lattice_high_dimensional_initialization_is_eager_and_complete():
    lattice = Lattice(dimensionality=4, resolution=2, bipolar=False, periodic=False)

    assert lattice._is_lazy is False
    assert lattice.number_of_nodes() == 81
    assert lattice.number_of_edges() == 216
    assert (0, 0, 0, 0) in lattice
    assert (2, 2, 2, 2) in lattice
    assert lattice.get_node((0, 0, 0, 0)) is not None


def test_graph_subgraph_reconstruction_still_returns_graph():
    graph = Graph(directed=True)
    n0 = graph.add_node(label="root")
    n1 = graph.add_node(label="child")
    n2 = graph.add_node(label="sibling")
    graph.add_edge(n0, n1)
    graph.add_edge(n0, n2)

    subgraph = graph.subgraph(n0)

    assert isinstance(subgraph, Graph)
    assert subgraph.number_of_nodes() == 3
    assert subgraph.number_of_edges() == 2


def _prod(values):
    return reduce(mul, values, 1)


def _expected_edges(dims, periodic):
    lengths = [len(d) for d in dims]
    total = 0
    for i, axis_len in enumerate(lengths):
        others = _prod(lengths[:i] + lengths[i + 1 :])
        if periodic:
            total += axis_len * others
        else:
            total += (axis_len - 1) * others
    return total


def _coord_map(graph):
    mapping = {}
    for node_id in graph.nodes:
        coord = graph[node_id]["coord"]
        mapping[coord] = node_id
    return mapping


def test_graph_grid_graph_nd_counts_and_coordinates_non_periodic():
    dims = [range(-2, 3), range(0, 4), range(10, 13)]
    graph = Graph.grid_graph(dims, periodic=False)

    expected_nodes = _prod(len(d) for d in dims)
    expected_edges = _expected_edges(dims, periodic=False)

    assert graph.number_of_nodes() == expected_nodes
    assert graph.number_of_edges() == expected_edges

    coords = [graph[node]["coord"] for node in graph.nodes]
    assert len(coords) == expected_nodes
    assert len(set(coords)) == expected_nodes

    expected_coords = {
        (x, y, z) for x in dims[0] for y in dims[1] for z in dims[2]
    }
    assert set(coords) == expected_coords


def test_graph_grid_graph_nd_periodic_wrap_edges_exist():
    dims = [range(-1, 2), range(0, 4), range(3, 6)]
    graph = Graph.grid_graph(dims, periodic=True)
    coord_to_node = _coord_map(graph)

    anchor = (dims[0][-1], dims[1][1], dims[2][1])
    wrapped = (dims[0][0], dims[1][1], dims[2][1])
    assert graph.has_edge(coord_to_node[anchor], coord_to_node[wrapped])

    anchor = (dims[0][1], dims[1][-1], dims[2][1])
    wrapped = (dims[0][1], dims[1][0], dims[2][1])
    assert graph.has_edge(coord_to_node[anchor], coord_to_node[wrapped])

    anchor = (dims[0][1], dims[1][1], dims[2][-1])
    wrapped = (dims[0][1], dims[1][1], dims[2][0])
    assert graph.has_edge(coord_to_node[anchor], coord_to_node[wrapped])


def test_graph_grid_graph_nd_adjacency_matches_axis_steps():
    dims = [range(0, 4), range(0, 3), range(0, 3)]
    graph = Graph.grid_graph(dims, periodic=False)
    coord_to_node = _coord_map(graph)

    u = (1, 1, 1)
    v = (2, 1, 1)
    w = (2, 2, 1)
    x = (3, 2, 2)

    assert graph.has_edge(coord_to_node[u], coord_to_node[v])
    assert graph.has_edge(coord_to_node[v], coord_to_node[w])
    assert not graph.has_edge(coord_to_node[u], coord_to_node[w])
    assert not graph.has_edge(coord_to_node[u], coord_to_node[x])


def test_tone_lattice_ratios_are_cached_on_access():
    lattice = ToneLattice(dimensionality=3, resolution=2, bipolar=True)
    coord = (1, -1, 0)
    node_id = lattice.get_node(coord)
    node_data_before = lattice._graph.get_node_data(node_id)

    assert 'ratio' not in node_data_before
    ratio = lattice.get_ratio(coord)
    assert ratio == lattice.get_ratio(coord)
    assert lattice[coord]['ratio'] == ratio


def test_tone_lattice_bipolar_equave_window_is_open():
    lattice = ToneLattice(dimensionality=1, resolution=1, bipolar=True, equave_reduce=True, equave=2)
    assert lattice.get_ratio((1,)) == Fraction(3, 2)
    assert lattice.get_ratio((-1,)) == Fraction(2, 3)
    assert Fraction(1, 2) < lattice.get_ratio((-1,)) < Fraction(2, 1)
    assert Fraction(1, 2) < lattice.get_ratio((1,)) < Fraction(2, 1)


def test_tone_lattice_unipolar_equave_window_is_half_open():
    lattice = ToneLattice(dimensionality=1, resolution=2, bipolar=False, equave_reduce=True, equave=2)
    assert lattice.get_ratio((0,)) == Fraction(1, 1)
    assert lattice.get_ratio((1,)) == Fraction(3, 2)
    assert lattice.get_ratio((2,)) == Fraction(9, 8)
    assert Fraction(1, 1) <= lattice.get_ratio((2,)) < Fraction(2, 1)


def test_tone_lattice_from_generators_drops_equave_axis_when_present():
    lattice = ToneLattice.from_generators(
        generators=[2, "5/4", "6/5"],
        resolution=1,
        bipolar=True,
        equave_reduce=True,
        equave=2,
    )
    assert lattice.dimensionality == 2
    assert lattice.generators == [Fraction(5, 4), Fraction(6, 5)]
    assert lattice.prime_basis == [2, 3, 5]
    assert lattice.coord_label == "Coordinate"


def test_tone_lattice_from_generators_rejects_float_generators():
    with pytest.raises(TypeError):
        ToneLattice.from_generators(generators=[2.0, "3/2"], resolution=1)


def test_tone_lattice_rejects_float_equave():
    with pytest.raises(TypeError):
        ToneLattice(dimensionality=2, resolution=1, equave=2.0)
    with pytest.raises(TypeError):
        ToneLattice.from_generators(generators=["3/2", "5/4"], resolution=1, equave=2.0)


def test_tone_lattice_prime_basis_tracks_active_generators_only():
    lattice = ToneLattice.from_generators(
        generators=[2, 3],
        resolution=1,
        bipolar=True,
        equave_reduce=True,
        equave=2,
    )
    assert lattice.generators == [Fraction(3, 1)]
    assert lattice.prime_basis == [3]


def test_tone_lattice_get_coordinates_warns_for_unrepresentable_ratio():
    lattice = ToneLattice.from_generators(
        generators=["4/3", "5/4"],
        resolution=1,
        bipolar=True,
        equave_reduce=False,
        equave=2,
    )
    with pytest.warns(ToneLatticeLookupWarning, match="not representable"):
        coord = lattice.get_coordinates_for_ratio("3/2")
    assert coord is None


def test_tone_lattice_get_coordinates_warns_for_out_of_bounds_ratio():
    lattice = ToneLattice(dimensionality=2, resolution=0, bipolar=True, equave_reduce=False, equave=2)
    with pytest.warns(ToneLatticeLookupWarning, match="outside the current lattice bounds/resolution"):
        coord = lattice.get_coordinates_for_ratio("3/2")
    assert coord is None


def test_tone_lattice_lookup_warn_once_controls_warning_spam():
    lattice = ToneLattice.from_generators(
        generators=["4/3", "5/4"],
        resolution=1,
        bipolar=True,
        equave_reduce=False,
        equave=2,
    )
    with pytest.warns(ToneLatticeLookupWarning, match="not representable"):
        assert lattice.get_coordinates_for_ratio("3/2", warn=True, warn_once=True) is None
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ToneLatticeLookupWarning)
        assert lattice.get_coordinates_for_ratio("3/2", warn=True, warn_once=True) is None
    assert len(captured) == 0
    with pytest.warns(ToneLatticeLookupWarning, match="not representable"):
        assert lattice.get_coordinates_for_ratio("3/2", warn=True, warn_once=False) is None


def test_tone_lattice_lookup_can_suppress_warnings():
    lattice = ToneLattice.from_generators(
        generators=["4/3", "5/4"],
        resolution=1,
        bipolar=True,
        equave_reduce=False,
        equave=2,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", ToneLatticeLookupWarning)
        assert lattice.get_coordinates_for_ratio("3/2", warn=False) is None
    assert len(captured) == 0


def test_tone_lattice_lookup_modes_handle_ambiguous_ratio():
    lattice = ToneLattice.from_generators(
        generators=["4/3", "3/2"],
        resolution=1,
        bipolar=False,
        equave_reduce=True,
        equave=2,
    )
    ratio = Fraction(1, 1)
    first = lattice.get_coordinates_for_ratio(ratio, lookup="first")
    assert first == (0, 0)

    all_coords = lattice.get_coordinates_for_ratio(ratio, lookup="all")
    assert isinstance(all_coords, list)
    assert (0, 0) in all_coords and (1, 1) in all_coords

    with pytest.warns(ToneLatticeLookupWarning, match="uniquely"):
        unique = lattice.get_coordinates_for_ratio(ratio, lookup="unique")
    assert unique is None


def test_tone_lattice_lookup_rejects_invalid_mode():
    lattice = ToneLattice(dimensionality=2, resolution=1, bipolar=True, equave_reduce=False, equave=2)
    with pytest.raises(ValueError, match="lookup must be one of"):
        lattice.get_coordinates_for_ratio("3/2", lookup="bad-mode")  # type: ignore[arg-type]


def test_tone_lattice_default_prime_generators_have_matching_prime_basis():
    lattice = ToneLattice(dimensionality=3, resolution=1, bipolar=True, equave_reduce=False, equave=2)
    assert lattice.generators == [Fraction(2, 1), Fraction(3, 1), Fraction(5, 1)]
    assert lattice.prime_basis == [2, 3, 5]
    assert lattice.coord_label == "Monzo"


def test_ratio_coordinate_helpers_support_generator_basis():
    coord = ratio_to_coordinate("9/5", generators=["3/2", "6/5"], basis_primes=[2, 3, 5])
    assert tuple(int(x) for x in coord) == (1, 1)

    coords = ratios_to_coordinates(
        ["3/2", "9/5"],
        generators=["3/2", "6/5"],
        basis_primes=[2, 3, 5],
    )
    assert [tuple(int(x) for x in c) for c in coords] == [(1, 0), (1, 1)]


def test_parametric_field_values_are_cached_on_access():
    field = ParameterField(
        dimensionality=3,
        resolution=3,
        bipolar=True,
        function=lambda x: x[:, 0] + 2 * x[:, 1] - x[:, 2],
        compute_all=False,
    )
    coord = (1, -1, 2)
    node_id = field.get_node(coord)
    node_data_before = field._graph.get_node_data(node_id)
    assert 'field_value' not in node_data_before

    value_1 = field.get_field_value(coord)
    value_2 = field.get_field_value(coord)
    node_data_after = field._graph.get_node_data(node_id)

    assert value_1 == value_2
    assert 'field_value' in node_data_after
