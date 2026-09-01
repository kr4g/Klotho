"""Runtime, in-memory registry for SuperSonic SynthDefs.

This module lets callers register compiled SuperCollider SynthDefs at
runtime (e.g. ones authored with Supriya) so the SuperSonic engine can
load them in the browser and the instrument layer can build a
:class:`~klotho.thetos.instruments.synthdef.SynthDefInstrument` for them
-- all without writing any files to the package assets directory.

Two pieces of state must be made available for a registered synth:

- the compiled ``.scsyndef`` bytes (base64-encoded) so the browser
  scsynth can ``loadSynthDef`` them, and
- the ``{control_name: default_value}`` controls dict so the Python
  instrument layer and the browser auto-release logic can introspect it.

The on-disk asset/manifest loaders in
:mod:`klotho.utils.playback.supersonic.engine` and
:mod:`klotho.thetos.instruments._shared` overlay these runtime maps on
each call, so registrations take effect immediately (no reimport).
"""

import base64

_RUNTIME: dict[str, dict] = {}

#: Folder name -> taxonomy kind, mirroring the layout under ``synthdefs/``.
_FOLDER_TO_KIND = {"instruments": "inst", "effects": "fx", "infra": "infra"}
_REGISTRY_VERSION = 0


def _round_default(v):
    """Undo float32 round-off in a SynthDef control default.

    A compiled ``.scsyndef`` stores defaults as float32, so ``0.08`` comes
    back as ``0.07999999821186066``. The bundled manifest is built with this
    applied (see ``scripts/regenerate_manifest.build_manifest``), so runtime
    registration must apply it too or the same synth reports different
    defaults depending on how it was loaded.
    """
    try:
        return float(f"{v:.7g}")
    except (TypeError, ValueError):
        return v


def registry_version() -> int:
    """Monotonic counter bumped on every runtime (un)registration; lets
    consumers memoize merged manifest views."""
    return _REGISTRY_VERSION


def register_compiled(def_name: str, compiled_bytes: bytes, controls: dict,
                      kind: str = "inst") -> str:
    """Register a compiled SynthDef's bytes + controls under ``def_name``.

    Parameters
    ----------
    def_name : str
        The SynthDef name (must match the name embedded in the compiled
        bytes so the browser registers it under the same key).
    compiled_bytes : bytes
        The compiled ``.scsyndef`` blob.
    controls : dict
        ``{control_name: default_value}`` for the synth.
    kind : str, optional
        ``'inst'`` (default) or ``'fx'`` — how the def participates in
        the instrument/effect taxonomy.

    Returns
    -------
    str
        ``def_name`` (for convenience / chaining).
    """
    if kind not in ("inst", "fx"):
        raise ValueError(f"kind must be 'inst' or 'fx', got {kind!r}")
    global _REGISTRY_VERSION
    _RUNTIME[def_name] = {
        "b64": base64.b64encode(bytes(compiled_bytes)).decode("ascii"),
        "controls": dict(controls),
        "kind": kind,
        "io": _io_from_compiled(compiled_bytes, def_name),
    }
    _REGISTRY_VERSION += 1
    return def_name


def runtime_assets() -> dict:
    """Return ``{def_name: base64_bytes}`` for all runtime-registered synths."""
    return {name: entry["b64"] for name, entry in _RUNTIME.items()}


def runtime_controls() -> dict:
    """Return ``{def_name: {control: default}}`` for all runtime synths."""
    return {name: dict(entry["controls"]) for name, entry in _RUNTIME.items()}


def runtime_kinds() -> dict:
    """Return ``{def_name: kind}`` for all runtime-registered synths."""
    return {name: entry.get("kind", "inst") for name, entry in _RUNTIME.items()}


def runtime_io() -> dict:
    """Return ``{def_name: io_record}`` for all runtime-registered synths.

    Same record shape as ``assets/io.json`` (``ins``/``outs``/``reads``/
    ``writes``), and produced by the same function, so a Supriya-authored
    def is width-checkable exactly like a bundled one.  A def whose widths
    could not be derived is **omitted**, not recorded as zero: a missing
    entry means "refuse", and a zero would read as "touches no bus".
    """
    return {name: entry["io"] for name, entry in _RUNTIME.items()
            if entry.get("io")}


def is_registered(def_name: str) -> bool:
    """Return True if ``def_name`` has been registered at runtime."""
    return def_name in _RUNTIME


def clear_runtime() -> None:
    """Drop all runtime registrations (primarily for tests)."""
    global _REGISTRY_VERSION
    _RUNTIME.clear()
    _REGISTRY_VERSION += 1


def _controls_from_compiled(compiled_bytes: bytes, def_name: str) -> dict:
    """Extract ``{control: default}`` from compiled SynthDef bytes.

    Uses the vendored ``synthdef_parser`` (SCgf v2).  Falls back to the
    first synth in the file if ``def_name`` is not found.
    """
    from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
        parse_synthdef,
    )

    parsed = parse_synthdef(bytes(compiled_bytes))
    synths = parsed.get("synths", {})
    synth = synths.get(def_name)
    if synth is None and synths:
        synth = next(iter(synths.values()))
    if synth is None:
        return {}
    return {k: _round_default(v)
            for k, v in synth.get("named_parameters", {}).items()}


