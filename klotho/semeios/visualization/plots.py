from klotho.topos.graphs import Graph, Tree
from klotho.topos.collections.sets import CombinationSet, PartitionSet
from klotho.topos.graphs.lattices import Lattice
from klotho.topos.graphs.lattices.fields import Field

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units import TemporalMeta, TemporalUnit, TemporalUnitSequence, TemporalBlock

from klotho.tonos.systems.combination_product_sets import CombinationProductSet
from klotho.tonos.systems.combination_product_sets.master_sets import MASTER_SETS
from klotho.tonos.scales import Scale
from klotho.tonos.chords import Chord
from klotho.tonos.scales.scale import AddressedScale
from klotho.tonos.chords.chord import AddressedChord, Sonority, AddressedSonority

from klotho.dynatos.dynamics import DynamicRange
from klotho.dynatos.envelopes import Envelope

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.parameters.parameter_tree import ParameterTree

import rustworkx as rx
# Temporary compatibility imports for visualization
try:
    import networkx as nx
except ImportError:
    # If NetworkX not available, create a minimal compatibility layer
    class _NetworkXCompat:
        def __getattr__(self, name):
            raise ImportError(f"NetworkX function '{name}' not available. Visualization may be limited.")
    nx = _NetworkXCompat()
import matplotlib.pyplot as plt
from fractions import Fraction
import numpy as np
import plotly.graph_objects as go
import math
from sklearn.manifold import MDS, SpectralEmbedding

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
        case Graph():
            match obj:
                case Tree():
                    match obj:
                        case RhythmTree():
                            return _plot_rt(obj, **kwargs)
                        case ParameterTree():
                            return _plot_parameter_tree(obj, **kwargs)
                        case _:
                            return _plot_tree(obj, **kwargs)
                case Field():
                    return _plot_field(obj, **kwargs)
                case Lattice():
                    return _plot_lattice(obj, **kwargs)
                case _:
                    return _plot_graph(obj._graph, **kwargs)
        case CombinationSet():
            match obj:
                case CombinationProductSet():
                    return _plot_cps(obj, **kwargs)
                case _:
                    return _plot_cs(obj, **kwargs)
        case Scale() | Chord() | AddressedScale() | AddressedChord() | Sonority() | AddressedSonority():
            return _plot_scale_chord(obj, **kwargs)
        case PartitionSet():
            return _plot_graph(obj.graph._graph, **kwargs)
        case DynamicRange():
            return _plot_dynamic_range(obj, **kwargs)
        case Envelope():
            return _plot_envelope(obj, **kwargs)
        case TemporalMeta():
            match obj:
                case TemporalUnit():
                    match obj:
                        case CompositionalUnit():
                            return _plot_rt(obj.rt, **kwargs)
                        case _:
                            return _plot_rt(obj.rt, **kwargs)
                case TemporalUnitSequence():
                    raise NotImplementedError("Plotting for temporal unit sequences not yet implemented")
                case TemporalBlock():
                    raise NotImplementedError("Plotting for temporal blocks not yet implemented")
                case _:
                    raise NotImplementedError("Must be a TemporalUnit, TemporalUnitSequence, or TemporalBlock")
        case _ if hasattr(obj, 'nodes') and hasattr(obj, 'edges'):
            # Handle NetworkX graphs or other graph-like objects
            return _plot_graph(obj, **kwargs)
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
        
        children = _get_children(G, root, parent)
        
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
        children = _get_children(G, node, parent)
        
        if not children:
            return 1
        
        return sum(_count_leaves(G, child, node) for child in children)
    
    def _get_max_depth(G, node, parent=None, current_depth=0):
        children = _get_children(G, node, parent)
        
        if not children:
            return current_depth
        
        return max(_get_max_depth(G, child, node, current_depth + 1) for child in children)
    
    def _get_max_breadth(G, root, parent=None):
        nodes_by_level = {}
        
        def _count_by_level(node, level=0, parent=None):
            if level not in nodes_by_level:
                nodes_by_level[level] = 0
            nodes_by_level[level] += 1
            
            children = _get_children(G, node, parent)
            
            for child in children:
                _count_by_level(child, level+1, node)
        
        _count_by_level(root, parent=parent)
        
        return max(nodes_by_level.values()) if nodes_by_level else 1
    
    G = tree._graph
    root = tree.root
    height_scale = figsize[1] / 1.5
    pos = _hierarchy_pos(G, root, height=height_scale, inverted=invert)
    
    fig = go.Figure()
    
    # Handle edge iteration for both wrapped and raw RustworkX graphs
    if hasattr(G, 'edge_list') and str(type(G)).find('rustworkx') != -1:
        # Raw RustworkX graph - use edge_list() for (u, v) pairs
        edges = G.edge_list()
    else:
        # Wrapped graph or NetworkX - use edges() method
        edges = G.edges()
    
    for u, v in edges:
        if u in pos and v in pos:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                    line=dict(color='#808080', width=2),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
    
    node_x, node_y = [], []
    hover_data = []
    node_symbols = []
    node_text = []
    
    # Handle node iteration for both wrapped and raw RustworkX graphs
    if hasattr(G, 'node_indices') and str(type(G)).find('rustworkx') != -1:
        # Raw RustworkX graph - use node_indices() for node IDs
        nodes = G.node_indices()
    else:
        # Wrapped graph or NetworkX - use nodes() method
        nodes = G.nodes()
    
    for node in nodes:
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
                label_text = str(G[node].get('label', node)) if G[node].get('label') is not None else str(node)
            else:
                label_parts = []
                for attr in attributes:
                    if attr in {"node_id", "node", "id"}:
                        label_parts.append(str(node))
                    elif attr in active_items:
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

def _plot_rt_tree(rt: RhythmTree, attributes: list[str] | None = None, figsize: tuple[float, float] = (20, 5), 
                 invert: bool = True, output_file: str | None = None) -> go.Figure:
    """
    Visualize a RhythmTree structure with dynamic scaling to handle density.
    
    Uses plotly for better scaling and zoom capabilities when dealing with complex trees.
    
    Args:
        rt: RhythmTree instance to visualize
        attributes: List of node attributes to display instead of labels. If None, shows proportions.
                   Special values "node_id", "node", or "id" will display the node identifier.
        figsize: Width and height of the output figure in inches
        invert: When True, places root at the top; when False, root is at the bottom
        output_file: Path to save the visualization (displays plot if None)
    """
    def _proportional_tree_layout(rt, height=1.0, inverted=True):
        """
        Exact copy of container layout logic, but places nodes at bar centers instead of drawing bars.
        """
        max_depth = rt.depth
        positions = {}
        
        margin = 0.01
        ratio_space = 0.15
        usable_height = height - (2 * margin) - ratio_space
        
        level_positions = []
        level_height = usable_height / (max_depth + 1)
        
        for level in range(max_depth + 1):
            if inverted:
                y_pos = height - margin - (level * level_height) - (level_height / 2)
            else:
                y_pos = margin + ratio_space + (level * level_height) + (level_height / 2)
            level_positions.append(y_pos)
        
        for level in range(max_depth + 1):
            nodes = rt.at_depth(level)
            y_pos = level_positions[level]
            
            nodes_by_parent = {}
            for node in nodes:
                parent = rt.parent(node)
                if parent not in nodes_by_parent:
                    nodes_by_parent[parent] = []
                nodes_by_parent[parent].append(node)
            
            # Sort siblings by their order in parent's successors to ensure correct left-to-right positioning
            for parent, siblings in nodes_by_parent.items():
                if parent is not None:
                    parent_successors = list(rt.successors(parent))
                    siblings.sort(key=lambda x: parent_successors.index(x) if x in parent_successors else 0)
            
            for node in nodes:
                node_data = rt[node]
                ratio = node_data.get('metric_duration', None)
                proportion = node_data.get('proportion', None)
                
                if ratio is None:
                    continue
                
                parent = rt.parent(node)
                
                if parent is None:
                    x_start = 0
                    width = 1
                else:
                    siblings = nodes_by_parent[parent]
                    parent_data = rt[parent]
                    
                    total_proportion = sum(abs(rt[sib].get('proportion', 1)) for sib in siblings)
                    
                    preceding_proportion = 0
                    for sib in siblings:
                        if sib == node:
                            break
                        preceding_proportion += abs(rt[sib].get('proportion', 1))
                    
                    parent_x_start = parent_data.get('_x_start', 0)
                    parent_width = parent_data.get('_width', 1)
                    
                    x_start = parent_x_start + (preceding_proportion / total_proportion) * parent_width
                    width = (abs(proportion) / total_proportion) * parent_width
                
                rt[node]['_x_start'] = x_start
                rt[node]['_width'] = width
                
                x_center = x_start + width / 2
                positions[node] = (x_center, y_pos)
        
        return positions, 1.0
    
    G = rt
    root = rt.root
    height_scale = figsize[1] / 1.5
    
    base_node_size = 25
    base_text_size = 15
    
    pos, scale_factor = _proportional_tree_layout(rt, height=height_scale, inverted=invert)
    
    if pos:
        x_coords = [x for x, y in pos.values()]
        y_coords = [y for x, y in pos.values()]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        x_padding = figsize[0] * 0.02
        y_padding = figsize[1] * 0.05
        
        target_width = figsize[0] - (2 * x_padding)
        target_height = figsize[1] - (2 * y_padding)
        
        current_width = max_x - min_x if max_x != min_x else 1
        current_height = max_y - min_y if max_y != min_y else 1
        
        x_scale = target_width / current_width
        y_scale = target_height / current_height
        
        scaled_pos = {}
        for node, (x, y) in pos.items():
            scaled_x = x_padding + (x - min_x) * x_scale
            scaled_y = y_padding + (y - min_y) * y_scale
            scaled_pos[node] = (scaled_x, scaled_y)
        
        pos = scaled_pos
        
        x_range = [-x_padding * 0.1, figsize[0] + x_padding * 0.1]
        y_range = [-y_padding * 0.1, figsize[1] + y_padding * 0.1]
    else:
        x_range = [-0.01, figsize[0] + 0.01]
        y_range = [-0.01, figsize[1] + 0.01]
    
    total_nodes = G.number_of_nodes()
    max_breadth = max(len(rt.at_depth(level)) for level in range(rt.depth + 1))
    
    density_factor = max(1.0, max_breadth / 8.0)
    node_size = max(8, base_node_size / density_factor)
    text_size = max(6, base_text_size / density_factor)
    
    fig = go.Figure()
    
    for u, v in G.edges():
        if u in pos and v in pos:
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
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
            
            node_data = G[node]
            
            display_text = ""
            if attributes is None:
                if 'proportion' in node_data:
                    display_text = str(node_data['proportion'])
                else:
                    display_text = str(node)
            else:
                label_parts = []
                for attr in attributes:
                    if attr in {"node_id", "node", "id"}:
                        label_parts.append(str(node))
                    elif attr in node_data:
                        value = node_data[attr]
                        # label_parts.append(f"{attr}: {value}" if value is not None else f"{attr}: None")
                        label_parts.append(str(value))
                display_text = "<br>".join(label_parts)
            
            node_text.append(display_text)
            
            hover_parts = [f"Node: {node}"]
            if 'proportion' in node_data:
                hover_parts.append(f"Proportion: {node_data['proportion']}")
            if 'metric_duration' in node_data:
                hover_parts.append(f"Duration: {node_data['metric_duration']}")
            if 'metric_onset' in node_data:
                hover_parts.append(f"Onset: {node_data['metric_onset']}")
            
            hover_data.append("<br>".join(hover_parts))
            
            is_leaf = len(list(G.neighbors(node))) == 0
            node_symbols.append('square' if is_leaf else 'circle')
    
    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            marker=dict(
                size=node_size,
                color='white',
                line=dict(color='white', width=2),
                symbol=node_symbols
            ),
            text=node_text,
            textposition='middle center',
            textfont=dict(color='#404040', size=text_size, family='Arial', weight='bold'),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_data,
            showlegend=False
        )
    )
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=x_range
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=y_range
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
        
        children = _get_children(G, root, parent)
        
        if children:
            if len(children) == 1:
                child_width = width * 0.8
                child_x = xcenter
                
                _hierarchy_pos(G, children[0],
                             width=child_width,
                             vert_gap=vert_gap,
                             xcenter=child_x,
                             pos=pos,
                             parent=root,
                             depth=depth+1,
                             inverted=inverted)
            else:
                dx = width / len(children)
                start_x = xcenter - width/2 + dx/2
                
                for i, child in enumerate(children):
                    child_x = start_x + i * dx
                    child_width = dx * 0.9
                    
                    _hierarchy_pos(G, child,
                                 width=child_width,
                                 vert_gap=vert_gap,
                                 xcenter=child_x,
                                 pos=pos,
                                 parent=root,
                                 depth=depth+1,
                                 inverted=inverted)
        return pos
    
    def _count_leaves(G, node, parent=None):
        children = _get_children(G, node, parent)
        
        if not children:
            return 1
        
        return sum(_count_leaves(G, child, node) for child in children)
    
    def _get_max_depth(G, node, parent=None, current_depth=0):
        children = _get_children(G, node, parent)
        
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
            
            children = _get_children(G, node, parent)
            
            for child in children:
                _count_by_level(child, level+1, node)
        
        _count_by_level(root, parent=parent)
        
        return max(nodes_by_level.values()) if nodes_by_level else 1
    
    original_G = tree._graph
    root = tree.root
    
    # Use original_G for our custom tree operations
    pos = _hierarchy_pos(tree, root, inverted=invert)
    
    # Convert to NetworkX for matplotlib plotting
    is_rustworkx = hasattr(original_G, 'node_indices') or str(type(original_G)).find('rustworkx') != -1
    
    if is_rustworkx:
        import networkx as nx
        if hasattr(original_G, 'in_degree'):
            G = nx.DiGraph()
        else:
            G = nx.Graph()
        
        # Add nodes with their data
        for node_idx in original_G.node_indices():
            try:
                node_data = tree[node_idx] if hasattr(tree, '__getitem__') else {}
                G.add_node(node_idx, **node_data)
            except:
                G.add_node(node_idx)
        
        # Add edges
        try:
            for edge in original_G.edge_list():
                src, dst = edge
                G.add_edge(src, dst)
        except:
            pass
    else:
        G = original_G
    
    plt.figure(figsize=figsize)
    ax = plt.gca()
    
    ax.set_facecolor('black')
    plt.gcf().set_facecolor('black')
    
    for node, (x, y) in pos.items():
        if attributes is None:
            label_text = str(tree[node].get('label', node)) if tree[node].get('label') is not None else str(node)
        else:
            label_parts = []
            for attr in attributes:
                if attr in {"node_id", "node", "id"}:
                    label_parts.append(str(node))
                elif attr in tree[node]:
                    value = tree[node][attr]
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

def _plot_ratios(ratios, figsize=(20, 0.667), output_file=None):
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

def _get_children(G, node, parent=None):
    """Helper function to get children of a node in tree-like graphs."""
    if hasattr(G, 'successors') and not str(type(G)).find('rustworkx') != -1:
        # For our wrapped Graph/Tree classes
        return list(G.successors(node))
    elif hasattr(G, 'successor_indices'):
        # For raw RustworkX graphs - use successor_indices to get node indices, not data
        return list(G.successor_indices(node))
    elif hasattr(G, 'neighbors'):
        # For NetworkX graphs (both directed and undirected)
        children = list(G.neighbors(node))
        if parent is not None and parent in children:
            children.remove(parent)
        return children
    else:
        return []

