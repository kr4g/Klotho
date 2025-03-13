from ...collections.sets import CombinationSet as CS

class Network:
    def __init__(self, nodes=None, edges=None):
        self._nodes = {}
        self._edges = {}
        
        if nodes:
            for node, attributes in nodes.items():
                self.add_node(node, **attributes)
        
        if edges:
            for edge, attributes in edges.items():
                self.add_edge(edge[0], edge[1], **attributes)
    
    def add_node(self, node, **attributes):
        self._nodes[node] = attributes
    
    def add_edge(self, node1, node2, **attributes):
        if node1 not in self._nodes or node2 not in self._nodes:
            raise ValueError("Both nodes must be added to the network before adding an edge.")
        
        if node1 not in self._edges:
            self._edges[node1] = {}
        if node2 not in self._edges:
            self._edges[node2] = {}

        self._edges[node1][node2] = attributes
        self._edges[node2][node1] = attributes
    
    @property
    def nodes(self):
        return self._nodes
    
    @property
    def edges(self):
        return self._edges

    def node_attributes(self, node):
        return self._nodes.get(node, {})
    
    def edge_attributes(self, node1, node2):
        return self._edges.get(node1, {}).get(node2, {})


class ComboNet:
    def __init__(self, cps:CS):
        self._cps = cps
        self._graph = self._make_network()

    def _make_network(self):
        graph = {}
        for combo in self._cps.combos:
            graph[combo] = {}

        for combo1 in self._cps.combos:
            for combo2 in self._cps.combos:
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

    def edge_weight(self, node1, node2):
        return self._graph.get(node1, {}).get(node2, 0)