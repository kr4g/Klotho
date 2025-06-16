from ...topos.graphs.trees import Tree
from ..instruments.instrument import Instrument
import pandas as pd

class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        super().__init__(root, children)
        self._meta['pfields'] = pd.Series([set()], index=[''])
        self._node_instruments = {}
        self._subtree_muted_pfields = {}
    
    def __getitem__(self, node):
        return ParameterNode(self, node)
    
    @property
    def pfields(self):
        return sorted(self._meta.loc['', 'pfields'])
    
    def _traverse_to_instrument_node(self, node):
        current = node
        while current is not None:
            if current in self._node_instruments:
                return current
            try:
                current = self.parent(current)
            except (IndexError, AttributeError, TypeError):
                try:
                    parents = list(self.predecessors(current))
                    current = parents[0] if parents else None
                except (IndexError, AttributeError):
                    current = None
        return None
    
    def set_pfields(self, node, **kwargs):
        self._meta.loc['', 'pfields'].update(kwargs.keys())
        
        for key, value in kwargs.items():
            self.graph.nodes[node][key] = value
        
        for descendant in self.descendants(node):
            descendant_data = self.graph.nodes[descendant]
            for key, value in kwargs.items():
                descendant_data[key] = value
    
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
        self._meta.loc['', 'pfields'].update(instrument_pfields)
        
        self._node_instruments[node] = instrument
        
        descendants = list(self.descendants(node))
        subtree_nodes = [node] + descendants
        
        existing_pfields = set()
        for n in subtree_nodes:
            existing_pfields.update(self.graph.nodes[n].keys())
        
        non_instrument_pfields = existing_pfields - instrument_pfields
        self._subtree_muted_pfields[node] = non_instrument_pfields
        
        for n in subtree_nodes:
            node_data = self.graph.nodes[n]
            for key in instrument.keys():
                if key in exclude:
                    node_data[key] = instrument[key]
                elif key == 'synth_name' or key not in node_data:
                    node_data[key] = instrument[key]
    
    def get_active_instrument(self, node):
        instrument_node = self._traverse_to_instrument_node(node)
        return self._node_instruments.get(instrument_node) if instrument_node else None
    
    def get_governing_subtree_node(self, node):
        return self._traverse_to_instrument_node(node)
    
    def get_active_pfields(self, node):
        active_instrument = self.get_active_instrument(node)
        if active_instrument is None:
            return list(self.items(node).keys())
        return list(active_instrument.keys())
        
    def get(self, node, key):
        return self.graph.nodes[node].get(key)
    
    def clear(self, node=None):
        if node is None:
            for n in self.graph.nodes:
                self.graph.nodes[n].clear()
        else:
            self.graph.nodes[node].clear()
            for descendant in self.descendants(node):
                self.graph.nodes[descendant].clear()
            
    def items(self, node):
        return dict(self.graph.nodes[node])

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
        all_items = self._tree.items(self._node)
        governing_subtree_node = self._tree.get_governing_subtree_node(self._node)
        
        if governing_subtree_node is None:
            return all_items
        
        muted_pfields = self._tree._subtree_muted_pfields.get(governing_subtree_node, set())
        return {k: v for k, v in all_items.items() if k not in muted_pfields}
    
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self.active_items())
    
    def __repr__(self):
        return repr(self.active_items())
