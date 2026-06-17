import rustworkx as rx
import copy
from functools import lru_cache
from typing import List, TypeVar, Optional, Any, Union, Dict, Tuple
from types import MappingProxyType

T = TypeVar('T')


class GraphCore:
    """Read-only core for all Klotho graph-shaped structures.

    Wraps a RustworkX ``PyGraph``/``PyDiGraph`` (stored as ``self._rx``) and
    exposes views, traversal, and query operations only. Mutation is provided
    by subclasses that opt in (e.g. :class:`Graph`, :class:`Tree`); immutable
    structures (lattices, combination sets) simply never expose mutators.

    Subclasses and internal code perform sanctioned writes through the
    protected ``_*_raw`` primitives, which write directly to ``self._rx`` and
    invalidate caches without any validation or recomputation policy.
    """

    def __init__(self, directed: bool = False):
        """Initialize an empty graph core."""
        self._meta = {}
        self._structure_version = 0
        self._rx = rx.PyDiGraph() if directed else rx.PyGraph()

    @property
    def nodes(self):
        """Return a view of the nodes that can be subscripted."""
        return GraphNodeView(self)

    @property
    def edges(self):
        """Return a view of the edges."""
        return GraphEdgeView(self)

    def __getitem__(self, node):
        """Get node data for a given node."""
        if not self._rx.has_node(node):
            raise KeyError(f"Node {node} not found in graph")
        node_data = self._rx.get_node_data(node)

        if not isinstance(node_data, dict):
            return MappingProxyType({})

        return MappingProxyType(node_data)

    def __len__(self):
        """Return the number of nodes."""
        return self._rx.num_nodes()

    def __str__(self):
        """String representation of the graph."""
        return f"Graph with {self.number_of_nodes()} nodes and {self.number_of_edges()} edges"

    def __repr__(self):
        """String representation of the graph."""
        return f"Graph({self.number_of_nodes()}, {self.number_of_edges()})"

    def __iter__(self):
        """Iterate over node objects."""
        return iter(self._rx.node_indices())

    def __contains__(self, node):
        """Check if a node is in the graph."""
        return self._rx.has_node(node)

    # ------------------------------------------------------------------
    # Sanctioned low-level write primitives (no policy / no recomputation)
    # ------------------------------------------------------------------
    def _add_node_raw(self, **attr):
        """Add a node directly. Returns the new node id."""
        node_id = self._rx.add_node(attr if attr else {})
        self._invalidate_caches()
        return node_id

    def _add_edge_raw(self, u, v, **attr):
        """Add an edge directly between existing nodes."""
        if not self._rx.has_node(u):
            raise KeyError(f"Node {u} not found in graph")
        if not self._rx.has_node(v):
            raise KeyError(f"Node {v} not found in graph")
        self._rx.add_edge(u, v, attr if attr else {})
        self._invalidate_caches()

    def _remove_node_raw(self, node):
        """Remove a node directly."""
        self._rx.remove_node(node)
        self._invalidate_caches()

    def _remove_edge_raw(self, u, v):
        """Remove an edge directly."""
        self._rx.remove_edge(u, v)
        self._invalidate_caches()

    def _write_node_data(self, node, attrs: Dict[str, Any], replace: bool = False):
        """Sanctioned write of node data. Used by subclasses and internal code."""
        if not self._rx.has_node(node):
            raise KeyError(f"Node {node} not found in graph")
        normalized = dict(attrs) if isinstance(attrs, dict) else {}
        existing = self._rx.get_node_data(node)
        existing = existing if isinstance(existing, dict) else {}
        if replace:
            new_data = dict(normalized)
        else:
            new_data = dict(existing)
            new_data.update(normalized)
        self._rx[node] = new_data
        self._invalidate_caches()

    def _clear_raw(self):
        """Remove all nodes and edges directly."""
        self._rx.clear()
        self._invalidate_caches()

    def _invalidate_caches(self):
        """Invalidate all caches when structure changes"""
        self._structure_version += 1
        if hasattr(self, 'descendants'):
            self.descendants.cache_clear()
        if hasattr(self, 'ancestors'):
            self.ancestors.cache_clear()
        if hasattr(self, 'successors'):
            self.successors.cache_clear()
        if hasattr(self, 'predecessors'):
            self.predecessors.cache_clear()

    def out_degree(self, node):
        """Get the out-degree of a node"""
        if hasattr(self._rx, 'out_degree'):
            return self._rx.out_degree(node)
        else:
            return self._rx.degree(node)

    def in_degree(self, node):
        """Get the in-degree of a node"""
        if hasattr(self._rx, 'in_degree'):
            return self._rx.in_degree(node)
        else:
            return self._rx.degree(node)

    def _get_node_object(self, index):
        """Convert RustworkX node index to node object.

        For the base graph, nodes are just their indices. Subclasses can
        override this for different node representations.
        """
        return index

    def _get_node_index(self, node):
        """Convert node object to RustworkX index.

        For the base graph, nodes are just their indices. Subclasses can
        override this for different node representations.
        """
        return node

    def neighbors(self, node):
        """Get neighbors of a node"""
        return list(self._rx.neighbors(node))

    @lru_cache(maxsize=None)
    def predecessors(self, node):
        """Returns all predecessors of a node."""
        _ = self._structure_version
        if hasattr(self._rx, 'predecessor_indices'):
            return tuple(self._rx.predecessor_indices(node))
        else:
            return tuple(self.neighbors(node))

    @lru_cache(maxsize=None)
    def successors(self, node):
        """Returns all successors of a node in sorted order (left-to-right)."""
        _ = self._structure_version
        if hasattr(self._rx, 'successor_indices'):
            succ_indices = self._rx.successor_indices(node)
            return tuple(sorted(succ_indices))
        else:
            return tuple(sorted(self.neighbors(node)))

    @lru_cache(maxsize=None)
    def descendants(self, node):
        """Returns all descendants of a node using native RustworkX algorithm."""
        _ = self._structure_version
        try:
            return tuple(rx.descendants(self._rx, node))
        except Exception:
            return tuple()

    @lru_cache(maxsize=None)
    def ancestors(self, node):
        """Returns all ancestors of a node using native RustworkX algorithm."""
        _ = self._structure_version
        try:
            return tuple(rx.ancestors(self._rx, node))
        except Exception:
            return tuple()

    def topological_sort(self):
        """Returns nodes in topological order."""
        if hasattr(self._rx, 'out_degree'):
            indices = rx.topological_sort(self._rx)
        else:
            indices = self._rx.node_indices()

        return (idx for idx in indices)

    def to_directed(self):
        """Return a directed version of this graph as a mutable :class:`Graph`."""
        from .graphs import Graph

        directed_rx = rx.PyDiGraph()

        for idx in self._rx.node_indices():
            node_data = self._rx.get_node_data(idx)
            directed_rx.add_node(node_data)

        for src, tgt, edge_data in self.edges(data=True):
            directed_rx.add_edge(src, tgt, edge_data)

        new_graph = Graph.__new__(Graph)
        new_graph._rx = directed_rx
        new_graph._meta = copy.deepcopy(self._meta)
        new_graph._structure_version = 0

        return new_graph

    def number_of_nodes(self):
        """Return the number of nodes in the graph."""
        return self._rx.num_nodes()

    def number_of_edges(self):
        """Return the number of edges in the graph."""
        return self._rx.num_edges()

    def nodes_with_data(self, data=True):
        """Return nodes with their data."""
        if data:
            for idx in self._rx.node_indices():
                node_data = self._rx.get_node_data(idx)
                yield (idx, node_data if isinstance(node_data, dict) else {})
        else:
            for idx in self._rx.node_indices():
                yield idx

    def subgraph(self, node, renumber=True):
        """Extract a subgraph starting from a given node."""
        if node not in self:
            raise ValueError(f"Node {node} not found in graph")

        descendants = [node] + list(self.descendants(node))

        subgraph_rx = self._rx.subgraph(descendants)

        return self._from_graph(subgraph_rx, renumber=renumber)

    @property
    def root_nodes(self):
        """Returns root nodes (nodes with no predecessors)"""
        root_indices = []

        if hasattr(self._rx, 'in_degree'):
            for idx in self._rx.node_indices():
                if self._rx.in_degree(idx) == 0:
                    root_indices.append(idx)
        else:
            if self._rx.num_nodes() == 0:
                return tuple()

            degrees = [(idx, self._rx.degree(idx)) for idx in self._rx.node_indices()]
            if degrees:
                min_deg_nodes = [idx for idx, deg in degrees if deg > 0]
                if min_deg_nodes:
                    root_indices = [min(min_deg_nodes)]

        return tuple(root_indices)

    def has_edge(self, u, v):
        """Check if an edge exists between two nodes."""
        return self._rx.has_edge(u, v)

    def renumber_nodes(self, method='default'):
        """Renumber the nodes in the graph to consecutive integers."""
        if method == 'default':
            pass
        elif method in ['dfs', 'bfs']:
            pass
        else:
            raise ValueError(f"Unknown renumbering method: {method}")

        return self

    def copy(self):
        """Create a deep copy of this graph."""
        return copy.deepcopy(self)

    def is_directed(self):
        """Return True if graph is directed, False otherwise."""
        return isinstance(self._rx, rx.PyDiGraph)

    def is_multigraph(self):
        """Return True if graph is a multigraph, False otherwise."""
        return False

    def to_networkx(self):
        """Convert this graph to a NetworkX graph."""
        import networkx as nx

        if self.is_directed():
            nx_graph = nx.DiGraph()
        else:
            nx_graph = nx.Graph()

        for node, attrs in self.nodes(data=True):
            nx_graph.add_node(node, **attrs)

        for u, v, attrs in self.edges(data=True):
            nx_graph.add_edge(u, v, **attrs)

        return nx_graph

    @classmethod
    def _wrap_rx(cls, rx_graph: Union[rx.PyGraph, rx.PyDiGraph], copy_graph: bool = True):
        """Create an instance wrapping an existing RustworkX graph."""
        if not isinstance(rx_graph, (rx.PyGraph, rx.PyDiGraph)):
            raise TypeError(f"Expected rustworkx graph, got: {type(rx_graph)}")
        inst = cls.__new__(cls)
        inst._rx = rx_graph.copy() if copy_graph else rx_graph
        inst._meta = {}
        inst._structure_version = 0
        return inst

    @classmethod
    def _from_graph(cls, G, **kwargs):
        """Create a new instance from an existing graph or rustworkx graph."""
        if isinstance(G, GraphCore):
            new_graph = cls._wrap_rx(G._rx)
            new_graph._meta = copy.deepcopy(G._meta)
            return new_graph
        if isinstance(G, (rx.PyGraph, rx.PyDiGraph)):
            return cls._wrap_rx(G)
        raise TypeError(f"Unsupported graph type: {type(G)}")

    def __deepcopy__(self, memo):
        new_graph = self.__class__.__new__(self.__class__)

        new_graph._rx = self._rx.copy()
        new_graph._meta = copy.deepcopy(self._meta, memo)
        new_graph._structure_version = 0

        return new_graph


class GraphNodeView:
    """View of graph nodes that mimics NetworkX NodeView behavior."""

    def __init__(self, graph: GraphCore):
        self._owner = graph

    def __iter__(self):
        return iter(self._owner._rx.node_indices())

    def __len__(self):
        return self._owner.number_of_nodes()

    def __contains__(self, node):
        return self._owner._rx.has_node(node)

    def __getitem__(self, node):
        node_data = self._owner._rx.get_node_data(node)
        if not isinstance(node_data, dict):
            return MappingProxyType({})
        return MappingProxyType(node_data)

    def __call__(self, data=False):
        """Return nodes with optional data."""
        if data:
            for idx in self._owner._rx.node_indices():
                node_data = self._owner._rx.get_node_data(idx)
                if isinstance(node_data, dict):
                    yield (idx, MappingProxyType(node_data))
                else:
                    yield (idx, MappingProxyType({}))
        else:
            for idx in self._owner._rx.node_indices():
                yield idx


class GraphEdgeView:
    """View of graph edges that mimics NetworkX EdgeView behavior."""

    def __init__(self, graph: GraphCore):
        self._owner = graph

    def __iter__(self):
        for edge_data in self._owner._rx.edge_list():
            src_idx, tgt_idx = edge_data
            yield (src_idx, tgt_idx)

    def __len__(self):
        return self._owner.number_of_edges()

    def __call__(self, data=False):
        """Return edges with optional data."""
        if data:
            for src_idx, tgt_idx in self._owner._rx.edge_list():
                edge_data = self._owner._rx.get_edge_data(src_idx, tgt_idx)
                yield (src_idx, tgt_idx, edge_data if isinstance(edge_data, dict) else {})
        else:
            for src_idx, tgt_idx in self._owner._rx.edge_list():
                yield (src_idx, tgt_idx)

    def __getitem__(self, edge):
        """Get edge data for a given edge (u, v)."""
        u, v = edge
        edge_data = self._owner._rx.get_edge_data(u, v)
        return edge_data if isinstance(edge_data, dict) else {}
