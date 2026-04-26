"""Canonical serialization of UC/Score state for parity testing.

Captures two levels:

- **Level 1 (compositional IR)**: per-UC state after user calls -
  ``uc.events``, ``uc._slur_specs``, ``uc._control_envelopes``,
  ``uc.resolved_control_envelopes()``.
- **Level 2 (post-lowering)**: actual playback event stream -
  ``lower_compositional_ir_to_sc_assembly(uc)`` per UC, and for
  Score scenarios, ``convert_score_to_sc_events(score)``.

Canonicalization normalizes:
- ``Fraction`` -> "num/den" string
- numpy scalars -> native Python scalars
- ``Envelope`` -> {"values", "times", "curve", "time_scale"} dict
- ``Instrument`` / ``Effect`` / ``Kit`` -> string display
- tuples -> lists (for JSON)
- dict keys sorted; set values sorted
- UUID-style hex strings (Effect uids, per-event new-event ids) replaced
  with "__id_{n}" placeholders in first-seen order per scenario, so cross-run
  parity comparisons are stable despite fresh uid generation.
"""

from __future__ import annotations

import re
from dataclasses import is_dataclass, asdict
from fractions import Fraction
from typing import Any

import numpy as np


_HEX_ID_RE = re.compile(r'^[0-9a-f]{12}(?:[0-9a-f]{20})?$')


def _is_hex_id(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) not in (12, 32):
        return False
    return bool(_HEX_ID_RE.match(value))


class _IdNormalizer:
    """Replace uuid-hex strings with stable ``__id_{n}`` placeholders by first-seen order."""

    def __init__(self):
        self._map: dict[str, str] = {}

    def __call__(self, value: str) -> str:
        if value in self._map:
            return self._map[value]
        placeholder = f"__id_{len(self._map)}"
        self._map[value] = placeholder
        return placeholder


def _envelope_to_dict(env) -> dict:
    return {
        "__type__": "Envelope",
        "values": list(getattr(env, "_values", getattr(env, "values", []))),
        "times": list(getattr(env, "_times", getattr(env, "times", []))),
        "curve": getattr(env, "_curve", None),
        "time_scale": getattr(env, "_time_scale", 1.0),
    }


def _instrument_display(inst) -> str:
    if inst is None:
        return None
    parts = [type(inst).__name__]
    for attr in ("_defName", "defName", "name"):
        val = getattr(inst, attr, None)
        if val:
            parts.append(str(val))
            break
    return ":".join(parts)


def _canonicalize(obj: Any, id_norm: _IdNormalizer) -> Any:
    # envelope first because it has specific attrs
    from klotho.dynatos.envelopes.envelopes import Envelope
    from klotho.thetos.instruments.base import Instrument, Effect, Kit

    if obj is None:
        return None
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, str):
        if _is_hex_id(obj):
            return id_norm(obj)
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        v = float(obj)
        # Keep floats as-is; parity test does exact equality. NaN handled separately.
        if np.isnan(v):
            return "__nan__"
        if np.isinf(v):
            return "__inf__" if v > 0 else "__-inf__"
        return v
    if isinstance(obj, Fraction):
        return f"{obj.numerator}/{obj.denominator}"
    if isinstance(obj, np.ndarray):
        return [_canonicalize(x, id_norm) for x in obj.tolist()]
    if isinstance(obj, Envelope):
        env_dict = _envelope_to_dict(obj)
        return _canonicalize(env_dict, id_norm)
    if isinstance(obj, (Instrument, Effect, Kit)):
        return _instrument_display(obj)
    if isinstance(obj, dict):
        return {
            str(k): _canonicalize(v, id_norm)
            for k, v in sorted(obj.items(), key=lambda x: str(x[0]))
        }
    if isinstance(obj, (list, tuple)):
        return [_canonicalize(x, id_norm) for x in obj]
    if isinstance(obj, (set, frozenset)):
        return sorted((_canonicalize(x, id_norm) for x in obj),
                      key=lambda v: (type(v).__name__, str(v)))
    if is_dataclass(obj):
        return _canonicalize(asdict(obj), id_norm)
    # fall through: stringify
    return repr(obj)


