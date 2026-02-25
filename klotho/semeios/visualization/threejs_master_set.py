from .threejs_lattice import ThreejsLatticeData


def _threejs_master_set_3d(ms, figsize=(12, 12), node_size=30, text_size=12,
                           show_labels=True, title=None, override_positions=None):
    positions = override_positions if override_positions is not None else ms.positions
    edge_pairs = ms.edges
    nd = ms.node_data()

    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    grid_edges = []
    for fr, to in edge_pairs:
        if fr in positions and to in positions:
            x1, y1, z1 = positions[fr]
            x2, y2, z2 = positions[to]
            grid_edges.append([float(x1), float(y1), float(z1),
                               float(x2), float(y2), float(z2)])

    scene_nodes = []
    node_colors = []
    hover_data = []
    sorted_labels = sorted(positions)
    for i, label in enumerate(sorted_labels):
        pos = positions[label]
        scene_nodes.append([float(pos[0]), float(pos[1]), float(pos[2])])
        node_colors.append('#ffffff')
        info = nd.get(label, {})
        parts = [f"Alias: {label}"]
        if 'factor' in info:
            parts.append(f"Factor: {info['factor']}")
            parts.append(f"Ratio: {info['ratio']}")
        hover_data.append('\n'.join(parts))

    if not scene_nodes:
        scene_nodes = [[0, 0, 0]]
        node_colors = ['#ffffff']
        hover_data = ['(empty)']

    xs = [n[0] for n in scene_nodes]
    ys = [n[1] for n in scene_nodes]
    zs = [n[2] for n in scene_nodes]
    pad_frac = 0.15
    x_span = (max(xs) - min(xs)) or 1.0
    y_span = (max(ys) - min(ys)) or 1.0
    z_span = (max(zs) - min(zs)) or 1.0

    if title is None:
        title = f"MasterSet: {ms.name or 'unnamed'}"

    scene_data = {
        'gridEdges': grid_edges,
        'gridEdgeColor': '#808080',
        'highlightEdges': [],
        'nodes': scene_nodes,
        'nodeColors': node_colors,
        'nodeSize': 2,
        'dimmedNodeColor': '#555555',
        'pathNodeIndices': [],
        'pathNodeColors': [],
        'hoverData': hover_data,
        'axisConfig': {
            'xRange': [min(xs) - x_span * pad_frac, max(xs) + x_span * pad_frac],
            'yRange': [min(ys) - y_span * pad_frac, max(ys) + y_span * pad_frac],
            'zRange': [min(zs) - z_span * pad_frac, max(zs) + z_span * pad_frac],
            'xTicks': [],
            'yTicks': [],
            'zTicks': [],
            'labels': ['', '', ''],
        },
    }

    return ThreejsLatticeData(
        scene_data=scene_data,
        path_steps=[],
        halo_data=None,
        title=title,
        width_px=width_px,
        height_px=height_px,
    )
