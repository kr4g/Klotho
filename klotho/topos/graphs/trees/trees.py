from ..graphs import Graph
import networkx as nx
from functools import cached_property, lru_cache
# from ....utils.data_structures.group import Group
from klotho.utils.data_structures import Group


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
    
    def _invalidate_caches(self):
        """Invalidate all tree caches"""
        super()._invalidate_caches()
        for attr in ['depth', 'k', 'leaf_nodes']:
            if attr in self.__dict__:
                delattr(self, attr)
        if hasattr(self, 'parent'):
            self.parent.cache_clear()
    
    @cached_property
    def depth(self):
        """Maximum depth of the tree"""
        return max(nx.single_source_shortest_path_length(self._graph, self._root).values())
    
    @cached_property
    def k(self):
        """Maximum branching factor of the tree"""
        return max((self.out_degree(n) for n in self.nodes), default=0)
    
    @cached_property
    def leaf_nodes(self):
        """Returns leaf nodes (nodes with no successors)"""
        return tuple(n for n in nx.dfs_preorder_nodes(self._graph) if self.out_degree(n) == 0)

    def depth_of(self, node):
        """Returns the depth of a node in the tree.
        
        Args:
            node: The node to get the depth of
            
        Returns:
            int: The depth of the node
        """
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in tree")
        return nx.shortest_path_length(self._graph, self.root, node)

    @lru_cache(maxsize=None)
    def parent(self, node):
        """Returns the parent of a node.
        
        Args:
            node: The node to get the parent of
            
        Returns:
            int: The parent node, or None if the node is the root
        """
        parents = list(self.predecessors(node))
        return parents[0] if parents else None

    def branch(self, node):
        """Return all nodes on the branch from the root to the given node.
        
        Args:
            node: The target node
            
        Returns:
            tuple: All nodes from root to the given node (inclusive)
        """
        if node not in self._graph:
            raise ValueError(f"Node {node} not found in tree")
            
        if node == self.root:
            return (self.root,)
        
        path = nx.shortest_path(self._graph, self.root, node)
        return tuple(path)

    def siblings(self, node):
        """Returns the siblings of a node (nodes with the same parent)."""
        parent = self.parent(node)
        return tuple(n for n in self.successors(parent) if n != node) if parent else tuple()

    def subtree(self, node, renumber=True):
        """Extract a subtree rooted at the given node."""
        return super().subgraph(node, renumber=renumber)

    def at_depth(self, n, operator='=='):
        """Return nodes at a specific depth.
        
        Args:
            n: The depth level to query
            operator: Comparison operator ('==', '>=', '<=', '<', '>')
            
        Returns:
            list: Nodes satisfying the depth condition
        """
        depth_dict = nx.single_source_shortest_path_length(self._graph, self.root)
        
        if operator == '==':
            nodes_at_depth = [node for node, depth in depth_dict.items() if depth == n]
        elif operator == '>=':
            nodes_at_depth = [node for node, depth in depth_dict.items() if depth >= n]
        elif operator == '<=':
            nodes_at_depth = [node for node, depth in depth_dict.items() if depth <= n]
        elif operator == '<':
            nodes_at_depth = [node for node, depth in depth_dict.items() if depth < n]
        elif operator == '>':
            nodes_at_depth = [node for node, depth in depth_dict.items() if depth > n]
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        # Sort by breadth-first order to maintain consistent ordering
        bfs_order = list(nx.bfs_tree(self._graph, self.root).nodes())
        nodes_at_depth.sort(key=lambda x: bfs_order.index(x))
        
        return nodes_at_depth

    def add_node(self, **attr):
        """Add a node to the tree"""
        raise NotImplementedError("Use add_child() to add nodes to a tree")

    def add_edge(self, u, v, **attr):
        """Add an edge to the tree"""
        raise NotImplementedError("Use add_child() to add edges to a tree")

    def remove_node(self, node):
        """Remove a node and its subtree"""
        raise NotImplementedError("Use prune() or remove_subtree() to remove nodes from a tree")

    def remove_edge(self, u, v):
        """Remove an edge from the tree"""
        raise NotImplementedError("Use prune() or remove_subtree() to remove edges from a tree")

    def add_child(self, parent, index=None, **attr):
        """Add a child node to a parent.
        
        Args:
            parent: The parent node ID
            index: Position to insert child (None for append)
            **attr: Node attributes
            
        Returns:
            int: The new child node ID
        """
        child_id = super().add_node(**attr)
        super().add_edge(parent, child_id)
        return child_id

    def add_subtree(self, parent, subtree, index=None):
        """Add a subtree as a child of a parent node.
        
        Args:
            parent: The parent node to attach to
            subtree: Tree instance to attach
            index: Position to insert subtree (None for append)
            
        Returns:
            int: The root ID of the attached subtree
        """
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")
        
        node_mapping = {}
        
        # Add all nodes from subtree
        for node in subtree.nodes:
            new_id = super().add_node(**subtree[node])
            node_mapping[node] = new_id
        
        # Add all edges from subtree
        for u, v in subtree.edges:
            super().add_edge(node_mapping[u], node_mapping[v])
        
        # Connect subtree root to parent
        subtree_root = node_mapping[subtree.root]
        super().add_edge(parent, subtree_root)
        
        self._invalidate_caches()
        return subtree_root

    def prune(self, node):
        """Remove a node and promote its children to its parent.
        
        Args:
            node: The node to remove
        """
        if node == self.root:
            raise ValueError("Cannot prune the root node")
        
        parent = self.parent(node)
        children = list(self.successors(node))
        
        # Connect children to grandparent
        for child in children:
            super().add_edge(parent, child)
        
        # Remove the node
        super().remove_node(node)

    def remove_subtree(self, node):
        """Remove a node and its entire subtree.
        
        Args:
            node: The root of the subtree to remove
        """
        if node == self.root:
            raise ValueError("Cannot remove the root node")
        
        # Get all nodes in subtree
        subtree_nodes = [node] + list(self.descendants(node))
        
        # Remove all nodes
        for n in subtree_nodes:
            super().remove_node(n)

    def replace_node(self, old_node, **attr):
        """Replace a node with new attributes while preserving structure.
        
        Args:
            old_node: The node to replace
            **attr: New attributes for the node
            
        Returns:
            int: The new node ID
        """
        parent = self.parent(old_node)
        children = list(self.successors(old_node))
        
        # Create new node
        new_node = super().add_node(**attr)
        
        # Connect to parent (if exists)
        if parent is not None:
            super().add_edge(parent, new_node)
        else:
            # This is the root node
            self._root = new_node
        
        # Connect to children
        for child in children:
            super().add_edge(new_node, child)
        
        # Remove old node
        super().remove_node(old_node)
        
        return new_node

    def graft_subtree(self, node, subtree, handle_children='adopt'):
        """Replace a node with a subtree.
        
        Args:
            node: The node to replace
            subtree: Tree instance to graft
            handle_children: How to handle existing children ('adopt', 'discard', 'error')
            
        Returns:
            int: The root ID of the grafted subtree
        """
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")
        
        children = list(self.successors(node))
        
        if children and handle_children == 'error':
            raise ValueError(f"Node {node} has children and handle_children='error'")
        
        parent = self.parent(node)
        
        # Add the subtree
        if parent is not None:
            new_root = self.add_subtree(parent, subtree)
            
            if children and handle_children == 'adopt':
                # Move children to appropriate node in subtree
                for child in children:
                    super().add_edge(new_root, child)
            
            # Remove original node
            super().remove_node(node)
        else:
            # Replacing root
            node_mapping = {}
            
            # Add all nodes from subtree
            for n in subtree.nodes:
                new_id = super().add_node(**subtree[n])
                node_mapping[n] = new_id
            
            # Add all edges from subtree
            for u, v in subtree.edges:
                super().add_edge(node_mapping[u], node_mapping[v])
            
            new_root = node_mapping[subtree.root]
            
            if children and handle_children == 'adopt':
                for child in children:
                    super().add_edge(new_root, child)
            
            # Remove original root and update
            super().remove_node(node)
            self._root = new_root
        
        self._invalidate_caches()
        return new_root if parent else self._root

    def move_subtree(self, node, new_parent, index=None):
        """Move a subtree to a new parent.
        
        Args:
            node: Root of subtree to move
            new_parent: New parent node
            index: Position under new parent (None for append)
        """
        if node == self.root:
            raise ValueError("Cannot move the root node")
        
        old_parent = self.parent(node)
        
        # Remove edge from old parent
        super().remove_edge(old_parent, node)
        
        # Add edge to new parent
        super().add_edge(new_parent, node)
        
        self._invalidate_caches()

    def _build_tree(self, root, children):
        """Build the tree structure from nested tuples."""
        root_id = super().add_node(label=root)
        self._add_children(root_id, children)
        return root_id

    def _add_children(self, parent_id, children_list):
        for child in children_list:
            match child:
                case tuple((D, S)):
                    duration_id = super().add_node(label=D)
                    super().add_edge(parent_id, duration_id)
                    self._add_children(duration_id, S)
                case Tree():
                    duration_id = super().add_node(label=child._graph.nodes[child.root]['label'], 
                                               meta=child._meta.to_dict('records')[0])
                    super().add_edge(parent_id, duration_id)
                    self._add_children(duration_id, child.group.S)
                case _:
                    child_id = super().add_node(label=child)
                    super().add_edge(parent_id, child_id)
    
    @classmethod
    def _from_graph(cls, G, clear_attributes=False, renumber=True):
        """Create a Tree from a networkx graph.
        
        Args:
            G: NetworkX DiGraph
            clear_attributes: Whether to clear node attributes
            renumber: Whether to renumber nodes
            
        Returns:
            Tree: New Tree instance
        """
        if not isinstance(G, nx.DiGraph):
            raise TypeError("Tree graphs must be directed")
        
        def _build_children_list(node_id):
            children = list(G.successors(node_id))
            if not children:
                root_label = None if clear_attributes else G.nodes[node_id].get('label')
                return root_label if root_label is not None else node_id
            
            root_label = None if clear_attributes else G.nodes[node_id].get('label')
            root_label = root_label if root_label is not None else node_id
            
            child_structures = []
            for child_id in children:
                child_label = None if clear_attributes else G.nodes[child_id].get('label')
                child_label = child_label if child_label is not None else child_id
                
                child_structure = _build_children_list(child_id)
                if isinstance(child_structure, tuple):
                    child_structures.append(child_structure)
                else:
                    child_structures.append(child_structure)
            
            return (root_label, *child_structures)
        
        # Find root (node with no incoming edges)
        root_candidates = [n for n in G.nodes() if G.in_degree(n) == 0]
        if len(root_candidates) != 1:
            raise ValueError(f"Graph must have exactly one root node, found {len(root_candidates)}")
        
        root = root_candidates[0]
        root_label = None if clear_attributes else G.nodes[root].get('label')
        children_structure = _build_children_list(root)
        
        if isinstance(children_structure, tuple):
            tree = cls(children_structure[0], children_structure[1:])
        else:
            tree = cls(children_structure, tuple())
        
        if renumber:
            tree.renumber_nodes()
        
        return tree