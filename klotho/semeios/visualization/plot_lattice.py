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
                 arp: bool = False, strum: float = 0, direction: str = 'u'):
    import networkx as nx
    """
    Plot a Lattice as a 2D or 3D grid visualization.
    
    Args:
        lattice: Lattice instance to visualize
        figsize: Width and height of the output figure in inches
        node_size: Size of the nodes in the plot
        title: Title for the plot (auto-generated if None)
        output_file: Path to save the visualization (displays plot if None)
        dim_reduction: Dimensionality reduction method for high-dimensional lattices.
                      Options: 'mds', 'spectral', or None (raises error for dim > 3)
        target_dims: Target dimensionality for reduction (2 or 3, default 3)
        mds_metric: Whether to use metric MDS (True) or non-metric MDS (False)
        mds_max_iter: Maximum iterations for MDS algorithm
        spectral_affinity: Kernel for spectral embedding ('rbf', 'nearest_neighbors', etc.)
        spectral_gamma: Kernel coefficient for rbf kernel (auto-determined if None)
        nodes: List of coordinate tuples to highlight, e.g. [(0,0,0), (-3,2,0), (2,-1,1)]
               Highlights selected coordinates and draws edges based on path_mode
        path: List of coordinate tuples representing a path, e.g. [(0,0,0), (1,0,0), (1,1,0)]
              Draws edges between successive coordinates with viridis coloring for time progression
        path_mode: Edge drawing mode when nodes are selected. Options:
                  'adjacent' - Only show edges between selected nodes that are adjacent (default)
                  'origin' - Show shortest paths from origin (0,0,0...) to each selected node
        fit: Controls how the lattice display is cropped when nodes/path are provided.
             False (default) shows the full lattice. Accepts a string mode or True:
             - 'rect' or True: minimal bounding rectangle per dimension
             - 'square': uniform bounding box (largest dimension span used for all axes)
             - 'tight': only the selected nodes/path plus their immediate lattice neighbors
        pad: Integer padding (default 1) added around the selection in each direction
             when ``fit`` is active. Clamped to lattice bounds. Ignored when fit is False.
        path_cmap: Matplotlib colormap name for path edge coloring (default 'viridis').
                   Only applies when ``path`` is provided.
        animate: If True and ``path``/``shape`` is provided, returns an animated figure
                 with playback controls instead of a static go.Figure.
        dur: Duration in seconds between animation steps (default 0.5).
             Only applies when ``animate`` is True.
        shape: List of coordinate tuples (a chord) or list of lists of coordinate tuples
               (a chord sequence). Highlights nodes and draws edges between adjacent ones.
               When animate=True, plays as chord or chord sequence.
        arp: If True, arpeggiate chord notes sequentially instead of block chord
        strum: Strum offset (0-1) for slight timing offset per note in a chord
        direction: 'u' for ascending or 'd' for descending pitch order
        
    Returns:
        go.Figure: Plotly figure object
        
    Raises:
        ValueError: If lattice dimensionality > 3 and dim_reduction is None
    """
    
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
        from klotho.utils.playback.tonejs.converters import freq_to_velocity

        ref_freq = 261.63
        audio_events = []
        for i, coord in enumerate(path):
            try:
                ratio = lattice._coord_to_ratio(coord) if hasattr(lattice, '_coord_to_ratio') else None
                freq = ref_freq * float(ratio) if ratio is not None else ref_freq
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
        from klotho.utils.playback.tonejs.converters import freq_to_velocity

        ref_freq = 261.63
        audio_events = []
        current_time = 0.0

        for gi, group in enumerate(lattice_shape_groups):
            freqs = []
            for coord in group:
                try:
                    ratio = lattice._coord_to_ratio(coord) if hasattr(lattice, '_coord_to_ratio') else None
                    freq = ref_freq * float(ratio) if ratio is not None else ref_freq
                except Exception:
                    freq = ref_freq
                freqs.append(freq)
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

        if effective_dimensionality <= 2:
            from .animated import AnimatedLatticeShapeFigure
            svg_data = _svg_lattice_2d(**svg_threejs_kwargs, shape=lattice_shape_groups)
            return AnimatedLatticeShapeFigure(
                svg_data=svg_data, audio_payload=audio_payload, dur=dur
            )

    if effective_dimensionality <= 2:
        return _svg_lattice_2d(**svg_threejs_kwargs, shape=lattice_shape_groups if lattice_shape_groups else None)
    return _threejs_lattice_3d(**svg_threejs_kwargs)


