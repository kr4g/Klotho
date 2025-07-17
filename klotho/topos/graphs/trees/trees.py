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
        """Return leaf nodes (nodes with no successors) in sorted order.
        
        Returns
        -------
        tuple
            All leaf nodes in the tree, sorted for consistent ordering
        """
        leaf_indices = [idx for idx in self._graph.node_indices() 
                       if self._graph.out_degree(idx) == 0]
        
        leaf_indices.sort()
        
        return tuple(self._get_node_object(idx) for idx in leaf_indices)

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
        
        def edge_cost_fn(edge_data):
            return 1.0
        
        distances = rx.digraph_dijkstra_shortest_path_lengths(
            self._graph, root_idx, edge_cost_fn, goal=node_idx
        )
        
        try:
            return int(distances[node_idx])
        except KeyError:
            raise ValueError(f"Node {node} is not reachable from root")

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
        
        paths = rx.digraph_dijkstra_shortest_paths(
            self._graph, root_idx, target=node_idx, default_weight=1.0
        )
        
        if node_idx in paths:
            path_indices = paths[node_idx]
            ancestor_indices = path_indices[:-1]
            return tuple(self._get_node_object(ai) for ai in ancestor_indices)
        else:
            raise ValueError(f"Node {node} is not reachable from root")

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
        
        paths = rx.digraph_dijkstra_shortest_paths(
            self._graph, root_idx, target=node_idx, default_weight=1.0
        )
        
        if node_idx in paths:
            path_indices = paths[node_idx]
            return tuple(self._get_node_object(idx) for idx in path_indices)
        else:
            return tuple()

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
        Graph
            A new Graph object representing the subtree containing the node 
            and all its descendants
            
        Raises
        ------
        ValueError
            If the node is not found in the tree
        """
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        descendants = [node] + list(self.descendants(node))
        descendant_indices = [self._get_node_index(n) for n in descendants]

        subgraph_rx = self._graph.subgraph(descendant_indices)
        
        return self._from_graph(subgraph_rx, renumber=renumber)

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
        root_idx = self._get_node_index(self._root)
        
        def edge_cost_fn(edge_data):
            return 1.0
        
        distances_mapping = rx.digraph_dijkstra_shortest_path_lengths(
            self._graph, root_idx, edge_cost_fn
        )
        
        # Convert to dict and ensure root is included at distance 0
        distances = dict(distances_mapping)
        distances[root_idx] = 0
        
        matching_indices = []
        if operator == '==':
            matching_indices = [idx for idx, dist in distances.items() if dist == n]
        elif operator == '>=':
            matching_indices = [idx for idx, dist in distances.items() if dist >= n]
        elif operator == '<=':
            matching_indices = [idx for idx, dist in distances.items() if dist <= n]
        elif operator == '<':
            matching_indices = [idx for idx, dist in distances.items() if dist < n]
        elif operator == '>':
            matching_indices = [idx for idx, dist in distances.items() if dist > n]
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        # Sort indices for consistent ordering
        matching_indices.sort()
        
        return [self._get_node_object(idx) for idx in matching_indices]

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
        
        if parent is not None:
            new_root = self.add_subtree(parent, subtree)
            
            if children and handle_children == 'adopt':
                for child in children:
                    Graph.add_edge(self, new_root, child)
            
            Graph.remove_node(self, node)
        else:
            node_mapping = {}
            
            for n in subtree.nodes:
                new_id = Graph.add_node(self, **subtree[n])
                node_mapping[n] = new_id
            
            for u, v in subtree.edges:
                Graph.add_edge(self, node_mapping[u], node_mapping[v])
            
            new_root = node_mapping[subtree.root]
            
            if children and handle_children == 'adopt':
                for child in children:
                    Graph.add_edge(self, new_root, child)
            
            Graph.remove_node(self, node)
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
    def _from_graph(cls, G, clear_attributes=False, renumber=True):
        """Create a Tree from a RustworkX graph.
        
        Args:
            G: RustworkX PyDiGraph or Graph instance
            clear_attributes: Whether to clear node attributes
            renumber: Whether to renumber nodes
            
        Returns:
            Tree: New Tree instance
        """
        if isinstance(G, Graph):
            graph = G
        else:
            graph = Graph(G)
        
        if not hasattr(graph._graph, 'in_degree'):
            raise TypeError("Tree graphs must be directed")
        
        def _build_children_list(node_obj):
            child_objects = list(graph.successors(node_obj))
            if not child_objects:
                node_data = graph[node_obj]
                root_label = None if clear_attributes else node_data.get('label')
                return root_label if root_label is not None else node_obj
            
            node_data = graph[node_obj]
            root_label = None if clear_attributes else node_data.get('label')
            root_label = root_label if root_label is not None else node_obj
            
            child_structures = []
            for child_obj in child_objects:
                child_data = graph[child_obj]
                child_label = None if clear_attributes else child_data.get('label')
                child_label = child_label if child_label is not None else child_obj
                
                child_structure = _build_children_list(child_obj)
                if isinstance(child_structure, tuple):
                    child_structures.append(child_structure)
                else:
                    child_structures.append(child_structure)
            
            return (root_label, *child_structures)
        
        root_objects = [node for node in graph if graph.in_degree(node) == 0]
        if len(root_objects) != 1:
            raise ValueError(f"Graph must have exactly one root node, found {len(root_objects)}")
        
        root = root_objects[0]
        root_data = graph[root]
        root_label = None if clear_attributes else root_data.get('label')
        children_structure = _build_children_list(root)
        
        if isinstance(children_structure, tuple):
            tree = cls(children_structure[0], children_structure[1:])
        else:
            tree = cls(children_structure, tuple())
        
        if renumber:
            tree.renumber_nodes()
        
        return tree
