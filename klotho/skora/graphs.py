from typing import Tuple
from itertools import count
import networkx as nx
import matplotlib.pyplot as plt


def plot_graph(G, attributes=None, invert=True, output_file=None):
    """
    Plot graph with node labels and optional attributes.
    
    Args:
        G: NetworkX graph
        output_file: Path to save the plot (if None, displays plot)
        attributes: List of node attributes to display below the label
    """
    root = [n for n, d in G.in_degree() if d == 0][0]
    pos = _hierarchy_pos(G, root, inverted=invert)
    labels = nx.get_node_attributes(G, 'label')
    
    plt.figure(figsize=(20, 5))
    ax = plt.gca()
    
    ax.set_facecolor('white')
    plt.gcf().set_facecolor('white')
    
    for node, (x, y) in pos.items():
        label_parts = [str(labels[node])]
        
        if attributes:
            for attr in attributes:
                attr_dict = nx.get_node_attributes(G, attr)
                if node in attr_dict:
                    label_parts.append(f"{attr_dict[node]}")
        
        label_text = "\n".join(label_parts)
        
        # Determine if node is a leaf
        is_leaf = len(list(G.neighbors(node))) == 0
        box_style = "circle,pad=0.3" if is_leaf else "square,pad=0.3"
        
        # Increased text size with fontsize=12
        ax.text(x, y, label_text, ha='center', va='center', zorder=5, fontsize=16,
                bbox=dict(boxstyle=box_style, fc="white", ec="black", linewidth=2))
    
    nx.draw_networkx_edges(G, pos, arrows=False, width=2.0)
    plt.axis('off')
    
    # Remove padding by setting margins to 0
    plt.margins(x=0)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    if output_file:
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
        plt.close()
    else:
        plt.show()

def _hierarchy_pos(G, root, width=1.5, vert_gap=0.2, xcenter=0.5, pos=None, parent=None, depth=0, inverted=True):
    """
    Simple hierarchical layout with consistent sibling spacing.
    """
    if pos is None:
        pos = {root: (xcenter, 1 if inverted else 0)}
    else:
        y = (1 - (depth * vert_gap)) if inverted else (depth * vert_gap)
        pos[root] = (xcenter, y)
    
    children = list(G.neighbors(root))
    if not isinstance(G, nx.DiGraph) and parent is not None:
        children.remove(parent)
    
    if children:
        dx = width / len(children)
        nextx = xcenter - width/2 + dx/2
        for child in children:
            _hierarchy_pos(G, child,
                         width=dx,
                         vert_gap=vert_gap,
                         xcenter=nextx,
                         pos=pos,
                         parent=root,
                         depth=depth+1,
                         inverted=inverted)
            nextx += dx
    return pos
