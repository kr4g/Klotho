import pytest
from fractions import Fraction

from klotho.topos.graphs import Graph
from klotho.chronos import RhythmTree
from klotho.tonos import HarmonicTree, ToneLattice, CombinationProductSet


def test_graph_node_view_is_read_only():
    graph = Graph()
    node = graph.add_node(label="A")

    with pytest.raises(TypeError):
        graph.nodes[node]["label"] = "B"

    with pytest.raises(TypeError):
        graph[node]["label"] = "B"


def test_rhythm_tree_set_node_data_uses_proportion_and_tied():
    rt = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 1))
    target = list(rt.successors(rt.root))[1]

    rt.set_node_data(target, proportion=5)
    assert rt[target]["proportion"] == 5

    rt.set_node_data(target, tied=True)
    assert isinstance(rt[target]["proportion"], float)
    assert rt[target]["tied"] is True

    rt.set_node_data(target, tied=False)
    assert isinstance(rt[target]["proportion"], int)
    assert rt[target]["tied"] is False


def test_rhythm_tree_illegal_direct_keys_rejected():
    rt = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 1))
    target = list(rt.successors(rt.root))[0]

    with pytest.raises(ValueError):
        rt.set_node_data(target, label=3)

    with pytest.raises(ValueError):
        rt.set_node_data(target, metric_duration=1)


def test_harmonic_tree_factor_is_canonical_mutable_key():
    ht = HarmonicTree(root=1, children=(3, 5, 7))
    target = list(ht.successors(ht.root))[1]

    ht.set_node_data(target, factor=11)
    assert ht[target]["factor"] == 11

    with pytest.raises(ValueError):
        ht.set_node_data(target, label=11)

    with pytest.raises(ValueError):
        ht.set_node_data(target, harmonic=11)


def test_lattice_topology_and_attr_mutation_are_blocked():
    lattice = ToneLattice.from_generators((Fraction(3, 2), Fraction(5, 4)), resolution=2)
    coord = lattice.coords[0]
    node = lattice.get_node(coord)

    with pytest.raises(PermissionError):
        lattice.add_node(coord=(99, 99))

    with pytest.raises(PermissionError):
        lattice.set_node_data(node, ratio=1)


def test_cps_graph_surface_is_immutable():
    cps = CombinationProductSet.hexany((1, 3, 5, 7))
    node = next(iter(cps.graph.nodes))
    edge = next(iter(cps.graph.edges))

    with pytest.raises(PermissionError):
        cps.graph.set_node_data(node, ratio=1)

    with pytest.raises(PermissionError):
        cps.graph.remove_edge(*edge)
