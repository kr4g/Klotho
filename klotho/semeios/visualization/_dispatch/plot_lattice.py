import math
import numpy as np
import networkx as nx

from klotho.topos.graphs.lattices import Lattice

from .._shared.audio_ref import reference_freq
from .._shared.colors import SHAPE_COLORS as _SHAPE_COLORS_GLOBAL
from .._projections import apply_projection
from ._klotho_plot import transport_kwargs


_PREVIEW_CONTROL_KEYS = frozenset({
    "pause", "loop", "ring_time", "defName", "dur", "amp",
    "arp", "strum", "direction", "beat", "bpm", "glow", "inst",
})


def _resolve_plot_inst(kwargs):
    """Pop and resolve the ``inst`` kwarg for plot playback.

    Returns ``(def_name, inst_pfields)`` where ``def_name`` is the
    SynthDef to use for previews and audio payloads (``defName=`` kwarg
    wins as a lower-level escape hatch, then the instrument, then
    ``'kl_tri'``) and ``inst_pfields`` are the instrument's default
    pfields (merged below explicit user kwargs).
    """
    from klotho.utils.playback._converter_base import resolve_instrument
    inst = kwargs.pop('inst', None) if kwargs else None
    inst_def_name, inst_pfields, _ = resolve_instrument(inst)
    explicit = kwargs.get('defName') if kwargs else None
    def_name = explicit or inst_def_name or 'kl_tri'
    cleaned = {k: v for k, v in (inst_pfields or {}).items()
               if k not in ('gate', 'out', 'freq', 'amp')}
    return def_name, cleaned


def _build_preview_config(dur, amp, kwargs, engine, def_name='kl_tri', inst_pfields=None):
    """Build the click-to-play preview configuration dict.

    Carries ``pfields`` (instrument defaults overlaid with any extra
    synth kwargs from ``.play()``, e.g. ``attackTime``) so previews
    respect the same parameters as full playback.
    """
    pfields = dict(inst_pfields or {})
    if kwargs:
        pfields.update({k: v for k, v in kwargs.items() if k not in _PREVIEW_CONTROL_KEYS})
    return {
        "dur": kwargs.get("dur", dur) if kwargs else dur,
        "amp": kwargs.get("amp", amp) if kwargs else amp,
        "defName": def_name,
        "engine": engine,
        "pfields": pfields or None,
    }


def _payload_extra_pfields(kwargs, inst_pfields=None):
    """Extra pfields for path/shape audio payloads: instrument defaults
    below explicit user kwargs (control keys excluded)."""
    merged = dict(inst_pfields or {})
    if kwargs:
        merged.update({k: v for k, v in kwargs.items()
                       if k not in {"pause", "loop", "ring_time", "inst", "defName", "equaves"}})
    return merged or None


def _prepare_plot_audio(kwargs, dur, amp, animate):
    """Resolve engine, preview synth, click-preview config, and payload
    extras for a lattice-family plot in one step.

    Returns ``(engine_name, preview_def_name, preview_config,
    extra_synth_kwargs)``; ``preview_config`` is None unless *animate*.
    """
    from klotho.utils.playback._config import get_audio_engine
    preview_def_name, inst_pfields = _resolve_plot_inst(kwargs)
    engine_name = get_audio_engine()
    preview_config = _build_preview_config(
        dur, amp, kwargs, engine_name,
        def_name=preview_def_name, inst_pfields=inst_pfields,
    ) if animate else None
    return engine_name, preview_def_name, preview_config, _payload_extra_pfields(kwargs, inst_pfields)


def _normalize_shape_groups(shape):
    """Normalize a ``shape`` argument to a list of groups (possibly empty)."""
    if shape is not None and len(shape) > 0:
        if isinstance(shape[0], (list, tuple)):
            return [list(g) for g in shape]
        return [list(shape)]
    return []


