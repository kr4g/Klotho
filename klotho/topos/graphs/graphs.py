import rustworkx as rx
from typing import List, TypeVar, Optional, Any, Union, Dict, Tuple

from .core import GraphCore, GraphNodeView, GraphEdgeView

T = TypeVar('T')


class Graph(GraphCore):
    """A general-purpose mutable graph.

    Adds free-form topology and node-data mutation on top of the read-only
    :class:`GraphCore`. Node views remain read-only (use the sanctioned
    ``set_node_data``/``update_node_data``/``replace_node_data`` methods to
    change node attributes).
    """

    @classmethod
    def directed(cls):
        """Create an empty directed graph."""
        return cls(directed=True)

    @classmethod
    def digraph(cls):
        """Alias for directed graph creation."""
        return cls.directed()

    @classmethod
    def from_rustworkx(cls, graph: Union[rx.PyGraph, rx.PyDiGraph], copy_graph: bool = True):
        """Create a Graph from an existing RustworkX graph."""
        return cls._wrap_rx(graph, copy_graph=copy_graph)

    @classmethod
    def from_networkx(cls, graph, copy_graph: bool = True):
        """Create a Graph from a NetworkX graph."""
        import networkx as nx

        if not isinstance(graph, (nx.Graph, nx.DiGraph)):
            raise TypeError(f"Expected networkx.Graph or networkx.DiGraph, got: {type(graph)}")

        nx_graph = graph.copy() if copy_graph else graph
        directed = nx_graph.is_directed()
        new_graph = cls(directed=directed)

        node_index_map = {}
        for node, attrs in nx_graph.nodes(data=True):
            node_attrs = dict(attrs) if isinstance(attrs, dict) else {}
            node_index_map[node] = new_graph._rx.add_node(node_attrs)

        for u, v, attrs in nx_graph.edges(data=True):
            edge_attrs = dict(attrs) if isinstance(attrs, dict) else {}
            new_graph._rx.add_edge(node_index_map[u], node_index_map[v], edge_attrs)

        return new_graph

    @classmethod
    def from_nodes_edges(
        cls,
        nodes: Optional[List[Any]] = None,
        edges: Optional[List[Tuple[Any, ...]]] = None,
        directed: bool = False,
        node_mode: str = 'label',
        node_key: str = 'label',
    ):
        """Create a graph from node and edge iterables."""
        graph = cls(directed=directed)
        node_lookup: Dict[Any, int] = {}

        if node_mode not in {'label', 'id'}:
            raise ValueError("node_mode must be 'label' or 'id'")

        def ensure_node(node_value, attrs=None):
            attrs = dict(attrs) if isinstance(attrs, dict) else {}
            if node_mode == 'id':
                if not isinstance(node_value, int):
                    raise TypeError("node_mode='id' requires integer node values")
                while graph.number_of_nodes() <= node_value:
                    graph.add_node()
                graph.set_node_data(node_value, **attrs)
                return node_value

            if node_value in node_lookup:
                node_id = node_lookup[node_value]
                if attrs:
                    graph.set_node_data(node_id, **attrs)
                return node_id

            node_attrs = {node_key: node_value}
            node_attrs.update(attrs)
            node_id = graph.add_node(**node_attrs)
            node_lookup[node_value] = node_id
            return node_id

        if nodes:
            for node_entry in nodes:
                if isinstance(node_entry, tuple) and len(node_entry) == 2 and isinstance(node_entry[1], dict):
                    ensure_node(node_entry[0], node_entry[1])
                else:
                    ensure_node(node_entry)

        if edges:
            for edge in edges:
                if len(edge) == 2:
                    u_label, v_label = edge
                    edge_attrs = {}
                elif len(edge) == 3:
                    u_label, v_label, edge_attrs = edge
                    edge_attrs = dict(edge_attrs) if isinstance(edge_attrs, dict) else {}
                else:
                    raise ValueError("Edges must be (u, v) or (u, v, attrs)")

                u = ensure_node(u_label)
                v = ensure_node(v_label)
                graph.add_edge(u, v, **edge_attrs)

        return graph

    @classmethod
    def from_edges(
        cls,
        edges: List[Tuple[Any, ...]],
        directed: bool = False,
        node_mode: str = 'label',
        node_key: str = 'label',
    ):
        """Create a graph from an edge list."""
        return cls.from_nodes_edges(
            nodes=None,
            edges=edges,
            directed=directed,
            node_mode=node_mode,
            node_key=node_key,
        )

    @classmethod
    def empty_graph(
        cls,
        n_nodes: int = 0,
        labels: Optional[List[Any]] = None,
        directed: bool = False,
        node_key: str = 'label',
    ):
        """Create an empty graph with optional labeled nodes."""
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        if labels is None:
            resolved_labels = list(range(n_nodes))
        else:
            if len(labels) != n_nodes:
                raise ValueError(f"Expected {n_nodes} labels, got {len(labels)}")
            resolved_labels = list(labels)
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=[],
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def add_node(self, **attr):
        """Add a node to the graph. Returns the node id."""
        return self._add_node_raw(**attr)

    def set_node_data(self, node, **attr):
        """Update data for an existing node."""
        self._write_node_data(node, attr, replace=False)

    def update_node_data(self, node, attrs: Dict[str, Any]):
        """Update data for an existing node from a dictionary."""
        self._write_node_data(node, attrs, replace=False)

    def replace_node_data(self, node, attrs: Dict[str, Any]):
        """Replace all data for an existing node."""
        self._write_node_data(node, attrs, replace=True)

    def remove_node(self, node):
        """Remove a node from the graph."""
        self._remove_node_raw(node)

    def add_edge(self, u, v, **attr):
        """Add an edge to the graph with optional attributes."""
        self._add_edge_raw(u, v, **attr)

    def remove_edge(self, u, v):
        """Remove an edge from the graph."""
        self._remove_edge_raw(u, v)

    def update(self, edges=None, nodes=None):
        """Update the graph with nodes and edges."""
        if nodes:
            for node_data in nodes:
                if isinstance(node_data, tuple) and len(node_data) == 2:
                    node, attrs = node_data
                    if not self._rx.has_node(node):
                        raise KeyError(f"Node {node} not found in graph")
                    self.set_node_data(node, **attrs)
                else:
                    self.add_node(label=node_data)

        if edges:
            for edge_data in edges:
                if len(edge_data) == 2:
                    u, v = edge_data
                    self.add_edge(u, v)
                elif len(edge_data) == 3:
                    u, v, attrs = edge_data
                    self.add_edge(u, v, **attrs)

        self._invalidate_caches()

    def clear(self):
        """Remove all nodes and edges from the graph."""
        self._clear_raw()

    def set_node_attributes(self, node, attributes):
        """Set attributes for a node."""
        self._write_node_data(node, attributes, replace=False)

    def clear_node_attributes(self, nodes=None):
        """Clear attributes of specified nodes or all nodes."""
        nodes_to_clear = nodes if nodes is not None else self._rx.node_indices()
        for node in nodes_to_clear:
            if node in self:
                self._write_node_data(node, {}, replace=True)
