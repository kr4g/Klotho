_VALID_ENGINES = ("tone", "supersonic")

_current_engine = "supersonic"


def set_audio_engine(engine):
    global _current_engine
    if engine not in _VALID_ENGINES:
        raise ValueError(
            f"Unknown audio engine {engine!r}. "
            f"Choose from: {', '.join(_VALID_ENGINES)}"
        )
    _current_engine = engine


def get_audio_engine():
    return _current_engine
