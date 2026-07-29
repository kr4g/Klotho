"""Audio sample assets for the SuperSonic engine: bundled + runtime.

Bundled samples live in per-kit subfolders of ``assets/samples/`` next to
a ``samples.json`` manifest mapping sample names to file metadata::

    {"bb_kick": {"file": "beatbox/0_bb_kick.wav", "group": "beatbox",
                 "channels": 2, "sampleRate": 44100, "frames": 27263,
                 "duration": 0.618209}, ...}

User samples are added at runtime with :func:`register_sample` (used
under the hood by ``SynthDefInstrument.sampler(path)`` and
``SynthDefKit.from_folder``); they overlay the bundled manifest in every
accessor here, so the instrument layer, the engine's sample collection,
and the animated-payload builders all see them with no further changes.

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

# name -> {"info": manifest-shaped dict, "b64": str}. Runtime entries win
# over bundled ones in every accessor, but claiming a bundled name
# requires replace=True (so a student's local file can never silently
# shadow e.g. 'bb_kick').
_RUNTIME_SAMPLES = {}


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


def register_sample(name, source, *, group="user", replace=False):
    """Register a user WAV sample under *name* for this session.

    Once registered, the name works everywhere a bundled sample name
    does: ``SynthDefInstrument.sampler(name)``, ``buf`` pfields,
    ``SynthDefKit.from_samples``, and the playback widgets (the bytes are
    embedded in each widget's HTML, exactly like bundled samples).

    Parameters
    ----------
    name : str
        The sample name events will reference.
    source : str, Path, or bytes
        Path to a ``.wav`` file, or the raw WAV bytes.
    group : str, optional
        Group label (used by ``sample_names(group=...)`` /
        ``sample_groups()``; kits register their members under the kit
        name).
    replace : bool, optional
        Required to overwrite a bundled sample name or an existing
        runtime registration with different audio. Re-registering
        identical bytes is always a no-op.

    Returns
    -------
    str
        *name*, for convenience.
    """
    from klotho.utils.playback.supersonic._wav_meta import wav_metadata

    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Sample file not found: {path}")
        data = path.read_bytes()
        file_label = str(path)
    elif isinstance(source, (bytes, bytearray)):
        data = bytes(source)
        file_label = "<memory>"
    else:
        raise TypeError(
            f"source must be a path or bytes, got {type(source).__name__}"
        )

    try:
        meta = wav_metadata(data)
    except ValueError as exc:
        raise ValueError(f"{name!r} ({file_label}): {exc}") from None

    b64 = base64.b64encode(data).decode("ascii")

    existing = _RUNTIME_SAMPLES.get(name)
    if existing is not None:
        if existing["b64"] == b64:
            return name
        if not replace:
            raise ValueError(
                f"Sample {name!r} is already registered with different "
                f"audio. Pass replace=True to overwrite, or register "
                f"under another name: register_sample('my_{name}', ...)"
            )
    elif name in load_sample_manifest() and not replace:
        raise ValueError(
            f"{name!r} is a bundled Klotho sample. Pass replace=True to "
            f"shadow it, or register under another name."
        )

    _RUNTIME_SAMPLES[name] = {
        "info": {
            "file": file_label,
            "group": group,
            "channels": meta["channels"],
            "sampleRate": meta["sampleRate"],
            "frames": meta["frames"],
            "duration": meta["duration"],
        },
        "b64": b64,
    }
    return name


def unregister_sample(name):
    """Drop a runtime sample registration (bundled samples are untouched)."""
    _RUNTIME_SAMPLES.pop(name, None)


def registered_samples():
    """Return the runtime-registered sample names, in registration order."""
    return list(_RUNTIME_SAMPLES.keys())


def clear_runtime_samples():
    """Drop all runtime sample registrations (primarily for tests)."""
    _RUNTIME_SAMPLES.clear()


def sample_names(group=None):
    """Return sample names — bundled (manifest order) then runtime-registered.

    Parameters
    ----------
    group : str or None, optional
        Restrict to one sample group, e.g. ``'beatbox'``, ``'tabla'``, or
        a group used at :func:`register_sample` time.
    """
    manifest = load_sample_manifest()
    names = []
    for n, info in manifest.items():
        if n in _RUNTIME_SAMPLES:
            continue  # replaced: listed with its runtime group below
        if group is None or info.get('group') == group:
            names.append(n)
    for n, entry in _RUNTIME_SAMPLES.items():
        if group is None or entry["info"].get('group') == group:
            names.append(n)
    return names


def sample_groups():
    """Return the available sample group names (bundled, then runtime)."""
    groups = []
    for info in load_sample_manifest().values():
        g = info.get('group')
        if g and g not in groups:
            groups.append(g)
    for entry in _RUNTIME_SAMPLES.values():
        g = entry["info"].get('group')
        if g and g not in groups:
            groups.append(g)
    return groups


def sample_info(name):
    """Return the manifest entry for *name* (runtime registrations win).

    Raises
    ------
    KeyError
        If *name* is neither bundled nor registered.
    """
    entry = _RUNTIME_SAMPLES.get(name)
    if entry is not None:
        return entry["info"]
    manifest = load_sample_manifest()
    if name not in manifest:
        available = ', '.join(sorted(manifest.keys()))
        registered = ', '.join(_RUNTIME_SAMPLES.keys()) or 'none'
        raise KeyError(
            f"Unknown sample {name!r}. Bundled samples: {available}. "
            f"Registered this session: {registered}. Add your own with "
            f"register_sample(name, path) or by passing a .wav path to "
            f"SynthDefInstrument.sampler()."
        )
    return manifest[name]


def sample_bytes_b64(name):
    """Return the raw WAV bytes of sample *name*, base64-encoded (cached)."""
    entry = _RUNTIME_SAMPLES.get(name)
    if entry is not None:
        return entry["b64"]
    if name not in _B64_CACHE:
        info = sample_info(name)
        path = SAMPLES_DIR / info["file"]
        _B64_CACHE[name] = base64.b64encode(path.read_bytes()).decode("ascii")
    return _B64_CACHE[name]
