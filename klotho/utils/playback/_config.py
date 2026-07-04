_VALID_ENGINES = ("tone", "supersonic")

_current_engine = "supersonic"


def set_audio_engine(engine):
    """Select the global audio engine used by :func:`~klotho.utils.playback.player.play`.

    Parameters
    ----------
    engine : {'supersonic', 'tone'}
        The engine to use. ``'supersonic'`` (the default) renders SuperCollider
        synthesis in the browser via WebAssembly; ``'tone'`` uses Tone.js.

    Raises
    ------
    ValueError
        If ``engine`` is not a recognized engine name.
    """
    global _current_engine
    if engine not in _VALID_ENGINES:
        raise ValueError(
            f"Unknown audio engine {engine!r}. "
            f"Choose from: {', '.join(_VALID_ENGINES)}"
        )
    _current_engine = engine


def get_audio_engine():
    """Return the name of the currently selected audio engine.

    Returns
    -------
    str
        Either ``'supersonic'`` or ``'tone'``.
    """
    return _current_engine
