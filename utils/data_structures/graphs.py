# import networkx as nx
# from itertools import count
# import matplotlib.pyplot as plt
# from typing import Tuple, Dict, Any
# from allopy.chronos.rhythm_trees import rt_algorithms as rt_alg
# from fractions import Fraction

# class Graph:
#     def __init__(self, root: int, S: Tuple):
#         self.G = nx.DiGraph()
#         self.node_info = {}
#         self._graph_tree(root, S)

#     def _graph_tree(self, root: int, S: Tuple):
#         def add_nodes(graph, parent_id, children_list):
#             for child in children_list:
#                 if isinstance(child, (int, float)):
#                     child_id = next(unique_id)
#                     graph.add_node(child_id, label=child)
#                     self.node_info[child_id] = {}
#                     graph.add_edge(parent_id, child_id)
#                 elif isinstance(child, tuple):
#                     duration, subdivisions = child
#                     duration_id = next(unique_id)
#                     graph.add_node(duration_id, label=duration)
#                     self.node_info[duration_id] = {}
#                     graph.add_edge(parent_id, duration_id)
#                     add_nodes(graph, duration_id, subdivisions)
#         unique_id = count()
#         root_id = next(unique_id)
#         self.G.add_node(root_id, label=root)
#         self.node_info[root_id] = {}
#         add_nodes(self.G, root_id, S)
#         return self.G

#     def calc_children(self, node: int = 0, level: int = 0):
#         children = list(self.G.successors(node))
#         if not children: # leaf node means it's a note event
#             hdb = rt_alg.head_dots_beams(abs(self.G.nodes[node]['label']))
#             print(f"{hdb[0]}, {hdb[1]} dot(s), and {hdb[2]} beam(s)")
#             return
#         child_sum = int(sum(abs(self.G.nodes[child]['label']) for child in children))
#         # print(f'level {level}, n: {self.G.nodes[node]["label"]}, sum: {child_sum}')
#         # print(self.G.nodes[node]['label'], type(self.G.nodes[node]['label']))
#         numer = self.G.nodes[node]['label'].numerator
#         if (tup := rt_alg.create_tuplet((numer, (child_sum,)))) is not None:
#             self.node_info[level + 1] = tup
#         for child in children:
#             meas = str(self.G.nodes[node]['label']).replace('-', '')
#             meas = Fraction(meas)
#             if level == 0:
#                 if not (meas.numerator / child_sum).is_integer() and not (child_sum / meas.numerator).is_integer():
#                     # meas = Fraction(child_sum, meas.denominator)
#                     meas = Fraction(child_sum, rt_alg.symbolic_approx(meas.denominator))
#             meas = Fraction(meas.numerator, rt_alg.symbolic_approx(meas.denominator))
#             # print(f"meas: {meas}, child_sum: {child_sum}")
#             d = abs(self.G.nodes[child]['label'])
#             new_label = rt_alg.symbolic_duration(d, meas, (child_sum,))
#             new_label = Fraction(abs(new_label.numerator), rt_alg.symbolic_approx(abs(new_label.denominator)))
#             self.G.nodes[child]['label'] = new_label
#         for child in children:
#             self.calc_children(child, level + 1)

#     def notate_tree(self, node: int = 0, level: int = 0):
#         if level == 0:
#             return f"\\time {self.G.nodes[node]['label']}\n{self.notate_tree(node, level + 1)}"
#         result = ""
#         children = list(self.G.successors(node))
#         tup = None
#         if not children:
#             result += f"{self.G.nodes[node]['label']} "
#         else:
#             if (tup := self.node_info[level]):
#                 result += f"\\tuplet {tup[0]}/{tup[1]} " + "{ "
#             for child in children:
#                 result += self.notate_tree(child, level + 1)
#         if tup:
#             result += "} "
#         return result

#     def graph_depth(self) -> int:
#         return max(nx.single_source_shortest_path_length(self.G, 0).values())

#     def prune_graph(self, max_depth: int) -> 'Graph':
#         pruned_graph = Graph()
#         queue = [(list(self.G.in_degree())[0][0], 0)]  # (node, depth)

#         while queue:
#             node, depth = queue.pop(0)
#             if depth <= max_depth:
#                 if node not in pruned_graph.G:
#                     pruned_graph.G.add_node(node, label=self.G.nodes[node]['label'])
#                     pruned_graph.node_info[node] = self.node_info[node]
#                 if depth < max_depth:
#                     for neighbor in self.G.neighbors(node):
#                         if neighbor not in pruned_graph.G:
#                             pruned_graph.G.add_node(neighbor, label=self.G.nodes[neighbor]['label'])
#                             pruned_graph.node_info[neighbor] = self.node_info[neighbor]
#                         pruned_graph.G.add_edge(node, neighbor)
#                         queue.append((neighbor, depth + 1))

#         return pruned_graph

#     def plot_tree(self, figsize=(10, 5)):
#         root = [n for n, d in self.G.in_degree() if d == 0][0]
#         pos = self._hierarchy_pos(root)
#         labels = nx.get_node_attributes(self.G, 'label')
        
#         plt.figure(figsize=figsize)
#         ax = plt.gca()
#         for node, (x, y) in pos.items():
#             ax.text(x, y, labels[node], ha='center', va='center', zorder=5,
#                     bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="black"))
        
#         nx.draw_networkx_edges(self.G, pos, arrows=False, width=2.0)
#         plt.axis('off')
#         plt.show()

#     def _hierarchy_pos(self, root, width=1.0, vert_gap=0.1, xcenter=0.5, pos=None, parent=None, depth=0):
#         if pos is None:
#             pos = {root: (xcenter, 1)}
#         else:
#             pos[root] = (xcenter, 1 - depth * vert_gap)
        
#         children = list(self.G.neighbors(root))
#         if not isinstance(self.G, nx.DiGraph) and parent is not None:
#             children.remove(parent)
        
#         if len(children) != 0:
#             dx = width / len(children)
#             nextx = xcenter - width / 2 - dx / 2
#             for child in children:
#                 nextx += dx
#                 self._hierarchy_pos(child, width=dx, vert_gap=vert_gap, xcenter=nextx, pos=pos, parent=root, depth=depth + 1)
        
#         return pos
