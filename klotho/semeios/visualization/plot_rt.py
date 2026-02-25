from klotho.chronos.rhythm_trees import RhythmTree


def _plot_rt(rt: RhythmTree, layout: str = 'containers', figsize: tuple[float, float] | None = None, 
            invert: bool = True, output_file: str | None = None, 
            attributes: list[str] | None = None, vertical_lines: bool = True, 
            barlines: bool = True, barline_color: str = '#666666', 
            subdivision_line_color: str = '#aaaaaa',
            animate: bool = False, dur: float = 0.5,
            audio_source=None,
            beat=None, bpm=None,
            glow: bool = False) -> None:
    """
    Render a RhythmTree using one of several SVG layout modes.

    Parameters
    ----------
    rt : RhythmTree
        RhythmTree instance to visualize.
    layout : str, optional
        Layout mode: ``'containers'`` (nested bars, default),
        ``'ratios'`` (leaf-duration bar), or ``'tree'`` (node-link
        diagram).
    figsize : tuple of float or None, optional
        Width and height in inches.  Defaults vary by layout.
    invert : bool, optional
        When ``True``, places the root at the top.
    output_file : str or None, optional
        Path to save the visualization.
    attributes : list of str or None, optional
        Node attributes to display (tree layout only).
    vertical_lines : bool, optional
        Show subdivision guide lines (containers layout).
    barlines : bool, optional
        Show barlines for multi-span trees (containers layout).
    barline_color : str, optional
        CSS colour for barlines.
    subdivision_line_color : str, optional
        CSS colour for subdivision guide lines.
    animate : bool, optional
        Return an animated figure with audio playback controls.
    dur : float, optional
        Seconds between animation steps.
    audio_source : TemporalUnit or CompositionalUnit or None, optional
        Source of real-time audio data for the animation.
    beat : optional
        Beat value forwarded to the animation event converter.
    bpm : optional
        Tempo value forwarded to the animation event converter.
    glow : bool, optional
        Enable halo glow effect on the active leaf during animation.

    Returns
    -------
    SvgRTData or AnimatedRTSvgFigure
        Renderable SVG data or animated figure.
    """
    from klotho.semeios.visualization.svg_rt import (
        _svg_rt_ratios, _svg_rt_containers, _svg_rt_tree,
    )

    if layout == 'tree':
        if figsize is None:
            figsize = (11, 2)
        svg_data = _svg_rt_tree(rt, attributes=attributes, figsize=figsize, invert=invert,
                                audio_source=audio_source)
    elif layout == 'ratios':
        if figsize is None:
            figsize = (11, 0.5)
        svg_data = _svg_rt_ratios(rt, figsize=figsize, audio_source=audio_source)
    elif layout == 'containers':
        if figsize is None:
            figsize = (11, 2)
        svg_data = _svg_rt_containers(rt, figsize=figsize, invert=invert,
                                      vertical_lines=vertical_lines, barlines=barlines,
                                      barline_color=barline_color,
                                      subdivision_line_color=subdivision_line_color,
                                      audio_source=audio_source)
    else:
        raise ValueError(f"Unknown layout: {layout}. Choose 'tree', 'containers', or 'ratios'.")

    if not animate:
        return svg_data

    from klotho.semeios.visualization.animated import AnimatedRTSvgFigure
    from klotho.utils.playback.tonejs.converters import (
        rhythm_tree_to_animation_events,
        temporal_unit_to_animation_events,
        compositional_unit_to_animation_events,
    )
    from klotho.chronos.temporal_units.temporal import TemporalUnit as _TemporalUnit
    from klotho.thetos.composition.compositional import CompositionalUnit as _CompositionalUnit

    if audio_source is not None:
        if isinstance(audio_source, _CompositionalUnit):
            audio_payload = compositional_unit_to_animation_events(audio_source)
        elif isinstance(audio_source, _TemporalUnit):
            audio_payload = temporal_unit_to_animation_events(audio_source)
        else:
            audio_payload = rhythm_tree_to_animation_events(rt, beat=beat, bpm=bpm)
    else:
        audio_payload = rhythm_tree_to_animation_events(rt, beat=beat, bpm=bpm)

    return AnimatedRTSvgFigure(
        svg_data=svg_data,
        audio_payload=audio_payload,
        dur=dur,
        glow=glow,
    )

