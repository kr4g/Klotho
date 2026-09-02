import functools
import inspect
import os

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
        "equaves",
        "pause",
        "loop",
        "ring_time",
        "inst",
        "defName",
        "record",
    }
)


def transport_kwargs(kwargs):
    """``ring_time``/``loop`` animated-figure options from plot/play kwargs."""
    kw = kwargs or {}
    return {"ring_time": kw.get("ring_time", 5), "loop": kw.get("loop", False)}


_HTML_SUFFIXES = ('.html', '.htm')


def save_figure(fig, output_file):
    """Write a rendered SVG/Three.js/animated figure to ``output_file``.

    ``.html`` writes ``fig.to_html()`` -- the interactive figure, tooltips
    and playback controls included. ``.svg`` writes only the ``<svg>``
    element, which is a static picture: the tooltip and animation layers
    live in sibling ``<div>`` and ``<script>`` elements and cannot travel
    inside an SVG document, so they are dropped rather than silently
    half-written.

    Any other extension raises. These figures have no raster pipeline
    (nothing here is a matplotlib or plotly figure that could be handed to
    ``write_image``), and quietly writing HTML into a file named ``.png``
    would be the same class of silence this function exists to remove.
    """
    ext = os.path.splitext(output_file)[1].lower()

    if ext in _HTML_SUFFIXES:
        to_html = getattr(fig, 'to_html', None)
        if to_html is None:
            raise ValueError(
                f"Cannot write {output_file}: this figure "
                f"({type(fig).__name__}) has no to_html()."
            )
        with open(output_file, 'w', encoding='utf-8') as fh:
            fh.write(to_html())
        return output_file

    if ext == '.svg':
        svg_str = getattr(fig, 'svg_str', None)
        if not svg_str:
            raise ValueError(
                f"Cannot write {output_file}: this figure "
                f"({type(fig).__name__}) is an HTML widget, not a single "
                f"SVG element. Save it as .html instead."
            )
        if svg_str.count('<svg') != 1:
            raise ValueError(
                f"Cannot write {output_file}: the rendered figure contains "
                f"{svg_str.count('<svg')} <svg> elements, so there is no one "
                f"element to save. Save it as .html instead."
            )
        start = svg_str.index('<svg')
        end = svg_str.rindex('</svg>') + len('</svg>')
        with open(output_file, 'w', encoding='utf-8') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            fh.write(svg_str[start:end])
        return output_file

    raise ValueError(
        f"Unsupported output_file extension {ext!r} for {output_file}: "
        f"these figures serialize as '.html' (interactive) or '.svg' "
        f"(static picture)."
    )


def honors_output_file(fn):
    """Make a dispatcher's declared ``output_file`` parameter do something.

    Four dispatchers declared and documented ``output_file`` and then never
    read it, so ``plot(cps, output_file='x.html')`` produced no file, no
    warning and no error (AUD-35). Each of them has many return points, so
    the save is applied here once, around the whole call, rather than
    repeated at every ``return`` where one could later be missed.

    The parameter stays in the wrapped function's own signature, so
    ``inspect.signature`` and the docstrings are unchanged; this wrapper
    intercepts the value -- keyword or positional -- and passes ``None``
    through to a body that ignores it.

    A figure reached through :class:`KlothoPlot` is rendered twice, once
    statically and again on ``.play()``, and the file is written on each
    render: ``plot(rt, output_file='x.html').play()`` leaves the *animated*
    figure on disk.
    """
    index = list(inspect.signature(fn).parameters).index('output_file')

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if 'output_file' in kwargs and len(args) > index:
            # Python would raise this itself if the parameter were not
            # intercepted here; keep the same answer rather than quietly
            # preferring one of the two values.
            raise TypeError(
                f"{fn.__name__}() got multiple values for argument "
                f"'output_file'"
            )
        if 'output_file' in kwargs:
            output_file = kwargs.pop('output_file')
        elif len(args) > index:
            output_file = args[index]
            args = args[:index] + (None,) + args[index + 1:]
        else:
            output_file = None
        fig = fn(*args, **kwargs)
        if output_file:
            save_figure(fig, output_file)
        return fig

    return wrapper


class KlothoPlot:
    def __init__(self, plot_fn, obj, kwargs):
        self._plot_fn = plot_fn
        self._obj = obj
        self._play_kwargs = {k: v for k, v in kwargs.items() if k in _PLAYBACK_KWARGS}
        self._kwargs = {k: v for k, v in kwargs.items()
                        if k not in _PLAYBACK_KWARGS and k != 'output_file'}
        # ``output_file`` belongs to the STATIC render and fires exactly once.
        # Left in ``_kwargs`` it re-fired on every subsequent render, and
        # ``.play()`` renders an animated widget -- which has no single ``<svg>``
        # element -- so `plot(obj, output_file='x.svg').play()` raised instead of
        # playing, after the picture had already been written correctly. Writing
        # an animation over the file the caller asked a picture for would have
        # been no better; the file is the still image, and the caller asked for
        # one of them.
        self._output_file = kwargs.get('output_file')
        self._static_fig = None
        self._display_handle = None
        self._eager_display()

    def _build_static(self):
        if self._static_fig is None:
            kw = {**self._kwargs, "animate": False}
            if self._output_file is not None:
                kw["output_file"] = self._output_file
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

    def play(self, dur=None, loop=None, **play_kwargs):
        """Render the animated figure and display it.

        ``dur`` and ``loop`` may each be given at plot time
        (``plot(obj, dur=...)``) or here at play time. Play time wins:
        it is the caller's later word, and the plot-time value was a
        default for a figure that has since been re-rendered.

        ``dur`` defaults to ``None`` rather than ``0.5`` so that "the
        caller passed nothing" stays distinguishable from "the caller
        passed 0.5". With a literal default, ``dur`` was always present
        and ``**merged_play`` -- unpacked after it -- silently put the
        plot-time value back, so ``plot(obj, dur=3).play(dur=10)`` played
        at 3 with no warning (AUD-114). ``loop`` already had the sentinel
        and already behaved correctly.
        """
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
        if dur is not None:
            merged_play["dur"] = dur
        else:
            merged_play.setdefault("dur", 0.5)
        kw = {**self._kwargs, "animate": True, **merged_play}
        fig = self._plot_fn(self._obj, **kw)
        if hasattr(fig, "to_html"):
            html_content = HTML(fig.to_html())
        else:
            html_content = fig

        if self._display_handle is not None:
            self._display_handle.update(html_content)
        else:
            display(html_content)
