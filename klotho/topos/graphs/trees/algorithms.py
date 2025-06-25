from ..trees import Tree
import networkx as nx
from typing import Tuple
from itertools import count

__all__ = [
    'factor_children',
    'refactor_children',
    'get_signs',
    'get_abs',
    'rotate_children',
    'rotate_tree',
    'print_subdivisons',
    'prune_to_depth',
    'prune_leaves',
    'path_to_node',
    'extract_subtree',
    'are_isomorphic',
    'get_levels'
]

def factor_children(subdivs:tuple) -> tuple:
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor_children(subdivs:tuple, factors:tuple) -> tuple:
    def _refactor(subdivs, index):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                nested_result, index = _refactor(element, index)
                result.append(nested_result)
            else:
                result.append(factors[index])
                index += 1
        return tuple(result), index
    return _refactor(subdivs, 0)[0]

def get_signs(subdivs):
        signs = []
        for element in subdivs:
            if isinstance(element, tuple):
                signs.extend(get_signs(element))
            else:
                signs.append(1 if element >= 0 else -1)
        return signs
    
def get_abs(subdivs):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                result.extend(get_abs(element))
            else:
                result.append(abs(element))
        return result

def rotate_children(subdivs: tuple, n: int = 1, preserve_signs: bool = False) -> tuple:
    """Rotates the children of a nested tuple structure.
    
    Args:
        subdivs: Nested tuple structure to rotate
        n: Number of positions to rotate
        preserve_signs: If True, preserves the signs of numbers while rotating their absolute values
    """
    if not preserve_signs:
        factors = factor_children(subdivs)
        n = n % len(factors)
        factors = factors[n:] + factors[:n]
        return refactor_children(subdivs, factors)
    
    signs = get_signs(subdivs)
    abs_values = get_abs(subdivs)
    
    n = n % len(abs_values)
    rotated_values = abs_values[n:] + abs_values[:n]
    
    signed_values = [val * sign for val, sign in zip(rotated_values, signs)]
    
    return refactor_children(subdivs, tuple(signed_values))

def rotate_tree(tree:Tree, n:int=1) -> Tree:
    return Tree(tree.group.D, rotate_children(tree.group.S, n))

def print_subdivisons(subdivs):
    """Format nested tuple structure removing commas."""
    if isinstance(subdivs, (tuple, list)):
        inner = ' '.join(str(print_subdivisons(x)) for x in subdivs)
        return f"({inner})"
    return str(subdivs)

def prune_to_depth(tree: Tree, max_depth: int) -> Tree:
    """Prunes the tree to a maximum depth, removing all nodes beyond that depth."""
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    
    G = tree.graph.copy()
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
    
    G = tree.graph.copy()
    for _ in range(n):
        leaves = [node for node in G.nodes() if G.out_degree(node) == 0]
        G.remove_nodes_from(leaves)
        if len(G) == 1:  # Only root remains
            break
    
    return Tree.from_graph(G)

def path_to_node(tree: Tree, node_id: int) -> list[int]:
    """Returns the path from root to the specified node as a list of node IDs."""
    if node_id not in tree.graph:
        raise ValueError(f"Node {node_id} not found in tree")
    
    try:
        path = nx.shortest_path(tree.graph, 0, node_id)
        return path
    except nx.NetworkXNoPath:
        raise ValueError(f"No path exists to node {node_id}")

def extract_subtree(tree: Tree, root_id: int) -> Tree:
    """Creates a new tree from the subtree rooted at the specified node."""
    if root_id not in tree.graph:
        raise ValueError(f"Node {root_id} not found in tree")
    
    G = tree.graph.copy()
    descendants = nx.descendants(G, root_id)
    descendants.add(root_id)
    subtree = G.subgraph(descendants).copy()
    
    # Relabel nodes to ensure root is 0
    mapping = {root_id: 0}
    counter = count(1)
    for node in subtree.nodes():
        if node != root_id:
            mapping[node] = next(counter)
    subtree = nx.relabel_nodes(subtree, mapping)
    
    return Tree.from_graph(subtree)

def are_isomorphic(tree1: Tree, tree2: Tree) -> bool:
    """Returns True if the two trees are structurally identical."""
    return nx.is_isomorphic(tree1.graph, tree2.graph, 
                           node_match=lambda x, y: x['label'] == y['label'])

def get_levels(tree: Tree) -> list[list[int]]:
    """Returns lists of nodes grouped by their depth in the tree."""
    depths = nx.single_source_shortest_path_length(tree.graph, 0)
    max_depth = max(depths.values())
    
    levels = [[] for _ in range(max_depth + 1)]
    for node, depth in depths.items():
        levels[depth].append(node)
    
    return levels

