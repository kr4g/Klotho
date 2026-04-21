import math
from collections import defaultdict
from html import escape as html_escape

from .._shared.colors import SHAPE_COLORS, _path_color_array, _rgba_to_hex
from .._shared.svg_utils import (
    SvgFigureData, svg_wrap, svg_radial_halo, svg_arrow_polygon,
    svg_glow_edge, svg_path_edge, compute_quadratic_bezier_midpoint,
)
from .._shared.svg_shared import render_tooltip_system


class SvgMasterSetData(SvgFigureData):
    """Container for 2D MasterSet SVG rendering data and animation metadata."""

    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_group_ids', 'halo_ids', 'all_path_ids',
                 'all_node_ids', 'path_node_indices', 'path_node_colors',
                 'dimmed_node_color',
                 'shape_group_node_indices', 'shape_group_edge_ids',
                 'shape_colors', 'all_shape_edge_ids')


def _svg_master_set_2d(ms, figsize=(12, 12), node_size=30, text_size=12,
                       show_labels=True, title=None,
                       nodes=None, path=None, path_cmap='viridis',
                       mute_background=False, shape=None,
                       preview_config=None):
    """
    Build a 2D SVG representation of a MasterSet.

    Mirrors the CPS renderer, supporting optional path traversal,
    chord / chord-sequence shape overlays, tooltip with click-to-play,
    and path-based dimming.

    Parameters
    ----------
    ms : MasterSet
        The master set to render.
    figsize : tuple of float, optional
        Width and height in inches.
    node_size : int, optional
        Diameter of each node circle.
    text_size : int, optional
        Font size for node labels.
    show_labels : bool, optional
        Whether to display alias labels inside nodes.
    title : str or None, optional
        Title rendered above the diagram.
    nodes : list or None, optional
        Alias labels to highlight.
    path : list or None, optional
        Alias labels defining a traversal path.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes/edges when a path or shape is active.
    shape : list or None, optional
        Alias labels (chord) or list of lists (chord sequence).
    preview_config : dict or None, optional
        Click-to-play configuration forwarded to the tooltip.

    Returns
    -------
    SvgMasterSetData
        SVG string and associated animation metadata.
    """
    positions = ms.positions
    edge_pairs = ms.edges
    nd = ms.node_data()

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    sorted_labels = sorted(positions)
    xs = [positions[l][0] for l in sorted_labels]
    ys = [positions[l][1] for l in sorted_labels]
    if not xs:
        xs, ys = [0], [0]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_span = (x_max - x_min) or 1.0
    y_span = (y_max - y_min) or 1.0
    pad_frac = 0.08

    data_l = x_min - x_span * pad_frac
    data_r = x_max + x_span * pad_frac
    data_b = y_min - y_span * pad_frac
    data_t = y_max + y_span * pad_frac
    dw = data_r - data_l
    dh = data_t - data_b

    aspect_data = dw / dh
    aspect_px = width_px / height_px
    if aspect_data > aspect_px:
        scale = width_px / dw
    else:
        scale = height_px / dh
    cx_data = (data_l + data_r) / 2
    cy_data = (data_b + data_t) / 2

    def tx(v):
        return width_px / 2 + (v - cx_data) * scale

    def ty(v):
        return height_px / 2 - (v - cy_data) * scale

    import uuid as _uuid
    uid = f"svgms_{_uuid.uuid4().hex[:8]}"
    els = []
    eid_counter = [0]

    def next_eid(prefix="m"):
        eid_counter[0] += 1
        return f"{uid}_{prefix}{eid_counter[0]}"

    dimmed_edge_color = '#333333'
    dimmed_node_color = '#555555'

    has_path = path and len(path) >= 2
    if shape is not None and len(shape) > 0 and isinstance(shape[0], (list, tuple)):
        shape_groups = [list(g) for g in shape]
    elif shape is not None and len(shape) > 0:
        shape_groups = [list(shape)]
    else:
        shape_groups = []
    has_shape = len(shape_groups) > 0
    all_shape_nodes = set()
    for g in shape_groups:
        all_shape_nodes.update(g)

    highlighted_nodes = set(nodes) if nodes else set()
    dim_bg = mute_background and (has_path or has_shape or bool(highlighted_nodes))

    els.append(f'<rect width="{width_px}" height="{height_px}" fill="black"/>')

    if title is None:
        title = f"MasterSet: {ms.name or 'unnamed'}"
    if title:
        els.append(
            f'<text x="{width_px / 2:.1f}" y="18" text-anchor="middle" '
            f'dominant-baseline="central" '
            f'font-family="Arial" font-size="14" fill="white">'
            f'{html_escape(title)}</text>'
        )

    edge_color = dimmed_edge_color if dim_bg else '#808080'
    for fr, to in edge_pairs:
        if fr in positions and to in positions:
            x1, y1 = positions[fr][0], positions[fr][1]
            x2, y2 = positions[to][0], positions[to][1]
            els.append(
                f'<line x1="{tx(x1):.2f}" y1="{ty(y1):.2f}" '
                f'x2="{tx(x2):.2f}" y2="{ty(y2):.2f}" '
                f'stroke="{edge_color}" stroke-width="1.5"/>'
            )

    path_els = []
    step_group_ids = []
    halo_ids = []
    all_path_el_ids = []
    colors = None
    base_arc_offset = 0.15 * max(dw, dh)

    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)
        edge_counts = defaultdict(int)

        for i in range(len(path) - 1):
            n1, n2 = path[i], path[i + 1]
            if n1 not in positions or n2 not in positions:
                step_group_ids.append([])
                continue

            x1, y1 = positions[n1][0], positions[n1][1]
            x2, y2 = positions[n2][0], positions[n2][1]
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
                length = math.sqrt(dx * dx + dy * dy)
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
        sx, sy = tx(positions[path[0]][0]), ty(positions[path[0]][1])
        ex, ey = tx(positions[path[-1]][0]), ty(positions[path[-1]][1])

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
    path_nodes = set(path) if path else set()

    shape_els = []
    svg_shape_group_edge_ids = []
    all_shape_el_ids = []
    shape_node_colors_map = {}
    used_shape_colors = []

    if has_shape:
        graph_edges = set()
        for fr, to in edge_pairs:
            graph_edges.add((fr, to))
            graph_edges.add((to, fr))

        for gi, group in enumerate(shape_groups):
            color = SHAPE_COLORS[gi % len(SHAPE_COLORS)]
            used_shape_colors.append(color)
            gids = []
            for n in group:
                shape_node_colors_map[n] = color
            for i, n1 in enumerate(group):
                for n2 in group[i + 1:]:
                    if (n1, n2) in graph_edges or (n2, n1) in graph_edges:
                        if n1 in positions and n2 in positions:
                            px1, py1 = tx(positions[n1][0]), ty(positions[n1][1])
                            px2, py2 = tx(positions[n2][0]), ty(positions[n2][1])
                            eid = next_eid("se")
                            shape_els.append(
                                f'<line id="{eid}" x1="{px1:.2f}" y1="{py1:.2f}" '
                                f'x2="{px2:.2f}" y2="{py2:.2f}" '
                                f'stroke="{color}" stroke-width="3" opacity="0.8" '
                                f'pointer-events="none"/>'
                            )
                            gids.append(eid)
                            all_shape_el_ids.append(eid)
            svg_shape_group_edge_ids.append(gids)

    node_els = []
    all_node_ids = []
    node_id_map = {}
    hover_texts = []
    is_active_list = []
    node_freqs = []
    ref_freq = 261.63

    r_px = node_size * 0.5
    node_idx_counter = 0
    for label in sorted_labels:
        x, y = positions[label][0], positions[label][1]
        cx, cy = tx(x), ty(y)
        info = nd.get(label, {})
        tooltip_parts = [f"Alias: {label}"]
        if 'factor' in info:
            tooltip_parts.append(f"Factor: {info['factor']}")
            tooltip_parts.append(f"Ratio: {info['ratio']}")
            try:
                node_freqs.append(ref_freq * float(info['ratio']))
            except (TypeError, ValueError):
                node_freqs.append(ref_freq)
        else:
            node_freqs.append(ref_freq)

        if has_path:
            nc = path_node_colors_map.get(label, dimmed_node_color)
            active = label in path_nodes
        elif has_shape:
            nc = shape_node_colors_map.get(label, dimmed_node_color if dim_bg else 'white')
            active = label in all_shape_nodes
        elif highlighted_nodes and label in highlighted_nodes:
            nc = 'white'
            active = True
        elif dim_bg:
            nc = dimmed_node_color
            active = False
        else:
            nc = 'white'
            active = True

        nid = next_eid("nd")
        all_node_ids.append(nid)
        node_id_map[label] = nid
        hover_texts.append('\n'.join(tooltip_parts))
        is_active_list.append(active)

        node_els.append(
            f'<circle id="{nid}" cx="{cx:.2f}" cy="{cy:.2f}" r="{r_px}" '
            f'fill="{nc}" stroke="white" stroke-width="2" '
            f'data-idx="{node_idx_counter}" data-tip-uid="{uid}"/>'
        )
        node_idx_counter += 1

        if show_labels:
            node_els.append(
                f'<text x="{cx:.2f}" y="{cy + 1:.2f}" text-anchor="middle" '
                f'dominant-baseline="central" font-family="Arial Black" '
                f'font-size="{text_size}" font-weight="bold" fill="black" '
                f'pointer-events="none">{html_escape(str(label))}</text>'
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
    has_selection = has_path or has_shape or bool(highlighted_nodes)
    tooltip_html = render_tooltip_system(
        uid, hover_texts,
        is_active=is_active_list if has_selection else None,
        node_freqs=node_freqs if preview_config else None,
        preview_config=preview_config,
    )
    svg_str = svg_wrap(all_svg, width_px, height_px) + tooltip_html

    return SvgMasterSetData(
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
