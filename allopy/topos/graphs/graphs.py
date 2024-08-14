from ..sets import CombinationProductSet as CPS

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

class CombNet:
    def __init__(self, cps:CPS):
        self._cps = cps.combos
        self._graph = self._make_network()

    def _make_network(self):
        graph = {}
        for combo in self._cps:
            graph[combo] = {}

        for combo1 in self._cps:
            for combo2 in self._cps:
                if combo1 != combo2:
                    common_factors = len(set(combo1) & set(combo2))
                    if common_factors > 0:
                        graph[combo1][combo2] = common_factors
                        graph[combo2][combo1] = common_factors

        return graph

    @property
    def cps(self):
        return self._cps
    
    @property
    def graph(self):
        return self._graph

    def get_edge_weight(self, node1, node2):
        return self._graph.get(node1, {}).get(node2, 0)