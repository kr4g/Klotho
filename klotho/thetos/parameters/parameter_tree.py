"""
Hierarchical parameter storage synchronized with rhythm tree structure.

This module provides ``ParameterTree``, a tree data structure that mirrors the
shape of a ``RhythmTree`` and stores per-node musical parameter values
(frequencies, amplitudes, etc.) with automatic inheritance.

The parameter behavior is implemented as a :class:`ParameterLayer` (owning the
pfield/mfield key sets, per-node overrides, instrument bindings, and the
effective-value cache) plus a :class:`ParameterApiMixin` that exposes the public
parameter API on any tree the layer is attached to. This lets a single tree
carry both rhythmic and parametric data (see ``CompositionalTree``) without
maintaining two mirrored trees.

Storage model: overrides are stored only at the node where set. Effective
values (inherited from ancestors) are computed on read and cached for O(1)
subsequent reads.
"""

from ...topos.graphs.trees import Tree, TreeLayer
import copy


class ParameterLayer(TreeLayer):
    """Layer owning per-node parameter/meta overrides, instruments, and the
    effective-value cache. Setting a value on a node makes it effective for all
    descendants via inheritance resolution."""

    def __init__(self):
        self._pfields = set()
        self._mfields = set()
        self._node_instruments = {}
        self._effective_cache = None

    @property
    def owned_keys(self):
        return frozenset(self._pfields | self._mfields)

    def invalidate(self, tree):
        self._effective_cache = None

    def on_structure_changed(self, tree, scope, op):
        self._effective_cache = None

    def on_clone(self, tree):
        self._pfields = set()
        self._mfields = set()
        self._node_instruments = {}
        self._effective_cache = None

    def clone_state(self, source_layer, new_tree, memo):
        self._pfields = set(source_layer._pfields)
        self._mfields = set(source_layer._mfields)
        self._node_instruments = copy.deepcopy(source_layer._node_instruments, memo)
        self._effective_cache = None

    def on_nodes_remapped(self, tree, mapping):
        self._effective_cache = None

    # ------------------------------------------------------------------
    def _build_effective(self, tree):
        if self._effective_cache is not None:
            return
        keys = self._pfields | self._mfields
        self._effective_cache = {}
        stack = [tree.root]
        while stack:
            node = stack.pop()
            p = tree.parent(node)
            parent_eff = self._effective_cache[p] if p is not None else {}
            raw = tree._rx[node]
            own = {k: v for k, v in raw.items() if k in keys} if isinstance(raw, dict) else {}
            self._effective_cache[node] = {**parent_eff, **own}
            for c in tree.successors(node):
                stack.append(c)

    def set_pfields(self, tree, node, **kwargs):
        self._pfields.update(kwargs.keys())
        tree._write_node_data(node, kwargs, replace=False)
        self._effective_cache = None

    def set_mfields(self, tree, node, **kwargs):
        self._mfields.update(kwargs.keys())
        tree._write_node_data(node, kwargs, replace=False)
        self._effective_cache = None

    def set_instrument(self, tree, node, instrument):
        if hasattr(instrument, 'pfields'):
            self._pfields.update(instrument.pfields.keys())
        self._node_instruments[node] = instrument

    def _resolve_governing_instrument_node(self, tree, node):
        if node in self._node_instruments:
            return node
        for ancestor in reversed(tree.branch(node)[:-1]):
            if ancestor in self._node_instruments:
                return ancestor
        return None

    def get_instrument(self, tree, node):
        governing = self._resolve_governing_instrument_node(tree, node)
        return self._node_instruments.get(governing) if governing is not None else None

    def get_pfield(self, tree, node, key):
        if key not in self._pfields:
            return None
        self._build_effective(tree)
        return self._effective_cache[node].get(key)

    def get_mfield(self, tree, node, key):
        if key not in self._mfields:
            return None
        self._build_effective(tree)
        return self._effective_cache[node].get(key)

    def get(self, tree, node, key):
        if key == 'instrument':
            return self.get_instrument(tree, node)
        self._build_effective(tree)
        return self._effective_cache[node].get(key)

    def items(self, tree, node):
        self._build_effective(tree)
        return dict(self._effective_cache[node])

    def remove_fields(self, tree, node, keys):
        raw = tree._rx[node]
        if isinstance(raw, dict):
            for k in keys:
                raw.pop(k, None)
        self._effective_cache = None

    def clear_fields(self, tree, node=None):
        keys = self._pfields | self._mfields
        if node is None:
            for n in tree.nodes:
                raw = tree._rx[n]
                if isinstance(raw, dict):
                    for k in list(raw.keys()):
                        if k in keys:
                            del raw[k]
            self._node_instruments.clear()
        else:
            targets = [node] + list(tree.descendants(node))
            for n in targets:
                raw = tree._rx[n]
                if isinstance(raw, dict):
                    for k in list(raw.keys()):
                        if k in keys:
                            del raw[k]
                self._node_instruments.pop(n, None)
        self._effective_cache = None


