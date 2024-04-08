import networkx as nx

def graph_cps(combos:tuple):
    G = nx.Graph()    
    # each combination is a node (vertex) in the graph
    for combo in combos:
        G.add_node(combo)

    # edges are between nodes that share at least one common factor
    for combo1 in combos:
        for combo2 in combos:
            if combo1 != combo2 and set(combo1).intersection(combo2):
                G.add_edge(combo1, combo2)
    return G

def find_cliques(G:nx.Graph, n:int):
    cliques = nx.enumerate_all_cliques(G)
    return tuple(tuple(clique) for clique in cliques if len(clique) == n)
