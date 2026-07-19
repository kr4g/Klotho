import numpy as np
from html import escape as html_escape

from .._shared.audio_ref import reference_freq
from .._shared.colors import _rgba_to_hex
from .._shared.svg_utils import SvgFigureData, svg_wrap
from .._shared.svg_shared import (
    render_tooltip_system, render_path_edges, render_shape_groups,
)


class SvgLatticeData(SvgFigureData):
    """Container for 2D lattice SVG rendering data and animation metadata."""

    __slots__ = ('svg_str', 'width_px', 'height_px',
                 'step_group_ids', 'halo_ids', 'all_path_ids',
                 'all_node_ids', 'path_node_indices', 'path_node_colors',
                 'dimmed_node_color',
                 'shape_group_node_indices', 'shape_group_edge_ids',
                 'shape_colors', 'all_shape_edge_ids')


def _svg_lattice_2d(lattice, coords, G, path, nodes,
                    highlighted_coords, coord_mapping, original_coords,
                    effective_dimensionality, use_dimmed, mute_background,
                    path_mode, figsize, node_size, title,
                    is_tone_lattice, coord_label, gen_labels,
                    path_cmap='viridis', shape=None, preview_config=None):
    """
    Build a 2D SVG representation of a lattice.

    Generates an inline SVG with grid edges, nodes, optional path /
    shape overlays, axis labels, and hover tooltips.  The result is
    wrapped in an `SvgLatticeData` container for display or animation.

    Parameters
    ----------
    lattice : Lattice
        The lattice object providing coordinate and metadata access.
    coords : list of tuple
        Lattice coordinates to render.
    G : networkx.Graph
        Edge structure for the rendered region.
    path : list of tuple or None
        Coordinate path to overlay.
    nodes : list of tuple or None
        Coordinates to highlight.
    highlighted_coords : set
        Union of all highlighted coordinates.
    coord_mapping : dict
        Maps original high-dimensional coordinates to reduced ones.
    original_coords : list of tuple
        Pre-reduction coordinate list.
    effective_dimensionality : int
        Number of plotting dimensions (1 or 2).
    use_dimmed : bool
        Whether non-highlighted elements should be dimmed.
    mute_background : bool
        Hide non-selected nodes entirely when ``True``.
    path_mode : str
        ``'adjacent'`` or ``'origin'``.
    figsize : tuple of float
        Width and height in inches.
    node_size : float
        Base node diameter.
    title : str
        Title rendered above the diagram.
    is_tone_lattice : bool
        Whether the lattice carries ratio information.
    coord_label : str
        Label prefix for hover tooltips (e.g. ``"Monzo"``).
    gen_labels : list of str
        Axis labels derived from lattice generators.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    shape : list of list of tuple or None, optional
        Chord groups to highlight.

    Returns
    -------
    SvgLatticeData
        SVG string and associated animation metadata.
    """
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

    def _plot_key(coord):
        """Map a lattice coordinate to its plot-space key, or None."""
        if lattice.dimensionality > 3:
            if coord not in coord_mapping:
                return None
            return coord_mapping[coord]
        return coord

    path_els = []
    step_group_ids = []
    halo_ids = []
    all_path_el_ids = []
    colors = None

    if path and len(path) >= 2:
        plot_path = []
        for coord in path:
            pc = _plot_key(coord)
            plot_path.append(pc)
        for i in range(len(plot_path) - 1):
            if plot_path[i] is not None and plot_path[i + 1] is not None:
                drawn_nodes_set.add(plot_path[i])
                drawn_nodes_set.add(plot_path[i + 1])

        def _plot_key_positions(pc):
            if pc is None:
                return None
            if effective_dimensionality == 1:
                x, y = pc[0], 0
            else:
                x, y = pc[0], pc[1]
            return x, y, tx(x), ty(y)

        _plot_key_positions._tx = tx
        _plot_key_positions._ty = ty

        path_els, step_group_ids, halo_ids, all_path_el_ids, colors = render_path_edges(
            plot_path, _plot_key_positions, next_eid, path_cmap=path_cmap)

    has_path = path and len(path) >= 2

    if shape is not None and len(shape) > 0:
        shape_groups = shape
    else:
        shape_groups = []
    has_shape = len(shape_groups) > 0
    all_shape_node_set = set()
    for g in shape_groups:
        for c in g:
            all_shape_node_set.add(tuple(c) if not isinstance(c, tuple) else c)

    coords_iter = coords
    if (nodes or path or has_shape) and mute_background and len(drawn_nodes_set) > 0:
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

    shape_els = []
    svg_shape_group_edge_ids = []
    all_shape_el_ids = []
    shape_coord_colors = {}
    used_shape_colors = []

    if has_shape:
        edge_set = set()
        for u, v in G.edges():
            edge_set.add((u, v))
            edge_set.add((v, u))

        shape_groups_t = [
            [tuple(c) if not isinstance(c, tuple) else c for c in group]
            for group in shape_groups
        ]

        def _shape_plot(c):
            return coord_mapping.get(c, c) if lattice.dimensionality > 3 else c

        def _shape_edge_exists(c1, c2):
            pc1, pc2 = _shape_plot(c1), _shape_plot(c2)
            return (pc1, pc2) in edge_set or (pc2, pc1) in edge_set

        def _shape_positions(c):
            pc = _shape_plot(c)
            if effective_dimensionality == 1:
                return tx(pc[0]), ty(0)
            return tx(pc[0]), ty(pc[1])

        shape_els, svg_shape_group_edge_ids, all_shape_el_ids, used_shape_colors, shape_coord_colors = (
            render_shape_groups(shape_groups_t, _shape_edge_exists, _shape_positions, next_eid)
        )

    node_els = []
    all_node_ids = []
    coord_to_node_id = {}
    hover_texts = []
    is_active_list = []
    node_freqs = [] if is_tone_lattice else None
    ref_freq = reference_freq(lattice)
    ns = node_size * 2
    node_idx_counter = 0
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
            hover_text = f"{coord_label}: {orig_str}"
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
                if node_freqs is not None:
                    node_freqs.append(ref_freq * float(ratio))
            except (KeyError, AttributeError):
                if node_freqs is not None:
                    node_freqs.append(ref_freq)

        orig_or_coord = orig_coord if orig_coord is not None else coord
        if has_path:
            nc = path_coord_colors.get(coord, dimmed_node_color)
            active = coord in path_coord_colors
        elif has_shape and orig_or_coord in shape_coord_colors:
            nc = shape_coord_colors[orig_or_coord]
            active = True
        elif has_shape and coord in shape_coord_colors:
            nc = shape_coord_colors[coord]
            active = True
        elif highlighted_coords and (
            (coords_iter is coords and i < len(original_coords) and original_coords[i] in highlighted_coords) or
            (coords_iter is not coords and (coord in highlighted_coords or (orig_coord is not None and orig_coord in highlighted_coords)))
        ):
            nc = 'white'
            active = True
        elif use_dimmed:
            nc = dimmed_node_color
            active = False
        else:
            nc = 'white'
            active = True

        nid = next_eid("nd")
        all_node_ids.append(nid)
        coord_to_node_id[coord] = nid
        hover_texts.append(hover_text)
        is_active_list.append(active)

        node_els.append(
            f'<circle id="{nid}" cx="{cx_px:.2f}" cy="{cy_px:.2f}" r="{ns / 2:.1f}" '
            f'fill="{nc}" stroke="white" stroke-width="2" '
            f'data-idx="{node_idx_counter}" data-tip-uid="{uid}"/>'
        )
        node_idx_counter += 1

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

    svg_shape_group_node_indices = []
    if has_shape:
        for group in shape_groups:
            indices = []
            for c in group:
                ct = tuple(c) if not isinstance(c, tuple) else c
                plot_c = coord_mapping.get(ct, ct) if lattice.dimensionality > 3 else ct
                nid = coord_to_node_id.get(plot_c, '')
                idx = all_node_ids.index(nid) if nid in all_node_ids else -1
                indices.append(idx)
            svg_shape_group_node_indices.append(indices)

    all_svg = '\n'.join(els + path_els + shape_els + node_els)
    tooltip_html = render_tooltip_system(uid, hover_texts,
                                         is_active=is_active_list if use_dimmed else None,
                                         node_freqs=node_freqs if preview_config else None,
                                         preview_config=preview_config,
                                         dimmed_node_color=dimmed_node_color)
    svg_str = svg_wrap(all_svg, width_px, height_px) + tooltip_html

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
        shape_group_node_indices=svg_shape_group_node_indices,
        shape_group_edge_ids=svg_shape_group_edge_ids,
        shape_colors=used_shape_colors,
        all_shape_edge_ids=all_shape_el_ids,
    )
