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


class SvgLatticeData:
    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_group_ids', 'halo_ids', 'all_path_ids',
                 'all_node_ids', 'path_node_indices', 'path_node_colors',
                 'dimmed_node_color')

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_html(self, **kwargs):
        return self.svg_str


def _svg_lattice_2d(lattice, coords, G, path, nodes,
                    highlighted_coords, coord_mapping, original_coords,
                    effective_dimensionality, use_dimmed, mute_background,
                    path_mode, figsize, node_size, title,
                    is_tone_lattice, coord_label, gen_labels,
                    path_cmap='viridis'):
    import networkx as nx

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    reverse_coord_mapping = {v: k for k, v in coord_mapping.items()} if len(coord_mapping) > 0 else {}

    if effective_dimensionality == 2:
        dimmed_edge_color = '#555555'
        dimmed_node_color = '#111111'
    else:
        dimmed_edge_color = '#555555'
        dimmed_node_color = '#111111'

    valid_coords = set(coords) if lattice.dimensionality <= 3 else set(original_coords)

    bounds_coords = coords
    drawn_nodes_set = set()

    x_coords_all = [c[0] for c in coords]
    x_min, x_max = min(x_coords_all), max(x_coords_all)
    if effective_dimensionality >= 2:
        y_coords_all = [c[1] for c in coords]
        y_min, y_max = min(y_coords_all), max(y_coords_all)
    else:
        y_min, y_max = -0.5, 0.5

    x_pad = 0.5
    y_pad = 0.5

    if lattice.dimensionality > 3:
        x_ticks = [round(t, 1) for t in np.linspace(x_min, x_max, min(10, int(x_max - x_min) + 1))]
        y_ticks = [round(t, 1) for t in np.linspace(y_min, y_max, min(10, int(y_max - y_min) + 1))] if effective_dimensionality == 2 else [0]
    else:
        x_ticks = list(range(int(x_min), int(x_max) + 1))
        y_ticks = list(range(int(y_min), int(y_max) + 1)) if effective_dimensionality == 2 else [0]

    data_x_min = x_min - x_pad
    data_x_max = x_max + x_pad
    data_y_min = y_min - y_pad
    data_y_max = y_max + y_pad

    margin_left = 50
    margin_right = 20
    margin_top = 50
    margin_bottom = 40
    plot_w = width_px - margin_left - margin_right
    plot_h = height_px - margin_top - margin_bottom

    data_w = data_x_max - data_x_min
    data_h = data_y_max - data_y_min

    if effective_dimensionality == 2:
        aspect = data_w / data_h if data_h > 0 else 1
        plot_aspect = plot_w / plot_h if plot_h > 0 else 1
        if aspect > plot_aspect:
            actual_w = plot_w
            actual_h = plot_w / aspect
        else:
            actual_h = plot_h
            actual_w = plot_h * aspect
        ox = margin_left
        oy = margin_top
        width_px = int(ox + actual_w + margin_right)
        height_px = int(oy + actual_h + margin_bottom)
    else:
        actual_w = plot_w
        actual_h = plot_h
        ox = margin_left
        oy = margin_top

    def tx(val):
        return ox + (val - data_x_min) / data_w * actual_w

    def ty(val):
        return oy + actual_h - (val - data_y_min) / data_h * actual_h

    import uuid as _uuid
    uid = f"svglat_{_uuid.uuid4().hex[:8]}"
    els = []
    eid_counter = [0]

    def next_eid(prefix="l"):
        eid_counter[0] += 1
        return f"{uid}_{prefix}{eid_counter[0]}"

    els.append(f'<rect width="{width_px}" height="{height_px}" fill="black"/>')

    if title:
        els.append(
            f'<text x="{width_px / 2:.1f}" y="{margin_top / 2:.1f}" '
            f'text-anchor="middle" dominant-baseline="central" '
            f'font-family="Arial" font-size="14" fill="white">'
            f'{html_escape(title)}</text>'
        )

    if not (lattice.dimensionality > 2 or lattice.dimensionality > 3):
        x_title = gen_labels[0] if len(gen_labels) > 0 else 'X'
        y_title = (gen_labels[1] if len(gen_labels) > 1 else 'Y') if effective_dimensionality == 2 else ''

        for t in x_ticks:
            px = tx(t)
            py = oy + actual_h + 15
            els.append(
                f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="middle" '
                f'font-family="Arial" font-size="11" fill="white">{t}</text>'
            )

        els.append(
            f'<text x="{ox + actual_w / 2:.1f}" y="{oy + actual_h + 35:.1f}" '
            f'text-anchor="middle" font-family="Arial" font-size="12" fill="white">'
            f'{html_escape(x_title)}</text>'
        )

        if effective_dimensionality == 2:
            for t in y_ticks:
                px = ox - 10
                py = ty(t)
                els.append(
                    f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="end" '
                    f'dominant-baseline="central" '
                    f'font-family="Arial" font-size="11" fill="white">{t}</text>'
                )

            els.append(
                f'<text x="{ox - 35:.1f}" y="{oy + actual_h / 2:.1f}" '
                f'text-anchor="middle" dominant-baseline="central" '
                f'font-family="Arial" font-size="12" fill="white" '
                f'transform="rotate(-90,{ox - 35:.1f},{oy + actual_h / 2:.1f})">'
                f'{html_escape(y_title)}</text>'
            )

    if not ((nodes or path) and mute_background):
        edge_color = dimmed_edge_color if use_dimmed else '#808080'
        edge_width = 1 if use_dimmed else 2

        if effective_dimensionality == 1:
            for u, v in G.edges():
                px1, py1 = tx(u[0]), ty(0)
                px2, py2 = tx(v[0]), ty(0)
                els.append(
                    f'<line x1="{px1:.2f}" y1="{py1:.2f}" x2="{px2:.2f}" y2="{py2:.2f}" '
                    f'stroke="{edge_color}" stroke-width="{edge_width}"/>'
                )
        else:
            for u, v in G.edges():
                px1, py1 = tx(u[0]), ty(u[1])
                px2, py2 = tx(v[0]), ty(v[1])
                els.append(
                    f'<line x1="{px1:.2f}" y1="{py1:.2f}" x2="{px2:.2f}" y2="{py2:.2f}" '
                    f'stroke="{edge_color}" stroke-width="{edge_width}"/>'
                )

    if nodes and len(highlighted_coords) >= 1:
        highlighted_list = list(highlighted_coords)

        if path_mode == 'adjacent' and len(highlighted_coords) > 1:
            for i in range(len(highlighted_list)):
                for j in range(i + 1, len(highlighted_list)):
                    coord1, coord2 = highlighted_list[i], highlighted_list[j]
                    diff_count = sum(1 for a, b in zip(coord1, coord2) if abs(a - b) == 1)
                    same_count = sum(1 for a, b in zip(coord1, coord2) if a == b)
                    if diff_count == 1 and same_count == len(coord1) - 1:
                        if lattice.dimensionality > 3:
                            if coord1 in coord_mapping and coord2 in coord_mapping:
                                pc1, pc2 = coord_mapping[coord1], coord_mapping[coord2]
                            else:
                                continue
                        else:
                            pc1, pc2 = coord1, coord2
                        if effective_dimensionality == 1:
                            px1, py1 = tx(pc1[0]), ty(0)
                            px2, py2 = tx(pc2[0]), ty(0)
                        else:
                            px1, py1 = tx(pc1[0]), ty(pc1[1])
                            px2, py2 = tx(pc2[0]), ty(pc2[1])
                        drawn_nodes_set.add(pc1)
                        drawn_nodes_set.add(pc2)
                        els.append(
                            f'<line x1="{px1:.2f}" y1="{py1:.2f}" x2="{px2:.2f}" y2="{py2:.2f}" '
                            f'stroke="white" stroke-width="4"/>'
                        )

        elif path_mode == 'origin':
            origin = tuple(0 for _ in range(lattice.dimensionality))
            origin_plot = coord_mapping.get(origin, origin) if lattice.dimensionality > 3 else origin
            for target_coord in highlighted_list:
                if target_coord != origin:
                    try:
                        target_plot = coord_mapping.get(target_coord, target_coord) if lattice.dimensionality > 3 else target_coord
                        if hasattr(G, 'has_node') and G.has_node(origin_plot) and G.has_node(target_plot):
                            path_coords = nx.shortest_path(G, origin_plot, target_plot)
                            for k in range(len(path_coords) - 1):
                                pc1, pc2 = path_coords[k], path_coords[k + 1]
                                if effective_dimensionality == 1:
                                    px1, py1 = tx(pc1[0]), ty(0)
                                    px2, py2 = tx(pc2[0]), ty(0)
                                else:
                                    px1, py1 = tx(pc1[0]), ty(pc1[1])
                                    px2, py2 = tx(pc2[0]), ty(pc2[1])
                                drawn_nodes_set.add(pc1)
                                drawn_nodes_set.add(pc2)
                                els.append(
                                    f'<line x1="{px1:.2f}" y1="{py1:.2f}" '
                                    f'x2="{px2:.2f}" y2="{py2:.2f}" '
                                    f'stroke="white" stroke-width="4"/>'
                                )
                    except Exception:
                        continue

    path_els = []
    step_group_ids = []
    halo_ids = []
    all_path_el_ids = []
    base_arc_offset = 0.15
    n_bezier_points = 20

    if path and len(path) >= 2:
        colors = _path_color_array(path_cmap, len(path) - 1)
        edge_counts = defaultdict(int)

        for i in range(len(path) - 1):
            coord1, coord2 = path[i], path[i + 1]

            if lattice.dimensionality > 3:
                if coord1 in coord_mapping and coord2 in coord_mapping:
                    pc1, pc2 = coord_mapping[coord1], coord_mapping[coord2]
                else:
                    step_group_ids.append([])
                    continue
            else:
                pc1, pc2 = coord1, coord2

            if effective_dimensionality == 1:
                x1, y1 = pc1[0], 0
                x2, y2 = pc2[0], 0
            else:
                x1, y1 = pc1[0], pc1[1]
                x2, y2 = pc2[0], pc2[1]

            drawn_nodes_set.add(pc1)
            drawn_nodes_set.add(pc2)

            edge_key = tuple(sorted([pc1, pc2]))
            traversal_idx = edge_counts[edge_key]
            edge_counts[edge_key] += 1
            is_forward = pc1 <= pc2

            path_color_hex = _rgba_to_hex(colors[i])

            px1, py1 = tx(x1), ty(y1)
            px2, py2 = tx(x2), ty(y2)

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
                if traversal_idx == 1:
                    offset_mag = base_arc_offset
                else:
                    offset_mag = base_arc_offset * ((traversal_idx + 1) // 2)
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
                t1 = 0.5 - dt
                t2 = 0.5 + dt
                tan_x = ((1-t2)**2*px1 + 2*(1-t2)*t2*cpx + t2**2*px2) - ((1-t1)**2*px1 + 2*(1-t1)*t1*cpx + t1**2*px2)
                tan_y = ((1-t2)**2*py1 + 2*(1-t2)*t2*cpy + t2**2*py2) - ((1-t1)**2*py1 + 2*(1-t1)*t1*cpy + t1**2*py2)
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

        start_coord = path[0]
        end_coord = path[-1]
        if lattice.dimensionality > 3:
            start_plot = coord_mapping.get(start_coord, start_coord)
            end_plot = coord_mapping.get(end_coord, end_coord)
        else:
            start_plot = start_coord
            end_plot = end_coord

        start_hex = _rgba_to_hex(colors[0])
        end_hex = _rgba_to_hex(colors[-1])

        if effective_dimensionality == 1:
            sx, sy = tx(start_plot[0]), ty(0)
            ex, ey = tx(end_plot[0]), ty(0)
        else:
            sx, sy = tx(start_plot[0]), ty(start_plot[1])
            ex, ey = tx(end_plot[0]), ty(end_plot[1])

        start_halo_id = next_eid("hs")
        end_halo_id = next_eid("he")
        sg_id = next_eid("rg")
        eg_id = next_eid("rg")

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

    has_path = path and len(path) >= 2
    coords_iter = coords
    if (nodes or path) and mute_background and len(drawn_nodes_set) > 0:
        coords_iter = list(drawn_nodes_set)

    path_coord_colors = {}
    if has_path:
        for k in range(len(path)):
            coord = path[k]
            if lattice.dimensionality > 3:
                coord = coord_mapping.get(coord, coord)
            if k == 0:
                path_coord_colors[coord] = _rgba_to_hex(colors[0])
            else:
                path_coord_colors[coord] = _rgba_to_hex(colors[k - 1])

    node_els = []
    all_node_ids = []
    coord_to_node_id = {}
    ns = node_size * 2
    for i, coord in enumerate(coords_iter):
        if effective_dimensionality == 1:
            cx_px, cy_px = tx(coord[0]), ty(0)
        else:
            cx_px, cy_px = tx(coord[0]), ty(coord[1])

        if lattice.dimensionality <= 3 or len(reverse_coord_mapping) == 0:
            orig_coord = coord
        else:
            orig_coord = reverse_coord_mapping.get(coord, None)

        if lattice.dimensionality > 3 and orig_coord is not None:
            orig_str = str(orig_coord).replace(',)', ')')
            if effective_dimensionality == 1:
                red_str = f"({coord[0]:.2f})"
            else:
                red_str = f"({coord[0]:.2f}, {coord[1]:.2f})"
            hover_text = f"Original: {orig_str}\nReduced: {red_str}"
        else:
            if effective_dimensionality == 1:
                hover_text = f"{coord_label}: ({coord[0]})"
            else:
                hover_text = f"{coord_label}: ({coord[0]}, {coord[1]})"

        if is_tone_lattice:
            try:
                coord_to_use = orig_coord if orig_coord is not None else coord
                ratio = lattice._coord_to_ratio(coord_to_use)
                hover_text += f"\nRatio: {ratio}"
            except (KeyError, AttributeError):
                pass

        if has_path:
            nc = path_coord_colors.get(coord, dimmed_node_color)
        elif highlighted_coords and (
            (coords_iter is coords and i < len(original_coords) and original_coords[i] in highlighted_coords) or
            (coords_iter is not coords and (coord in highlighted_coords or (orig_coord is not None and orig_coord in highlighted_coords)))
        ):
            nc = 'white'
        elif use_dimmed:
            nc = dimmed_node_color
        else:
            nc = 'white'

        nid = next_eid("nd")
        all_node_ids.append(nid)
        coord_to_node_id[coord] = nid

        tooltip = html_escape(hover_text)
        node_els.append(
            f'<circle id="{nid}" cx="{cx_px:.2f}" cy="{cy_px:.2f}" r="{ns / 2:.1f}" '
            f'fill="{nc}" stroke="white" stroke-width="2">'
            f'<title>{tooltip}</title></circle>'
        )

    path_node_indices = []
    path_node_colors = []
    if has_path:
        for k, coord in enumerate(path):
            if lattice.dimensionality > 3:
                plot_coord = coord_mapping.get(coord, coord)
            else:
                plot_coord = coord
            nid = coord_to_node_id.get(plot_coord, '')
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

    return SvgLatticeData(
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
