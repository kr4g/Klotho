import math
import numpy as np

from klotho.tonos.systems.combination_product_sets import CombinationProductSet, MasterSet
from klotho.tonos.systems.combination_product_sets.master_set import MASTER_SETS

from .._projections import apply_projection
from ._klotho_plot import transport_kwargs
from .._shared.audio_ref import reference_freq


def _plot_master_set(ms, figsize=(12, 12), node_size=30, text_size=12,
                     show_labels=True, title=None, output_file=None,
                     dim_reduction='mds', nodes=None, path=None,
                     path_cmap='viridis', mute_background=False,
                     animate=False, dur=0.5, shape=None,
                     arp=False, strum=0, direction='u', amp=None,
                     trail=False, **kwargs):
    """
    Render a MasterSet as a 2D SVG or 3D Three.js network diagram.

    Automatically chooses a 3D renderer when the master set has three or
    more effective dimensions, falling back to 2D SVG otherwise.
    High-dimensional positions are reduced via ``dim_reduction``.
    Supports the full CPS plotting surface (``path``, ``shape``,
    ``nodes``, ``animate``, click-to-play).

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
    dim_reduction : str, optional
        Projection method used when ``ms.dimensionality > 3``. One of
        ``'mds'`` (default), ``'pca'``, ``'ortho_best'``, or
        ``'ortho_first'``.
    nodes : list or None, optional
        Alias labels to highlight.
    path : list or None, optional
        Alias labels defining a traversal path through the MasterSet.
    path_cmap : str, optional
        Matplotlib colormap name for path edge colouring.
    mute_background : bool, optional
        Dim non-selected nodes when a path or shape is active.
    animate : bool, optional
        Return an animated figure with playback controls when ``True``.
    dur : float, optional
        Seconds between animation steps.
    shape : list or None, optional
        Alias labels (a chord) or list of lists (chord sequence).
    arp : bool, optional
        Arpeggiate chord notes sequentially instead of block chord.
    strum : float, optional
        Strum offset (0--1) for per-note timing in a chord.
    direction : str, optional
        ``'u'`` for ascending or ``'d'`` for descending pitch order.
    amp : float or None, optional
        Amplitude for playback.

    Returns
    -------
    SvgMasterSetData, ThreejsLatticeData, or animated figure
        Renderable figure data.
    """
    from .plot_lattice import (
        _prepare_plot_audio, _normalize_shape_groups, _resolve_chord_shape,
        _ratio_freqs, _animated_path_figure, _animated_shape_figure,
    )

    dim = ms.dimensionality
    override_positions = None
    if dim > 3:
        override_positions = _reduce_positions(
            ms.positions, target_dims=3, dim_reduction=dim_reduction)
        dim = 3
    is_3d = dim == 3

    engine_name, preview_def_name, animate_preview_config, extra_synth_kwargs = (
        _prepare_plot_audio(kwargs, dur, amp, animate))

    chord_freq_groups = None
    resolved = _resolve_chord_shape(ms, shape)
    if resolved is not None:
        shape_groups, chord_freq_groups = resolved
        shape = shape_groups
    else:
        shape_groups = _normalize_shape_groups(shape)
    has_shape = len(shape_groups) > 0

    def _render_2d(**extra):
        from .._renderers.svg_master_set import _svg_master_set_2d
        return _svg_master_set_2d(
            ms, figsize=figsize, node_size=node_size, text_size=text_size,
            show_labels=show_labels, title=title,
            nodes=nodes, path=path, path_cmap=path_cmap,
            mute_background=mute_background,
            preview_config=animate_preview_config, **extra)

    def _render_3d(**extra):
        from .._renderers.threejs_master_set import _threejs_master_set_3d
        return _threejs_master_set_3d(
            ms, figsize=figsize, node_size=node_size, text_size=text_size,
            show_labels=show_labels, title=title,
            override_positions=override_positions,
            preview_engine=engine_name, preview_config=animate_preview_config,
            nodes=nodes, path_cmap=path_cmap,
            mute_background=mute_background, **extra)

    nd = ms.node_data()

    def _label_ratio(label):
        return nd.get(label, {}).get('ratio')

    if animate and path and len(path) > 1:
        freqs = _ratio_freqs(path, _label_ratio, reference_freq(ms))
        return _animated_path_figure(
            freqs, is_3d, _render_2d, lambda: _render_3d(path=path),
            dur, amp, extra_synth_kwargs, preview_def_name, engine_name, kwargs)

    if animate and has_shape:
        freq_groups = (chord_freq_groups if chord_freq_groups is not None
                       else [_ratio_freqs(group, _label_ratio, reference_freq(ms))
                             for group in shape_groups])
        return _animated_shape_figure(
            freq_groups, is_3d,
            lambda: _render_2d(shape=shape),
            lambda: _render_3d(shape=shape_groups),
            dur, arp, strum, direction, amp, extra_synth_kwargs,
            preview_def_name, engine_name, kwargs, trail=trail)

    if is_3d:
        static_fig = _render_3d(path=path, shape=shape_groups if has_shape else None)
    else:
        static_fig = _render_2d(shape=shape)

    if animate:
        from .._animation import ClickPreviewFigure
        return ClickPreviewFigure(static_fig, def_name=preview_def_name,
                                  engine=engine_name)
    return static_fig


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


