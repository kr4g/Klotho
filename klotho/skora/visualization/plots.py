from typing import Tuple
from itertools import count
import networkx as nx
import matplotlib.pyplot as plt
from klotho.topos.graphs.trees.trees import Tree
from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock
from fractions import Fraction
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Union, Dict, Optional
import math

from klotho.tonos.systems.combination_product_sets import CombinationProductSet
from klotho.tonos.systems.combination_product_sets.cps import MASTER_SETS

__all__ = [
    'plot_tree', 'plot_ratios', 'plot_graph', 'plot_ut', 'plot_rt', 'plot_curve', 
    'plot_timeline', 'plot_cps'
]

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

def plot_ratios(ratios, figsize=(25, 1), output_file=None):
    """
    Plot ratios as horizontal bars with thin white borders.
    
    Args:
        ratios: List of ratios (positive for white segments, negative for grey "rests")
        output_file: Path to save the plot (if None, displays plot)
    """
    plt.figure(figsize=figsize)
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
            attributes: list[str] | None = None, vertical_lines: bool = True) -> None:
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

def plot_curve(*args, figsize=(16, 8), x_range=(0, 1), colors=None, labels=None, 
               title=None, grid=True, legend=True, output_file=None):
    """
    Plot one or more curves with a consistent dark background style.
    
    Args:
        *args: One or more sequences of y-values to plot
        figsize: Tuple of (width, height) for the figure
        x_range: Tuple of (min, max) for the x-axis range
        colors: List of colors for multiple curves (defaults to viridis colormap)
        labels: List of labels for the legend
        title: Title for the plot
        grid: Whether to show grid lines
        legend: Whether to display the legend
        output_file: Path to save the plot (if None, displays plot)
    
    Returns:
        None
    """
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    curves = args
    
    if not curves:
        raise ValueError("At least one curve must be provided")
    
    if colors is None and len(curves) > 1:
        colors = plt.cm.viridis(np.linspace(0, 0.8, len(curves)))
    elif colors is None:
        colors = ['#e6e6e6']  # Default white
    
    if labels is None:
        labels = [f"Curve {i+1}" for i in range(len(curves))]
    
    for i, curve in enumerate(curves):
        if i < len(colors):
            color = colors[i]
        else:
            color = plt.cm.viridis(i / len(curves))
            
        label = labels[i] if i < len(labels) else f"Curve {i+1}"
        
        x = np.linspace(x_range[0], x_range[1], len(curve))
        ax.plot(x, curve, color=color, linewidth=2.5, label=label)
    
    if title:
        ax.set_title(title, color='white', fontsize=14)
    
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    if grid:
        ax.grid(color='#555555', linestyle='-', linewidth=0.5, alpha=0.5)
    
    if legend and len(curves) > 1:
        ax.legend(frameon=True, facecolor='black', edgecolor='#555555', labelcolor='white')
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', facecolor='black')
        plt.close()
    else:
        plt.show()

