from .threejs_lattice import ThreejsLatticeData
from .._shared.colors import _path_color_array, _rgba_to_hex


def _threejs_master_set_3d(ms, figsize=(12, 12), node_size=30, text_size=12,
                           show_labels=True, title=None, override_positions=None,
                           preview_engine='supersonic', preview_config=None,
                           nodes=None, path=None, path_cmap='viridis',
                           mute_background=False):
    """
    Build a Three.js 3D scene for a MasterSet.

    Mirrors the 3D lattice path pipeline, supporting optional
    node highlight, path traversal with per-segment colouring,
    and start/end halos.

    Parameters
    ----------
    ms : MasterSet
        The master set to render.
    figsize : tuple of float, optional
        Width and height in inches.
    node_size : int, optional
        Base node diameter.
    text_size : int, optional
        Font size for labels.
    show_labels : bool, optional
        Whether to display labels (title generation only).
    title : str or None, optional
        Scene title.  Auto-generated when ``None``.
    override_positions : dict or None, optional
        Pre-computed 3D positions to use instead of ``ms.positions``.
    preview_engine : str, optional
        Default audio engine for click-to-play.
    preview_config : dict or None, optional
        Click-to-play configuration (``dur``, ``amp``, ``defName``,
        ``engine``).
    nodes : list or None, optional
        Alias labels to highlight.
    path : list or None, optional
        Alias labels defining a traversal path.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes when a path/nodes selection is active.

    Returns
    -------
    ThreejsLatticeData
        Three.js scene description and metadata.
    """
    positions = override_positions if override_positions is not None else ms.positions
    edge_pairs = ms.edges
    nd = ms.node_data()

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    has_path = path and len(path) >= 2
    highlight_set = set(nodes) if nodes else set()
    path_set = set(path) if path else set()
    has_selection = bool(highlight_set) or has_path
    use_dimmed = mute_background and has_selection

    def _as_xyz(p):
        x = float(p[0]) if len(p) > 0 else 0.0
        y = float(p[1]) if len(p) > 1 else 0.0
        z = float(p[2]) if len(p) > 2 else 0.0
        return x, y, z

    highlight_edges = []
    grid_edges = []
    for fr, to in edge_pairs:
        if fr in positions and to in positions:
            x1, y1, z1 = _as_xyz(positions[fr])
            x2, y2, z2 = _as_xyz(positions[to])
            edge = [x1, y1, z1, x2, y2, z2]
            if fr in highlight_set and to in highlight_set:
                highlight_edges.append(edge)
            else:
                grid_edges.append(edge)

    sorted_labels = sorted(positions)
    scene_nodes = []
    node_colors = []
    hover_data = []
    node_freqs = []
    is_active_list = []
    ref_freq = 261.63
    dimmed_color_hex = '#555555'

    label_to_idx = {}
    for i, label in enumerate(sorted_labels):
        x, y, z = _as_xyz(positions[label])
        scene_nodes.append([x, y, z])
        label_to_idx[label] = i

        info = nd.get(label, {})
        parts = [f"Alias: {label}"]
        if 'factor' in info:
            parts.append(f"Factor: {info['factor']}")
            parts.append(f"Ratio: {info['ratio']}")
            try:
                node_freqs.append(ref_freq * float(info['ratio']))
            except (TypeError, ValueError):
                node_freqs.append(ref_freq)
        else:
            node_freqs.append(ref_freq)
        hover_data.append('\n'.join(parts))

        if label in path_set:
            node_colors.append('#ffffff')
            is_active_list.append(True)
        elif label in highlight_set:
            node_colors.append('#90EE90')
            is_active_list.append(True)
        elif use_dimmed:
            node_colors.append(dimmed_color_hex)
            is_active_list.append(False)
        else:
            node_colors.append('#ffffff')
            is_active_list.append(not has_selection)

    if not scene_nodes:
        scene_nodes = [[0.0, 0.0, 0.0]]
        node_colors = ['#ffffff']
        hover_data = ['(empty)']
        node_freqs = [ref_freq]
        is_active_list = [True]

    path_steps = []
    halo_data = None
    path_node_indices = []
    path_node_colors = []

    if has_path:
        colors = _path_color_array(path_cmap, len(path) - 1)

        for i in range(len(path) - 1):
            a, b = path[i], path[i + 1]
            if a not in positions or b not in positions:
                path_steps.append(None)
                continue
            x1, y1, z1 = _as_xyz(positions[a])
            x2, y2, z2 = _as_xyz(positions[b])
            hex_color = _rgba_to_hex(colors[i])
            polyline = [[x1, y1, z1], [x2, y2, z2]]
            mid = [(x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2]
            direction = [x2 - x1, y2 - y1, z2 - z1]
            path_steps.append({
                'polyline': polyline,
                'color': hex_color,
                'arrow_pos': mid,
                'arrow_dir': direction,
            })

        for k, label in enumerate(path):
            idx = label_to_idx.get(label, -1)
            path_node_indices.append(idx)
            step_color = _rgba_to_hex(colors[0]) if k == 0 else _rgba_to_hex(colors[k - 1])
            path_node_colors.append(step_color)
            if idx >= 0 and idx < len(node_colors):
                node_colors[idx] = step_color

        start_idx = label_to_idx.get(path[0], -1)
        end_idx = label_to_idx.get(path[-1], -1)
        if start_idx >= 0 and end_idx >= 0:
            halo_data = {
                'start': {
                    'pos': scene_nodes[start_idx],
                    'color': _rgba_to_hex(colors[0]),
                },
                'end': {
                    'pos': scene_nodes[end_idx],
                    'color': _rgba_to_hex(colors[-1]),
                },
            }

    xs = [n[0] for n in scene_nodes]
    ys = [n[1] for n in scene_nodes]
    zs = [n[2] for n in scene_nodes]
    pad_frac = 0.08
    x_span = (max(xs) - min(xs)) or 1.0
    y_span = (max(ys) - min(ys)) or 1.0
    z_span = (max(zs) - min(zs)) or 1.0

    if title is None:
        title = f"MasterSet: {ms.name or 'unnamed'}"

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
        'hoverData': hover_data,
        'nodeFreqs': node_freqs if preview_config else None,
        'isActive': is_active_list if has_selection else None,
        'axisConfig': {
            'xRange': [min(xs) - x_span * pad_frac, max(xs) + x_span * pad_frac],
            'yRange': [min(ys) - y_span * pad_frac, max(ys) + y_span * pad_frac],
            'zRange': [min(zs) - z_span * pad_frac, max(zs) + z_span * pad_frac],
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
