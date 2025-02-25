from ...topos.graphs.trees import Tree
import pandas as pd

class ParameterTree(Tree):
    def __init__(self, root, children:tuple):
        super().__init__(root, children)
        self._parameters = {}
    
    def __getitem__(self, node):
        return ParameterNode(self, node)
    
    def set(self, node, **kwargs):
        if node not in self._parameters:
            self._parameters[node] = {}
        self._parameters[node].update(kwargs)
        
        # Update the graph nodes with the new parameters
        for key, value in kwargs.items():
            self.graph.nodes[node][key] = value
        
    def get(self, node, key):
        current = node
        while current is not None:
            if current in self._parameters and key in self._parameters[current]:
                return self._parameters[current][key]
            current = self.parent(current)
        return None
    
    def clear(self, node=None):
        if node is None:
            self._parameters.clear()
        elif node in self._parameters:
            del self._parameters[node]
            
    def items(self, node):
        params = {}
        current = node
        while current is not None:
            if current in self._parameters:
                for k, v in self._parameters[current].items():
                    if k not in params:
                        params[k] = v
            current = self.parent(current)
        return params

class ParameterNode:
    def __init__(self, tree, node):
        self._tree = tree
        self._node = node
        
    def __getitem__(self, key):
        return self._tree.get(self._node, key)
    
    def __setitem__(self, key, value):
        self._tree.set(self._node, **{key: value})
        
    def clear(self):
        self._tree.clear(self._node)
        
    def items(self):
        return self._tree.items(self._node)