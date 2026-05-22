import math

import matplotlib.pyplot as plt
import networkx as nx

from klotho.topos.collections.sequences import Pattern
from klotho.topos.collections._pattern import pattern_to_graph

COLOR_SPOKE = '#00e5ff'
COLOR_WRAP = '#ffb300'
COLOR_RING = '#ce93d8'
COLOR_DELEGATE = '#bbbbbb'
COLOR_TREE_SLOT = '#ffffff'


def _structural_depths(graph, root):
    depths = {root: 0}
    stack = [(root, 0)]
    while stack:
        node_id, depth = stack.pop()
        node = graph.nodes[node_id]
        if node.get('kind') != 'structural':
            continue
        for child_id in node.get('child_ids') or []:
            anchor = _slot_anchor(graph, child_id)
            child_depth = depth + 1
            if graph.nodes[anchor].get('kind') == 'structural':
                if anchor not in depths or depths[anchor] > child_depth:
                    depths[anchor] = child_depth
                stack.append((anchor, child_depth))
    return depths


def _depth_palette(base_colors, depth):
    return base_colors[depth % len(base_colors)]


SPOKE_PALETTE = ('#00e5ff', '#40c4ff', '#18ffff')
WRAP_PALETTE = ('#ffb300', '#ff9100', '#ffd54f')
RING_PALETTE = ('#e040fb', '#ce93d8', '#9575cd')


def _add_cycle_legend(ax, layout):
    if layout != 'cycle':
        return
    from matplotlib.lines import Line2D

    handles = [
        Line2D([0], [0], color=COLOR_SPOKE, lw=2.5, linestyle='--', label='slot spoke (hub → branch)'),
        Line2D([0], [0], color=COLOR_WRAP, lw=2.5, linestyle=':', label='cycle order (slot → slot)'),
        Line2D([0], [0], color=COLOR_RING, lw=2.5, linestyle='--', label='cycle boundary ring'),
    ]
    ax.legend(
        handles=handles,
        loc='upper right',
        framealpha=0.9,
        facecolor='#1a1a1a',
        edgecolor='#888888',
        labelcolor='#ffffff',
        fontsize=8,
        borderpad=0.4,
        handlelength=2.2,
    )


def _slot_angles(n: int) -> list[float]:
    if n <= 0:
        return []
    if n == 1:
        return [0.0]
    if n == 2:
        return [0.0, math.pi]
    return [2 * math.pi * i / n - math.pi / 2 for i in range(n)]


def _delegate_subgraph_root(graph, node_id):
    for _, sub_id, data in graph.out_edges(node_id, data=True):
        if data.get('edge_kind') == 'delegate':
            return sub_id
    return None


def _slot_anchor(graph, node_id):
    node = graph.nodes[node_id]
    if node.get('hidden'):
        sub_id = _delegate_subgraph_root(graph, node_id)
        if sub_id is not None:
            return _slot_anchor(graph, sub_id)
    return node_id


def _structural_anchors(graph, node_id):
    child_ids = graph.nodes[node_id].get('child_ids') or []
    return [_slot_anchor(graph, cid) for cid in child_ids]


def _mark_hidden_shells(graph, expand_delegates: bool):
    if not expand_delegates:
        return
    for node_id, node in graph.nodes(data=True):
        if node.get('kind') == 'delegate_pattern' and _delegate_subgraph_root(graph, node_id) is not None:
            node['hidden'] = True


