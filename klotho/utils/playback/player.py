from .tonejs import ToneEngine, convert_to_events
from ._config import get_audio_engine
from ._session_boot import boot_supersonic

boot_supersonic()


def play(obj, engine=None, custom_js_path=None, custom_js=None, **kwargs):
    """
    Play a musical object in a Jupyter notebook.

    Converts the given object to audio events and renders an
    interactive playback widget via the selected audio engine.

    If *obj* is a :class:`KlothoPlot` (returned by :func:`plot`),
    delegates to its ``.play()`` method to display an animated figure
    with audio.

    If *obj* is a :class:`Score`, the universal dispatcher lowers its
    items via
    :func:`klotho.utils.playback.supersonic.converters.convert_score_to_sc_events`
    and renders a SuperSonic widget with track / FX metadata and
    control-envelope buses.

    Parameters
    ----------
    obj : object
        A Klotho musical object (e.g. ``Pitch``, ``Chord``, ``Scale``,
        ``RhythmTree``, ``TemporalUnit``, ``CompositionalUnit``),
        a ``Score``, or a ``KlothoPlot`` returned by :func:`plot`.
    engine : str or None, optional
        Audio engine to use: ``'tone'`` (Tone.js) or ``'supersonic'``
        (SuperSonic / browser scsynth).  When ``None``, uses the global
        default set by :func:`set_audio_engine` (initially ``'supersonic'``).
    custom_js_path : str or Path, optional
        Path to a custom JavaScript file to load in the widget
        (Tone.js engine only).
    custom_js : str, optional
        Inline custom JavaScript source to embed in the widget
        (Tone.js engine only).
    **kwargs
        Forwarded to the converter (e.g. ``dur``, ``arp``,
        ``strum``, ``mode``).  For :class:`Score`, ``ring_time`` is
        supported.

        ``loop`` sets the widget's initial loop policy, exactly as in
        ``plot(obj).play(loop=...)``: ``False`` (default) leaves the
        loop button off, ``True`` starts with infinite looping, and an
        int > 1 loops that many cycles.

        ``inst`` selects the instrument for pitch-like objects
        (``Pitch``, ``PitchCollection``, ``Scale``, ``Chord``,
        ``Spectrum``): pass a SynthDef name string (exact match,
        including Supriya defs registered via
        :func:`~klotho.utils.playback.supersonic.registry.register_synthdef`)
        or a ``SynthDefInstrument`` instance. Ignored (like ``dur``)
        for time-structured objects (``RhythmTree``, ``TemporalUnit``,
        ``TemporalUnitSequence``, ``TemporalBlock``,
        ``CompositionalUnit``, ``Score``), whose instruments come from
        their own structure. SuperSonic engine only.

    Returns
    -------
    IPython.display.DisplayHandle or KlothoPlot
        The displayed HTML widget handle, or the KlothoPlot after
        triggering its animation.
    """
    from klotho.thetos.composition.score import Score
    if isinstance(obj, Score):
        from klotho.utils.playback.supersonic import SuperSonicEngine
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )
        boot_supersonic()
        ring_time = kwargs.pop('ring_time', 5)
        loop = kwargs.pop('loop', False)
        payload = convert_score_to_sc_events(obj, **kwargs)
        engine_obj = SuperSonicEngine(
            payload["events"],
            meta=payload.get("meta"),
            control_data=payload.get("control_data"),
            ring_time=ring_time,
            loop=loop,
        )
        return engine_obj.display()

    from klotho.semeios.visualization._dispatch import KlothoPlot
    if isinstance(obj, KlothoPlot):
        return obj.play(**kwargs)

    boot_supersonic()

    if engine is None:
        engine = get_audio_engine()

    if engine == "supersonic":
        from .supersonic import SuperSonicEngine, convert_to_sc_events
        ring_time = kwargs.pop('ring_time', 5)
        loop = kwargs.pop('loop', False)

        from klotho.chronos.temporal_units.temporal import (
            TemporalBlock, TemporalUnitSequence,
        )
        from klotho.thetos.composition.compositional import CompositionalUnit
        if isinstance(obj, (CompositionalUnit, TemporalUnitSequence, TemporalBlock)):
            from .supersonic.converters import convert_to_sc_payload
            payload = convert_to_sc_payload(obj, **kwargs)
            return SuperSonicEngine(
                payload["events"],
                control_data=payload["control_data"],
                ring_time=ring_time,
                loop=loop,
            ).display()

        events = convert_to_sc_events(obj, **kwargs)
        return SuperSonicEngine(events, ring_time=ring_time, loop=loop).display()
    else:
        loop = kwargs.pop('loop', False)
        events = convert_to_events(obj, **kwargs)
        return ToneEngine(events, custom_js_path=custom_js_path, custom_js=custom_js,
                          loop=loop).display()