def _shape_group_colors(shape, mode=None):
    """Per-group colors for shape groups.

    ``mode=None`` (default): groups carrying a ``color`` attribute (e.g.
    :class:`klotho.topos.shapes.Shape`) use it; otherwise None so the
    cycling palette applies.

    ``mode='one-sided'``: every group is colored by its one-sided shape
    identity — rotations and translations of the same shape share a color
    (the Tetris convention, :attr:`Shape.color`).

    ``mode='fixed'``: every distinct *orientation* gets its own color —
    translations of a shape share a color, rotations and reflections do
    not. Hues are evenly spaced in order of first appearance.
    """
    if shape is None or len(shape) == 0:
        return None
    if not isinstance(shape[0], (list, tuple)):
        return None

    first = shape[0]
    is_group = isinstance(first, list) or (
        isinstance(first, tuple) and len(first) > 0
        and isinstance(first[0], (list, tuple))
    )
    groups = list(shape) if is_group else [shape]

    if mode is None:
        colors = [getattr(g, 'color', None) for g in groups]
        if any(c is not None for c in colors):
            return colors
        return None

    from klotho.topos.shapes.polyominoes import Shape as _Shape, normalize as _normalize

    if mode == 'one-sided':
        return [_Shape(g).color for g in groups]

    if mode == 'fixed':
        import colorsys
        form_colors = {}
        order = []
        for g in groups:
            form = tuple(_normalize(g))
            if form not in form_colors:
                form_colors[form] = None
                order.append(form)
        for i, form in enumerate(order):
            r, gg, b = colorsys.hsv_to_rgb(i / max(len(order), 1), 0.62, 0.95)
            form_colors[form] = f'#{int(r * 255):02x}{int(gg * 255):02x}{int(b * 255):02x}'
        return [form_colors[tuple(_normalize(g))] for g in groups]

    raise ValueError(
        f"shape_color must be None, 'one-sided', or 'fixed', got {mode!r}"
    )


def _resolve_chord_shape(obj, shape):
    """Resolve a Chord/Voicing/ChordSequence ``shape`` argument against a
    lattice-family object.

    Returns ``(shape_groups, freq_groups)`` — highlight node groups from
    resolving each chord's degrees back to the object's nodes (each
    class's ``_node_for_ratio`` hook normalizes by its own equave
    convention, so voiced/shifted degrees find their node), and playback
    frequencies from the chords' own realization (root, equave shifts,
    and voicing all respected) — or ``None`` when *shape* is not
    chord-like, falling through to the node-group path.

    Raises
    ------
    ValueError
        If a degree does not correspond to any node of *obj*.
    TypeError
        If *obj* has no ratio-to-node lookup (not a lattice-family class).
    """
    from klotho.tonos.chords.chord import Chord, Voicing, ChordSequence

    if isinstance(shape, ChordSequence):
        chords = list(shape)
    elif isinstance(shape, (Chord, Voicing)):
        chords = [shape]
    else:
        return None

    if not hasattr(obj, '_node_for_ratio'):
        raise TypeError(
            f"shape={type(shape).__name__} requires a lattice-family object "
            f"with ratio-to-node lookup; {type(obj).__name__} has none."
        )

    shape_groups, freq_groups = [], []
    for ch in chords:
        group = []
        for degree in ch.degrees:
            node = obj._node_for_ratio(degree)
            if node is None:
                raise ValueError(
                    f"Shape chord degree {degree} does not correspond to a "
                    f"node of this {type(obj).__name__}."
                )
            group.append(node)
        shape_groups.append(group)
        freq_groups.append([float(f) for f in ch.freqs])
    return shape_groups, freq_groups


def _resolve_scale_nodes(obj, nodes):
    """Resolve a Scale ``nodes`` argument against a lattice-family object.

    Returns ``(scale, coords)`` — the scale itself and one lattice
    coordinate per scale degree (via the object's ``_node_for_ratio``
    hook, so equave conventions are respected) — or ``None`` when
    *nodes* is not a Scale, falling through to the coordinate-list
    path.  The coordinates highlight exactly like a hand-built
    ``nodes=`` list; on ``.play()`` the scale runs up ``equaves``
    equaves and back down, selecting each sounding node per step
    (similar to the default CPS scale run).

    Raises
    ------
    ValueError
        If a degree does not correspond to any node of *obj*.
    TypeError
        If *obj* has no ratio-to-node lookup (not a lattice-family class).
    """
    from klotho.tonos.scales.scale import Scale

    if not isinstance(nodes, Scale):
        return None

    if not hasattr(obj, '_node_for_ratio'):
        raise TypeError(
            f"nodes={type(nodes).__name__} requires a lattice-family object "
            f"with ratio-to-node lookup; {type(obj).__name__} has none."
        )

    coords, unresolved = [], []
    for degree in nodes.degrees:
        node = obj._node_for_ratio(degree)
        if node is None:
            unresolved.append(str(degree))
        else:
            coords.append(node)
    if unresolved:
        raise ValueError(
            f"Scale degrees {unresolved} do not correspond to nodes "
            f"of this {type(obj).__name__}."
        )
    return nodes, coords


