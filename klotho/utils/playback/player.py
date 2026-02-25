from .tonejs import ToneEngine, convert_to_events


def play(obj, custom_js_path=None, custom_js=None, **kwargs):
    """
    Play a musical object in a Jupyter notebook using Tone.js.

    Converts the given object to audio events and renders an
    interactive playback widget via the :class:`ToneEngine`.

    Parameters
    ----------
    obj : object
        A Klotho musical object (e.g. ``Pitch``, ``Chord``, ``Scale``,
        ``RhythmTree``, ``TemporalUnit``, ``CompositionalUnit``).
    custom_js_path : str or Path, optional
        Path to a custom JavaScript file to load in the widget.
    custom_js : str, optional
        Inline custom JavaScript source to embed in the widget.
    **kwargs
        Forwarded to :func:`convert_to_events` (e.g. ``dur``, ``arp``,
        ``strum``, ``mode``).

    Returns
    -------
    IPython.display.DisplayHandle
        The displayed HTML widget handle.
    """
    events = convert_to_events(obj, **kwargs)
    engine = ToneEngine(events, custom_js_path=custom_js_path, custom_js=custom_js)
    return engine.display()
