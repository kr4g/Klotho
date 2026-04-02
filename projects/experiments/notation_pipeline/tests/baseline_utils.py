"""Serialization and comparison utilities for notation pipeline baselines.

Baselines capture the full NotatedMeasure / NotatedSystem / NotatedScore
output from the pipeline so that structural invariants and x-positions can
be regression-tested without visual inspection.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from notation_pipeline.models import (
    BeamGroup,
    EngravingLeaf,
    NotatedMeasure,
    NotatedScore,
    NotatedSystem,
    TupletBracket,
)


BASELINES_DIR = Path(__file__).parent / "baselines"

X_TOLERANCE = 1.0


def serialize_event(ev: EngravingLeaf) -> dict[str, Any]:
    return {
        "node_id": ev.node_id,
        "duration": str(ev.duration),
        "onset": str(ev.onset),
        "note_type": ev.note_type.name,
        "dots": ev.dots,
        "is_rest": ev.is_rest,
        "is_continuation_tie": ev.is_continuation_tie,
        "is_tied_forward": ev.is_tied_forward,
        "tuplet_scale": str(ev.tuplet_scale) if ev.tuplet_scale is not None else None,
        "x": round(ev.x, 4),
    }


def serialize_tuplet(t: TupletBracket) -> dict[str, Any]:
    return {
        "actual": t.actual,
        "normal": t.normal,
        "inner_note_type": t.inner_note_type.name if t.inner_note_type else None,
        "event_indices": t.event_indices,
        "group_node_id": t.group_node_id,
    }


def serialize_beam_group(bg: BeamGroup) -> dict[str, Any]:
    return {
        "event_indices": bg.event_indices,
        "max_beam_level": bg.max_beam_level,
        "group_node_id": bg.group_node_id,
    }


def serialize_measure(m: NotatedMeasure) -> dict[str, Any]:
    ts = None
    if m.time_signature is not None:
        ts = f"{m.time_signature.numerator}/{m.time_signature.denominator}"
    return {
        "time_signature": ts,
        "event_count": len(m.events),
        "events": [serialize_event(ev) for ev in m.events],
        "tuplets": [serialize_tuplet(t) for t in m.tuplets],
        "beam_groups": [serialize_beam_group(bg) for bg in m.beam_groups],
        "barline_x_positions": [round(x, 4) for x in m.barline_x_positions],
        "show_barlines": m.show_barlines,
        "tempo_beat": str(m.tempo_beat) if m.tempo_beat is not None else None,
        "tempo_bpm": m.tempo_bpm,
        "end_barline_type": m.end_barline_type,
    }


def serialize_system(system: NotatedSystem) -> dict[str, Any]:
    return {
        "measure_count": len(system.measures),
        "measures": [serialize_measure(m) for m in system.measures],
    }


def serialize_score(score: NotatedScore) -> dict[str, Any]:
    return {
        "row_count": len(score.rows),
        "rows": [serialize_system(s) for s in score.rows],
    }


def save_baseline(data: dict, category: str, name: str) -> Path:
    out_dir = BASELINES_DIR / category
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def load_baseline(category: str, name: str) -> dict:
    path = BASELINES_DIR / category / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def assert_structural_match(actual_measure: dict, baseline_measure: dict, label: str = ""):
    """Level 1: exact structural invariants (no floats)."""
    prefix = f"[{label}] " if label else ""

    assert actual_measure["event_count"] == baseline_measure["event_count"], (
        f"{prefix}event count: {actual_measure['event_count']} != {baseline_measure['event_count']}"
    )

    for i, (a, b) in enumerate(zip(actual_measure["events"], baseline_measure["events"])):
        assert a["note_type"] == b["note_type"], f"{prefix}event {i} note_type: {a['note_type']} != {b['note_type']}"
        assert a["dots"] == b["dots"], f"{prefix}event {i} dots: {a['dots']} != {b['dots']}"
        assert a["is_rest"] == b["is_rest"], f"{prefix}event {i} is_rest: {a['is_rest']} != {b['is_rest']}"
        assert a["is_tied_forward"] == b["is_tied_forward"], f"{prefix}event {i} is_tied_forward mismatch"
        assert a["is_continuation_tie"] == b["is_continuation_tie"], f"{prefix}event {i} is_continuation_tie mismatch"
        assert a["duration"] == b["duration"], f"{prefix}event {i} duration: {a['duration']} != {b['duration']}"
        assert a["onset"] == b["onset"], f"{prefix}event {i} onset: {a['onset']} != {b['onset']}"
        assert a["tuplet_scale"] == b["tuplet_scale"], f"{prefix}event {i} tuplet_scale mismatch"

    assert len(actual_measure["tuplets"]) == len(baseline_measure["tuplets"]), (
        f"{prefix}tuplet count: {len(actual_measure['tuplets'])} != {len(baseline_measure['tuplets'])}"
    )
    for i, (a, b) in enumerate(zip(actual_measure["tuplets"], baseline_measure["tuplets"])):
        assert a["actual"] == b["actual"], f"{prefix}tuplet {i} actual: {a['actual']} != {b['actual']}"
        assert a["normal"] == b["normal"], f"{prefix}tuplet {i} normal: {a['normal']} != {b['normal']}"
        assert a["event_indices"] == b["event_indices"], f"{prefix}tuplet {i} event_indices mismatch"

    assert len(actual_measure["beam_groups"]) == len(baseline_measure["beam_groups"]), (
        f"{prefix}beam_group count mismatch"
    )
    for i, (a, b) in enumerate(zip(actual_measure["beam_groups"], baseline_measure["beam_groups"])):
        assert a["event_indices"] == b["event_indices"], f"{prefix}beam_group {i} event_indices mismatch"
        assert a["max_beam_level"] == b["max_beam_level"], f"{prefix}beam_group {i} max_beam_level mismatch"

    assert actual_measure["time_signature"] == baseline_measure["time_signature"], (
        f"{prefix}time_signature: {actual_measure['time_signature']} != {baseline_measure['time_signature']}"
    )

    assert len(actual_measure["barline_x_positions"]) == len(baseline_measure["barline_x_positions"]), (
        f"{prefix}barline count: {len(actual_measure['barline_x_positions'])} != {len(baseline_measure['barline_x_positions'])}"
    )


def assert_ordering_invariants(measure_data: dict, label: str = ""):
    """Level 2: relational invariants on x-positions."""
    prefix = f"[{label}] " if label else ""
    events = measure_data["events"]
    barlines = measure_data["barline_x_positions"]

    if len(events) > 1:
        xs = [e["x"] for e in events]
        for i in range(len(xs) - 1):
            assert xs[i] < xs[i + 1], (
                f"{prefix}events not in strict x order: event {i} x={xs[i]} >= event {i+1} x={xs[i+1]}"
            )

    if len(barlines) > 1:
        for i in range(len(barlines) - 1):
            assert barlines[i] <= barlines[i + 1], (
                f"{prefix}barlines not monotonic: barline {i}={barlines[i]} > barline {i+1}={barlines[i+1]}"
            )

    if events and barlines:
        assert events[0]["x"] > barlines[0], (
            f"{prefix}first event x={events[0]['x']} not after opening barline x={barlines[0]}"
        )


def assert_x_positions_match(actual_measure: dict, baseline_measure: dict, tol: float = X_TOLERANCE, label: str = ""):
    """Level 3: x-position snapshot comparison with tolerance."""
    prefix = f"[{label}] " if label else ""

    for i, (a, b) in enumerate(zip(actual_measure["events"], baseline_measure["events"])):
        assert abs(a["x"] - b["x"]) <= tol, (
            f"{prefix}event {i} x drift: {a['x']} vs baseline {b['x']} (tol={tol})"
        )

    for i, (a, b) in enumerate(zip(actual_measure["barline_x_positions"], baseline_measure["barline_x_positions"])):
        assert abs(a - b) <= tol, (
            f"{prefix}barline {i} x drift: {a} vs baseline {b} (tol={tol})"
        )
