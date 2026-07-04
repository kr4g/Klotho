def _plot_timeline(obj, layout: str = 'ratios',
                   figsize: tuple[float, float] | None = None,
                   outlines: bool = True,
                   animate: bool = False, dur: float = 0.5,
                   glow: bool = False, amp: float = None, **kwargs):
    """
    Render a TemporalUnitSequence or TemporalBlock as a multi-lane timeline.

    Each contained TemporalUnit / CompositionalUnit is drawn as a
    "ratios"-style strip spanning its absolute time interval on a
    real-time x-axis, placed on a lane assigned by a deterministic
    recursive layout (nested containers stack vertically for blocks and
    share lanes for sequences).

    Parameters
    ----------
    obj : TemporalUnitSequence or TemporalBlock
        Temporal container to visualize.
    layout : str, optional
        Layout mode.  Only ``'ratios'`` is currently supported.
    figsize : tuple of float or None, optional
        Width and height in inches.  Defaults to ``(11, 0.55 * lanes)``.
    outlines : bool, optional
        Draw subtle outlines around nested container extents.
    animate : bool, optional
        Return an animated figure with audio playback controls.
    dur : float, optional
        Seconds between animation steps (no-audio fallback only).
    glow : bool, optional
        Enable halo glow effect on active segments during animation.
    amp : float, optional
        Amplitude forwarded to the animation event converter.

    Returns
    -------
    SvgTimelineData or AnimatedTimelineSvgFigure
        Renderable SVG data or animated figure.
    """
    if layout != 'ratios':
        raise ValueError(
            f"Unknown layout: {layout}. Only 'ratios' is currently supported "
            f"for TemporalUnitSequence and TemporalBlock."
        )

    from .._renderers.svg_timeline import _svg_timeline_ratios

    svg_data = _svg_timeline_ratios(obj, figsize=figsize, outlines=outlines)

    if not animate:
        return svg_data

    from .._animation import AnimatedTimelineSvgFigure
    from klotho.utils.playback._config import get_audio_engine

    engine = get_audio_engine()

    if engine == "supersonic":
        from klotho.utils.playback.supersonic.converters import (
            temporal_container_to_sc_animation_events,
        )
        audio_payload = temporal_container_to_sc_animation_events(obj, amp=amp)
    else:
        from klotho.utils.playback.tonejs.converters import (
            temporal_container_to_animation_events,
        )
        audio_payload = temporal_container_to_animation_events(obj, amp=amp)

    return AnimatedTimelineSvgFigure(
        svg_data=svg_data,
        audio_payload=audio_payload,
        dur=dur,
        glow=glow,
        engine=engine,
        ring_time=kwargs.get("ring_time", 5),
        loop=kwargs.get("loop", False),
    )
