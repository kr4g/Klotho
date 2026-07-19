from pathlib import Path

_ANIMATION_BRIDGE_JS_PATH = Path(__file__).parent / '_animation_bridge.js'
_ANIMATION_BRIDGE_JS_CACHE = None
_LOOP_CONTROL_JS_PATH = Path(__file__).parent / '_loop_control.js'
_LOOP_CONTROL_JS_CACHE = None


def normalize_loop_policy(loop):
    """Normalize a ``loop`` playback argument to ``(mode, count, enabled)``.

    ``False`` (default): infinite mode, loop button off. ``True``:
    infinite mode, button on. An int > 1: finite mode with that many
    cycles, button on. Anything else disables looping. Shared by the
    animated plot figures and the bare playback engines so
    ``play(obj, loop=...)`` and ``plot(obj).play(loop=...)`` behave
    identically.
    """
    if isinstance(loop, bool):
        return ("infinite", 0, loop)
    if isinstance(loop, int) and loop > 1:
        return ("finite", int(loop), True)
    return ("infinite", 0, False)


def get_loop_control_js():
    """The shared ``KlothoLoopControl`` widget JS (installed once per page)."""
    global _LOOP_CONTROL_JS_CACHE
    if _LOOP_CONTROL_JS_CACHE is None:
        _LOOP_CONTROL_JS_CACHE = _LOOP_CONTROL_JS_PATH.read_text() if _LOOP_CONTROL_JS_PATH.exists() else ""
    return _LOOP_CONTROL_JS_CACHE


def substitute_loop_tokens(template, loop):
    """Fill a JS template's ``__LOOP_MODE__/__LOOP_COUNT__/__LOOP_ENABLED__`` tokens."""
    mode, count, enabled = normalize_loop_policy(loop)
    return (template
            .replace('__LOOP_MODE__', mode)
            .replace('__LOOP_COUNT__', str(count))
            .replace('__LOOP_ENABLED__', 'true' if enabled else 'false'))


def get_animation_bridge_js():
    global _ANIMATION_BRIDGE_JS_CACHE
    if _ANIMATION_BRIDGE_JS_CACHE is None:
        _ANIMATION_BRIDGE_JS_CACHE = _ANIMATION_BRIDGE_JS_PATH.read_text() if _ANIMATION_BRIDGE_JS_PATH.exists() else ""
    return _ANIMATION_BRIDGE_JS_CACHE


def convert_numpy_types(obj):
    try:
        import numpy as np
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(v) for v in obj]
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        else:
            return obj
    except ImportError:
        return obj
