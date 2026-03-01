"""
Hierarchical parameter storage synchronized with rhythm tree structure.

This module provides ``ParameterTree``, a tree data structure that mirrors the
shape of a ``RhythmTree`` and stores per-node musical parameter values
(frequencies, amplitudes, etc.) with automatic inheritance.

Storage model: overrides are stored only at the node where set. Effective
values (inherited from ancestors) are computed on write and cached for O(1) read.
"""

from ...topos.graphs.trees import Tree
import copy


class ParameterTree(Tree):
    """
    A tree that stores per-node parameter and meta field values.

    Extends ``Tree`` with parameter-field and meta-field semantics: setting a
    value on a node propagates it to all descendants. Overrides are stored
    only at the set site; effective values are cached for O(1) read.

    Parameters
    ----------
    root : int
        The root value used to construct the tree.
    children : tuple
        Subdivision tuple defining the tree structure (same format as
        ``RhythmTree`` subdivisions).
    """
    def __init__(self, root, children:tuple):
        super().__init__(root, children)
        for node in self.nodes:
            self._graph[node].pop('label', None)
        self._meta['pfields'] = set()
        self._meta['mfields'] = set()
        self._node_instruments = {}
        self._effective_cache = None

    def _post_structure_clone(self):
        self._meta['pfields'] = set()
        self._meta['mfields'] = set()
        self._node_instruments = {}
        self._effective_cache = None

    def _invalidate_caches(self):
        super()._invalidate_caches()
        self._effective_cache = None

    def _build_effective(self):
        if self._effective_cache is not None:
            return
        self._effective_cache = {}
        stack = [self.root]
        while stack:
            node = stack.pop()
            p = self.parent(node)
            parent_eff = self._effective_cache[p] if p is not None else {}
            self._effective_cache[node] = {**parent_eff, **self.nodes[node]}
            for c in self.successors(node):
                stack.append(c)

    def _after_subtree_built(self, new_tree, node_mapping, renumber):
        new_tree._node_instruments = {}
        for old_node, inst in self._node_instruments.items():
            if old_node in node_mapping:
                new_tree._node_instruments[node_mapping[old_node]] = inst
        new_tree._effective_cache = None

    def _resolve_governing_instrument_node(self, node: int):
        if node in self._node_instruments:
            return node
        for ancestor in reversed(self.branch(node)[:-1]):
            if ancestor in self._node_instruments:
                return ancestor
        return None

    def set_instrument(self, node, instrument):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._meta['pfields'].update(instrument.keys())
        self._node_instruments[node] = instrument

    def __deepcopy__(self, memo):
        new_pt = super().__deepcopy__(memo)
        new_pt._node_instruments = copy.deepcopy(self._node_instruments, memo)
        new_pt._effective_cache = None
        return new_pt

    def subtree(self, node, renumber=True):
        return super().subtree(node, renumber)

    def _map_parallel_nodes(self, other_tree, other_node, this_node, mapping):
        mapping[other_node] = this_node
        other_children = list(other_tree.successors(other_node))
        this_children = list(self.successors(this_node))
        if len(other_children) != len(this_children):
            raise ValueError("Topology mismatch while mapping grafted subtree")
        for o_child, t_child in zip(other_children, this_children):
            self._map_parallel_nodes(other_tree, o_child, t_child, mapping)

    def graft_subtree(self, target_node, subtree, mode='replace'):
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")

        graft_result = super().graft_subtree(target_node, subtree, mode)

        if isinstance(subtree, ParameterTree):
            mapping = {}
            if mode == 'replace':
                self._map_parallel_nodes(subtree, subtree.root, graft_result, mapping)
            else:
                target_children = list(self.successors(target_node))
                subtree_root_children = list(subtree.successors(subtree.root))
                for o_child, t_child in zip(subtree_root_children, target_children[-len(subtree_root_children):]):
                    self._map_parallel_nodes(subtree, o_child, t_child, mapping)

            self._meta['pfields'].update(subtree._meta.get('pfields', set()))
            self._meta['mfields'].update(subtree._meta.get('mfields', set()))

            for old_node, instrument in subtree._node_instruments.items():
                mapped = mapping.get(old_node)
                if mapped is not None:
                    self._node_instruments[mapped] = copy.deepcopy(instrument)

            self._effective_cache = None

        return graft_result

    def __getitem__(self, node):
        return ParameterNode(self, node)

    @property
    def pfields(self):
        return sorted(self._meta['pfields'])

    @property
    def mfields(self):
        return sorted(self._meta['mfields'])

    def set_pfields(self, node, **kwargs):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._meta['pfields'].update(kwargs.keys())
        self._graph[node].update(kwargs)
        self._effective_cache = None

    def set_mfields(self, node, **kwargs):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._meta['mfields'].update(kwargs.keys())
        self._graph[node].update(kwargs)
        self._effective_cache = None

    def get_instrument(self, node):
        governing = self._resolve_governing_instrument_node(node)
        return self._node_instruments.get(governing) if governing is not None else None

    def get_pfield(self, node, key):
        if key not in self._meta['pfields']:
            return None
        self._build_effective()
        return self._effective_cache[node].get(key)

    def get_mfield(self, node, key):
        if key not in self._meta['mfields']:
            return None
        self._build_effective()
        return self._effective_cache[node].get(key)

    def get(self, node, key):
        if key == 'instrument':
            return self.get_instrument(node)
        self._build_effective()
        return self._effective_cache[node].get(key)

    def clear(self, node=None):
        if node is None:
            for n in self.nodes:
                super().__getitem__(n).clear()
        else:
            super().__getitem__(node).clear()
            for descendant in self.descendants(node):
                super().__getitem__(descendant).clear()
        self._effective_cache = None

    def items(self, node):
        self._build_effective()
        return dict(self._effective_cache[node])


