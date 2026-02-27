_PLAYBACK_KWARGS = frozenset({
    'beat', 'bpm', 'amp', 'glow', 'arp', 'strum', 'direction', 'dur',
})


class KlothoPlot:
    """Wrapper around a Klotho plot that supports deferred animation.

    Eagerly displays the static figure on creation (so it appears even
    when the ``plot()`` call is not the last expression in a notebook
    cell).  Calling ``.play()`` replaces the static display with an
    animated, audio-capable version.

    Playback-only keyword arguments (``beat``, ``bpm``, ``amp``,
    ``glow``, ``arp``, ``strum``, ``direction``, ``dur``) are
    automatically separated: they are excluded from the static render
    and forwarded when ``.play()`` is called.

    Parameters
    ----------
    plot_fn : callable
        The internal plotting function (e.g. ``_plot_lattice``).
    obj : object
        The Klotho object being plotted.
    kwargs : dict
        Keyword arguments originally passed to ``plot()``.
    """

    def __init__(self, plot_fn, obj, kwargs):
        self._plot_fn = plot_fn
        self._obj = obj
        self._play_kwargs = {k: v for k, v in kwargs.items() if k in _PLAYBACK_KWARGS}
        self._kwargs = {k: v for k, v in kwargs.items() if k not in _PLAYBACK_KWARGS}
        self._static_fig = None
        self._display_handle = None
        self._eager_display()

    def _build_static(self):
        if self._static_fig is None:
            kw = {**self._kwargs, 'animate': False}
            self._static_fig = self._plot_fn(self._obj, **kw)
        return self._static_fig

    def _static_html(self):
        fig = self._build_static()
        if hasattr(fig, 'to_html'):
            return fig.to_html(full_html=False, include_plotlyjs=True)
        return ""

    def _eager_display(self):
        try:
            from IPython.display import display, HTML
            html = self._static_html()
            if html:
                self._display_handle = display(HTML(html), display_id=True)
        except ImportError:
            pass

    def _repr_html_(self):
        return ""

    def play(self, dur=0.5, **play_kwargs):
        """Replace the static plot with an animated version and play audio.

        Parameters
        ----------
        dur : float, optional
            Seconds between animation steps.
        **play_kwargs
            Additional keyword arguments forwarded to the plot function
            (e.g. ``beat``, ``bpm``, ``amp``, ``glow``, ``arp``,
            ``strum``, ``direction``).
        """
        from IPython.display import display, HTML
        merged_play = {**self._play_kwargs, **play_kwargs}
        kw = {**self._kwargs, 'animate': True, 'dur': dur, **merged_play}
        fig = self._plot_fn(self._obj, **kw)
        if hasattr(fig, 'to_html'):
            html_content = HTML(fig.to_html())
        else:
            html_content = fig

        if self._display_handle is not None:
            self._display_handle.update(html_content)
        else:
            display(html_content)
