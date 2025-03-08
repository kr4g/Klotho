from ..graphs import Graph
import networkx as nx
from itertools import count
import pandas as pd
from collections import deque

class Tree(Graph):
    def __init__(self, root, children:tuple):
        super().__init__(self._graph_tree(root, children))
        self._root = [n for n, d in self.graph.in_degree() if d == 0][0]
        self._leaf_nodes = [n for n in nx.dfs_preorder_nodes(self.graph) if self._graph.out_degree(n) == 0]
        self._list = (self._graph.nodes[self.root]['label'], children)
        self._meta['depth'] = max(nx.single_source_shortest_path_length(self.graph, self._root).values())
        self._meta['k'] = max((self.graph.out_degree(n) for n in self.graph.nodes), default=0)
    
    def __iter__(self):
        yield self._graph.nodes[self.root]['label']
        yield self._list[1]
    
    def __tuple__(self):
        return self._list
    
    def __call__(self):
        return self._list

    @property
    def root(self):
        return self._root
    
    @property
    def leaf_nodes(self):
        """Returns leaf nodes in depth-first order"""
        return self._leaf_nodes
        
    @property
    def depth(self):
        return self._meta['depth'].iloc[0]
    
    @property
    def k(self):
        return self._meta['k'].iloc[0]
            
    def parent(self, node):
        return next(self.graph.predecessors(node), None)

    def branch(self, node):
        """The highest ancestor of a node, not including the root."""
        if node is None:
            return None

        if self.parent(node) is None:
            return None

        current = node
        while self.parent(current) is not None:
            if self.parent(self.parent(current)) is None:
                return current
            current = self.parent(current)
            
        return current
    
    def siblings(self, node):
        return tuple(self.graph.successors(self.parent(node)))
    
    def successors(self, node):
        return tuple(self.graph.successors(node))
    
    def descendants(self, node):
        """Returns all descendants of a node in depth-first order.
        
        Args:
            node: The node whose descendants to return
            
        Returns:
            tuple: All descendants of the node in depth-first order
        """
        descendants = list(nx.dfs_preorder_nodes(self.graph, node))
        return tuple(descendants[1:])
    
    def subtree(self, node, renumber=True):
        """Extract a subtree starting from a given node.
        
        Args:
            node: The node to use as the root of the subtree
            
        Returns:
            Tree: A new Tree object representing the subtree
        """
        if node not in self.graph:
            raise ValueError(f"Node {node} not found in graph")
            
        descendants = [node] + list(self.descendants(node))
        subgraph = self.graph.subgraph(descendants).copy()
        
        new_tree = self._from_graph(subgraph, renumber=renumber)
        
        return new_tree

    def at_depth(self, n, operator='=='):
        """Returns nodes filtered by depth using the specified operator
        
        Args:
            n (int): The depth to compare against
            operator (str): One of '==', '<', '<=', '>', '>='
            
        Returns:
            tuple: Nodes at the specified depth, ordered from left to right
        """
        ops = {
            '==': lambda x, y: x == y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y,
            '>': lambda x, y: x > y,
            '>=': lambda x, y: x >= y
        }
        
        if operator not in ops:
            raise ValueError(f"Operator must be one of {list(ops.keys())}")
        
        nodes_at_depth = [node for node, depth in nx.single_source_shortest_path_length(self.graph, 0).items() 
                if ops[operator](depth, n)]
        
        bfs_order = list(nx.bfs_tree(self.graph, 0).nodes())
        nodes_at_depth.sort(key=lambda x: bfs_order.index(x))
        
        return tuple(nodes_at_depth)

    def _add_nodes(self, graph, parent_id, children_list, unique_id):        
        for child in children_list:
            match child:
                case tuple((D, S)):
                    duration_id = next(unique_id)
                    graph.add_node(duration_id, label=D)
                    graph.add_edge(parent_id, duration_id)
                    self._add_nodes(graph, duration_id, S, unique_id)
                case Tree():
                    duration_id = next(unique_id)
                    graph.add_node(duration_id, label=graph.nodes[child.root]['label'], meta=child._meta.to_dict('records')[0])
                    graph.add_edge(parent_id, duration_id)
                    self._add_nodes(graph, duration_id, child._children, unique_id)
                case _:
                    child_id = next(unique_id)
                    graph.add_node(child_id, label=child)
                    graph.add_edge(parent_id, child_id)
    
    def _graph_tree(self, root, children) -> nx.DiGraph:
        unique_id = count()
        G = nx.DiGraph()
        root_id = next(unique_id)
        G.add_node(root_id, label=root)
        self._add_nodes(G, root_id, children, unique_id)
        return G
    
    @classmethod
    def _from_graph(cls, G, clear_attributes=False, renumber=True):
        root_node = [n for n, d in G.in_degree() if d == 0]
        if len(root_node) != 1:
            raise ValueError("Graph must have exactly one root node.")
        
        root_id = root_node[0]
        root_label = None if clear_attributes else G.nodes[root_id].get('label')
        
        tree = cls.__new__(cls)
        Graph.__init__(tree, G.copy())
        
        tree._root = [n for n, d in tree.graph.in_degree() if d == 0][0]
        tree._leaf_nodes = [n for n in nx.dfs_preorder_nodes(tree.graph) if tree._graph.out_degree(n) == 0]
        
        def _build_children(node_id):
            children = list(G.successors(node_id))
            if not children:
                return None if clear_attributes else G.nodes[node_id].get('label')
            
            result = []
            for child_id in children:
                child_label = None if clear_attributes else G.nodes[child_id].get('label')
                child_tuple = _build_children(child_id)
                
                if isinstance(child_tuple, tuple):
                    result.append((child_label, child_tuple))
                else:
                    result.append(child_label)
            
            return tuple(result) if len(result) > 1 else (result[0],)
        
        children = _build_children(root_id)
        tree._list = (root_label, children)
        
        tree._meta['depth'] = max(nx.single_source_shortest_path_length(tree.graph, tree._root).values())
        tree._meta['k'] = max((tree.graph.out_degree(n) for n in tree.graph.nodes), default=0)
        
        if clear_attributes:
            for node in tree._graph.nodes:
                tree._graph.nodes[node].clear()
                tree._graph.nodes[node]['label'] = None

        return tree