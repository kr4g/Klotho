_VALID_ENGINES = ("supersonic",)

_current_engine = "supersonic"


def set_audio_engine(engine):
    """Select the global audio engine used by :func:`~klotho.utils.playback.player.play`.

    Parameters
    ----------
    engine : {'supersonic'}
        The engine to use. ``'supersonic'`` (the default and only engine)
        renders SuperCollider synthesis in the browser via WebAssembly.

    Raises
    ------
    ValueError
        If ``engine`` is not a recognized engine name. The Tone.js engine
        (``'tone'``) was removed in Klotho 10.12; playback is
        SuperSonic-only.
    """
    global _current_engine
    if engine not in _VALID_ENGINES:
        raise ValueError(
            f"Unknown audio engine {engine!r}. "
            f"Choose from: {', '.join(_VALID_ENGINES)}. "
            f"(The Tone.js engine was removed in Klotho 10.12.)"
        )
    _current_engine = engine


def get_audio_engine():
    """Return the name of the currently selected audio engine.

    Returns
    -------
    str
        Always ``'supersonic'``.
    """
    return _current_engine
