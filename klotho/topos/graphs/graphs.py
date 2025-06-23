import networkx as nx
import hypernetx as hnx
import pandas as pd
from itertools import count


class Graph:
    def __init__(self, graph: nx.Graph = nx.Graph()):
        self._graph = graph
        self._meta = pd.DataFrame(index=[''])
        self._next_id = max(self._graph.nodes(), default=-1) + 1
   
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
    
    def predecessors(self, node):
        """Returns all predecessors of a node.
        
        Args:
            node: The node whose predecessors to return
            
        Returns:
            tuple: All predecessors of the node
        """
        return tuple(self._graph.predecessors(node))
    
    def successors(self, node):
        """Returns all successors of a node.
        
        Args:
            node: The node whose successors to return
            
        Returns:
            tuple: All successors of the node
        """
        return tuple(self._graph.successors(node))
    
    def descendants(self, node):
        """Returns all descendants of a node in depth-first order.
        
        Args:
            node: The node whose descendants to return
            
        Returns:
            tuple: All descendants of the node in depth-first order
        """
        descendants = list(nx.dfs_preorder_nodes(self._graph, node))
        return tuple(descendants[1:])  # Exclude the node itself
    
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
    def leaf_nodes(self):
        """Returns leaf nodes (nodes with no successors)"""
        return tuple(n for n in nx.dfs_preorder_nodes(self.graph) if self._graph.out_degree(n) == 0)
    
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
        
    def add_edge(self, u, v, **attr):
        """Add an edge to the graph with optional attributes."""
        self._graph.add_edge(u, v, **attr)
        
    def remove_edge(self, u, v):
        """Remove an edge from the graph."""
        self._graph.remove_edge(u, v)
        
    def update(self, edges=None, nodes=None):
        """Update the graph with nodes and edges."""
        self._graph.update(edges=edges, nodes=nodes)
        
    def clear(self):
        """Remove all nodes and edges from the graph."""
        self._graph.clear()
    
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
        copied = self._from_graph(self._graph.copy())
        copied._meta = self._meta.copy()
        copied._next_id = self._next_id
        return copied

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
    