def plot_timeline(
    units: List[Union[TemporalUnit, TemporalUnitSequence, TemporalBlock]],
    width: int = 1200,
    track_height: int = 100,
    title: str = "Timeline",
    show_labels: bool = True,
    show_grid: bool = True,
    color_scheme: str = "dark",
    output_file: Optional[str] = None
) -> go.Figure:
    
    temporal_objects = []
    
    for unit in units:
        if isinstance(unit, TemporalUnit):
            temporal_objects.append(unit)
        elif isinstance(unit, TemporalUnitSequence):
            temporal_objects.extend(unit.seq)
        elif isinstance(unit, TemporalBlock):
            for row in unit.rows:
                if isinstance(row, TemporalUnit):
                    temporal_objects.append(row)
                elif isinstance(row, TemporalUnitSequence):
                    temporal_objects.extend(row.seq)
    
    if not temporal_objects:
        raise ValueError("No temporal units found in input")
    
    tracks = _assign_tracks(temporal_objects)
    num_tracks = max(track for _, track in tracks.items()) + 1
    
    colors = {
        "dark": {
            "background": "black",
            "grid": "#333333",
            "text": "white",
            "rest": "#808080",
            "duration": "#e6e6e6",
            "subdivision": "#c8c8c8"
        }
    }
    scheme = colors.get(color_scheme, colors["dark"])
    
    fig = go.Figure()
    
    for idx, ut in enumerate(temporal_objects):
        track = tracks[idx]
        
        for _, event in ut.events.iterrows():
            is_rest = event['is_rest']
            ratio = event['metric_ratio']
            
            color = scheme["rest"] if is_rest else scheme["duration"]
            
            fig.add_trace(
                go.Scatter(
                    x=[event['start'], event['start'] + abs(event['duration'])],
                    y=[track, track],
                    mode="lines",
                    line=dict(
                        color=color,
                        width=track_height * 0.6,
                    ),
                    fill=None,
                    showlegend=False,
                    hovertemplate=(
                        f"Track: {track}<br>"
                        f"Start: %{{x[0]:.2f}}s<br>"
                        f"End: %{{x[1]:.2f}}s<br>"
                        f"Duration: {abs(event['duration']):.2f}s<br>"
                        f"Ratio: {ratio}<br>"
                        f"Unit: {ut.tempus} | {ut.beat}={ut.bpm} BPM"
                    ),
                    hoverlabel=dict(bgcolor=scheme["background"]),
                )
            )
            
            if show_labels and track_height >= 80:
                fig.add_annotation(
                    x=(event['start'] + event['start'] + abs(event['duration'])) / 2,
                    y=track,
                    text=str(ratio),
                    showarrow=False,
                    font=dict(
                        size=min(12, max(8, int(track_height * 0.1))),
                        color="white" if is_rest else "black"
                    ),
                    bgcolor="rgba(0,0,0,0)"
                )
    
    y_range = [-0.5, num_tracks - 0.5]
    x_min = min(ut.offset for ut in temporal_objects)
    x_max = max(ut.offset + ut.duration for ut in temporal_objects)
    x_padding = (x_max - x_min) * 0.05
    
    fig.update_layout(
        title=title,
        width=width,
        height=track_height * num_tracks + 100,
        plot_bgcolor=scheme["background"],
        paper_bgcolor=scheme["background"],
        font=dict(color=scheme["text"]),
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis=dict(
            showgrid=show_grid,
            gridcolor=scheme["grid"],
            zeroline=False,
            title="Time (seconds)",
            range=[x_min - x_padding, x_max + x_padding]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=y_range
        ),
        dragmode="pan",
        modebar=dict(
            orientation="v",
            bgcolor=scheme["background"],
            color=scheme["text"]
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=[
                    dict(
                        args=[{"yaxis.range": y_range}],
                        label="Reset Y",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.range": [x_min - x_padding, x_max + x_padding]}],
                        label="Reset X",
                        method="relayout"
                    ),
                    dict(
                        args=[{"xaxis.range": [x_min - x_padding, x_max + x_padding], 
                              "yaxis.range": y_range}],
                        label="Reset All",
                        method="relayout"
                    ),
                ],
                pad={"r": 10, "t": 10},
                showactive=False,
                x=0.15,
                y=1.1,
                bgcolor=scheme["background"],
                bordercolor=scheme["grid"],
                font=dict(color=scheme["text"])
            )
        ]
    )
    
    config = {
        "scrollZoom": True,
        "displayModeBar": True,
        "modeBarButtonsToAdd": ["drawline", "eraseshape"],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "timeline",
            "height": track_height * num_tracks + 100,
            "width": width,
            "scale": 2
        }
    }
    
    if output_file:
        fig.write_html(output_file, include_plotlyjs="cdn", config=config)
    
    return fig

def _assign_tracks(units: List[TemporalUnit]) -> Dict[int, int]:
    sorted_units = sorted(enumerate(units), key=lambda x: x[1].offset)
    tracks = {}
    track_end_times = []
    
    for idx, unit in sorted_units:
        unit_start = unit.offset
        unit_end = unit.offset + unit.duration
        
        track_idx = 0
        while track_idx < len(track_end_times) and unit_start < track_end_times[track_idx]:
            track_idx += 1
            
        if track_idx == len(track_end_times):
            track_end_times.append(unit_end)
        else:
            track_end_times[track_idx] = unit_end
            
        tracks[idx] = track_idx
        
    return tracks

