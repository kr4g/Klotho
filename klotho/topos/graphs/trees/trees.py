from ..graphs import Graph
import rustworkx as rx
from functools import cached_property, lru_cache
from klotho.utils.data_structures import Group
import copy


class Tree(Graph):
    def __init__(self, root, children:tuple):
        super().__init__(Graph.digraph()._graph)
        self._building_tree = True
        self._root = self._build_tree(root, children)
        self._building_tree = False
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
        """Maximum depth of the tree.
        
        Returns
        -------
        int
            The maximum depth of any node in the tree
        """
        if not hasattr(self, '_root') or self._root is None:
            return 0
        root_idx = self._get_node_index(self._root)
        if root_idx is None:
            return 0
        
        def edge_cost_fn(edge_data):
            return 1.0
        
        distances = rx.digraph_dijkstra_shortest_path_lengths(
            self._graph, root_idx, edge_cost_fn
        )
        
        return int(max(distances.values())) if distances else 0
    
    @cached_property
    def k(self):
        """Maximum branching factor of the tree"""
        return max((self.out_degree(n) for n in self.nodes), default=0)
    
    @cached_property
    def leaf_nodes(self):
        """Return leaf nodes (nodes with no successors) in tree traversal order.
        
        Returns
        -------
        tuple
            All leaf nodes in the tree, in left-right traversal order
        """
        leaf_nodes_list = []
        
        def collect_leaves(node):
            if self.out_degree(node) == 0:
                leaf_nodes_list.append(node)
            else:
                for child in self.successors(node):
                    collect_leaves(child)
        
        collect_leaves(self.root)
        return tuple(leaf_nodes_list)

    def depth_of(self, node):
        """Return the depth of a node in the tree.
        
        The depth is the length of the path from the root to the node.
        
        Parameters
        ----------
        node : int
            The node to get the depth of
            
        Returns
        -------
        int
            The depth of the node (0 for root)
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        
        root_idx = self._get_node_index(self._root)
        node_idx = self._get_node_index(node)
        
        if root_idx == node_idx:
            return 0
        
        depth = 0
        current = node_idx
        
        while current != root_idx:
            parents = list(self._graph.predecessor_indices(current))
            if not parents:
                raise ValueError(f"Node {node} is not reachable from root")
            current = parents[0]
            depth += 1
        
        return depth

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

    @lru_cache(maxsize=None)
    def ancestors(self, node):
        """Return all ancestors of a node in the tree.
        
        Parameters
        ----------
        node : int
            The node whose ancestors to return
            
        Returns
        -------
        tuple
            All ancestors from root to parent (excluding the node itself)
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
            
        if node == self._root:
            return tuple()
        
        root_idx = self._get_node_index(self._root)
        node_idx = self._get_node_index(node)
        
        ancestor_indices = []
        current = node_idx
        
        while current != root_idx:
            parents = list(self._graph.predecessor_indices(current))
            if not parents:
                raise ValueError(f"Node {node} is not reachable from root")
            current = parents[0]
            ancestor_indices.append(current)
        
        ancestor_indices.reverse()
        return tuple(self._get_node_object(ai) for ai in ancestor_indices)

    @lru_cache(maxsize=None)
    def descendants(self, node):
        """Return all descendants of a node in depth-first order.
        
        Parameters
        ----------
        node : int
            The node whose descendants to return
            
        Returns
        -------
        tuple
            All descendants of the node in depth-first order
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        
        node_idx = self._get_node_index(node)
        
        dfs_edges = rx.dfs_edges(self._graph, node_idx)
        
        descendant_indices = []
        visited = {node_idx}
        
        for src, tgt in dfs_edges:
            if src == node_idx or src in visited:
                if tgt not in visited:
                    descendant_indices.append(tgt)
                    visited.add(tgt)
        
        return tuple(self._get_node_object(di) for di in descendant_indices)

    @lru_cache(maxsize=None)
    def branch(self, node):
        """Return all nodes on the branch from the root to the given node.
        
        Parameters
        ----------
        node : int
            The target node
            
        Returns
        -------
        tuple
            All nodes from root to the given node (inclusive)
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
            
        if node == self._root:
            return (self._root,)
        
        root_idx = self._get_node_index(self._root)
        node_idx = self._get_node_index(node)
        
        branch_indices = []
        current = node_idx
        
        while current != root_idx:
            branch_indices.append(current)
            parents = list(self._graph.predecessor_indices(current))
            if not parents:
                return tuple()
            current = parents[0]
        
        branch_indices.append(root_idx)
        branch_indices.reverse()
        return tuple(self._get_node_object(idx) for idx in branch_indices)

    def siblings(self, node):
        """Returns the siblings of a node (nodes with the same parent)."""
        parent = self.parent(node)
        return tuple(n for n in self.successors(parent) if n != node) if parent else tuple()

    def subtree(self, node, renumber=True):
        """Extract a tree subtree rooted at the given node.
        
        Parameters
        ----------
        node : int
            The node to use as the root of the subtree
        renumber : bool, optional
            Whether to renumber the nodes in the new tree (default: True)
            
        Returns
        -------
        Tree
            A new Tree object representing the subtree containing the node 
            and all its descendants
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        descendants = [node] + list(self.descendants(node))
        
        new_tree = self.__class__.__new__(self.__class__)
        new_tree._graph = rx.PyDiGraph()
        new_tree._meta = self._meta.copy()
        new_tree._structure_version = 0
        
        node_mapping = {}
        for old_node in descendants:
            new_node_id = new_tree._graph.add_node(self[old_node].copy())
            node_mapping[old_node] = new_node_id
        
        for old_node in descendants:
            for successor in self.successors(old_node):
                if successor in descendants:
                    new_tree._graph.add_edge(
                        node_mapping[old_node], 
                        node_mapping[successor], 
                        None
                    )
        
        new_tree._root = node_mapping[node]
        
        if hasattr(self, 'group'):
            def build_group_structure(root_node):
                children = [child for child in descendants if self.parent(child) == root_node]
                if not children:
                    return self[root_node].get('label', root_node)
                
                child_structures = []
                for child in sorted(children):
                    child_structure = build_group_structure(child)
                    child_structures.append(child_structure)
                
                root_label = self[root_node].get('label', root_node)
                return (root_label, tuple(child_structures))
            
            structure = build_group_structure(node)
            if isinstance(structure, tuple) and len(structure) > 1:
                from klotho.utils.data_structures import Group
                new_tree._list = Group(structure)
            else:
                from klotho.utils.data_structures import Group  
                new_tree._list = Group((structure, tuple()))
        
        if renumber:
            new_tree.renumber_nodes()
        
        return new_tree

    def at_depth(self, n, operator='=='):
        """Return nodes at a specific depth.
        
        Parameters
        ----------
        n : int
            The depth level to query
        operator : str, optional
            Comparison operator ('==', '>=', '<=', '<', '>'), default is '=='
            
        Returns
        -------
        list
            Nodes satisfying the depth condition in breadth-first order
            
        Raises
        ------
        ValueError
            If operator is not supported
        """
        if operator not in ['==', '>=', '<=', '<', '>']:
            raise ValueError(f"Unsupported operator: {operator}")
        
        all_levels = []
        current_level = [self.root]
        current_depth = 0
        
        while current_level and current_depth <= self.depth:
            all_levels.append(current_level[:])
            
            if current_depth >= self.depth:
                break
                
            next_level = []
            for node in current_level:
                for child in self.successors(node):
                    next_level.append(child)
            
            current_level = next_level
            current_depth += 1
        
        matching_nodes = []
        
        if operator == '==':
            if n < len(all_levels):
                matching_nodes = all_levels[n]
        elif operator == '>=':
            for depth, level in enumerate(all_levels):
                if depth >= n:
                    matching_nodes.extend(level)
        elif operator == '<=':
            for depth, level in enumerate(all_levels):
                if depth <= n:
                    matching_nodes.extend(level)
        elif operator == '<':
            for depth, level in enumerate(all_levels):
                if depth < n:
                    matching_nodes.extend(level)
        elif operator == '>':
            for depth, level in enumerate(all_levels):
                if depth > n:
                    matching_nodes.extend(level)
        
        return matching_nodes

    def add_node(self, **attr):
        """Add a node to the tree"""
        if getattr(self, '_building_tree', False):
            return Graph.add_node(self, **attr)
        raise NotImplementedError("Use add_child() to add nodes to a tree")

    def add_edge(self, u, v, **attr):
        """Add an edge to the tree"""
        if getattr(self, '_building_tree', False):
            return Graph.add_edge(self, u, v, **attr)
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
        self._building_tree = True
        try:
            child_id = super().add_node(**attr)
            super().add_edge(parent, child_id)
            return child_id
        finally:
            self._building_tree = False

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
        
        for node in subtree.nodes:
            new_id = Graph.add_node(self, **subtree[node])
            node_mapping[node] = new_id
        
        for u, v in subtree.edges:
            Graph.add_edge(self, node_mapping[u], node_mapping[v])
        
        subtree_root = node_mapping[subtree.root]
        Graph.add_edge(self, parent, subtree_root)
        
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
        
        for child in children:
            Graph.add_edge(self, parent, child)
        
        Graph.remove_node(self, node)

    def remove_subtree(self, node):
        """Remove a node and its entire subtree.
        
        Args:
            node: The root of the subtree to remove
        """
        if node == self.root:
            raise ValueError("Cannot remove the root node")
        
        subtree_nodes = [node] + list(self.descendants(node))
        
        for n in subtree_nodes:
            Graph.remove_node(self, n)

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
        
        new_node = Graph.add_node(self, **attr)
        
        if parent is not None:
            Graph.add_edge(self, parent, new_node)
        else:
            self._root = new_node
        
        for child in children:
            Graph.add_edge(self, new_node, child)
        
        Graph.remove_node(self, old_node)
        
        return new_node

    def _update_group_structure(self):
        """Update the Group structure based on current graph state.
        
        This method rebuilds the _list Group from the current tree structure.
        Subclasses can override this to preserve specific parts of the Group.
        """
        if hasattr(self, '_list'):
            def get_node_value(node):
                return self[node].get('label', node)
            
            def get_children(node):
                return list(self.successors(node))
            
            structure = self._build_nested_structure(self.root, get_node_value, get_children)
            if isinstance(structure, tuple) and len(structure) > 1:
                self._list = Group(structure)
            else:
                self._list = Group((structure, tuple()))

    def graft_subtree(self, target_node, subtree, mode='replace'):
        """Graft a subtree onto the tree at the specified leaf node.
        
        Parameters
        ----------
        target_node : int
            The leaf node where the subtree will be grafted
        subtree : Tree
            The Tree instance to graft onto this tree
        mode : str, optional
            Grafting mode - either 'replace' or 'adopt' (default: 'replace')
            - 'replace': Replace the leaf node with subtree root
            - 'adopt': Keep the leaf node and give it the children from subtree root
            
        Returns
        -------
        int
            The root node ID of the grafted subtree (for 'replace' mode) or
            the target_node ID (for 'adopt' mode)
            
        Raises
        ------
        TypeError
            If subtree is not a Tree instance
        ValueError
            If target_node is not found in the tree, is not a leaf node, or mode is invalid
        """
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")
        
        if target_node not in self:
            raise ValueError(f"Target node {target_node} not found in tree")
        
        if self.out_degree(target_node) > 0:
            raise ValueError(f"Target node {target_node} is not a leaf node. Can only graft to leaf nodes.")
        
        if mode not in ['replace', 'adopt']:
            raise ValueError(f"Invalid mode '{mode}'. Use 'replace' or 'adopt'")
        
        if mode == 'replace':
            return self._graft_replace_leaf(target_node, subtree)
        else:  # adopt
            return self._graft_adopt_leaf(target_node, subtree)
    
    def _graft_replace_leaf(self, target_node, subtree):
        """Replace the leaf node with the subtree root."""
        parent = self.parent(target_node)
        
        # Add all subtree nodes
        node_mapping = {}
        for node in subtree.nodes:
            new_id = Graph.add_node(self, **subtree[node])
            node_mapping[node] = new_id
        
        # Add all subtree edges
        for u, v in subtree.edges:
            Graph.add_edge(self, node_mapping[u], node_mapping[v])
        
        new_root = node_mapping[subtree.root]
        
        # Connect new root to parent (or make it the tree root)
        if parent is not None:
            Graph.add_edge(self, parent, new_root)
        else:
            self._root = new_root
        
        # Remove the target leaf node
        Graph.remove_node(self, target_node)
        
        self._invalidate_caches()
        self._update_group_structure()
        return new_root
    
    def _graft_adopt_leaf(self, target_node, subtree):
        """Keep the leaf node and give it the children from subtree root."""
        # Add all subtree nodes except the root
        subtree_nodes_except_root = [node for node in subtree.nodes if node != subtree.root]
        
        node_mapping = {}
        for node in subtree_nodes_except_root:
            new_id = Graph.add_node(self, **subtree[node])
            node_mapping[node] = new_id
        
        # Add edges between the mapped nodes (excluding edges from subtree root)
        for u, v in subtree.edges:
            if u != subtree.root and v != subtree.root:
                Graph.add_edge(self, node_mapping[u], node_mapping[v])
        
        # Connect target node to the children of subtree root
        subtree_root_children = list(subtree.successors(subtree.root))
        for child in subtree_root_children:
            Graph.add_edge(self, target_node, node_mapping[child])
        
        self._invalidate_caches()
        self._update_group_structure()
        return target_node

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
        
        Graph.remove_edge(self, old_parent, node)
        
        Graph.add_edge(self, new_parent, node)
        
        self._invalidate_caches()

    def prune_to_depth(self, max_depth):
        """Prune the tree to a maximum depth, removing all nodes beyond that depth."""
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")
        
        root_idx = self._get_node_index(self._root)
        
        depths = {}
        visited = set()
        queue = [(root_idx, 0)]
        
        while queue:
            node_idx, depth = queue.pop(0)
            if node_idx in visited:
                continue
            visited.add(node_idx)
            depths[node_idx] = depth
            
            for successor_idx in self._graph.successor_indices(node_idx):
                if successor_idx not in visited:
                    queue.append((successor_idx, depth + 1))
        
        indices_to_remove = [idx for idx, depth in depths.items() if depth > max_depth]
        
        for idx in indices_to_remove:
            node_obj = self._get_node_object(idx)
            Graph.remove_node(self, node_obj)
        
        self._invalidate_caches()

    def prune_leaves(self, n):
        """Prune n levels from each branch, starting from the leaves."""
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return
        
        for _ in range(n):
            leaf_indices = [idx for idx in self._graph.node_indices() if self._graph.out_degree(idx) == 0]
            for idx in leaf_indices:
                node_obj = self._get_node_object(idx)
                Graph.remove_node(self, node_obj)
            if self._graph.num_nodes() == 1:
                break
        
        self._invalidate_caches()

    def __deepcopy__(self, memo):
        """Create a deep copy of the tree including Tree-specific attributes."""
        new_tree = self.__class__.__new__(self.__class__)

        new_tree._graph = self._graph.copy()
        new_tree._meta = copy.deepcopy(self._meta, memo)
        new_tree._structure_version = 0

        new_tree._root = self._root
        new_tree._list = copy.deepcopy(self._list, memo)

        if hasattr(self, '_building_tree'):
            new_tree._building_tree = self._building_tree
        
        return new_tree
    
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
    def _from_graph(cls, G, clear_attributes=False, renumber=True, node_attr='label'):
        """Create a Tree from a RustworkX graph.
        
        Args:
            G: RustworkX PyDiGraph or Graph instance
            clear_attributes: Whether to clear node attributes
            renumber: Whether to renumber nodes
            node_attr: Attribute name to use for node labels
            
        Returns:
            Tree: New Tree instance
        """
        if isinstance(G, Graph):
            graph = G
        else:
            graph = Graph(G)
        
        if not hasattr(graph._graph, 'in_degree'):
            raise TypeError("Tree graphs must be directed")
        
        def get_node_value(node_obj):
            node_data = graph[node_obj]
            if clear_attributes:
                return None
            value = node_data.get(node_attr)
            return value if value is not None else node_obj
        
        def get_children(node_obj):
            return list(graph.successors(node_obj))
        
        def _build_children_list(node_obj):
            return cls._build_nested_structure(node_obj, get_node_value, get_children)
        
        root_objects = [node for node in graph if graph.in_degree(node) == 0]
        if len(root_objects) != 1:
            raise ValueError(f"Graph must have exactly one root node, found {len(root_objects)}")
        
        root = root_objects[0]
        children_structure = _build_children_list(root)
        
        if cls is Tree:
            if isinstance(children_structure, tuple) and len(children_structure) > 1:
                tree = cls(children_structure[0], children_structure[1])
            else:
                tree = cls(children_structure, tuple())
        else:
            base_tree = Tree._from_graph(G, clear_attributes, renumber=False, node_attr=node_attr)
            tree = cls._from_base_tree(base_tree)
        
        if renumber:
            tree.renumber_nodes()
        
        return tree
    
    @classmethod
    def _build_nested_structure(cls, root_node, get_node_value, get_children):
        """Build nested tuple structure from a tree starting at root_node.
        
        Args:
            root_node: The node to start building from
            get_node_value: Function that takes a node and returns its value
            get_children: Function that takes a node and returns its children
            
        Returns:
            Nested tuple structure representing the tree
        """
        children = get_children(root_node)
        if not children:
            return get_node_value(root_node)
        
        child_structures = []
        for child in sorted(children):
            child_structure = cls._build_nested_structure(child, get_node_value, get_children)
            child_structures.append(child_structure)
        
        root_value = get_node_value(root_node)
        return (root_value, tuple(child_structures))
    
    @classmethod
    def _from_base_tree(cls, base_tree):
        """Create a Tree subclass instance from a base Tree.
        
        Subclasses should override this method to handle their specific construction.
        
        Args:
            base_tree: Base Tree instance
            
        Returns:
            Tree: New Tree subclass instance
        """
        return base_tree
