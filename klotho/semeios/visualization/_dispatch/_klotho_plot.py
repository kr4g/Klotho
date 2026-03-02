_PLAYBACK_KWARGS = frozenset(
    {
        "beat",
        "bpm",
        "amp",
        "glow",
        "arp",
        "strum",
        "direction",
        "dur",
        "pause",
        "loop",
        "ring_time",
    }
)


class KlothoPlot:
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
            kw = {**self._kwargs, "animate": False}
            self._static_fig = self._plot_fn(self._obj, **kw)
        return self._static_fig

    def _static_html(self):
        fig = self._build_static()
        if hasattr(fig, "to_html"):
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

    def play(self, dur=0.5, loop=None, **play_kwargs):
        from klotho.utils.playback._session_boot import boot_supersonic

        boot_supersonic()
        from IPython.display import display, HTML

        merged_play = {**self._play_kwargs, **play_kwargs}
        if "loop" in play_kwargs:
            merged_play["loop"] = play_kwargs["loop"]
        elif loop is not None:
            merged_play["loop"] = loop
        else:
            merged_play["loop"] = merged_play.get("loop", False)
        kw = {**self._kwargs, "animate": True, "dur": dur, **merged_play}
        fig = self._plot_fn(self._obj, **kw)
        if hasattr(fig, "to_html"):
            html_content = HTML(fig.to_html())
        else:
            html_content = fig

        if self._display_handle is not None:
            self._display_handle.update(html_content)
        else:
            display(html_content)
