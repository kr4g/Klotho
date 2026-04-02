#!/usr/bin/env python3
"""Generate JSON baselines for all notation pipeline render examples.

Run this once when the pipeline output is visually verified (known-good).
Re-run after intentional changes to update baselines.

Usage:
    /Users/ryanmillett/klotho-venv/bin/python tests/generate_baselines.py
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(experiments_dir))

from klotho.chronos import RhythmTree as RT

from notation_pipeline.pipeline import notate
from notation_pipeline.pipeline_uts import notate_uts
from notation_pipeline.pipeline_bt import notate_bt

from notation_pipeline.render_examples import EXAMPLES as RT_EXAMPLES
from notation_pipeline.render_barline_splits import EXAMPLES as BARLINE_EXAMPLES
from notation_pipeline.render_span_edge_cases import EXAMPLES as SPAN_EXAMPLES
from notation_pipeline.render_containers import make_uts_examples, make_bt_examples

from baseline_utils import save_baseline, serialize_measure, serialize_system, serialize_score


def generate_rt_baselines(examples, category: str) -> int:
    count = 0
    for example in examples:
        name, meas_str, subdivisions = example[0], example[1], example[2]
        span = example[3] if len(example) > 3 else 1
        tempo_beat = example[4] if len(example) > 4 else None
        tempo_bpm = example[5] if len(example) > 5 else None

        rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
        measure = notate(rt, spacing_mode='hybrid',
                         tempo_beat=tempo_beat, tempo_bpm=tempo_bpm)
        data = serialize_measure(measure)
        data["_meta"] = {
            "category": category,
            "name": name,
            "meas": meas_str,
            "span": span,
        }
        save_baseline(data, category, name)
        count += 1
    return count


def generate_uts_baselines() -> int:
    count = 0
    for name, uts in make_uts_examples():
        system = notate_uts(uts, spacing_mode='hybrid', barlines=True)
        data = serialize_system(system)
        data["_meta"] = {"category": "uts", "name": name}
        save_baseline(data, "uts", name)
        count += 1
    return count


def generate_bt_baselines() -> int:
    count = 0
    for name, bt in make_bt_examples():
        score = notate_bt(bt, spacing_mode='hybrid', barlines=True)
        data = serialize_score(score)
        data["_meta"] = {"category": "bt", "name": name}
        save_baseline(data, "bt", name)
        count += 1
    return count


def main():
    print("Generating notation pipeline baselines...\n")

    n = generate_rt_baselines(RT_EXAMPLES, "rt")
    print(f"  RT examples:          {n} baselines")

    n = generate_rt_baselines(BARLINE_EXAMPLES, "barline_splits")
    print(f"  Barline splits:       {n} baselines")

    n = generate_rt_baselines(SPAN_EXAMPLES, "span_edge_cases")
    print(f"  Span edge cases:      {n} baselines")

    n = generate_uts_baselines()
    print(f"  UTS examples:         {n} baselines")

    n = generate_bt_baselines()
    print(f"  BT examples:          {n} baselines")

    from baseline_utils import BASELINES_DIR
    total = sum(1 for _ in BASELINES_DIR.rglob("*.json"))
    print(f"\nTotal: {total} baseline files in {BASELINES_DIR}/")


if __name__ == "__main__":
    main()
