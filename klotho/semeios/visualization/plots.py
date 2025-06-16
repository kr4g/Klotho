from typing import Tuple
from itertools import count
import networkx as nx
import matplotlib.pyplot as plt
from klotho.topos.graphs.trees.trees import Tree
from klotho.chronos.rhythm_trees import RhythmTree
from klotho.thetos.parameters.parameter_tree import ParameterTree
from klotho.chronos.temporal_units import TemporalUnit, TemporalUnitSequence, TemporalBlock
from fractions import Fraction
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Union, Dict, Optional
import math

from klotho.tonos.systems.combination_product_sets import CombinationProductSet
from klotho.tonos.systems.combination_product_sets.master_sets import MASTER_SETS
from klotho.topos.collections.sets import CombinationSet
from klotho.dynatos.expression.dynamics import DynamicRange
from klotho.dynatos.expression.enevelopes import Envelope

__all__ = ['plot']

def plot(obj, **kwargs):
    """
    Universal plot function that dispatches to appropriate plotting function based on object type.
    
    Args:
        obj: Object to plot (Tree, RhythmTree, CombinationSet, CombinationProductSet, DynamicRange, Envelope, networkx.Graph, etc.)
        **kwargs: Keyword arguments passed to the specific plotting function
        
    Raises:
        TypeError: If the object type is not supported
    """
    match obj:
        case Tree():
            match obj:
                case RhythmTree():
                    return _plot_rt(obj, **kwargs)
                case ParameterTree():
                    return _plot_parameter_tree(obj, **kwargs)
                case _:
                    return _plot_tree(obj, **kwargs)
        case CombinationSet():
            match obj:
                case CombinationProductSet():
                    return _plot_cps(obj, **kwargs)
                case _:
                    return _plot_cs(obj, **kwargs)
        case DynamicRange():
            return _plot_dynamic_range(obj, **kwargs)
        case Envelope():
            return _plot_envelope(obj, **kwargs)
        case nx.Graph():
            return _plot_graph(obj, **kwargs)
        case TemporalUnit() | TemporalUnitSequence() | TemporalBlock():
            raise NotImplementedError("Plotting for temporal units not yet implemented")
        case _:
            raise TypeError(f"Unsupported object type for plotting: {type(obj)}")

