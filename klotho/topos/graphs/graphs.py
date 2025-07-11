import networkx as nx
import hypernetx as hnx
from itertools import count
import copy
from functools import lru_cache


class Graph:
    def __init__(self, graph: nx.Graph = nx.Graph()):
        self._graph = graph
        self._meta = {}
        self._next_id = max(self._graph.nodes(), default=-1) + 1
        self._structure_version = 0
   
    @property
    def graph(self):
        return self._graph
   
    @property
    def nodes(self):
        return self._graph.nodes
    
    @property
    def edges(self):
        return self._graph.edges
    
    def __getitem__(self, node):
        return self._graph.nodes[node]
    
    def __len__(self):
        return len(self._graph)
    
    def __str__(self):
        return str(self._graph)
    
    def __repr__(self):
        return repr(self._graph)
    
    def __iter__(self):
        return iter(self._graph)
    
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
    
    @lru_cache(maxsize=None)
    def predecessors(self, node):
        """Returns all predecessors of a node.
        
        Args:
            node: The node whose predecessors to return
            
        Returns:
            tuple: All predecessors of the node
        """
        _ = self._structure_version
        return tuple(self._graph.predecessors(node))
    
    @lru_cache(maxsize=None)
    def successors(self, node):
        """Returns all successors of a node.
        
        Args:
            node: The node whose successors to return
            
        Returns:
            tuple: All successors of the node
        """
        _ = self._structure_version
        return tuple(self._graph.successors(node))
    
    @lru_cache(maxsize=None)
    def descendants(self, node):
        """Returns all descendants of a node in depth-first order.
        
        Args:
            node: The node whose descendants to return
            
        Returns:
            tuple: All descendants of the node in depth-first order
        """
        _ = self._structure_version
        descendants = list(nx.dfs_preorder_nodes(self._graph, node))
        return tuple(descendants[1:])
    
    @lru_cache(maxsize=None)
    def ancestors(self, node):
        """Returns all ancestors of a node.
        
        Args:
            node: The node whose ancestors to return
            
        Returns:
            tuple: All ancestors of the node
        """
        _ = self._structure_version
        try:
            if not self.root_nodes:
                return tuple()
            root = self.root_nodes[0]
            path = nx.shortest_path(self._graph, root, node)
            return tuple(path[:-1])
        except (nx.NetworkXNoPath, IndexError):
            return tuple()
    
    def subgraph(self, node, renumber=True):
        """Extract a subgraph starting from a given node.
        
        Args:
            node: The node to use as the starting point of the subgraph
            renumber: Whether to renumber the nodes in the new graph
            
        Returns:
            Graph: A new Graph object representing the subgraph
        """
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in graph")
            
        descendants = [node] + list(self.descendants(node))
        subgraph = self._graph.subgraph(descendants).copy()
        
        # implemented by subclasses
        return self._from_graph(subgraph, renumber=renumber)
    
    @property
    def root_nodes(self):
        """Returns root nodes (nodes with no predecessors)"""
        return tuple(n for n, d in self._graph.in_degree() if d == 0)
    
    def get_next_id(self):
        next_id = self._next_id
        self._next_id += 1
        return next_id
        
    def add_node(self, **attr):
        node_id = self.get_next_id()
        self._graph.add_node(node_id, **attr)
        return node_id
    
    def remove_node(self, node):
        """Remove a node from the graph."""
        self._graph.remove_node(node)
        self._invalidate_caches()
        
    def add_edge(self, u, v, **attr):
        """Add an edge to the graph with optional attributes."""
        self._graph.add_edge(u, v, **attr)
        self._invalidate_caches()
        
    def remove_edge(self, u, v):
        """Remove an edge from the graph."""
        self._graph.remove_edge(u, v)
        self._invalidate_caches()
        
    def update(self, edges=None, nodes=None):
        """Update the graph with nodes and edges."""
        self._graph.update(edges=edges, nodes=nodes)
        self._invalidate_caches()
        
    def clear(self):
        """Remove all nodes and edges from the graph."""
        self._graph.clear()
        self._invalidate_caches()
    
    def set_node_attributes(self, node, attributes):
        """Set attributes for a node."""
        for key, value in attributes.items():
            self._graph.nodes[node][key] = value
    
    def clear_node_attributes(self, nodes=None):
        """Clear attributes of specified nodes or all nodes.
        
        Args:
            nodes: Specific nodes to clear attributes for, or None for all nodes
        """
        nodes_to_clear = nodes if nodes is not None else self._graph.nodes
        for node in nodes_to_clear:
            if node in self._graph:
                self._graph.nodes[node].clear()
        
    def renumber_nodes(self, method='default'):
        """Renumber the nodes in the graph to consecutive integers.
        
        Args:
            method (str): The method to use for renumbering:
                - 'default': Use NetworkX's default renumbering
                - 'dfs': Use depth-first search preorder
                - 'bfs': Use breadth-first search
                
        Returns:
            Graph: Self with renumbered nodes
        """
        if method == 'default':
            mapping = {old: new for new, old in enumerate(self._graph.nodes())}
        elif method == 'dfs':
            roots = self.root_nodes
            if not roots:
                mapping = {old: new for new, old in enumerate(self._graph.nodes())}
            else:
                mapping = {old: new for new, old in enumerate(nx.dfs_preorder_nodes(self._graph, roots[0]))}
        elif method == 'bfs':
            roots = self.root_nodes
            if not roots:
                mapping = {old: new for new, old in enumerate(self._graph.nodes())}
            else:
                mapping = {old: new for new, old in enumerate(nx.bfs_tree(self._graph, roots[0]).nodes())}
        else:
            raise ValueError(f"Unknown renumbering method: {method}")
            
        self._graph = nx.relabel_nodes(self._graph, mapping)
        return self

    def copy(self):
        """Create a deep copy of this graph."""
        return copy.deepcopy(self)

    @classmethod
    def _from_graph(cls, G, **kwargs):
        """Create a new instance from an existing graph.
        
        Args:
            G: The graph to create a new instance from
            clear_attributes: Whether to clear node attributes
            renumber: Whether to renumber the nodes
            
        Returns:
            Graph: A new Graph instance
        """
        return cls(G)
    
    def __deepcopy__(self, memo):
        new_graph = self.__class__.__new__(self.__class__)
        
        for attr_name, attr_value in self.__dict__.items():
            setattr(new_graph, attr_name, copy.deepcopy(attr_value, memo))
        
        return new_graph
    