def _scale_nodes_run(scale, coords, equaves=1):
    """Build the ``nodes=<Scale>`` playback run.

    Returns ``(freqs, run_coords)``: the scale played up ``equaves``
    equaves and back down (mirroring the CPS scale run), and for each
    step the lattice coordinate whose equave-reduced ratio sounds — so
    octave-equivalent steps select the same node.  Returns None for an
    empty scale.
    """
    n = len(coords)
    if n == 0:
        return None
    eq = int(equaves) if equaves else 1
    abs_eq = abs(eq) or 1
    idxs = list(range(abs_eq * n + 1))
    if eq < 0:
        idxs = [-i for i in idxs]
    idxs = idxs + idxs[-2::-1]
    freqs = [float(scale[i].freq) for i in idxs]
    run_coords = [coords[i % n] for i in idxs]
    return freqs, run_coords


def _ratio_freqs(items, get_ratio, ref_freq):
    """``ref_freq``-scaled frequencies for path/shape items.

    Items whose ratio is missing or malformed fall back to the
    reference frequency itself.
    """
    freqs = []
    for item in items:
        try:
            ratio = get_ratio(item)
            freqs.append(ref_freq * float(ratio) if ratio is not None else ref_freq)
        except Exception:
            freqs.append(ref_freq)
    return freqs


def _path_audio_payload(freqs, dur, amp, extra_synth_kwargs, preview_def_name,
                        engine_name, kwargs):
    """Engine audio payload for a step-per-frequency (path-style) animation."""
    from klotho.utils.playback.animation_events import build_path_engine_payload
    return build_path_engine_payload(
        freqs,
        dur,
        engine=engine_name,
        amp=amp,
        extra_pfields=extra_synth_kwargs,
        pause=kwargs.get("pause", 0.0) if kwargs else 0.0,
        def_name=preview_def_name,
    )


def _animated_path_figure(freqs, use_3d, render_2d, render_3d, dur, amp,
                          extra_synth_kwargs, preview_def_name, engine_name, kwargs):
    """Path-traversal audio payload wrapped in the matching animated figure.

    Shared by the lattice, CPS, and MasterSet dispatchers; ``render_2d``
    / ``render_3d`` are zero-arg closures over the family-specific
    renderer call.
    """
    from .._animation import AnimatedLatticeSvgFigure, AnimatedLattice3dFigure

    audio_payload = _path_audio_payload(
        freqs, dur, amp, extra_synth_kwargs, preview_def_name, engine_name, kwargs)
    if use_3d:
        return AnimatedLattice3dFigure(
            scene_data=render_3d(), audio_payload=audio_payload, dur=dur,
            **transport_kwargs(kwargs),
        )
    return AnimatedLatticeSvgFigure(
        svg_data=render_2d(), audio_payload=audio_payload, dur=dur,
        **transport_kwargs(kwargs),
    )


def _animated_shape_figure(freq_groups, use_3d, render_2d, render_3d, dur, arp,
                           strum, direction, amp, extra_synth_kwargs,
                           preview_def_name, engine_name, kwargs, trail=False):
    """Shape (chord/chord-sequence) audio payload wrapped in the matching
    animated figure, mirroring :func:`_animated_path_figure`."""
    from klotho.utils.playback.animation_events import build_shape_engine_payload
    from .._animation import AnimatedLatticeShapeFigure, AnimatedLattice3dShapeFigure

    audio_payload = build_shape_engine_payload(
        freq_groups,
        dur,
        engine=engine_name,
        arp=arp,
        strum=strum,
        direction=direction,
        amp=amp,
        extra_pfields=extra_synth_kwargs,
        pause=kwargs.get("pause", 0.25) if kwargs else 0.25,
        def_name=preview_def_name,
    )
    if use_3d:
        return AnimatedLattice3dShapeFigure(
            scene_data=render_3d(), audio_payload=audio_payload, dur=dur,
            trail=trail, **transport_kwargs(kwargs),
        )
    return AnimatedLatticeShapeFigure(
        svg_data=render_2d(), audio_payload=audio_payload, dur=dur,
        trail=trail, **transport_kwargs(kwargs),
    )


def _coerce_to_tuples(items):
    if items is None:
        return None
    result = []
    for item in items:
        if isinstance(item, (list, tuple)):
            result.append(tuple(item))
        elif hasattr(item, 'tolist'):
            result.append(tuple(item.tolist()))
        elif hasattr(item, '__iter__') and not isinstance(item, str):
            result.append(tuple(item))
        else:
            result.append(item)
    return result


