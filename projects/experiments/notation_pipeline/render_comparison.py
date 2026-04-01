#!/usr/bin/env python3
"""Render each example in all 3 spacing modes side-by-side for comparison."""

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
from notation_pipeline.render_examples import EXAMPLES

OUTPUT_DIR = Path(__file__).parent / "output" / "comparison"
MODES = ['proportional', 'traditional', 'hybrid']

# Examples to also render with barlines=False for comparison.
# All span > 1 examples + a selection of span=1 examples.
BARLINE_COMPARISON_NAMES = {
    # span=1 samples
    '01_four_quarters', '08_triplet_plus_binary',
    '17_triplet_of_triplets', '21_complex_mixed',
    # span > 1 (all)
    '25_span2_basic', '26_span2_tuplet', '27_span3_mixed',
    '30_span2_cross_barline_tuplet', '31_span2_cross_barline_tie',
    '32_span2_beam_near_barline',
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for example in EXAMPLES:
        name, meas_str, subdivisions = example[0], example[1], example[2]
        span = example[3] if len(example) > 3 else 1
        tempo_beat = example[4] if len(example) > 4 else None
        tempo_bpm = example[5] if len(example) > 5 else None

        for mode in MODES:
            try:
                rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
                measure = notate(rt, spacing_mode=mode,
                                 tempo_beat=tempo_beat, tempo_bpm=tempo_bpm)
                width = 900 if span <= 2 else 1200
                dwg = render_measure(measure, width=width, height=200)
                png_path = OUTPUT_DIR / f"{name}_{mode}.png"
                export_drawing_png(dwg, png_path)
            except Exception as e:
                print(f"  [FAIL] {name} ({mode}): {e}")

        # barlines=True/False comparison for selected examples
        if name in BARLINE_COMPARISON_NAMES:
            for bl in (True, False):
                bl_tag = "barlines" if bl else "nobarlines"
                try:
                    rt = RT(span=span, meas=meas_str, subdivisions=subdivisions)
                    measure = notate(rt, spacing_mode='hybrid', barlines=bl,
                                     tempo_beat=tempo_beat, tempo_bpm=tempo_bpm)
                    width = 900 if span <= 2 else 1200
                    dwg = render_measure(measure, width=width, height=200)
                    png_path = OUTPUT_DIR / f"{name}_{bl_tag}.png"
                    export_drawing_png(dwg, png_path)
                except Exception as e:
                    print(f"  [FAIL] {name} ({bl_tag}): {e}")

    print(f"Done. Comparison PNGs saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
