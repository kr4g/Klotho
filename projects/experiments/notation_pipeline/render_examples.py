#!/usr/bin/env python3
"""Render a suite of test RhythmTrees to PNG only in output/ (SVG is temporary)."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure imports work
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(experiments_dir))

from klotho.chronos import RhythmTree as RT, Meas

from notation_pipeline.pipeline import notate
from notation_pipeline.render.svg_renderer import export_drawing_png, render_measure


OUTPUT_DIR = Path(__file__).parent / "output"


# Test cases: (name, meas, subdivisions, [optional kwargs])
EXAMPLES = [
    # --- Basic ---
    ("01_four_quarters",
     "4/4", (1, 1, 1, 1)),

    ("02_three_quarters_3_4",
     "3/4", (1, 1, 1)),

    ("03_unequal_proportions",
     "4/4", (3, 1, 2, 2)),

    # --- Rests ---
    ("04_rest_beat1",
     "4/4", (-1, 1, 1, 1)),

    ("05_two_rests_middle",
     "4/4", (1, -1, -1, 1)),

    # --- Ties ---
    ("06_tie_beats_1_2",
     "4/4", (1, 1.0, 1, 1)),

    # --- Nested (one level) ---
    ("07_all_eighths_nested",
     "4/4", ((1, (1, 1)), (1, (1, 1)), (1, (1, 1)), (1, (1, 1)))),

    ("08_triplet_plus_binary",
     "4/4", ((1, (1, 1, 1)), (1, (1, 1)))),

    ("09_compound_6_8",
     "6/8", ((1, (1, 1, 1)), (1, (1, 1, 1)))),

    # --- Tuplets (flat) ---
    ("10_half_note_triplet",
     "4/4", (1, 1, 1)),

    ("11_quintuplet",
     "4/4", (1, 1, 1, 1, 1)),

    ("12_septuplet",
     "4/4", (1, 1, 1, 1, 1, 1, 1)),

    # --- Nested tuplets ---
    ("13_triplet_beat1_binary_beat4",
     "4/4", ((1, (1, 1, 1)), 1, 1, (1, (1, 1)))),

    ("14_quintuplet_plus_triplet",
     "4/4", ((1, (1, 1, 1, 1, 1)), (1, (1, 1, 1)))),

    # --- Deep nesting ---
    ("15_two_levels_deep",
     "4/4", ((4, (1, 1, (1, (1, 1)))), 2, 1, 1)),

    ("16_nested_with_rests",
     "4/4", ((1, (1, 1, 1)), (1, (-1, 1, 1)), (1, (1, -1, 1)), (1, (1, 1, -1)))),

    # --- Nested tuplets (tuplet inside tuplet) ---
    ("17_triplet_of_triplets",
     "4/4", ((1, ((1, (1, 1, 1)), (1, (1, 1, 1)), (1, (1, 1, 1)))),
             (1, (1, 1)))),

    ("18_quintuplet_with_inner_triplet",
     "4/4", ((1, ((1, (1, 1, 1)), 1, 1, 1, 1)),
             (1, (1, 1)))),

    ("19_triplet_of_pairs",
     "4/4", ((1, ((1, (1, 1)), (1, (1, 1)), (1, (1, 1)))),
             (1, (1, 1)))),

    ("20_nested_5_in_3",
     "4/4", ((1, ((1, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1)))),
             (1, (1, 1)))),

    # --- Complex ---
    ("21_complex_mixed",
     "3/4", ((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)))),

    ("22_irregular_5_4",
     "5/4", ((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1)),

    ("23_accelerando_pattern",
     "4/4", ((1, (1, 2, 3, 4)), (1, (4, 3, 2, 1)))),

    ("24_deep_triplet_chain",
     "4/4", ((1, (1, 1, (1, (1, 1, (1, (1, 1, 1)))))), (1, (1, 1)))),

    # --- Span > 1 (multi-bar) ---
    ("25_span2_basic",
     "4/4", (1, 1, 1, 1, 1, 1, 1, 1), 2),

    ("26_span2_tuplet",
     "4/4", ((1, (1, 1, 1)), 1, 1, 1, 1, 1, 1, (1, (1, 1))), 2),

    ("27_span3_mixed",
     "3/4", (1, 1, 1, -1, 1, 1, 1, 1, 1), 3),

    # --- Tempo markings (UT context) ---
    ("28_tempo_quarter_120",
     "4/4", ((1, (1, 1, 1)), 1, 1, (1, (1, 1))), 1, "1/4", 120),

    ("29_tempo_dotted_quarter_90",
     "6/8", ((1, (1, 1, 1)), (1, (1, 1, 1))), 1, "3/8", 90),

    # --- Cross-barline stress tests (span > 1) ---
    ("30_span2_cross_barline_tuplet",
     "4/4", ((1, (1, 1)), 1, 1, (1, (1, 1, 1)), 1, 1, 1, 1), 2),

    ("31_span2_cross_barline_tie",
     "4/4", (1, 1, 1, 1.0, 1, 1, 1), 2),

    ("32_span2_beam_near_barline",
     "4/4", (1, 1, 1, (1, (1, 1)), (1, (1, 1)), 1, 1, 1), 2),
]


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"Rendering {len(EXAMPLES)} examples to {OUTPUT_DIR}/\n")

    for example in EXAMPLES:
        name, meas_str, subdivisions = example[0], example[1], example[2]
        span = example[3] if len(example) > 3 else 1
        tempo_beat = example[4] if len(example) > 4 else None
        tempo_bpm = example[5] if len(example) > 5 else None
        try:
            rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
            measure = notate(rt, spacing_mode='hybrid',
                             tempo_beat=tempo_beat, tempo_bpm=tempo_bpm)
            width = 900 if span <= 2 else 1200
            dwg = render_measure(measure, width=width, height=200)
            png_path = OUTPUT_DIR / f"{name}.png"
            export_drawing_png(dwg, png_path)

            n_events = len(measure.events)
            n_tuplets = len(measure.tuplets)
            n_beams = len(measure.beam_groups)
            print(f"  [OK] {name}: {n_events} events, {n_tuplets} tuplets, {n_beams} beam groups")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone. PNGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
