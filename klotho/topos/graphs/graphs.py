import rustworkx as rx
import copy
from functools import lru_cache
from typing import List, TypeVar, Optional, Any, Union, Dict, Iterator, Tuple
import numpy as np

T = TypeVar('T')


class Graph:
    def __init__(self, directed: bool = False):
        """Initialize an empty Klotho graph."""
        self._meta = {}
        self._structure_version = 0
        self._graph = rx.PyDiGraph() if directed else rx.PyGraph()
        
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
        if not self._graph.has_node(node):
            raise KeyError(f"Node {node} not found in graph")
        node_data = self._graph.get_node_data(node)
        
        if not isinstance(node_data, dict):
            empty_dict = {}
            return empty_dict
        
        return node_data
    
    def __len__(self):
        """Return the number of nodes."""
        return self._graph.num_nodes()
    
    def __str__(self):
        """String representation of the graph."""
        return f"Graph with {self.number_of_nodes()} nodes and {self.number_of_edges()} edges"
    
    def __repr__(self):
        """String representation of the graph."""
        return f"Graph({self.number_of_nodes()}, {self.number_of_edges()})"
    
    def __iter__(self):
        """Iterate over node objects."""
        return iter(self._graph.node_indices())
    
    def __contains__(self, node):
        """Check if a node is in the graph."""
        return self._graph.has_node(node)
    
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
        if hasattr(self._graph, 'out_degree'):
            return self._graph.out_degree(node)
        else:
            return self._graph.degree(node)
    
    def in_degree(self, node):
        """Get the in-degree of a node"""
        if hasattr(self._graph, 'in_degree'):
            return self._graph.in_degree(node)
        else:
            return self._graph.degree(node)
    
    def _get_node_object(self, index):
        """Convert RustworkX node index to node object.
        
        For the base Graph class, nodes are just their indices.
        Subclasses can override this for different node representations.
        """
        return index
    
    def _get_node_index(self, node):
        """Convert node object to RustworkX index.
        
        For the base Graph class, nodes are just their indices.
        Subclasses can override this for different node representations.
        """
        return node

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
        if not isinstance(graph, (rx.PyGraph, rx.PyDiGraph)):
            raise TypeError(f"Expected rustworkx graph, got: {type(graph)}")

        new_graph = cls.__new__(cls)
        new_graph._graph = graph.copy() if copy_graph else graph
        new_graph._meta = {}
        new_graph._structure_version = 0
        return new_graph

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
            node_index_map[node] = new_graph._graph.add_node(node_attrs)

        for u, v, attrs in nx_graph.edges(data=True):
            edge_attrs = dict(attrs) if isinstance(attrs, dict) else {}
            new_graph._graph.add_edge(node_index_map[u], node_index_map[v], edge_attrs)

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
        resolved_labels = cls._resolve_labels(n_nodes, labels)
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=[],
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    @classmethod
    def path_graph(
        cls,
        n_nodes: int,
        labels: Optional[List[Any]] = None,
        directed: bool = False,
        node_key: str = 'label',
    ):
        """Create a path graph with optional labels."""
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        resolved_labels = cls._resolve_labels(n_nodes, labels)
        edges = [(resolved_labels[i], resolved_labels[i + 1]) for i in range(max(0, n_nodes - 1))]
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=edges,
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    @classmethod
    def cycle_graph(
        cls,
        n_nodes: int,
        labels: Optional[List[Any]] = None,
        directed: bool = False,
        node_key: str = 'label',
    ):
        """Create a cycle graph with optional labels."""
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        resolved_labels = cls._resolve_labels(n_nodes, labels)
        edges = [(resolved_labels[i], resolved_labels[i + 1]) for i in range(max(0, n_nodes - 1))]
        if n_nodes > 2:
            edges.append((resolved_labels[-1], resolved_labels[0]))
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=edges,
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    @classmethod
    def star_graph(
        cls,
        n_nodes: int,
        center: int = 0,
        labels: Optional[List[Any]] = None,
        directed: bool = False,
        node_key: str = 'label',
    ):
        """Create a star graph with optional labels."""
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        if n_nodes == 0:
            return cls.empty_graph(0, directed=directed, node_key=node_key)
        if center < 0 or center >= n_nodes:
            raise ValueError("center must be a valid node index")
        resolved_labels = cls._resolve_labels(n_nodes, labels)
        center_label = resolved_labels[center]
        edges = [(center_label, resolved_labels[i]) for i in range(n_nodes) if i != center]
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=edges,
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    @classmethod
    def random_graph(
        cls,
        n_nodes: int,
        p: float = 0.3,
        labels: Optional[List[Any]] = None,
        directed: bool = False,
        seed: Optional[int] = None,
        node_key: str = 'label',
    ):
        """Create a random Erdos-Renyi style graph with optional labels."""
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        if p < 0 or p > 1:
            raise ValueError("p must be between 0 and 1")
        resolved_labels = cls._resolve_labels(n_nodes, labels)
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
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=edges,
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )

    @staticmethod
    def _resolve_labels(n_nodes: int, labels: Optional[List[Any]] = None) -> List[Any]:
        if labels is None:
            return list(range(n_nodes))
        if len(labels) != n_nodes:
            raise ValueError(f"Expected {n_nodes} labels, got {len(labels)}")
        return list(labels)
    
    def neighbors(self, node):
        """Get neighbors of a node"""
        return list(self._graph.neighbors(node))
    
    @lru_cache(maxsize=None)
    def predecessors(self, node):
        """Returns all predecessors of a node.
        
        Args:
            node: The node whose predecessors to return
            
        Returns:
            tuple: All predecessors of the node
        """
        _ = self._structure_version
        if hasattr(self._graph, 'predecessor_indices'):
            return tuple(self._graph.predecessor_indices(node))
        else:
            return tuple(self.neighbors(node))
    
    @lru_cache(maxsize=None)
    def successors(self, node):
        """Returns all successors of a node.
        
        Args:
            node: The node whose successors to return
            
        Returns:
            tuple: All successors of the node in sorted order (left-to-right)
        """
        _ = self._structure_version
        if hasattr(self._graph, 'successor_indices'):
            succ_indices = self._graph.successor_indices(node)
            return tuple(sorted(succ_indices))
        else:
            return tuple(sorted(self.neighbors(node)))
    
    @lru_cache(maxsize=None)
    def descendants(self, node):
        """Returns all descendants of a node using native RustworkX algorithm.
        
        Args:
            node: The node whose descendants to return
            
        Returns:
            tuple: All descendants of the node
        """
        _ = self._structure_version
        try:
            return tuple(rx.descendants(self._graph, node))
        except Exception:
            return tuple()
    
    @lru_cache(maxsize=None)
    def ancestors(self, node):
        """Returns all ancestors of a node using native RustworkX algorithm.
        
        Args:
            node: The node whose ancestors to return
            
        Returns:
            tuple: All ancestors of the node
        """
        _ = self._structure_version
        try:
            return tuple(rx.ancestors(self._graph, node))
        except Exception:
            return tuple()
    
    def topological_sort(self):
        """Returns nodes in topological order.
        
        Returns:
            generator: Nodes in topological order
        """
        if hasattr(self._graph, 'out_degree'):
            indices = rx.topological_sort(self._graph)
        else:
            indices = self._graph.node_indices()
        
        return (idx for idx in indices)
    
    def to_directed(self):
        """Return a directed version of this graph.
        
        Returns:
            Graph: A new Graph instance with directed edges
        """
        directed_rx = rx.PyDiGraph()
        
        for idx in self._graph.node_indices():
            node_data = self._graph.get_node_data(idx)
            directed_rx.add_node(node_data)
        
        for src, tgt, edge_data in self.edges(data=True):
            directed_rx.add_edge(src, tgt, edge_data)
        
        new_graph = Graph.__new__(Graph)
        new_graph._graph = directed_rx
        new_graph._meta = copy.deepcopy(self._meta)
        new_graph._structure_version = 0
        
        return new_graph
    
    def number_of_nodes(self):
        """Return the number of nodes in the graph.
        
        Returns:
            int: Number of nodes
        """
        return self._graph.num_nodes()
        
    def number_of_edges(self):
        """Return the number of edges in the graph.
        
        Returns:
            int: Number of edges
        """
        return self._graph.num_edges()
        
    def nodes_with_data(self, data=True):
        """Return nodes with their data.
        
        Args:
            data: If True, return node data as well
            
        Returns:
            Iterator: Iterator of (node, data) pairs if data=True, else just nodes
        """
        if data:
            for idx in self._graph.node_indices():
                node_data = self._graph.get_node_data(idx)
                yield (idx, node_data if isinstance(node_data, dict) else {})
        else:
            for idx in self._graph.node_indices():
                yield idx
    
    def subgraph(self, node, renumber=True):
        """Extract a subgraph starting from a given node.
        
        Args:
            node: The node to use as the starting point of the subgraph
            renumber: Whether to renumber the nodes in the new graph
            
        Returns:
            Graph: A new Graph object representing the subgraph
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in graph")
            
        descendants = [node] + list(self.descendants(node))
        
        subgraph_rx = self._graph.subgraph(descendants)
        
        return self._from_graph(subgraph_rx, renumber=renumber)
    
    @property
    def root_nodes(self):
        """Returns root nodes (nodes with no predecessors)"""
        root_indices = []
        
        if hasattr(self._graph, 'in_degree'):
            for idx in self._graph.node_indices():
                if self._graph.in_degree(idx) == 0:
                    root_indices.append(idx)
        else:
            if self._graph.num_nodes() == 0:
                return tuple()
            
            degrees = [(idx, self._graph.degree(idx)) for idx in self._graph.node_indices()]
            if degrees:
                min_deg_nodes = [idx for idx, deg in degrees if deg > 0]
                if min_deg_nodes:
                    root_indices = [min(min_deg_nodes)]
        
        return tuple(root_indices)
    
    def add_node(self, **attr):
        """Add a node to the graph.
        
        Args:
            **attr: Node attributes
            
        Returns:
            The node ID that was added
        """
        node_id = self._graph.add_node(attr if attr else {})
        self._invalidate_caches()
        return node_id
    
    def set_node_data(self, node, **attr):
        """Update data for an existing node.
        
        Args:
            node: The node to update
            **attr: Node attributes to set
        """
        if not self._graph.has_node(node):
            raise KeyError(f"Node {node} not found in graph")
        
        existing_data = self._graph.get_node_data(node)
        if existing_data is None:
            new_data = attr.copy()
            node_data = {}
            node_data.update(attr)
            self._graph.remove_node(node)
            new_node_id = self._graph.add_node(attr)
            if new_node_id != node:
                raise RuntimeError(f"Expected node ID {node}, got {new_node_id}")
        elif not isinstance(existing_data, dict):
            raise ValueError(f"Cannot update non-dict node data for node {node}. Node data type: {type(existing_data)}")
        else:
            existing_data.update(attr)
        
        self._invalidate_caches()
    
    def remove_node(self, node):
        """Remove a node from the graph."""
        self._graph.remove_node(node)
        self._invalidate_caches()
        
    def add_edge(self, u, v, **attr):
        """Add an edge to the graph with optional attributes."""
        if not self._graph.has_node(u):
            raise KeyError(f"Node {u} not found in graph")
        if not self._graph.has_node(v):
            raise KeyError(f"Node {v} not found in graph")
        
        self._graph.add_edge(u, v, attr if attr else {})
        self._invalidate_caches()
        
    def has_edge(self, u, v):
        """Check if an edge exists between two nodes."""
        return self._graph.has_edge(u, v)
        
    def remove_edge(self, u, v):
        """Remove an edge from the graph."""
        self._graph.remove_edge(u, v)
        self._invalidate_caches()
        
    def update(self, edges=None, nodes=None):
        """Update the graph with nodes and edges."""
        if nodes:
            for node_data in nodes:
                if isinstance(node_data, tuple) and len(node_data) == 2:
                    node, attrs = node_data
                    self.add_node(node, **attrs)
                else:
                    self.add_node(node_data)
        
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
        self._graph.clear()
        self._invalidate_caches()
    
    def set_node_attributes(self, node, attributes):
        """Set attributes for a node."""
        current_data = self._graph.get_node_data(node)
        if not isinstance(current_data, dict):
            current_data = {}
        current_data.update(attributes)
    
    def clear_node_attributes(self, nodes=None):
        """Clear attributes of specified nodes or all nodes.
        
        Args:
            nodes: Specific nodes to clear attributes for, or None for all nodes
        """
        nodes_to_clear = nodes if nodes is not None else self._graph.node_indices()
        for node in nodes_to_clear:
            if node in self:
                self._graph[node] = {}
        
    def renumber_nodes(self, method='default'):
        """Renumber the nodes in the graph to consecutive integers.
        
        Args:
            method (str): The method to use for renumbering:
                - 'default': Use sequential numbering
                - 'dfs': Use depth-first search preorder
                - 'bfs': Use breadth-first search
                
        Returns:
            Graph: Self with renumbered nodes
        """
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
        return isinstance(self._graph, rx.PyDiGraph)
    
    def is_multigraph(self):
        """Return True if graph is a multigraph, False otherwise."""
        return False
    
    def to_networkx(self):
        """Convert this Graph to a NetworkX graph for compatibility with NetworkX functions.
        
        Returns:
            networkx.Graph or networkx.DiGraph: NetworkX equivalent of this graph
        """
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
    def _from_graph(cls, G, **kwargs):
        """Create a new instance from an existing graph.
        
        Args:
            G: The graph to create a new instance from
            **kwargs: Additional arguments
            
        Returns:
            Graph: A new Graph instance
        """
        if isinstance(G, Graph):
            new_graph = cls.from_rustworkx(G._graph)
            new_graph._meta = copy.deepcopy(G._meta)
            return new_graph
        if isinstance(G, (rx.PyGraph, rx.PyDiGraph)):
            return cls.from_rustworkx(G)
        raise TypeError(f"Unsupported graph type: {type(G)}")
    
    @classmethod
    def grid_graph(cls, dims, periodic=False):
        """Create a grid graph with dimensions specified in dims.
        
        Creates a grid graph where nodes are numbered sequentially 0, 1, 2, ...
        and node data contains the coordinate as a tuple.
        
        Parameters
        ----------
        dims : list or tuple
            List of ranges or iterables defining the coordinate space for each dimension.
        periodic : bool, optional
            Whether to create periodic boundary conditions (default is False)
            
        Returns
        -------
        Graph
            A new Graph instance with grid structure and coordinate data in nodes
        """
        if not dims or len(dims) == 0:
            return cls()
        
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
            import itertools
            for i, coord in enumerate(itertools.product(dims[0], dims[1])):
                rx_graph[i] = {'coord': coord}
        else:
            rx_graph = rx.PyGraph()
            
            import itertools
            all_coords = list(itertools.product(*dims))
            
            node_indices = rx_graph.add_nodes_from([{'coord': coord} for coord in all_coords])
            coord_to_index = {coord: i for i, coord in enumerate(all_coords)}
            
            edge_list = []
            for coord in all_coords:
                coord_idx = coord_to_index[coord]
                
                for dim_idx in range(len(coord)):
                    for direction in [-1, 1]:
                        neighbor_coord = list(coord)
                        neighbor_coord[dim_idx] += direction
                        neighbor_coord = tuple(neighbor_coord)
                        
                        if neighbor_coord in coord_to_index:
                            neighbor_idx = coord_to_index[neighbor_coord]
                            if coord_idx < neighbor_idx:
                                edge_list.append((coord_idx, neighbor_idx))
                        elif periodic:
                            dim_values = dims[dim_idx]
                            if direction == 1 and coord[dim_idx] == dim_values[-1]:
                                wrap_coord = list(coord)
                                wrap_coord[dim_idx] = dim_values[0]
                                wrap_coord = tuple(wrap_coord)
                                if wrap_coord in coord_to_index:
                                    wrap_idx = coord_to_index[wrap_coord]
                                    if coord_idx < wrap_idx:
                                        edge_list.append((coord_idx, wrap_idx))
                            elif direction == -1 and coord[dim_idx] == dim_values[0]:
                                wrap_coord = list(coord)
                                wrap_coord[dim_idx] = dim_values[-1]
                                wrap_coord = tuple(wrap_coord)
                                if wrap_coord in coord_to_index:
                                    wrap_idx = coord_to_index[wrap_coord]
                                    if coord_idx < wrap_idx:
                                        edge_list.append((coord_idx, wrap_idx))
            
            if edge_list:
                rx_graph.extend_from_edge_list(edge_list)
        
        return cls.from_rustworkx(rx_graph)
    
    @classmethod
    def complete_graph(cls, n_nodes, labels: Optional[List[Any]] = None, directed: bool = False, node_key: str = 'label'):
        """Create a complete graph.
        
        Args:
            n_nodes: Number of nodes in the complete graph
            
        Returns:
            Graph: A new Graph instance with complete structure
        """
        if n_nodes < 0:
            raise ValueError("n_nodes must be >= 0")
        resolved_labels = cls._resolve_labels(n_nodes, labels)
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
        return cls.from_nodes_edges(
            nodes=[(label, {node_key: label}) for label in resolved_labels],
            edges=edges,
            directed=directed,
            node_mode='label',
            node_key=node_key,
        )
    
    @classmethod
    def from_cost_matrix(cls, cost_matrix: np.ndarray, items: List[T]):
        """Create a Graph from a cost matrix.
        
        Transform a symmetric cost matrix into an undirected graph where
        edge weights represent the costs between nodes. Self-loops are
        excluded from the resulting graph.

        Parameters
        ----------
        cost_matrix : numpy.ndarray
            Symmetric cost matrix with numeric values. Should be square
            with dimensions matching the length of items.
        items : List[T]
            List of items corresponding to matrix indices. Used as node
            values in the resulting graph.

        Returns
        -------
        Graph
            Undirected graph with nodes corresponding to matrix indices
            and edge weights equal to the cost matrix values. Only edges
            with positive costs are included. Node attributes 'value' 
            contain the original items.

        Examples
        --------
        Create a graph from a simple cost matrix:
        
        >>> import numpy as np
        >>> matrix = np.array([[0, 1, 2], [1, 0, 3], [2, 3, 0]])
        >>> items = ['A', 'B', 'C']
        >>> graph = Graph.from_cost_matrix(matrix, items)
        >>> list(graph.edges(data=True))
        [('A', 'B', {'weight': 1}), ('A', 'C', {'weight': 2}), ('B', 'C', {'weight': 3})]
        """
        graph = cls()
        
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
            graph._graph.add_edges_from(edge_list)
        
        return graph
    
    def __deepcopy__(self, memo):
        new_graph = self.__class__.__new__(self.__class__)
        
        new_graph._graph = self._graph.copy()
        new_graph._meta = copy.deepcopy(self._meta, memo)
        new_graph._structure_version = 0
        
        return new_graph


class GraphNodeView:
    """View of graph nodes that mimics NetworkX NodeView behavior."""
    
    def __init__(self, graph: Graph):
        self._graph = graph
    
    def __iter__(self):
        return iter(self._graph._graph.node_indices())
    
    def __len__(self):
        return self._graph.number_of_nodes()
    
    def __contains__(self, node):
        return self._graph._graph.has_node(node)
    
    def __getitem__(self, node):
        node_data = self._graph._graph.get_node_data(node)
        return node_data if isinstance(node_data, dict) else {}
    
    def __call__(self, data=False):
        """Return nodes with optional data."""
        if data:
            for idx in self._graph._graph.node_indices():
                node_data = self._graph._graph.get_node_data(idx)
                yield (idx, node_data if isinstance(node_data, dict) else {})
        else:
            for idx in self._graph._graph.node_indices():
                yield idx


class GraphEdgeView:
    """View of graph edges that mimics NetworkX EdgeView behavior."""
    
    def __init__(self, graph: Graph):
        self._graph = graph
    
    def __iter__(self):
        for edge_data in self._graph._graph.edge_list():
            src_idx, tgt_idx = edge_data
            yield (src_idx, tgt_idx)
    
    def __len__(self):
        return self._graph.number_of_edges()
    
    def __call__(self, data=False):
        """Return edges with optional data."""
        if data:
            for src_idx, tgt_idx in self._graph._graph.edge_list():
                edge_data = self._graph._graph.get_edge_data(src_idx, tgt_idx)
                yield (src_idx, tgt_idx, edge_data if isinstance(edge_data, dict) else {})
        else:
            for src_idx, tgt_idx in self._graph._graph.edge_list():
                yield (src_idx, tgt_idx)
    
    def __getitem__(self, edge):
        """Get edge data for a given edge (u, v)."""
        u, v = edge
        edge_data = self._graph._graph.get_edge_data(u, v)
        return edge_data if isinstance(edge_data, dict) else {}
    