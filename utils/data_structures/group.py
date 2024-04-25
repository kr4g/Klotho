
class Group(tuple):
    def __init__(self, G:tuple) -> None:
        self.__G = G
    
    @property
    def D(self):
        return self.__G[0]
    
    @property
    def S(self):
        return self.__G[1]
    
    def __repr__(self) -> str:
        return super().__repr__()