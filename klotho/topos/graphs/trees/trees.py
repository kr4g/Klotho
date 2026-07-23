from ..core import GraphCore
from ..graphs import Graph
from .layers import TreeLayer
import rustworkx as rx
from functools import cached_property, lru_cache
from .group import Group
import copy


class Tree(GraphCore):
    """A directed acyclic graph tree structure.

    Represents a rooted tree where each node has at most one parent. Built from
    nested tuple structures and backed by a RustworkX directed graph inherited
    from :class:`GraphCore`.

    ``Tree`` is read-only at the topology level except through its sanctioned
    structural mutators (``add_child``, ``subdivide`` on subclasses, ``prune``,
    ``graft_subtree``, ``move_subtree``, ...). It does not inherit the free-form
    ``add_node``/``add_edge`` of :class:`Graph`.

    Domain behavior (rhythm, harmony, parameters) is provided by attached
    :class:`TreeLayer` objects rather than by overriding a mutation pipeline.

    Subclasses can override ``_node_value_attr`` to use a different attribute
    name for the node value (e.g. RhythmTree uses ``'proportion'``).

    Parameters
    ----------
    root : hashable
        The value for the root node of the tree.
    children : tuple
        Nested tuple structure defining the tree's children.
    """
    _node_value_attr = 'label'

    def __init__(self, root, children: tuple):
        super().__init__(directed=True)
        self._layers = []
        self._group_dirty = False
        self._root = self._build_tree(root, children)
        self._list = Group((root, children))
        self._init_layers()
        self._group_dirty = False

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------
    def _init_layers(self):
        """Subclass hook: create and attach domain layers. Base trees have none."""
        pass

    def attach_layer(self, layer: TreeLayer):
        """Attach a :class:`TreeLayer` to this tree."""
        self._layers.append(layer)
        layer.on_attach(self)
        return layer

    @property
    def layers(self):
        """tuple of TreeLayer : The domain layers attached to this tree."""
        return tuple(getattr(self, '_layers', ()))

    @property
    def root(self):
        """int : The root node id."""
        return self._root

    @property
    def group(self):
        """Group : The tree's ``(D, S)`` tuple representation, rebuilt lazily after mutation."""
        if getattr(self, '_group_dirty', False):
            self._rebuild_group()
            self._group_dirty = False
        return self._list

    @classmethod
    def from_tree_structure(cls, source_tree):
        """Create a new instance with the same topology as source_tree but no node data."""
        inst = cls.__new__(cls)
        inst._rx = source_tree._rx.copy()
        for idx in inst._rx.node_indices():
            inst._rx[idx] = {}
        inst._root = source_tree._root
        inst._list = copy.deepcopy(source_tree._list)
        inst._meta = {}
        inst._structure_version = 0
        inst._layers = []
        inst._group_dirty = False
        inst._init_layers()
        inst._post_structure_clone()
        inst._group_dirty = False
        return inst

    def _post_structure_clone(self):
        """Subclass hook: initialize domain-specific state after topology-only cloning."""
        for layer in self._layers:
            layer.on_clone(self)

    # ------------------------------------------------------------------
    # Node-data write pipeline (routes through attached layers)
    # ------------------------------------------------------------------
    def set_node_data(self, node, **attr):
        """Update data for an existing node (routed through layers)."""
        self._apply_layer_node_write(node, attr, replace=False, op='set_node_data')

    def update_node_data(self, node, attrs: dict):
        """Update data for an existing node from a dictionary (routed through layers)."""
        self._apply_layer_node_write(node, attrs, replace=False, op='update_node_data')

    def replace_node_data(self, node, attrs: dict):
        """Replace all data for an existing node (routed through layers)."""
        self._apply_layer_node_write(node, attrs, replace=True, op='replace_node_data')

    def set_node_attributes(self, node, attributes):
        """Set attributes for a node (routed through layers)."""
        self._apply_layer_node_write(node, attributes, replace=False, op='set_node_attributes')

    def _apply_layer_node_write(self, node, attrs, replace, op):
        if node not in self:
            raise KeyError(f"Node {node} not found in graph")
        normalized = dict(attrs) if isinstance(attrs, dict) else {}
        for layer in self._layers:
            normalized = layer.normalize_attrs(self, node, normalized, op)
        for layer in self._layers:
            layer.validate_attrs(self, node, normalized, op)
        changed_keys = tuple(sorted(normalized.keys()))
        scope = self._resolve_write_scope(node, changed_keys, op)
        self._write_node_data(node, normalized, replace=replace)
        self._post_mutation(scope_node=scope, op=op)

    def _resolve_write_scope(self, node, changed_keys, op):
        scope = node
        for layer in self._layers:
            s = layer.data_scope(self, node, changed_keys, op)
            if s is not None:
                scope = s
        return scope if (scope is None or scope in self) else None

    def _post_mutation(self, scope_node=None, op=None):
        if scope_node is not None and scope_node not in self:
            scope_node = None
        self._invalidate_caches()
        for layer in self._layers:
            layer.on_structure_changed(self, scope_node, op)

    def _invalidate_caches(self):
        """Invalidate all tree caches"""
        super()._invalidate_caches()
        for attr in ['depth', 'k', 'leaf_nodes']:
            if attr in self.__dict__:
                del self.__dict__[attr]
        if hasattr(self, 'parent'):
            self.parent.cache_clear()
        self._group_dirty = True
        for layer in getattr(self, '_layers', ()):
            layer.invalidate(self)

    @cached_property
    def depth(self):
        """Maximum depth of the tree."""
        if not hasattr(self, '_root') or self._root is None:
            return 0
        root_idx = self._get_node_index(self._root)
        if root_idx is None:
            return 0

        def edge_cost_fn(edge_data):
            return 1.0

        distances = rx.digraph_dijkstra_shortest_path_lengths(
            self._rx, root_idx, edge_cost_fn
        )

        return int(max(distances.values())) if distances else 0

    @cached_property
    def k(self):
        """Maximum branching factor of the tree"""
        return max((self.out_degree(n) for n in self.nodes), default=0)

    @cached_property
    def leaf_nodes(self):
        """Return leaf nodes (nodes with no successors) in tree traversal order."""
        leaf_nodes_list = []

        def collect_leaves(node):
            if self.out_degree(node) == 0:
                leaf_nodes_list.append(node)
            else:
                for child in self.successors(node):
                    collect_leaves(child)

        collect_leaves(self.root)
        return tuple(leaf_nodes_list)

    def subtree_leaves(self, node):
        """Return leaf nodes of the subtree rooted at the given node, in left-right order."""
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        leaves = []

        def collect_leaves(n):
            if self.out_degree(n) == 0:
                leaves.append(n)
            else:
                for child in self.successors(n):
                    collect_leaves(child)

        collect_leaves(node)
        return tuple(leaves)

    def depth_of(self, node):
        """Return the depth of a node in the tree (0 for root)."""
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        root_idx = self._get_node_index(self._root)
        node_idx = self._get_node_index(node)

        if root_idx == node_idx:
            return 0

        depth = 0
        current = node_idx

        while current != root_idx:
            parents = list(self._rx.predecessor_indices(current))
            if not parents:
                raise ValueError(f"Node {node} is not reachable from root")
            current = parents[0]
            depth += 1

        return depth

    @lru_cache(maxsize=None)
    def parent(self, node):
        """Returns the parent of a node, or None if the node is the root."""
        parents = list(self.predecessors(node))
        return parents[0] if parents else None

    @lru_cache(maxsize=None)
    def ancestors(self, node):
        """Return all ancestors of a node from root to parent (excluding the node)."""
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        if node == self._root:
            return tuple()

        root_idx = self._get_node_index(self._root)
        node_idx = self._get_node_index(node)

        ancestor_indices = []
        current = node_idx

        while current != root_idx:
            parents = list(self._rx.predecessor_indices(current))
            if not parents:
                raise ValueError(f"Node {node} is not reachable from root")
            current = parents[0]
            ancestor_indices.append(current)

        ancestor_indices.reverse()
        return tuple(self._get_node_object(ai) for ai in ancestor_indices)

    @lru_cache(maxsize=None)
    def descendants(self, node):
        """Return all descendants of a node in depth-first order."""
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        node_idx = self._get_node_index(node)

        dfs_edges = rx.dfs_edges(self._rx, node_idx)

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
        """Return all nodes on the branch from the root to the given node (inclusive)."""
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
            parents = list(self._rx.predecessor_indices(current))
            if not parents:
                return tuple()
            current = parents[0]

        branch_indices.append(root_idx)
        branch_indices.reverse()
        return tuple(self._get_node_object(idx) for idx in branch_indices)

    def path_signature(self, root_node, target_node):
        """Return child-index path from ``root_node`` to ``target_node``."""
        if root_node not in self:
            raise ValueError(f"Root node {root_node} not found in tree")
        if target_node not in self:
            raise ValueError(f"Target node {target_node} not found in tree")

        branch = list(self.branch(target_node))
        if root_node not in branch:
            raise ValueError(
                f"Node {target_node} is not in subtree rooted at {root_node}"
            )

        root_idx = branch.index(root_node)
        signature = []
        for i in range(root_idx + 1, len(branch)):
            parent = branch[i - 1]
            current = branch[i]
            children = list(self.successors(parent))
            signature.append(children.index(current))
        return tuple(signature)

    def node_from_signature(self, root_node, signature):
        """Resolve a node by child-index signature from ``root_node``."""
        if root_node not in self:
            raise ValueError(f"Root node {root_node} not found in tree")

        current = root_node
        for idx in signature:
            children = list(self.successors(current))
            if idx < 0 or idx >= len(children):
                raise ValueError(
                    f"Invalid child index {idx} for node {current} with {len(children)} children"
                )
            current = children[idx]
        return current

    def map_parallel_nodes(self, other_tree, self_root=None, other_root=None):
        """Map nodes between topologically parallel subtrees."""
        if not isinstance(other_tree, Tree):
            raise TypeError("other_tree must be a Tree instance")

        self_root = self.root if self_root is None else self_root
        other_root = other_tree.root if other_root is None else other_root

        if self_root not in self:
            raise ValueError(f"Node {self_root} not found in source tree")
        if other_root not in other_tree:
            raise ValueError(f"Node {other_root} not found in target tree")

        mapping = {}
        stack = [(self_root, other_root)]
        while stack:
            src_node, dst_node = stack.pop()
            mapping[src_node] = dst_node

            src_children = list(self.successors(src_node))
            dst_children = list(other_tree.successors(dst_node))
            if len(src_children) != len(dst_children):
                raise ValueError(
                    "Topology mismatch while mapping parallel subtrees"
                )
            for src_child, dst_child in zip(reversed(src_children), reversed(dst_children)):
                stack.append((src_child, dst_child))
        return mapping

    def siblings(self, node):
        """Returns the siblings of a node (nodes with the same parent)."""
        parent = self.parent(node)
        return tuple(n for n in self.successors(parent) if n != node) if parent else tuple()

    def lowest_common_ancestor(self, node_a, node_b):
        """
        Find the deepest node that is an ancestor of both given nodes.

        Parameters
        ----------
        node_a : int
            First node id.
        node_b : int
            Second node id.

        Returns
        -------
        int
            The id of the lowest common ancestor (the root in the
            worst case).

        Raises
        ------
        ValueError
            If either node is not in the tree.
        """
        if node_a not in self or node_b not in self:
            raise ValueError("Both nodes must exist in the tree")
        branch_a = self.branch(node_a)
        branch_b = self.branch(node_b)
        lca = self.root
        for a, b in zip(branch_a, branch_b):
            if a != b:
                break
            lca = a
        return lca

    def subtree(self, node, renumber=True):
        """Extract a tree subtree rooted at the given node."""
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")

        descendants = [node] + list(self.descendants(node))

        new_tree = self.__class__.__new__(self.__class__)
        new_tree._rx = rx.PyDiGraph()
        new_tree._meta = self._meta.copy()
        new_tree._structure_version = 0
        new_tree._layers = []
        new_tree._group_dirty = False

        node_mapping = {}
        for old_node in descendants:
            new_node_id = new_tree._rx.add_node(self[old_node].copy())
            node_mapping[old_node] = new_node_id

        for old_node in descendants:
            for successor in self.successors(old_node):
                if successor in descendants:
                    new_tree._rx.add_edge(
                        node_mapping[old_node],
                        node_mapping[successor],
                        None
                    )

        new_tree._root = node_mapping[node]

        attr = getattr(self, '_node_value_attr', 'label')

        def build_group_structure(root_node):
            children = [child for child in descendants if self.parent(child) == root_node]
            if not children:
                return self[root_node].get(attr, root_node)

            child_structures = []
            for child in sorted(children):
                child_structure = build_group_structure(child)
                child_structures.append(child_structure)

            root_val = self[root_node].get(attr, root_node)
            return (root_val, tuple(child_structures))

        structure = build_group_structure(node)
        if isinstance(structure, tuple) and len(structure) > 1:
            new_tree._list = Group(structure)
        else:
            new_tree._list = Group((structure, tuple()))

        new_tree._init_layers()
        for layer in new_tree._layers:
            layer.on_nodes_remapped(new_tree, node_mapping)

        if hasattr(self, '_after_subtree_built'):
            self._after_subtree_built(new_tree, node_mapping, renumber)
        if renumber:
            new_tree.renumber_nodes()

        return new_tree

    def at_depth(self, n, operator='=='):
        """Return nodes at a specific depth."""
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

    # ------------------------------------------------------------------
    # Structural mutators
    # ------------------------------------------------------------------
    def add_child(self, parent, index=None, **attr):
        """Add a child node to a parent. Returns the new child node id."""
        normalized = dict(attr)
        for layer in self._layers:
            normalized = layer.normalize_attrs(self, parent, normalized, 'add_child')
        for layer in self._layers:
            layer.validate_attrs(self, parent, normalized, 'add_child')
        child_id = self._add_node_raw(**normalized)
        self._add_edge_raw(parent, child_id)
        self._post_mutation(scope_node=parent, op='add_child')
        return child_id

    def add_subtree(self, parent, subtree, index=None):
        """Add a subtree as a child of a parent node. Returns the attached subtree root id."""
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")

        node_mapping = {}

        for node in subtree.nodes:
            new_id = self._add_node_raw(**dict(subtree.nodes[node]))
            node_mapping[node] = new_id

        for u, v in subtree.edges:
            self._add_edge_raw(node_mapping[u], node_mapping[v])

        subtree_root = node_mapping[subtree.root]
        self._add_edge_raw(parent, subtree_root)

        self._post_mutation(scope_node=parent, op='add_subtree')
        return subtree_root

    def prune(self, node):
        """Remove a node and promote its children to its parent."""
        if node == self.root:
            raise ValueError("Cannot prune the root node")

        parent = self.parent(node)
        children = list(self.successors(node))

        for child in children:
            self._add_edge_raw(parent, child)

        self._remove_node_raw(node)
        self._post_mutation(scope_node=parent, op='prune')

    def remove_subtree(self, node):
        """Remove a node and its entire subtree."""
        if node == self.root:
            raise ValueError("Cannot remove the root node")

        subtree_nodes = [node] + list(self.descendants(node))
        parent = self.parent(node)

        for n in subtree_nodes:
            self._remove_node_raw(n)
        self._post_mutation(scope_node=parent, op='remove_subtree')

    def replace_node(self, old_node, **attr):
        """Replace a node's attributes while preserving structure."""
        parent = self.parent(old_node)
        normalized = dict(attr)
        for layer in self._layers:
            normalized = layer.normalize_attrs(self, old_node, normalized, 'replace_node')
        for layer in self._layers:
            layer.validate_attrs(self, old_node, normalized, 'replace_node')
        self._write_node_data(old_node, copy.deepcopy(normalized if normalized else {}), replace=True)
        scope_node = parent if parent is not None else old_node
        self._post_mutation(scope_node=scope_node, op='replace_node')
        return old_node

    def _rebuild_group(self):
        """Rebuild the Group structure based on current graph state."""
        if hasattr(self, '_list'):
            attr = getattr(self, '_node_value_attr', 'label')

            def get_node_value(node):
                return self[node].get(attr, node)

            def get_children(node):
                return list(self.successors(node))

            structure = self._build_nested_structure(self.root, get_node_value, get_children)
            if isinstance(structure, tuple) and len(structure) > 1:
                self._list = Group(structure)
            else:
                self._list = Group((structure, tuple()))

    def graft_subtree(self, target_node, subtree, mode='replace'):
        """Graft a subtree onto the tree at the specified leaf node."""
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
        else:
            return self._graft_adopt_leaf(target_node, subtree)

    def _graft_replace_leaf(self, target_node, subtree):
        """Replace the leaf node with the subtree root."""
        parent = self.parent(target_node)

        node_mapping = {subtree.root: target_node}
        for node in subtree.nodes:
            if node == subtree.root:
                continue
            new_id = self._add_node_raw(**dict(subtree.nodes[node]))
            node_mapping[node] = new_id

        self._write_node_data(target_node, copy.deepcopy(dict(subtree.nodes[subtree.root])), replace=True)

        for u, v in subtree.edges:
            if u == subtree.root:
                self._add_edge_raw(target_node, node_mapping[v])
            else:
                self._add_edge_raw(node_mapping[u], node_mapping[v])

        self._post_mutation(scope_node=parent, op='graft_subtree')
        return target_node

    def _graft_adopt_leaf(self, target_node, subtree):
        """Keep the leaf node and give it the children from subtree root."""
        subtree_nodes_except_root = [node for node in subtree.nodes if node != subtree.root]

        node_mapping = {}
        for node in subtree_nodes_except_root:
            new_id = self._add_node_raw(**dict(subtree.nodes[node]))
            node_mapping[node] = new_id

        for u, v in subtree.edges:
            if u != subtree.root and v != subtree.root:
                self._add_edge_raw(node_mapping[u], node_mapping[v])

        subtree_root_children = list(subtree.successors(subtree.root))
        for child in subtree_root_children:
            self._add_edge_raw(target_node, node_mapping[child])

        self._post_mutation(scope_node=target_node, op='graft_subtree')
        return target_node

    def move_subtree(self, node, new_parent, index=None):
        """Move a subtree to a new parent."""
        if node == self.root:
            raise ValueError("Cannot move the root node")

        old_parent = self.parent(node)
        scope_node = new_parent
        if old_parent is not None and new_parent is not None:
            scope_node = self.lowest_common_ancestor(old_parent, new_parent)

        self._remove_edge_raw(old_parent, node)
        self._add_edge_raw(new_parent, node)

        self._post_mutation(scope_node=scope_node, op='move_subtree')

    def prune_to_depth(self, max_depth):
        """Prune the tree to a maximum depth."""
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

            for successor_idx in self._rx.successor_indices(node_idx):
                if successor_idx not in visited:
                    queue.append((successor_idx, depth + 1))

        indices_to_remove = [idx for idx, depth in depths.items() if depth > max_depth]

        for idx in indices_to_remove:
            node_obj = self._get_node_object(idx)
            self._remove_node_raw(node_obj)

        self._post_mutation(scope_node=None, op='prune_to_depth')

    def prune_leaves(self, n):
        """Prune n levels from each branch, starting from the leaves."""
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return

        for _ in range(n):
            leaf_indices = [idx for idx in self._rx.node_indices() if self._rx.out_degree(idx) == 0]
            for idx in leaf_indices:
                node_obj = self._get_node_object(idx)
                self._remove_node_raw(node_obj)
            if self._rx.num_nodes() == 1:
                break

        self._post_mutation(scope_node=None, op='prune_leaves')

    def __deepcopy__(self, memo):
        """Create a deep copy of the tree including Tree-specific attributes."""
        new_tree = self.__class__.__new__(self.__class__)

        new_tree._rx = self._rx.copy()
        new_tree._meta = copy.deepcopy(self._meta, memo)
        new_tree._structure_version = 0

        new_tree._root = self._root
        new_tree._list = copy.deepcopy(self._list, memo)
        new_tree._group_dirty = getattr(self, '_group_dirty', False)
        new_tree._layers = []
        new_tree._init_layers()
        for old_layer, new_layer in zip(getattr(self, '_layers', ()), new_tree._layers):
            new_layer.clone_state(old_layer, new_tree, memo)

        return new_tree

    def _build_tree(self, root, children):
        """Build the tree structure from nested tuples."""
        attr = getattr(self, '_node_value_attr', 'label')
        root_id = self._add_node_raw(**{attr: root})
        self._add_children(root_id, children)
        return root_id

    def _add_children(self, parent_id, children_list):
        attr = getattr(self, '_node_value_attr', 'label')
        for child in children_list:
            match child:
                case tuple((D, S)):
                    duration_id = self._add_node_raw(**{attr: D})
                    self._add_edge_raw(parent_id, duration_id)
                    self._add_children(duration_id, S)
                case Tree():
                    child_attr = getattr(child, '_node_value_attr', 'label')
                    val = child[child.root].get(child_attr, child.root)
                    meta_val = child._meta if isinstance(child._meta, dict) else child._meta.to_dict('records')[0]
                    duration_id = self._add_node_raw(**{attr: val}, meta=meta_val)
                    self._add_edge_raw(parent_id, duration_id)
                    self._add_children(duration_id, child.group.S)
                case _:
                    child_id = self._add_node_raw(**{attr: child})
                    self._add_edge_raw(parent_id, child_id)

    @classmethod
    def _from_graph(cls, G, clear_attributes=False, renumber=True, node_attr='label'):
        """Create a Tree from a RustworkX graph or Graph."""
        if isinstance(G, GraphCore):
            graph = G
        else:
            graph = Graph.from_rustworkx(G)

        if not hasattr(graph._rx, 'in_degree'):
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
        """Build nested tuple structure from a tree starting at root_node."""
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
        """Create a Tree subclass instance from a base Tree."""
        return base_tree
