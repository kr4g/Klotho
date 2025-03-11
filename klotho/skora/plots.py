from typing import Tuple
from itertools import count
import networkx as nx
import matplotlib.pyplot as plt
from ..topos.graphs.trees.trees import Tree
from ..chronos.rhythm_trees.rt import RhythmTree
from ..chronos.temporal_units import TemporalUnit
from fractions import Fraction
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def plot_tree(tree: Tree, attributes: list[str] | None = None, figsize: tuple[float, float] = (20, 5), 
             invert: bool = True, output_file: str | None = None) -> None:
    """
    Visualize a tree structure with customizable node appearance and layout.
    
    Renders a tree graph with nodes positioned hierarchically, where each node is displayed
    with either its label or specified attributes. Nodes are drawn as squares (internal nodes)
    or circles (leaf nodes) with white borders on a black background.
    
    Args:
        tree: Tree instance to visualize
        attributes: List of node attributes to display instead of labels. If None, shows only labels.
                   Special values "node_id", "node", or "id" will display the node identifier.
        figsize: Width and height of the output figure in inches
        invert: When True, places root at the top; when False, root is at the bottom
        output_file: Path to save the visualization (displays plot if None)
    """
    def _hierarchy_pos(G, root, width=1.5, vert_gap=0.2, xcenter=0.5, pos=None, parent=None, depth=0, inverted=True):
        """
        Position nodes in a hierarchical layout optimized for both wide and deep trees.
        
        Allocates horizontal space based on the structure of the tree, giving more
        room to branches with deeper chains and ensuring proper vertical spacing.
        
        Returns a dictionary mapping each node to its (x, y) position.
        """
        if pos is None:
            max_depth = _get_max_depth(G, root)
            vert_gap = min(0.2, 0.8 / max(max_depth, 1))
            max_breadth = _get_max_breadth(G, root)
            width = max(1.5, 0.8 * max_breadth)
            pos = {root: (xcenter, 1 if inverted else 0)}
        else:
            y = (1 - (depth * vert_gap)) if inverted else (depth * vert_gap)
            pos[root] = (xcenter, y)
        
        children = list(G.neighbors(root))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if children:
            chain_depths = {child: _get_max_depth(G, child, parent=root) for child in children}
            total_depth = sum(chain_depths.values())
            
            if len(children) == 1:
                dx = width * 0.8
            else:
                dx = width / len(children)
            
            nextx = xcenter - width/2 + dx/2
            
            for child in children:
                depth_factor = 1.0
                if total_depth > 0 and len(children) > 1:
                    depth_factor = 0.5 + (0.5 * chain_depths[child] / total_depth)
                
                child_width = dx * depth_factor * 1.5
                
                _hierarchy_pos(G, child,
                             width=child_width,
                             vert_gap=vert_gap,
                             xcenter=nextx,
                             pos=pos,
                             parent=root,
                             depth=depth+1,
                             inverted=inverted)
                nextx += dx
        return pos
    
    def _count_leaves(G, node, parent=None):
        """
        Count the number of leaf nodes in the subtree rooted at node.
        
        A leaf node is defined as a node with no children.
        """
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if not children:
            return 1
        
        return sum(_count_leaves(G, child, node) for child in children)
    
    def _get_max_depth(G, node, parent=None, current_depth=0):
        """
        Calculate the maximum depth of the tree or subtree.
        
        Returns the longest path length from the given node to any leaf.
        """
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if not children:
            return current_depth
        
        return max(_get_max_depth(G, child, node, current_depth + 1) for child in children)
    
    def _get_max_breadth(G, root, parent=None):
        """
        Calculate the maximum breadth of the tree.
        
        Returns the maximum number of nodes at any single level of the tree.
        """
        nodes_by_level = {}
        
        def _count_by_level(node, level=0, parent=None):
            if level not in nodes_by_level:
                nodes_by_level[level] = 0
            nodes_by_level[level] += 1
            
            children = list(G.neighbors(node))
            if parent is not None and parent in children:
                children.remove(parent)
            
            for child in children:
                _count_by_level(child, level+1, node)
        
        _count_by_level(root, parent=parent)
        
        return max(nodes_by_level.values()) if nodes_by_level else 1
    
    G = tree.graph
    root = tree.root
    pos = _hierarchy_pos(G, root, inverted=invert)
    
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    for node, (x, y) in pos.items():
        if attributes is None:
            label_text = str(G.nodes[node]['label']) if G.nodes[node]['label'] is not None else ''
        else:
            label_parts = []
            for attr in attributes:
                if attr in {"node_id", "node", "id"}:
                    label_parts.append(str(node))
                elif attr in G.nodes[node]:
                    value = G.nodes[node][attr]
                    label_parts.append(str(value) if value is not None else '')
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