def _reduce_positions(node_positions, target_dims=3, dim_reduction='mds'):
    """
    Reduce high-dimensional node positions to ``target_dims``.

    Parameters
    ----------
    node_positions : dict
        Mapping of node IDs to coordinate tuples.
    target_dims : int, optional
        Number of output dimensions (default 3).
    dim_reduction : str, optional
        One of ``'mds'`` (default), ``'pca'``, ``'ortho_best'``,
        or ``'ortho_first'``.

    Returns
    -------
    dict
        Mapping of node IDs to reduced-dimension coordinate tuples.
    """
    nodes = list(node_positions.keys())
    coords = np.array([list(node_positions[n]) for n in nodes])
    reduced = apply_projection(coords, dim_reduction, target_dims=target_dims)
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



def _cps_scale_run(cps, equaves=1):
    """Build the default ``plot(cps).play()`` scale run.

    Returns ``(freqs, node_ids)``: the frequencies of the CPS collection
    played up ``equaves`` equaves and back down (mirroring
    ``scale_pitch_sequence``), and for each step the graph node whose
    equave-reduced ratio sounds — so octave-equivalent steps select the
    same node. Returns None for an empty CPS.
    """
    collection = cps.collection
    n = len(collection)
    if n == 0:
        return None
    eq = int(equaves) if equaves else 1
    abs_eq = abs(eq) or 1
    idxs = list(range(abs_eq * n + 1))
    if eq < 0:
        idxs = [-i for i in idxs]
    idxs = idxs + idxs[-2::-1]
    freqs = [float(collection[i].freq) for i in idxs]

    ratios = list(cps.ratios)
    ratio_to_node = {}
    for node, attrs in cps.nodes(data=True):
        r = attrs.get('ratio')
        if r is not None and r not in ratio_to_node:
            ratio_to_node[r] = node
    node_ids = [ratio_to_node.get(ratios[i % n]) for i in idxs]
    return freqs, node_ids


def _cps_render_node_order(G, node_positions):
    """Graph node ids in renderer order.

    Both ``_svg_cps`` and ``_threejs_cps_3d`` iterate ``G.nodes(data=True)``
    and skip nodes without a position or ``combo``; this must mirror that
    filter so select-step indices line up with rendered node indices.
    """
    return [node for node, attrs in G.nodes(data=True)
            if node in node_positions and 'combo' in attrs]


