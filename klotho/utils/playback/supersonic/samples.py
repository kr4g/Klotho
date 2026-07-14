"""Bundled audio sample assets for the SuperSonic engine.

Samples live in per-kit subfolders of ``assets/samples/`` next to a
``samples.json`` manifest mapping sample names to file metadata::

    {"bb_kick": {"file": "beatbox/0_bb_kick.wav", "group": "beatbox",
                 "channels": 2, "sampleRate": 44100, "frames": 27263,
                 "duration": 0.618209}, ...}

Events reference samples symbolically (``buf`` pfields carry the sample
name as a string); the browser widget loads each referenced sample into
an scsynth buffer via SuperSonic's ``loadSample`` and the scheduler
substitutes the allocated bufnum at OSC-assembly time.
"""

import base64
import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).parent / "assets" / "samples"
_SAMPLES_MANIFEST_PATH = SAMPLES_DIR / "samples.json"

_MANIFEST_CACHE = None
_B64_CACHE = {}


def load_sample_manifest():
    """Return the ``{name: {file, channels, sampleRate, frames, duration}}``
    manifest for the bundled sample assets (insertion order preserved)."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is None:
        if _SAMPLES_MANIFEST_PATH.exists():
            _MANIFEST_CACHE = json.loads(_SAMPLES_MANIFEST_PATH.read_text())
        else:
            _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


def sample_names(group=None):
    """Return bundled sample names in manifest order.

    Parameters
    ----------
    group : str or None, optional
        Restrict to one sample group (kit subfolder), e.g. ``'beatbox'``
        or ``'tabla'``.
    """
    manifest = load_sample_manifest()
    if group is None:
        return list(manifest.keys())
    return [n for n, info in manifest.items() if info.get('group') == group]


def sample_groups():
    """Return the available sample group names, in manifest order."""
    groups = []
    for info in load_sample_manifest().values():
        g = info.get('group')
        if g and g not in groups:
            groups.append(g)
    return groups


def sample_info(name):
    """Return the manifest entry for *name*.

    Raises
    ------
    KeyError
        If *name* is not a bundled sample.
    """
    manifest = load_sample_manifest()
    if name not in manifest:
        available = ', '.join(sorted(manifest.keys()))
        raise KeyError(
            f"Unknown sample {name!r}. Bundled samples: {available}"
        )
    return manifest[name]


def sample_bytes_b64(name):
    """Return the raw WAV bytes of sample *name*, base64-encoded (cached)."""
    if name not in _B64_CACHE:
        info = sample_info(name)
        path = SAMPLES_DIR / info["file"]
        _B64_CACHE[name] = base64.b64encode(path.read_bytes()).decode("ascii")
    return _B64_CACHE[name]
