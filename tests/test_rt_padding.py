"""Regression: RT ratios/containers leave horizontal padding and an onset label budget."""
import re

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.semeios.visualization._renderers.svg_rt import (
    _svg_rt_ratios, _svg_rt_containers,
)


def _extract_rect_xs(svg):
    """Return every leaf-bar 'x' coordinate (first rect argument after the background)."""
    rects = re.findall(r'<rect[^>]*\bx="([-\d.]+)"', svg)
    return [float(x) for x in rects]


def _extract_viewbox(svg):
    m = re.search(r'viewBox="([^"]+)"', svg)
    assert m, f"no viewBox in svg: {svg[:200]}"
    return [float(v) for v in m.group(1).split()]


class TestRatiosHorizontalPadding:
    def test_leftmost_bar_is_padded(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        svg = _svg_rt_ratios(rt, figsize=(10, 0.5)).svg_str
        xs = _extract_rect_xs(svg)
        width_px = 1000
        assert xs, "expected leaf bars in svg"
        # Skip the background rect (x=0).  The first leaf bar should be > 0.
        leaf_xs = [x for x in xs if x > 0]
        assert leaf_xs, "no leaf bars found past background"
        leftmost = min(leaf_xs)
        assert 0 < leftmost, "leaf bars should start to the right of x=0"
        assert leftmost >= width_px * 0.01, (
            f"leftmost bar at x={leftmost} is not padded (expected >= {width_px * 0.01})"
        )


class TestContainersOnsetLabelBudget:
    def test_viewbox_accommodates_onset_text(self):
        # Small height ⇒ tightest budget; make sure viewBox still clears the
        # onset baseline + descent.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        figsize = (10, 2.0)
        height_px = int(figsize[1] * 100)
        svg = _svg_rt_containers(rt, figsize=figsize).svg_str

        onset_font_size = 10
        onset_text_y_frac = -0.015
        onset_text_budget_frac = max(0.04, (onset_font_size + 4) / height_px)
        expected_y_min = (onset_text_y_frac - onset_text_budget_frac) * height_px

        vb_x, vb_y, vb_w, vb_h = _extract_viewbox(svg)
        # The viewBox y-range is inverted via -y_max; ensure the rendered y_min
        # is captured inside the viewBox extent.
        inner_y_min = -(vb_y + vb_h)
        assert inner_y_min <= expected_y_min + 1.0, (
            f"viewBox y-min ({inner_y_min}) does not enclose onset budget ({expected_y_min})"
        )

    def test_small_figsize_budget(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        figsize = (10, 1.0)
        height_px = int(figsize[1] * 100)
        svg = _svg_rt_containers(rt, figsize=figsize).svg_str
        onset_font_size = 10
        onset_text_y_frac = -0.015
        onset_text_budget_frac = max(0.04, (onset_font_size + 4) / height_px)
        expected_y_min = (onset_text_y_frac - onset_text_budget_frac) * height_px
        vb_x, vb_y, vb_w, vb_h = _extract_viewbox(svg)
        inner_y_min = -(vb_y + vb_h)
        assert inner_y_min <= expected_y_min + 1.0


class TestContainersHorizontalPadding:
    def test_inner_content_not_flush_to_edges(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        figsize = (10, 2.0)
        width_px = int(figsize[0] * 100)
        svg = _svg_rt_containers(rt, figsize=figsize).svg_str

        # Pull out every <rect> x attribute that isn't the full-width
        # background.
        rect_xs = [
            float(x) for x in re.findall(
                r'<rect[^>]*\bx="([-\d.]+)"[^>]*\bwidth="([-\d.]+)"', svg
            )
            for x in (x[0],)
        ]
        # Filter to inner content rects.  Exclude the background rect at x=0
        # spanning the full width (the only rect with width == width_px).
        rect_pairs = re.findall(
            r'<rect[^>]*\bx="([-\d.]+)"[^>]*\bwidth="([-\d.]+)"', svg
        )
        inner_starts = [
            float(x) for (x, w) in rect_pairs
            if float(w) < width_px  # not the background
        ]
        assert inner_starts, "expected at least one inner rect"
        leftmost = min(inner_starts)
        assert leftmost >= width_px * 0.005, (
            f"leftmost inner rect at x={leftmost} has no visible padding"
        )
