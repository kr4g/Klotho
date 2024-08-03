# def graph_tree(root, S:Tuple) -> nx.DiGraph:
#     def add_nodes(graph, parent_id, children_list):        
#         for child in children_list:
#             if isinstance(child, int):
#                 child_id = next(unique_id)
#                 graph.add_node(child_id, label=child)
#                 graph.add_edge(parent_id, child_id)
#             elif isinstance(child, tuple):
#                 duration, subdivisions = child
#                 duration_id = next(unique_id)
#                 graph.add_node(duration_id, label=duration)
#                 graph.add_edge(parent_id, duration_id)
#                 add_nodes(graph, duration_id, subdivisions)
#     unique_id = count()
#     G = nx.DiGraph()
#     root_id = next(unique_id)
#     G.add_node(root_id, label=root)
#     add_nodes(G, root_id, S)
#     return G

# def graph_depth(G:nx.DiGraph) -> int:
#     return max(nx.single_source_shortest_path_length(G, 0).values())

# def plot_graph(G):
#     root = [n for n, d in G.in_degree() if d == 0][0]
#     pos = _hierarchy_pos(G, root)
#     labels = nx.get_node_attributes(G, 'label')
    
#     plt.figure(figsize=(10, 5))
#     ax = plt.gca()
#     for node, (x, y) in pos.items():
#         ax.text(x, y, labels[node], ha='center', va='center', zorder=5,
#                 bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="black"))
    
#     nx.draw_networkx_edges(G, pos, arrows=False, width=2.0)
#     plt.axis('off')
#     plt.show()

# def _hierarchy_pos(G, root, width=1.0, vert_gap=0.1, xcenter=0.5, pos=None, parent=None, parsed=None, depth=0):
#     if pos is None:
#         pos = {root:(xcenter, 1)}
#         parsed = [root]
#     else:
#         y = 1 - (depth * vert_gap)
#         pos[root] = (xcenter, y)
#     children = list(G.neighbors(root))
#     if not isinstance(G, nx.DiGraph) and parent is not None:
#         children.remove(parent)
#     if len(children) != 0:
#         dx = width / len(children)
#         nextx = xcenter - width / 2 - dx / 2
#         for child in children:
#             nextx += dx
#             _hierarchy_pos(G, child, width=dx, vert_gap=vert_gap, xcenter=nextx, pos=pos, parent=root, parsed=parsed, depth=depth+1)
#     return pos

# def prune_graph(G:nx.DiGraph, max_depth:int) -> nx.DiGraph:
#     pruned_graph = nx.DiGraph()
#     root = [n for n, d in G.in_degree() if d == 0][0]
#     queue = [(root, 0)]  # (node, depth)
    
#     while queue:
#         node, depth = queue.pop(0)
#         if depth <= max_depth:
#             pruned_graph.add_node(node, label=G.nodes[node]['label'])
#             if depth < max_depth:
#                 for neighbor in G.neighbors(node):
#                     pruned_graph.add_edge(node, neighbor)
#                     queue.append((neighbor, depth + 1))
    
#     return pruned_graph