from ...topos.graphs.trees import Tree
import pandas as pd

class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        super().__init__(root, children)
        self._meta['pfields'] = pd.Series([set()], index=[''])
    
    def __getitem__(self, node):
        return ParameterNode(self, node)
    
    @property
    def pfields(self):
        return sorted(self._meta.loc['', 'pfields'])
    
    def set(self, node, **kwargs):
        self._meta.loc['', 'pfields'].update(kwargs.keys())
        
        for key, value in kwargs.items():
            self.graph.nodes[node][key] = value
        
        for descendant in self.descendants(node):
            for key, value in kwargs.items():
                self.graph.nodes[descendant][key] = value
        
    def get(self, node, key):
        if key in self.graph.nodes[node]:
            return self.graph.nodes[node][key]
        return None
    
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
        self._tree.set(self._node, **{key: value})
        
    def clear(self):
        self._tree.clear(self._node)
        
    def items(self):
        return self._tree.items(self._node)
    
    def __dict__(self):
        return self._tree.items(self._node)
        
    def __str__(self):
        return str(self._tree.items(self._node))
    
    def __repr__(self):
        return repr(self._tree.items(self._node))