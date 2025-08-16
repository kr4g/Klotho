from ...topos.graphs.trees import Tree
from ..instruments.instrument import Instrument
import copy
from functools import lru_cache


class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        # Initialize parameter-specific attributes before calling super()
        # since super().__init__() may call _invalidate_caches()
        self._parameter_version = 0
        self._governing_node_cache = {}
        self._active_instrument_cache = {}
        self._active_items_cache = {}
        self._node_instruments = {}
        self._subtree_muted_pfields = {}
        self._slurs = {}
        self._next_slur_id = 0
        
        super().__init__(root, children)
        for node in self.nodes:
            # Access raw node data directly from Graph class, not through ParameterNode wrapper
            super().__getitem__(node).pop('label', None)
        self._meta['pfields'] = set()
    
    def _ensure_parameter_attributes(self):
        """Ensure all parameter-specific attributes are initialized"""
        if not hasattr(self, '_parameter_version'):
            self._parameter_version = 0
        if not hasattr(self, '_governing_node_cache'):
            self._governing_node_cache = {}
        if not hasattr(self, '_active_instrument_cache'):
            self._active_instrument_cache = {}
        if not hasattr(self, '_active_items_cache'):
            self._active_items_cache = {}
        if not hasattr(self, '_node_instruments'):
            self._node_instruments = {}
        if not hasattr(self, '_subtree_muted_pfields'):
            self._subtree_muted_pfields = {}
        if not hasattr(self, '_slurs'):
            self._slurs = {}
        if not hasattr(self, '_next_slur_id'):
            self._next_slur_id = 0
    
    def subtree(self, node, renumber=True):
        """Override Tree.subtree to ensure ParameterTree-specific attributes are initialized"""
        result = super().subtree(node, renumber)
        if isinstance(result, ParameterTree):
            result._ensure_parameter_attributes()
        return result
    
    def __deepcopy__(self, memo):
        new_pt = super().__deepcopy__(memo)
        new_pt._node_instruments = copy.deepcopy(self._node_instruments, memo)
        new_pt._subtree_muted_pfields = copy.deepcopy(self._subtree_muted_pfields, memo)
        new_pt._slurs = copy.deepcopy(self._slurs, memo)
        new_pt._next_slur_id = self._next_slur_id
        
        # Initialize caches for the new copy
        new_pt._governing_node_cache = {}
        new_pt._active_instrument_cache = {}
        new_pt._active_items_cache = {}
        new_pt._parameter_version = 0
        return new_pt
    
    def _invalidate_parameter_caches(self):
        """Invalidate parameter-specific caches when data changes"""
        self._parameter_version += 1
        self._governing_node_cache.clear()
        self._active_instrument_cache.clear()
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
    
    def _traverse_to_instrument_node(self, node):
        """Cached instrument node traversal"""
        cache_key = (node, self._parameter_version)
        if cache_key in self._governing_node_cache:
            return self._governing_node_cache[cache_key]
        
        result = None
        if node in self._node_instruments:
            result = node
        else:
            for ancestor in self.ancestors(node):
                if ancestor in self._node_instruments:
                    result = ancestor
                    break
        
        self._governing_node_cache[cache_key] = result
        return result
    
    def set_pfields(self, node, **kwargs):
        """Optimized parameter setting with cache invalidation"""
        self._meta['pfields'].update(kwargs.keys())
        
        affected_nodes = [node] + list(self.descendants(node))
        
        for affected_node in affected_nodes:
            node_data = self.nodes[affected_node]
            node_data.update(kwargs)
        
        self._invalidate_parameter_caches()
    
    def set_instrument(self, node, instrument, exclude=None):        
        if not isinstance(instrument, Instrument):
            raise TypeError("Expected Instrument instance")
        
        if exclude is None:
            exclude = set()
        elif isinstance(exclude, str):
            exclude = {exclude}
        elif isinstance(exclude, (list, tuple)):
            exclude = set(exclude)
        elif not isinstance(exclude, set):
            exclude = set(exclude)
            
        instrument_pfields = set(instrument.keys())
        self._meta['pfields'].update(instrument_pfields)
        
        self._node_instruments[node] = instrument
        
        descendants = list(self.descendants(node))
        subtree_nodes = [node] + descendants
        
        existing_pfields = set()
        for n in subtree_nodes:
            existing_pfields.update(self.nodes[n].keys())
        
        non_instrument_pfields = existing_pfields - instrument_pfields
        self._subtree_muted_pfields[node] = non_instrument_pfields
        
        for n in subtree_nodes:
            node_data = self.nodes[n]
            for key in instrument.keys():
                if key in exclude:
                    node_data[key] = instrument[key]
                elif key == 'synth_name' or key not in node_data:
                    node_data[key] = instrument[key]
        
        self._invalidate_parameter_caches()
    
    def get_active_instrument(self, node):
        """Cached active instrument lookup"""
        cache_key = (node, self._parameter_version)
        if cache_key in self._active_instrument_cache:
            return self._active_instrument_cache[cache_key]
        
        instrument_node = self._traverse_to_instrument_node(node)
        result = self._node_instruments.get(instrument_node) if instrument_node is not None else None
        
        self._active_instrument_cache[cache_key] = result
        return result
    
    def get_governing_subtree_node(self, node):
        return self._traverse_to_instrument_node(node)
    
    def get_active_pfields(self, node):
        active_instrument = self.get_active_instrument(node)
        if active_instrument is None:
            return list(self.items(node).keys())
        return list(active_instrument.keys())
    
    def add_slur(self, affected_nodes, rhythm_tree, events):
        """Add a slur affecting the given nodes with validation"""
        if not affected_nodes:
            return None
        
        affected_nodes = set(affected_nodes)
        
        instruments = set()
        for node in affected_nodes:
            instrument = self.get_active_instrument(node)
            if instrument:
                instruments.add(instrument.name)
        
        if len(instruments) > 1:
            raise ValueError(f"All nodes in a slur must belong to the same instrument. Found: {instruments}")
        
        for existing_slur_nodes in self._slurs.values():
            if affected_nodes & existing_slur_nodes:
                raise ValueError("Slurs cannot overlap")
        
        slur_id = self._next_slur_id
        self._next_slur_id += 1
        
        self._slurs[slur_id] = affected_nodes
        
        # Find actual events for affected nodes and sort by their start times
        slur_events = [event for event in events if event.node_id in affected_nodes]
        slur_events.sort(key=lambda e: e.start)
        
        first_node = slur_events[0].node_id
        last_node = slur_events[-1].node_id
        
        for node in affected_nodes:
            slur_start = 1 if node == first_node else 0
            slur_end = 1 if node == last_node else 0
            self.set_pfields(node, _slur_start=slur_start, _slur_end=slur_end, _slur_id=slur_id)
        
        return slur_id
        
    def get(self, node, key):
        return self.nodes[node].get(key)
    
    def clear(self, node=None):
        if node is None:
            for n in self.nodes:
                super().__getitem__(n).clear()
            self._slurs.clear()
        else:
            super().__getitem__(node).clear()
            for descendant in self.descendants(node):
                super().__getitem__(descendant).clear()
            
            affected_descendants = {node}.union(set(self.descendants(node)))
            to_remove = []
            for slur_id, slur_nodes in self._slurs.items():
                if slur_nodes & affected_descendants:
                    to_remove.append(slur_id)
            for slur_id in to_remove:
                del self._slurs[slur_id]
        
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
        
    def set_instrument(self, instrument, exclude=None):
        self._tree.set_instrument(self._node, instrument, exclude=exclude)
        
    def clear(self):
        self._tree.clear(self._node)
        
    def items(self):
        return self._tree.items(self._node)
    
    def active_items(self):
        """Heavily optimized active items with caching"""
        cache_key = (self._node, self._tree._parameter_version)
        if cache_key in self._tree._active_items_cache:
            return self._tree._active_items_cache[cache_key]
        
        all_items = self._tree.items(self._node)
        governing_subtree_node = self._tree.get_governing_subtree_node(self._node)
        
        if governing_subtree_node is None:
            result = all_items
        else:
            muted_pfields = self._tree._subtree_muted_pfields.get(governing_subtree_node, set())
            result = {k: v for k, v in all_items.items() 
                     if k not in muted_pfields or k.startswith('_slur_')}
        
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
