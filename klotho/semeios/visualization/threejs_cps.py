import math
from .threejs_lattice import ThreejsLatticeData


def _threejs_cps_3d(cps, node_positions, G, figsize=(12, 12),
                    node_size=30, text_size=12, show_labels=True,
                    title=None, nodes=None):
    width_px = int(figsize[0] * 100)
    height_px = int(figsize[1] * 100)

    highlight_set = set(nodes) if nodes else set()

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
    for node, attrs in G.nodes(data=True):
        if node not in node_positions or 'combo' not in attrs:
            continue
        x, y, z = node_positions[node]
        scene_nodes.append([float(x), float(y), float(z)])

        combo = attrs['combo']
        label = ''.join(str(cps.factor_to_alias[f]).strip('()') for f in combo)
        combo_str = '(' + ' '.join(str(f) for f in combo) + ')'
        hover_data.append(
            f"Node: {node}\nAlias: {label}\nCombo: {combo_str}\n"
            f"Product: {attrs['product']}\nRatio: {attrs['ratio']}"
        )

        if node in highlight_set:
            node_colors.append('#90EE90')
        else:
            node_colors.append('#ffffff')

    if not scene_nodes:
        scene_nodes = [[0, 0, 0]]
        node_colors = ['#ffffff']
        hover_data = ['(empty)']

    xs = [n[0] for n in scene_nodes]
    ys = [n[1] for n in scene_nodes]
    zs = [n[2] for n in scene_nodes]
    pad = 0.15
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
        'dimmedNodeColor': '#555555',
        'pathNodeIndices': [],
        'pathNodeColors': [],
        'hoverData': hover_data,
        'axisConfig': {
            'xRange': [min(xs) - x_span * pad, max(xs) + x_span * pad],
            'yRange': [min(ys) - y_span * pad, max(ys) + y_span * pad],
            'zRange': [min(zs) - z_span * pad, max(zs) + z_span * pad],
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
