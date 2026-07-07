from .threejs_lattice import ThreejsLatticeData
from .._shared.colors import SHAPE_COLORS, _path_color_array, _rgba_to_hex


def _threejs_cps_3d(cps, node_positions, G, figsize=(12, 12),
                    node_size=30, text_size=12, show_labels=True,
                    title=None, nodes=None, preview_engine='supersonic',
                    preview_config=None, path=None, path_cmap='viridis',
                    mute_background=False, shape=None):
    """
    Build a Three.js 3D scene for a Combination Product Set.

    Mirrors the 3D lattice/MasterSet pipeline: node highlighting, path
    traversal with per-segment colouring and start/end halos, and
    per-group shape (chord) colouring.

    Parameters
    ----------
    cps : CombinationProductSet
        The CPS to render.
    node_positions : dict
        Mapping of node IDs to 3D ``(x, y, z)`` positions.
    G : Graph
        CPS graph providing edge and node attribute data.
    figsize : tuple of float, optional
        Width and height in inches (converted to pixels at 100 dpi).
    node_size : int, optional
        Base node diameter.
    text_size : int, optional
        Font size for labels.
    show_labels : bool, optional
        Whether to display labels (used for title generation).
    title : str or None, optional
        Scene title.  Auto-generated when ``None``.
    nodes : list or None, optional
        Node IDs to highlight in pale green.
    path : list or None, optional
        Node IDs defining a traversal path.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes when a selection is active.
    shape : list of list or None, optional
        Normalized shape groups (lists of node IDs).

    Returns
    -------
    ThreejsLatticeData
        Three.js scene description and metadata.
    """
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    highlight_set = set(nodes) if nodes else set()
    has_path = path and len(path) >= 2
    shape_groups = [list(g) for g in shape] if shape else []
    has_shape = len(shape_groups) > 0
    has_selection = bool(highlight_set) or has_path or has_shape
    use_dimmed = mute_background and has_selection
    dimmed_color_hex = '#555555'

    grid_edges = []
    highlight_edges = []
    for u, v, _data in G.edges(data=True):
        if u in node_positions and v in node_positions:
            x1, y1, z1 = node_positions[u]
            x2, y2, z2 = node_positions[v]
            edge = [float(x1), float(y1), float(z1),
                    float(x2), float(y2), float(z2)]
            if u in highlight_set and v in highlight_set:
                highlight_edges.append(edge)
            else:
                grid_edges.append(edge)

    scene_nodes = []
    node_colors = []
    hover_data = []
    node_freqs = []
    is_active_list = []
    node_id_to_idx = {}
    ref_freq = 261.63
    path_set = set(path) if path else set()
    for node, attrs in G.nodes(data=True):
        if node not in node_positions or 'combo' not in attrs:
            continue
        x, y, z = node_positions[node]
        node_id_to_idx[node] = len(scene_nodes)
        scene_nodes.append([float(x), float(y), float(z)])

        combo = attrs['combo']
        label = ''.join(str(cps.factor_to_alias[f]).strip('()') for f in combo)
        combo_str = '(' + ' '.join(str(f) for f in combo) + ')'
        ratio = attrs['ratio']
        hover_data.append(
            f"Node: {node}\nAlias: {label}\nCombo: {combo_str}\n"
            f"Product: {attrs['product']}\nRatio: {ratio}"
        )

        try:
            node_freqs.append(ref_freq * float(ratio))
        except (TypeError, ValueError):
            node_freqs.append(ref_freq)

        if node in path_set:
            node_colors.append('#ffffff')
            is_active_list.append(True)
        elif node in highlight_set:
            node_colors.append('#90EE90')
            is_active_list.append(True)
        elif use_dimmed:
            node_colors.append(dimmed_color_hex)
            is_active_list.append(False)
        else:
            node_colors.append('#ffffff')
            is_active_list.append(not has_selection)

    if not scene_nodes:
        scene_nodes = [[0, 0, 0]]
        node_colors = ['#ffffff']
        hover_data = ['(empty)']
        node_freqs = [ref_freq]
        is_active_list = [True]

    shape_group_node_indices = []
    shape_group_edges = []
    used_shape_colors = []
    if has_shape:
        graph_edges = set()
        for u, v, _ in G.edges(data=True):
            graph_edges.add((u, v))
            graph_edges.add((v, u))

        shape_node_final = {}
        for gi, group in enumerate(shape_groups):
            color = SHAPE_COLORS[gi % len(SHAPE_COLORS)]
            used_shape_colors.append(color)
            indices = []
            for n in group:
                idx = node_id_to_idx.get(n, -1)
                indices.append(idx)
                if idx >= 0:
                    shape_node_final[idx] = color
            shape_group_node_indices.append(indices)

            group_edges = []
            for i, n1 in enumerate(group):
                for n2 in group[i + 1:]:
                    if (n1, n2) in graph_edges and \
                            n1 in node_positions and n2 in node_positions:
                        x1, y1, z1 = node_positions[n1]
                        x2, y2, z2 = node_positions[n2]
                        group_edges.append([float(x1), float(y1), float(z1),
                                            float(x2), float(y2), float(z2)])
            shape_group_edges.append(group_edges)

        for idx, color in shape_node_final.items():
            if 0 <= idx < len(node_colors):
                node_colors[idx] = color

    path_steps = []
    halo_data = None
    path_node_indices = []
    path_node_colors = []
    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)

        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            if a not in node_positions or b not in node_positions:
                path_steps.append(None)
                continue
            x1, y1, z1 = (float(c) for c in node_positions[a])
            x2, y2, z2 = (float(c) for c in node_positions[b])
            hex_color = _rgba_to_hex(colors[i])
            path_steps.append({
                'polyline': [[x1, y1, z1], [x2, y2, z2]],
                'color': hex_color,
                'arrow_pos': [(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2],
                'arrow_dir': [x2 - x1, y2 - y1, z2 - z1],
            })

        for k, node in enumerate(path):
            idx = node_id_to_idx.get(node, -1)
            path_node_indices.append(idx)
            step_color = _rgba_to_hex(colors[0]) if k == 0 else _rgba_to_hex(colors[k - 1])
            path_node_colors.append(step_color)
            if 0 <= idx < len(node_colors):
                node_colors[idx] = step_color

        start_idx = node_id_to_idx.get(path[0], -1)
        end_idx = node_id_to_idx.get(path[-1], -1)
        if start_idx >= 0 and end_idx >= 0:
            halo_data = {
                'start': {'pos': scene_nodes[start_idx], 'color': _rgba_to_hex(colors[0])},
                'end': {'pos': scene_nodes[end_idx], 'color': _rgba_to_hex(colors[-1])},
            }

    xs = [n[0] for n in scene_nodes]
    ys = [n[1] for n in scene_nodes]
    zs = [n[2] for n in scene_nodes]
    pad = 0.08
    x_span = (max(xs) - min(xs)) or 1.0
    y_span = (max(ys) - min(ys)) or 1.0
    z_span = (max(zs) - min(zs)) or 1.0

    if title is None:
        cps_type = type(cps).__name__
        factor_string = ' '.join(str(cps.factor_to_alias[f]) for f in cps.factors)
        title = f"{cps_type} [{factor_string}] (3D)"

    scene_data = {
        'gridEdges': grid_edges,
        'gridEdgeColor': '#808080',
        'highlightEdges': highlight_edges,
        'nodes': scene_nodes,
        'nodeColors': node_colors,
        'nodeSize': 2,
        'dimmedNodeColor': dimmed_color_hex,
        'pathNodeIndices': path_node_indices,
        'pathNodeColors': path_node_colors,
        'shapeGroupNodeIndices': shape_group_node_indices,
        'shapeGroupEdges': shape_group_edges,
        'shapeColors': used_shape_colors,
        'hoverData': hover_data,
        'nodeFreqs': node_freqs if preview_config else None,
        'isActive': is_active_list if has_selection else None,
        'axisConfig': {
            'xRange': [min(xs) - x_span * pad, max(xs) + x_span * pad],
            'yRange': [min(ys) - y_span * pad, max(ys) + y_span * pad],
            'zRange': [min(zs) - z_span * pad, max(zs) + z_span * pad],
            'xTicks': [],
            'yTicks': [],
            'zTicks': [],
            'labels': ['', '', ''],
        },
        'previewEngine': preview_engine,
        'previewConfig': preview_config,
    }

    return ThreejsLatticeData(
        scene_data=scene_data,
        path_steps=path_steps,
        halo_data=halo_data,
        title=title,
        width_px=width_px,
        height_px=height_px,
    )
