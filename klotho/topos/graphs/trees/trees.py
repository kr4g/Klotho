import networkx as nx

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
