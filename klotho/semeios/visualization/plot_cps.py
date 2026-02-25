import math
import numpy as np

from klotho.tonos.systems.combination_product_sets import CombinationProductSet, MasterSet
from klotho.tonos.systems.combination_product_sets.master_set import MASTER_SETS


def _plot_master_set(ms, figsize=(12, 12), node_size=30, text_size=12,
                     show_labels=True, title=None, output_file=None):
    """
    Render a MasterSet as a 2D SVG or 3D Three.js network diagram.

    Automatically chooses a 3D renderer when the master set has three or
    more effective dimensions, falling back to 2D SVG otherwise.
    High-dimensional positions are reduced via MDS.

    Parameters
    ----------
    ms : MasterSet
        MasterSet instance to visualize.
    figsize : tuple of float, optional
        Width and height of the figure in inches.
    node_size : int, optional
        Diameter of the rendered nodes.
    text_size : int, optional
        Font size for node labels.
    show_labels : bool, optional
        Whether to display labels on nodes.
    title : str or None, optional
        Plot title.  Auto-generated when ``None``.
    output_file : str or None, optional
        Path to save the figure.

    Returns
    -------
    SvgMasterSetData or ThreejsLatticeData
        Renderable figure data.
    """
    dim = ms.dimensionality
    override_positions = None
    if dim > 3:
        from klotho.semeios.visualization.plots import _reduce_positions
        override_positions = _reduce_positions(ms.positions, target_dims=3)
        dim = 3
    is_3d = dim == 3

    if is_3d:
        from .threejs_master_set import _threejs_master_set_3d
        return _threejs_master_set_3d(ms, figsize=figsize, node_size=node_size,
                                      text_size=text_size, show_labels=show_labels,
                                      title=title,
                                      override_positions=override_positions)
    else:
        from .svg_master_set import _svg_master_set_2d
        return _svg_master_set_2d(ms, figsize=figsize, node_size=node_size,
                                  text_size=text_size, show_labels=show_labels,
                                  title=title)


def _detect_faces(G, node_positions, max_size=8):
    """
    Detect chordless cycles (faces) in a planar CPS graph.

    Parameters
    ----------
    G : Graph
        CPS graph with ``'distance'`` edge attributes.
    node_positions : dict
        Mapping of node IDs to coordinate tuples.
    max_size : int, optional
        Maximum cycle length to search for.

    Returns
    -------
    list of tuple
        Each tuple contains the node IDs forming a detected face.
    """
    adj = {}
    for u, v, data in G.edges(data=True):
        if u in node_positions and v in node_positions and 'distance' in data:
            adj.setdefault(u, set()).add(v)
            adj.setdefault(v, set()).add(u)

    all_nodes = sorted(n for n in G.nodes() if n in node_positions)
    found = []
    seen_sets = set()

    for a, b, c in _combinations(all_nodes, 3):
        if b in adj.get(a, set()) and c in adj.get(b, set()) and a in adj.get(c, set()):
            found.append((a, b, c))
            seen_sets.add(frozenset((a, b, c)))

    if max_size >= 4:
        for cycle_len in range(4, max_size + 1):
            for subset in _combinations(all_nodes, cycle_len):
                fs = frozenset(subset)
                if fs in seen_sets:
                    continue
                subset_set = set(subset)
                sub_adj = {n: adj.get(n, set()) & subset_set for n in subset}
                if any(len(nb) != 2 for nb in sub_adj.values()):
                    continue
                start = subset[0]
                visited = {start}
                cycle = [start]
                current = start
                valid = True
                for _ in range(cycle_len - 1):
                    nxt = [n for n in sub_adj[current] if n not in visited]
                    if not nxt:
                        valid = False
                        break
                    current = nxt[0]
                    visited.add(current)
                    cycle.append(current)
                if not valid or len(cycle) != cycle_len or start not in sub_adj[cycle[-1]]:
                    continue
                cycle_set = set(cycle)
                has_chord = False
                for i, node in enumerate(cycle):
                    non_neighbors_in_cycle = adj.get(node, set()) & cycle_set - {cycle[(i-1) % cycle_len], cycle[(i+1) % cycle_len]}
                    if non_neighbors_in_cycle:
                        has_chord = True
                        break
                if not has_chord:
                    seen_sets.add(fs)
                    found.append(tuple(cycle))

    return found


_FACE_COLORS = [
    'rgba(65,105,225,0.18)',
    'rgba(220,60,60,0.18)',
    'rgba(50,205,50,0.18)',
    'rgba(255,165,0,0.18)',
    'rgba(148,103,189,0.18)',
    'rgba(0,206,209,0.18)',
    'rgba(255,105,180,0.18)',
    'rgba(255,215,0,0.18)',
]


def _reduce_positions(node_positions, target_dims=3):
    """
    Reduce high-dimensional node positions via MDS.

    Parameters
    ----------
    node_positions : dict
        Mapping of node IDs to coordinate tuples.
    target_dims : int, optional
        Number of output dimensions (default 3).

    Returns
    -------
    dict
        Mapping of node IDs to reduced-dimension coordinate tuples.
    """
    from sklearn.manifold import MDS
    nodes = list(node_positions.keys())
    coords = np.array([list(node_positions[n]) for n in nodes])
    reducer = MDS(n_components=target_dims, random_state=42, normalized_stress='auto')
    reduced = reducer.fit_transform(coords)
    return {nodes[i]: tuple(reduced[i]) for i in range(len(nodes))}


