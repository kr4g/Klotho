from ..trees import *
import networkx as nx

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

def rotate_children(subdivs:tuple, n:int=1) -> tuple:
    factors = factor_children(subdivs)
    n = n % len(factors)
    factors = factors[n:] + factors[:n]
    return refactor_children(subdivs, factors)

def rotate_tree(tree:Tree, n:int=1) -> Tree:
    return Tree(tree._root, rotate_children(tree._children, n))

def prune_graph(G:nx.DiGraph, max_depth:int) -> nx.DiGraph:
    pruned_graph = nx.DiGraph()
    root = [n for n, d in G.in_degree() if d == 0][0]
    queue = [(root, 0)]  # (node, depth)
    
    while queue:
        node, depth = queue.pop(0)
        if depth <= max_depth:
            pruned_graph.add_node(node, label=G.nodes[node]['label'])
            if depth < max_depth:
                for neighbor in G.neighbors(node):
                    pruned_graph.add_edge(node, neighbor)
                    queue.append((neighbor, depth + 1))
    
    return pruned_graph