def _is_leaf(G, node):
    """Helper function to check if a node is a leaf."""
    return len(_get_children(G, node)) == 0

def _get_graph_layout(G, layout='spring', k=1, dim=2):
    """
    Get node positions using RustworkX layouts when possible, fallback to NetworkX.
    """
    import rustworkx as rx
    
    # Check if this is a RustworkX graph
    is_rustworkx = hasattr(G, 'node_indices') or str(type(G)).find('rustworkx') != -1
    
    try:
        # Try RustworkX layouts first for better performance
        if hasattr(G, '_graph') and hasattr(G._graph, 'node_indices'):
            # This is our Graph class wrapping RustworkX
            rx_graph = G._graph
            if layout == 'spring':
                return rx.spring_layout(rx_graph, k=k, dim=dim)
            elif layout == 'circular':
                pos_2d = rx.circular_layout(rx_graph)
                if dim == 3:
                    return {node: (*coords, 0) for node, coords in pos_2d.items()}
                return pos_2d
            elif layout == 'random':
                return rx.random_layout(rx_graph, dim=dim)
        elif is_rustworkx:
            # This is a raw RustworkX graph - use RustworkX layouts directly
            rx_graph = G
            if layout == 'spring':
                return rx.spring_layout(rx_graph, k=k, dim=dim)
            elif layout == 'circular':
                pos_2d = rx.circular_layout(rx_graph)
                if dim == 3:
                    return {node: (*coords, 0) for node, coords in pos_2d.items()}
                return pos_2d
            elif layout == 'random':
                return rx.random_layout(rx_graph, dim=dim)
    except Exception:
        pass
    
    # Fallback to NetworkX layouts - convert RustworkX to NetworkX if needed
    try:
        nx_graph = G
        
        # Convert RustworkX to NetworkX if needed
        if is_rustworkx:
            import networkx as nx
            nx_graph = nx.DiGraph() if hasattr(G, 'in_degree') else nx.Graph()
            
            # Preserve original node indices and data for semantic meaning
            for node_idx in G.node_indices():
                try:
                    node_data = G[node_idx] if hasattr(G, '__getitem__') else {}
                    nx_graph.add_node(node_idx, **node_data)
                except:
                    nx_graph.add_node(node_idx)
            
            # Add edges with their data
            try:
                for edge in G.edge_list():
                    src, dst = edge
                    try:
                        edge_data = G.get_edge_data(src, dst) if hasattr(G, 'get_edge_data') else {}
                        if edge_data is None:
                            edge_data = {}
                        nx_graph.add_edge(src, dst, **edge_data)
                    except:
                        nx_graph.add_edge(src, dst)
            except:
                # If edge_list fails, try to add edges without data
                try:
                    edges = [(i, j) for i in G.node_indices() for j in G.node_indices() 
                            if G.has_edge(i, j)]
                    nx_graph.add_edges_from(edges)
                except:
                    pass
        
        if layout == 'spring':
            pos = nx.spring_layout(nx_graph, k=k, dim=dim)
        elif layout == 'random':
            pos = nx.random_layout(nx_graph, dim=dim)
        elif layout == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(nx_graph, dim=dim)
        elif layout == 'spectral':
            if dim == 3:
                try:
                    pos = nx.spectral_layout(nx_graph, dim=3)
                except (ValueError, Exception):
                    pos_2d = nx.spectral_layout(nx_graph, dim=2)
                    pos = {node: (*coords, 0) for node, coords in pos_2d.items()}
            else:
                pos = nx.spectral_layout(nx_graph, dim=dim)
        elif layout == 'circular':
            pos_2d = nx.circular_layout(nx_graph)
            if dim == 3:
                pos = {node: (*coords, 0) for node, coords in pos_2d.items()}
            else:
                pos = pos_2d
        else:
            layout_func = getattr(nx, f'{layout}_layout')
            pos_2d = layout_func(nx_graph)
            if dim == 3:
                pos = {node: (*coords, 0) for node, coords in pos_2d.items()}
            else:
                pos = pos_2d
        
        # No need to map back since we preserved original node indices
        return pos
        
    except Exception:
        # Final fallback to spring layout
        try:
            if is_rustworkx:
                # For RustworkX graphs, use a simple layout
                node_indices = list(G.node_indices())
                return {node: (i, 0, 0) if dim == 3 else (i, 0) for i, node in enumerate(node_indices)}
            else:
                return nx.spring_layout(G, k=k, dim=dim)
        except Exception:
            # Return minimal layout if all else fails
            try:
                if is_rustworkx:
                    node_indices = list(G.node_indices())
                    nodes = node_indices
                else:
                    nodes = list(G.nodes()) if hasattr(G, 'nodes') else list(range(len(G)))
                return {node: (i, 0, 0) if dim == 3 else (i, 0) for i, node in enumerate(nodes)}
            except Exception:
                # Ultimate fallback - create simple positions for any graph
                if hasattr(G, '__len__'):
                    return {i: (i, 0, 0) if dim == 3 else (i, 0) for i in range(len(G))}
                else:
                    return {0: (0, 0, 0) if dim == 3 else (0, 0)}

