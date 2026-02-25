"""
Hierarchical parameter storage synchronized with rhythm tree structure.

This module provides ``ParameterTree``, a tree data structure that mirrors the
shape of a ``RhythmTree`` and stores per-node musical parameter values
(frequencies, amplitudes, etc.) with automatic inheritance and cache management.
"""

from ...topos.graphs.trees import Tree
import copy


class ParameterTree(Tree):
    """
    A tree that stores per-node parameter and meta field values.
    
    Extends ``Tree`` with parameter-field and meta-field semantics: setting a
    value on a node propagates it to all descendants. Maintains separate
    registries for ``pfields`` (parameter fields) and ``mfields`` (meta fields)
    and implements version-based caching for fast active-item lookups.
    
    Parameters
    ----------
    root : int
        The root value used to construct the tree.
    children : tuple
        Subdivision tuple defining the tree structure (same format as
        ``RhythmTree`` subdivisions).
    """
    def __init__(self, root, children:tuple):
        self._parameter_version = 0
        self._active_items_cache = {}
        
        super().__init__(root, children)
        for node in self.nodes:
            super().__getitem__(node).pop('label', None)
        self._meta['pfields'] = set()
        self._meta['mfields'] = set()
    
    def _ensure_parameter_attributes(self):
        """Ensure all parameter-specific attributes are initialized."""
        if not hasattr(self, '_parameter_version'):
            self._parameter_version = 0
        if not hasattr(self, '_active_items_cache'):
            self._active_items_cache = {}
    
    def subtree(self, node, renumber=True):
        """
        Extract a subtree rooted at the given node.
        
        Overrides ``Tree.subtree`` to ensure parameter-specific caching
        attributes are initialized on the result.
        
        Parameters
        ----------
        node : int
            Root node of the subtree to extract.
        renumber : bool, optional
            Whether to renumber nodes starting from 0 (default is True).
            
        Returns
        -------
        ParameterTree
            A new ParameterTree containing the subtree.
        """
        result = super().subtree(node, renumber)
        if isinstance(result, ParameterTree):
            result._ensure_parameter_attributes()
        return result
    
    def __deepcopy__(self, memo):
        new_pt = super().__deepcopy__(memo)
        
        # Initialize caches for the new copy
        new_pt._active_items_cache = {}
        new_pt._parameter_version = 0
        return new_pt
    
    def _invalidate_parameter_caches(self):
        """Invalidate parameter-specific caches when data changes"""
        self._parameter_version += 1
        self._active_items_cache.clear()
    
    def _invalidate_caches(self):
        """Override to include parameter cache invalidation"""
        super()._invalidate_caches()
        self._invalidate_parameter_caches()
    
    def __getitem__(self, node):
        return ParameterNode(self, node)
    
    @property
    def pfields(self):
        """list of str : Sorted names of all registered parameter fields."""
        return sorted(self._meta['pfields'])
    
    @property
    def mfields(self):
        """list of str : Sorted names of all registered meta fields."""
        return sorted(self._meta['mfields'])
    
    def set_pfields(self, node, **kwargs):
        """
        Set parameter field values on a node and all its descendants.
        
        Parameters
        ----------
        node : int
            Target node ID.
        **kwargs
            Parameter field names and their values.
        """
        self._meta['pfields'].update(kwargs.keys())
        
        affected_nodes = [node] + list(self.descendants(node))
        
        for affected_node in affected_nodes:
            node_data = self.nodes[affected_node]
            node_data.update(kwargs)
        
        self._invalidate_parameter_caches()
    
    def set_mfields(self, node, **kwargs):
        """
        Set meta field values on a node and all its descendants.
        
        Parameters
        ----------
        node : int
            Target node ID.
        **kwargs
            Meta field names and their values.
        """
        self._meta['mfields'].update(kwargs.keys())
        
        affected_nodes = [node] + list(self.descendants(node))
        
        for affected_node in affected_nodes:
            node_data = self.nodes[affected_node]
            node_data.update(kwargs)
        
        self._invalidate_parameter_caches()
        
    def get(self, node, key):
        """
        Get a single field value from a node.
        
        Parameters
        ----------
        node : int
            The node ID.
        key : str
            The field name to retrieve.
            
        Returns
        -------
        Any or None
            The value, or None if the key is not set.
        """
        return self.nodes[node].get(key)
    
    def clear(self, node=None):
        """
        Clear all field values from a node (and its descendants), or from the
        entire tree if no node is specified.
        
        Parameters
        ----------
        node : int, optional
            Node ID to clear. If None, clears all nodes.
        """
        if node is None:
            for n in self.nodes:
                super().__getitem__(n).clear()
        else:
            super().__getitem__(node).clear()
            for descendant in self.descendants(node):
                super().__getitem__(descendant).clear()
        
        self._invalidate_parameter_caches()
            
    def items(self, node):
        """
        Get all field values for a node as a dictionary.
        
        Parameters
        ----------
        node : int
            The node ID.
            
        Returns
        -------
        dict
            Copy of the node's field data.
        """
        return dict(self.nodes[node])


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
        Get all field values for this node, with version-based caching.
        
        Returns
        -------
        dict
            The node's active field data (cached per parameter version).
        """
        cache_key = (self._node, self._tree._parameter_version)
        if cache_key in self._tree._active_items_cache:
            return self._tree._active_items_cache[cache_key]
        
        result = self._tree.items(self._node)
        
        self._tree._active_items_cache[cache_key] = result
        return result
    
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
        return self._tree.get(self._node, key) or default
        
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self.active_items())
    
    def __repr__(self):
        return repr(self.active_items())
