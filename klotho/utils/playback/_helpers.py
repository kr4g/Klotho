from pathlib import Path

_ANIMATION_BRIDGE_JS_PATH = Path(__file__).parent / '_animation_bridge.js'
_ANIMATION_BRIDGE_JS_CACHE = None


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
