from ..trees import Tree
import networkx as nx

__all__ = [
    'prune_to_depth',
    'prune_leaves',
    'path_to_node',
    'get_levels'
]

def prune_to_depth(tree: Tree, max_depth: int) -> Tree:
    """Prunes the tree to a maximum depth, removing all nodes beyond that depth."""
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    
    G = tree._graph.copy()
    depths = nx.single_source_shortest_path_length(G, 0)
    nodes_to_remove = [n for n, depth in depths.items() if depth > max_depth]
    G.remove_nodes_from(nodes_to_remove)
    
    return Tree.from_graph(G)

def prune_leaves(tree: Tree, n: int) -> Tree:
    """Prunes n levels from each branch, starting from the leaves."""
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return tree
    
    G = tree._graph.copy()
    for _ in range(n):
        leaves = [node for node in G.nodes() if G.out_degree(node) == 0]
        G.remove_nodes_from(leaves)
        if len(G) == 1:  # Only root remains
            break
    
    return Tree.from_graph(G)

def path_to_node(tree: Tree, node_id: int) -> list[int]:
    """Returns the path from root to the specified node as a list of node IDs."""
    if node_id not in tree._graph:
        raise ValueError(f"Node {node_id} not found in tree")
    
    try:
        path = nx.shortest_path(tree._graph, 0, node_id)
        return path
    except nx.NetworkXNoPath:
        raise ValueError(f"No path exists to node {node_id}")

def get_levels(tree: Tree) -> list[list[int]]:
    """Returns lists of nodes grouped by their depth in the tree."""
    depths = nx.single_source_shortest_path_length(tree._graph, 0)
    max_depth = max(depths.values())
    
    levels = [[] for _ in range(max_depth + 1)]
    for node, depth in depths.items():
        levels[depth].append(node)
    
    return levels