def _prepare_lattice_coordinates(lattice, nodes, path, path_mode, fit, pad,
                                 dim_reduction, target_dims,
                                 mds_metric, mds_max_iter,
                                 spectral_affinity, spectral_gamma,
                                 shape=None, layout='lattice'):
    if dim_reduction is None:
        dim_reduction = 'mds'
    if target_dims not in [2, 3]:
        raise ValueError(f"target_dims must be 2 or 3, got {target_dims}")

    if lattice.dimensionality <= 2:
        max_resolution = 5
    elif lattice.dimensionality == 3:
        max_resolution = 2
    elif target_dims == 3:
        max_resolution = 1
    else:
        max_resolution = 3

    expected_total = 1
    for dim in lattice._dims:
        expected_total *= len(dim)
        if expected_total > 10000:
            expected_total = float('inf')
            break

    shape_coords = []
    if shape is not None and len(shape) > 0:
        if isinstance(shape[0], (list, tuple)) and shape[0] and isinstance(shape[0][0], (list, tuple, int)):
            if isinstance(shape[0][0], (list, tuple)):
                for g in shape:
                    for c in g:
                        shape_coords.append(tuple(c) if not isinstance(c, tuple) else c)
            else:
                for c in shape:
                    shape_coords.append(tuple(c) if not isinstance(c, tuple) else c)
        else:
            for c in shape:
                shape_coords.append(tuple(c) if not isinstance(c, tuple) else c)

    has_selection = bool(nodes) or bool(path) or bool(shape_coords)

    fit_mode = None
    if fit is True:
        fit_mode = 'rect'
    elif isinstance(fit, str) and fit in ('rect', 'square', 'tight'):
        fit_mode = fit

    if has_selection and fit_mode:
        import itertools
        all_coords_to_fit = list(nodes or []) + list(path or []) + shape_coords

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
        if path:
            import itertools
            coord_ranges = []
            for dim_idx in range(lattice.dimensionality):
                dim_vals = [coord[dim_idx] for coord in path if coord in lattice]
                if dim_vals:
                    min_val, max_val = min(dim_vals), max(dim_vals)
                    coord_ranges.append((min_val - 2, max_val + 2))
                else:
                    coord_ranges.append((-max_resolution, max_resolution))
            ranges = [range(start, end + 1) for start, end in coord_ranges]
            coords = [coord for coord in itertools.product(*ranges) if coord in lattice]
        else:
            coords = lattice._get_plot_coords(max_resolution)
    else:
        coords = lattice.coords

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
        G = lattice

    if nodes and path_mode == 'origin':
        origin = tuple(0 for _ in range(lattice.dimensionality))
        if origin not in coords:
            coords.append(origin)
            if hasattr(G, 'add_node'):
                G.add_node(origin)
                for coord in coords:
                    if coord != origin:
                        diff_count = sum(1 for a, b in zip(origin, coord) if abs(a - b) == 1)
                        same_count = sum(1 for a, b in zip(origin, coord) if a == b)
                        if diff_count == 1 and same_count == len(coord) - 1:
                            G.add_edge(origin, coord)

    original_coords = coords

    if lattice.dimensionality > 3:
        coord_matrix = np.array([list(coord) for coord in coords])

        adjacency_matrix = None
        if dim_reduction == 'spectral' and spectral_affinity == 'precomputed':
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

        reduced_coords = apply_projection(
            coord_matrix, dim_reduction,
            target_dims=target_dims,
            mds_metric=mds_metric,
            mds_max_iter=mds_max_iter,
            spectral_affinity=spectral_affinity,
            spectral_gamma=spectral_gamma,
            adjacency=adjacency_matrix,
        )

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

    if layout == 'tonnetz':
        # Isometric embedding of a triangular 2D lattice: node identity
        # stays the axial coordinate (original_coords); drawn positions
        # are x = q + r/2, y = (sqrt(3)/2) r. Edges come from the
        # lattice's own neighbor offsets (three directions for a Tonnetz).
        import math
        root3_2 = math.sqrt(3) / 2.0
        original_coords = coords
        coord_mapping = {
            c: (c[0] + c[1] / 2.0, root3_2 * c[1]) for c in coords
        }
        coords = [coord_mapping[c] for c in original_coords]
        offsets = getattr(lattice, '_edge_offsets', ((1, 0), (0, 1)))
        G_tri = nx.Graph()
        G_tri.add_nodes_from(coords)
        axial_set = set(original_coords)
        for c in original_coords:
            for dq, dr in offsets:
                neighbor = (c[0] + dq, c[1] + dr)
                if neighbor in axial_set:
                    G_tri.add_edge(coord_mapping[c], coord_mapping[neighbor])
        G = G_tri
        effective_dimensionality = 2

    return coords, G, original_coords, coord_mapping, effective_dimensionality


