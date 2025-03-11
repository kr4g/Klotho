from ..graphs import Graph
import networkx as nx
from itertools import count
import pandas as pd
from collections import deque

class Tree(Graph):
    def __init__(self, root, children:tuple):
        super().__init__(self._build_tree(root, children))
        self._root = self.root_nodes[0]
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
    def depth(self):
        return self._meta['depth'].iloc[0]
    
    @property
    def k(self):
        return self._meta['k'].iloc[0]

    def depth_of(self, node):
        """Returns the depth of a node in the tree.
        
        Args:
            node (int): The node to get the depth of
            
        Returns:
            int: The depth of the node
        """
        if node not in self.graph:
            raise ValueError(f"Node {node} not found in graph")
        return nx.shortest_path_length(self.graph, self.root, node)

    def parent(self, node):
        """Returns the parent of a node, or None if the node is the root."""
        predecessors = self.predecessors(node)
        return predecessors[0] if predecessors else None

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
        parent = self.parent(node)
        return self.successors(parent) if parent is not None else tuple()
    
    def subtree(self, node, renumber=True):
        """Extract a subtree starting from a given node.
        
        Args:
            node: The node to use as the root of the subtree
            renumber: Whether to renumber the nodes in the new tree
            
        Returns:
            Tree: A new Tree object representing the subtree
        """
        return self.subgraph(node, renumber=renumber)

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
        
        nodes_at_depth = [node for node, depth in nx.single_source_shortest_path_length(self.graph, self.root).items() 
                if ops[operator](depth, n)]
        
        bfs_order = list(nx.bfs_tree(self.graph, self.root).nodes())
        nodes_at_depth.sort(key=lambda x: bfs_order.index(x))
        
        return tuple(nodes_at_depth)

    def _add_children(self, graph, parent_id, children_list, unique_id):        
        for child in children_list:
            match child:
                case tuple((D, S)):
                    duration_id = next(unique_id)
                    graph.add_node(duration_id, label=D)
                    graph.add_edge(parent_id, duration_id)
                    self._add_children(graph, duration_id, S, unique_id)
                case Tree():
                    duration_id = next(unique_id)
                    graph.add_node(duration_id, label=graph.nodes[child.root]['label'], meta=child._meta.to_dict('records')[0])
                    graph.add_edge(parent_id, duration_id)
                    self._add_children(graph, duration_id, child._list[1], unique_id)
                case _:
                    child_id = next(unique_id)
                    graph.add_node(child_id, label=child)
                    graph.add_edge(parent_id, child_id)
    
    def _build_tree(self, root, children) -> nx.DiGraph:
        unique_id = count()
        G = nx.DiGraph()
        root_id = next(unique_id)
        G.add_node(root_id, label=root)
        self._add_children(G, root_id, children, unique_id)
        return G
    
    @classmethod
    def _from_graph(cls, G, clear_attributes=False, renumber=True):
        tree = cls.__new__(cls)
        Graph.__init__(tree, G.copy())
        
        if renumber:
            tree.renumber_nodes(method='dfs')
        
        root_nodes = tree.root_nodes
        if len(root_nodes) != 1:
            raise ValueError("Graph must have exactly one root node.")
        
        tree._root = root_nodes[0]
        root_label = None if clear_attributes else tree.graph.nodes[tree._root].get('label')
        
        def _build_children_list(node_id):
            children = list(tree.graph.successors(node_id))
            if not children:
                return None if clear_attributes else tree.graph.nodes[node_id].get('label')
            
            result = []
            for child_id in children:
                child_label = None if clear_attributes else tree.graph.nodes[child_id].get('label')
                child_tuple = _build_children_list(child_id)
                
                if isinstance(child_tuple, tuple):
                    result.append((child_label, child_tuple))
                else:
                    result.append(child_label)
            
            return tuple(result) if len(result) > 1 else (result[0],)
        
        children = _build_children_list(tree._root)
        tree._list = (root_label, children)
        
        tree._meta['depth'] = max(nx.single_source_shortest_path_length(tree.graph, tree._root).values())
        tree._meta['k'] = max((tree.graph.out_degree(n) for n in tree.graph.nodes), default=0)
        
        if clear_attributes:
            tree.clear_node_attributes()

        return tree
    