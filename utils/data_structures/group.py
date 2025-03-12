class Group(tuple):
    def __new__(cls, G):
        if isinstance(G, tuple):
            D = G[0]
            S = G[1]
            
            if isinstance(S, tuple):
                processed_S = []
                for item in S:
                    if isinstance(item, tuple):
                        processed_S.append(Group(item))
                    else:
                        processed_S.append(item)
                S = tuple(processed_S)
            
            G = (D, S)
        
        return super(Group, cls).__new__(cls, G)
    
    @property
    def D(self):
        return self[0]
    
    @property
    def S(self):
        return self[1]
    
    def __repr__(self) -> str:
        return super().__repr__()