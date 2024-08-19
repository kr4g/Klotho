import sys
from pathlib import Path

root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))

from klotho.topos.graphs import Tree
# from klotho.skora.graphs import graph_tree
from klotho.topos import autoref
from klotho.topos.graphs.graph_algorithms import factor_children, refactor_children
from klotho.chronos.rhythm_trees import RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import auto_subdiv
from klotho.skora.graphs import *
from klotho.skora.animate import *

import os
import networkx as nx

def find_leaf_nodes(G):
    return [node for node in G.nodes() if G.out_degree(node) == 0]

def prune_leaf(G, index=0):
    G_copy = G.copy()
    leaf_nodes = find_leaf_nodes(G_copy)
    if not leaf_nodes:
        return G_copy
    sorted_leaves = sorted(leaf_nodes)
    if index < 0:
        index += len(sorted_leaves)
    leaf_to_remove = sorted_leaves[index]
    parent_nodes = list(G_copy.predecessors(leaf_to_remove))
    G_copy.remove_node(leaf_to_remove)
    for parent_node in parent_nodes:
        children = list(G_copy.successors(parent_node))
        if not children:
            G_copy.remove_node(parent_node)
    return G_copy

output_dir = "/Users/ryanmillett/Klotho/examples/thesis/output"
os.makedirs(output_dir, exist_ok=True)

# Example usage:
R = '2/4'
# S = ((17, ((15, ((13, (13, 9, 5, 2)), 7)), (13, (7, 5, 2)))), (13, (6, 9)))
S = autoref((5, 2, 3))
S = refactor_children(S, tuple(reversed(factor_children(S))))
mS = []
for i, d in enumerate(S):
    mS.append((d[0], auto_subdiv(d[1], n=i + 1)))
mS = tuple(mS)

image_files = []
rt = RT(meas=R, subdivisions=mS)
# print(rt)
for i in range(len(rt.ratios)+1):
    G = graph_tree(rt.meas, rt.subdivisions)
    G = prune_leaf(G, index=-1)
    output_file = os.path.join(output_dir, f"graph_{i}a.png")
    plot_graph(G, output_file)
    image_files.append(output_file)
    rt = RT.from_tree(Tree.from_graph(G))
    print(rt)

gif_file = os.path.join(output_dir, 'graph_animation_B_v2.gif')
duration_per_frame = 500
# reverse the images
image_files = image_files[::-1]
create_gif(image_files, gif_file, duration_per_frame)
# delete the images
for image_file in image_files:
    os.remove(image_file)
