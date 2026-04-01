#!/usr/bin/env python3
"""Render span > 1 edge-case examples for visual inspection.

Output goes to output/span_edge_cases/.  No code changes—pure diagnosis.
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(experiments_dir))

from klotho.chronos import RhythmTree as RT

from notation_pipeline.pipeline import notate
from notation_pipeline.render.svg_renderer import export_drawing_png, render_measure

OUTPUT_DIR = Path(__file__).parent / "output" / "span_edge_cases"

EXAMPLES = [
    # ──────────────────────────────────────────────────────────────────
    # A. Simple ties across barline (no tuplet context)
    # ──────────────────────────────────────────────────────────────────
    ("A01_8q_tie_beat4to5",
     "4/4", (1, 1, 1, 1, 1.0, 1, 1, 1), 2),

    ("A02_8q_tie_beat3to4",
     "4/4", (1, 1, 1.0, 1, 1, 1, 1, 1), 2),

    ("A03_8q_two_ties",
     "4/4", (1, 1, 1.0, 1, 1.0, 1, 1, 1), 2),

    ("A04_tie_first_to_second",
     "4/4", (1.0, 1, 1, 1, 1, 1, 1, 1), 2),

    ("A05_tie_last_pair",
     "4/4", (1, 1, 1, 1, 1, 1, 1.0, 1), 2),

    ("A06_tie_across_barline_3_4",
     "3/4", (1, 1, 1, 1.0, 1, 1), 2),

    ("A07_tie_across_barline_6_8",
     "6/8", ((1, (1, 1, 1)), (1, (1.0, 1, 1)), (1, (1, 1, 1)), (1, (1, 1, 1))), 2),

    # ──────────────────────────────────────────────────────────────────
    # B. Tuplets that DON'T cross a barline (tie inside one measure)
    # ──────────────────────────────────────────────────────────────────
    ("B01_tuplet7_no_tie_span2",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), 2),

    ("B02_triplet_per_half_span2",
     "4/4", ((1, (1, 1, 1)), (1, (1, 1, 1)), (1, (1, 1, 1)), (1, (1, 1, 1))), 2),

    ("B03_quintuplet_first_bar_quarters_second",
     "4/4", ((1, (1, 1, 1, 1, 1)), 1, 1, 1, 1), 2),

    # ──────────────────────────────────────────────────────────────────
    # C. Tuplets that CROSS a barline (the original problem area)
    # ──────────────────────────────────────────────────────────────────
    ("C01_7over2bars_no_tie",
     "4/4", (1, 1, 1, 1, 1, 1, 1), 2),

    ("C02_7over2bars_tie_at_barline",
     "4/4", (1, 1, 1, 1.0, 1, 1, 1), 2),

    ("C03_5over2bars_no_tie",
     "4/4", (1, 1, 1, 1, 1), 2),

    ("C04_5over2bars_tie_mid",
     "4/4", (1, 1, 1.0, 1, 1), 2),

    ("C05_3over2bars",
     "4/4", (1, 1, 1), 2),

    ("C06_3over2bars_tie",
     "4/4", (1, 1.0, 1), 2),

    ("C07_9over2bars_no_tie",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1, 1), 2),

    ("C08_9over2bars_tie_near_bar",
     "4/4", (1, 1, 1, 1, 1.0, 1, 1, 1, 1), 2),

    ("C09_11over2bars",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), 2),

    ("C10_7over2bars_3_4",
     "3/4", (1, 1, 1, 1, 1, 1, 1), 2),

    ("C11_7over2bars_3_4_tie",
     "3/4", (1, 1, 1, 1.0, 1, 1, 1), 2),

    # ──────────────────────────────────────────────────────────────────
    # D. Nested tuplets crossing barlines
    # ──────────────────────────────────────────────────────────────────
    ("D01_triplet_of_pairs_span2",
     "4/4", ((1, (1, 1)), (1, (1, 1)), (1, (1, 1))), 2),

    ("D02_triplet_of_triplets_span2",
     "4/4", ((1, (1, 1, 1)), (1, (1, 1, 1)), (1, (1, 1, 1))), 2),

    ("D03_nested_5in3_span2",
     "4/4", ((1, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1))), 2),

    # ──────────────────────────────────────────────────────────────────
    # E. Rests crossing barlines
    # ──────────────────────────────────────────────────────────────────
    ("E01_rest_at_barline",
     "4/4", (1, 1, 1, -1, 1, 1, 1, 1), 2),

    ("E02_rest_after_barline",
     "4/4", (1, 1, 1, 1, -1, 1, 1, 1), 2),

    ("E03_tuplet7_rest_near_bar",
     "4/4", (1, 1, 1, -1, 1, 1, 1), 2),

    # ──────────────────────────────────────────────────────────────────
    # F. Mixed: tuplets + ties + rests
    # ──────────────────────────────────────────────────────────────────
    ("F01_7_tie_and_rest",
     "4/4", (1, 1, -1, 1.0, 1, 1, 1), 2),

    ("F02_nested_with_tie_span2",
     "4/4", ((1, (1, 1, 1)), 1, 1, 1.0, 1, 1, (1, (1, 1))), 2),

    ("F03_unequal_props_tie",
     "4/4", (3, 1, 2, 2, 1.0, 1, 1, 1), 2),

    ("F04_unequal_tuplet_tie",
     "4/4", (2, 1, 1, 1.0, 2, 1), 2),

    # ──────────────────────────────────────────────────────────────────
    # G. span=3 cases
    # ──────────────────────────────────────────────────────────────────
    ("G01_12q_span3_no_tie",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), 3),

    ("G02_12q_span3_ties_at_bars",
     "4/4", (1, 1, 1, 1, 1.0, 1, 1, 1, 1.0, 1, 1, 1), 3),

    ("G03_7_span3",
     "4/4", (1, 1, 1, 1, 1, 1, 1), 3),

    ("G04_7_span3_tie",
     "4/4", (1, 1, 1, 1.0, 1, 1, 1), 3),

    ("G05_9_span3_3_4",
     "3/4", (1, 1, 1, 1, 1, 1, 1, 1, 1), 3),

    ("G06_9_span3_3_4_ties",
     "3/4", (1, 1, 1, 1.0, 1, 1, 1.0, 1, 1), 3),

    # ──────────────────────────────────────────────────────────────────
    # H. Exactly filling measures (no tuplet) with ties
    # ──────────────────────────────────────────────────────────────────
    ("H01_halves_span2_tie",
     "4/4", (1, 1, 1.0, 1), 2),

    ("H02_wholes_span2_tie",
     "4/4", (1, 1.0), 2),

    ("H03_dotted_halves_6_8_span2",
     "6/8", (1, 1, 1.0, 1), 2),

    # ──────────────────────────────────────────────────────────────────
    # I. Large tuplets spanning multiple bars
    # ──────────────────────────────────────────────────────────────────
    ("I01_13over3bars",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1), 3),

    ("I02_13over3bars_tie",
     "4/4", (1, 1, 1, 1, 1.0, 1, 1, 1, 1, 1.0, 1, 1, 1), 3),

    ("I03_5over3bars_4_4",
     "4/4", (1, 1, 1, 1, 1), 3),
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {len(EXAMPLES)} span edge-case examples to {OUTPUT_DIR}/\n")

    for example in EXAMPLES:
        name, meas_str, subdivisions = example[0], example[1], example[2]
        span = example[3] if len(example) > 3 else 1
        try:
            rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
            measure = notate(rt, spacing_mode='hybrid')

            n_leaves = len(rt.leaf_nodes)
            n_events = len(measure.events)
            n_tuplets = len(measure.tuplets)

            width = 900 if span <= 2 else 1200
            dwg = render_measure(measure, width=width, height=200)
            png_path = OUTPUT_DIR / f"{name}.png"
            export_drawing_png(dwg, png_path)

            flag = ""
            if n_events != n_leaves:
                flag = f"  *** SPLIT: {n_leaves} leaves -> {n_events} events"
            print(f"  [OK] {name}: {n_leaves} leaves, {n_events} events, "
                  f"{n_tuplets} tuplets, span={span}{flag}")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone. PNGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
