#!/usr/bin/env python3
"""Render UTS and BT container examples to PNG only (SVG is temporary)."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))
experiments_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(experiments_dir))

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock

from notation_pipeline.pipeline_uts import notate_uts
from notation_pipeline.pipeline_bt import notate_bt
from notation_pipeline.render.svg_renderer import (
    export_drawing_png,
    render_score,
    render_system,
)


OUTPUT_DIR = Path(__file__).parent / "output" / "containers"


def make_uts_examples():
    """Build and return all UTS test cases as (name, uts) pairs."""
    examples = []

    # ── 1. Simple UTS: two units, same meter, same tempo ────────────
    ut1 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
    ut2 = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
    examples.append(("uts_01_simple_two_units", TemporalUnitSequence([ut1, ut2])))

    # ── 2. UTS with tempo change ────────────────────────────────────
    ut3 = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1, 1)), 1, 1, 1),
                       beat='1/4', bpm=120)
    ut4 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                       beat='1/4', bpm=90)
    examples.append(("uts_02_tempo_change", TemporalUnitSequence([ut3, ut4])))

    # ── 3. UTS with meter change ────────────────────────────────────
    ut5 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
    ut6 = TemporalUnit(tempus='6/8', prolatio=((1, (1, 1, 1)), (1, (1, 1, 1))),
                       beat='3/8', bpm=120)
    examples.append(("uts_03_meter_change", TemporalUnitSequence([ut5, ut6])))

    # ── 4. UTS with both tempo and meter change ─────────────────────
    ut7 = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), 1, 1, (1, (1, 1))),
                       beat='1/4', bpm=120)
    ut8 = TemporalUnit(tempus='3/4', prolatio=((1, (1, 1, 1)), 1, 1),
                       beat='1/4', bpm=80)
    examples.append(("uts_04_tempo_and_meter_change",
                     TemporalUnitSequence([ut7, ut8])))

    # ── 5. Three units in sequence ──────────────────────────────────
    ut_a = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
    ut_b = TemporalUnit(tempus='3/4', prolatio=((1, (1, 1, 1)), 1, 1),
                        beat='1/4', bpm=120)
    ut_c = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1)),
                        (1, (1, 1)), (1, (1, 1))), beat='1/4', bpm=120)
    examples.append(("uts_05_three_units", TemporalUnitSequence([ut_a, ut_b, ut_c])))

    # ── 6. UTS with rests and ties ──────────────────────────────────
    ut_r1 = TemporalUnit(tempus='4/4', prolatio=(1, -1, 1, 1), beat='1/4', bpm=100)
    ut_r2 = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), beat='1/4', bpm=100)
    examples.append(("uts_06_rests_and_ties",
                     TemporalUnitSequence([ut_r1, ut_r2])))

    # ── 7. UTS with span > 1 unit (multi-bar UT inside UTS) ────────
    ut_s1 = TemporalUnit(span=2, tempus='4/4', prolatio=(1, 1, 1, 1, 1, 1, 1, 1),
                         beat='1/4', bpm=120)
    ut_s2 = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120)
    examples.append(("uts_07_span2_unit_in_uts",
                     TemporalUnitSequence([ut_s1, ut_s2])))

    # ── 8. Nested UTS (sub-UTSs end with double barlines) ──────────
    sub_uts1 = TemporalUnitSequence([
        TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120),
        TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), beat='1/4', bpm=120),
    ])
    sub_uts2 = TemporalUnitSequence([
        TemporalUnit(tempus='4/4', prolatio=((1, (1, 1, 1)), 1, 1, 1),
                     beat='1/4', bpm=90),
    ])
    examples.append(("uts_08_nested_sub_uts",
                     TemporalUnitSequence([sub_uts1, sub_uts2])))

    # ── 9. Same tempo throughout (tempo shown only once) ────────────
    ut_same1 = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), 1, 1, 1),
                            beat='1/4', bpm=120)
    ut_same2 = TemporalUnit(tempus='4/4', prolatio=(1, 1, (1, (1, 1, 1)), 1),
                            beat='1/4', bpm=120)
    ut_same3 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                            beat='1/4', bpm=120)
    examples.append(("uts_09_same_tempo_throughout",
                     TemporalUnitSequence([ut_same1, ut_same2, ut_same3])))

    # ── 10. Complex: nested tuplets across units ────────────────────
    ut_cx1 = TemporalUnit(tempus='4/4',
                          prolatio=((1, (1, 1, 1)), (1, (1, 1))),
                          beat='1/4', bpm=108)
    ut_cx2 = TemporalUnit(tempus='5/4',
                          prolatio=((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1),
                          beat='1/4', bpm=108)
    examples.append(("uts_10_complex_tuplets",
                     TemporalUnitSequence([ut_cx1, ut_cx2])))

    return examples


def make_bt_examples():
    """Build and return all BT test cases as (name, bt) pairs."""
    examples = []

    # ── BT 1: Same meter, same tempo (barlines DO align) ────────────
    ut_top = TemporalUnit(tempus='4/4',
                          prolatio=((1, (1, 1, 1)), 1, 1, 1),
                          beat='1/4', bpm=120)
    ut_bot = TemporalUnit(tempus='4/4',
                          prolatio=(1, 1, 1, 1),
                          beat='1/4', bpm=120)
    examples.append(("bt_01_same_meter_tempo", TemporalBlock([ut_top, ut_bot])))

    # ── BT 2: Same meter, different density (barlines align) ────────
    ut_dense = TemporalUnit(tempus='4/4',
        prolatio=((1, (1, 1)), (1, (1, 1)), (1, (1, 1, 1)), (1, (1, 1))),
        beat='1/4', bpm=120)
    ut_sparse = TemporalUnit(tempus='4/4',
        prolatio=(1, 1),
        beat='1/4', bpm=120)
    examples.append(("bt_02_dense_vs_sparse", TemporalBlock([ut_dense, ut_sparse])))

    # ── BT 3: DIFFERENT meters (barlines DON'T align) ───────────────
    ut_4_4 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                          beat='1/4', bpm=120)
    ut_3_4 = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1),
                          beat='1/4', bpm=120)
    examples.append(("bt_03_polymetric", TemporalBlock([ut_4_4, ut_3_4])))

    # ── BT 4: DIFFERENT tempos, same meter (barlines DON'T align) ───
    ut_fast = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                           beat='1/4', bpm=120)  # 2.0s
    ut_slow = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                           beat='1/4', bpm=60)    # 4.0s
    examples.append(("bt_04_polytempo", TemporalBlock([ut_fast, ut_slow])))

    # ── BT 5: Multi-measure UTS rows with different meters ──────────
    # Measure-1 end aligns in wall time: 3*(60/90) == 4*(60/120) == 2s.
    # Measure 2 starts at the same instant on both rows; durations then differ
    # (4/4@120 = 2s vs 5/8@90 with beat 1/8 = 10/3 s).
    ut_a1 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                         beat='1/4', bpm=120)
    ut_a2 = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), 1, 1, 1),
                         beat='1/4', bpm=120)
    uts_top = TemporalUnitSequence([ut_a1, ut_a2])  # 4.0s total

    ut_b1 = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1),
                         beat='1/4', bpm=90)
    ut_b2 = TemporalUnit(tempus='5/8', prolatio=(1, 1, 1, 1, 1),
                         beat='1/8', bpm=90)
    uts_bot = TemporalUnitSequence([ut_b1, ut_b2])

    examples.append(("bt_05_uts_rows_polymeter",
                     TemporalBlock([uts_top, uts_bot])))

    # ── BT 6: Right-aligned (axis=1) ────────────────────────────────
    ut_long = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                           beat='1/4', bpm=60)    # 4.0s
    ut_short = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1),
                            beat='1/4', bpm=120)  # 1.5s
    examples.append(("bt_06_right_aligned",
                     TemporalBlock([ut_long, ut_short], axis=1)))

    # ── BT 7: Three rows, mixed rhythms ─────────────────────────────
    ut_r1 = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1, 1)), 1, 1, 1),
                         beat='1/4', bpm=120)
    ut_r2 = TemporalUnit(tempus='3/4', prolatio=(1, (1, (1, 1)), 1),
                         beat='1/4', bpm=120)
    ut_r3 = TemporalUnit(tempus='5/4', prolatio=(1, 1, 1, 1, 1),
                         beat='1/4', bpm=120)
    examples.append(("bt_07_three_rows",
                     TemporalBlock([ut_r1, ut_r2, ut_r3])))

    # ── BT 8: Center-aligned (axis=0) ───────────────────────────────
    ut_c1 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                         beat='1/4', bpm=100)  # 2.4s
    ut_c2 = TemporalUnit(tempus='3/4', prolatio=(1, 1, 1),
                         beat='1/4', bpm=120)  # 1.5s
    ut_c3 = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1),
                         beat='1/4', bpm=60)   # 4.0s
    examples.append(("bt_08_center_aligned",
                     TemporalBlock([ut_c1, ut_c2, ut_c3], axis=0)))

    return examples


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── UTS examples ──────────────────────────────────────────────────
    uts_examples = make_uts_examples()
    print(f"Rendering {len(uts_examples)} UTS examples to {OUTPUT_DIR}/\n")

    for name, uts in uts_examples:
        try:
            system = notate_uts(uts, spacing_mode='hybrid', barlines=True)
            n_measures = len(system.measures)
            n_events = sum(len(m.events) for m in system.measures)
            dwg = render_system(system, height=200)
            png_path = OUTPUT_DIR / f"{name}.png"
            export_drawing_png(dwg, png_path)
            print(f"  [OK] {name}: {n_measures} measures, {n_events} events")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    # ── BT examples ───────────────────────────────────────────────────
    bt_examples = make_bt_examples()
    print(f"\nRendering {len(bt_examples)} BT examples to {OUTPUT_DIR}/\n")

    for name, bt in bt_examples:
        try:
            score = notate_bt(bt, spacing_mode='hybrid', barlines=True)
            n_rows = len(score.rows)
            n_events = sum(
                len(m.events)
                for sys in score.rows
                for m in sys.measures
            )
            row_height = 80
            total_height = 110 + (n_rows - 1) * row_height + 80
            dwg = render_score(score, height=total_height, row_spacing=row_height)
            png_path = OUTPUT_DIR / f"{name}.png"
            export_drawing_png(dwg, png_path)
            print(f"  [OK] {name}: {n_rows} rows, {n_events} events")
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nDone. PNGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
