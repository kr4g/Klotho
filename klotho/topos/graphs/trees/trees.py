import networkx as nx
from itertools import count
import pandas as pd

class Tree:
    def __init__(self, root, children:tuple):
        self._root = root
        self._children = children
        self._leaf_nodes = None
        self._graph = self._graph_tree()
        self._meta = pd.DataFrame([{
            'depth': max(nx.single_source_shortest_path_length(self.graph, 0).values()),
            'k': max((self.graph.out_degree(n) for n in self.graph.nodes), default=0)
        }], index=[''])
    
    @property
    def root(self):
        return self._root
    
    @property
    def children(self):
        return self._children
    
    @property
    def leaf_nodes(self):
        """Returns leaf nodes in depth-first order"""
        if self._leaf_nodes is None:
            self._leaf_nodes = [n for n in nx.dfs_preorder_nodes(self.graph) 
                if self._graph.out_degree(n) == 0]
        return self._leaf_nodes
    
    def __getitem__(self, node):
        return self.graph.nodes[node]
    
    @property
    def graph(self):
        return self._graph
    
    @property
    def depth(self):
        return self._meta['depth'].iloc[0]
    
    @property
    def k(self):
        return self._meta['k'].iloc[0]
    
    @property
    def nodes(self):
        return self.graph.nodes
    
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
    
    def at_depth(self, n, operator='=='):
        """Returns nodes filtered by depth using the specified operator
        
        Args:
            n (int): The depth to compare against
            operator (str): One of '==', '<', '<=', '>', '>='
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
            
        return tuple(node for node, depth in nx.single_source_shortest_path_length(self.graph, 0).items() 
                if ops[operator](depth, n))
    
    def _graph_tree(self) -> nx.DiGraph:
        def add_nodes(graph, parent_id, children_list):        
            for child in children_list:
                match child:
                    case tuple((D, S)):
                        duration_id = next(unique_id)
                        graph.add_node(duration_id, label=D)
                        graph.add_edge(parent_id, duration_id)
                        add_nodes(graph, duration_id, S)
                    case Tree():
                        duration_id = next(unique_id)
                        graph.add_node(duration_id, label=child.root, meta=child._meta.to_dict('records')[0])
                        graph.add_edge(parent_id, duration_id)
                        add_nodes(graph, duration_id, child._children)
                    case _:
                        child_id = next(unique_id)
                        graph.add_node(child_id, label=child)
                        graph.add_edge(parent_id, child_id)
        unique_id = count()
        G = nx.DiGraph()
        root_id = next(unique_id)
        G.add_node(root_id, label=self._root)
        add_nodes(G, root_id, self._children)
        return G
    
    @classmethod
    def from_graph(cls, G, clear_attributes=False):
        root_node = [n for n, d in G.in_degree() if d == 0]
        if len(root_node) != 1:
            raise ValueError("Graph must have exactly one root node.")
        
        root_id = root_node[0]
        root = None if clear_attributes else G.nodes[root_id].get('label')
        
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
        tree = cls(root, children)
        
        mapping = {new: old for new, old in zip(nx.dfs_preorder_nodes(tree.graph), nx.dfs_preorder_nodes(G))}
        tree._graph = nx.relabel_nodes(tree._graph, mapping)
        
        if clear_attributes:
            for node in tree._graph.nodes:
                tree._graph.nodes[node].clear()
                tree._graph.nodes[node]['label'] = None
            
        return tree
