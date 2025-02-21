from typing import Tuple
from itertools import count
import networkx as nx
import matplotlib.pyplot as plt
from ..topos.graphs.trees.trees import Tree
from ..chronos.rhythm_trees.rt import RhythmTree
from ..chronos.temporal_units import TemporalUnit

def plot_tree(tree: Tree, attributes: list[str] | None = None, figsize: tuple[float, float] = (20, 5), 
             invert: bool = True, output_file: str | None = None) -> None:
    """
    Plot tree with node labels and optional attributes.
    
    Args:
        tree: Tree instance to plot
        attributes: List of node attributes to display (if None, shows only labels)
        figsize: Tuple of (width, height) for the figure size
        invert: If True, root is at top. If False, root is at bottom
        output_file: Path to save the plot (if None, displays plot)
    """
    G = tree.graph
    root = tree.root
    pos = _hierarchy_pos(G, 0, inverted=invert)
    
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    for node, (x, y) in pos.items():
        if attributes is None:
            label_text = str(G.nodes[node]['label'])
        else:
            label_parts = []
            for attr in attributes:
                if attr in G.nodes[node]:
                    label_parts.append(str(G.nodes[node][attr]))
            label_text = "\n".join(label_parts)
        
        is_leaf = len(list(G.neighbors(node))) == 0
        box_style = "circle,pad=0.3" if is_leaf else "square,pad=0.3"
        
        ax.text(x, y, label_text, ha='center', va='center', zorder=5, fontsize=16,
                bbox=dict(boxstyle=box_style, fc="black", ec="white", linewidth=2),
                color='white')
    
    nx.draw_networkx_edges(G, pos, arrows=False, width=2.0, edge_color='white')
    plt.axis('off')
    
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

def plot_ratios(ratios, total_value, output_file=None):
    """
    Plot ratios as horizontal bars with thin white borders.
    
    Args:
        ratios: List of ratios (positive for white segments, negative for grey "rests")
        total_value: Total value that the ratios divide (typically a fraction)
        output_file: Path to save the plot (if None, displays plot)
    """
    total_value = float(total_value)
    
    plt.figure(figsize=(25, 1))
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    total_ratio = sum(abs(r) for r in ratios)
    segment_widths = [abs(r) * total_value / total_ratio for r in ratios]
    
    positions = [0]
    for width in segment_widths[:-1]:
        positions.append(positions[-1] + width)
    
    bar_height = 0.2
    border_height = 0.6
    y_offset_bar = (1 - bar_height) / 2
    y_offset_border = (1 - border_height) / 2
    
    for i, (pos, width, ratio) in enumerate(zip(positions, segment_widths, ratios)):
        color = '#808080' if ratio < 0 else '#e6e6e6'
        ax.add_patch(plt.Rectangle((pos, y_offset_bar), width, bar_height, 
                                 facecolor=color,
                                 edgecolor=None))
    
    for pos in positions + [total_value]:
        ax.plot([pos, pos], [y_offset_border, y_offset_border + border_height], 
                color='white', linewidth=2)
    
    ax.set_xlim(-0.01, total_value + 0.01)
    ax.set_ylim(0, 1)
    plt.axis('off')
    
    plt.margins(x=0)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
        plt.close()
    else:
        plt.show()