def _capture_uc_ir(uc, id_norm: _IdNormalizer) -> dict:
    """Level 1: compositional IR state of a UC."""
    events_df = uc.events
    events = events_df.to_dict('records')
    slur_specs = dict(uc._slur_specs)
    control_envelopes = dict(uc._control_envelopes)
    resolved_envs = uc.resolved_control_envelopes()

    return {
        "events": _canonicalize(events, id_norm),
        "slur_specs": _canonicalize(slur_specs, id_norm),
        "control_envelopes": _canonicalize(control_envelopes, id_norm),
        "resolved_control_envelopes": _canonicalize(resolved_envs, id_norm),
    }


def _capture_uc_assembly(uc, id_norm: _IdNormalizer) -> list:
    """Level 2: per-UC lowered SC assembly event stream."""
    from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly
    events = lower_compositional_ir_to_sc_assembly(
        uc, extra_pfields=None, animation=False
    )
    return _canonicalize(events, id_norm)


def _capture_score_payload(score, id_norm: _IdNormalizer) -> dict:
    """Level 2: full Score playback payload."""
    from klotho.utils.playback.supersonic.converters import convert_score_to_sc_events
    payload = convert_score_to_sc_events(score)
    # Drop the raw control buffer (numpy array of audio samples) — its byte
    # content is huge and governed by non-UC numerics; the descriptors list
    # captures the same information structurally.
    if isinstance(payload.get("control_data"), dict):
        payload = dict(payload)
        payload["control_data"] = {
            k: v for k, v in payload["control_data"].items() if k != "buffer"
        }
        # Replace buffer with a shape marker if it was present
        if "buffer" in convert_score_to_sc_events(score).get("control_data", {}):
            buf = convert_score_to_sc_events(score)["control_data"]["buffer"]
            if buf is not None:
                payload["control_data"]["buffer_shape"] = list(np.asarray(buf).shape)
    return _canonicalize(payload, id_norm)


def serialize(scenario_result: Any, seed: int, name: str) -> dict:
    """Serialize a scenario's build() result to a JSON-compatible dict.

    Parameters
    ----------
    scenario_result : dict
        Must contain ``"ucs"`` (dict[str, UC]) and/or ``"score"`` (Score).
    seed : int
        The scenario's SEED value (for embedding in fixture).
    name : str
        Scenario name.

    Returns
    -------
    dict
        Canonical fixture payload.
    """
    from klotho.thetos.composition.score import Score

    id_norm = _IdNormalizer()

    ucs: dict = {}
    sc_assembly_per_uc: dict = {}
    score_obj = scenario_result.get("score")

    if score_obj is not None:
        for item in score_obj.items():
            ucs[item.name] = _capture_uc_ir(item.unit, id_norm)
        sc_score_payload = _capture_score_payload(score_obj, id_norm)
        out = {
            "scenario": name,
            "seed": seed,
            "ucs": ucs,
            "score": {"items": [item.name for item in score_obj.items()],
                      "tracks": list(score_obj.tracks.keys())},
            "sc_assembly_per_uc": None,
            "sc_score_payload": sc_score_payload,
        }
    else:
        user_ucs = scenario_result.get("ucs", {})
        for name_key, uc in user_ucs.items():
            ucs[name_key] = _capture_uc_ir(uc, id_norm)
            sc_assembly_per_uc[name_key] = _capture_uc_assembly(uc, id_norm)
        out = {
            "scenario": name,
            "seed": seed,
            "ucs": ucs,
            "score": None,
            "sc_assembly_per_uc": sc_assembly_per_uc,
            "sc_score_payload": None,
        }

    return out