class ParameterApiMixin:
    """Exposes the parameter API on a tree that has a :class:`ParameterLayer`.

    The owning tree must set ``self._param_layer`` to its attached
    ``ParameterLayer`` (done in ``_init_layers``).
    """

    @property
    def pfields(self):
        return sorted(self._param_layer._pfields)

    @property
    def mfields(self):
        return sorted(self._param_layer._mfields)

    @property
    def pfield_names(self):
        return set(self._param_layer._pfields)

    @property
    def mfield_names(self):
        return set(self._param_layer._mfields)

    @property
    def node_instruments(self):
        return self._param_layer._node_instruments

    def register_pfields(self, keys):
        self._param_layer._pfields.update(keys)

    def register_mfields(self, keys):
        self._param_layer._mfields.update(keys)

    def set_pfields(self, node, **kwargs):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._param_layer.set_pfields(self, node, **kwargs)

    def set_mfields(self, node, **kwargs):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._param_layer.set_mfields(self, node, **kwargs)

    def set_instrument(self, node, instrument):
        if node not in self:
            raise ValueError(f"Node {node} not found in tree")
        self._param_layer.set_instrument(self, node, instrument)

    def get_instrument(self, node):
        return self._param_layer.get_instrument(self, node)

    def get_pfield(self, node, key):
        return self._param_layer.get_pfield(self, node, key)

    def get_mfield(self, node, key):
        return self._param_layer.get_mfield(self, node, key)

    def get(self, node, key):
        return self._param_layer.get(self, node, key)

    def items(self, node):
        return self._param_layer.items(self, node)

    def clear_fields(self, node=None):
        self._param_layer.clear_fields(self, node)

    def remove_fields(self, node, keys):
        self._param_layer.remove_fields(self, node, keys)

    def _resolve_governing_instrument_node(self, node):
        return self._param_layer._resolve_governing_instrument_node(self, node)


class ParameterTree(ParameterApiMixin, Tree):
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
    def __init__(self, root, children: tuple):
        super().__init__(root, children)
        for node in self.nodes:
            raw = self._rx[node]
            if isinstance(raw, dict):
                raw.pop('label', None)
        self._group_dirty = False

    def _init_layers(self):
        self._param_layer = self.attach_layer(ParameterLayer())

    def _after_subtree_built(self, new_tree, node_mapping, renumber):
        src = self._param_layer
        dst = new_tree._param_layer
        dst._pfields = set(src._pfields)
        dst._mfields = set(src._mfields)
        dst._node_instruments = {}
        for old_node, inst in src._node_instruments.items():
            if old_node in node_mapping:
                dst._node_instruments[node_mapping[old_node]] = inst
        dst._effective_cache = None

    def subtree(self, node, renumber=True):
        return super().subtree(node, renumber)

    def graft_subtree(self, target_node, subtree, mode='replace'):
        if not isinstance(subtree, Tree):
            raise TypeError("subtree must be a Tree instance")

        graft_result = super().graft_subtree(target_node, subtree, mode)

        if isinstance(subtree, ParameterTree):
            mapping = {}
            if mode == 'replace':
                mapping = subtree.map_parallel_nodes(
                    self, self_root=subtree.root, other_root=graft_result
                )
            else:
                target_children = list(self.successors(target_node))
                subtree_root_children = list(subtree.successors(subtree.root))
                grafted_children = target_children[-len(subtree_root_children):]
                for o_child, t_child in zip(subtree_root_children, grafted_children):
                    mapping.update(
                        subtree.map_parallel_nodes(
                            self, self_root=o_child, other_root=t_child
                        )
                    )

            self._param_layer._pfields.update(subtree._param_layer._pfields)
            self._param_layer._mfields.update(subtree._param_layer._mfields)

            for old_node, instrument in subtree._param_layer._node_instruments.items():
                mapped = mapping.get(old_node)
                if mapped is not None:
                    self._param_layer._node_instruments[mapped] = copy.deepcopy(instrument)

            self._param_layer._effective_cache = None

        return graft_result

    def __getitem__(self, node):
        return ParameterNode(self, node)


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
        self._tree.clear_fields(self._node)
        
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
