from .tonejs import ToneEngine, convert_to_events
from ._config import get_audio_engine


def play(obj, engine=None, custom_js_path=None, custom_js=None, **kwargs):
    """
    Play a musical object in a Jupyter notebook.

    Converts the given object to audio events and renders an
    interactive playback widget via the selected audio engine.

    Parameters
    ----------
    obj : object
        A Klotho musical object (e.g. ``Pitch``, ``Chord``, ``Scale``,
        ``RhythmTree``, ``TemporalUnit``, ``CompositionalUnit``).
    engine : str or None, optional
        Audio engine to use: ``'tone'`` (Tone.js) or ``'supersonic'``
        (SuperSonic / browser scsynth).  When ``None``, uses the global
        default set by :func:`set_audio_engine` (initially ``'tone'``).
    custom_js_path : str or Path, optional
        Path to a custom JavaScript file to load in the widget
        (Tone.js engine only).
    custom_js : str, optional
        Inline custom JavaScript source to embed in the widget
        (Tone.js engine only).
    **kwargs
        Forwarded to the converter (e.g. ``dur``, ``arp``,
        ``strum``, ``mode``).

    Returns
    -------
    IPython.display.DisplayHandle
        The displayed HTML widget handle.
    """
    if engine is None:
        engine = get_audio_engine()

    if engine == "supersonic":
        from .supersonic import SuperSonicEngine, convert_to_sc_events
        events = convert_to_sc_events(obj, **kwargs)
        return SuperSonicEngine(events).display()
    else:
        events = convert_to_events(obj, **kwargs)
        return ToneEngine(events, custom_js_path=custom_js_path, custom_js=custom_js).display()
