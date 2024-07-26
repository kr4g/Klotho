
class Tree:
    def __init__(self, root, children:tuple):
        self.__root = root
        self.__children = children
    
    @property
    def root(self):
        return self.__root
    
    @property
    def children(self):
        return self.__children