def _cps_node_positions(G):
    """
    Compute spatial positions for CPS graph nodes from edge geometry.

    Traverses connected components of *G* using BFS, accumulating
    positions from angle, distance, and displacement edge attributes.

    Parameters
    ----------
    G : Graph
        CPS graph whose edges carry ``'angle'``, ``'distance'``, and
        optionally ``'elevation'`` / ``'displacement'`` attributes.

    Returns
    -------
    dict
        Mapping of node IDs to position tuples.
    """
    node_neighbors = {}
    n_dims = 2
    for u, v, data in G.edges(data=True):
        if 'angle' in data and 'distance' in data:
            disp = data.get('displacement')
            if disp is not None and len(disp) > n_dims:
                n_dims = len(disp)
            elev = data.get('elevation', 0.0) or 0.0
            if abs(elev) > 1e-12 and n_dims < 3:
                n_dims = 3
            node_neighbors.setdefault(u, []).append({
                'nb': v, 'angle': data['angle'], 'distance': data['distance'],
                'elevation': elev, 'displacement': disp,
            })

    node_positions = {}

    nx_graph = G.to_networkx()
    components = list(nx.strongly_connected_components(nx_graph))

    for component in components:
        start_node = next(iter(component))
        pos = {start_node: tuple(0.0 for _ in range(n_dims))}
        placed = {start_node}
        queue = [start_node]

        while queue:
            current = queue.pop(0)
            for edge_data in node_neighbors.get(current, []):
                nb = edge_data['nb']
                if nb not in placed and nb in component:
                    cur_pos = pos[current]
                    disp = edge_data['displacement']
                    if disp is not None and len(disp) >= n_dims:
                        pos[nb] = tuple(cur_pos[i] + disp[i] for i in range(n_dims))
                    elif n_dims == 3:
                        angle = edge_data['angle']
                        dist = edge_data['distance']
                        elev = edge_data['elevation']
                        horiz_dist = dist * math.cos(elev)
                        pos[nb] = (cur_pos[0] + horiz_dist * math.cos(angle),
                                   cur_pos[1] + horiz_dist * math.sin(angle),
                                   cur_pos[2] + dist * math.sin(elev))
                    else:
                        angle = edge_data['angle']
                        dist = edge_data['distance']
                        pos[nb] = (cur_pos[0] + dist * math.cos(angle),
                                   cur_pos[1] + dist * math.sin(angle))
                    placed.add(nb)
                    queue.append(nb)

        if pos:
            n_pos = len(pos)
            center = tuple(sum(p[i] for p in pos.values()) / n_pos for i in range(n_dims))
            for n in pos:
                pos[n] = tuple(pos[n][i] - center[i] for i in range(n_dims))

        node_positions.update(pos)

    return node_positions



