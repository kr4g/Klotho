from ...topos.graphs.trees import Tree
import copy


class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        # Initialize parameter-specific attributes before calling super()
        # since super().__init__() may call _invalidate_caches()
        self._parameter_version = 0
        self._active_items_cache = {}
        
        super().__init__(root, children)
        for node in self.nodes:
            # Access raw node data directly from Graph class, not through ParameterNode wrapper
            super().__getitem__(node).pop('label', None)
        self._meta['pfields'] = set()
        self._meta['mfields'] = set()
    
    def _ensure_parameter_attributes(self):
        """Ensure all parameter-specific attributes are initialized"""
        if not hasattr(self, '_parameter_version'):
            self._parameter_version = 0
        if not hasattr(self, '_active_items_cache'):
            self._active_items_cache = {}
    
    def subtree(self, node, renumber=True):
        """Override Tree.subtree to ensure ParameterTree-specific attributes are initialized"""
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
        return sorted(self._meta['pfields'])
    
    @property
    def mfields(self):
        return sorted(self._meta['mfields'])
    
    def set_pfields(self, node, **kwargs):
        """Optimized parameter setting with cache invalidation"""
        self._meta['pfields'].update(kwargs.keys())
        
        affected_nodes = [node] + list(self.descendants(node))
        
        for affected_node in affected_nodes:
            node_data = self.nodes[affected_node]
            node_data.update(kwargs)
        
        self._invalidate_parameter_caches()
    
    def set_mfields(self, node, **kwargs):
        """Optimized meta field setting with cache invalidation"""
        self._meta['mfields'].update(kwargs.keys())
        
        affected_nodes = [node] + list(self.descendants(node))
        
        for affected_node in affected_nodes:
            node_data = self.nodes[affected_node]
            node_data.update(kwargs)
        
        self._invalidate_parameter_caches()
        
    def get(self, node, key):
        return self.nodes[node].get(key)
    
    def clear(self, node=None):
        if node is None:
            for n in self.nodes:
                super().__getitem__(n).clear()
        else:
            super().__getitem__(node).clear()
            for descendant in self.descendants(node):
                super().__getitem__(descendant).clear()
        
        self._invalidate_parameter_caches()
            
    def items(self, node):
        return dict(self.nodes[node])
    

class ParameterNode:
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
        self._tree.set_pfields(self._node, **kwargs)
    
    def set_mfields(self, **kwargs):
        self._tree.set_mfields(self._node, **kwargs)
        
    def clear(self):
        self._tree.clear(self._node)
        
    def items(self):
        return self._tree.items(self._node)
    
    def active_items(self):
        """Heavily optimized active items with caching"""
        cache_key = (self._node, self._tree._parameter_version)
        if cache_key in self._tree._active_items_cache:
            return self._tree._active_items_cache[cache_key]
        
        result = self._tree.items(self._node)
        
        self._tree._active_items_cache[cache_key] = result
        return result
    
    def copy(self):
        """Create a copy of the node's data as a dict"""
        return dict(self._tree.items(self._node))
    
    def get(self, key, default=None):
        """Get a value with optional default"""
        return self._tree.get(self._node, key) or default
        
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self.active_items())
    
    def __repr__(self):
        return repr(self.active_items())
