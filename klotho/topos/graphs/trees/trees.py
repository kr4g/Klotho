import networkx as nx
from itertools import count

class Tree:
    def __init__(self, root, children:tuple):
        self._root = root
        self._children = children
        self._graph = None
        self._depth = None
        self._leaf_nodes = None
    
    @property
    def root(self):
        return self._root
    
    @property
    def children(self):
        return self._children
    
    @property
    def leaf_nodes(self):
        """Returns leaf nodes in depth-first order"""
        if self._leaf_nodes is None:
            self._leaf_nodes = [n for n in nx.dfs_preorder_nodes(self.graph) 
                if self._graph.out_degree(n) == 0]
        return self._leaf_nodes
    
    @property
    def graph(self):
        if self._graph is None:
            self._graph = self._graph_tree()
        return self._graph
    
    @property
    def depth(self):
        if self._depth is None:
            self._depth = self._calculate_depth()
        return self._depth
    
    def _graph_tree(self) -> nx.DiGraph:
        def add_nodes(graph, parent_id, children_list):        
            for child in children_list:
                if isinstance(child, int):
                    child_id = next(unique_id)
                    graph.add_node(child_id, label=child)
                    graph.add_edge(parent_id, child_id)
                elif isinstance(child, tuple):
                    duration, subdivisions = child
                    duration_id = next(unique_id)
                    graph.add_node(duration_id, label=duration)
                    graph.add_edge(parent_id, duration_id)
                    add_nodes(graph, duration_id, subdivisions)
        unique_id = count()
        G = nx.DiGraph()
        root_id = next(unique_id)
        G.add_node(root_id, label=self._root)
        add_nodes(G, root_id, self._children)
        return G
    
    def _calculate_depth(self) -> int:
        if self._depth is None:
            self._depth = max(nx.single_source_shortest_path_length(self._graph, 0).values())
        return self._depth
    
    @classmethod
    def from_graph(cls, G):
        root_node = [n for n, d in G.in_degree() if d == 0]
        if len(root_node) != 1:
            raise ValueError("Graph must have exactly one root node.")
        
        root_id = root_node[0]
        root = G.nodes[root_id]['label']
        
        def _build_children(node_id):
            children = list(G.successors(node_id))
            if not children:
                return G.nodes[node_id]['label']
            
            result = []
            for child_id in children:
                child_label = G.nodes[child_id]['label']
                child_tuple = _build_children(child_id)
                
                if isinstance(child_tuple, tuple):
                    result.append((child_label, child_tuple))
                else:
                    result.append(child_label)
            
            return tuple(result) if len(result) > 1 else (result[0],)
        
        children = _build_children(root_id)
        return cls(root, children)