def _build_lattice_graph_data(lattice, coords, original_coords, coord_mapping,
                              effective_dimensionality, nodes, path, shape,
                              path_mode, mute_background, is_tone_lattice):
    valid_coords = set(original_coords) if coord_mapping else set(coords)
    highlighted_coords = set()

    if nodes:
        highlighted_coords.update(coord for coord in nodes if coord in valid_coords)
    if path:
        highlighted_coords.update(coord for coord in path if coord in valid_coords)

    if shape is not None and len(shape) > 0:
        first = shape[0]
        is_group = isinstance(first, list) or (
            isinstance(first, tuple) and len(first) > 0
            and isinstance(first[0], (list, tuple))
        )
        if is_group:
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
    use_dimmed = (bool(nodes) or bool(path) or has_shape) and not mute_background

    gen_labels = [str(g) for g in lattice.generators] if is_tone_lattice else []

    return highlighted_coords, lattice_shape_groups, use_dimmed, gen_labels


def _setup_lattice_animation(lattice, coords, G, original_coords, coord_mapping,
                              effective_dimensionality, highlighted_coords,
                              lattice_shape_groups, use_dimmed, mute_background,
                              gen_labels, is_tone_lattice, coord_label,
                              path, path_mode, shape,
                              figsize, node_size, title, path_cmap,
                              dur, arp, strum, direction, amp, kwargs,
                              preview_def_name='kl_tri', inst_pfields=None,
                              chord_freq_groups=None, layout='lattice',
                              shape_colors=None, trail=False,
                              scale_run=None, equaves=1, nodes=None):
    has_shape = len(lattice_shape_groups) > 0
    from klotho.utils.playback._config import get_audio_engine
    engine_name = get_audio_engine()

    svg_threejs_kwargs = dict(
        lattice=lattice, coords=coords, G=G, path=path,
        # The scale-run figure keeps its nodes= highlighting (connector
        # edges between adjacent members); path/shape animations render
        # without it, as before.
        nodes=(nodes if scale_run is not None else None),
        highlighted_coords=highlighted_coords, coord_mapping=coord_mapping,
        original_coords=original_coords,
        effective_dimensionality=effective_dimensionality,
        use_dimmed=use_dimmed, mute_background=mute_background,
        path_mode=path_mode, figsize=figsize, node_size=node_size,
        title=title, is_tone_lattice=is_tone_lattice,
        coord_label=coord_label, gen_labels=gen_labels,
        path_cmap=path_cmap, layout=layout, shape_colors=shape_colors,
    )

    preview_config = _build_preview_config(dur, amp, kwargs, engine_name,
                                           def_name=preview_def_name,
                                           inst_pfields=inst_pfields)
    extra_synth_kwargs = _payload_extra_pfields(kwargs, inst_pfields)

    def _coord_ratio(coord):
        return lattice._coord_to_ratio(coord) if hasattr(lattice, '_coord_to_ratio') else None

    use_3d = effective_dimensionality > 2

    def _render_2d(shape=None):
        from .._renderers.svg_lattice import _svg_lattice_2d
        extra = {'shape': shape} if shape is not None else {}
        return _svg_lattice_2d(**svg_threejs_kwargs, preview_config=preview_config, **extra)

    def _render_3d(shape=None):
        from .._renderers.threejs_lattice import _threejs_lattice_3d
        extra = {'shape': shape} if shape is not None else {}
        return _threejs_lattice_3d(
            **svg_threejs_kwargs,
            preview_engine=engine_name,
            preview_config=preview_config,
            **extra,
        )

    if scale_run is not None:
        # nodes=<Scale>: play the scale up `equaves` equaves and back
        # down, selecting each sounding node the way a mouse click does
        # (similar to the default CPS scale run).
        run = _scale_nodes_run(scale_run[0], scale_run[1], equaves)
        if run is not None:
            freqs, run_coords = run
            audio_payload = _path_audio_payload(
                freqs, dur, amp, extra_synth_kwargs, preview_def_name,
                engine_name, kwargs)
            plot_run = [coord_mapping.get(c, c) for c in run_coords]

            if use_3d:
                threejs_data = _render_3d()
                pos_idx = {}
                for i, p in enumerate(threejs_data.scene_data['nodes']):
                    pos_idx[(round(p[0], 6), round(p[1], 6), round(p[2], 6))] = i

                def _key3(c):
                    x, y, z = (list(c) + [0.0, 0.0])[:3]
                    return (round(float(x), 6), round(float(y), 6), round(float(z), 6))

                threejs_data.scene_data['selectNodeIndices'] = [
                    pos_idx.get(_key3(c), -1) for c in plot_run
                ]
                from .._animation import AnimatedLattice3dSelectFigure
                return AnimatedLattice3dSelectFigure(
                    threejs_data, audio_payload=audio_payload, dur=dur,
                    **transport_kwargs(kwargs),
                )

            svg_data = _render_2d()
            id_index = {nid: i for i, nid in enumerate(svg_data.all_node_ids)}
            c2n = svg_data.coord_to_node_id
            select_indices = [id_index.get(c2n.get(c, ''), -1) for c in plot_run]
            from .._animation import AnimatedNodeSelectSvgFigure
            return AnimatedNodeSelectSvgFigure(
                svg_data, select_indices,
                audio_payload=audio_payload, dur=dur,
                **transport_kwargs(kwargs),
            )

    if path and len(path) > 1:
        freqs = _ratio_freqs(path, _coord_ratio, reference_freq(lattice))
        return _animated_path_figure(
            freqs, use_3d, _render_2d, _render_3d,
            dur, amp, extra_synth_kwargs, preview_def_name, engine_name, kwargs)

    if has_shape:
        freq_groups = (chord_freq_groups if chord_freq_groups is not None
                       else [_ratio_freqs(group, _coord_ratio, reference_freq(lattice))
                             for group in lattice_shape_groups])
        return _animated_shape_figure(
            freq_groups, use_3d,
            lambda: _render_2d(shape=lattice_shape_groups),
            lambda: _render_3d(shape=lattice_shape_groups),
            dur, arp, strum, direction, amp, extra_synth_kwargs,
            preview_def_name, engine_name, kwargs, trail=trail)

    return None


