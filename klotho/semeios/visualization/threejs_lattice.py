import math
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict


def _path_color_array(cmap_name, n):
    cmap = plt.cm.get_cmap(cmap_name)
    return cmap(np.linspace(0.15, 1, n))


def _rgba_to_hex(rgba):
    return '#%02x%02x%02x' % (int(rgba[0]*255), int(rgba[1]*255), int(rgba[2]*255))


def _bezier_3d(p0, p1, control, n_points=20):
    ts = np.linspace(0, 1, n_points)
    xs = (1 - ts)**2 * p0[0] + 2 * (1 - ts) * ts * control[0] + ts**2 * p1[0]
    ys = (1 - ts)**2 * p0[1] + 2 * (1 - ts) * ts * control[1] + ts**2 * p1[1]
    zs = (1 - ts)**2 * p0[2] + 2 * (1 - ts) * ts * control[2] + ts**2 * p1[2]
    return xs, ys, zs


def _rodrigues_rotate(v, axis, theta):
    axis = axis / np.linalg.norm(axis)
    return (v * math.cos(theta)
            + np.cross(axis, v) * math.sin(theta)
            + axis * np.dot(axis, v) * (1 - math.cos(theta)))


def _get_perp(edge_dir):
    up = np.array([0.0, 0.0, 1.0])
    perp = np.cross(edge_dir, up)
    perp_len = np.linalg.norm(perp)
    if perp_len < 1e-9:
        up = np.array([0.0, 1.0, 0.0])
        perp = np.cross(edge_dir, up)
        perp_len = np.linalg.norm(perp)
    return perp / perp_len


def _unpack3(c):
    if len(c) >= 3:
        return c[0], c[1], c[2]
    elif len(c) == 2:
        return c[0], c[1], 0
    return c[0], 0, 0


