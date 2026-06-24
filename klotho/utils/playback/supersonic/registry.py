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


def register_compiled(def_name: str, compiled_bytes: bytes, controls: dict) -> str:
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

    Returns
    -------
    str
        ``def_name`` (for convenience / chaining).
    """
    _RUNTIME[def_name] = {
        "b64": base64.b64encode(bytes(compiled_bytes)).decode("ascii"),
        "controls": dict(controls),
    }
    return def_name


def runtime_assets() -> dict:
    """Return ``{def_name: base64_bytes}`` for all runtime-registered synths."""
    return {name: entry["b64"] for name, entry in _RUNTIME.items()}


def runtime_controls() -> dict:
    """Return ``{def_name: {control: default}}`` for all runtime synths."""
    return {name: dict(entry["controls"]) for name, entry in _RUNTIME.items()}


def is_registered(def_name: str) -> bool:
    return def_name in _RUNTIME


def clear_runtime() -> None:
    """Drop all runtime registrations (primarily for tests)."""
    _RUNTIME.clear()


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
    return dict(synth.get("named_parameters", {}))


def register_synthdef(supriya_synthdef, name: str = None, pfields: dict = None):
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

    Returns
    -------
    SynthDefInstrument
        An instrument whose ``defName`` is the registered name and whose
        pfields are the synth's controls (with ``pfields`` overrides).
    """
    from klotho.thetos.instruments.synthdef import SynthDefInstrument

    compiled = supriya_synthdef.compile()
    def_name = name or supriya_synthdef.name
    controls = _controls_from_compiled(compiled, supriya_synthdef.name)
    register_compiled(def_name, compiled, controls)
    return SynthDefInstrument.from_manifest(def_name, **(pfields or {}))