def _plot_cps(cps: CombinationProductSet, figsize: tuple = (12, 12),
             node_size: int = 30, text_size: int = 12, show_labels: bool = True,
             title: str = None, output_file: str = None, nodes: list = None,
             path: list = None, path_cmap: str = 'viridis',
             mute_background: bool = False,
             animate: bool = False, dur: float = 0.5,
             shape: list = None,
             arp: bool = False, strum: float = 0, direction: str = 'u',
             amp: float = None, dim_reduction: str = 'mds',
             equaves: int = 1, trail=False, **kwargs):
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
    dim_reduction : str, optional
        Projection method used when the CPS's master-set positions live
        in more than 3 dimensions. One of ``'mds'`` (default), ``'pca'``,
        ``'ortho_best'``, or ``'ortho_first'``.
    equaves : int, optional
        For the default ``.play()`` (no ``path``/``shape``): how many
        equaves the scale run ascends before descending. Default is 1.

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
    
    G = cps
    node_positions = cps.positions if hasattr(cps, 'positions') else _cps_node_positions(G)

    pos_dim = max((len(p) for p in node_positions.values()), default=2)
    if pos_dim > 3:
        node_positions = _reduce_positions(
            node_positions, target_dims=3, dim_reduction=dim_reduction)
        pos_dim = 3
    is_3d = pos_dim >= 3 and any(abs(p[2]) > 1e-12 for p in node_positions.values())

    from .plot_lattice import (
        _prepare_plot_audio, _normalize_shape_groups, _resolve_chord_shape,
        _ratio_freqs, _animated_path_figure, _animated_shape_figure,
        _path_audio_payload,
    )

    engine_name, preview_def_name, animate_preview_config, extra_synth_kwargs = (
        _prepare_plot_audio(kwargs, dur, amp, animate))

    chord_freq_groups = None
    resolved = _resolve_chord_shape(cps, shape)
    if resolved is not None:
        shape_groups, chord_freq_groups = resolved
        shape = shape_groups
    else:
        shape_groups = _normalize_shape_groups(shape)
    has_shape = len(shape_groups) > 0

    def _render_2d(**extra):
        from .._renderers.svg_cps import _svg_cps
        return _svg_cps(cps, node_positions, path=path, path_cmap=path_cmap,
                        mute_background=mute_background, figsize=figsize,
                        node_size=node_size, text_size=text_size,
                        show_labels=show_labels, title=title,
                        preview_config=animate_preview_config, **extra)

    def _render_3d(**extra):
        from .._renderers.threejs_cps import _threejs_cps_3d
        return _threejs_cps_3d(
            cps, node_positions, G, figsize=figsize,
            node_size=node_size, text_size=text_size,
            show_labels=show_labels, title=title, nodes=nodes,
            mute_background=mute_background,
            preview_engine=engine_name,
            preview_config=animate_preview_config, **extra)

    def _node_ratio(node_id):
        return G.nodes[node_id]['ratio']

    if animate and path:
        freqs = _ratio_freqs(path, _node_ratio, reference_freq(cps))
        return _animated_path_figure(
            freqs, is_3d, _render_2d, lambda: _render_3d(path=path, path_cmap=path_cmap),
            dur, amp, extra_synth_kwargs, preview_def_name, engine_name, kwargs)

    if animate and has_shape:
        freq_groups = (chord_freq_groups if chord_freq_groups is not None
                       else [_ratio_freqs(group, _node_ratio, reference_freq(cps))
                             for group in shape_groups])
        return _animated_shape_figure(
            freq_groups, is_3d,
            lambda: _render_2d(shape=shape),
            lambda: _render_3d(shape=shape_groups),
            dur, arp, strum, direction, amp, extra_synth_kwargs,
            preview_def_name, engine_name, kwargs, trail=trail)

    # Default play (no path/shape): the CPS "scale" — sorted ratios up
    # `equaves` equaves and back down — selecting each sounding node the
    # way a mouse click does.
    if animate:
        run = _cps_scale_run(cps, equaves)
        if run is not None:
            freqs, run_node_ids = run
            audio_payload = _path_audio_payload(
                freqs, dur, amp, extra_synth_kwargs, preview_def_name,
                engine_name, kwargs)
            node_order = _cps_render_node_order(G, node_positions)
            select_indices = [
                node_order.index(nid) if nid in node_order else -1
                for nid in run_node_ids
            ]

            if is_3d:
                from .._animation import AnimatedLattice3dSelectFigure
                threejs_data = _render_3d()
                threejs_data.scene_data['selectNodeIndices'] = select_indices
                return AnimatedLattice3dSelectFigure(
                    threejs_data, audio_payload=audio_payload, dur=dur,
                    **transport_kwargs(kwargs),
                )

            from .._animation import AnimatedNodeSelectSvgFigure
            return AnimatedNodeSelectSvgFigure(
                _render_2d(), select_indices,
                audio_payload=audio_payload, dur=dur,
                **transport_kwargs(kwargs),
            )

    if is_3d:
        static_fig = _render_3d(path=path, path_cmap=path_cmap,
                                shape=shape_groups if has_shape else None)
    else:
        static_fig = _render_2d(shape=shape)

    if animate:
        from .._animation import ClickPreviewFigure
        return ClickPreviewFigure(static_fig, def_name=preview_def_name,
                                  engine=engine_name)
    return static_fig

