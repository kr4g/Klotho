class Tree:
    def __init__(self, root, children:tuple):
        self._root = root
        self._children = children
    
    @property
    def root(self):
        return self._root
    
    @property
    def children(self):
        return self._children