def _pattern_tree_positions(graph, root, x=0.0, y=0.0, x_offset=2.5, depth=0):
    positions = {root: (x, y)}
    node = graph.nodes[root]
    kind = node.get('kind')

    if kind == 'structural':
        child_ids = node.get('child_ids') or []
        if child_ids:
            width = x_offset * len(child_ids)
            start_x = x - width / 2 + x_offset / 2
            child_y = y - 2.8
            for idx, child_id in enumerate(child_ids):
                child_x = start_x + idx * x_offset
                positions.update(
                    _pattern_tree_positions(graph, child_id, child_x, child_y, x_offset * 0.82, depth + 1)
                )
        return positions

    if kind == 'delegate_pattern':
        sub_id = _delegate_subgraph_root(graph, root)
        if sub_id is not None:
            positions.update(
                _pattern_tree_positions(graph, sub_id, x, y - 2.8, x_offset * 0.82, depth + 1)
            )
        return positions

    return positions


def _pattern_cycle_positions(graph, root, center=(0.0, 0.0), radius=2.2, depth=0):
    positions = {root: center}
    node = graph.nodes[root]
    kind = node.get('kind')

    if kind == 'structural':
        child_ids = node.get('child_ids') or []
        if not child_ids:
            return positions
        child_radius = max(radius * 0.88, 1.35)
        for idx, child_id in enumerate(child_ids):
            angle = _slot_angles(len(child_ids))[idx]
            cx = center[0] + child_radius * math.cos(angle)
            cy = center[1] + child_radius * math.sin(angle)
            positions.update(
                _pattern_cycle_positions(graph, child_id, (cx, cy), radius * 0.72, depth + 1)
            )
        return positions

    if kind == 'delegate_pattern':
        sub_id = _delegate_subgraph_root(graph, root)
        if sub_id is not None:
            positions.update(
                _pattern_cycle_positions(graph, sub_id, center, radius * 0.72, depth + 1)
            )
        return positions

    return positions


def _visible_nodes(graph):
    return [node_id for node_id, node in graph.nodes(data=True) if not node.get('hidden')]


def _axis_limits(graph, positions, visible, layout):
    xs = [positions[nid][0] for nid in visible if nid in positions]
    ys = [positions[nid][1] for nid in visible if nid in positions]
    if not xs:
        return -4, 4, -4, 4

    if layout == 'cycle':
        for node_id in visible:
            node = graph.nodes[node_id]
            if node.get('kind') != 'structural':
                continue
            anchors = _structural_anchors(graph, node_id)
            if len(anchors) < 2:
                continue
            pts = [positions[aid] for aid in anchors if aid in positions]
            if len(pts) < 2:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            ring_r = max(math.hypot(p[0] - cx, p[1] - cy) for p in pts) * 1.04
            xs.extend((cx - ring_r, cx + ring_r))
            ys.extend((cy - ring_r, cy + ring_r))

    xspan = max(xs) - min(xs)
    yspan = max(ys) - min(ys)
    xpad = max(0.2, xspan * 0.025 + 0.12)
    ypad = max(0.25, yspan * 0.03 + 0.15)
    return min(xs) - xpad, max(xs) + xpad, min(ys) - ypad, max(ys) + ypad


def _figsize_for_bounds(xmin, xmax, ymin, ymax, layout, default=(12, 7)):
    xspan = xmax - xmin
    yspan = ymax - ymin
    if xspan <= 0 or yspan <= 0:
        return default
    if layout == 'cycle':
        scale = 1.45
        height = max(4.5, min(9.0, yspan * scale + 0.5))
        width = max(5.5, min(14.0, xspan * scale + 0.5))
        data_aspect = xspan / yspan
        fig_aspect = width / height
        if fig_aspect > data_aspect * 1.05:
            width = height * data_aspect
        elif fig_aspect < data_aspect * 0.95:
            height = width / data_aspect
        return (width, height)
    width = max(8, min(18, xspan * 1.1 + 1.0))
    height = max(5, min(12, yspan * 1.1 + 1.0))
    return (width, height)


def _node_style(kind: str) -> tuple[str, str, str]:
    match kind:
        case 'leaf':
            return 'circle,pad=0.35', '#1f4d2e', '#88ffaa'
        case 'structural':
            return 'square,pad=0.45', '#2a2a5a', '#aaaaff'
        case 'delegate_pattern':
            return 'round4,pad=0.45', '#5a2020', '#ff9999'
        case 'delegate_cyclic':
            return 'round4,pad=0.45', '#5a4020', '#ffdd77'
        case _:
            return 'round,pad=0.3', '#333333', '#ffffff'


