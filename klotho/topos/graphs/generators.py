"""Topology generators returning mutable :class:`Graph` instances.

These were previously classmethods on ``Graph``; they live here as module-level
functions so they are not inherited (and broken) by ``Graph`` subclasses such as
``Tree`` or ``RhythmTree``.
"""
import rustworkx as rx
import itertools
from typing import List, TypeVar, Optional, Any, Tuple
import numpy as np

from .graphs import Graph

T = TypeVar('T')

__all__ = [
    'path_graph',
    'cycle_graph',
    'star_graph',
    'random_graph',
    'complete_graph',
    'grid_graph',
    'from_cost_matrix',
]


def _resolve_labels(n_nodes: int, labels: Optional[List[Any]] = None) -> List[Any]:
    if labels is None:
        return list(range(n_nodes))
    if len(labels) != n_nodes:
        raise ValueError(f"Expected {n_nodes} labels, got {len(labels)}")
    return list(labels)


def path_graph(
    n_nodes: int,
    labels: Optional[List[Any]] = None,
    directed: bool = False,
    node_key: str = 'label',
) -> Graph:
    """Create a path graph with optional labels."""
    if n_nodes < 0:
        raise ValueError("n_nodes must be >= 0")
    resolved_labels = _resolve_labels(n_nodes, labels)
    edges = [(resolved_labels[i], resolved_labels[i + 1]) for i in range(max(0, n_nodes - 1))]
    return Graph.from_nodes_edges(
        nodes=[(label, {node_key: label}) for label in resolved_labels],
        edges=edges,
        directed=directed,
        node_mode='label',
        node_key=node_key,
    )


def cycle_graph(
    n_nodes: int,
    labels: Optional[List[Any]] = None,
    directed: bool = False,
    node_key: str = 'label',
) -> Graph:
    """Create a cycle graph with optional labels."""
    if n_nodes < 0:
        raise ValueError("n_nodes must be >= 0")
    resolved_labels = _resolve_labels(n_nodes, labels)
    edges = [(resolved_labels[i], resolved_labels[i + 1]) for i in range(max(0, n_nodes - 1))]
    if n_nodes > 2:
        edges.append((resolved_labels[-1], resolved_labels[0]))
    return Graph.from_nodes_edges(
        nodes=[(label, {node_key: label}) for label in resolved_labels],
        edges=edges,
        directed=directed,
        node_mode='label',
        node_key=node_key,
    )


def star_graph(
    n_nodes: int,
    center: int = 0,
    labels: Optional[List[Any]] = None,
    directed: bool = False,
    node_key: str = 'label',
) -> Graph:
    """Create a star graph with optional labels."""
    if n_nodes < 0:
        raise ValueError("n_nodes must be >= 0")
    if n_nodes == 0:
        return Graph.empty_graph(0, directed=directed, node_key=node_key)
    if center < 0 or center >= n_nodes:
        raise ValueError("center must be a valid node index")
    resolved_labels = _resolve_labels(n_nodes, labels)
    center_label = resolved_labels[center]
    edges = [(center_label, resolved_labels[i]) for i in range(n_nodes) if i != center]
    return Graph.from_nodes_edges(
        nodes=[(label, {node_key: label}) for label in resolved_labels],
        edges=edges,
        directed=directed,
        node_mode='label',
        node_key=node_key,
    )


def random_graph(
    n_nodes: int,
    p: float = 0.3,
    labels: Optional[List[Any]] = None,
    directed: bool = False,
    seed: Optional[int] = None,
    node_key: str = 'label',
) -> Graph:
    """Create a random Erdos-Renyi style graph with optional labels."""
    if n_nodes < 0:
        raise ValueError("n_nodes must be >= 0")
    if p < 0 or p > 1:
        raise ValueError("p must be between 0 and 1")
    resolved_labels = _resolve_labels(n_nodes, labels)
    rng = np.random.default_rng(seed)
    edges: List[Tuple[Any, Any]] = []
    if directed:
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i == j:
                    continue
                if rng.random() < p:
                    edges.append((resolved_labels[i], resolved_labels[j]))
    else:
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                if rng.random() < p:
                    edges.append((resolved_labels[i], resolved_labels[j]))
    return Graph.from_nodes_edges(
        nodes=[(label, {node_key: label}) for label in resolved_labels],
        edges=edges,
        directed=directed,
        node_mode='label',
        node_key=node_key,
    )


