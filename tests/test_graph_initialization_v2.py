import networkx as nx
import rustworkx as rx

from klotho.topos.graphs import Graph


def test_graph_constructor_directed_flag():
    undirected = Graph()
    directed = Graph(directed=True)

    assert undirected.is_directed() is False
    assert directed.is_directed() is True


def test_from_edges_label_mode_with_strings():
    graph = Graph.from_edges([("A", "B"), ("A", "C")])

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2

    labels = {graph[node]["label"] for node in graph.nodes}
    assert labels == {"A", "B", "C"}


def test_from_edges_label_mode_with_non_contiguous_integers():
    graph = Graph.from_edges([(10, 42), (42, 999)])

    assert graph.number_of_nodes() == 3
    assert graph.number_of_edges() == 2

    labels = {graph[node]["label"] for node in graph.nodes}
    assert labels == {10, 42, 999}


def test_from_nodes_edges_preserves_node_and_edge_attrs():
    graph = Graph.from_nodes_edges(
        nodes=[("A", {"kind": "root"}), ("B", {"kind": "leaf"})],
        edges=[("A", "B", {"weight": 2.5})],
    )

    node_by_label = {graph[node]["label"]: node for node in graph.nodes}
    a = node_by_label["A"]
    b = node_by_label["B"]

    assert graph[a]["kind"] == "root"
    assert graph[b]["kind"] == "leaf"
    assert graph.edges[a, b]["weight"] == 2.5


def test_from_rustworkx_imports_graph_structure():
    rx_graph = rx.PyDiGraph()
    n0 = rx_graph.add_node({"label": "A"})
    n1 = rx_graph.add_node({"label": "B"})
    rx_graph.add_edge(n0, n1, {"weight": 3})

    graph = Graph.from_rustworkx(rx_graph)

    assert graph.is_directed() is True
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1
    assert graph[n0]["label"] == "A"
    assert graph.edges[n0, n1]["weight"] == 3


def test_from_networkx_imports_graph_structure():
    nx_graph = nx.DiGraph()
    nx_graph.add_node("src", role="source")
    nx_graph.add_node("dst", role="target")
    nx_graph.add_edge("src", "dst", weight=1.25)

    graph = Graph.from_networkx(nx_graph)

    assert graph.is_directed() is True
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1

    roles = {graph[node]["role"] for node in graph.nodes}
    assert roles == {"source", "target"}

    nx_round_trip = graph.to_networkx()
    assert nx_round_trip.number_of_nodes() == 2
    assert nx_round_trip.number_of_edges() == 1