class ThreejsLatticeData:
    __slots__ = ('scene_data', 'path_steps', 'halo_data',
                 'title', 'width_px', 'height_px')

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _threejs_lattice_3d(lattice, coords, G, path, nodes,
                        highlighted_coords, coord_mapping, original_coords,
                        effective_dimensionality, use_dimmed, mute_background,
                        path_mode, figsize, node_size, title,
                        is_tone_lattice, coord_label, gen_labels,
                        path_cmap='viridis'):
    import networkx as nx

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    reverse_coord_mapping = {v: k for k, v in coord_mapping.items()} if len(coord_mapping) > 0 else {}

    dimmed_edge_color = '#333333'
    dimmed_node_color = '#080808'
    drawn_nodes = set()

    grid_edges = []
    if not ((nodes or path) and mute_background):
        edge_color = dimmed_edge_color if use_dimmed else '#808080'
        edge_width = 1 if use_dimmed else 3
        for u, v in G.edges():
            x1, y1, z1 = _unpack3(u)
            x2, y2, z2 = _unpack3(v)
            grid_edges.append([x1, y1, z1, x2, y2, z2])
    else:
        edge_color = '#808080'
        edge_width = 3

    highlight_edges = []
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
                        x1, y1, z1 = _unpack3(pc1)
                        x2, y2, z2 = _unpack3(pc2)
                        drawn_nodes.add((x1, y1, z1))
                        drawn_nodes.add((x2, y2, z2))
                        highlight_edges.append([x1, y1, z1, x2, y2, z2])
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
                                x1, y1, z1 = _unpack3(pc1)
                                x2, y2, z2 = _unpack3(pc2)
                                drawn_nodes.add((x1, y1, z1))
                                drawn_nodes.add((x2, y2, z2))
                                highlight_edges.append([x1, y1, z1, x2, y2, z2])
                    except Exception:
                        continue

    path_steps = []
    halo_data = None
    base_arc_offset = 0.15
    n_bezier_points = 20

    if path and len(path) >= 2:
        colors = _path_color_array(path_cmap, len(path) - 1)
        edge_counts = defaultdict(int)

        for i in range(len(path) - 1):
            coord1, coord2 = path[i], path[i + 1]

            if lattice.dimensionality > 3:
                if coord1 in coord_mapping and coord2 in coord_mapping:
                    plot_coord1, plot_coord2 = coord_mapping[coord1], coord_mapping[coord2]
                else:
                    path_steps.append(None)
                    continue
            else:
                plot_coord1, plot_coord2 = coord1, coord2

            x1, y1, z1 = _unpack3(plot_coord1)
            x2, y2, z2 = _unpack3(plot_coord2)
            drawn_nodes.add((x1, y1, z1))
            drawn_nodes.add((x2, y2, z2))

            edge_key = tuple(sorted([plot_coord1, plot_coord2]))
            traversal_idx = edge_counts[edge_key]
            edge_counts[edge_key] += 1

            path_color_hex = _rgba_to_hex(colors[i])
            dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
            length = math.sqrt(dx*dx + dy*dy + dz*dz)

            if traversal_idx == 0:
                polyline = [[x1, y1, z1], [x2, y2, z2]]
                mid = [(x1+x2)/2, (y1+y2)/2, (z1+z2)/2]
            else:
                if length < 1e-9:
                    path_steps.append(None)
                    continue
                edge_dir = np.array([dx, dy, dz]) / length
                base_perp = _get_perp(edge_dir)
                rotation_angle = (math.pi / 3) * traversal_idx
                perp = _rodrigues_rotate(base_perp, edge_dir, rotation_angle)
                offset_mag = base_arc_offset * math.ceil(traversal_idx / 2)
                if traversal_idx % 2 == 0:
                    perp = -perp
                ctrl = np.array([(x1+x2)/2, (y1+y2)/2, (z1+z2)/2]) + perp * offset_mag
                bx, by, bz = _bezier_3d(
                    (x1, y1, z1), (x2, y2, z2),
                    (ctrl[0], ctrl[1], ctrl[2]), n_bezier_points
                )
                polyline = [[float(bx[k]), float(by[k]), float(bz[k])] for k in range(len(bx))]
                mid_idx = n_bezier_points // 2
                mid = [float(bx[mid_idx]), float(by[mid_idx]), float(bz[mid_idx])]

            norm = length if length > 1e-9 else 1.0
            arrow_dir = [dx / norm, dy / norm, dz / norm]

            path_steps.append({
                'polyline': polyline,
                'color': path_color_hex,
                'arrow_pos': mid,
                'arrow_dir': arrow_dir,
            })

        start_coord = path[0]
        end_coord = path[-1]
        if lattice.dimensionality > 3:
            start_plot = coord_mapping.get(start_coord, start_coord)
            end_plot = coord_mapping.get(end_coord, end_coord)
        else:
            start_plot = start_coord
            end_plot = end_coord

        sx, sy, sz = _unpack3(start_plot)
        ex, ey, ez = _unpack3(end_plot)
        start_hex = _rgba_to_hex(colors[0])
        end_hex = _rgba_to_hex(colors[-1])

        halo_data = {
            'start': {'pos': [sx, sy, sz], 'color': start_hex},
            'end': {'pos': [ex, ey, ez], 'color': end_hex},
        }

    node_positions = []
    node_colors = []
    hover_texts = []
    has_path = path and len(path) >= 2

    coords_iter = coords
    if (nodes or path) and mute_background and len(drawn_nodes) > 0:
        coords_iter = list(drawn_nodes)

    for i, coord in enumerate(coords_iter):
        x, y, z = _unpack3(coord)
        node_positions.append([x, y, z])

        if lattice.dimensionality <= 3 or len(reverse_coord_mapping) == 0:
            orig_coord = coord
        else:
            orig_coord = reverse_coord_mapping.get(coord, None)

        if lattice.dimensionality > 3 and orig_coord is not None:
            orig_str = str(orig_coord).replace(',)', ')')
            reduced_str = f"({x:.2f}, {y:.2f}, {z:.2f})"
            hover_text = f"Original: {orig_str}\nReduced: {reduced_str}"
        else:
            hover_text = f"{coord_label}: ({x}, {y}, {z})"

        if is_tone_lattice:
            try:
                coord_to_use = orig_coord if orig_coord is not None else coord
                ratio = lattice._coord_to_ratio(coord_to_use)
                hover_text += f"\nRatio: {ratio}"
            except (KeyError, AttributeError):
                pass

        hover_texts.append(hover_text)

        if highlighted_coords and orig_coord in highlighted_coords:
            node_colors.append('#ffffff')
        elif use_dimmed:
            node_colors.append(dimmed_node_color)
        else:
            node_colors.append('#ffffff')

    pos_to_node_idx = {}
    for i, p in enumerate(node_positions):
        key = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
        pos_to_node_idx[key] = i

    path_node_indices = []
    path_node_colors = []
    path_node_final = {}
    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)
        for k, coord in enumerate(path):
            if lattice.dimensionality > 3:
                plot_coord = coord_mapping.get(coord, coord)
            else:
                plot_coord = coord
            px, py, pz = _unpack3(plot_coord)
            key = (round(px, 6), round(py, 6), round(pz, 6))
            idx = pos_to_node_idx.get(key, -1)
            path_node_indices.append(idx)
            step_color = _rgba_to_hex(colors[0]) if k == 0 else _rgba_to_hex(colors[k - 1])
            path_node_colors.append(step_color)
            if idx >= 0:
                path_node_final[idx] = step_color

        for i in range(len(node_colors)):
            node_colors[i] = path_node_final.get(i, dimmed_node_color)

    x_all = [p[0] for p in node_positions] if node_positions else [c[0] for c in coords]
    y_all = [p[1] for p in node_positions] if node_positions else [c[1] if len(c) > 1 else 0 for c in coords]
    z_all = [p[2] for p in node_positions] if node_positions else [c[2] if len(c) > 2 else 0 for c in coords]

    x_min, x_max = min(x_all), max(x_all)
    y_min, y_max = min(y_all), max(y_all)
    z_min, z_max = min(z_all), max(z_all)
    pad = 0.5

    if lattice.dimensionality > 3:
        x_ticks = [round(t, 1) for t in np.linspace(x_min, x_max, min(10, int(x_max - x_min) + 1))]
        y_ticks = [round(t, 1) for t in np.linspace(y_min, y_max, min(10, int(y_max - y_min) + 1))]
        z_ticks = [round(t, 1) for t in np.linspace(z_min, z_max, min(10, int(z_max - z_min) + 1))]
        axis_labels = ['', '', '']
    else:
        x_ticks = list(range(int(x_min), int(x_max) + 1))
        y_ticks = list(range(int(y_min), int(y_max) + 1))
        z_ticks = list(range(int(z_min), int(z_max) + 1))
        axis_labels = [
            gen_labels[0] if len(gen_labels) > 0 else 'X',
            gen_labels[1] if len(gen_labels) > 1 else 'Y',
            gen_labels[2] if len(gen_labels) > 2 else 'Z',
        ]

    scene_data = {
        'gridEdges': grid_edges,
        'gridEdgeColor': edge_color,
        'gridEdgeWidth': edge_width,
        'highlightEdges': highlight_edges,
        'nodes': node_positions,
        'nodeColors': node_colors,
        'nodeSize': node_size,
        'hoverData': hover_texts,
        'dimmedNodeColor': dimmed_node_color,
        'pathNodeIndices': path_node_indices,
        'pathNodeColors': path_node_colors,
        'axisConfig': {
            'xRange': [x_min - pad, x_max + pad],
            'yRange': [y_min - pad, y_max + pad],
            'zRange': [z_min - pad, z_max + pad],
            'xTicks': x_ticks,
            'yTicks': y_ticks,
            'zTicks': z_ticks,
            'labels': axis_labels,
        },
        'camera': {'eye': [1.5, 1.5, 1.5]},
    }

    return ThreejsLatticeData(
        scene_data=scene_data,
        path_steps=path_steps,
        halo_data=halo_data,
        title=title or '',
        width_px=width_px,
        height_px=height_px,
    )
