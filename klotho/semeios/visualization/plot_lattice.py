import math
import numpy as np
import networkx as nx
from sklearn.manifold import MDS, SpectralEmbedding

from klotho.topos.graphs.lattices import Lattice

from ._colors import SHAPE_COLORS as _SHAPE_COLORS_GLOBAL





def _plot_lattice(lattice: Lattice, figsize: tuple[float, float] = (12, 12),
                 node_size: float = 8, title: str = None, 
                 output_file: str = None, 
                 dim_reduction: str = None, target_dims: int = 3,
                 mds_metric: bool = True, mds_max_iter: int = 300,
                 spectral_affinity: str = 'rbf', spectral_gamma: float = None,
                 nodes: list = None, path: list = None, path_mode: str = 'adjacent',
                 mute_background: bool = False, fit=False, pad: int = 1,
                 path_cmap: str = 'viridis',
                 animate: bool = False, dur: float = 0.5,
                 shape: list = None,
                 arp: bool = False, strum: float = 0, direction: str = 'u',
                 amp: float = None, **kwargs):
    """
    Render a Lattice as a 2D SVG or 3D Three.js grid visualization.

    Supports dimensionality reduction for lattices with more than 3
    dimensions.  Coordinate highlighting, path traversal, and animated
    chord / chord-sequence playback are available as overlays.

    Parameters
    ----------
    lattice : Lattice
        Lattice instance to visualize.
    figsize : tuple of float, optional
        Width and height of the figure in inches.
    node_size : float, optional
        Size of the drawn nodes.
    title : str or None, optional
        Plot title.  Auto-generated when ``None``.
    output_file : str or None, optional
        Path to save the figure.
    dim_reduction : str or None, optional
        ``'mds'``, ``'spectral'``, or ``None`` (raises for dim > 3).
    target_dims : int, optional
        Target dimensions after reduction (2 or 3).
    mds_metric : bool, optional
        Use metric MDS when ``True``.
    mds_max_iter : int, optional
        Maximum MDS iterations.
    spectral_affinity : str, optional
        Kernel for spectral embedding.
    spectral_gamma : float or None, optional
        Kernel coefficient for rbf.
    nodes : list of tuple or None, optional
        Coordinate tuples to highlight.
    path : list of tuple or None, optional
        Coordinate tuples defining a traversal path.
    path_mode : str, optional
        ``'adjacent'`` (default) or ``'origin'``.
    mute_background : bool, optional
        Hide non-selected nodes when ``True``.
    fit : bool or str, optional
        Cropping mode when nodes/path are provided.  ``'rect'`` /
        ``True``, ``'square'``, or ``'tight'``.
    pad : int, optional
        Padding around the selection in each dimension when *fit* is
        active.
    path_cmap : str, optional
        Matplotlib colormap for path edge colouring.
    animate : bool, optional
        Return an animated figure when ``True``.
    dur : float, optional
        Seconds between animation steps.
    shape : list or None, optional
        Coordinate tuples (chord) or list of lists (chord sequence).
    arp : bool, optional
        Arpeggiate chord notes sequentially.
    strum : float, optional
        Per-note timing offset (0--1) in a chord.
    direction : str, optional
        ``'u'`` for ascending or ``'d'`` for descending pitch order.

    Returns
    -------
    SvgLatticeData, ThreejsLatticeData, or animated figure
        Renderable figure data.

    Raises
    ------
    ValueError
        If lattice dimensionality exceeds 3 and *dim_reduction* is
        ``None``.
    """
    import networkx as nx
    
    # Check if this is a ToneLattice for enhanced hover information
    is_tone_lattice = hasattr(lattice, '_coord_to_ratio')
    coord_label = "Coordinate"
    if is_tone_lattice:
        coord_label = getattr(lattice, "coord_label", "Monzo")
    
    # Convert nodes parameter to tuples if needed (safety mechanism for all lattice types)
    if nodes is not None:
        converted_nodes = []
        for node in nodes:
            if isinstance(node, (list, tuple)):
                converted_nodes.append(tuple(node))
            elif hasattr(node, 'tolist'):  # numpy array
                converted_nodes.append(tuple(node.tolist()))
            elif hasattr(node, '__iter__') and not isinstance(node, str):
                converted_nodes.append(tuple(node))
            else:
                converted_nodes.append(node)
        nodes = converted_nodes
    
    # Convert path parameter to tuples if needed (safety mechanism for all lattice types)
    if path is not None:
        converted_path = []
        for coord in path:
            if isinstance(coord, (list, tuple)):
                converted_path.append(tuple(coord))
            elif hasattr(coord, 'tolist'):  # numpy array
                converted_path.append(tuple(coord.tolist()))
            elif hasattr(coord, '__iter__') and not isinstance(coord, str):
                converted_path.append(tuple(coord))
            else:
                converted_path.append(coord)
        path = converted_path
    
    # Validate that all nodes/path coordinates exist in the lattice
    if nodes is not None:
        invalid = [c for c in nodes if c not in lattice]
        if invalid:
            raise ValueError(
                f"The following node coordinates are outside the lattice bounds: {invalid}"
            )
    if path is not None:
        invalid = [c for c in path if c not in lattice]
        if invalid:
            raise ValueError(
                f"The following path coordinates are outside the lattice bounds: {invalid}"
            )

    if lattice.dimensionality > 3 and dim_reduction is None:
        raise ValueError(f"Plotting dimensionality > 3 requires dim_reduction. Got dimensionality={lattice.dimensionality}. "
                        f"Use dim_reduction='mds' or 'spectral'")
    
    if target_dims not in [2, 3]:
        raise ValueError(f"target_dims must be 2 or 3, got {target_dims}")
    
    if lattice.dimensionality <= 2:
        max_resolution = 5
    elif lattice.dimensionality == 3:
        max_resolution = 2
    else:
        if target_dims == 3:
            max_resolution = 1
        else:
            max_resolution = 3
    
    expected_total = 1
    for dim in lattice._dims:
        expected_total *= len(dim)
        if expected_total > 10000:
            expected_total = float('inf')
            break
    
    has_selection = (nodes is not None and len(nodes) > 0) or (path is not None and len(path) > 0)

    fit_mode = None
    if fit is True:
        fit_mode = 'rect'
    elif isinstance(fit, str) and fit in ('rect', 'square', 'tight'):
        fit_mode = fit

    if has_selection and fit_mode:
        import itertools
        all_coords_to_fit = []
        if nodes:
            all_coords_to_fit.extend(nodes)
        if path:
            all_coords_to_fit.extend(path)

        if all_coords_to_fit:
            ndim = lattice.dimensionality
            p = max(0, int(pad))

            if fit_mode == 'tight':
                selection_set = set(all_coords_to_fit)
                neighbor_shell = set()
                for coord in selection_set:
                    for d in range(ndim):
                        for delta in range(-p, p + 1):
                            if delta == 0:
                                continue
                            neighbor = list(coord)
                            neighbor[d] += delta
                            neighbor = tuple(neighbor)
                            if neighbor in lattice:
                                neighbor_shell.add(neighbor)
                coords = sorted(selection_set | neighbor_shell)

            else:
                per_dim_lo = []
                per_dim_hi = []
                for d in range(ndim):
                    vals = [c[d] for c in all_coords_to_fit]
                    per_dim_lo.append(min(vals))
                    per_dim_hi.append(max(vals))

                if fit_mode == 'square':
                    half_spans = [(hi - lo) / 2.0 for lo, hi in zip(per_dim_lo, per_dim_hi)]
                    max_half = max(half_spans)
                    centers = [(lo + hi) / 2.0 for lo, hi in zip(per_dim_lo, per_dim_hi)]
                    for d in range(ndim):
                        per_dim_lo[d] = int(centers[d] - max_half)
                        per_dim_hi[d] = int(centers[d] + max_half) + (1 if (max_half % 1) else 0)

                ranges = []
                for d in range(ndim):
                    lo = max(per_dim_lo[d] - p, min(lattice._dims[d]))
                    hi = min(per_dim_hi[d] + p, max(lattice._dims[d]))
                    ranges.append(range(lo, hi + 1))

                coords = [c for c in itertools.product(*ranges) if c in lattice]
        else:
            coords = lattice.coords

    elif lattice.dimensionality > 3 or lattice._is_lazy or expected_total > 1000:
        # For large lattices, determine plotting area based on path extent if provided
        if path:
            # Calculate the range needed to encompass the entire path
            coord_ranges = []
            for dim in range(lattice.dimensionality):
                dim_vals = [coord[dim] for coord in path if coord in lattice]
                if dim_vals:
                    min_val, max_val = min(dim_vals), max(dim_vals)
                    # Add buffer around path
                    coord_ranges.append((min_val - 2, max_val + 2))
                else:
                    coord_ranges.append((-max_resolution, max_resolution))
            
            # Generate coordinates for the path-encompassing area
            coords = []
            import itertools
            ranges = [range(start, end + 1) for start, end in coord_ranges]
            coords = list(itertools.product(*ranges))
            coords = [coord for coord in coords if coord in lattice]
        else:
            # No path provided, use default reduced coordinates
            coords = lattice._get_plot_coords(max_resolution)
    else:
        coords = lattice.coords
    
    # For reduced coordinate plotting, we need to build a reduced graph
    # to avoid iterating over thousands of edges in the full lattice
    if has_selection or lattice.dimensionality > 3 or lattice._is_lazy or expected_total > 1000:
        G_reduced = nx.Graph()
        coord_set = set(coords)
        G_reduced.add_nodes_from(coords)
        
        ndim = lattice.dimensionality
        for coord in coords:
            for d in range(ndim):
                neighbor = list(coord)
                neighbor[d] += 1
                neighbor = tuple(neighbor)
                if neighbor in coord_set:
                    G_reduced.add_edge(coord, neighbor)
        
        G = G_reduced
    else:
        G = lattice  # Use full lattice for small coordinate sets
    
    # Handle origin inclusion for path_mode='origin' before setting original_coords
    if nodes and path_mode == 'origin':
        origin = tuple(0 for _ in range(lattice.dimensionality))
        if origin not in coords:
            coords.append(origin)
            # Update the reduced graph if we're using one
            if hasattr(G, 'add_node'):
                G.add_node(origin)
                # Add edges from origin to adjacent coordinates
                for coord in coords:
                    if coord != origin:
                        diff_count = sum(1 for a, b in zip(origin, coord) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(origin, coord) if a == b)
                        if diff_count == 1 and same_count == len(coord) - 1:
                            G.add_edge(origin, coord)
    
    original_coords = coords
    
    if lattice.dimensionality > 3:
        coord_matrix = np.array([list(coord) for coord in coords])
        
        if dim_reduction == 'mds':
            reducer = MDS(n_components=target_dims, metric=mds_metric, max_iter=mds_max_iter, random_state=42)
            reduced_coords = reducer.fit_transform(coord_matrix)
        elif dim_reduction == 'spectral':
            if spectral_affinity == 'precomputed':
                coord_to_idx = {coord: i for i, coord in enumerate(coords)}
                n = len(coords)
                adjacency_matrix = np.zeros((n, n))
                spec_ndim = len(coords[0]) if coords else 0
                for coord in coords:
                    ci = coord_to_idx[coord]
                    for d in range(spec_ndim):
                        neighbor = list(coord)
                        neighbor[d] += 1
                        neighbor = tuple(neighbor)
                        if neighbor in coord_to_idx:
                            adjacency_matrix[ci, coord_to_idx[neighbor]] = 1
                            adjacency_matrix[coord_to_idx[neighbor], ci] = 1
                
                reducer = SpectralEmbedding(n_components=target_dims, affinity='precomputed', random_state=42)
                reduced_coords = reducer.fit_transform(adjacency_matrix)
            else:
                reducer = SpectralEmbedding(n_components=target_dims, affinity=spectral_affinity, 
                                          gamma=spectral_gamma, random_state=42)
                reduced_coords = reducer.fit_transform(coord_matrix)
        else:
            raise ValueError(f"Unknown dim_reduction method: {dim_reduction}. Use 'mds' or 'spectral'")
        
        coords = [tuple(reduced_coords[i]) for i in range(len(coords))]
        effective_dimensionality = target_dims
        
        coord_mapping = {original_coords[i]: coords[i] for i in range(len(coords))}
        G_reduced = nx.Graph()
        G_reduced.add_nodes_from(coords)
        
        orig_set = set(original_coords)
        orig_ndim = len(original_coords[0]) if original_coords else 0
        for coord in original_coords:
            for d in range(orig_ndim):
                neighbor = list(coord)
                neighbor[d] += 1
                neighbor = tuple(neighbor)
                if neighbor in orig_set:
                    G_reduced.add_edge(coord_mapping[coord], coord_mapping[neighbor])
        
        G = G_reduced
    else:
        effective_dimensionality = lattice.dimensionality
        coord_mapping = {}

    _edge_trace_data = []
    _edge_color_data = []
    _path_trace_start = 0
    _path_trace_end = 0
    
    if title is None:
        resolution_str = 'x'.join(str(r) for r in lattice.resolution)
        bipolar_str = "bipolar" if lattice.bipolar else "unipolar"
        if lattice.dimensionality > 3:
            title = f"{lattice.dimensionality}D→{target_dims}D Lattice ({resolution_str}, {bipolar_str}, {dim_reduction})"
        else:
            title = f"{lattice.dimensionality}D Lattice ({resolution_str}, {bipolar_str})"
    
    # Handle edge highlighting for selected coordinates
    # Only include nodes that actually exist in the plotting coordinate set
    valid_coords = set(coords) if lattice.dimensionality <= 3 else set(original_coords)
    highlighted_coords = set()
    
    if nodes:
        highlighted_coords.update(coord for coord in nodes if coord in valid_coords)
    
    if path:
        highlighted_coords.update(coord for coord in path if coord in valid_coords)

    if shape is not None and len(shape) > 0:
        if isinstance(shape[0], list):
            lattice_shape_groups = [list(g) for g in shape]
        else:
            lattice_shape_groups = [list(shape)]
        for g in lattice_shape_groups:
            for coord in g:
                c = tuple(coord) if not isinstance(coord, tuple) else coord
                if c in valid_coords:
                    highlighted_coords.add(c)
    else:
        lattice_shape_groups = []

    has_shape = len(lattice_shape_groups) > 0
    lattice_shape_color_map = {}
    if has_shape:
        for gi, group in enumerate(lattice_shape_groups):
            color = _SHAPE_COLORS_GLOBAL[gi % len(_SHAPE_COLORS_GLOBAL)]
            for coord in group:
                c = tuple(coord) if not isinstance(coord, tuple) else coord
                lattice_shape_color_map[c] = color
    
    use_dimmed = ((nodes is not None and len(nodes) > 0) or (path is not None and len(path) > 0) or has_shape) and not mute_background
    
    if effective_dimensionality > 2:
        dimmed_edge_color = '#333333'
        dimmed_node_color = '#080808'
    else:
        dimmed_edge_color = '#555555'
        dimmed_node_color = '#111111'
    
    gen_labels = [str(g) for g in lattice.generators] if is_tone_lattice else []

    from .svg_lattice import _svg_lattice_2d
    from .threejs_lattice import _threejs_lattice_3d

    svg_threejs_kwargs = dict(
        lattice=lattice, coords=coords, G=G, path=path, nodes=nodes,
        highlighted_coords=highlighted_coords, coord_mapping=coord_mapping,
        original_coords=original_coords,
        effective_dimensionality=effective_dimensionality,
        use_dimmed=use_dimmed, mute_background=mute_background,
        path_mode=path_mode, figsize=figsize, node_size=node_size,
        title=title, is_tone_lattice=is_tone_lattice,
        coord_label=coord_label, gen_labels=gen_labels,
        path_cmap=path_cmap,
    )

    if not animate:
        if effective_dimensionality <= 2:
            return _svg_lattice_2d(**svg_threejs_kwargs, shape=lattice_shape_groups if lattice_shape_groups else None)
        else:
            return _threejs_lattice_3d(**svg_threejs_kwargs)

    if path and len(path) > 1:
        from ._audio_events import build_path_audio_events

        ref_freq = 261.63
        freqs = []
        for coord in path:
            try:
                ratio = lattice._coord_to_ratio(coord) if hasattr(lattice, '_coord_to_ratio') else None
                freqs.append(ref_freq * float(ratio) if ratio is not None else ref_freq)
            except Exception:
                freqs.append(ref_freq)
        audio_payload = build_path_audio_events(freqs, dur, amp=amp)

        if effective_dimensionality <= 2:
            from .animated import AnimatedLatticeSvgFigure
            svg_data = _svg_lattice_2d(**svg_threejs_kwargs)
            return AnimatedLatticeSvgFigure(
                svg_data=svg_data, audio_payload=audio_payload, dur=dur
            )
        else:
            from .animated import AnimatedLattice3dFigure
            threejs_data = _threejs_lattice_3d(**svg_threejs_kwargs)
            return AnimatedLattice3dFigure(
                scene_data=threejs_data, audio_payload=audio_payload, dur=dur
            )

    if has_shape:
        from ._audio_events import build_shape_audio_events

        ref_freq = 261.63
        freq_groups = []
        for group in lattice_shape_groups:
            group_freqs = []
            for coord in group:
                try:
                    ratio = lattice._coord_to_ratio(coord) if hasattr(lattice, '_coord_to_ratio') else None
                    group_freqs.append(ref_freq * float(ratio) if ratio is not None else ref_freq)
                except Exception:
                    group_freqs.append(ref_freq)
            freq_groups.append(group_freqs)

        audio_payload = build_shape_audio_events(freq_groups, dur, arp=arp, strum=strum, direction=direction, amp=amp)

        if effective_dimensionality <= 2:
            from .animated import AnimatedLatticeShapeFigure
            svg_data = _svg_lattice_2d(**svg_threejs_kwargs, shape=lattice_shape_groups)
            return AnimatedLatticeShapeFigure(
                svg_data=svg_data, audio_payload=audio_payload, dur=dur
            )

    if effective_dimensionality <= 2:
        return _svg_lattice_2d(**svg_threejs_kwargs, shape=lattice_shape_groups if lattice_shape_groups else None)
    return _threejs_lattice_3d(**svg_threejs_kwargs)