def _draw_pattern_graph(
    graph,
    positions,
    *,
    figsize,
    output_file,
    title=None,
    layout='tree',
    expand_delegates=True,
):
    visible = set(_visible_nodes(graph))

    fig, ax = plt.subplots(figsize=figsize)
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')

    for u, v, data in graph.edges(data=True):
        if u not in visible or v not in visible:
            continue
        edge_kind = data.get('edge_kind')
        if layout == 'cycle' and edge_kind == 'slot' and graph.nodes[u].get('kind') == 'structural':
            continue
        if edge_kind == 'delegate' and graph.nodes[u].get('hidden'):
            continue
        x0, y0 = positions[u]
        x1, y1 = positions[v]
        color = COLOR_DELEGATE if edge_kind == 'delegate' else COLOR_TREE_SLOT
        style = 'dashed' if edge_kind == 'delegate' else 'solid'
        ax.annotate(
            '',
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(arrowstyle='->', color=color, linestyle=style, lw=1.8),
            zorder=1,
        )
        if edge_kind == 'slot' and 'slot' in data and layout == 'tree':
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            ax.text(
                mx,
                my + 0.15,
                str(data['slot']),
                color='#ffffff',
                fontsize=9,
                ha='center',
                va='bottom',
                zorder=6,
                bbox=dict(boxstyle='round,pad=0.15', fc='#111111', ec='none', alpha=0.85),
            )

    draw_order = sorted(
        visible,
        key=lambda nid: {
            'structural': 0,
            'delegate_pattern': 1,
            'delegate_cyclic': 1,
            'leaf': 2,
        }.get(graph.nodes[nid].get('kind', ''), 1),
    )

    for node_id in draw_order:
        x, y = positions[node_id]
        node = graph.nodes[node_id]
        boxstyle, fc, ec = _node_style(node.get('kind', ''))
        fontsize = 10 if node.get('kind') == 'structural' else 11
        ax.text(
            x,
            y,
            node.get('label', str(node_id)),
            ha='center',
            va='center',
            fontsize=fontsize,
            color='white',
            bbox=dict(boxstyle=boxstyle, fc=fc, ec=ec, lw=2.0),
            zorder=4 if node.get('kind') == 'structural' else 6,
        )

    if layout == 'cycle':
        root = graph.graph.get('root')
        depths = _structural_depths(graph, root) if root is not None else {}
        for node_id, node in graph.nodes(data=True):
            if node_id not in visible or node.get('kind') != 'structural':
                continue
            anchors = [aid for aid in _structural_anchors(graph, node_id) if aid in visible]
            hub_x, hub_y = positions[node_id]
            depth = depths.get(node_id, 0)
            spoke_color = _depth_palette(SPOKE_PALETTE, depth)
            wrap_color = _depth_palette(WRAP_PALETTE, depth)
            ring_color = _depth_palette(RING_PALETTE, depth)

            for idx, anchor_id in enumerate(anchors):
                ax_x, ax_y = positions[anchor_id]
                ax.annotate(
                    '',
                    xy=(ax_x, ax_y),
                    xytext=(hub_x, hub_y),
                    arrowprops=dict(
                        arrowstyle='->',
                        color=spoke_color,
                        linestyle='dashed',
                        lw=2.2,
                    ),
                    zorder=2,
                )
                mx, my = (hub_x + ax_x) / 2, (hub_y + ax_y) / 2
                ax.text(
                    mx,
                    my,
                    str(idx),
                    color='#ffffff',
                    fontsize=8,
                    ha='center',
                    va='center',
                    zorder=7,
                    bbox=dict(boxstyle='round,pad=0.12', fc='#111122', ec=spoke_color, lw=1.0),
                )

            if len(anchors) < 2:
                continue
            pts = [positions[aid] for aid in anchors]
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            ring_r = max(math.hypot(p[0] - cx, p[1] - cy) for p in pts) * 1.05
            ring = plt.Circle((cx, cy), ring_r, fill=False, linestyle='--', color=ring_color, lw=2.2, zorder=2)
            ax.add_patch(ring)
            for idx in range(len(anchors)):
                c0 = anchors[idx]
                c1 = anchors[(idx + 1) % len(anchors)]
                x0, y0 = positions[c0]
                x1, y1 = positions[c1]
                ax.annotate(
                    '',
                    xy=(x1, y1),
                    xytext=(x0, y0),
                    arrowprops=dict(
                        arrowstyle='->',
                        color=wrap_color,
                        linestyle='dotted',
                        lw=2.4,
                        connectionstyle='arc3,rad=0.25',
                    ),
                    zorder=2,
                )

        _add_cycle_legend(ax, layout)

    period = graph.graph.get('period_sequence', [])
    length = graph.graph.get('pattern_length', len(period))
    period_text = ' → '.join(repr(v) for v in period[: min(len(period), 16)])
    if len(period) > 16:
        period_text += ' → …'
    caption = f'period (len={length}): {period_text}'
    if title:
        caption = f'{title}\n{caption}'
    ax.text(
        0.5,
        0.01,
        caption,
        transform=ax.transAxes,
        ha='center',
        va='bottom',
        color='#eeeeee',
        fontsize=9,
        wrap=True,
        clip_on=False,
        zorder=8,
    )

    xmin, xmax, ymin, ymax = _axis_limits(graph, positions, visible, layout)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    if layout == 'cycle':
        ax.set_aspect('equal', adjustable='box')
    else:
        ax.set_aspect('auto')
    ax.axis('off')
    ax.margins(0)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.07)

    if output_file:
        fig.savefig(output_file, bbox_inches='tight', facecolor='black', pad_inches=0.06)
        plt.close(fig)
    return fig


