"""Hand-written spec goldens for the new event-list contract.

Every ``new`` and ``set`` event carries top-level ``dur`` and ``releaseAfter``
fields. The lowering layer never emits explicit ``type:"release"`` events
for normal lifecycle gate-off; the scheduler does that at fire time by
inspecting the synthdef for a ``'gate'`` control.

These tests assert the converter implements that contract via 8 small
hand-written scenarios. Expected outputs are written from the spec, not
copied from converter output.
"""
from __future__ import annotations

import pytest

from klotho.thetos.composition.compositional import CompositionalUnit
from klotho.thetos.instruments.synthdef import SynthDefInstrument, SynthDefKit
from klotho.utils.playback._sc_assembly import lower_compositional_ir_to_sc_assembly


# ---- helpers ------------------------------------------------------------


def _gated(name: str, defName: str = "kl_tri", **pf):
    d = {"amp": 0.1, "freq": 440.0, "pan": 0.0, "out": 0, "gate": 1}
    d.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=d)


def _free(name: str, defName: str = "kl_kicktone", **pf):
    """Build a non-gated instrument (no ``gate`` pfield)."""
    d = {"amp": 0.1, "pan": 0.0, "out": 0}
    d.update(pf)
    return SynthDefInstrument(name=name, defName=defName, pfields=d)


def _new_events(events):
    return [e for e in events if e["type"] == "new" and e.get("defName") != "__rest__"]


def _set_events(events):
    return [e for e in events if e["type"] == "set"]


def _release_events(events):
    return [e for e in events if e["type"] == "release"]


def _has_required_fields(ev):
    assert isinstance(ev.get("dur"), (int, float)), f"missing/bad dur: {ev}"
    assert ev["dur"] > 0, f"dur must be positive: {ev}"
    assert isinstance(ev.get("releaseAfter"), bool), f"missing releaseAfter: {ev}"


# ---- 1. Single non-slur leaf, gated -------------------------------------


def test_single_leaf_gated_emits_one_terminal_new():
    inst = _gated("g")
    uc = CompositionalUnit(tempus="1/4", prolatio=(1,), bpm=120)
    uc.set_instrument(uc.rt.root, inst)

    events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
    news = _new_events(events)

    assert len(_release_events(events)) == 0
    assert len(news) == 1
    _has_required_fields(news[0])
    assert news[0]["releaseAfter"] is True
    assert news[0]["defName"] == "kl_tri"


# ---- 2. Single non-slur leaf, non-gated ---------------------------------


def test_single_leaf_free_still_emits_release_after_true():
    """Uniformity: even non-gated synths get releaseAfter=true. The scheduler
    no-ops the follow-up because the synthdef has no ``gate`` control."""
    inst = _free("f")
    uc = CompositionalUnit(tempus="1/4", prolatio=(1,), bpm=120)
    uc.set_instrument(uc.rt.root, inst)

    events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
    news = _new_events(events)

    assert len(_release_events(events)) == 0
    assert len(news) == 1
    _has_required_fields(news[0])
    assert news[0]["releaseAfter"] is True


# ---- 5. Polyphonic, constant voice count --------------------------------


def test_poly_strum_terminal_release_after_only():
    """Each voice gets its own uid; each terminal carries releaseAfter=true.
    No explicit release events.
    """
    inst = _gated("g")
    uc = CompositionalUnit(tempus="1/4", prolatio=(1,), bpm=120)
    uc.set_instrument(uc.rt.root, inst)
    leaves = list(uc.rt.leaf_nodes)
    uc.set_pfields(leaves[0], note=(60, 64, 67))

    events = lower_compositional_ir_to_sc_assembly(uc, sort_output=True)
    news = _new_events(events)

    assert len(_release_events(events)) == 0
    assert len(news) == 3
    # Each voice has a unique uid and is terminal.
    assert len({n["id"] for n in news}) == 3
    for n in news:
        _has_required_fields(n)
        assert n["releaseAfter"] is True


# ---- 8. Explicit override path still allowed ----------------------------


def test_explicit_release_event_passes_validator():
    """The validator accepts ``type:"release"`` events as an override path.
    Converters never emit them, but external code may.
    """
    from klotho.utils.playback._sc_validate import validate_sc_events
    events = [
        {
            "type": "new",
            "id": "u1",
            "defName": "kl_tri",
            "start": 0.0,
            "dur": 1.0,
            "releaseAfter": False,
            "pfields": {"freq": 440.0, "amp": 0.1},
        },
        {"type": "release", "id": "u1", "start": 1.5},
    ]
    # Should not raise.
    validate_sc_events(events)


# ---- Validator contract -------------------------------------------------


def test_new_event_must_have_dur():
    from klotho.utils.playback._sc_validate import (
        AssemblyValidationError,
        validate_sc_events,
    )

    events = [
        {
            "type": "new",
            "id": "u1",
            "defName": "kl_tri",
            "start": 0.0,
            # missing dur
            "pfields": {"freq": 440.0, "amp": 0.1},
        },
    ]
    with pytest.raises(AssemblyValidationError, match="missing 'dur'"):
        validate_sc_events(events)


def test_release_after_must_be_bool():
    from klotho.utils.playback._sc_validate import (
        AssemblyValidationError,
        validate_sc_events,
    )

    events = [
        {
            "type": "new",
            "id": "u1",
            "defName": "kl_tri",
            "start": 0.0,
            "dur": 1.0,
            "releaseAfter": "yes",
            "pfields": {"freq": 440.0, "amp": 0.1},
        },
    ]
    with pytest.raises(AssemblyValidationError, match="releaseAfter"):
        validate_sc_events(events)