def plot_ratios(ratios, output_file=None):
    """
    Plot ratios as horizontal bars with thin white borders.
    
    Args:
        ratios: List of ratios (positive for white segments, negative for grey "rests")
        output_file: Path to save the plot (if None, displays plot)
    """
    plt.figure(figsize=(25, 1))
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    total_ratio = sum(abs(r) for r in ratios)
    # Normalize segment widths to ensure they span the entire plot width
    segment_widths = [abs(r) / total_ratio for r in ratios]
    
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
                                 edgecolor=None, alpha=0.4 if ratio < 0 else 1))
    
    for pos in positions + [1.0]:  # Use 1.0 as the final position since we normalized
        ax.plot([pos, pos], [y_offset_border, y_offset_border + border_height], 
                color='#aaaaaa', linewidth=2)
    
    ax.set_xlim(-0.01, 1.01)  # Set x-axis limits to slightly beyond [0,1]
    ax.set_ylim(0, 1)
    plt.axis('off')
    
    plt.margins(x=0)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
        plt.close()
    else:
        plt.show()

def plot_graph(G: nx.Graph, figsize: tuple[float, float] = (10, 10), 
               node_size: float = 1000, font_size: float = 12,
               layout: str = 'spring', k: float = 1,
               show_edge_labels: bool = True,
               weighted_edges: bool = False,
               path: list | None = None,
               output_file: str | None = None) -> None:
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    layouts = {
        'spring': lambda: nx.spring_layout(G, k=k),
        'circular': lambda: nx.circular_layout(G),
        'random': lambda: nx.random_layout(G),
        'shell': lambda: nx.shell_layout(G),
        'spectral': lambda: nx.spectral_layout(G),
        'kamada_kawai': lambda: nx.kamada_kawai_layout(G)
    }
    
    pos = layouts.get(layout, layouts['spring'])()
    
    if path:
        path_edges = list(zip(path[:-1], path[1:]))
        non_path_edges = [(u, v) for u, v in G.edges() if (u, v) not in path_edges and (v, u) not in path_edges]
        
        if weighted_edges and non_path_edges:
            weights = [G[u][v]['weight'] for u, v in non_path_edges]
            min_weight, max_weight = min(weights), max(weights)
            width_scale = lambda w: 1 + 3 * ((w - min_weight) / (max_weight - min_weight) if max_weight > min_weight else 0)
            edge_widths = [width_scale(w) for w in weights]
            nx.draw_networkx_edges(G, pos, edgelist=non_path_edges, edge_color='#808080', width=edge_widths, alpha=0.5)
        else:
            nx.draw_networkx_edges(G, pos, edgelist=non_path_edges, edge_color='#808080', width=2, alpha=0.5)
        
        if path_edges:
            colors = plt.cm.viridis(np.linspace(0, 1, len(path_edges)))
            for (u, v), color in zip(path_edges, colors):
                nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], edge_color=[color], width=3)
    else:
        if weighted_edges:
            weights = list(nx.get_edge_attributes(G, 'weight').values())
            min_weight, max_weight = min(weights), max(weights)
            width_scale = lambda w: 1 + 3 * ((w - min_weight) / (max_weight - min_weight) if max_weight > min_weight else 0)
            edge_widths = [width_scale(w) for w in weights]
            nx.draw_networkx_edges(G, pos, edge_color='#808080', width=edge_widths)
        else:
            nx.draw_networkx_edges(G, pos, edge_color='#808080', width=2)
    
    if path:
        non_path_nodes = [node for node in G.nodes() if node not in path]
        nx.draw_networkx_nodes(G, pos, nodelist=non_path_nodes, node_color='black',
                             node_size=node_size, edgecolors='white', linewidths=2)
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(path)))
        nx.draw_networkx_nodes(G, pos, nodelist=path, node_color=colors,
                             node_size=node_size, edgecolors='white', linewidths=2)
    else:
        nx.draw_networkx_nodes(G, pos, node_color='black', node_size=node_size,
                             edgecolors='white', linewidths=2)
    
    labels = {node: G.nodes[node]['value'] for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=labels, font_color='white', font_size=font_size)
    
    if show_edge_labels:
        edge_weights = {(u,v): f'{w:.2f}' for (u,v), w in nx.get_edge_attributes(G, 'weight').items()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_weights,
                                   font_color='white', font_size=font_size,
                                   bbox=dict(facecolor='black', edgecolor='none', alpha=0.6),
                                   label_pos=0.5, rotate=False)
    
    plt.axis('off')
    plt.margins(x=0.1, y=0.1)
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0, 
                    facecolor='black', edgecolor='none')
        plt.close()
    else:
        plt.show()

def plot_ut(ut, height=100):
    fig = make_subplots(rows=1, cols=1)
    
    events = ut.events
    
    # Plot each event as a separate trace
    for _, event in events.iterrows():
        fig.add_trace(
            go.Bar(
                base=[event['start']],  # Single value in a list
                x=[abs(event['duration'])],  # Single value in a list
                y=['Timeline'],  # All events on same timeline
                orientation='h',
                marker=dict(
                    color='#808080' if event['is_rest'] else '#e6e6e6',
                    line=dict(color='white', width=1)
                ),
                hovertemplate=(
                    'Start: %{base:.2f}s<br>'
                    'Duration: %{x:.2f}s<br>'
                    'End: %{customdata[0]:.2f}s<br>'
                    'Ratio: %{customdata[1]}<br>'
                    'Type: ' + ut.type.value +
                    '<extra></extra>'
                ),
                customdata=[[event['end'], str(event['metric_ratio'])]]
            )
        )

    fig.update_layout(
        title=dict(
            text=f'Tempus: {ut.tempus} | Beat: {str(ut.beat)} = {ut.bpm} BPM',
            x=0,
            font=dict(color='white')
        ),
        plot_bgcolor='black',
        paper_bgcolor='black',
        showlegend=False,
        height=height,
        margin=dict(l=50, r=20, t=40, b=20),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            fixedrange=True,
            range=[-0.5, 0.5]
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor='#333333',
            color='white',
            title='Time (seconds)',
            range=[ut.offset, ut.offset + ut.duration * 1.1]
        ),
        barmode='overlay'  # Changed to overlay mode
    )

    return fig

def plot_rt(rt: RhythmTree, layout: str = 'containers', figsize: tuple[float, float] = (20, 5), 
            invert: bool = True, output_file: str | None = None, 
            attributes: list[str] | None = None, vertical_lines: bool = False) -> None:
    """
    Visualize a rhythm tree with customizable layout options.
    
    Args:
        rt: RhythmTree instance to visualize
        layout: 'default' uses the standard tree visualization, 'containers' shows proportional containers
        figsize: Width and height of the output figure in inches
        invert: When True, places root at the top; when False, root is at the bottom
        output_file: Path to save the visualization (displays plot if None)
        attributes: List of node attributes to display (only used with 'default' layout)
        vertical_lines: When True, draws vertical lines at block boundaries
    """
    if layout == 'default':
        return plot_tree(rt, attributes=attributes, figsize=figsize, invert=invert, output_file=output_file)
    
    elif layout == 'containers':
        
        def get_node_scaling(node, rt, min_scale=0.5):
            """Calculate the height scaling for a node based on its position in the tree."""
            if rt.graph.out_degree(node) == 0:
                return min_scale
            
            current_depth = rt.depth_of(node)
            
            # Find the maximum depth of any leaf descendant from this 
            max_descendant_depth = current_depth
            for descendant in nx.descendants(rt.graph, node):
                if rt.graph.out_degree(descendant) == 0:  # If it's a leaf
                    descendant_depth = rt.depth_of(descendant)
                    max_descendant_depth = max(max_descendant_depth, descendant_depth)
            
            levels_to_leaf = max_descendant_depth - current_depth
            
            if levels_to_leaf == 0:  # This is a leaf
                return min_scale
            
            # Scale linearly from 1.0 (at root or nodes far from leaves) to min_scale (at leaves)
            # The more levels to a leaf, the closer to 1.0
            # We use a maximum of 3 levels for full scaling to avoid too much variation
            max_levels_for_scaling = 3
            scaling_factor = 1.0 - ((1.0 - min_scale) * min(1.0, (max_levels_for_scaling - levels_to_leaf) / max_levels_for_scaling))
            
            return scaling_factor
        
        plt.figure(figsize=figsize)
        ax = plt.gca()
        
        ax.set_facecolor('black')
        plt.gcf().set_facecolor('black')
        
        max_depth = rt.depth
        
        margin = 0.01
        usable_height = 1.0 - (2 * margin)
        
        level_positions = []
        level_height = usable_height / (max_depth + 1)
        
        for level in range(max_depth + 1):
            if invert:
                y_pos = 1.0 - margin - (level * level_height) - (level_height / 2)
            else:
                y_pos = margin + (level * level_height) + (level_height / 2)
            level_positions.append(y_pos)
        
        vertical_line_positions = set() # avoid duplicates
        
        for level in range(max_depth + 1):
            nodes = rt.at_depth(level)
            y_pos = level_positions[level]
            
            nodes_by_parent = {}
            for node in nodes:
                parent = rt.parent(node)
                if parent not in nodes_by_parent:
                    nodes_by_parent[parent] = []
                nodes_by_parent[parent].append(node)
            
            for node in nodes:
                node_data = rt.graph.nodes[node]
                ratio = node_data.get('ratio', None)
                proportion = node_data.get('proportion', None)
                
                # XXX - maybe not necessary
                if ratio is None:
                    continue
                
                parent = rt.parent(node)
                
                if parent is None:  # Root node spans the entire width
                    x_start = 0
                    width = 1
                    is_first_child = True
                    is_last_child = True
                else:
                    siblings = nodes_by_parent[parent]
                    parent_data = rt.graph.nodes[parent]
                    
                    is_first_child = siblings[0] == node
                    is_last_child = siblings[-1] == node
                    
                    total_proportion = sum(abs(rt.graph.nodes[sib].get('proportion', 1)) for sib in siblings)
                    
                    preceding_proportion = 0
                    for sib in siblings:
                        if sib == node:
                            break
                        preceding_proportion += abs(rt.graph.nodes[sib].get('proportion', 1))
                    
                    parent_x_start = parent_data.get('_x_start', 0)
                    parent_width = parent_data.get('_width', 1)
                    
                    x_start = parent_x_start + (preceding_proportion / total_proportion) * parent_width
                    width = (abs(proportion) / total_proportion) * parent_width
                
                rt.graph.nodes[node]['_x_start'] = x_start
                rt.graph.nodes[node]['_width'] = width
                
                is_leaf = rt.graph.out_degree(node) == 0
                
                # Assign color based on node type and ratio sign
                is_rest = Fraction(str(ratio)) < 0
                if is_rest:
                    # Rests are always dark grey
                    color = '#808080'
                else:
                    # For positive ratios, leaf nodes are bright white, parent nodes slightly darker
                    color = '#e6e6e6' if is_leaf else '#c8c8c8'
                
                bar_height = level_height * 0.5 * get_node_scaling(node, rt)
                rect = plt.Rectangle((x_start, y_pos - bar_height/2), width, bar_height,
                                    facecolor=color, edgecolor='black', linewidth=1, alpha=0.4 if is_rest else 1 if is_leaf else 0.95)
                ax.add_patch(rect)
                
                label_text = f"{ratio}" if ratio is not None else ""
                ax.text(x_start + width/2, y_pos, 
                       label_text, ha='center', va='center', color='black' if not is_rest else 'white', fontsize=12 * get_node_scaling(node, rt, 9/12), fontweight='bold' if is_leaf else 'normal')
                
                if vertical_lines:
                    left_x = x_start
                    right_x = x_start + width
                    
                    if not is_first_child and left_x not in vertical_line_positions:
                        vertical_line_positions.add(left_x)
                        plt.plot([left_x, left_x], [y_pos - bar_height/2, 0], 
                                color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
                    
                    if not is_last_child and right_x not in vertical_line_positions:
                        vertical_line_positions.add(right_x)
                        plt.plot([right_x, right_x], [y_pos - bar_height/2, 0], 
                                color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
        
        if vertical_lines:
            top_y_pos = level_positions[0]
            bar_height = level_height * 0.5
            top_bar_bottom = top_y_pos - bar_height/2
            
            # Left border (x=0)
            if 0 not in vertical_line_positions:
                plt.plot([0, 0], [top_bar_bottom, 0], 
                        color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
            
            # Right border (x=1)
            if 1 not in vertical_line_positions:
                plt.plot([1, 1], [top_bar_bottom, 0], 
                        color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
        
        plt.axis('off')
        plt.xlim(-0.01, 1.01)
        plt.ylim(-0.01, 1.01)
        
        if output_file:
            plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
            plt.close()
        else:
            plt.show()
    
    else:
        raise ValueError(f"Unknown layout: {layout}. Choose 'default' or 'containers'.")