def complete_graph(
    n_nodes: int,
    labels: Optional[List[Any]] = None,
    directed: bool = False,
    node_key: str = 'label',
) -> Graph:
    """Create a complete graph with optional labels."""
    if n_nodes < 0:
        raise ValueError("n_nodes must be >= 0")
    resolved_labels = _resolve_labels(n_nodes, labels)
    edges: List[Tuple[Any, Any]] = []
    if directed:
        for i in range(n_nodes):
            for j in range(n_nodes):
                if i != j:
                    edges.append((resolved_labels[i], resolved_labels[j]))
    else:
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                edges.append((resolved_labels[i], resolved_labels[j]))
    return Graph.from_nodes_edges(
        nodes=[(label, {node_key: label}) for label in resolved_labels],
        edges=edges,
        directed=directed,
        node_mode='label',
        node_key=node_key,
    )


def grid_graph(dims, periodic=False) -> Graph:
    """Create an n-dimensional grid graph with coordinate data in nodes."""
    if not dims or len(dims) == 0:
        return Graph()

    dims = [list(d) for d in dims]

    if len(dims) == 1:
        if periodic:
            rx_graph = rx.generators.cycle_graph(len(dims[0]))
        else:
            rx_graph = rx.generators.path_graph(len(dims[0]))
        for i, coord_val in enumerate(dims[0]):
            rx_graph[i] = {'coord': (coord_val,)}
    elif len(dims) == 2 and not periodic:
        rows, cols = len(dims[0]), len(dims[1])
        rx_graph = rx.generators.grid_graph(rows, cols)
        for i, coord in enumerate(itertools.product(dims[0], dims[1])):
            rx_graph[i] = {'coord': coord}
    else:
        factor_graphs = []
        for dim_values in dims:
            if periodic:
                factor_graph = rx.generators.cycle_graph(len(dim_values))
            else:
                factor_graph = rx.generators.path_graph(len(dim_values))
            factor_graphs.append(factor_graph)

        product_graph = factor_graphs[0]
        id_to_coord_index = {node_id: (node_id,) for node_id in product_graph.node_indices()}

        for next_factor in factor_graphs[1:]:
            product_graph, node_map = rx.graph_cartesian_product(product_graph, next_factor)
            next_id_to_coord_index = {}
            for (left_node, right_node), product_node in node_map.items():
                next_id_to_coord_index[product_node] = id_to_coord_index[left_node] + (right_node,)
            id_to_coord_index = next_id_to_coord_index

        for node_id, coord_idx_tuple in id_to_coord_index.items():
            coord = tuple(dims[i][coord_idx_tuple[i]] for i in range(len(dims)))
            product_graph[node_id] = {'coord': coord}

        rx_graph = product_graph

    return Graph.from_rustworkx(rx_graph)


def from_cost_matrix(cost_matrix: np.ndarray, items: List[T]) -> Graph:
    """Create a Graph from a symmetric cost matrix.

    Edge weights represent the costs between nodes. Self-loops are excluded
    and only positive-cost edges are included.
    """
    graph = Graph()

    node_list = []
    for item in items:
        node_id = graph.add_node(value=item)
        node_list.append((node_id, {'value': item}))

    edge_list = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            cost = cost_matrix[i, j]
            if cost > 0:
                edge_list.append((node_list[i][0], node_list[j][0], {'weight': cost}))

    if edge_list:
        graph._rx.add_edges_from(edge_list)

    return graph