def _plot_parameter_tree(tree: ParameterTree, attributes: list[str] | None = None, figsize: tuple[float, float] = (20, 5), 
                        invert: bool = True, output_file: str | None = None) -> go.Figure:
    """
    Visualize a ParameterTree structure with muting logic applied.
    
    Similar to _plot_tree but respects the ParameterTree's muting mechanism,
    only displaying active (non-muted) attributes for each node.
    
    Args:
        tree: ParameterTree instance to visualize
        attributes: List of node attributes to display instead of labels. If None, shows only labels.
                   Special values "node_id", "node", or "id" will display the node identifier.
        figsize: Width and height of the output figure in inches
        invert: When True, places root at the top; when False, root is at the bottom
        output_file: Path to save the visualization (displays plot if None)
    """
    def _hierarchy_pos(G, root, width=1.5, height=1.0, xcenter=0.5, pos=None, parent=None, depth=0, inverted=True, vert_gap=None):
        if pos is None:
            max_depth = _get_max_depth(G, root)
            vert_gap = height / max(max_depth, 1) if max_depth > 0 else height
            max_breadth = _get_max_breadth(G, root)
            width = max(2.5, 1.5 * max_breadth)
            pos = {root: (xcenter, height if inverted else 0)}
        else:
            y = (height - (depth * vert_gap)) if inverted else (depth * vert_gap)
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
                             height=height,
                             xcenter=nextx,
                             pos=pos,
                             parent=root,
                             depth=depth+1,
                             inverted=inverted,
                             vert_gap=vert_gap)
                nextx += dx
        return pos
    
    def _count_leaves(G, node, parent=None):
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if not children:
            return 1
        
        return sum(_count_leaves(G, child, node) for child in children)
    
    def _get_max_depth(G, node, parent=None, current_depth=0):
        children = list(G.neighbors(node))
        if not isinstance(G, nx.DiGraph) and parent is not None:
            children.remove(parent)
        
        if not children:
            return current_depth
        
        return max(_get_max_depth(G, child, node, current_depth + 1) for child in children)
    
    def _get_max_breadth(G, root, parent=None):
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
    height_scale = figsize[1] / 1.5
    pos = _hierarchy_pos(G, root, height=height_scale, inverted=invert)
    
    fig = go.Figure()
    
    for u, v in G.edges():
        if u in pos and v in pos:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines',
                    line=dict(color='#808080', width=2),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
    
    node_x, node_y = [], []
    hover_data = []
    node_symbols = []
    node_text = []
    
    for node in G.nodes():
        if node in pos:
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            active_items = tree[node].active_items()
            
            display_text = ""
            if "synth_name" in active_items:
                display_text = str(active_items["synth_name"])
            
            node_text.append(display_text)
            
            if attributes is None:
                label_text = str(G.nodes[node]['label']) if G.nodes[node]['label'] is not None else ''
            else:
                label_parts = []
                for attr in attributes:
                    if attr in {"node_id", "node", "id"}:
                        label_parts.append(str(node))
                    else:
                        if attr in active_items:
                            value = active_items[attr]
                            label_parts.append(f"{attr}: {value}" if value is not None else f"{attr}: None")
                label_text = "<br>".join(label_parts)
            
            hover_data.append(label_text)
            
            is_leaf = len(list(G.neighbors(node))) == 0
            node_symbols.append('circle' if is_leaf else 'square')
    
    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            marker=dict(
                size=30,
                color='white',
                line=dict(color='white', width=2),
                symbol=node_symbols
            ),
            text=node_text,
            textposition='middle center',
            textfont=dict(color='#404040', size=10, family='Arial', weight='bold'),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_data,
            showlegend=False
        )
    )
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    x_padding = (max(node_x) - min(node_x)) * 0.02 if node_x else 0.05
    y_padding = (max(node_y) - min(node_y)) * 0.1 if node_y else 0.2
    
    fig.update_layout(
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[min(node_x)-x_padding, max(node_x)+x_padding] if node_x else [-1, 1]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor="x", scaleratio=1,
            range=[min(node_y)-y_padding, max(node_y)+y_padding] if node_y else [-1, 1]
        ),
        hovermode='closest',
        margin=dict(l=0, r=0, t=0, b=0),
    )
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig

def _plot_tree(tree: Tree, attributes: list[str] | None = None, figsize: tuple[float, float] = (20, 5), 
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

def _plot_ratios(ratios, figsize=(20, 1), output_file=None):
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

def _plot_graph(G: nx.Graph, figsize: tuple[float, float] = (10, 10), 
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

def _plot_rt(rt: RhythmTree, layout: str = 'containers', figsize: tuple[float, float] | None = None, 
            invert: bool = True, output_file: str | None = None, 
            attributes: list[str] | None = None, vertical_lines: bool = True) -> None:
    """
    Visualize a rhythm tree with customizable layout options.
    
    Args:
        rt: RhythmTree instance to visualize
        layout: 'tree' uses the standard tree visualization, 'containers' shows proportional containers, 'ratios' shows just the ratio segmentation
        figsize: Width and height of the output figure in inches
        invert: When True, places root at the top; when False, root is at the bottom
        output_file: Path to save the visualization (displays plot if None)
        attributes: List of node attributes to display (only used with 'tree' layout)
        vertical_lines: When True, draws vertical lines at block boundaries
    """
    if layout == 'tree':
        if figsize is None:
            figsize = (20, 5)
        return _plot_tree(rt, attributes=attributes, figsize=figsize, invert=invert, output_file=output_file)
    
    elif layout == 'ratios':
        if figsize is None:
            figsize = (20, 1)
        return _plot_ratios(rt.ratios, figsize=figsize, output_file=output_file)
    
    elif layout == 'containers':
        if figsize is None:
            figsize = (20, 5)
        
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
        ratio_space = 0.15
        usable_height = 1.0 - (2 * margin) - ratio_space
        
        level_positions = []
        level_height = usable_height / (max_depth + 1)
        
        for level in range(max_depth + 1):
            if invert:
                y_pos = 1.0 - margin - (level * level_height) - (level_height / 2)
            else:
                y_pos = margin + ratio_space + (level * level_height) + (level_height / 2)
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
                        plt.plot([left_x, left_x], [y_pos - bar_height/2, margin], 
                                color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
                    
                    if not is_last_child and right_x not in vertical_line_positions:
                        vertical_line_positions.add(right_x)
                        plt.plot([right_x, right_x], [y_pos - bar_height/2, margin], 
                                color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
        
        if vertical_lines:
            top_y_pos = level_positions[0]
            bar_height = level_height * 0.5
            top_bar_bottom = top_y_pos - bar_height/2
            
            # Left border (x=0)
            if 0 not in vertical_line_positions:
                plt.plot([0, 0], [top_bar_bottom, margin], 
                        color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
            
            # Right border (x=1)
            if 1 not in vertical_line_positions:
                plt.plot([1, 1], [top_bar_bottom, margin], 
                        color='#aaaaaa', linestyle='--', linewidth=0.8, alpha=0.7)
        
        ratios = rt.ratios
        total_ratio = sum(abs(r) for r in ratios)
        segment_widths = [abs(r) / total_ratio for r in ratios]
        
        positions = [0]
        for width in segment_widths[:-1]:
            positions.append(positions[-1] + width)
        
        ratio_bar_height = ratio_space * 0.4
        ratio_y_center = margin + ratio_space * 0.5
        
        for i, (pos, width, ratio) in enumerate(zip(positions, segment_widths, ratios)):
            color = '#808080' if ratio < 0 else '#e6e6e6'
            ax.add_patch(plt.Rectangle((pos, ratio_y_center - ratio_bar_height/2), width, ratio_bar_height, 
                                     facecolor=color,
                                     edgecolor=None, alpha=0.4 if ratio < 0 else 1))
        
        for pos in positions + [1.0]:
            ax.plot([pos, pos], [ratio_y_center - ratio_bar_height/2, ratio_y_center + ratio_bar_height/2], 
                    color='#aaaaaa', linewidth=2)
        
        plt.axis('off')
        plt.xlim(-0.01, 1.01)
        plt.ylim(-0.01, 1.01)
        
        plt.margins(x=0)
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
        
        if output_file:
            plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
            plt.close()
        else:
            plt.show()
    
    else:
        raise ValueError(f"Unknown layout: {layout}. Choose 'tree', 'containers', or 'ratios'.")

def _plot_curve(*args, figsize=(16, 8), x_range=(0, 1), colors=None, labels=None, 
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

def _plot_cs(cs: CombinationSet, figsize: tuple[float, float] = (10, 10), 
             node_size: float = 1000, font_size: float = 12, 
             show_edge_labels: bool = False, edge_alpha: float = 0.3,
             title: str = None, output_file: str = None) -> None:
    """
    Plot a CombinationSet as a circular graph with all combinations connected.
    
    Args:
        cs: CombinationSet instance to visualize
        figsize: Width and height of the output figure in inches
        node_size: Size of the nodes in the plot
        font_size: Size of the node labels
        show_edge_labels: Whether to show labels on edges
        edge_alpha: Transparency of the edges (0-1)
        title: Title for the plot (auto-generated if None)
        output_file: Path to save the visualization (displays plot if None)
    """
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    G = cs.graph
    pos = nx.circular_layout(G)
    
    # Draw edges with low alpha since it's a complete graph
    nx.draw_networkx_edges(G, pos, edge_color='#808080', width=1, alpha=edge_alpha)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color='black', node_size=node_size,
                         edgecolors='white', linewidths=2)
    
    # Create labels from combos
    labels = {}
    for node, attrs in G.nodes(data=True):
        if 'combo' in attrs:
            combo = attrs['combo']
            label = ''.join(str(cs.factor_to_alias[f]).strip('()') for f in combo)
            labels[node] = label
    
    nx.draw_networkx_labels(G, pos, labels=labels, font_color='white', font_size=font_size)
    
    if show_edge_labels and G.number_of_edges() < 50:  # Only show edge labels for smaller graphs
        edge_labels = {(u, v): f'{u}-{v}' for u, v in G.edges()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                   font_color='white', font_size=font_size-2,
                                   bbox=dict(facecolor='black', edgecolor='none', alpha=0.6))
    
    if title is None:
        factor_string = ' '.join(str(cs.factor_to_alias[f]) for f in cs.factors)
        title = f"CombinationSet r={cs.rank} [{factor_string}]"
    
    ax.set_title(title, color='white', fontsize=14)
    plt.axis('off')
    plt.margins(x=0.1, y=0.1)
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', pad_inches=0, 
                    facecolor='black', edgecolor='none')
        plt.close()
    else:
        plt.show()

def _plot_cps(cps: CombinationProductSet, figsize: tuple = (12, 12), 
             node_size: int = 30, text_size: int = 12, show_labels: bool = True,
             title: str = None, output_file: str = None) -> go.Figure:
    """
    Plot a Combination Product Set as an interactive network diagram based on its master set.
    
    Note: This function requires a CPS instance with a defined master set. 
    
    Supported types:
    - Hexany (tetrad master set)
    - Eikosany (asterisk master set) 
    - Hebdomekontany (ogdoad master set)
    - Dekany/Pentadekany (with master_set parameter)
    - CombinationProductSet (with master_set parameter)
    
    Args:
        cps: CPS instance to visualize (must have a master_set defined)
        figsize: Size of the figure as (width, height) in inches
        node_size: Size of the nodes in the plot
        show_labels: Whether to show labels on the nodes
        title: Title for the plot (default is derived from CPS if None)
        output_file: Path to save the figure (if None, display instead)
        
    Returns:
        Plotly figure object that can be displayed or further customized
    """
    master_set_name = cps.master_set
    if not master_set_name:
        raise ValueError(
            f"CPS instance has no master set defined. plot() requires a master set for node positioning.\n"
            f"Available master sets: {list(MASTER_SETS.keys())}\n"
            f"Try using specific CPS classes like Hexany, Eikosany, or Hebdomekontany, "
            f"or create a CPS with master_set parameter: CombinationProductSet(factors, r, master_set='tetrad')"
        )
    if master_set_name not in MASTER_SETS:
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
                    line=dict(color='#808080', width=1),
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

def _plot_dynamic_range(dynamic_range: DynamicRange, mode: str = 'db', figsize=(20, 5), 
                       resolution: int = 1000, show_labels: bool = True, 
                       show_grid: bool = True, title: str = None, output_file: str = None):
    """
    Plot a DynamicRange as a colored curve with dynamic markings.
    
    Args:
        dynamic_range: DynamicRange instance to visualize
        mode: 'db' or 'amp' to plot decibel or amplitude values
        figsize: Tuple of (width, height) for the figure
        resolution: Number of points in the curve for smooth plotting
        show_labels: Whether to show dynamic marking labels
        show_grid: Whether to show grid lines
        title: Title for the plot (auto-generated if None)
        output_file: Path to save the plot (if None, displays plot)
        
    Returns:
        None
    """
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    dynamics = dynamic_range._dynamics
    num_dynamics = len(dynamics)
    
    match mode.lower():
        case 'db':
            min_val = dynamic_range.min_dynamic.db
            max_val = dynamic_range.max_dynamic.db
            ylabel = 'Decibels (dB)'
            get_value = lambda d: d.db
            mode_display = 'dB'
        case 'amp':
            min_val = dynamic_range.min_dynamic.amp
            max_val = dynamic_range.max_dynamic.amp
            ylabel = 'Amplitude'
            get_value = lambda d: d.amp
            mode_display = 'amp'
        case _:
            raise ValueError(f"Invalid mode '{mode}'. Must be 'db' or 'amp'.")
    
    x = np.linspace(0, 1, resolution)
    y = np.zeros(resolution)
    
    for i, xi in enumerate(x):
        norm_pos = xi
        
        if dynamic_range.curve == 0:
            curved_pos = norm_pos
        else:
            curved_pos = (np.exp(dynamic_range.curve * norm_pos) - 1) / (np.exp(dynamic_range.curve) - 1)
        
        value = min_val + curved_pos * (max_val - min_val)
        y[i] = value
    
    colors = plt.cm.plasma(np.linspace(0, 1, resolution))
    
    for i in range(resolution - 1):
        ax.plot([x[i], x[i+1]], [y[i], y[i+1]], 
               color=colors[i], linewidth=3, alpha=0.8)
    
    if show_labels:
        dynamic_positions = np.linspace(0, 1, num_dynamics)
        
        for i, (pos, dyn) in enumerate(zip(dynamic_positions, dynamics)):
            dynamic_obj = dynamic_range[dyn]
            value = get_value(dynamic_obj)
            
            ax.axvline(x=pos, color='white', linestyle='--', alpha=0.6, linewidth=1)
            
            ax.text(pos, max_val + (max_val - min_val) * 0.02, dyn, 
                   ha='center', va='bottom', color='white', fontsize=12, fontweight='bold')
            
            ax.scatter([pos], [value], color='white', s=50, zorder=5, edgecolor='black', linewidth=1)
    
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(min_val - (max_val - min_val) * 0.05, max_val + (max_val - min_val) * 0.1)
    
    # ax.set_xlabel('Dynamic Range Position', color='white', fontsize=12)
    ax.set_ylabel(ylabel, color='white', fontsize=12)
        
    if title is None:
        curve_desc = f"curve={dynamic_range.curve}" if dynamic_range.curve != 0 else "linear"
        title = f"Dynamic Range ({mode_display}) - {curve_desc}"
    
    ax.set_title(title, color='white', fontsize=14)
    
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    if show_grid:
        ax.grid(color='#555555', linestyle='-', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', facecolor='black')
        plt.close()
    else:
        plt.show()

def _plot_envelope(envelope: Envelope, figsize=(20, 5), show_points: bool = True,
                  show_grid: bool = True, title: str = None, output_file: str = None):
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    x = envelope.time_points
    y = np.array(envelope)
    
    ax.plot(x, y, color='#e6e6e6', linewidth=2.5)
    
    if show_points:
        point_times = [0]
        current_time = 0
        for duration in envelope._times:
            current_time += duration * envelope._time_scale
            point_times.append(current_time)
        
        point_values = envelope._values
        ax.scatter(point_times, point_values, color='white', s=80, 
                  zorder=5, edgecolor='black', linewidth=2)
        
        for i, (t, v) in enumerate(zip(point_times, point_values)):
            ax.text(t, v + (max(y) - min(y)) * 0.05, f'{v:.2f}', 
                   ha='center', va='bottom', color='white', fontsize=10, fontweight='bold')
    
    if title is None:
        title = f"Envelope"
    
    ax.set_title(title, color='white', fontsize=14)
    ax.set_xlabel('Time', color='white', fontsize=12)
    ax.set_ylabel('Value', color='white', fontsize=12)
    
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white') 
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')
    
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    if show_grid:
        ax.grid(color='#555555', linestyle='-', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight', facecolor='black')
        plt.close()
    else:
        plt.show()