def plot_cps(cps: CombinationProductSet, figsize: tuple = (12, 12), 
             node_size: int = 30, text_size: int = 12, show_labels: bool = True,
             title: str = None, output_file: str = None) -> go.Figure:
    """
    Plot a Combination Product Set as an interactive network diagram based on its master set.
    
    Args:
        cps: CombinationProductSet instance to visualize
        figsize: Size of the figure as (width, height) in inches
        node_size: Size of the nodes in the plot
        show_labels: Whether to show labels on the nodes
        title: Title for the plot (default is derived from CPS if None)
        output_file: Path to save the figure (if None, display instead)
        
    Returns:
        Plotly figure object that can be displayed or further customized
    """
    master_set_name = cps.master_set
    if not master_set_name or master_set_name not in MASTER_SETS:
        raise ValueError(f"Invalid master set name: {master_set_name}. Must be one of {list(MASTER_SETS.keys())}")
    
    relationship_angles = MASTER_SETS[master_set_name]
    G = cps.graph
    
    combo_to_node = {}
    node_to_combo = {}
    for node, attrs in G.nodes(data=True):
        if 'combo' in attrs:
            combo = attrs['combo']
            combo_to_node[combo] = node
            node_to_combo[node] = combo
    
    node_relationships = {}
    for u, v, data in G.edges(data=True):
        if 'relation' in data:
            if u not in node_relationships:
                node_relationships[u] = []
            relation_str = str(data['relation'])
            node_relationships[u].append((v, relation_str))
    
        node_positions = {}
    
    components = list(nx.strongly_connected_components(G))
    
    for component in components:
        start_node = next(iter(component))
        component_positions = {start_node: (0, 0)}
        
        placed_nodes = set([start_node])
        to_visit = [start_node]
        
        while to_visit:
            current_node = to_visit.pop(0)
            
            if current_node in node_relationships:
                for neighbor_node, relation in node_relationships[current_node]:
                    if neighbor_node not in placed_nodes and neighbor_node in component:
                        for sym_rel, rel_data in relationship_angles.items():
                            if str(sym_rel) == relation:
                                current_pos = component_positions[current_node]
                                distance = rel_data['distance']
                                angle = rel_data['angle']
                                
                                x = current_pos[0] + distance * math.cos(angle)
                                y = current_pos[1] + distance * math.sin(angle)
                                
                                component_positions[neighbor_node] = (x, y)
                                placed_nodes.add(neighbor_node)
                                to_visit.append(neighbor_node)
                                break
        
        if component_positions:
            center_x = sum(x for x, y in component_positions.values()) / len(component_positions)
            center_y = sum(y for x, y in component_positions.values()) / len(component_positions)
            
            for node in component_positions:
                x, y = component_positions[node]
                component_positions[node] = (x - center_x, y - center_y)
        
        node_positions.update(component_positions)
    
    fig = go.Figure()
    
    for u, v, data in G.edges(data=True):
        if u in node_positions and v in node_positions:
            x1, y1 = node_positions[u]
            x2, y2 = node_positions[v]
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines',
                    line=dict(color='white', width=1),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
    
    node_x, node_y = [], []
    node_text, hover_data = [], []
    
    for node, attrs in G.nodes(data=True):
        if node in node_positions and 'combo' in attrs:
            x, y = node_positions[node]
            node_x.append(x)
            node_y.append(y)
            
            combo = attrs['combo']
            label = ''.join(str(cps.factor_to_alias[f]).strip('()') for f in combo)
            node_text.append(label)
            
            combo_str = str(combo).replace(',)', ')')
            product = attrs['product']
            ratio = attrs['ratio']
            
            hover_info = f"Combo: {combo_str}<br>Product: {product}<br>Ratio: {ratio}"
            hover_data.append(hover_info)
    
    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if show_labels else 'markers',
            marker=dict(
                size=node_size,
                color='white',
                line=dict(color='white', width=2)
            ),
            text=node_text,
            textposition='middle center',
            textfont=dict(color='black', size=text_size, family='Arial Black', weight='bold'),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_data,
            showlegend=False
        )
    )
    
    if title is None:
        cps_type = type(cps).__name__
        # factor_string = ', '.join(str(f) for f in cps.factors)
        factor_string = ' '.join(str(cps.factor_to_alias[f]) for f in cps.factors)
        title = f"{cps_type} [{factor_string}]"
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(node_x)-1, max(node_x)+1]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor="x", scaleratio=1,
            range=[min(node_y)-1, max(node_y)+1]
        ),
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0),
    )
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig