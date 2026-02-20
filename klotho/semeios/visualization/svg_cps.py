import math
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from html import escape as html_escape


def _path_color_array(cmap_name, n):
    cmap = plt.cm.get_cmap(cmap_name)
    return cmap(np.linspace(0.15, 1, n))


def _rgba_to_hex(rgba):
    return '#%02x%02x%02x' % (int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))


class SvgCPSData:
    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_group_ids', 'halo_ids', 'all_path_ids',
                 'all_node_ids', 'path_node_indices', 'path_node_colors',
                 'dimmed_node_color')

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_html(self, **kwargs):
        return self.svg_str


def _svg_cps(cps, node_positions, path=None, path_cmap='viridis',
             mute_background=False, figsize=(12, 12),
             node_size=30, text_size=12, show_labels=True, title=None):
    import uuid as _uuid

    G = cps.graph

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    dimmed_edge_color = '#333333'
    dimmed_node_color = '#555555'

    xs = [pos[0] for pos in node_positions.values()]
    ys = [pos[1] for pos in node_positions.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x_pad = 1.0
    y_pad = 1.0
    data_x_min = x_min - x_pad
    data_x_max = x_max + x_pad
    data_y_min = y_min - y_pad
    data_y_max = y_max + y_pad
    data_w = data_x_max - data_x_min
    data_h = data_y_max - data_y_min

    margin_left = 20
    margin_right = 20
    margin_top = 50
    margin_bottom = 20
    plot_w = width_px - margin_left - margin_right
    plot_h = height_px - margin_top - margin_bottom

    aspect = data_w / data_h if data_h > 0 else 1
    plot_aspect = plot_w / plot_h if plot_h > 0 else 1
    if aspect > plot_aspect:
        actual_w = plot_w
        actual_h = plot_w / aspect
    else:
        actual_h = plot_h
        actual_w = plot_h * aspect
    ox = margin_left + (plot_w - actual_w) / 2
    oy = margin_top

    def tx(val):
        return ox + (val - data_x_min) / data_w * actual_w

    def ty(val):
        return oy + actual_h - (val - data_y_min) / data_h * actual_h

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
    dim_bg = mute_background and has_path
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

                ts = np.array([0.5])
                mid_bx = (1 - ts)**2 * px1 + 2 * (1 - ts) * ts * cpx + ts**2 * px2
                mid_by = (1 - ts)**2 * py1 + 2 * (1 - ts) * ts * cpy + ts**2 * py2
                mid_px = float(mid_bx[0])
                mid_py = float(mid_by[0])

                dt = 0.01
                t1, t2 = 0.5 - dt, 0.5 + dt
                tan_x = ((1-t2)**2*px1 + 2*(1-t2)*t2*cpx + t2**2*px2) - \
                         ((1-t1)**2*px1 + 2*(1-t1)*t1*cpx + t1**2*px2)
                tan_y = ((1-t2)**2*py1 + 2*(1-t2)*t2*cpy + t2**2*py2) - \
                         ((1-t1)**2*py1 + 2*(1-t1)*t1*cpy + t1**2*py2)
                arrow_angle = math.degrees(math.atan2(tan_y, tan_x))

            glow_id = next_eid("pg")
            edge_id = next_eid("pe")
            arrow_id = next_eid("pa")

            path_els.append(
                f'<path id="{glow_id}" d="{svg_d}" fill="none" '
                f'stroke="white" stroke-width="6" opacity="0.3" '
                f'pointer-events="none"/>'
            )
            path_els.append(
                f'<path id="{edge_id}" d="{svg_d}" fill="none" '
                f'stroke="{path_color_hex}" stroke-width="4" opacity="0.9" '
                f'pointer-events="none"/>'
            )

            arr_size = 6
            svg_angle = arrow_angle + 90
            path_els.append(
                f'<polygon id="{arrow_id}" '
                f'points="{-arr_size},{arr_size} {arr_size},{arr_size} 0,{-arr_size}" '
                f'fill="{path_color_hex}" stroke="white" stroke-width="1" '
                f'transform="translate({mid_px:.2f},{mid_py:.2f}) rotate({svg_angle:.2f})" '
                f'pointer-events="none"/>'
            )

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

        path_els.append(
            f'<defs>'
            f'<radialGradient id="{sg_id}">'
            f'<stop offset="0%" stop-color="{start_hex}" stop-opacity="0.6"/>'
            f'<stop offset="70%" stop-color="{start_hex}" stop-opacity="0.2"/>'
            f'<stop offset="100%" stop-color="{start_hex}" stop-opacity="0"/>'
            f'</radialGradient>'
            f'<radialGradient id="{eg_id}">'
            f'<stop offset="0%" stop-color="{end_hex}" stop-opacity="0.6"/>'
            f'<stop offset="70%" stop-color="{end_hex}" stop-opacity="0.2"/>'
            f'<stop offset="100%" stop-color="{end_hex}" stop-opacity="0"/>'
            f'</radialGradient>'
            f'</defs>'
        )
        path_els.append(
            f'<circle id="{start_halo_id}" cx="{sx:.2f}" cy="{sy:.2f}" r="20" '
            f'fill="url(#{sg_id})" pointer-events="none"/>'
        )
        path_els.append(
            f'<circle id="{end_halo_id}" cx="{ex:.2f}" cy="{ey:.2f}" r="20" '
            f'fill="url(#{eg_id})" pointer-events="none"/>'
        )
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

    node_els = []
    all_node_ids = []
    node_id_map = {}
    ns = node_size

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
        hover_text = f"Node: {node}  Alias: {label}  Combo: {combo_str}  Product: {product}  Ratio: {ratio}"

        if has_path:
            nc = path_node_colors_map.get(node, dimmed_node_color)
        else:
            nc = 'white'

        nid = next_eid("nd")
        all_node_ids.append(nid)
        node_id_map[node] = nid

        tooltip = html_escape(hover_text)
        node_els.append(
            f'<circle id="{nid}" cx="{cx_px:.2f}" cy="{cy_px:.2f}" r="{ns / 2:.1f}" '
            f'fill="{nc}" stroke="white" stroke-width="2">'
            f'<title>{tooltip}</title></circle>'
        )

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

    all_svg = '\n'.join(els + path_els + node_els)
    svg_str = (
        f'<div style="overflow-x:auto;overflow-y:hidden;background:black">'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width_px}" height="{height_px}" '
        f'style="display:block;background:black">'
        f'{all_svg}</svg></div>'
    )

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
    )