def _plot_graph(G, figsize: tuple[float, float] = (10, 10), 
               node_size: float = 1000, font_size: float = 12,
               layout: str = 'spring', k: float = 1,
               show_edge_labels: bool = True,
               edge_width: bool = False,
               edge_color: bool = False,
               width_range: tuple[float, float] = (0.75, 3),
               cmap: str = 'viridis',
               invert_weights: bool = False,
               path: list | None = None,
               attributes: list[str] | None = None,
               dim: int = 2,
               output_file: str | None = None):
    
    # Convert RustworkX graphs to NetworkX for plotting compatibility
    original_G = G
    is_rustworkx = hasattr(G, 'node_indices') or str(type(G)).find('rustworkx') != -1
    
    if is_rustworkx:
        import networkx as nx
        # Convert RustworkX to NetworkX for plotting functions
        if hasattr(G, 'in_degree'):
            G = nx.DiGraph()
        else:
            G = nx.Graph()
        
        # Add nodes with their data
        for node_idx in original_G.node_indices():
            try:
                node_data = original_G[node_idx] if hasattr(original_G, '__getitem__') else {}
                G.add_node(node_idx, **node_data)
            except:
                G.add_node(node_idx)
        
        # Add edges with their data
        try:
            for edge in original_G.edge_list():
                src, dst = edge
                try:
                    edge_data = original_G.get_edge_data(src, dst) if hasattr(original_G, 'get_edge_data') else {}
                    if edge_data is None:
                        edge_data = {}
                    G.add_edge(src, dst, **edge_data)
                except:
                    G.add_edge(src, dst)
        except:
            # If edge_list fails, try to add edges without data
            try:
                edges = [(i, j) for i in original_G.node_indices() for j in original_G.node_indices() 
                        if original_G.has_edge(i, j)]
                G.add_edges_from(edges)
            except:
                pass
    
    if dim not in [2, 3]:
        raise ValueError(f"dim must be 2 or 3, got {dim}")
    
    # Use original RustworkX graph for layout if possible, otherwise use converted graph
    layout_graph = original_G if is_rustworkx else G
    pos = _get_graph_layout(layout_graph, layout=layout, k=k, dim=dim)
    
    is_directed = isinstance(G, nx.DiGraph)
    
    weights = []
    min_weight = max_weight = None
    if edge_width or edge_color:
        weight_dict = nx.get_edge_attributes(G, 'weight')
        if weight_dict:
            weights = list(weight_dict.values())
            min_weight, max_weight = min(weights), max(weights)
    
    def get_edge_props(edge_list, for_plotly=False):
        widths = []
        colors = []
        
        for u, v in edge_list:
            if edge_width and weights:
                w = G[u][v].get('weight', min_weight)
                if max_weight > min_weight:
                    norm_w = (w - min_weight) / (max_weight - min_weight)
                    if invert_weights:
                        norm_w = 1 - norm_w
                else:
                    norm_w = 0
                width = width_range[0] + norm_w * (width_range[1] - width_range[0])
                widths.append(width)
            else:
                widths.append(2)
            
            if edge_color and weights:
                w = G[u][v].get('weight', min_weight)
                if max_weight > min_weight:
                    norm_w = (w - min_weight) / (max_weight - min_weight)
                    if invert_weights:
                        norm_w = 1 - norm_w
                else:
                    norm_w = 0
                color = plt.cm.get_cmap(cmap)(norm_w)
                if for_plotly:
                    color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
                    colors.append(color_hex)
                else:
                    colors.append(color)
            else:
                colors.append('#808080')
        
        return widths, colors
    
    def get_node_labels():
        labels = {}
        for node in G.nodes():
            if attributes is None:
                label_text = str(node)
            else:
                label_parts = []
                for attr in attributes:
                    if attr in {"node_id", "node", "id"}:
                        label_parts.append(str(node))
                    elif attr in G[node]:
                        value = G[node][attr]
                        label_parts.append(str(value) if value is not None else '')
                if dim == 3:
                    label_text = "<br>".join(label_parts)
                else:
                    label_text = "\n".join(label_parts)
            labels[node] = label_text
        return labels
    
    if dim == 3:
        fig = go.Figure()
        
        if path:
            path_edges = list(zip(path[:-1], path[1:]))
            non_path_edges = [(u, v) for u, v in G.edges() if (u, v) not in path_edges and (v, u) not in path_edges]
            
            if non_path_edges:
                widths, colors = get_edge_props(non_path_edges, for_plotly=True)
                for i, (u, v) in enumerate(non_path_edges):
                    x1, y1, z1 = pos[u]
                    x2, y2, z2 = pos[v]
                    fig.add_trace(
                        go.Scatter3d(
                            x=[x1, x2], y=[y1, y2], z=[z1, z2],
                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                            line=dict(color=colors[i], width=widths[i]),
                            opacity=0.5,
                            showlegend=False,
                            hoverinfo='none'
                        )
                    )
            
            if path_edges:
                path_colors = plt.cm.viridis(np.linspace(0, 1, len(path_edges)))
                for i, (u, v) in enumerate(path_edges):
                    x1, y1, z1 = pos[u]
                    x2, y2, z2 = pos[v]
                    color = path_colors[i]
                    color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
                    fig.add_trace(
                        go.Scatter3d(
                            x=[x1, x2], y=[y1, y2], z=[z1, z2],
                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                            line=dict(color=color_hex, width=6),
                            showlegend=False,
                            hoverinfo='none'
                        )
                    )
        else:
            edge_list = list(G.edges())
            widths, colors = get_edge_props(edge_list, for_plotly=True)
            for i, (u, v) in enumerate(edge_list):
                x1, y1, z1 = pos[u]
                x2, y2, z2 = pos[v]
                fig.add_trace(
                    go.Scatter3d(
                        x=[x1, x2], y=[y1, y2], z=[z1, z2],
                        mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                        line=dict(color=colors[i], width=widths[i]),
                        showlegend=False,
                        hoverinfo='none'
                    )
                )
        
        node_x, node_y, node_z = [], [], []
        node_text, hover_data = [], []
        node_colors = []
        labels = get_node_labels()
        
        for node in G.nodes():
            if node in pos:
                x, y, z = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_z.append(z)
                
                node_text.append(str(node))
                hover_data.append(labels[node])
                
                if path and node in path:
                    path_index = path.index(node)
                    color = plt.cm.viridis(path_index / len(path))
                    color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
                    node_colors.append(color_hex)
                else:
                    node_colors.append('white')
        
        fig.add_trace(
            go.Scatter3d(
                x=node_x, y=node_y, z=node_z,
                mode='markers+text',
                marker=dict(
                    size=node_size/50,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                text=node_text,
                textposition='middle center',
                textfont=dict(color='black', size=font_size, family='Arial', weight='bold'),
                hovertemplate='%{customdata}<extra></extra>',
                customdata=hover_data,
                showlegend=False
            )
        )
        
        if show_edge_labels:
            edge_weights = nx.get_edge_attributes(G, 'weight')
            for (u, v), weight in edge_weights.items():
                if u in pos and v in pos:
                    x1, y1, z1 = pos[u]
                    x2, y2, z2 = pos[v]
                    mid_x, mid_y, mid_z = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2
                    
                    fig.add_trace(
                        go.Scatter3d(
                            x=[mid_x], y=[mid_y], z=[mid_z],
                            mode='text',
                            text=[f'{weight:.2f}'],
                            textfont=dict(color='white', size=font_size-2),
                            showlegend=False,
                            hoverinfo='none'
                        )
                    )
        
        width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
        
        fig.update_layout(
            width=width_px,
            height=height_px,
            paper_bgcolor='black',
            plot_bgcolor='black',
            scene=dict(
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.5),
                    center=dict(x=0, y=0, z=0)
                ),
                xaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, showbackground=False,
                    title=dict(text='', font=dict(color='white'))
                ),
                yaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, showbackground=False,
                    title=dict(text='', font=dict(color='white'))
                ),
                zaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, showbackground=False,
                    title=dict(text='', font=dict(color='white'))
                ),
                bgcolor='black'
            ),
            hovermode='closest',
            margin=dict(l=0, r=0, t=0, b=0)
        )
        
        if output_file:
            if output_file.endswith('.html'):
                fig.write_html(output_file)
            else:
                fig.write_image(output_file)
        
        return fig
    
    else:
        plt.figure(figsize=figsize)
        ax = plt.gca()
        
        ax.set_facecolor('black')
        plt.gcf().set_facecolor('black')
        
        if path:
            path_edges = list(zip(path[:-1], path[1:]))
            non_path_edges = [(u, v) for u, v in G.edges() if (u, v) not in path_edges and (v, u) not in path_edges]
            
            if non_path_edges:
                widths, colors = get_edge_props(non_path_edges)
                if is_directed:
                    nx.draw_networkx_edges(G, pos, edgelist=non_path_edges, edge_color=colors, 
                                         width=widths, alpha=0.5, arrows=True,
                                         connectionstyle="arc3,rad=0.1")
                else:
                    nx.draw_networkx_edges(G, pos, edgelist=non_path_edges, edge_color=colors, 
                                         width=widths, alpha=0.5)
            
            if path_edges:
                path_colors = plt.cm.viridis(np.linspace(0, 1, len(path_edges)))
                for (u, v), color in zip(path_edges, path_colors):
                    if is_directed:
                        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], edge_color=[color], 
                                             width=3, arrows=True,
                                             connectionstyle="arc3,rad=0.1")
                    else:
                        nx.draw_networkx_edges(G, pos, edgelist=[(u, v)], edge_color=[color], 
                                             width=3)
        else:
            edge_list = list(G.edges())
            widths, colors = get_edge_props(edge_list)
            if is_directed:
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths,
                                     arrows=True, connectionstyle="arc3,rad=0.1")
            else:
                nx.draw_networkx_edges(G, pos, edge_color=colors, width=widths)
        
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
        
        labels = get_node_labels()
        nx.draw_networkx_labels(G, pos, labels=labels, font_color='white', font_size=font_size)
        
        if show_edge_labels:
            edge_weights = {(u,v): f'{w:.2f}' for (u,v), w in nx.get_edge_attributes(G, 'weight').items()}
            if is_directed:
                for (u, v), weight in edge_weights.items():
                    x1, y1 = pos[u]
                    x2, y2 = pos[v]
                    
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    
                    dx = x2 - x1
                    dy = y2 - y1
                    length = (dx**2 + dy**2)**0.5
                    if length > 0:
                        curve_rad = 0.1
                        offset_x = -dy / length * curve_rad
                        offset_y = dx / length * curve_rad
                        
                        curve_mid_x = mid_x + offset_x
                        curve_mid_y = mid_y + offset_y
                    else:
                        curve_mid_x, curve_mid_y = mid_x, mid_y
                    
                    ax.text(curve_mid_x, curve_mid_y, weight, ha='center', va='center',
                           color='white', fontsize=font_size,
                           bbox=dict(facecolor='black', edgecolor='none', alpha=0.6))
            else:
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
            attributes: list[str] | None = None, vertical_lines: bool = True, 
            barlines: bool = True, barline_color: str = '#666666', 
            subdivision_line_color: str = '#aaaaaa') -> None:
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
        barlines: When True, draws span division lines (when span > 1)
        barline_color: Color for span division lines and outer borders
        subdivision_line_color: Color for subdivision lines and ratio dividers
    """
    if layout == 'tree':
        if figsize is None:
            figsize = (20, 5)
        return _plot_rt_tree(rt, attributes=attributes, figsize=figsize, invert=invert, output_file=output_file)
    
    elif layout == 'ratios':
        if figsize is None:
            figsize = (20, 1)
        return _plot_ratios(rt.durations, output_file=output_file)
    
    elif layout == 'containers':
        if figsize is None:
            figsize = (20, 5)
        
        def get_node_scaling(node, rt, min_scale=0.5):
            """Calculate the height scaling for a node based on its position in the tree."""
            if rt.out_degree(node) == 0:
                return min_scale
            
            current_depth = rt.depth_of(node)
            
            # Find the maximum depth of any leaf descendant from this 
            max_descendant_depth = current_depth
            for descendant in nx.descendants(rt._graph, node):
                if rt._graph.out_degree(descendant) == 0:  # If it's a leaf
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
        
        vertical_line_positions = set()
        
        # Calculate cutoff point for vertical lines (above onset text)
        onset_text_y = margin * 0.3
        line_cutoff = onset_text_y + (margin * 2.0)  # Larger gap above text
        
        if rt.span > 1 and barlines:
            top_bar_height = level_height * 0.5 * get_node_scaling(rt.root, rt)
            for i in range(rt.span + 1):
                x_pos = i / rt.span
                ax.plot([x_pos, x_pos], [level_positions[0] + top_bar_height/2, line_cutoff], 
                       color=barline_color, linestyle=(0, (8, 4)), linewidth=1.5, alpha=0.3, zorder=0.5)
        
        for level in range(max_depth + 1):
            nodes = rt.at_depth(level)
            y_pos = level_positions[level]
            
            nodes_by_parent = {}
            for node in nodes:
                parent = rt.parent(node)
                if parent not in nodes_by_parent:
                    nodes_by_parent[parent] = []
                nodes_by_parent[parent].append(node)
            
            # Sort siblings by their order in parent's successors to ensure correct left-to-right positioning
            for parent, siblings in nodes_by_parent.items():
                if parent is not None:
                    parent_successors = list(rt.successors(parent))
                    siblings.sort(key=lambda x: parent_successors.index(x) if x in parent_successors else 0)
            
            for node in nodes:
                node_data = rt[node]
                ratio = node_data.get('metric_duration', None)
                proportion = node_data.get('proportion', None)
                
                # XXX - maybe not necessary
                if ratio is None:
                    continue
                
                parent = rt.parent(node)
                
                if parent is None:  # Root node
                    if rt.span > 1:
                        # Draw span divisions at the top level
                        for i in range(rt.span):
                            x_start = i / rt.span
                            width = 1 / rt.span
                            
                            is_leaf = rt._graph.out_degree(node) == 0
                            is_rest = Fraction(str(ratio)) < 0
                            
                            if is_rest:
                                color = '#404040'
                            else:
                                color = '#e6e6e6' if is_leaf else '#c8c8c8'
                            
                            bar_height = level_height * 0.5 * get_node_scaling(node, rt)
                            rect = plt.Rectangle((x_start, y_pos - bar_height/2), width, bar_height,
                                                facecolor=color, edgecolor='black', linewidth=1, alpha=1, zorder=1)
                            ax.add_patch(rect)
                            
                            ax.text(x_start + width/2, y_pos, 
                                   str(rt.meas), ha='center', va='center', 
                                   color='black' if not is_rest else 'white', 
                                   fontsize=12 * get_node_scaling(node, rt, 9/12), 
                                   fontweight='bold' if is_leaf else 'normal')
                        
                        # Store position info for child nodes
                        rt[node]['_x_start'] = 0
                        rt[node]['_width'] = 1
                        continue
                    else:
                        x_start = 0
                        width = 1
                        is_first_child = True
                        is_last_child = True
                else:
                    siblings = nodes_by_parent[parent]
                    parent_data = rt[parent]
                    
                    is_first_child = siblings[0] == node
                    is_last_child = siblings[-1] == node
                    
                    total_proportion = sum(abs(rt[sib].get('proportion', 1)) for sib in siblings)
                    
                    preceding_proportion = 0
                    for sib in siblings:
                        if sib == node:
                            break
                        preceding_proportion += abs(rt[sib].get('proportion', 1))
                    
                    parent_x_start = parent_data.get('_x_start', 0)
                    parent_width = parent_data.get('_width', 1)
                    
                    x_start = parent_x_start + (preceding_proportion / total_proportion) * parent_width
                    width = (abs(proportion) / total_proportion) * parent_width
                
                rt[node]['_x_start'] = x_start
                rt[node]['_width'] = width
                
                is_leaf = rt._graph.out_degree(node) == 0
                
                # Assign color based on node type and ratio sign
                is_rest = Fraction(str(ratio)) < 0
                if is_rest:
                    color = '#404040'
                else:
                    color = '#e6e6e6' if is_leaf else '#c8c8c8'
                
                bar_height = level_height * 0.5 * get_node_scaling(node, rt)
                rect = plt.Rectangle((x_start, y_pos - bar_height/2), width, bar_height,
                                    facecolor=color, edgecolor='black', linewidth=1, alpha=1, zorder=1)
                ax.add_patch(rect)
                
                label_text = f"{ratio}" if ratio is not None else ""
                ax.text(x_start + width/2, y_pos, 
                       label_text, ha='center', va='center', color='black' if not is_rest else 'white', fontsize=12 * get_node_scaling(node, rt, 9/12), fontweight='bold' if is_leaf else 'normal')
                
                if vertical_lines:
                    left_x = x_start
                    right_x = x_start + width
                    
                    if not is_first_child and left_x not in vertical_line_positions:
                        vertical_line_positions.add(left_x)
                        plt.plot([left_x, left_x], [y_pos - bar_height/2, line_cutoff], 
                                color=subdivision_line_color, linestyle='--', linewidth=0.8, alpha=0.9, zorder=2)
                    
                    if not is_last_child and right_x not in vertical_line_positions:
                        vertical_line_positions.add(right_x)
                        plt.plot([right_x, right_x], [y_pos - bar_height/2, line_cutoff], 
                                color=subdivision_line_color, linestyle='--', linewidth=0.8, alpha=0.9, zorder=2)
        
        if vertical_lines:
            top_y_pos = level_positions[0]
            top_bar_height = level_height * 0.5 * get_node_scaling(rt.root, rt)
            top_bar_top = top_y_pos + (top_bar_height/2) - 0.001
            
            # Left border (x=0) - always solid with barline properties, starts from top
            if 0 not in vertical_line_positions:
                plt.plot([0, 0], [top_bar_top, line_cutoff], 
                        color=barline_color, linestyle='-', linewidth=1.5, alpha=0.9, zorder=2)
            
            # Right border (x=1) - always solid with barline properties, starts from top  
            if 1 not in vertical_line_positions:
                plt.plot([1, 1], [top_bar_top, line_cutoff], 
                        color=barline_color, linestyle='-', linewidth=1.5, alpha=0.9, zorder=2)
        
        ratios = rt.durations
        total_ratio = sum(abs(r) for r in ratios)
        segment_widths = [abs(r) / total_ratio for r in ratios]
        
        positions = [0]
        for width in segment_widths[:-1]:
            positions.append(positions[-1] + width)
        
        ratio_bar_height = ratio_space * 0.2
        ratio_y_center = margin + ratio_space * 0.5
        
        for i, (pos, width, ratio) in enumerate(zip(positions, segment_widths, ratios)):
            color = '#404040' if ratio < 0 else '#e6e6e6'
            ax.add_patch(plt.Rectangle((pos, ratio_y_center - ratio_bar_height/2), width, ratio_bar_height, 
                                     facecolor=color,
                                     edgecolor=None, alpha=1, zorder=1))
        
        for pos in positions + [1.0]:
            ax.plot([pos, pos], [ratio_y_center - ratio_bar_height/2, ratio_y_center + ratio_bar_height/2], 
                    color=subdivision_line_color, linewidth=2, zorder=2)
        
        for i, onset in enumerate(rt.onsets):
            if i < len(positions):
                x_pos = positions[i]
                ax.text(x_pos, margin * 0.3, str(onset), 
                       ha='center', va='center', color='white', fontsize=10, fontweight='bold')
        
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

def _plot_cs(cs: CombinationSet, figsize: tuple[float, float] = (12, 12), 
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
    
    # Convert RustworkX graph to NetworkX for visualization
    rx_graph = cs.graph._graph
    G = nx.Graph()
    
    # Add nodes with data
    for node_idx in rx_graph.node_indices():
        node_data = rx_graph.get_node_data(node_idx)
        if isinstance(node_data, dict):
            G.add_node(node_idx, **node_data)
        else:
            G.add_node(node_idx)
    
    # Add edges with data  
    for src, tgt in rx_graph.edge_list():
        edge_data = rx_graph.get_edge_data(src, tgt)
        if edge_data is not None and isinstance(edge_data, dict):
            G.add_edge(src, tgt, **edge_data)
        else:
            G.add_edge(src, tgt)
    
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
             title: str = None, output_file: str = None, nodes: list = None) -> go.Figure:
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
        nodes: List of node IDs to highlight in pale green
        
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
    
    G = cps.graph  # Use the Graph wrapper, not the internal _graph
    
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
    
    # Convert our Graph wrapper to NetworkX for compatibility with NetworkX algorithms
    nx_graph = G.to_networkx()
    components = list(nx.strongly_connected_components(nx_graph))
    
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
    
    highlight_nodes = set(nodes) if nodes else set()
    
    regular_edges = []
    highlighted_edges = []
    
    for u, v, data in G.edges(data=True):
        if u in node_positions and v in node_positions:
            if u in highlight_nodes and v in highlight_nodes:
                highlighted_edges.append((u, v))
            else:
                regular_edges.append((u, v))
    
    for u, v in regular_edges:
        x1, y1 = node_positions[u]
        x2, y2 = node_positions[v]
        fig.add_trace(
            go.Scatter(
                x=[x1, x2], y=[y1, y2],
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                line=dict(color='#808080', width=1),
                showlegend=False,
                hoverinfo='none'
            )
        )
    
    for u, v in highlighted_edges:
        x1, y1 = node_positions[u]
        x2, y2 = node_positions[v]
        fig.add_trace(
            go.Scatter(
                x=[x1, x2], y=[y1, y2],
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                line=dict(color='#90EE90', width=2),
                showlegend=False,
                hoverinfo='none'
            )
        )
    
    node_x, node_y = [], []
    node_text, hover_data, node_colors = [], [], []
    
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
            
            hover_info = f"Node: {node}<br>Combo: {combo_str}<br>Product: {product}<br>Ratio: {ratio}"
            hover_data.append(hover_info)
            
            if node in highlight_nodes:
                node_colors.append('#90EE90')
            else:
                node_colors.append('white')
    
    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if show_labels else 'markers',
            marker=dict(
                size=node_size,
                color=node_colors,
                line=dict(color='white', width=2)
            ),
            text=node_text,
            textposition='middle center',
            textfont=dict(color='black', size=text_size, family='Arial Black', weight='bold'),
            hovertemplate='%{customdata}<extra></extra>',
            hoverlabel=dict(bgcolor='lightgrey', font_color='black'),
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

def _plot_scale_chord(obj, figsize: tuple = (12, 12), 
                     node_size: int = 30, text_size: int = 12, show_labels: bool = True,
                     title: str = None, output_file: str = None, nodes: list = None, 
                     layout: str = 'circle') -> go.Figure:
    """
    Plot a Scale or Chord with different visualizations based on interval type.
    
    For cents-based scales/chords: Circular clock-like diagram with nodes
    For ratio-based scales/chords: Proportional segments showing interval sizes
    
    Args:
        obj: Scale or Chord instance to visualize
        figsize: Size of the figure as (width, height) in inches
        node_size: Size of the nodes in the plot (cents mode only)
        text_size: Size of the text labels
        show_labels: Whether to show labels on the segments/nodes
        title: Title for the plot (default is derived from object type if None)
        output_file: Path to save the figure (if None, display instead)
        nodes: List of node IDs to highlight (cents mode only)
        layout: 'circle' (default) or 'line' for ratio-based visualization
        
    Returns:
        Plotly figure object that can be displayed or further customized
    """
    degrees = obj.degrees
    if not degrees:
        raise ValueError(f"{type(obj).__name__} has no degrees to plot")
    
    n_degrees = len(degrees)
    
    # For addressed objects, use the underlying collection for calculations
    calc_obj = obj._collection if isinstance(obj, (AddressedScale, AddressedChord, AddressedSonority)) else obj
    calc_degrees = calc_obj.degrees
    
    fig = go.Figure()
    
    # Branch based on interval type
    if calc_obj._interval_type_mode == "cents":
        return _plot_cents_scale_chord(obj, calc_obj, degrees, calc_degrees, fig, figsize, 
                                     node_size, text_size, show_labels, title, output_file, nodes)
    else:
        return _plot_ratio_scale_chord_clean(obj, calc_obj, degrees, calc_degrees, fig, figsize,
                                            text_size, show_labels, title, output_file, layout)

def _plot_cents_scale_chord(obj, calc_obj, degrees, calc_degrees, fig, figsize, 
                           node_size, text_size, show_labels, title, output_file, nodes):
    """Plot cents-based scales/chords as circular node diagrams."""
    n_degrees = len(degrees)
    node_x, node_y = [], []
    node_text, hover_data, node_colors = [], [], []
    
    for i, degree in enumerate(degrees):
        # Use the underlying collection's degrees for angle calculation
        calc_degree = calc_degrees[i]
        
        if calc_obj._interval_type_mode == "cents":
            equave_value = calc_obj._equave if isinstance(calc_obj._equave, float) else 1200.0
            proportion = calc_degree / equave_value
        else:
            equave_value = float(calc_obj._equave)
            proportion = math.log(float(calc_degree)) / math.log(equave_value)
        
        angle = -2 * math.pi * proportion + math.pi / 2
        x = math.cos(angle)
        y = math.sin(angle)
        node_x.append(x)
        node_y.append(y)
        
        # Handle addressed vs non-addressed objects
        if isinstance(obj, (AddressedScale, AddressedChord, AddressedSonority)):
            # For addressed objects, use the underlying collection for display
            calc_degree = calc_degrees[i]
            if calc_obj._interval_type_mode == "cents":
                display_text = f"{calc_degree:.1f}¢"
                base_hover = f"{calc_degree:.1f} cents"
            else:
                display_text = f"{calc_degree}"
                base_hover = f"{calc_degree}"
            
            # Extract note name (no octave) and cent offset from pitch object
            note_name = degree.pitchclass
            cents_offset = degree.cents_offset
            
            # Format cent offset if significant
            cent_info = ""
            if abs(cents_offset) > 0.01:
                cent_info = f" ({cents_offset:+.2f}¢)"
            
            hover_info = f"Node {i}<br>{base_hover}<br>{note_name}{cent_info}"
        elif calc_obj._interval_type_mode == "cents":
            display_text = f"{degree:.1f}¢"
            hover_info = f"Node {i}<br>{degree:.1f} cents"
        else:
            display_text = f"{degree}"
            hover_info = f"Node {i}<br>{degree}"
        
        node_text.append(display_text if show_labels else "")
        hover_data.append(hover_info)
        
        rainbow_color = plt.cm.hsv(i / n_degrees)
        color_hex = '#%02x%02x%02x' % (int(rainbow_color[0]*255), int(rainbow_color[1]*255), int(rainbow_color[2]*255))
        
        if nodes is not None:
            # Handle both single list and list of lists, plus numpy arrays and Motive objects
            all_highlighted_nodes = set()
            
            # Convert nodes to a list if it's a single numpy array or Motive
            if hasattr(nodes, 'to_numpy'):  # Motive object
                nodes = nodes.to_numpy().tolist()
            elif hasattr(nodes, 'tolist') and hasattr(nodes, 'shape'):  # numpy array
                nodes = nodes.tolist()
            
            # Check if it's a list of lists/arrays/motives
            if isinstance(nodes, list) and len(nodes) > 0:
                first_item = nodes[0]
                # Check if first item is a container (list, array, motive) rather than a scalar
                is_container_list = False
                try:
                    is_container_list = (
                        hasattr(first_item, 'to_numpy') or  # Motive
                        (hasattr(first_item, 'tolist') and hasattr(first_item, 'shape')) or   # numpy array
                        (isinstance(first_item, list))  # list
                    )
                except:
                    is_container_list = False
                
                if is_container_list:
                    # Handle list of lists/arrays/motives
                    for node_list in nodes:
                        if hasattr(node_list, 'to_numpy'):  # Motive object
                            all_highlighted_nodes.update(node_list.to_numpy().tolist())
                        elif hasattr(node_list, 'tolist') and hasattr(node_list, 'shape'):  # numpy array
                            all_highlighted_nodes.update(node_list.tolist())
                        elif hasattr(node_list, '__iter__') and not isinstance(node_list, str):  # regular list
                            all_highlighted_nodes.update(node_list)
                        else:  # single value
                            all_highlighted_nodes.add(node_list)
                else:
                    # Single list of scalar nodes
                    all_highlighted_nodes = set(nodes)
            else:
                # Single list of nodes (already converted above if needed)
                all_highlighted_nodes = set(nodes)
            
            if i in all_highlighted_nodes:
                node_colors.append(color_hex)
            else:
                dimmed_color_hex = '#%02x%02x%02x' % (int(rainbow_color[0]*128), int(rainbow_color[1]*128), int(rainbow_color[2]*128))
                node_colors.append(dimmed_color_hex)
        else:
            node_colors.append(color_hex)
    
    for i in range(n_degrees):
        for j in range(i + 1, n_degrees):
            x1, y1 = node_x[i], node_y[i]
            x2, y2 = node_x[j], node_y[j]
            
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                    line=dict(color='#444444', width=1),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
    
    if nodes is not None:
        # Convert nodes to consistent format for edge drawing
        def convert_to_list(item):
            """Convert any node container to a plain list."""
            if hasattr(item, 'to_numpy'):  # Motive object
                return item.to_numpy().tolist()
            elif hasattr(item, 'tolist') and hasattr(item, 'shape'):  # numpy array
                return item.tolist()
            elif isinstance(item, list):
                return item
            else:
                return [item]
        
        # Convert main nodes structure
        if hasattr(nodes, 'to_numpy') or (hasattr(nodes, 'tolist') and hasattr(nodes, 'shape')):
            # Single Motive or numpy array
            processed_nodes = convert_to_list(nodes)
            is_container_list = False
        elif isinstance(nodes, list) and len(nodes) > 0:
            first_item = nodes[0]
            # Check if it's a list of containers
            try:
                is_container_list = (
                    hasattr(first_item, 'to_numpy') or  # Motive
                    (hasattr(first_item, 'tolist') and hasattr(first_item, 'shape')) or   # numpy array
                    isinstance(first_item, list)  # list
                )
            except:
                is_container_list = False
            
            if is_container_list:
                processed_nodes = [convert_to_list(item) for item in nodes]
            else:
                processed_nodes = nodes
                is_container_list = False
        else:
            processed_nodes = nodes
            is_container_list = False
        
        if is_container_list:
            # Multiple shapes - use viridis color scheme
            viridis_colors = plt.cm.viridis(np.linspace(0, 1, len(processed_nodes)))
            for shape_idx, node_list in enumerate(processed_nodes):
                sorted_nodes = sorted(node_list)
                viridis_color = viridis_colors[shape_idx]
                color_hex = '#%02x%02x%02x' % (int(viridis_color[0]*255), int(viridis_color[1]*255), int(viridis_color[2]*255))
                
                for i in range(len(sorted_nodes)):
                    current_idx = sorted_nodes[i]
                    next_idx = sorted_nodes[(i + 1) % len(sorted_nodes)]
                    
                    if current_idx < len(node_x) and next_idx < len(node_x):
                        x1, y1 = node_x[current_idx], node_y[current_idx]
                        x2, y2 = node_x[next_idx], node_y[next_idx]
                        fig.add_trace(
                            go.Scatter(
                                x=[x1, x2], y=[y1, y2],
                                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                line=dict(color=color_hex, width=3),
                                showlegend=False,
                                hoverinfo='none'
                            )
                        )
        else:
            # Single shape - use white
            sorted_nodes = sorted(processed_nodes)
            for i in range(len(sorted_nodes)):
                current_idx = sorted_nodes[i]
                next_idx = sorted_nodes[(i + 1) % len(sorted_nodes)]
                
                if current_idx < len(node_x) and next_idx < len(node_x):
                    x1, y1 = node_x[current_idx], node_y[current_idx]
                    x2, y2 = node_x[next_idx], node_y[next_idx]
                    fig.add_trace(
                        go.Scatter(
                            x=[x1, x2], y=[y1, y2],
                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                            line=dict(color='white', width=3),
                            showlegend=False,
                            hoverinfo='none'
                        )
                    )
    
    fig.add_trace(
        go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if show_labels else 'markers',
            marker=dict(
                size=node_size,
                color=node_colors,
                line=dict(color='white', width=2)
            ),
            text=node_text,
            textposition='middle center',
            textfont=dict(color='white', size=text_size, family='Arial', weight='bold'),
            hovertemplate='%{customdata}<extra></extra>',
            hoverlabel=dict(bgcolor='lightgrey', font_color='black'),
            customdata=hover_data,
            showlegend=False
        )
    )
    
    if calc_obj._interval_type_mode == "cents":
        equave_value = calc_obj._equave if isinstance(calc_obj._equave, float) else 1200.0
        equave_text = f"Equave: {equave_value:.1f}¢"
    else:
        equave_text = f"Equave: {calc_obj._equave}"
    
    fig.add_annotation(
        x=0, y=1.3,
        text=equave_text,
        showarrow=False,
        font=dict(color='white', size=text_size),
        align='center'
    )
    
    if title is None:
        if isinstance(obj, (AddressedScale, AddressedChord, AddressedSonority)):
            obj_type = type(obj).__name__.replace('Addressed', '')
            interval_type = "cents" if calc_obj._interval_type_mode == "cents" else "ratios"
            
            # Format root pitch with note name (no octave) and cent offset
            root_pitch = obj.reference_pitch
            root_note = root_pitch.pitchclass
            if abs(root_pitch.cents_offset) > 0.01:
                root_note += f" ({root_pitch.cents_offset:+.2f}¢)"
            
            title = f"{obj_type} ({interval_type}) - Root: {root_note}"
        else:
            obj_type = type(obj).__name__
            if calc_obj._interval_type_mode == "cents":
                title = f"{obj_type} (cents)"
            else:
                title = f"{obj_type} (ratios)"
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        xaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            range=[-1.5, 1.5]
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showticklabels=False,
            scaleanchor="x", scaleratio=1,
            range=[-1.5, 1.5]
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

def _plot_lattice(lattice: Lattice, figsize: tuple[float, float] = (12, 12),
                 node_size: float = 8, title: str = None, 
                 output_file: str = None, 
                 dim_reduction: str = None, target_dims: int = 3,
                 mds_metric: bool = True, mds_max_iter: int = 300,
                 spectral_affinity: str = 'rbf', spectral_gamma: float = None,
                 nodes: list = None, path_mode: str = 'adjacent',
                 mute_background: bool = False) -> go.Figure:
    import networkx as nx
    """
    Plot a Lattice as a 2D or 3D grid visualization.
    
    Args:
        lattice: Lattice instance to visualize
        figsize: Width and height of the output figure in inches
        node_size: Size of the nodes in the plot
        title: Title for the plot (auto-generated if None)
        output_file: Path to save the visualization (displays plot if None)
        dim_reduction: Dimensionality reduction method for high-dimensional lattices.
                      Options: 'mds', 'spectral', or None (raises error for dim > 3)
        target_dims: Target dimensionality for reduction (2 or 3, default 3)
        mds_metric: Whether to use metric MDS (True) or non-metric MDS (False)
        mds_max_iter: Maximum iterations for MDS algorithm
        spectral_affinity: Kernel for spectral embedding ('rbf', 'nearest_neighbors', etc.)
        spectral_gamma: Kernel coefficient for rbf kernel (auto-determined if None)
        nodes: List of coordinate tuples to highlight, e.g. [(0,0,0), (-3,2,0), (2,-1,1)]
               Highlights selected coordinates and draws edges based on path_mode
        path_mode: Edge drawing mode when nodes are selected. Options:
                  'adjacent' - Only show edges between selected nodes that are adjacent (default)
                  'origin' - Show shortest paths from origin (0,0,0...) to each selected node
        
    Returns:
        go.Figure: Plotly figure object
        
    Raises:
        ValueError: If lattice dimensionality > 3 and dim_reduction is None
    """
    if lattice.dimensionality > 3 and dim_reduction is None:
        raise ValueError(f"Plotting dimensionality > 3 requires dim_reduction. Got dimensionality={lattice.dimensionality}. "
                        f"Use dim_reduction='mds' or 'spectral'")
    
    if target_dims not in [2, 3]:
        raise ValueError(f"target_dims must be 2 or 3, got {target_dims}")
    
    if lattice.dimensionality <= 2:
        max_resolution = 5
    elif lattice.dimensionality == 3:
        max_resolution = 2
    else:
        if target_dims == 3:
            max_resolution = 1
        else:
            max_resolution = 3
    
    expected_total = 1
    for dim in lattice._dims:
        expected_total *= len(dim)
        if expected_total > 10000:
            expected_total = float('inf')
            break
    
    # If nodes are specified, use minimal resolution to just fit the selected nodes (for ALL lattices)
    if nodes:
        # Find the exact range needed for each dimension
        coord_ranges = []
        for dim in range(lattice.dimensionality):
            dim_vals = [coord[dim] for coord in nodes if coord in lattice]
            if dim_vals:
                min_val, max_val = min(dim_vals), max(dim_vals)
                # Add small buffer (1 coordinate) around the selection
                coord_ranges.append((min_val - 1, max_val + 1))
            else:
                coord_ranges.append((-1, 1))
        
        # Use custom coordinate range instead of resolution
        coords = []
        import itertools
        ranges = [range(start, end + 1) for start, end in coord_ranges]
        coords = list(itertools.product(*ranges))
        
        # Filter to only coordinates that exist in the lattice
        coords = [coord for coord in coords if coord in lattice]
    elif lattice.dimensionality > 3 or lattice._is_lazy or expected_total > 1000:
        coords = lattice._get_plot_coords(max_resolution)
    else:
        coords = lattice.coords
    
    # For reduced coordinate plotting, we need to build a reduced graph
    # to avoid iterating over thousands of edges in the full lattice
    if nodes or lattice.dimensionality > 3 or lattice._is_lazy or expected_total > 1000:
        # Build reduced graph with only the plotting coordinates
        G_reduced = nx.Graph()
        G_reduced.add_nodes_from(coords)
        
        # Add edges between coordinates that are adjacent in lattice structure
        for i, coord1 in enumerate(coords):
            for j, coord2 in enumerate(coords):
                if i < j:
                    # Check if coordinates are adjacent (differ by 1 in exactly one dimension)
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        G_reduced.add_edge(coord1, coord2)
        
        G = G_reduced
    else:
        G = lattice  # Use full lattice for small coordinate sets
    
    # Handle origin inclusion for path_mode='origin' before setting original_coords
    if nodes and path_mode == 'origin':
        origin = tuple(0 for _ in range(lattice.dimensionality))
        if origin not in coords:
            coords.append(origin)
            # Update the reduced graph if we're using one
            if hasattr(G, 'add_node'):
                G.add_node(origin)
                # Add edges from origin to adjacent coordinates
                for coord in coords:
                    if coord != origin:
                        diff_count = sum(1 for a, b in zip(origin, coord) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(origin, coord) if a == b)
                        if diff_count == 1 and same_count == len(coord) - 1:
                            G.add_edge(origin, coord)
    
    original_coords = coords
    
    if lattice.dimensionality > 3:
        coord_matrix = np.array([list(coord) for coord in coords])
        
        if dim_reduction == 'mds':
            reducer = MDS(n_components=target_dims, metric=mds_metric, max_iter=mds_max_iter, random_state=42)
            reduced_coords = reducer.fit_transform(coord_matrix)
        elif dim_reduction == 'spectral':
            if spectral_affinity == 'precomputed':
                # Build adjacency matrix from the sampled coordinates
                coord_to_idx = {coord: i for i, coord in enumerate(coords)}
                n = len(coords)
                adjacency_matrix = np.zeros((n, n))
                
                # Check adjacency based on lattice structure (neighbors differ by 1 in exactly one dimension)
                for i, coord1 in enumerate(coords):
                    for j, coord2 in enumerate(coords):
                        if i != j:
                            diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                            same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                            if diff_count == 1 and same_count == len(coord1) - 1:
                                adjacency_matrix[i, j] = 1
                
                reducer = SpectralEmbedding(n_components=target_dims, affinity='precomputed', random_state=42)
                reduced_coords = reducer.fit_transform(adjacency_matrix)
            else:
                reducer = SpectralEmbedding(n_components=target_dims, affinity=spectral_affinity, 
                                          gamma=spectral_gamma, random_state=42)
                reduced_coords = reducer.fit_transform(coord_matrix)
        else:
            raise ValueError(f"Unknown dim_reduction method: {dim_reduction}. Use 'mds' or 'spectral'")
        
        coords = [tuple(reduced_coords[i]) for i in range(len(coords))]
        effective_dimensionality = target_dims
        
        coord_mapping = {original_coords[i]: coords[i] for i in range(len(coords))}
        G_reduced = nx.Graph()
        G_reduced.add_nodes_from(coords)
        
        # Build edges based on lattice adjacency structure
        for i, coord1 in enumerate(original_coords):
            for j, coord2 in enumerate(original_coords):
                if i < j:
                    # Check if coordinates are adjacent (differ by 1 in exactly one dimension)
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        u_reduced = coord_mapping[coord1]
                        v_reduced = coord_mapping[coord2]
                        G_reduced.add_edge(u_reduced, v_reduced)
        
        G = G_reduced
    else:
        effective_dimensionality = lattice.dimensionality
        coord_mapping = {}
    
    if title is None:
        resolution_str = 'x'.join(str(r) for r in lattice.resolution)
        bipolar_str = "bipolar" if lattice.bipolar else "unipolar"
        if lattice.dimensionality > 3:
            title = f"{lattice.dimensionality}D→{target_dims}D Lattice ({resolution_str}, {bipolar_str}, {dim_reduction})"
        else:
            title = f"{lattice.dimensionality}D Lattice ({resolution_str}, {bipolar_str})"
    
    # Handle edge highlighting for selected coordinates
    # Only include nodes that actually exist in the plotting coordinate set
    if nodes:
        valid_coords = set(coords) if lattice.dimensionality <= 3 else set(original_coords)
        highlighted_coords = set(coord for coord in nodes if coord in valid_coords)
    else:
        highlighted_coords = set()
    
    # Determine if we should use dimmed appearance (whenever nodes are selected)
    use_dimmed = nodes is not None and len(nodes) > 0 and not mute_background
    
    fig = go.Figure()
    bounds_coords_override = None
    
    if effective_dimensionality == 1:
        
        if not (nodes and mute_background):
            edge_color = '#555555' if use_dimmed else '#808080'
            edge_width = 1 if use_dimmed else 3
            
            for u, v in G.edges():
                x1, y1 = u[0], 0
                x2, y2 = v[0], 0
                
                fig.add_trace(
                    go.Scatter(
                        x=[x1, x2], y=[y1, y2],
                        mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                        line=dict(color=edge_color, width=edge_width),
                        showlegend=False,
                        hoverinfo='none'
                    )
                )
        
        # Draw highlighted edges based on path_mode
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                # Original behavior: only edges between adjacent selected nodes
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        # Check if these coordinates are adjacent in the lattice structure
                        # (differ by 1 in exactly one dimension)
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            x1, x2 = coord1[0], coord2[0]
                            y1, y2 = 0, 0
                            fig.add_trace(
                                go.Scatter(
                                    x=[x1, x2], y=[y1, y2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                # New behavior: shortest paths from origin to each selected node
                origin = tuple(0 for _ in range(lattice.dimensionality))
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            # Find shortest path from origin to this target
                            if hasattr(G, 'has_node') and G.has_node(origin) and G.has_node(target_coord):
                                path_coords = nx.shortest_path(G, origin, target_coord)
                                
                                # Draw path edges
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, x2 = pc1[0], pc2[0]
                                    y1, y2 = 0, 0
                                    fig.add_trace(
                                        go.Scatter(
                                            x=[x1, x2], y=[y1, y2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            # Skip if path not found
                            continue
        
        node_x, node_y = [], []
        hover_data = []
        node_colors = []
        drawn_nodes = []
        
        # If we only want the sublattice, derive node iteration from drawn edges
        if nodes and mute_background:
            # Collect coordinates that are in highlighted edges or are highlighted nodes themselves
            drawn_set = set()
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        if diff_count == 1 and same_count == len(coord1) - 1:
                            drawn_set.add(coord1)
                            drawn_set.add(coord2)
            else:
                drawn_set.update(highlighted_coords)
            coords_iter = [(c[0],) for c in drawn_set]
        else:
            coords_iter = coords
        
        for i, coord in enumerate(coords_iter):
            x = coord[0]
            node_x.append(x)
            node_y.append(0)
            
            if lattice.dimensionality > 3:
                orig_coord_str = str(original_coords[i]).replace(',)', ')') if coords_iter is coords else 'selected'
                reduced_coord_str = f"({x:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}")
            else:
                hover_data.append(f"Coordinate: ({x})")
            
            if nodes and ((coords_iter is coords and original_coords[i] in highlighted_coords) or (coords_iter is not coords and (x,) in coords_iter)):
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')
            else:
                node_colors.append('white')
        
        fig.add_trace(
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                marker=dict(
                    size=node_size * 2,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
        
        fig.update_layout(
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[-0.5, 0.5]
            )
        )
    
    elif effective_dimensionality == 2:
        drawn_nodes = set()
        if not (nodes and mute_background):
            edge_color = '#555555' if use_dimmed else '#808080'
            edge_width = 1 if use_dimmed else 2
            
            for u, v in G.edges():
                x1, y1 = u
                x2, y2 = v
                
                fig.add_trace(
                    go.Scatter(
                        x=[x1, x2], y=[y1, y2],
                        mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                        line=dict(color=edge_color, width=edge_width),
                        showlegend=False,
                        hoverinfo='none'
                    )
                )
        
        # Draw highlighted edges based on path_mode
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                # Original behavior: only edges between adjacent selected nodes
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        # Check if these coordinates are adjacent in the lattice structure
                        # (differ by 1 in exactly one dimension)
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            if lattice.dimensionality > 3:
                                if coord1 in coord_mapping and coord2 in coord_mapping:
                                    plot_coord1 = coord_mapping[coord1]
                                    plot_coord2 = coord_mapping[coord2]
                                else:
                                    continue
                            else:
                                plot_coord1 = coord1
                                plot_coord2 = coord2
                            x1, y1 = plot_coord1[0], plot_coord1[1]
                            x2, y2 = plot_coord2[0], plot_coord2[1]
                            drawn_nodes.add((x1, y1))
                            drawn_nodes.add((x2, y2))
                            fig.add_trace(
                                go.Scatter(
                                    x=[x1, x2], y=[y1, y2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                # New behavior: shortest paths from origin to each selected node
                origin = tuple(0 for _ in range(lattice.dimensionality))
                origin_plot = coord_mapping.get(origin, origin) if lattice.dimensionality > 3 else origin
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            # Find shortest path from origin to this target
                            target_plot = coord_mapping.get(target_coord, target_coord) if lattice.dimensionality > 3 else target_coord
                            if hasattr(G, 'has_node') and G.has_node(origin_plot) and G.has_node(target_plot):
                                path_coords = nx.shortest_path(G, origin_plot, target_plot)
                                
                                # Draw path edges
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, y1 = pc1
                                    x2, y2 = pc2
                                    drawn_nodes.add((x1, y1))
                                    drawn_nodes.add((x2, y2))
                                    fig.add_trace(
                                        go.Scatter(
                                            x=[x1, x2], y=[y1, y2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            # Skip if path not found
                            continue
        
        node_x, node_y = [], []
        hover_data = []
        node_colors = []
        
        reverse_coord_mapping = {v: k for k, v in coord_mapping.items()} if len(coord_mapping) > 0 else {}
        coords_iter = coords
        if nodes and mute_background and len(drawn_nodes) > 0:
            coords_iter = list(drawn_nodes)
            bounds_coords_override = coords_iter
        
        for i, coord in enumerate(coords_iter):
            x, y = coord
            node_x.append(x)
            node_y.append(y)
            
            if lattice.dimensionality <= 3 or len(reverse_coord_mapping) == 0:
                orig_coord = coord
            else:
                orig_coord = reverse_coord_mapping.get(coord, None)
            
            if lattice.dimensionality > 3 and orig_coord is not None:
                orig_coord_str = str(orig_coord).replace(',)', ')')
                reduced_coord_str = f"({x:.2f}, {y:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}")
            else:
                hover_data.append(f"Coordinate: ({x}, {y})")
            
            # Set node color based on highlighting
            if nodes and orig_coord in highlighted_coords:
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')  # WAY more dimmed for non-selected nodes
            else:
                node_colors.append('white')  # Default color when no highlighting
        
        fig.add_trace(
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                marker=dict(
                    size=node_size * 2,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
        
        fig.update_layout(
            yaxis=dict(
                scaleanchor="x", scaleratio=1
            )
        )
    
    elif effective_dimensionality == 3:
        drawn_nodes = set()
        if not (nodes and mute_background):
            edge_color = '#555555' if use_dimmed else '#808080'
            edge_width = 1 if use_dimmed else 3
            
            for u, v in G.edges():
                x1, y1, z1 = (u[0], u[1], u[2]) if len(u) >= 3 else (u[0], u[1] if len(u) >= 2 else 0, 0)
                x2, y2, z2 = (v[0], v[1], v[2]) if len(v) >= 3 else (v[0], v[1] if len(v) >= 2 else 0, 0)
                
                fig.add_trace(
                    go.Scatter3d(
                        x=[x1, x2], y=[y1, y2], z=[z1, z2],
                        mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                        line=dict(color=edge_color, width=edge_width),
                        showlegend=False,
                        hoverinfo='none'
                    )
                )
        
        # Draw highlighted edges based on path_mode
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                # Original behavior: only edges between adjacent selected nodes
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        # Check if these coordinates are adjacent in the lattice structure
                        # (differ by 1 in exactly one dimension)
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            if lattice.dimensionality > 3:
                                if coord1 in coord_mapping and coord2 in coord_mapping:
                                    plot_coord1 = coord_mapping[coord1]
                                    plot_coord2 = coord_mapping[coord2]
                                else:
                                    continue
                            else:
                                plot_coord1 = coord1
                                plot_coord2 = coord2
                            x1, y1, z1 = (plot_coord1[0], plot_coord1[1], plot_coord1[2]) if len(plot_coord1) >= 3 else (plot_coord1[0], plot_coord1[1] if len(plot_coord1) >= 2 else 0, 0)
                            x2, y2, z2 = (plot_coord2[0], plot_coord2[1], plot_coord2[2]) if len(plot_coord2) >= 3 else (plot_coord2[0], plot_coord2[1] if len(plot_coord2) >= 2 else 0, 0)
                            drawn_nodes.add((x1, y1, z1))
                            drawn_nodes.add((x2, y2, z2))
                            fig.add_trace(
                                go.Scatter3d(
                                    x=[x1, x2], y=[y1, y2], z=[z1, z2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                # New behavior: shortest paths from origin to each selected node
                origin = tuple(0 for _ in range(lattice.dimensionality))
                origin_plot = coord_mapping.get(origin, origin) if lattice.dimensionality > 3 else origin
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            # Find shortest path from origin to this target
                            target_plot = coord_mapping.get(target_coord, target_coord) if lattice.dimensionality > 3 else target_coord
                            if hasattr(G, 'has_node') and G.has_node(origin_plot) and G.has_node(target_plot):
                                path_coords = nx.shortest_path(G, origin_plot, target_plot)
                                
                                # Draw path edges
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, y1, z1 = (pc1[0], pc1[1], pc1[2]) if len(pc1) >= 3 else (pc1[0], pc1[1] if len(pc1) >= 2 else 0, 0)
                                    x2, y2, z2 = (pc2[0], pc2[1], pc2[2]) if len(pc2) >= 3 else (pc2[0], pc2[1] if len(pc2) >= 2 else 0, 0)
                                    drawn_nodes.add((x1, y1, z1))
                                    drawn_nodes.add((x2, y2, z2))
                                    fig.add_trace(
                                        go.Scatter3d(
                                            x=[x1, x2], y=[y1, y2], z=[z1, z2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            # Skip if path not found
                            continue
        
        node_x, node_y, node_z = [], [], []
        hover_data = []
        node_colors = []
        
        reverse_coord_mapping = {v: k for k, v in coord_mapping.items()} if len(coord_mapping) > 0 else {}
        coords_iter = coords
        if nodes and mute_background and len(drawn_nodes) > 0:
            coords_iter = list(drawn_nodes)
            bounds_coords_override = coords_iter
        
        for i, coord in enumerate(coords_iter):
            if len(coord) >= 3:
                x, y, z = coord[0], coord[1], coord[2]
            elif len(coord) == 2:
                x, y, z = coord[0], coord[1], 0
            else:
                x, y, z = coord[0], 0, 0
            node_x.append(x)
            node_y.append(y) 
            node_z.append(z)
            
            if lattice.dimensionality <= 3 or len(reverse_coord_mapping) == 0:
                orig_coord = coord
            else:
                orig_coord = reverse_coord_mapping.get(coord, None)
            
            if lattice.dimensionality > 3 and orig_coord is not None:
                orig_coord_str = str(orig_coord).replace(',)', ')')
                reduced_coord_str = f"({x:.2f}, {y:.2f}, {z:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}")
            else:
                hover_data.append(f"Coordinate: ({x}, {y}, {z})")
            
            # Set node color based on highlighting
            if nodes and orig_coord in highlighted_coords:
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')  # WAY more dimmed for non-selected nodes
            else:
                node_colors.append('white')  # Default color when no highlighting
        
        fig.add_trace(
            go.Scatter3d(
                x=node_x, y=node_y, z=node_z,
                mode='markers',
                marker=dict(
                    size=node_size,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    bounds_coords = bounds_coords_override if (bounds_coords_override is not None and len(bounds_coords_override) > 0) else coords
    x_coords = [coord[0] for coord in bounds_coords]
    x_min, x_max = min(x_coords), max(x_coords)
    
    if effective_dimensionality >= 2:
        y_coords = [coord[1] for coord in bounds_coords]
        y_min, y_max = min(y_coords), max(y_coords)
    
    if effective_dimensionality == 3:
        z_coords = [coord[2] for coord in bounds_coords]
        z_min, z_max = min(z_coords), max(z_coords)
    
    if lattice.dimensionality > 3:
        x_ticks = np.linspace(x_min, x_max, min(10, int(x_max - x_min) + 1))
        x_ticks = [round(t, 1) for t in x_ticks]
        if effective_dimensionality >= 2:
            y_ticks = np.linspace(y_min, y_max, min(10, int(y_max - y_min) + 1))
            y_ticks = [round(t, 1) for t in y_ticks]
        if effective_dimensionality == 3:
            z_ticks = np.linspace(z_min, z_max, min(10, int(z_max - z_min) + 1))
            z_ticks = [round(t, 1) for t in z_ticks]
    else:
        x_ticks = list(range(int(x_min), int(x_max) + 1))
        if effective_dimensionality >= 2:
            y_ticks = list(range(int(y_min), int(y_max) + 1))
        if effective_dimensionality == 3:
            z_ticks = list(range(int(z_min), int(z_max) + 1))
    
    layout_dict = dict(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    if effective_dimensionality <= 2:
        if lattice.dimensionality > 3:
            layout_dict.update(dict(
                xaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, title=dict(text='', font=dict(color='white'))
                ),
                yaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, title=dict(text='', font=dict(color='white'))
                )
            ))
        else:
            x_title = 'X'
            y_title = 'Y' if effective_dimensionality == 2 else ''
            
            layout_dict.update(dict(
                xaxis=dict(
                    title=dict(text=x_title, font=dict(color='white')),
                    tickfont=dict(color='white'),
                    gridcolor='#555555',
                    zerolinecolor='#555555',
                    tickmode='array',
                    tickvals=x_ticks,
                    ticktext=[str(t) for t in x_ticks]
                ),
                yaxis=dict(
                    title=dict(text=y_title, font=dict(color='white')),
                    tickfont=dict(color='white'),
                    gridcolor='#555555',
                    zerolinecolor='#555555',
                    tickmode='array',
                    tickvals=y_ticks if effective_dimensionality == 2 else [0],
                    ticktext=[str(t) for t in y_ticks] if effective_dimensionality == 2 else ['']
                )
            ))
    else:
        if lattice.dimensionality > 3:
            layout_dict.update(dict(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        center=dict(x=0, y=0, z=0)
                    ),
                    xaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    yaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    zaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    bgcolor='black'
                )
            ))
        else:
            layout_dict.update(dict(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        center=dict(x=0, y=0, z=0)
                    ),
                    xaxis=dict(
                        title=dict(text='X', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=x_ticks,
                        ticktext=[str(t) for t in x_ticks],
                        range=[x_min - max(1, (x_max - x_min) * 0.05), x_max + max(1, (x_max - x_min) * 0.05)]
                    ),
                    yaxis=dict(
                        title=dict(text='Y', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=y_ticks,
                        ticktext=[str(t) for t in y_ticks],
                        range=[y_min - max(1, (y_max - y_min) * 0.05), y_max + max(1, (y_max - y_min) * 0.05)]
                    ),
                    zaxis=dict(
                        title=dict(text='Z', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=z_ticks,
                        ticktext=[str(t) for t in z_ticks],
                        range=[z_min - max(1, (z_max - z_min) * 0.05), z_max + max(1, (z_max - z_min) * 0.05)]
                    ),
                    bgcolor='black'
                )
            ))
    
    fig.update_layout(**layout_dict)
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig


def _plot_field(field: Field, figsize: tuple[float, float] = (12, 12),
               node_size: float = 8, title: str = None, 
               output_file: str = None, 
               dim_reduction: str = None, target_dims: int = 3,
               mds_metric: bool = True, mds_max_iter: int = 300,
               spectral_affinity: str = 'rbf', spectral_gamma: float = None,
               nodes: list = None, path_mode: str = 'adjacent',
               colormap: str = 'coolwarm', show_colorbar: bool = False) -> go.Figure:
    """
    Plot a Field as a 2D or 3D grid visualization with node colors representing field values.
    
    Args:
        field: Field instance to visualize
        figsize: Width and height of the output figure in inches
        node_size: Size of the nodes in the plot
        title: Title for the plot (auto-generated if None)
        output_file: Path to save the visualization (displays plot if None)
        dim_reduction: Dimensionality reduction method for high-dimensional fields.
                      Options: 'mds', 'spectral', or None (raises error for dim > 3)
        target_dims: Target dimensionality for reduction (2 or 3, default 3)
        mds_metric: Whether to use metric MDS (True) or non-metric MDS (False)
        mds_max_iter: Maximum iterations for MDS algorithm
        spectral_affinity: Kernel for spectral embedding ('rbf', 'nearest_neighbors', etc.)
        spectral_gamma: Kernel coefficient for rbf kernel (auto-determined if None)
        nodes: List of coordinate tuples to highlight, e.g. [(0,0,0), (-3,2,0), (2,-1,1)]
               Highlights selected coordinates and draws edges based on path_mode
        path_mode: Edge drawing mode when nodes are selected. Options:
                  'adjacent' - Only show edges between selected nodes that are adjacent (default)
                  'origin' - Show shortest paths from origin (0,0,0...) to each selected node
        colormap: Matplotlib colormap name for field values (default: 'hot')
        show_colorbar: Whether to show the colorbar (default: False)
        
    Returns:
        go.Figure: Plotly figure object
        
    Raises:
        ValueError: If field dimensionality > 3 and dim_reduction is None
    """
    import networkx as nx
    import matplotlib.pyplot as plt
    from sklearn.manifold import MDS, SpectralEmbedding
    
    if field.dimensionality > 3 and dim_reduction is None:
        raise ValueError(f"Plotting dimensionality > 3 requires dim_reduction. Got dimensionality={field.dimensionality}. "
                        f"Use dim_reduction='mds' or 'spectral'")
    
    if target_dims not in [2, 3]:
        raise ValueError(f"target_dims must be 2 or 3, got {target_dims}")
    
    if field.dimensionality <= 2:
        max_resolution = 5
    elif field.dimensionality == 3:
        max_resolution = 2
    else:
        if target_dims == 3:
            max_resolution = 1
        else:
            max_resolution = 3
    
    expected_total = 1
    for dim in field._dims:
        expected_total *= len(dim)
        if expected_total > 10000:
            expected_total = float('inf')
            break
    
    if nodes:
        coord_ranges = []
        for dim in range(field.dimensionality):
            dim_vals = [coord[dim] for coord in nodes if coord in field]
            if dim_vals:
                min_val, max_val = min(dim_vals), max(dim_vals)
                coord_ranges.append((min_val - 1, max_val + 1))
            else:
                coord_ranges.append((-1, 1))
        
        coords = []
        import itertools
        ranges = [range(start, end + 1) for start, end in coord_ranges]
        coords = list(itertools.product(*ranges))
        
        coords = [coord for coord in coords if coord in field]
    elif field.dimensionality > 3 or field._is_lazy or expected_total > 1000:
        coords = field._get_plot_coords(max_resolution)
    else:
        coords = field.coords
    
    if nodes or field.dimensionality > 3 or field._is_lazy or expected_total > 1000:
        G_reduced = nx.Graph()
        G_reduced.add_nodes_from(coords)
        
        for i, coord1 in enumerate(coords):
            for j, coord2 in enumerate(coords):
                if i < j:
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        G_reduced.add_edge(coord1, coord2)
        
        G = G_reduced
    else:
        G = field
    
    if nodes and path_mode == 'origin':
        origin = tuple(0 for _ in range(field.dimensionality))
        if origin not in coords:
            coords.append(origin)
            if hasattr(G, 'add_node'):
                G.add_node(origin)
                for coord in coords:
                    if coord != origin:
                        diff_count = sum(1 for a, b in zip(origin, coord) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(origin, coord) if a == b)
                        if diff_count == 1 and same_count == len(coord) - 1:
                            G.add_edge(origin, coord)
    
    original_coords = coords
    
    if field.dimensionality > 3:
        coord_matrix = np.array([list(coord) for coord in coords])
        
        if dim_reduction == 'mds':
            reducer = MDS(n_components=target_dims, metric=mds_metric, max_iter=mds_max_iter, random_state=42)
            reduced_coords = reducer.fit_transform(coord_matrix)
        elif dim_reduction == 'spectral':
            if spectral_affinity == 'precomputed':
                coord_to_idx = {coord: i for i, coord in enumerate(coords)}
                n = len(coords)
                adjacency_matrix = np.zeros((n, n))
                
                for i, coord1 in enumerate(coords):
                    for j, coord2 in enumerate(coords):
                        if i != j:
                            diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                            same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                            if diff_count == 1 and same_count == len(coord1) - 1:
                                adjacency_matrix[i, j] = 1
                
                reducer = SpectralEmbedding(n_components=target_dims, affinity='precomputed', random_state=42)
                reduced_coords = reducer.fit_transform(adjacency_matrix)
            else:
                reducer = SpectralEmbedding(n_components=target_dims, affinity=spectral_affinity, 
                                          gamma=spectral_gamma, random_state=42)
                reduced_coords = reducer.fit_transform(coord_matrix)
        else:
            raise ValueError(f"Unknown dim_reduction method: {dim_reduction}. Use 'mds' or 'spectral'")
        
        coords = [tuple(reduced_coords[i]) for i in range(len(coords))]
        effective_dimensionality = target_dims
        
        coord_mapping = {original_coords[i]: coords[i] for i in range(len(coords))}
        G_reduced = nx.Graph()
        G_reduced.add_nodes_from(coords)
        
        for i, coord1 in enumerate(original_coords):
            for j, coord2 in enumerate(original_coords):
                if i < j:
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        u_reduced = coord_mapping[coord1]
                        v_reduced = coord_mapping[coord2]
                        G_reduced.add_edge(u_reduced, v_reduced)
        
        G = G_reduced
    else:
        effective_dimensionality = field.dimensionality
    
    field_values = []
    for coord in original_coords:
        try:
            field_values.append(field.get_field_value(coord))
        except KeyError:
            field_values.append(0.0)
    
    field_values = np.array(field_values)
    
    if len(field_values) > 0:
        vmin, vmax = field_values.min(), field_values.max()
        if vmax == vmin:
            vmax = vmin + 1e-10
    else:
        vmin, vmax = 0, 1
    
    cmap = plt.get_cmap(colormap)
    normalized_values = (field_values - vmin) / (vmax - vmin)
    colors = [cmap(val) for val in normalized_values]
    color_hex = ['#%02x%02x%02x' % (int(c[0]*255), int(c[1]*255), int(c[2]*255)) for c in colors]
    
    # Map matplotlib colormap names to plotly colormap names
    plotly_colormap_mapping = {
        'viridis': 'viridis',
        'plasma': 'plasma', 
        'inferno': 'inferno',
        'magma': 'magma',
        'coolwarm': 'rdbu',
        'hot': 'hot',
        'cool': 'blues',
        'spring': 'greens',
        'summer': 'ylgnbu',
        'autumn': 'orrd',
        'winter': 'blues',
        'copper': 'burg',
        'gray': 'greys',
        'grey': 'greys',
        'jet': 'jet',
        'hsv': 'hsv',
        'rainbow': 'rainbow',
        'seismic': 'rdbu',
        'terrain': 'earth',
        'spectral': 'spectral',
        'RdYlBu': 'rdylbu',
        'RdBu': 'rdbu',
        'PiYG': 'piyg',
        'PRGn': 'prgn',
        'BrBG': 'brbg',
        'RdGy': 'rdgy',
        'PuOr': 'puor'
    }
    
    plotly_colormap = plotly_colormap_mapping.get(colormap, 'viridis')
    
    if title is None:
        resolution_str = 'x'.join(str(r) for r in field.resolution)
        bipolar_str = "bipolar" if field.bipolar else "unipolar"
        if field.dimensionality > 3:
            title = f"{field.dimensionality}D→{target_dims}D Field ({resolution_str}, {bipolar_str}, {dim_reduction})"
        else:
            title = f"{field.dimensionality}D Field ({resolution_str}, {bipolar_str})"
    
    if nodes:
        valid_coords = set(coords) if field.dimensionality <= 3 else set(original_coords)
        highlighted_coords = set(coord for coord in nodes if coord in valid_coords)
    else:
        highlighted_coords = set()
    
    use_dimmed = nodes is not None and len(nodes) > 0
    
    fig = go.Figure()
    
    if effective_dimensionality == 1:
        
        # Draw edges with gradient colors based on field values
        for u, v in G.edges():
            x1, y1 = u[0], 0
            x2, y2 = v[0], 0
            
            # Get field values at both nodes
            u_idx = coords.index(u) if u in coords else -1
            v_idx = coords.index(v) if v in coords else -1
            
            if u_idx >= 0 and v_idx >= 0 and u_idx < len(field_values) and v_idx < len(field_values):
                u_val = field_values[u_idx]
                v_val = field_values[v_idx]
                
                # Create gradient color between the two values
                avg_val = (u_val + v_val) / 2
                normalized_avg = (avg_val - vmin) / (vmax - vmin) if vmax != vmin else 0.5
                avg_color = cmap(normalized_avg)
                edge_color_hex = '#%02x%02x%02x' % (int(avg_color[0]*255), int(avg_color[1]*255), int(avg_color[2]*255))
                
                # Dim the edge color slightly
                edge_color_dimmed = '#%02x%02x%02x' % (
                    int(int(edge_color_hex[1:3], 16) * 0.7),
                    int(int(edge_color_hex[3:5], 16) * 0.7),
                    int(int(edge_color_hex[5:7], 16) * 0.7)
                )
            else:
                edge_color_dimmed = '#555555'
            
            edge_width = 1 if use_dimmed else 2
            
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                    line=dict(color=edge_color_dimmed, width=edge_width),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            x1, x2 = coord1[0], coord2[0]
                            y1, y2 = 0, 0
                            fig.add_trace(
                                go.Scatter(
                                    x=[x1, x2], y=[y1, y2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                origin = tuple(0 for _ in range(field.dimensionality))
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            if hasattr(G, 'has_node') and G.has_node(origin) and G.has_node(target_coord):
                                path_coords = nx.shortest_path(G, origin, target_coord)
                                
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, x2 = pc1[0], pc2[0]
                                    y1, y2 = 0, 0
                                    fig.add_trace(
                                        go.Scatter(
                                            x=[x1, x2], y=[y1, y2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            continue
        
        node_x, node_y = [], []
        hover_data = []
        node_colors = []
        
        for i, coord in enumerate(coords):
            x = coord[0]
            node_x.append(x)
            node_y.append(0)
            
            orig_coord = coord if field.dimensionality <= 3 else original_coords[i]
            field_val = field_values[i] if i < len(field_values) else 0.0
            
            if field.dimensionality > 3:
                orig_coord_str = str(original_coords[i]).replace(',)', ')')
                reduced_coord_str = f"({x:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}<br>Value: {field_val:.4f}")
            else:
                hover_data.append(f"Coordinate: ({x})<br>Value: {field_val:.4f}")
            
            if nodes and orig_coord in highlighted_coords:
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')
            else:
                node_colors.append(color_hex[i] if i < len(color_hex) else '#FFFFFF')
        
        fig.add_trace(
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                marker=dict(
                    size=node_size * 2,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
        
        fig.update_layout(
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=[-0.5, 0.5]
            )
        )
    
    elif effective_dimensionality == 2:
        # Draw edges with gradient colors based on field values
        for u, v in G.edges():
            x1, y1 = u
            x2, y2 = v
            
            # Get field values at both nodes
            u_idx = coords.index(u) if u in coords else -1
            v_idx = coords.index(v) if v in coords else -1
            
            if u_idx >= 0 and v_idx >= 0 and u_idx < len(field_values) and v_idx < len(field_values):
                u_val = field_values[u_idx]
                v_val = field_values[v_idx]
                
                # Create gradient color between the two values
                avg_val = (u_val + v_val) / 2
                normalized_avg = (avg_val - vmin) / (vmax - vmin) if vmax != vmin else 0.5
                avg_color = cmap(normalized_avg)
                edge_color_hex = '#%02x%02x%02x' % (int(avg_color[0]*255), int(avg_color[1]*255), int(avg_color[2]*255))
                
                # Dim the edge color slightly
                edge_color_dimmed = '#%02x%02x%02x' % (
                    int(int(edge_color_hex[1:3], 16) * 0.7),
                    int(int(edge_color_hex[3:5], 16) * 0.7),
                    int(int(edge_color_hex[5:7], 16) * 0.7)
                )
            else:
                edge_color_dimmed = '#555555'
            
            edge_width = 1 if use_dimmed else 2
            
            fig.add_trace(
                go.Scatter(
                    x=[x1, x2], y=[y1, y2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                    line=dict(color=edge_color_dimmed, width=edge_width),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            x1, y1 = coord1
                            x2, y2 = coord2
                            fig.add_trace(
                                go.Scatter(
                                    x=[x1, x2], y=[y1, y2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                origin = tuple(0 for _ in range(field.dimensionality))
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            if hasattr(G, 'has_node') and G.has_node(origin) and G.has_node(target_coord):
                                path_coords = nx.shortest_path(G, origin, target_coord)
                                
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, y1 = pc1
                                    x2, y2 = pc2
                                    fig.add_trace(
                                        go.Scatter(
                                            x=[x1, x2], y=[y1, y2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            continue
        
        node_x, node_y = [], []
        hover_data = []
        node_colors = []
        
        for i, coord in enumerate(coords):
            x, y = coord
            node_x.append(x)
            node_y.append(y)
            
            orig_coord = coord if field.dimensionality <= 3 else original_coords[i]
            field_val = field_values[i] if i < len(field_values) else 0.0
            
            if field.dimensionality > 3:
                orig_coord_str = str(original_coords[i]).replace(',)', ')')
                reduced_coord_str = f"({x:.2f}, {y:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}<br>Value: {field_val:.4f}")
            else:
                hover_data.append(f"Coordinate: ({x}, {y})<br>Value: {field_val:.4f}")
            
            if nodes and orig_coord in highlighted_coords:
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')
            else:
                node_colors.append(color_hex[i] if i < len(color_hex) else '#FFFFFF')
        
        fig.add_trace(
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                marker=dict(
                    size=node_size * 2,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
        
        fig.update_layout(
            yaxis=dict(
                scaleanchor="x", scaleratio=1
            )
        )
    
    elif effective_dimensionality == 3:
        # Draw edges with gradient colors based on field values
        for u, v in G.edges():
            x1, y1, z1 = (u[0], u[1], u[2]) if len(u) >= 3 else (u[0], u[1] if len(u) >= 2 else 0, 0)
            x2, y2, z2 = (v[0], v[1], v[2]) if len(v) >= 3 else (v[0], v[1] if len(v) >= 2 else 0, 0)
            
            # Get field values at both nodes
            u_idx = coords.index(u) if u in coords else -1
            v_idx = coords.index(v) if v in coords else -1
            
            if u_idx >= 0 and v_idx >= 0 and u_idx < len(field_values) and v_idx < len(field_values):
                u_val = field_values[u_idx]
                v_val = field_values[v_idx]
                
                # Create gradient color between the two values
                avg_val = (u_val + v_val) / 2
                normalized_avg = (avg_val - vmin) / (vmax - vmin) if vmax != vmin else 0.5
                avg_color = cmap(normalized_avg)
                edge_color_hex = '#%02x%02x%02x' % (int(avg_color[0]*255), int(avg_color[1]*255), int(avg_color[2]*255))
                
                # Dim the edge color slightly
                edge_color_dimmed = '#%02x%02x%02x' % (
                    int(int(edge_color_hex[1:3], 16) * 0.7),
                    int(int(edge_color_hex[3:5], 16) * 0.7),
                    int(int(edge_color_hex[5:7], 16) * 0.7)
                )
            else:
                edge_color_dimmed = '#555555'
            
            edge_width = 1 if use_dimmed else 2
            
            fig.add_trace(
                go.Scatter3d(
                    x=[x1, x2], y=[y1, y2], z=[z1, z2],
                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                    line=dict(color=edge_color_dimmed, width=edge_width),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        if nodes and len(highlighted_coords) >= 1:
            highlighted_list = list(highlighted_coords)
            
            if path_mode == 'adjacent' and len(highlighted_coords) > 1:
                for i in range(len(highlighted_list)):
                    for j in range(i + 1, len(highlighted_list)):
                        coord1, coord2 = highlighted_list[i], highlighted_list[j]
                        
                        diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                        is_lattice_adjacent = diff_count == 1 and same_count == len(coord1) - 1
                        
                        if is_lattice_adjacent:
                            x1, y1, z1 = (coord1[0], coord1[1], coord1[2]) if len(coord1) >= 3 else (coord1[0], coord1[1] if len(coord1) >= 2 else 0, 0)
                            x2, y2, z2 = (coord2[0], coord2[1], coord2[2]) if len(coord2) >= 3 else (coord2[0], coord2[1] if len(coord2) >= 2 else 0, 0)
                            fig.add_trace(
                                go.Scatter3d(
                                    x=[x1, x2], y=[y1, y2], z=[z1, z2],
                                    mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                    line=dict(color='white', width=4),
                                    showlegend=False,
                                    hoverinfo='none'
                                )
                            )
            
            elif path_mode == 'origin':
                origin = tuple(0 for _ in range(field.dimensionality))
                
                for target_coord in highlighted_list:
                    if target_coord != origin:
                        try:
                            if hasattr(G, 'has_node') and G.has_node(origin) and G.has_node(target_coord):
                                path_coords = nx.shortest_path(G, origin, target_coord)
                                
                                for k in range(len(path_coords) - 1):
                                    pc1, pc2 = path_coords[k], path_coords[k + 1]
                                    x1, y1, z1 = (pc1[0], pc1[1], pc1[2]) if len(pc1) >= 3 else (pc1[0], pc1[1] if len(pc1) >= 2 else 0, 0)
                                    x2, y2, z2 = (pc2[0], pc2[1], pc2[2]) if len(pc2) >= 3 else (pc2[0], pc2[1] if len(pc2) >= 2 else 0, 0)
                                    fig.add_trace(
                                        go.Scatter3d(
                                            x=[x1, x2], y=[y1, y2], z=[z1, z2],
                                            mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                                            line=dict(color='white', width=4),
                                            showlegend=False,
                                            hoverinfo='none'
                                        )
                                    )
                        except (KeyError, nx.NetworkXNoPath):
                            continue
        
        node_x, node_y, node_z = [], [], []
        hover_data = []
        node_colors = []
        
        for i, coord in enumerate(coords):
            if len(coord) >= 3:
                x, y, z = coord[0], coord[1], coord[2]
            elif len(coord) == 2:
                x, y, z = coord[0], coord[1], 0
            else:
                x, y, z = coord[0], 0, 0
            node_x.append(x)
            node_y.append(y) 
            node_z.append(z)
            
            orig_coord = coord if field.dimensionality <= 3 else original_coords[i]
            field_val = field_values[i] if i < len(field_values) else 0.0
            
            if field.dimensionality > 3:
                orig_coord_str = str(original_coords[i]).replace(',)', ')')
                reduced_coord_str = f"({x:.2f}, {y:.2f}, {z:.2f})"
                hover_data.append(f"Original: {orig_coord_str}<br>Reduced: {reduced_coord_str}<br>Value: {field_val:.4f}")
            else:
                hover_data.append(f"Coordinate: ({x}, {y}, {z})<br>Value: {field_val:.4f}")
            
            if nodes and orig_coord in highlighted_coords:
                node_colors.append('white')
            elif use_dimmed:
                node_colors.append('#111111')
            else:
                node_colors.append(color_hex[i] if i < len(color_hex) else '#FFFFFF')
        
        fig.add_trace(
            go.Scatter3d(
                x=node_x, y=node_y, z=node_z,
                mode='markers',
                marker=dict(
                    size=node_size,
                    color=node_colors,
                    line=dict(color='white', width=2)
                ),
                hovertemplate='%{text}<extra></extra>',
                text=hover_data,
                showlegend=False
            )
        )
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    x_coords = [coord[0] for coord in coords]
    x_min, x_max = min(x_coords), max(x_coords)
    
    if effective_dimensionality >= 2:
        y_coords = [coord[1] for coord in coords]
        y_min, y_max = min(y_coords), max(y_coords)
    
    if effective_dimensionality == 3:
        z_coords = [coord[2] for coord in coords]
        z_min, z_max = min(z_coords), max(z_coords)
    
    if field.dimensionality > 3:
        x_ticks = np.linspace(x_min, x_max, min(10, int(x_max - x_min) + 1))
        x_ticks = [round(t, 1) for t in x_ticks]
        if effective_dimensionality >= 2:
            y_ticks = np.linspace(y_min, y_max, min(10, int(y_max - y_min) + 1))
            y_ticks = [round(t, 1) for t in y_ticks]
        if effective_dimensionality == 3:
            z_ticks = np.linspace(z_min, z_max, min(10, int(z_max - z_min) + 1))
            z_ticks = [round(t, 1) for t in z_ticks]
    else:
        x_ticks = list(range(int(x_min), int(x_max) + 1))
        if effective_dimensionality >= 2:
            y_ticks = list(range(int(y_min), int(y_max) + 1))
        if effective_dimensionality == 3:
            z_ticks = list(range(int(z_min), int(z_max) + 1))
    
    layout_dict = dict(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    if effective_dimensionality <= 2:
        if field.dimensionality > 3:
            layout_dict.update(dict(
                xaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, title=dict(text='', font=dict(color='white'))
                ),
                yaxis=dict(
                    showgrid=False, zeroline=False, showticklabels=False,
                    showline=False, title=dict(text='', font=dict(color='white'))
                )
            ))
        else:
            x_title = 'X'
            y_title = 'Y' if effective_dimensionality == 2 else ''
            
            layout_dict.update(dict(
                xaxis=dict(
                    title=dict(text=x_title, font=dict(color='white')),
                    tickfont=dict(color='white'),
                    gridcolor='#555555',
                    zerolinecolor='#555555',
                    tickmode='array',
                    tickvals=x_ticks,
                    ticktext=[str(t) for t in x_ticks]
                ),
                yaxis=dict(
                    title=dict(text=y_title, font=dict(color='white')),
                    tickfont=dict(color='white'),
                    gridcolor='#555555',
                    zerolinecolor='#555555',
                    tickmode='array',
                    tickvals=y_ticks if effective_dimensionality == 2 else [0],
                    ticktext=[str(t) for t in y_ticks] if effective_dimensionality == 2 else ['']
                )
            ))
    else:
        if field.dimensionality > 3:
            layout_dict.update(dict(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        center=dict(x=0, y=0, z=0)
                    ),
                    xaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    yaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    zaxis=dict(
                        showgrid=False, zeroline=False, showticklabels=False,
                        showline=False, showbackground=False,
                        title=dict(text='', font=dict(color='white'))
                    ),
                    bgcolor='black'
                )
            ))
        else:
            layout_dict.update(dict(
                scene=dict(
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.5),
                        center=dict(x=0, y=0, z=0)
                    ),
                    xaxis=dict(
                        title=dict(text='X', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=x_ticks,
                        ticktext=[str(t) for t in x_ticks]
                    ),
                    yaxis=dict(
                        title=dict(text='Y', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=y_ticks,
                        ticktext=[str(t) for t in y_ticks]
                    ),
                    zaxis=dict(
                        title=dict(text='Z', font=dict(color='white')),
                        tickfont=dict(color='white'),
                        gridcolor='#555555',
                        zerolinecolor='#555555',
                        backgroundcolor='black',
                        tickmode='array',
                        tickvals=z_ticks,
                        ticktext=[str(t) for t in z_ticks]
                    ),
                    bgcolor='black'
                )
            ))
    
    if show_colorbar and len(field_values) > 0 and vmax != vmin:
        fig.add_trace(
            go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(
                    colorscale=plotly_colormap,
                    cmin=vmin,
                    cmax=vmax,
                    colorbar=dict(
                        title=dict(text="Field Value", font=dict(color='white')),
                        tickfont=dict(color='white'),
                        x=1.02
                    ),
                    showscale=True
                ),
                showlegend=False,
                hoverinfo='skip'
            )
        )
    
    fig.update_layout(**layout_dict)
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig
def _plot_ratio_scale_chord_new(obj, calc_obj, degrees, calc_degrees, fig, figsize,
                               text_size, show_labels, title, output_file, layout):
    """Plot ratio-based scales/chords as proportional segments."""
    n_degrees = len(degrees)
    
    if n_degrees < 2:
        raise ValueError("Need at least 2 degrees to plot intervals")
    
    # Get the complete intervals (including final interval to equave)
    if hasattr(calc_obj, 'complete_intervals'):
        interval_ratios = calc_obj.complete_intervals
    else:
        # Fallback for other types
        interval_ratios = list(calc_obj.intervals)
        if calc_obj._degrees:
            final_interval = calc_obj._equave / calc_obj._degrees[-1]
            interval_ratios.append(final_interval)
    
    # Convert interval ratios to log sizes for proportional display
    intervals = [math.log(float(ratio)) for ratio in interval_ratios]
    n_segments = len(interval_ratios)
    
    total_log_size = sum(intervals)
    
    if layout == 'circle':
        current_angle = math.pi / 2
        # Color based on distance from unison (1/1)
        colors = []
        for i in range(n_segments):
            if i < len(calc_degrees):
                # Distance from unison in log space
                distance = abs(math.log(float(calc_degrees[i])))
                hue = min(distance / 2.0, 1.0)  # Normalize and cap at 1.0
            else:
                # Final interval - use distance based on equave
                distance = abs(math.log(float(calc_obj._equave)))
                hue = min(distance / 2.0, 1.0)
            colors.append(plt.cm.hsv(hue))
        
        for i, (interval_size, interval_ratio) in enumerate(zip(intervals, interval_ratios)):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            angle_span = 2 * math.pi * proportion
            
            num_points = max(50, int(angle_span * 50))
            angles = np.linspace(current_angle, current_angle - angle_span, num_points)
            
            inner_radius = 0.85
            outer_radius = 1.0
            
            x_outer = outer_radius * np.cos(angles)
            y_outer = outer_radius * np.sin(angles)
            x_inner = inner_radius * np.cos(angles)
            y_inner = inner_radius * np.sin(angles)
            
            x_coords = np.concatenate([x_outer, x_inner[::-1], [x_outer[0]]])
            y_coords = np.concatenate([y_outer, y_inner[::-1], [y_outer[0]]])
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            if i < len(degrees):
                degree = degrees[i]
                calc_degree = calc_degrees[i]
                
                if isinstance(obj, (AddressedScale, AddressedChord, AddressedSonority)):
                    note_name = degree.pitchclass
                    cents_offset = degree.cents_offset
                    cent_info = f" ({cents_offset:+.2f}¢)" if abs(cents_offset) > 0.01 else ""
                    hover_text = f"Degree {i}<br>{calc_degree}<br>{note_name}{cent_info}"
                    label_text = f"{calc_degree}" if show_labels else ""
                else:
                    hover_text = f"Degree {i}<br>{calc_degree}"
                    label_text = f"{calc_degree}" if show_labels else ""
            else:
                hover_text = f"To Equave<br>{calc_obj._equave}"
                label_text = f"{calc_obj._equave}" if show_labels else ""
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            if show_labels and label_text:
                mid_angle = current_angle - angle_span / 2
                label_radius = 0.85
                label_x = label_radius * math.cos(mid_angle)
                label_y = label_radius * math.sin(mid_angle)
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[label_text],
                    textfont=dict(color='white', size=text_size, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_angle -= angle_span
        
        fig.update_layout(
            xaxis=dict(
                range=[-1.2, 1.2],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-1.2, 1.2], 
                scaleanchor="x", 
                scaleratio=1,
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    else:
        current_pos = 0
        # Color based on distance from unison (1/1)
        colors = []
        for i in range(n_segments):
            if i < len(calc_degrees):
                # Distance from unison in log space
                distance = abs(math.log(float(calc_degrees[i])))
                hue = min(distance / 2.0, 1.0)  # Normalize and cap at 1.0
            else:
                # Final interval - use distance based on equave
                distance = abs(math.log(float(calc_obj._equave)))
                hue = min(distance / 2.0, 1.0)
            colors.append(plt.cm.hsv(hue))
        y_center = 0
        bar_height = 0.3
        
        for i, interval_size in enumerate(intervals):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            segment_width = proportion * 2.0
            
            x_coords = [current_pos, current_pos + segment_width, current_pos + segment_width, current_pos, current_pos]
            y_coords = [y_center - bar_height/2, y_center - bar_height/2, y_center + bar_height/2, y_center + bar_height/2, y_center - bar_height/2]
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            if i < len(degrees):
                degree = degrees[i]
                calc_degree = calc_degrees[i]
                
                if isinstance(obj, (AddressedScale, AddressedChord, AddressedSonority)):
                    note_name = degree.pitchclass
                    cents_offset = degree.cents_offset
                    cent_info = f" ({cents_offset:+.2f}¢)" if abs(cents_offset) > 0.01 else ""
                    hover_text = f"Degree {i}<br>{calc_degree}<br>{note_name}{cent_info}"
                    label_text = f"{calc_degree}" if show_labels else ""
                else:
                    hover_text = f"Degree {i}<br>{calc_degree}"
                    label_text = f"{calc_degree}" if show_labels else ""
            else:
                hover_text = f"To Equave<br>{calc_obj._equave}"
                label_text = f"{calc_obj._equave}" if show_labels else ""
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            if show_labels and label_text:
                label_x = current_pos + segment_width / 2
                label_y = y_center
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[label_text],
                    textfont=dict(color='white', size=text_size, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_pos += segment_width
        
        fig.update_layout(
            xaxis=dict(
                range=[-0.1, 2.1],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-0.5, 0.5],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    if title is None:
        title = repr(obj)
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0),
    )
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig
def _plot_ratio_scale_chord_fixed(obj, calc_obj, degrees, calc_degrees, fig, figsize,
                                 text_size, show_labels, title, output_file, layout):
    """Plot ratio-based scales/chords as proportional segments."""
    n_degrees = len(degrees)
    
    if n_degrees < 2:
        raise ValueError("Need at least 2 degrees to plot intervals")
    
    # Use the intervals property (Scale now includes final interval)
    interval_ratios = calc_obj.intervals
    
    # Convert interval ratios to log sizes for proportional display
    intervals = [math.log(float(ratio)) for ratio in interval_ratios]
    n_segments = len(interval_ratios)
    total_log_size = sum(intervals)
    
    if layout == 'circle':
        current_angle = math.pi / 2
        # Color based on distance from unison (1/1)
        colors = []
        for i in range(n_segments):
            if i < len(calc_degrees):
                # Distance from unison in log space
                distance = abs(math.log(float(calc_degrees[i])))
                hue = min(distance / 2.0, 1.0)  # Normalize and cap at 1.0
            else:
                # Final interval - use distance based on equave
                distance = abs(math.log(float(calc_obj._equave)))
                hue = min(distance / 2.0, 1.0)
            colors.append(plt.cm.hsv(hue))
        
        # Add degree labels at borders first
        if show_labels:
            for i, calc_degree in enumerate(calc_degrees):
                degree_angle = current_angle
                for j in range(i):
                    degree_angle -= 2 * math.pi * (intervals[j] / total_log_size)
                
                degree_radius = 1.1
                degree_x = degree_radius * math.cos(degree_angle)
                degree_y = degree_radius * math.sin(degree_angle)
                
                fig.add_trace(go.Scatter(
                     x=[degree_x], y=[degree_y],
                     mode='text',
                     text=[f"{calc_degree}"],
                     textfont=dict(color='white', size=text_size+2, family='Arial'),
                     showlegend=False,
                     hovertemplate=f'Node {i}<br>Degree: {calc_degree}<extra></extra>',
                     hoverlabel=dict(bgcolor='lightgrey', font_color='black')
                 ))
            
            # Add equave label at the end
            equave_x = 1.1 * math.cos(math.pi / 2)
            equave_y = 1.1 * math.sin(math.pi / 2)
            fig.add_trace(go.Scatter(
                 x=[equave_x], y=[equave_y],
                 mode='text',
                 text=["1/1"],
                 textfont=dict(color='white', size=text_size+2, family='Arial'),
                 showlegend=False,
                 hovertemplate=f'Node 0<br>Degree: 1/1<extra></extra>',
                 hoverlabel=dict(bgcolor='lightgrey', font_color='black')
             ))
        
        # Draw interval segments
        for i, (interval_size, interval_ratio) in enumerate(zip(intervals, interval_ratios)):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            angle_span = 2 * math.pi * proportion
            
            num_points = max(50, int(angle_span * 50))
            angles = np.linspace(current_angle, current_angle - angle_span, num_points)
            
            inner_radius = 0.85
            outer_radius = 1.0
            
            x_outer = outer_radius * np.cos(angles)
            y_outer = outer_radius * np.sin(angles)
            x_inner = inner_radius * np.cos(angles)
            y_inner = inner_radius * np.sin(angles)
            
            x_coords = np.concatenate([x_outer, x_inner[::-1], [x_outer[0]]])
            y_coords = np.concatenate([y_outer, y_inner[::-1], [y_outer[0]]])
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            # Hover text for the interval segment
            hover_text = f"Interval: {interval_ratio}"
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            # Add interval label inside the segment
            if show_labels:
                mid_angle = current_angle - angle_span / 2
                label_radius = 0.925
                label_x = label_radius * math.cos(mid_angle)
                label_y = label_radius * math.sin(mid_angle)
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[f"{interval_ratio}"],
                    textfont=dict(color='black', size=text_size+2, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_angle -= angle_span
        
        fig.update_layout(
            xaxis=dict(
                range=[-1.2, 1.2],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-1.2, 1.2], 
                scaleanchor="x", 
                scaleratio=1,
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    else:  # line layout
        current_pos = 0
        # Color based on distance from unison (1/1)
        colors = []
        for i in range(n_segments):
            if i < len(calc_degrees):
                # Distance from unison in log space
                distance = abs(math.log(float(calc_degrees[i])))
                hue = min(distance / 2.0, 1.0)  # Normalize and cap at 1.0
            else:
                # Final interval - use distance based on equave
                distance = abs(math.log(float(calc_obj._equave)))
                hue = min(distance / 2.0, 1.0)
            colors.append(plt.cm.hsv(hue))
        y_center = 0
        bar_height = 0.3
        
        # Add degree labels at borders
        if show_labels:
            for i, calc_degree in enumerate(calc_degrees):
                degree_pos = current_pos
                for j in range(i):
                    degree_pos += (intervals[j] / total_log_size) * 2.0
                
                fig.add_trace(go.Scatter(
                    x=[degree_pos], y=[y_center + bar_height/2 + 0.1],
                    mode='text',
                    text=[f"{calc_degree}"],
                    textfont=dict(color='white', size=text_size+2, family='Arial'),
                    showlegend=False,
                    hovertemplate=f'Node {i}<br>Degree: {calc_degree}<extra></extra>',
                    hoverlabel=dict(bgcolor='lightgrey', font_color='black')
                ))
            
            # Add equave label at the end
            fig.add_trace(go.Scatter(
                x=[2.0], y=[y_center + bar_height/2 + 0.1],
                mode='text',
                text=["1/1"],
                textfont=dict(color='white', size=text_size+2, family='Arial'),
                showlegend=False,
                hovertemplate=f'Node 0<br>Degree: 1/1<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
        
        # Draw interval segments
        for i, (interval_size, interval_ratio) in enumerate(zip(intervals, interval_ratios)):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            segment_width = proportion * 2.0
            
            x_coords = [current_pos, current_pos + segment_width, current_pos + segment_width, current_pos, current_pos]
            y_coords = [y_center - bar_height/2, y_center - bar_height/2, y_center + bar_height/2, y_center + bar_height/2, y_center - bar_height/2]
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            # Hover text for the interval segment
            hover_text = f"Interval: {interval_ratio}"
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            # Add interval label inside the segment
            if show_labels:
                label_x = current_pos + segment_width / 2
                label_y = y_center
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[f"{interval_ratio}"],
                    textfont=dict(color='black', size=text_size+2, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_pos += segment_width
        
        fig.update_layout(
            xaxis=dict(
                range=[-0.1, 2.1],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-0.5, 0.5],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    if title is None:
        title = repr(obj)
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0),
    )
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig
def _plot_ratio_scale_chord_clean(obj, calc_obj, degrees, calc_degrees, fig, figsize,
                                 text_size, show_labels, title, output_file, layout):
    """Plot ratio-based scales/chords as proportional segments."""
    n_degrees = len(degrees)
    
    if n_degrees < 2:
        raise ValueError("Need at least 2 degrees to plot intervals")
    
    # Use the intervals property (Scale now includes final interval)
    interval_ratios = calc_obj.intervals
    
    # Convert interval ratios to log sizes for proportional display
    intervals = [math.log(float(ratio)) for ratio in interval_ratios]
    n_segments = len(interval_ratios)
    total_log_size = sum(intervals)
    
    # Generate distinct colors for each segment
    colors = plt.cm.Set1(np.linspace(0, 1, n_segments))
    
    if layout == 'circle':
        current_angle = math.pi / 2
        
        # Add degree labels at borders first
        if show_labels:
            for i, calc_degree in enumerate(calc_degrees):
                degree_angle = current_angle
                for j in range(i):
                    degree_angle -= 2 * math.pi * (intervals[j] / total_log_size)
                
                degree_radius = 1.1
                degree_x = degree_radius * math.cos(degree_angle)
                degree_y = degree_radius * math.sin(degree_angle)
                
                fig.add_trace(go.Scatter(
                    x=[degree_x], y=[degree_y],
                    mode='text',
                    text=[f"{calc_degree}"],
                    textfont=dict(color='white', size=text_size+2, family='Arial'),
                    showlegend=False,
                    hovertemplate=f'Node {i}<br>Degree: {calc_degree}<extra></extra>',
                    hoverlabel=dict(bgcolor='lightgrey', font_color='black')
                ))
            
            # Add equave label at the end
            equave_x = 1.1 * math.cos(math.pi / 2)
            equave_y = 1.1 * math.sin(math.pi / 2)
            fig.add_trace(go.Scatter(
                x=[equave_x], y=[equave_y],
                mode='text',
                text=["1/1"],
                textfont=dict(color='white', size=text_size+2, family='Arial'),
                showlegend=False,
                hovertemplate=f'Node 0<br>Degree: 1/1<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
        
        # Draw interval segments
        for i, (interval_size, interval_ratio) in enumerate(zip(intervals, interval_ratios)):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            angle_span = 2 * math.pi * proportion
            
            num_points = max(50, int(angle_span * 50))
            angles = np.linspace(current_angle, current_angle - angle_span, num_points)
            
            inner_radius = 0.85
            outer_radius = 1.0
            
            x_outer = outer_radius * np.cos(angles)
            y_outer = outer_radius * np.sin(angles)
            x_inner = inner_radius * np.cos(angles)
            y_inner = inner_radius * np.sin(angles)
            
            x_coords = np.concatenate([x_outer, x_inner[::-1], [x_outer[0]]])
            y_coords = np.concatenate([y_outer, y_inner[::-1], [y_outer[0]]])
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            # Hover text for the interval segment
            hover_text = f"Interval: {interval_ratio}"
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            # Add interval label inside the segment
            if show_labels:
                mid_angle = current_angle - angle_span / 2
                label_radius = 0.925
                label_x = label_radius * math.cos(mid_angle)
                label_y = label_radius * math.sin(mid_angle)
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[f"{interval_ratio}"],
                    textfont=dict(color='black', size=text_size+2, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_angle -= angle_span
        
        fig.update_layout(
            xaxis=dict(
                range=[-1.2, 1.2],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-1.2, 1.2], 
                scaleanchor="x", 
                scaleratio=1,
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    else:  # line layout
        # Use better dimensions for line layout
        figsize = (20, 1.5)
        current_pos = 0
        y_center = 0
        bar_height = 0.2
        
        # Add degree labels at borders
        if show_labels:
            # First degree (1/1)
            fig.add_trace(go.Scatter(
                x=[0], y=[y_center + bar_height/2 + 0.05],
                mode='text',
                text=["1/1"],
                textfont=dict(color='white', size=text_size+2, family='Arial'),
                showlegend=False,
                hovertemplate=f'Node 0<br>Degree: 1/1<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            # Other degrees
            for i, calc_degree in enumerate(calc_degrees[1:], 1):
                degree_pos = 0
                for j in range(i):
                    degree_pos += (intervals[j] / total_log_size) * 2.0
                
                fig.add_trace(go.Scatter(
                    x=[degree_pos], y=[y_center + bar_height/2 + 0.05],
                    mode='text',
                    text=[f"{calc_degree}"],
                    textfont=dict(color='white', size=text_size+2, family='Arial'),
                    showlegend=False,
                    hovertemplate=f'Node {i}<br>Degree: {calc_degree}<extra></extra>',
                    hoverlabel=dict(bgcolor='lightgrey', font_color='black')
                ))
            
            # Add equave label at the end
            fig.add_trace(go.Scatter(
                x=[2.0], y=[y_center + bar_height/2 + 0.05],
                mode='text',
                text=[f"{calc_obj._equave}"],
                textfont=dict(color='white', size=text_size+2, family='Arial'),
                showlegend=False,
                hovertemplate=f'Node {len(calc_degrees)}<br>Degree: {calc_obj._equave}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
        
        # Draw interval segments
        for i, (interval_size, interval_ratio) in enumerate(zip(intervals, interval_ratios)):
            if interval_size <= 0:
                continue
                
            proportion = interval_size / total_log_size
            segment_width = proportion * 2.0
            
            x_coords = [current_pos, current_pos + segment_width, current_pos + segment_width, current_pos, current_pos]
            y_coords = [y_center - bar_height/2, y_center - bar_height/2, y_center + bar_height/2, y_center + bar_height/2, y_center - bar_height/2]
            
            color = colors[i]
            color_hex = '#%02x%02x%02x' % (int(color[0]*255), int(color[1]*255), int(color[2]*255))
            
            # Hover text for the interval segment
            hover_text = f"Interval: {interval_ratio}"
            
            fig.add_trace(go.Scatter(
                x=x_coords, y=y_coords,
                fill='toself',
                fillcolor=color_hex,
                line=dict(color='white', width=1),
                mode='lines+markers',
                marker=dict(size=0.1, opacity=0),
                showlegend=False,
                hovertemplate=f'{hover_text}<extra></extra>',
                hoverlabel=dict(bgcolor='lightgrey', font_color='black')
            ))
            
            # Add interval label inside the segment
            if show_labels:
                label_x = current_pos + segment_width / 2
                label_y = y_center
                
                fig.add_trace(go.Scatter(
                    x=[label_x], y=[label_y],
                    mode='text',
                    text=[f"{interval_ratio}"],
                    textfont=dict(color='black', size=text_size+2, family='Arial', weight='bold'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            current_pos += segment_width
        
        fig.update_layout(
            xaxis=dict(
                range=[-0.05, 2.05],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            ),
            yaxis=dict(
                range=[-0.2, 0.2],
                showgrid=False, 
                zeroline=False, 
                showticklabels=False
            )
        )
    
    if title is None:
        title = repr(obj)
    
    width_px, height_px = int(figsize[0] * 72), int(figsize[1] * 72)
    
    fig.update_layout(
        title=dict(text=title, font=dict(color='white')),
        width=width_px,
        height=height_px,
        paper_bgcolor='black',
        plot_bgcolor='black',
        hovermode='closest',
        margin=dict(l=0, r=0, t=50, b=0),
    )
    
    if output_file:
        if output_file.endswith('.html'):
            fig.write_html(output_file)
        else:
            fig.write_image(output_file)
    
    return fig
