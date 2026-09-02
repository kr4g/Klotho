import rustworkx as rx
import copy
import operator
import sys
from collections.abc import Mapping
from contextlib import contextmanager
from typing import List, TypeVar, Optional, Any, Union, Dict, Tuple
from types import MappingProxyType

T = TypeVar('T')

#: Largest integer rustworkx can hold as a node index. Its indices are an
#: unsigned machine word, so this is ``2**64 - 1`` on a 64-bit build and
#: ``2**32 - 1`` on a 32-bit one; deriving it from ``sys.maxsize`` (the signed
#: maximum) rather than hard-coding 64 bits keeps it right on both.
_MAX_NODE_INDEX = sys.maxsize * 2 + 1


def _addressable(node) -> bool:
    """Return True when ``node`` is an integer rustworkx could use as an index.

    The PyO3 conversion raises ``OverflowError`` for an integer outside the
    unsigned index range -- a negative id, or one wider than the platform's
    index type -- *before* ``has_node`` gets to answer. That error escaped
    every node-addressed method here, naming neither the method nor the
    argument that was wrong, so ``rt.make_rest(-1)`` reported
    ``can't convert negative int to unsigned`` while ``rt.make_rest(999)``
    reported ``Node 999 not found in tree``.

    Such an integer names no node in any graph. Callers below use this to send
    it down the same path a positive-but-absent id already takes, so the two
    cases cannot diverge.

    This does NOT judge non-integers. A ``str`` or ``None`` node argument is a
    different mistake and is passed through, so rustworkx raises ``TypeError``
    -- the right type for an argument of the wrong type.
    """
    try:
        index = operator.index(node)
    except TypeError:
        return True
    return 0 <= index <= _MAX_NODE_INDEX


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
        if not self._has_node(node):
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

    def _has_node(self, node) -> bool:
        """Index-level membership: is ``node`` a live rustworkx node index?

        Deliberately NOT ``node in self``. A subclass may redefine
        ``__contains__`` over a different address space --
        :class:`~klotho.topos.graphs.lattices.lattices.Lattice` is keyed by
        coordinate tuples and answers False for the very integers its own
        ``__getitem__`` then forwards here -- while the readers and writers on
        this class address nodes by index and must keep doing so.

        An integer outside the index range (see :func:`_addressable`) is
        reported absent rather than allowed to raise ``OverflowError`` out of
        the binding.
        """
        return _addressable(node) and self._rx.has_node(node)

    def __contains__(self, node):
        """Check if a node is in the graph.

        This is the shared gate for node-addressed verbs: the
        ``node not in self`` guards across
        :mod:`~klotho.topos.graphs.trees.trees` and the RhythmTree verbs all
        reach the caller through it, so an unaddressable integer raises the
        documented ``ValueError`` there instead of a foreign frame.
        """
        return self._has_node(node)

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
        if not self._has_node(u):
            raise KeyError(f"Node {u} not found in graph")
        if not self._has_node(v):
            raise KeyError(f"Node {v} not found in graph")
        self._rx.add_edge(u, v, attr if attr else {})
        self._invalidate_caches()

    def _remove_node_raw(self, node):
        """Remove a node directly.

        Removing a node the graph does not have is a no-op in rustworkx; an
        unaddressable integer is skipped so that it is a no-op too, instead of
        raising ``OverflowError`` from the binding.
        """
        if _addressable(node):
            self._rx.remove_node(node)
        self._invalidate_caches()

    def _remove_edge_raw(self, u, v):
        """Remove an edge directly.

        An unaddressable endpoint holds no edge, so it raises what rustworkx
        raises for any other missing edge rather than an ``OverflowError``
        from the endpoint conversion.
        """
        if not (_addressable(u) and _addressable(v)):
            raise rx.NoEdgeBetweenNodes("No edge found between nodes")
        self._rx.remove_edge(u, v)
        self._invalidate_caches()

    def _write_node_data(self, node, attrs: Dict[str, Any], replace: bool = False):
        """Sanctioned write of node data. Used by subclasses and internal code.

        ``attrs`` must be a mapping. This used to read
        ``dict(attrs) if isinstance(attrs, dict) else {}``, which discarded
        anything else in silence -- including two payloads a caller has every
        reason to pass: a list of pairs (valid ``dict()`` input), and a node
        view. ``graph[n]`` is a ``mappingproxy``, not a ``dict``, so
        ``replace_node_data(a, graph[b])`` erased node ``a`` instead of
        copying ``b`` onto it. Accepting ``Mapping`` fixes the second; raising
        on anything else makes the first loud instead of ignored.
        """
        if not self._has_node(node):
            raise KeyError(f"Node {node} not found in graph")
        if not isinstance(attrs, Mapping):
            raise TypeError(
                f"node data must be a mapping of attributes; got "
                f"{type(attrs).__name__}. A list of pairs is valid dict() "
                f"input but this write path used to discard it in silence -- "
                f"pass dict(attrs) instead."
            )
        normalized = dict(attrs)
        existing = self._rx.get_node_data(node)
        existing = existing if isinstance(existing, dict) else {}
        if replace:
            new_data = dict(normalized)
        else:
            new_data = dict(existing)
            new_data.update(normalized)
        self._rx[node] = new_data
        if self._write_batch_depth:
            self._write_batch_dirty = True
        else:
            self._invalidate_caches()

    # Batch-write coalescing: inside batch_writes(), node-DATA writes skip
    # the per-write _invalidate_caches (and therefore the per-write layer
    # invalidation sweep on trees); one invalidation runs at exit. This is
    # for data writes only — structural mutators invalidate immediately
    # regardless.
    _write_batch_depth = 0
    _write_batch_dirty = False

    @contextmanager
    def batch_writes(self):
        """Coalesce cache invalidation across a run of node-data writes.

        Usage: ``with tree.batch_writes(): ...many set_pfields...``.
        Re-entrant; the single invalidation fires when the outermost
        context exits (only if a write actually happened).
        """
        self._write_batch_depth += 1
        try:
            yield self
        finally:
            self._write_batch_depth -= 1
            if self._write_batch_depth == 0 and self._write_batch_dirty:
                self._write_batch_dirty = False
                self._invalidate_caches()

    def _clear_raw(self):
        """Remove all nodes and edges directly."""
        self._rx.clear()
        self._invalidate_caches()

    # Per-instance traversal cache, keyed on _structure_version and
    # invalidated lazily: _invalidate_caches only bumps the version, and
    # the next cached read discards the stale dict. Class-level defaults
    # mean every construction path (__init__, __new__ + manual setup in
    # structural_clone, __deepcopy__) starts consistent without help.
    # (These were process-global @lru_cache methods before: any write to
    # any graph cleared every graph's cache and pinned instances against
    # GC via the strong self keys.)
    _trav_cache = None
    _trav_cache_version = -1

    def _traversal_cache(self):
        cache = self._trav_cache
        if cache is None or self._trav_cache_version != self._structure_version:
            cache = {}
            self._trav_cache = cache
            self._trav_cache_version = self._structure_version
        return cache

    def _invalidate_caches(self):
        """Invalidate all caches when structure changes"""
        self._structure_version += 1

    def out_degree(self, node):
        """Get the out-degree of a node. An absent node has degree 0."""
        if not _addressable(node):
            return 0
        if hasattr(self._rx, 'out_degree'):
            return self._rx.out_degree(node)
        else:
            return self._rx.degree(node)

    def in_degree(self, node):
        """Get the in-degree of a node. An absent node has degree 0."""
        if not _addressable(node):
            return 0
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
        """Neighbours of a node, in ascending node-index order.

        Sorted for the same reason :meth:`successors` is: rustworkx returns
        neighbours in internal adjacency order, which is stable within one
        build but carries no meaning and changes with insertion order. Every
        caller that iterates neighbours -- walks, weighted traversals,
        tie-breaks -- would otherwise inherit that order as its answer.

        An absent node has no neighbours, so an unaddressable id gets the same
        empty list a positive-but-absent one gets.
        """
        if not _addressable(node):
            return []
        return sorted(self._rx.neighbors(node))

    def predecessors(self, node):
        """Returns all predecessors of a node."""
        cache = self._traversal_cache()
        key = ('g_pred', node)
        try:
            return cache[key]
        except KeyError:
            pass
        if not _addressable(node):
            result = tuple()
        elif hasattr(self._rx, 'predecessor_indices'):
            result = tuple(self._rx.predecessor_indices(node))
        else:
            result = tuple(self.neighbors(node))
        cache[key] = result
        return result

    def successors(self, node):
        """Returns all successors of a node in sorted order (left-to-right)."""
        cache = self._traversal_cache()
        key = ('g_succ', node)
        try:
            return cache[key]
        except KeyError:
            pass
        if not _addressable(node):
            result = tuple()
        elif hasattr(self._rx, 'successor_indices'):
            result = tuple(sorted(self._rx.successor_indices(node)))
        else:
            result = tuple(sorted(self.neighbors(node)))
        cache[key] = result
        return result

    def descendants(self, node):
        """Returns all descendants of a node using native RustworkX algorithm."""
        cache = self._traversal_cache()
        key = ('g_desc', node)
        try:
            return cache[key]
        except KeyError:
            pass
        try:
            result = tuple(rx.descendants(self._rx, node))
        except Exception:
            result = tuple()
        cache[key] = result
        return result

    def ancestors(self, node):
        """Returns all ancestors of a node using native RustworkX algorithm."""
        cache = self._traversal_cache()
        key = ('g_anc', node)
        try:
            return cache[key]
        except KeyError:
            pass
        try:
            result = tuple(rx.ancestors(self._rx, node))
        except Exception:
            result = tuple()
        cache[key] = result
        return result

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
        """Extract a subgraph starting from a given node.

        The result is re-indexed from zero, so ``node`` is generally NOT the
        same id in the subgraph that it was here; read the new root off
        :attr:`root_nodes` rather than assuming it kept its number.

        Notes
        -----
        AF-1b / audit H1, third door -- and unlike the other two this one was
        never broken. Child order in this codebase is ascending node id
        (:meth:`successors` sorts), so a copy is faithful only if old-to-new
        is monotone, and the id list here is assembled in traversal order,
        which is exactly the shape that permuted
        :meth:`~klotho.topos.graphs.trees.trees.Tree.subtree`.

        It survives because ``rx.subgraph`` walks the SOURCE graph's own node
        indices and keeps the ones in the set -- the list's order never
        reaches the result. Measured on rustworkx 0.17.1 over randomised
        graphs with reused (LIFO) ids in shuffled input orders: monotone
        every time, and pinned by
        ``test_rustworkx_subgraph_reindexes_by_ascending_original_index``.

        The list is sorted anyway. That is a no-op under the behaviour above,
        but rustworkx does not document it, and the ONE other reading a
        maintainer would guess -- "nodes are added in the order given" --
        makes a sorted list monotone too. Sorting costs nothing and removes
        the need to know which of the two is true.
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in graph")

        descendants = sorted({node, *self.descendants(node)})

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
        """Check if an edge exists between two nodes.

        An unaddressable endpoint is no node, so it holds no edge: False,
        the same answer an absent-but-addressable endpoint gets.
        """
        if not (_addressable(u) and _addressable(v)):
            return False
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

    @staticmethod
    def _copy_rx(rx_graph: Union[rx.PyGraph, rx.PyDiGraph]):
        """Copy a rustworkx graph so the twin shares no payload dict with it.

        ``PyGraph.copy()`` / ``PyDiGraph.copy()`` duplicate the node and edge
        tables but keep every payload BY REFERENCE, so a bare ``.copy()``
        hands back a graph pointing at one dict per node and one per edge,
        shared with the source. Klotho's internal writers mutate those dicts
        in place (``RhythmTree._evaluate`` is the loudest), which makes the
        sharing silent two-way corruption: recomputing one graph rewrites the
        other's cached values, with nothing raised.

        The freshening is deliberately ONE LEVEL DEEP -- a new dict per node
        and per edge, with the VALUES shared. Writers replace entries rather
        than mutating a value in place, and a recursive copy would clone the
        Instrument / Envelope / Bind objects a copy is supposed to hand back
        identical.
        """
        new_rx = rx_graph.copy()
        for idx in new_rx.node_indices():
            payload = new_rx.get_node_data(idx)
            if isinstance(payload, dict):
                new_rx[idx] = dict(payload)
        for idx in new_rx.edge_indices():
            payload = new_rx.get_edge_data_by_index(idx)
            if isinstance(payload, dict):
                new_rx.update_edge_by_index(idx, dict(payload))
        return new_rx

    @classmethod
    def _wrap_rx(cls, rx_graph: Union[rx.PyGraph, rx.PyDiGraph], copy_graph: bool = True):
        """Create an instance wrapping an existing RustworkX graph.

        ``copy_graph=True`` is a copy request and is honoured as one: payload
        dicts are freshened by :meth:`_copy_rx`, so later writes to the source
        do not reach the wrapper. ``copy_graph=False`` is the opt-out and
        keeps the caller's graph, payloads and all.
        """
        if not isinstance(rx_graph, (rx.PyGraph, rx.PyDiGraph)):
            raise TypeError(f"Expected rustworkx graph, got: {type(rx_graph)}")
        inst = cls.__new__(cls)
        inst._rx = cls._copy_rx(rx_graph) if copy_graph else rx_graph
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
        """Deep-copy the graph core: topology, freshened payloads, and meta.

        Payloads go through :meth:`_copy_rx`, which is the whole point --
        without it ``copy()`` returns twins that share one dict per node and
        per edge, and an in-place write to either is felt by both.

        This copies only what :class:`GraphCore` itself owns (``_rx``,
        ``_meta``, ``_structure_version``). A subclass with state of its own
        must extend this, as :class:`~klotho.topos.graphs.trees.trees.Tree`
        does.
        """
        new_graph = self.__class__.__new__(self.__class__)

        new_graph._rx = self._copy_rx(self._rx)
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
        return self._owner._has_node(node)

    def __getitem__(self, node):
        if not _addressable(node):
            # rustworkx would raise OverflowError here; an absent index is an
            # IndexError, which is what it raises for any other absent index.
            raise IndexError(f"No node found for index {node}")
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
