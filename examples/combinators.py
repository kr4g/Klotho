import networkx as nx

def create_kary_tree(k, depth):
    G = nx.Graph()
    nodes = ['0']
    for level in range(1, depth + 1):
        new_nodes = []
        for node in nodes:
            for i in range(k):
                new_node = f"{node}-{i}"
                G.add_edge(node, new_node)
                new_nodes.append(new_node)
        nodes = new_nodes
    return G

def print_graph(G, title):
    print(f"\n{title}")
    print("Nodes:", G.nodes())
    print("Edges:", G.edges())

def K(x):
    return lambda y: x

def I(x):
    return x

def S(x):
    return lambda y: lambda z: x(z)(y(z))

def apply_combinator(G, combinator, node):
    H = G.copy()
    if combinator == K:
        # K combinator keeps the node and removes its children
        children = list(H.neighbors(node))
        H.remove_edges_from([(node, child) for child in children])
    elif combinator == I:
        # I combinator does nothing (identity)
        pass
    elif combinator == S:
        # S combinator: we'll interpret this as connecting grandchildren to the node
        children = list(H.neighbors(node))
        for child in children:
            grandchildren = list(H.neighbors(child))
            for grandchild in grandchildren:
                H.add_edge(node, grandchild)
    return H

# Create a ternary tree of depth 2
G = create_kary_tree(k=3, depth=2)
print_graph(G, "Initial Ternary Tree")

# Apply K combinator to node '0'
G_K = apply_combinator(G, K, '0')
print_graph(G_K, "After applying K combinator to node '0'")

# Apply I combinator to node '0'
G_I = apply_combinator(G, I, '0')
print_graph(G_I, "After applying I combinator to node '0'")

# Apply S combinator to node '0'
G_S = apply_combinator(G, S, '0')
print_graph(G_S, "After applying S combinator to node '0'")