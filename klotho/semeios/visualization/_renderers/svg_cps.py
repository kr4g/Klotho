import math
import numpy as np
from collections import defaultdict
from html import escape as html_escape

from .._shared.colors import SHAPE_COLORS, _path_color_array, _rgba_to_hex
from .._shared.svg_utils import (
    SvgFigureData, svg_wrap, svg_radial_halo, svg_arrow_polygon,
    svg_glow_edge, svg_path_edge, compute_quadratic_bezier_midpoint,
)
from .._shared.svg_shared import compute_svg_layout, render_shape_groups, render_tooltip_system, BASE_ARC_OFFSET


class SvgCPSData(SvgFigureData):
    """Container for CPS SVG rendering data and animation metadata."""

    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_group_ids', 'halo_ids', 'all_path_ids',
                 'all_node_ids', 'path_node_indices', 'path_node_colors',
                 'dimmed_node_color',
                 'shape_group_node_indices', 'shape_group_edge_ids',
                 'shape_colors', 'all_shape_edge_ids')


def _svg_cps(cps, node_positions, path=None, path_cmap='viridis',
             mute_background=False, figsize=(12, 12),
             node_size=30, text_size=12, show_labels=True, title=None,
             shape=None, preview_config=None):
    """
    Build a 2D SVG representation of a Combination Product Set.

    Generates an inline SVG string with nodes, edges, optional path
    overlays, and optional shape (chord) overlays, bundled into an
    `SvgCPSData` container for display or animation.

    Parameters
    ----------
    cps : CombinationProductSet
        The CPS to render.
    node_positions : dict
        Mapping of node IDs to 2D ``(x, y)`` positions.
    path : list or None, optional
        Node IDs defining a traversal path.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes when a path or shape is active.
    figsize : tuple of float, optional
        Width and height in inches (converted to pixels at 100 dpi).
    node_size : int, optional
        Diameter of the rendered nodes.
    text_size : int, optional
        Font size for node labels.
    show_labels : bool, optional
        Whether to draw alias labels inside nodes.
    title : str or None, optional
        Title string rendered above the diagram.
    shape : list or None, optional
        Node IDs (chord) or list of lists (chord sequence) to
        highlight with coloured edges.

    Returns
    -------
    SvgCPSData
        SVG string and associated animation metadata.
    """
    import uuid as _uuid

    G = cps.graph

    dimmed_edge_color = '#333333'
    dimmed_node_color = '#555555'

    layout = compute_svg_layout(node_positions, figsize)
    width_px = layout['width_px']
    height_px = layout['height_px']
    tx = layout['tx']
    ty = layout['ty']
    margin_top = layout['oy']

    uid = f"svgcps_{_uuid.uuid4().hex[:8]}"
    els = []
    eid_counter = [0]

    def next_eid(prefix="c"):
        eid_counter[0] += 1
        return f"{uid}_{prefix}{eid_counter[0]}"

    els.append(f'<rect width="{width_px}" height="{height_px}" fill="black"/>')

    if title is None:
        cps_type = type(cps).__name__
        factor_string = ' '.join(str(cps.factor_to_alias[f]) for f in cps.factors)
        title = f"{cps_type} [{factor_string}]"

    if title:
        els.append(
            f'<text x="{width_px / 2:.1f}" y="{margin_top / 2:.1f}" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'font-family="Arial" font-size="14" fill="white">'
            f'{html_escape(title)}</text>'
        )

    has_path = path and len(path) >= 2

    if shape is not None and len(shape) > 0 and isinstance(shape[0], (list, tuple)):
        shape_groups = [list(g) for g in shape]
        is_multi_shape = True
    elif shape is not None and len(shape) > 0:
        shape_groups = [list(shape)]
        is_multi_shape = False
    else:
        shape_groups = []
        is_multi_shape = False

    has_shape = len(shape_groups) > 0
    all_shape_nodes = set()
    for g in shape_groups:
        all_shape_nodes.update(g)

    dim_bg = mute_background and (has_path or has_shape)
    path_nodes = set(path) if path else set()

    edge_color = dimmed_edge_color if dim_bg else '#808080'
    for u, v, data in G.edges(data=True):
        if u in node_positions and v in node_positions:
            px1, py1 = tx(node_positions[u][0]), ty(node_positions[u][1])
            px2, py2 = tx(node_positions[v][0]), ty(node_positions[v][1])
            els.append(
                f'<line x1="{px1:.2f}" y1="{py1:.2f}" x2="{px2:.2f}" y2="{py2:.2f}" '
                f'stroke="{edge_color}" stroke-width="1"/>'
            )

    path_els = []
    step_group_ids = []
    halo_ids = []
    all_path_el_ids = []
    colors = None
    base_arc_offset = 0.15

    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)
        edge_counts = defaultdict(int)

        for i in range(len(path) - 1):
            n1, n2 = path[i], path[i + 1]
            if n1 not in node_positions or n2 not in node_positions:
                step_group_ids.append([])
                continue

            x1, y1 = node_positions[n1]
            x2, y2 = node_positions[n2]
            px1, py1 = tx(x1), ty(y1)
            px2, py2 = tx(x2), ty(y2)

            path_color_hex = _rgba_to_hex(colors[i])

            edge_key = tuple(sorted([n1, n2]))
            traversal_idx = edge_counts[edge_key]
            edge_counts[edge_key] += 1
            is_forward = n1 < n2

            if traversal_idx == 0:
                svg_d = f"M{px1:.2f},{py1:.2f} L{px2:.2f},{py2:.2f}"
                mid_px = (px1 + px2) / 2
                mid_py = (py1 + py2) / 2
                arrow_angle = math.degrees(math.atan2(py2 - py1, px2 - px1))
            else:
                dx, dy = x2 - x1, y2 - y1
                length = math.sqrt(dx*dx + dy*dy)
                if length < 1e-9:
                    step_group_ids.append([])
                    continue
                perp_x, perp_y = -dy / length, dx / length

                side = 1 if is_forward else -1
                offset_mag = base_arc_offset * max(1, (traversal_idx + 1) // 2)
                if traversal_idx % 2 == 0:
                    side = -side

                ctrl_x = (x1 + x2) / 2 + side * perp_x * offset_mag
                ctrl_y = (y1 + y2) / 2 + side * perp_y * offset_mag
                cpx, cpy = tx(ctrl_x), ty(ctrl_y)
                svg_d = f"M{px1:.2f},{py1:.2f} Q{cpx:.2f},{cpy:.2f} {px2:.2f},{py2:.2f}"

                mid_px, mid_py, arrow_angle = compute_quadratic_bezier_midpoint(
                    px1, py1, cpx, cpy, px2, py2)

            glow_id = next_eid("pg")
            edge_id = next_eid("pe")
            arrow_id = next_eid("pa")

            path_els.append(svg_glow_edge(glow_id, svg_d))
            path_els.append(svg_path_edge(edge_id, svg_d, path_color_hex))
            path_els.append(svg_arrow_polygon(arrow_id, mid_px, mid_py, arrow_angle, path_color_hex))

            group = [glow_id, edge_id, arrow_id]
            step_group_ids.append(group)
            all_path_el_ids.extend(group)

        start_hex = _rgba_to_hex(colors[0])
        end_hex = _rgba_to_hex(colors[-1])
        sx, sy = tx(node_positions[path[0]][0]), ty(node_positions[path[0]][1])
        ex, ey = tx(node_positions[path[-1]][0]), ty(node_positions[path[-1]][1])

        sg_id = next_eid("rg")
        eg_id = next_eid("rg")
        start_halo_id = next_eid("hs")
        end_halo_id = next_eid("he")

        s_defs, s_circle = svg_radial_halo(sg_id, start_halo_id, sx, sy, 20, start_hex)
        e_defs, e_circle = svg_radial_halo(eg_id, end_halo_id, ex, ey, 20, end_hex)
        path_els.append(s_defs)
        path_els.append(s_circle)
        path_els.append(e_defs)
        path_els.append(e_circle)
        halo_ids = [start_halo_id, end_halo_id]
        all_path_el_ids.extend(halo_ids)

    path_node_colors_map = {}
    if has_path:
        for k in range(len(path)):
            n = path[k]
            if k == 0:
                path_node_colors_map[n] = _rgba_to_hex(colors[0])
            else:
                path_node_colors_map[n] = _rgba_to_hex(colors[k - 1])

    shape_els = []
    svg_shape_group_edge_ids = []
    all_shape_el_ids = []
    shape_node_colors_map = {}
    used_shape_colors = []

    if has_shape:
        graph_edges = set()
        for u, v, _ in G.edges(data=True):
            graph_edges.add((u, v))
            graph_edges.add((v, u))

        def _cps_edge_exists(n1, n2):
            return (n1, n2) in graph_edges

        def _cps_shape_pos(n):
            if n not in node_positions:
                return None
            return tx(node_positions[n][0]), ty(node_positions[n][1])

        shape_els, svg_shape_group_edge_ids, all_shape_el_ids, used_shape_colors, shape_node_colors_map = (
            render_shape_groups(shape_groups, _cps_edge_exists, _cps_shape_pos, next_eid)
        )

    node_els = []
    all_node_ids = []
    node_id_map = {}
    hover_texts = []
    is_active_list = []
    node_freqs = []
    ref_freq = 261.63
    ns = node_size
    node_idx_counter = 0

    for node, attrs in G.nodes(data=True):
        if node not in node_positions or 'combo' not in attrs:
            continue

        x, y = node_positions[node]
        cx_px, cy_px = tx(x), ty(y)

        combo = attrs['combo']
        label = ''.join(str(cps.factor_to_alias[f]).strip('()') for f in combo)
        combo_str = '(' + ' '.join(str(f) for f in combo) + ')'
        product = attrs['product']
        ratio = attrs['ratio']
        hover_text = f"Node: {node}  Alias: {label}\nCombo: {combo_str}  Product: {product}\nRatio: {ratio}"

        if has_path:
            nc = path_node_colors_map.get(node, dimmed_node_color)
            active = node in path_nodes
        elif has_shape:
            nc = shape_node_colors_map.get(node, dimmed_node_color if dim_bg else 'white')
            active = node in all_shape_nodes
        else:
            nc = 'white'
            active = True

        nid = next_eid("nd")
        all_node_ids.append(nid)
        node_id_map[node] = nid
        hover_texts.append(hover_text)
        is_active_list.append(active)
        try:
            node_freqs.append(ref_freq * float(ratio))
        except (TypeError, ValueError):
            node_freqs.append(ref_freq)

        node_els.append(
            f'<circle id="{nid}" cx="{cx_px:.2f}" cy="{cy_px:.2f}" r="{ns / 2:.1f}" '
            f'fill="{nc}" stroke="white" stroke-width="2" '
            f'data-idx="{node_idx_counter}" data-tip-uid="{uid}"/>'
        )
        node_idx_counter += 1

        if show_labels:
            node_els.append(
                f'<text x="{cx_px:.2f}" y="{cy_px:.2f}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'font-family="Arial Black" font-size="{text_size}" '
                f'font-weight="bold" fill="black" pointer-events="none">'
                f'{html_escape(label)}</text>'
            )

    path_node_indices = []
    path_node_colors = []
    if has_path:
        for k, n in enumerate(path):
            nid = node_id_map.get(n, '')
            idx = all_node_ids.index(nid) if nid in all_node_ids else -1
            path_node_indices.append(idx)
            if k == 0:
                path_node_colors.append(_rgba_to_hex(colors[0]))
            else:
                path_node_colors.append(_rgba_to_hex(colors[k - 1]))

    svg_shape_group_node_indices = []
    if has_shape:
        for group in shape_groups:
            indices = []
            for n in group:
                nid = node_id_map.get(n, '')
                idx = all_node_ids.index(nid) if nid in all_node_ids else -1
                indices.append(idx)
            svg_shape_group_node_indices.append(indices)

    all_svg = '\n'.join(els + path_els + shape_els + node_els)
    has_selection = has_path or has_shape
    tooltip_html = render_tooltip_system(uid, hover_texts,
                                         is_active=is_active_list if has_selection else None,
                                         node_freqs=node_freqs if has_selection else None,
                                         preview_config=preview_config)
    svg_str = svg_wrap(all_svg, width_px, height_px) + tooltip_html

    return SvgCPSData(
        svg_str=svg_str,
        width_px=width_px,
        height_px=height_px,
        step_group_ids=step_group_ids,
        halo_ids=halo_ids,
        all_path_ids=all_path_el_ids,
        all_node_ids=all_node_ids,
        path_node_indices=path_node_indices,
        path_node_colors=path_node_colors,
        dimmed_node_color=dimmed_node_color,
        shape_group_node_indices=svg_shape_group_node_indices,
        shape_group_edge_ids=svg_shape_group_edge_ids,
        shape_colors=used_shape_colors,
        all_shape_edge_ids=all_shape_el_ids,
    )
