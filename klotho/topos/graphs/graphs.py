import networkx as nx
import hypernetx as hnx
import pandas as pd

class Graph:
    def __init__(self, graph: nx.Graph):
        self._graph = graph
        self._meta = pd.DataFrame(index=[''])
        
    @property
    def graph(self):
        return self._graph
    
    @property
    def nodes(self):
        return self._graph.nodes
    
    def __getitem__(self, node):
        return self._graph.nodes[node]
    
    def __len__(self):
        return len(self._graph)
    
    def __str__(self):
        return str(self._graph)
    
    def __repr__(self):
        return repr(self._graph)
    
    def __iter__(self):
        return iter(self._graph)
    
    