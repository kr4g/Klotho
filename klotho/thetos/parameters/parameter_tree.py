from ...topos.graphs.trees import Tree
from ..instruments.instrument import Instrument
import pandas as pd


class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        super().__init__(root, children)
        for node in self.graph.nodes:
            self.graph.nodes[node].pop('label', None)
        self._meta['pfields'] = pd.Series([set()], index=[''])
        self._node_instruments = {}
        self._subtree_muted_pfields = {}
        self._slurs = {}
        self._next_slur_id = 0
    
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
        return self._node_instruments.get(instrument_node) if instrument_node is not None else None
    
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
        return self.graph.nodes[node].get(key)
    
    def clear(self, node=None):
        if node is None:
            for n in self.graph.nodes:
                self.graph.nodes[n].clear()
            self._slurs.clear()
        else:
            self.graph.nodes[node].clear()
            for descendant in self.descendants(node):
                self.graph.nodes[descendant].clear()
            
            affected_descendants = {node}.union(set(self.descendants(node)))
            to_remove = []
            for slur_id, slur_nodes in self._slurs.items():
                if slur_nodes & affected_descendants:
                    to_remove.append(slur_id)
            for slur_id in to_remove:
                del self._slurs[slur_id]
            
    def items(self, node):
        return dict(self.graph.nodes[node])
    
    def copy(self):
        """Create a deep copy of this ParameterTree, preserving instrument-related attributes."""
        copied = super().copy()
        copied._node_instruments = self._node_instruments.copy()
        copied._subtree_muted_pfields = self._subtree_muted_pfields.copy()
        copied._slurs = self._slurs.copy()
        copied._next_slur_id = self._next_slur_id
        return copied

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
        return {k: v for k, v in all_items.items() if k not in muted_pfields or k.startswith('_slur_')}
    
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self.active_items())
    
    def __repr__(self):
        return repr(self.active_items())
