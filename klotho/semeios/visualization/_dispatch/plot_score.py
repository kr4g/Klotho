from ._klotho_plot import transport_kwargs

_PASSTHROUGH_KWARGS = frozenset({
    'beat', 'bpm', 'arp', 'strum', 'direction', 'pause', 'loop', 'ring_time',
    'record',
})


def _plot_score(score, figsize: tuple[float, float] | None = None,
                outlines: bool = True,
                animate: bool = False, dur: float = 0.5,
                glow: bool = False, **kwargs):
    """
    Render a Score as a track-lane timeline.

    Each track is a horizontal band (registration order); every item
    draws its unit's leaf strips over its absolute ``[start, end]``
    interval on a shared seconds axis, and loose Events draw as single
    blocks (held events extend to the score's end at reduced opacity).

    Parameters
    ----------
    score : Score
        Score to visualize. Must contain at least one item.
    figsize : tuple of float or None, optional
        Width and height in inches. Defaults scale with the lane count.
    outlines : bool, optional
        Draw outlines around item extents.
    animate : bool, optional
        Return an animated figure with audio playback controls.
    dur : float, optional
        Seconds between animation steps (no-audio fallback only).
    glow : bool, optional
        Enable halo glow effect on active segments during animation.

    Returns
    -------
    SvgScoreData or AnimatedTimelineSvgFigure
        Renderable SVG data or animated figure.
    """
    unknown = set(kwargs) - _PASSTHROUGH_KWARGS
    if unknown:
        raise TypeError(
            f"Unexpected keyword argument(s) for score plot: "
            f"{', '.join(sorted(unknown))}"
        )

    from .._renderers.svg_score import _svg_score_timeline

    svg_data = _svg_score_timeline(score, figsize=figsize, outlines=outlines)

    if not animate:
        return svg_data

    from .._animation import AnimatedTimelineSvgFigure
    from klotho.utils.playback.supersonic.converters import (
        convert_score_to_sc_animation_events,
    )

    audio_payload = convert_score_to_sc_animation_events(score)

    return AnimatedTimelineSvgFigure(
        svg_data=svg_data,
        audio_payload=audio_payload,
        dur=dur,
        glow=glow,
        record=bool(kwargs.get('record', False)),
        **transport_kwargs(kwargs),
    )