def plot_pattern(
    pattern: Pattern,
    *,
    layout: str = 'tree',
    figsize=None,
    expand_delegates: bool = True,
    output_file: str | None = None,
):
    """Visualize a :class:`Pattern` structure.

    Parameters
    ----------
    pattern : Pattern
        Pattern to visualize.
    layout : {'tree', 'cycle'}, optional
        ``'tree'`` draws nested structural containers top-down.
        ``'cycle'`` arranges each structural group's slots on a ring.
    figsize : tuple of float or None, optional
        Figure size in inches.  When ``None``, size is inferred from layout.
    expand_delegates : bool, optional
        When ``True``, nested ``Pattern`` delegates are expanded inline.
    output_file : str or None, optional
        Save path; when ``None`` the figure is returned for display.
    """
    if layout not in {'tree', 'cycle'}:
        raise ValueError("layout must be 'tree' or 'cycle'")

    graph = pattern_to_graph(pattern, expand_delegates=expand_delegates)
    _mark_hidden_shells(graph, expand_delegates)
    root = graph.graph['root']
    if layout == 'tree':
        positions = _pattern_tree_positions(graph, root, x_offset=2.8)
    else:
        positions = _pattern_cycle_positions(graph, root, center=(0.0, 0.0), radius=2.2)

    for node_id in graph.nodes:
        if node_id not in positions:
            positions[node_id] = (0.0, 0.0)

    visible = _visible_nodes(graph)
    if figsize is None:
        limits = _axis_limits(graph, positions, visible, layout)
        figsize = _figsize_for_bounds(*limits, layout)

    return _draw_pattern_graph(
        graph,
        positions,
        figsize=figsize,
        output_file=output_file,
        title=f'Pattern layout={layout}',
        layout=layout,
        expand_delegates=expand_delegates,
    )
