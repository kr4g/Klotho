#!/usr/bin/env python3
"""Render examples that exercise the barline tie-split mechanism.

These are all non-tuplet leaves that cross a measure boundary and get
decomposed into tied engravable components.  Output → output/barline_splits/.
"""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(experiments_dir))

from collections import Counter
from fractions import Fraction

from klotho.chronos import RhythmTree as RT

from notation_pipeline.pipeline import notate
from notation_pipeline.render.svg_renderer import export_drawing_png, render_measure

OUTPUT_DIR = Path(__file__).parent / "output" / "barline_splits"


EXAMPLES = [
    # ─── Simple two-leaf splits ──────────────────────────────────────
    # (5, 3) in 4/4 span=2: first leaf = 5/4, crosses bar → split
    ("S01_5_3",
     "4/4", (5, 3), 2),

    # (3, 5): second leaf = 5/4, crosses bar → split
    ("S02_3_5",
     "4/4", (3, 5), 2),

    # (7, 1): first leaf = 7/4 → spans almost two bars
    ("S03_7_1",
     "4/4", (7, 1), 2),

    # (1, 7): second leaf = 7/4
    ("S04_1_7",
     "4/4", (1, 7), 2),

    # (6, 2) and (2, 6): one leaf = 3/2
    ("S05_6_2",
     "4/4", (6, 2), 2),

    ("S06_2_6",
     "4/4", (2, 6), 2),

    # ─── Three-leaf: one crosses ─────────────────────────────────────
    # (3, 3, 2): middle leaf onset=3/4 dur=3/4 → crosses bar at 1
    ("T01_3_3_2",
     "4/4", (3, 3, 2), 2),

    # (2, 3, 3): middle leaf onset=1/2 dur=3/4 → crosses bar at 1
    ("T02_2_3_3",
     "4/4", (2, 3, 3), 2),

    # (1, 6, 1): big middle
    ("T03_1_6_1",
     "4/4", (1, 6, 1), 2),

    # (2, 4, 2): symmetric, middle crosses
    ("T04_2_4_2",
     "4/4", (2, 4, 2), 2),

    # ─── Four-leaf: one big leaf crosses ─────────────────────────────
    # (1, 5, 1, 1): second leaf = 5/4
    ("F01_1_5_1_1",
     "4/4", (1, 5, 1, 1), 2),

    # (1, 1, 5, 1): third leaf = 5/4
    ("F02_1_1_5_1",
     "4/4", (1, 1, 5, 1), 2),

    # (5, 1, 1, 1): first leaf = 5/4
    ("F03_5_1_1_1",
     "4/4", (5, 1, 1, 1), 2),

    # (1, 1, 1, 5): last leaf = 5/4
    ("F04_1_1_1_5",
     "4/4", (1, 1, 1, 5), 2),

    # ─── Nested: inner non-tuplet leaves cross barline ───────────────
    # ((5, (1, 1)), (3, (1, 1))): 4 leaves, inner halves of the 5-unit span cross
    ("N01_nest_5_3",
     "4/4", ((5, (1, 1)), (3, (1, 1))), 2),

    # ((3, (1, 1)), (5, (1, 1))): mirror
    ("N02_nest_3_5",
     "4/4", ((3, (1, 1)), (5, (1, 1))), 2),

    # (1, 1, (3, (1, 1)), 1, 1, 1): one inner pair crosses
    ("N03_deep_inner_cross",
     "4/4", (1, 1, (3, (1, 1)), 1, 1, 1), 2),

    # ((3, (1, 1, 1)), (5, (1, 1))): triplet inside first, pair inside second
    ("N04_nest_3trip_5pair",
     "4/4", ((3, (1, 1, 1)), (5, (1, 1))), 2),

    # ─── Different meters ────────────────────────────────────────────
    # 3/4 span=2: (3, 1) → first leaf = 3/4 of 3/2 = 9/8, crosses bar at 3/4
    ("M01_3_4_unequal",
     "3/4", (3, 1), 2),

    # 6/8 span=2: (5, 3) → first leaf = 5/8 of 3/2 = 15/16... 
    ("M02_6_8_unequal",
     "6/8", (5, 3), 2),

    # 5/4 span=2: (7, 3) → first leaf = 7/4
    ("M03_5_4_unequal",
     "5/4", (7, 3), 2),

    # 3/4 span=2: (3, 5) → both cross potentially
    ("M04_3_4_3_5",
     "3/4", (3, 5), 2),

    # 2/4 span=2: (3, 1) → first leaf = 3/4
    ("M05_2_4_3_1",
     "2/4", (3, 1), 2),

    # ─── span=3 ──────────────────────────────────────────────────────
    # (5, 3, 4) in 4/4 span=3: first leaf = 5/4, second = 3/4 etc.
    ("P01_span3_5_3_4",
     "4/4", (5, 3, 4), 3),

    # (4, 5, 3): middle leaf crosses
    ("P02_span3_4_5_3",
     "4/4", (4, 5, 3), 3),

    # (1, 1, 1, 5, 1, 1, 1, 1): one big leaf in the middle
    ("P03_span3_big_middle",
     "4/4", (1, 1, 1, 5, 1, 1, 1, 1, 1, 1, 1, 1), 3),

    # ─── Mixed: splits + ties + rests ────────────────────────────────
    # (5, 3) but with a rest: (-5, 3) → rest crosses barline
    ("X01_rest_crosses",
     "4/4", (-5, 3), 2),

    # (3, 5) with tie on second: (3, 5.0) → tied AND crosses
    ("X02_tied_and_crosses",
     "4/4", (3, 5.0), 2),

    # (1, -3, 3, 1): rest in middle crosses
    ("X03_rest_mid_cross",
     "4/4", (1, -3, 3, 1), 2),

    # (2, 3, -3): note crosses, then rest crosses
    ("X04_note_then_rest_cross",
     "4/4", (2, 3, -3), 2),
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {len(EXAMPLES)} barline-split examples to {OUTPUT_DIR}/\n")

    for example in EXAMPLES:
        name, meas_str, subdivisions = example[0], example[1], example[2]
        span = example[3] if len(example) > 3 else 1
        try:
            rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
            measure = notate(rt, spacing_mode='hybrid')

            n_leaves = len(rt.leaf_nodes)
            n_events = len(measure.events)

            splits = []
            for i, e in enumerate(measure.events):
                if e.is_tied_forward and i + 1 < len(measure.events):
                    splits.append(e.node_id)

            width = 900 if span <= 2 else 1200
            dwg = render_measure(measure, width=width, height=200)
            png_path = OUTPUT_DIR / f"{name}.png"
            export_drawing_png(dwg, png_path)

            split_nodes = len(set(splits))
            print(f"  [OK] {name}: {n_leaves} leaves → {n_events} events "
                  f"({split_nodes} leaf/leaves split at barline)")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone. PNGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