def _io_from_compiled(compiled_bytes: bytes, def_name: str):
    """Extract the ``io.json`` record from compiled SynthDef bytes.

    Delegates to ``scripts.regenerate_manifest._io_for_synth`` -- the same
    derivation that built the bundled sidecar -- so a runtime-registered
    def and a bundled one can never disagree about what ``outs`` means.
    Imported lazily: that module imports this one at module scope.

    Returns ``None`` when the bytes cannot be parsed or the named synth is
    not in them.  ``None`` propagates as "no recorded width", which the
    width validators refuse on; inventing a 2 here is exactly the guess
    that would reserve a loudspeaker channel that does not exist.
    """
    from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
        parse_synthdef,
    )
    from klotho.utils.playback.supersonic.scripts.regenerate_manifest import (
        _io_for_synth,
    )

    try:
        parsed = parse_synthdef(bytes(compiled_bytes))
    except Exception:
        return None
    synths = parsed.get("synths", {})
    synth = synths.get(def_name)
    if synth is None and synths:
        synth = next(iter(synths.values()))
    if synth is None:
        return None
    try:
        return _io_for_synth(synth)
    except Exception:
        return None


def register_compiled_file(path, kind: str = None):
    """Register every SynthDef in a compiled ``.scsyndef`` file on disk.

    The parsing and control extraction this does were previously reachable
    only by re-deriving them from ``build_manifest``, which builds the whole
    bundled manifest rather than registering one file.

    Parameters
    ----------
    path : str or pathlib.Path
        The ``.scsyndef`` file to read.
    kind : str, optional
        ``'inst'`` or ``'fx'``. When omitted it is inferred from the parent
        directory name (``instruments`` -> ``'inst'``, ``effects`` -> ``'fx'``).

    Returns
    -------
    str or list of str
        The registered def name, or the list of them when the file holds
        more than one synth.

    Raises
    ------
    ValueError
        If the file holds no SynthDef, or if *kind* resolves to ``'infra'`` --
        infrastructure defs (bus routers, the chain limiter) are Klotho
        internals and are bundled, not registered by callers.
    """
    from pathlib import Path

    from klotho.utils.playback.supersonic._vendor.synthdef_parser import (
        parse_synthdef_file,
    )

    p = Path(path)
    if kind is None:
        kind = _FOLDER_TO_KIND.get(p.parent.name, "inst")
    if kind == "infra":
        raise ValueError(
            f"{p.name} resolves to kind 'infra'. Infrastructure SynthDefs are "
            f"Klotho internals and ship with the package; pass kind='inst' or "
            f"kind='fx' explicitly if you really mean to register this one."
        )

    blob = p.read_bytes()
    synths = parse_synthdef_file(str(p)).get("synths", {})
    if not synths:
        raise ValueError(f"No SynthDef found in {p}")

    names = []
    for synth_name, synth in synths.items():
        controls = {k: _round_default(v)
                    for k, v in synth.get("named_parameters", {}).items()}
        register_compiled(synth_name, blob, controls, kind=kind)
        names.append(synth_name)
    return names[0] if len(names) == 1 else names


def register_synthdef(supriya_synthdef, name: str = None, pfields: dict = None,
                      kind: str = "inst"):
    """Compile + register a Supriya ``SynthDef`` and return an instrument.

    Supriya is imported lazily here so it is never a runtime dependency
    of Klotho itself; only callers that actually author SynthDefs need it
    installed.

    Parameters
    ----------
    supriya_synthdef : supriya.ugens.core.SynthDef
        A built Supriya SynthDef (e.g. from the ``@synthdef`` decorator or
        ``SynthDefBuilder.build()``).
    name : str, optional
        Override the registered def name.  Defaults to
        ``supriya_synthdef.name``.  Note the compiled bytes embed the
        Supriya name, so the browser will register under that name; pass
        ``name`` only when you also built the def with that name.
    pfields : dict, optional
        Extra pfield overrides applied on top of the synth's controls
        when building the :class:`SynthDefInstrument`.
    kind : str, optional
        ``'inst'`` (default) registers an instrument; ``'fx'`` registers
        an insert effect (usable with ``SynthDefFX`` / ``Score.track``
        but rejected by ``set_instrument``).

    Returns
    -------
    SynthDefInstrument
        An instrument whose ``defName`` is the registered name and whose
        pfields are the synth's controls (with ``pfields`` overrides).
        For ``kind='fx'``, returns ``None`` (build a ``SynthDefFX`` with
        the registered name instead).
    """
    from klotho.thetos.instruments.synthdef import SynthDefInstrument

    compiled = supriya_synthdef.compile()
    def_name = name or supriya_synthdef.name
    controls = _controls_from_compiled(compiled, supriya_synthdef.name)
    register_compiled(def_name, compiled, controls, kind=kind)
    if kind == "fx":
        return None
    return SynthDefInstrument.from_manifest(def_name, **(pfields or {}))