def _plot_cps(cps: CombinationProductSet, figsize: tuple = (12, 12), 
             node_size: int = 30, text_size: int = 12, show_labels: bool = True,
             title: str = None, output_file: str = None, nodes: list = None,
             path: list = None, path_cmap: str = 'viridis',
             mute_background: bool = False,
             animate: bool = False, dur: float = 0.5,
             shape: list = None,
             arp: bool = False, strum: float = 0, direction: str = 'u'):
    """
    Render a Combination Product Set as an interactive network diagram.

    Positions are derived from the CPS master set geometry.  When the
    effective dimensionality is 3 or higher a Three.js scene is returned;
    otherwise an SVG figure is produced.

    Parameters
    ----------
    cps : CombinationProductSet
        CPS instance to visualize (must have a ``master_set`` defined).
    figsize : tuple of float, optional
        Width and height of the figure in inches.
    node_size : int, optional
        Diameter of the rendered nodes.
    text_size : int, optional
        Font size for node labels.
    show_labels : bool, optional
        Whether to display labels on nodes.
    title : str or None, optional
        Plot title.  Derived from the CPS when ``None``.
    output_file : str or None, optional
        Path to save the figure.
    nodes : list or None, optional
        Node IDs to highlight in pale green.
    path : list or None, optional
        Node IDs defining a traversal path through the CPS graph.
    path_cmap : str, optional
        Matplotlib colormap name for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes when a path or shape is active.
    animate : bool, optional
        Return an animated figure with playback controls when ``True``.
    dur : float, optional
        Seconds between animation steps.
    shape : list or None, optional
        Node IDs (a chord) or list of lists (chord sequence).
        Highlights nodes and draws edges between adjacent members.
    arp : bool, optional
        Arpeggiate chord notes sequentially instead of block chord.
    strum : float, optional
        Strum offset (0--1) for per-note timing in a chord.
    direction : str, optional
        ``'u'`` for ascending or ``'d'`` for descending pitch order.

    Returns
    -------
    SvgCPSData, ThreejsLatticeData, or animated figure
        Renderable figure data.
    """
    master_set_name = cps.master_set
    if not master_set_name:
        raise ValueError(
            f"CPS instance has no master set defined. plot() requires a master set for node positioning.\n"
            f"Available master sets: {list(MASTER_SETS.keys())}\n"
            f"Try using CPS presets like CombinationProductSet.hexany() or CombinationProductSet.eikosany(), "
            f"or pass a master_set parameter: CombinationProductSet(factors, r, master_set='tetrad')"
        )
    if master_set_name not in MASTER_SETS:
        raise ValueError(f"Invalid master set name: {master_set_name}. Must be one of {list(MASTER_SETS.keys())}")
    
    G = cps.graph
    node_positions = cps.positions if hasattr(cps, 'positions') else _cps_node_positions(G)

    pos_dim = max((len(p) for p in node_positions.values()), default=2)
    if pos_dim > 3:
        node_positions = _reduce_positions(node_positions, target_dims=3)
        pos_dim = 3
    is_3d = pos_dim >= 3 and any(abs(p[2]) > 1e-12 for p in node_positions.values())
    if is_3d:
        from .threejs_cps import _threejs_cps_3d
        return _threejs_cps_3d(cps, node_positions, G, figsize=figsize,
                               node_size=node_size, text_size=text_size,
                               show_labels=show_labels, title=title, nodes=nodes)

    if animate and path:
        from .svg_cps import _svg_cps
        from .animated import AnimatedCPSSvgFigure
        from klotho.utils.playback.tonejs.converters import freq_to_velocity
        svg_data = _svg_cps(cps, node_positions, path=path, path_cmap=path_cmap,
                            mute_background=mute_background, figsize=figsize,
                            node_size=node_size, text_size=text_size,
                            show_labels=show_labels, title=title)
        ref_freq = 261.63
        audio_events = []
        for i, node_id in enumerate(path):
            try:
                ratio = float(G.nodes[node_id]['ratio'])
                freq = ref_freq * ratio
            except Exception:
                freq = ref_freq
            audio_events.append({
                "start": round(i * dur, 6),
                "duration": round(dur * 0.9, 6),
                "instrument": "synth",
                "pfields": {"freq": round(freq, 4), "vel": round(freq_to_velocity(freq, 0.5), 4)},
                "_stepIndex": i,
            })
        audio_payload = {"events": audio_events, "instruments": {}}
        return AnimatedCPSSvgFigure(svg_data, audio_payload=audio_payload, dur=dur)

    if shape is not None and len(shape) > 0:
        if isinstance(shape[0], (list, tuple)):
            shape_groups = [list(g) for g in shape]
        else:
            shape_groups = [list(shape)]

        if animate:
            from .svg_cps import _svg_cps
            from .animated import AnimatedCPSShapeFigure
            from klotho.utils.playback.tonejs.converters import freq_to_velocity
            svg_data = _svg_cps(cps, node_positions, path=path, path_cmap=path_cmap,
                                mute_background=mute_background, figsize=figsize,
                                node_size=node_size, text_size=text_size,
                                show_labels=show_labels, title=title,
                                shape=shape)
            ref_freq = 261.63
            audio_events = []
            current_time = 0.0

            for gi, group in enumerate(shape_groups):
                freqs = []
                for node_id in group:
                    try:
                        ratio = float(G.nodes[node_id]['ratio'])
                        freqs.append(ref_freq * ratio)
                    except Exception:
                        freqs.append(ref_freq)
                if direction.lower() == 'd':
                    freqs = list(reversed(freqs))

                if arp:
                    note_dur = dur
                    for i, freq in enumerate(freqs):
                        audio_events.append({
                            "start": round(current_time + i * note_dur, 6),
                            "duration": round(note_dur * 0.9, 6),
                            "instrument": "synth",
                            "pfields": {"freq": round(freq, 4), "vel": round(freq_to_velocity(freq, 0.5), 4)},
                            "_stepIndex": gi,
                        })
                    current_time += len(freqs) * note_dur
                else:
                    chord_dur = dur
                    num_notes = len(freqs)
                    strum_val = max(0, min(1, strum))
                    for i, freq in enumerate(freqs):
                        start_offset = (strum_val * chord_dur * i) / num_notes if num_notes > 1 else 0
                        audio_events.append({
                            "start": round(current_time + start_offset, 6),
                            "duration": round((chord_dur * 0.95) - start_offset, 6),
                            "instrument": "synth",
                            "pfields": {"freq": round(freq, 4), "vel": round(freq_to_velocity(freq, 0.5), 4)},
                            "_stepIndex": gi,
                        })
                    current_time += chord_dur

            audio_payload = {"events": audio_events, "instruments": {}}
            return AnimatedCPSShapeFigure(svg_data, audio_payload=audio_payload, dur=dur)

    from .svg_cps import _svg_cps
    return _svg_cps(cps, node_positions, path=path, path_cmap=path_cmap,
                    mute_background=mute_background, figsize=figsize,
                    node_size=node_size, text_size=text_size,
                    show_labels=show_labels, title=title, shape=shape)

