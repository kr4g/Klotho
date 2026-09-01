from pathlib import Path
import json

_SS_MANIFEST_PATH = Path(__file__).parents[2] / 'utils' / 'playback' / 'supersonic' / 'assets' / 'manifest.json'
_SS_KINDS_PATH = Path(__file__).parents[2] / 'utils' / 'playback' / 'supersonic' / 'assets' / 'kinds.json'
_SS_IO_PATH = Path(__file__).parents[2] / 'utils' / 'playback' / 'supersonic' / 'assets' / 'io.json'
_SS_DISK_MANIFEST_CACHE = None
_SS_DISK_KINDS_CACHE = None
_SS_DISK_IO_CACHE = None

def _load_disk_manifest():
    global _SS_DISK_MANIFEST_CACHE
    if _SS_DISK_MANIFEST_CACHE is None:
        if _SS_MANIFEST_PATH.exists():
            _SS_DISK_MANIFEST_CACHE = json.loads(_SS_MANIFEST_PATH.read_text())
        else:
            _SS_DISK_MANIFEST_CACHE = {}
    return _SS_DISK_MANIFEST_CACHE


_SS_MANIFEST_MERGE_CACHE = (None, None)  # (registry_version, merged dict)
_SS_KINDS_MERGE_CACHE = (None, None)
_SS_IO_MERGE_CACHE = (None, None)


def load_ss_manifest():
    """Return the flat ``{synth_name: {control_name: default_value}}`` dict.

    The on-disk manifest is auto-regenerated from compiled ``.scsyndef``
    files; see ``07_PLAYBACK.md`` for the schema.  Any SynthDefs
    registered at runtime via
    :mod:`klotho.utils.playback.supersonic.registry` are overlaid on top
    (taking precedence) so they are immediately introspectable by the
    instrument layer and the browser auto-release logic.

    The merged view is memoized on the registry's version counter — it
    was rebuilt (183 keys) on every call.
    """
    global _SS_MANIFEST_MERGE_CACHE
    from klotho.utils.playback.supersonic.registry import (
        registry_version, runtime_controls)
    version = registry_version()
    if _SS_MANIFEST_MERGE_CACHE[0] == version:
        return _SS_MANIFEST_MERGE_CACHE[1]
    merged = {**_load_disk_manifest(), **runtime_controls()}
    _SS_MANIFEST_MERGE_CACHE = (version, merged)
    return merged


def _load_disk_kinds():
    global _SS_DISK_KINDS_CACHE
    if _SS_DISK_KINDS_CACHE is None:
        if _SS_KINDS_PATH.exists():
            _SS_DISK_KINDS_CACHE = json.loads(_SS_KINDS_PATH.read_text())
        else:
            _SS_DISK_KINDS_CACHE = {}
    return _SS_DISK_KINDS_CACHE


def load_ss_kinds():
    """Return the ``{synth_name: 'inst' | 'fx' | 'infra'}`` kind map.

    Derived from the asset subfolder layout by the manifest regeneration
    script; runtime registrations are overlaid on top. Names absent from
    the map should be treated as ``'inst'`` (see :func:`ss_synth_kind`).
    """
    global _SS_KINDS_MERGE_CACHE
    from klotho.utils.playback.supersonic.registry import (
        registry_version, runtime_kinds)
    version = registry_version()
    if _SS_KINDS_MERGE_CACHE[0] == version:
        return _SS_KINDS_MERGE_CACHE[1]
    merged = {**_load_disk_kinds(), **runtime_kinds()}
    _SS_KINDS_MERGE_CACHE = (version, merged)
    return merged


def _load_disk_io():
    global _SS_DISK_IO_CACHE
    if _SS_DISK_IO_CACHE is None:
        if _SS_IO_PATH.exists():
            _SS_DISK_IO_CACHE = json.loads(_SS_IO_PATH.read_text())
        else:
            _SS_DISK_IO_CACHE = {}
    return _SS_DISK_IO_CACHE


def load_ss_io():
    """Return the ``{synth_name: {'ins': n, 'outs': n, ...}}`` bus-I/O map.

    ``manifest.json`` records control names and defaults but no channel
    counts, so nothing in it can tell a 2-channel insert from a 24-channel
    one.  ``io.json`` is the sidecar that does; see
    ``scripts/regenerate_manifest.py`` for the schema and for how ``ins``
    and ``outs`` are derived from the compiled UGen graph.

    Runtime registrations are overlaid on top, exactly as in
    :func:`load_ss_manifest` and :func:`load_ss_kinds`, so a SynthDef
    authored with Supriya and passed to ``register_synthdef`` is width-
    checkable the moment it is registered.

    A name absent from the merged map has **no recorded width**.  That is
    not the same as a width of zero and must never be treated as one: a
    caller that needs a width refuses rather than guesses (a guess would
    reserve a loudspeaker channel that does not exist).
    """
    global _SS_IO_MERGE_CACHE
    from klotho.utils.playback.supersonic.registry import (
        registry_version, runtime_io)
    version = registry_version()
    if _SS_IO_MERGE_CACHE[0] == version:
        return _SS_IO_MERGE_CACHE[1]
    merged = {**_load_disk_io(), **runtime_io()}
    _SS_IO_MERGE_CACHE = (version, merged)
    return merged


def ss_synth_io(def_name):
    """Return the ``io.json`` record for ``def_name``, or ``None``.

    ``None`` means "no width recorded", which callers must refuse on
    rather than default.
    """
    return load_ss_io().get(canonical_def_name(def_name))


def ss_synth_channels(def_name):
    """Return ``(ins, outs)`` bus widths for ``def_name``.

    Either element is ``None`` when the width is unknown -- because the
    def has no record at all, or because its record says ``null`` (a
    packed UGen input the generator refused to guess at).  A caller that
    needs a definite width must check for ``None`` and refuse.
    """
    rec = ss_synth_io(def_name)
    if not rec:
        return None, None
    return rec.get('ins'), rec.get('outs')


def canonical_def_name(name):
    """'edm/kick' -> 'edm_kick'; idempotent; non-strings/plain names pass through.

    ``'/'`` is reserved path syntax (it cannot appear in a real SynthDef
    name, since the on-disk def name is the ``.scsyndef`` filename), so
    the transform is purely syntactic — no alias table.
    """
    if isinstance(name, str) and '/' in name:
        return name.replace('/', '_')
    return name


def ss_synth_kind(def_name):
    """Return ``'inst'``, ``'fx'``, or ``'infra'`` for ``def_name``.

    Unknown names default to ``'inst'`` (permissive: user-supplied or
    external defs are assumed playable).
    """
    def_name = canonical_def_name(def_name)
    if isinstance(def_name, str) and def_name.startswith('__'):
        return 'infra'
    return load_ss_kinds().get(def_name, 'inst')


def ss_synth_controls(def_name):
    """Return the ``{control_name: default_value}`` dict for ``def_name``.

    Returns an empty dict if the synth is not in the manifest.
    """
    def_name = canonical_def_name(def_name)
    return load_ss_manifest().get(def_name, {})


def synth_has_gate(def_name):
    """Return ``True`` if the synthdef declares a ``gate`` control."""
    return 'gate' in ss_synth_controls(def_name)


# Deprecated: kept for backward compatibility with external callers that
# expected the old wrapped-meta shape ({'controls': ..., 'releaseMode': ...}).
# Returns just the controls dict now.
def ss_synth_meta(def_name):
    return ss_synth_controls(def_name)
