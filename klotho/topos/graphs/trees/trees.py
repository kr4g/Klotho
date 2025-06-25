from ..graphs import Graph
import networkx as nx
from itertools import count
import pandas as pd
from collections import deque
from ....utils.data_structures.group import Group


class Tree(Graph):
    def __init__(self, root, children:tuple):
        super().__init__(nx.DiGraph())
        self._root = self._build_tree(root, children)
        self._list = Group((root, children))
    
    @property
    def root(self):
        return self._root

    @property
    def group(self):
        return self._list
    
    @property
    def depth(self):
        return max(nx.single_source_shortest_path_length(self.graph, self._root).values())
    
    @property
    def k(self):
        return max((self.graph.out_degree(n) for n in self.graph.nodes), default=0)

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
            '==' : lambda x, y: x == y,
            '<'  : lambda x, y: x < y,
            '<=' : lambda x, y: x <= y,
            '>'  : lambda x, y: x > y,
            '>=' : lambda x, y: x >= y
        }
        
        if operator not in ops:
            raise ValueError(f"Operator must be one of {list(ops.keys())}")
        
        nodes_at_depth = [node for node, depth in nx.single_source_shortest_path_length(self.graph, self.root).items() 
                if ops[operator](depth, n)]
        
        bfs_order = list(nx.bfs_tree(self.graph, self.root).nodes())
        nodes_at_depth.sort(key=lambda x: bfs_order.index(x))
        
        return tuple(nodes_at_depth)

    def add_node(self, **attr):
        raise NotImplementedError("Cannot add disconnected node to a tree. Use add_child() instead.")
    
    def add_edge(self, u, v, **attr):
        raise NotImplementedError("Cannot add arbitrary edge to a tree. Use add_child() or add_subtree() instead.")
    
    def remove_node(self, node):
        raise NotImplementedError("Cannot remove arbitrary node from a tree. Use prune() or remove_subtree() instead.")
    
    def remove_edge(self, u, v):
        raise NotImplementedError("Cannot remove edge from a tree. Use prune() or remove_subtree() instead.")
    
    def add_child(self, parent, index=None, **attr):
        if parent not in self._graph:
            raise ValueError(f"Parent node {parent} not found in tree")
        
        node_id = super().add_node(**attr)
        
        if index is None or index >= len(list(self._graph.successors(parent))):
            self._graph.add_edge(parent, node_id)
        else:
            children = list(self._graph.successors(parent))
            self._graph.add_edge(parent, node_id)
            
            for i, child in enumerate(children):
                if i >= index:
                    self._graph.remove_edge(parent, child)
                    self._graph.add_edge(parent, child)
        
        return node_id
    
    def add_subtree(self, parent, subtree, index=None):
        if parent not in self._graph:
            raise ValueError(f"Parent node {parent} not found in tree")
        
        id_mapping = {}
        for node in subtree.graph.nodes():
            new_id = super().add_node(**subtree.graph.nodes[node])
            id_mapping[node] = new_id
        
        for u, v in subtree.graph.edges():
            self._graph.add_edge(id_mapping[u], id_mapping[v])
        
        if index is None or index >= len(list(self._graph.successors(parent))):
            self._graph.add_edge(parent, id_mapping[subtree.root])
        else:
            children = list(self._graph.successors(parent))
            self._graph.add_edge(parent, id_mapping[subtree.root])
            
            for i, child in enumerate(children):
                if i >= index:
                    self._graph.remove_edge(parent, child)
                    self._graph.add_edge(parent, child)
        
        return id_mapping
    
    def prune(self, node):
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in tree")
        
        if node == self.root and len(list(self._graph.successors(node))) > 0:
            raise ValueError("Cannot prune root with children")
            
        if self._graph.out_degree(node) > 0:
            raise ValueError(f"Node {node} is not a leaf node")
        
        parent = self.parent(node)
        if parent:
            self._graph.remove_edge(parent, node)
        self._graph.remove_node(node)
    
    def remove_subtree(self, node):
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in tree")
        
        if node == self.root:
            self.clear()
            return
        
        parent = self.parent(node)
        if parent:
            self._graph.remove_edge(parent, node)
        
        descendants = [node] + list(self.descendants(node))
        for n in descendants:
            self._graph.remove_node(n)
    
    def replace_node(self, old_node, **attr):
        if old_node not in self._graph:
            raise ValueError(f"Node {old_node} not found in tree")
        
        parent = self.parent(old_node)
        children = list(self._graph.successors(old_node))
        
        new_id = super().add_node(**attr)
        
        if parent:
            siblings = list(self._graph.successors(parent))
            old_index = siblings.index(old_node)
            self._graph.add_edge(parent, new_id)
            
            for i, child in enumerate(siblings):
                if i > old_index and child != old_node:
                    self._graph.remove_edge(parent, child)
                    self._graph.add_edge(parent, child)
        
        for child in children:
            self._graph.add_edge(new_id, child)
        
        self._graph.remove_node(old_node)
        
        if old_node == self._root:
            self._root = new_id
            
        return new_id
    
    def graft_subtree(self, node, subtree, handle_children='adopt'):
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in tree")
        
        if handle_children not in ('adopt', 'discard', 'distribute'):
            raise ValueError("handle_children must be 'adopt', 'discard', or 'distribute'")
        
        parent = self.parent(node)
        children = list(self._graph.successors(node))
        siblings = []
        
        if parent:
            siblings = list(self._graph.successors(parent))
            node_index = siblings.index(node)
        
        id_mapping = {}
        for n in subtree.graph.nodes():
            new_id = super().add_node(**subtree.graph.nodes[n])
            id_mapping[n] = new_id
        
        for u, v in subtree.graph.edges():
            self._graph.add_edge(id_mapping[u], id_mapping[v])
        
        if parent:
            self._graph.add_edge(parent, id_mapping[subtree.root])
            
            for i, sibling in enumerate(siblings):
                if i > node_index and sibling != node:
                    self._graph.remove_edge(parent, sibling)
                    self._graph.add_edge(parent, sibling)
        else:
            self._root = id_mapping[subtree.root]
        
        if handle_children == 'adopt':
            for child in children:
                self._graph.add_edge(id_mapping[subtree.root], child)
        elif handle_children == 'distribute':
            leaves = [n for n in id_mapping.values() 
                    if n != id_mapping[subtree.root] and self._graph.out_degree(n) == 0]
            
            if not leaves:
                for child in children:
                    self._graph.add_edge(id_mapping[subtree.root], child)
            else:
                for i, child in enumerate(children):
                    leaf_idx = i % len(leaves)
                    self._graph.add_edge(leaves[leaf_idx], child)
        
        self._graph.remove_node(node)
        
        return id_mapping
    
    def move_subtree(self, node, new_parent, index=None):
        if node not in self._graph or new_parent not in self._graph:
            raise ValueError("Node or new parent not found in tree")
            
        if node == self.root:
            raise ValueError("Cannot move root node")
            
        if node == new_parent or new_parent in self.descendants(node):
            raise ValueError("Cannot create a cycle in the tree")
        
        old_parent = self.parent(node)
        self._graph.remove_edge(old_parent, node)
        
        if index is None or index >= len(list(self._graph.successors(new_parent))):
            self._graph.add_edge(new_parent, node)
        else:
            children = list(self._graph.successors(new_parent))
            self._graph.add_edge(new_parent, node)
            
            for i, child in enumerate(children):
                if i >= index:
                    self._graph.remove_edge(new_parent, child)
                    self._graph.add_edge(new_parent, child)
        
    def _build_tree(self, root, children):
        root_id = super().add_node(label=root)
        self._add_children(root_id, children)
        return root_id
        
    def _add_children(self, parent_id, children_list):
        for child in children_list:
            match child:
                case tuple((D, S)):
                    duration_id = super().add_node(label=D)
                    self._graph.add_edge(parent_id, duration_id)
                    self._add_children(duration_id, S)
                case Tree():
                    duration_id = super().add_node(label=child._graph.nodes[child.root]['label'], 
                                               meta=child._meta.to_dict('records')[0])
                    self._graph.add_edge(parent_id, duration_id)
                    self._add_children(duration_id, child.group.S)
                case _:
                    child_id = super().add_node(label=child)
                    self._graph.add_edge(parent_id, child_id)
    
    def copy(self):
        """Create a deep copy of this tree."""
        copied = super().copy()
        copied._root = self._root
        copied._list = self._list
        return copied

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
        tree._list = Group((root_label, children))
        
        tree._meta['depth'] = max(nx.single_source_shortest_path_length(tree.graph, tree._root).values())
        tree._meta['k'] = max((tree.graph.out_degree(n) for n in tree.graph.nodes), default=0)
        
        if clear_attributes:
            tree.clear_node_attributes()

        return tree