def _plot_lattice(lattice: Lattice, figsize: tuple[float, float] = (12, 12),
                 node_size: float = 8, title: str = None,
                 output_file: str = None,
                 dim_reduction: str = 'mds', target_dims: int = 3,
                 mds_metric: bool = True, mds_max_iter: int = 300,
                 spectral_affinity: str = 'rbf', spectral_gamma: float = None,
                 nodes: list = None, path: list = None, path_mode: str = 'adjacent',
                 mute_background: bool = False, fit=False, pad: int = 1,
                 path_cmap: str = 'viridis', layout: str = None,
                 trail=False,
                 animate: bool = False, dur: float = 0.5,
                 shape: list = None, shape_color: str = None,
                 arp: bool = False, strum: float = 0, direction: str = 'u',
                 amp: float = None, equaves: int = 1, **kwargs):
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
    dim_reduction : str, optional
        Dimensionality-reduction method used when ``lattice.dimensionality``
        exceeds 3. One of ``'mds'`` (default), ``'spectral'``, ``'pca'``,
        ``'ortho_best'``, or ``'ortho_first'``.
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
    nodes : list of tuple, Scale, or None, optional
        Coordinate tuples to highlight, or a ``Scale``: its degrees
        resolve to lattice coordinates (all must resolve) and highlight,
        and ``.play()`` runs the scale up ``equaves`` equaves and back
        down, selecting each sounding node per step.
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
    layout : str, optional
        ``'lattice'`` draws nodes connected by grid edges.
        ``'cells'`` draws one filled square (2D) or translucent cube (3D)
        per coordinate, with no edges: highlights, shapes, and node
        selections colour the cells (``nodes=`` connector edges are not
        drawn), and paths draw arrows from cell center to cell center.
        Requires ``lattice.dimensionality <= 3``.
        ``'tonnetz'`` draws a 2D lattice isometrically (equilateral
        triangles), including the lattice's third-direction edges.
        Requires ``lattice.dimensionality == 2``.
        Defaults to the lattice's own preferred layout (``'tonnetz'``
        for a Tonnetz, ``'lattice'`` otherwise).
    trail : bool or float, optional
        During animated shape playback, leave a translucent onion-skin of
        already-played shapes (most recent stacking on top). ``True`` uses
        the default shadow opacity; a float in (0, 1] sets it explicitly.
    animate : bool, optional
        Return an animated figure when ``True``.
    dur : float, optional
        Seconds between animation steps.
    shape : list, Chord, ChordSequence, or None, optional
        Coordinate tuples (chord), list of lists (chord sequence), or a
        ``Chord``/``Voicing``/``ChordSequence`` (degrees resolved to
        nodes, playback from the chord's own realization).  Scales go
        to ``nodes=`` instead.
    shape_color : str or None, optional
        Group coloring policy. ``'one-sided'``: rotations and
        translations of the same shape share a color (the Tetris
        convention). ``'fixed'``: only translations share a color —
        every distinct orientation gets its own. ``None`` (default):
        the lattice's preferred policy (``'fixed'`` for a Tonnetz);
        otherwise groups carrying a ``color`` attribute (``Shape``) use
        it and others cycle the palette.
    arp : bool, optional
        Arpeggiate chord notes sequentially.
    strum : float, optional
        Per-note timing offset (0--1) in a chord.
    direction : str, optional
        ``'u'`` for ascending or ``'d'`` for descending pitch order.
    equaves : int, optional
        For ``nodes=<Scale>`` playback: how many equaves the scale run
        ascends before descending (negative descends first). Default 1.

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
    if layout is None:
        layout = getattr(lattice, '_plot_layout', 'lattice')
    if shape_color is None:
        shape_color = getattr(lattice, '_plot_shape_color', None)
    if layout not in ('lattice', 'cells', 'tonnetz'):
        raise ValueError(f"layout must be 'lattice', 'cells', or 'tonnetz', got {layout!r}")
    if layout == 'cells' and lattice.dimensionality > 3:
        raise ValueError(
            "layout='cells' requires an axis-aligned lattice with "
            "dimensionality <= 3; use layout='lattice' (with dim_reduction) "
            "for higher dimensions"
        )
    if layout == 'tonnetz' and lattice.dimensionality != 2:
        raise ValueError(
            "layout='tonnetz' requires a 2-dimensional lattice, "
            f"got dimensionality {lattice.dimensionality}"
        )

    is_tone_lattice = hasattr(lattice, '_coord_to_ratio')
    coord_label = "Coordinate"
    if is_tone_lattice:
        coord_label = getattr(lattice, "coord_label", "Monzo")

    preview_def_name, inst_pfields = _resolve_plot_inst(kwargs)

    from klotho.tonos.scales.scale import Scale as _Scale
    if isinstance(shape, _Scale):
        raise TypeError(
            "A Scale goes to nodes= (highlight + scale-run playback); "
            "shape= takes chords, chord sequences, or coordinate groups."
        )

    chord_freq_groups = None
    resolved = _resolve_chord_shape(lattice, shape)
    if resolved is not None:
        shape_groups, chord_freq_groups = resolved
        # Lattice shape groups are lists of coord tuples (group detection
        # downstream keys on list-ness of the outer elements).
        shape = [list(g) for g in shape_groups]
    shape_colors = _shape_group_colors(shape, shape_color)

    scale_run = None
    scale_resolved = _resolve_scale_nodes(lattice, nodes)
    if scale_resolved is not None:
        scale_obj, scale_coords = scale_resolved
        scale_run = (scale_obj, scale_coords)
        seen = set()
        nodes = [c for c in scale_coords if not (c in seen or seen.add(c))]

    nodes = _coerce_to_tuples(nodes)
    path = _coerce_to_tuples(path)

    if nodes is not None:
        expected_dim = lattice.dimensionality
        wrong_dim = [c for c in nodes if hasattr(c, '__len__') and len(c) != expected_dim]
        if wrong_dim:
            raise ValueError(
                f"Node coordinates must be {expected_dim}-dimensional to match "
                f"the lattice, but received {len(wrong_dim[0])}-dimensional "
                f"coordinates (e.g. {wrong_dim[0]}). Provide full lattice "
                f"coordinates; dim_reduction handles projection automatically."
            )
        invalid = [c for c in nodes if c not in lattice]
        if invalid:
            raise ValueError(
                f"The following node coordinates are outside the lattice bounds: {invalid}"
            )
    if path is not None:
        expected_dim = lattice.dimensionality
        wrong_dim = [c for c in path if hasattr(c, '__len__') and len(c) != expected_dim]
        if wrong_dim:
            raise ValueError(
                f"Path coordinates must be {expected_dim}-dimensional to match "
                f"the lattice, but received {len(wrong_dim[0])}-dimensional "
                f"coordinates (e.g. {wrong_dim[0]}). Provide full lattice "
                f"coordinates; dim_reduction handles projection automatically."
            )
        invalid = [c for c in path if c not in lattice]
        if invalid:
            raise ValueError(
                f"The following path coordinates are outside the lattice bounds: {invalid}"
            )

    coords, G, original_coords, coord_mapping, effective_dimensionality = (
        _prepare_lattice_coordinates(
            lattice, nodes, path, path_mode, fit, pad,
            dim_reduction, target_dims,
            mds_metric, mds_max_iter,
            spectral_affinity, spectral_gamma,
            shape=shape, layout=layout,
        )
    )

    if title is None:
        if is_tone_lattice:
            title = ' x '.join(str(g) for g in lattice.generators)
            if getattr(lattice, 'equave_reduce', False):
                from fractions import Fraction
                equave = getattr(lattice, 'equave', Fraction(2))
                if equave == 2:
                    title += " (Octave Reduced)"
                else:
                    title += " (Equave Reduced)"
        else:
            resolution_str = 'x'.join(str(r) for r in lattice.resolution)
            bipolar_str = "bipolar" if lattice.bipolar else "unipolar"
            if lattice.dimensionality > 3:
                title = f"{lattice.dimensionality}D→{target_dims}D Lattice ({resolution_str}, {bipolar_str}, {dim_reduction})"
            else:
                title = f"{lattice.dimensionality}D Lattice ({resolution_str}, {bipolar_str})"

    highlighted_coords, lattice_shape_groups, use_dimmed, gen_labels = (
        _build_lattice_graph_data(
            lattice, coords, original_coords, coord_mapping,
            effective_dimensionality, nodes, path, shape,
            path_mode, mute_background, is_tone_lattice,
        )
    )

    from .._renderers.svg_lattice import _svg_lattice_2d
    from .._renderers.threejs_lattice import _threejs_lattice_3d
    from klotho.utils.playback._config import get_audio_engine

    svg_threejs_kwargs = dict(
        lattice=lattice, coords=coords, G=G, path=path, nodes=nodes,
        highlighted_coords=highlighted_coords, coord_mapping=coord_mapping,
        original_coords=original_coords,
        effective_dimensionality=effective_dimensionality,
        use_dimmed=use_dimmed, mute_background=mute_background,
        path_mode=path_mode, figsize=figsize, node_size=node_size,
        title=title, is_tone_lattice=is_tone_lattice,
        coord_label=coord_label, gen_labels=gen_labels,
        path_cmap=path_cmap, layout=layout, shape_colors=shape_colors,
    )
    preview_engine = get_audio_engine()
    animate_preview_config = _build_preview_config(
        dur, amp, kwargs, preview_engine,
        def_name=preview_def_name, inst_pfields=inst_pfields,
    ) if (animate and is_tone_lattice) else None

    if not animate:
        if effective_dimensionality <= 2:
            return _svg_lattice_2d(
                **svg_threejs_kwargs,
                shape=lattice_shape_groups if lattice_shape_groups else None,
                preview_config=None,
            )
        else:
            return _threejs_lattice_3d(
                **svg_threejs_kwargs,
                preview_engine=preview_engine,
                preview_config=None,
                shape=lattice_shape_groups if lattice_shape_groups else None,
            )

    animated_fig = _setup_lattice_animation(
        lattice, coords, G, original_coords, coord_mapping,
        effective_dimensionality, highlighted_coords,
        lattice_shape_groups, use_dimmed, mute_background,
        gen_labels, is_tone_lattice, coord_label,
        path, path_mode, shape,
        figsize, node_size, title, path_cmap,
        dur, arp, strum, direction, amp, kwargs,
        preview_def_name=preview_def_name, inst_pfields=inst_pfields,
        chord_freq_groups=chord_freq_groups, layout=layout,
        shape_colors=shape_colors, trail=trail,
        scale_run=scale_run, equaves=equaves, nodes=nodes,
    )

    if animated_fig is not None:
        return animated_fig

    if effective_dimensionality <= 2:
        static_fig = _svg_lattice_2d(
            **svg_threejs_kwargs,
            shape=lattice_shape_groups if lattice_shape_groups else None,
            preview_config=animate_preview_config,
        )
    else:
        static_fig = _threejs_lattice_3d(
            **svg_threejs_kwargs,
            preview_engine=preview_engine,
            preview_config=animate_preview_config,
            shape=lattice_shape_groups if lattice_shape_groups else None,
        )

    if is_tone_lattice:
        from .._animation import ClickPreviewFigure
        return ClickPreviewFigure(static_fig, def_name=preview_def_name,
                                  engine=preview_engine)
    return static_fig