class ParameterNode:
    """
    Proxy object for convenient access to a single node's parameter data
    within a ``ParameterTree``.
    
    Returned by ``ParameterTree.__getitem__`` and supports dict-like read/write
    access as well as bulk parameter and meta field operations.
    
    Parameters
    ----------
    tree : ParameterTree
        The owning parameter tree.
    node : int
        The node ID this proxy represents.
    """
    def __init__(self, tree, node):
        self._tree = tree
        self._node = node
        
    def __getitem__(self, key):
        if isinstance(key, str):
            return self._tree.get(self._node, key)
        raise TypeError("Key must be a string")

    def get_instrument(self):
        return self._tree.get_instrument(self._node)

    def get_pfield(self, key):
        return self._tree.get_pfield(self._node, key)

    def get_mfield(self, key):
        return self._tree.get_mfield(self._node, key)
    
    def __setitem__(self, key, value):
        self._tree.set_pfields(self._node, **{key: value})
    
    def set_pfields(self, **kwargs):
        """
        Set parameter fields on this node and its descendants.
        
        Parameters
        ----------
        **kwargs
            Parameter field names and values.
        """
        self._tree.set_pfields(self._node, **kwargs)
    
    def set_mfields(self, **kwargs):
        """
        Set meta fields on this node and its descendants.
        
        Parameters
        ----------
        **kwargs
            Meta field names and values.
        """
        self._tree.set_mfields(self._node, **kwargs)
        
    def clear(self):
        """Clear all field values from this node and its descendants."""
        self._tree.clear(self._node)
        
    def items(self):
        """
        Get all field values for this node.
        
        Returns
        -------
        dict
            Copy of the node's field data.
        """
        return self._tree.items(self._node)
    
    def active_items(self):
        """
        Get all field values for this node.
        
        Returns
        -------
        dict
            The node's active field data.
        """
        return self._tree.items(self._node)
    
    def copy(self):
        """
        Create a standalone copy of this node's data.
        
        Returns
        -------
        dict
            Dictionary copy of the node's field data.
        """
        return dict(self._tree.items(self._node))
    
    def get(self, key, default=None):
        """
        Get a field value with an optional default.
        
        Parameters
        ----------
        key : str
            The field name.
        default : Any, optional
            Value returned if key is not set.
            
        Returns
        -------
        Any
            The field value, or *default*.
        """
        value = self._tree.get(self._node, key)
        return default if value is None else value
        
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self.active_items())
    
    def __repr__(self):
        return repr(self.active_items())
