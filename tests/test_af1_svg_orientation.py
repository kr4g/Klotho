"""AUD-2: ``plot(Score)`` and ``plot(UTS/BT)`` must render RIGHT WAY UP.

Both renderers author **y-down screen coordinates** -- lane 0 at y=0, each
band's label 13px *below* its own top edge -- but both wrapped that content
in ``svg_wrap_viewbox``, which unconditionally emitted a *math* frame
(``viewBox="0 -height w height"`` plus ``<g transform="scale(1,-1)">``, y up).

The consequences were entirely silent: no exception, no red test, just a
picture that is upside down. The first-registered track drew at the BOTTOM,
and every ``<text>`` inside the flipped group drew as mirror-imaged glyphs.
``svg_timeline`` has the identical wrap and the identical inversion; it has
no text, which is the only reason nobody noticed there.

Everything here is verified by PARSING SVG COORDINATES. Every expected
number is derived by hand from the renderers' own layout arithmetic and the
derivation is written out below it, so a reader can check it without running
the code under test.
"""
import re

import pytest

from klotho.chronos import TemporalUnitSequence as UTS
from klotho.chronos.temporal_units.temporal import TemporalUnit, TemporalBlock
from klotho.thetos import Score, CompositionalUnit as UC


# ---------------------------------------------------------------------------
# SVG coordinate parsing
# ---------------------------------------------------------------------------

def _svg_element(html):
    """The ``<svg>...</svg>`` substring, excluding any trailing tooltip HTML."""
    start = html.index('<svg')
    end = html.index('</svg>') + len('</svg>')
    return html[start:end]


def _viewbox(svg):
    m = re.search(r'viewBox="([^"]+)"', svg)
    assert m, f"no viewBox in svg: {svg[:200]}"
    parts = [float(v) for v in m.group(1).split()]
    assert len(parts) == 4, m.group(1)
    return parts  # [min_x, min_y, width, height]


def _is_flipped(svg):
    """True when the content sits inside a y-inverting group."""
    return '<g transform="scale(1,-1)">' in svg


def _depth_from_top(authored_y, viewbox, flipped):
    """Distance in px from the TOP edge of the rendered picture, for a
    coordinate the renderer authored as *authored_y*.

    Under ``scale(1,-1)`` an authored y maps to -y; the top edge of the
    picture is the viewBox's ``min_y`` either way.
    """
    min_y = viewbox[1]
    rendered_y = -authored_y if flipped else authored_y
    return rendered_y - min_y


def _label_y(svg, label):
    """Authored ``y`` of the ``<text>`` element whose content is *label*."""
    m = re.search(r'<text[^>]*\by="(-?[\d.]+)"[^>]*>' + re.escape(label)
                  + r'</text>', svg)
    assert m, f"no <text> for {label!r} in svg"
    return float(m.group(1))


def _rect_y(svg, element_id):
    m = re.search(r'<rect[^>]*\bid="' + re.escape(element_id)
                  + r'"[^>]*\by="(-?[\d.]+)"', svg)
    assert m, f"no <rect id={element_id!r}> in svg"
    return float(m.group(1))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _one_lane_uc():
    """A CompositionalUnit is a TemporalUnit, so ``_resolve_lanes`` gives it
    height 1 -- one lane per band, which keeps the arithmetic below simple."""
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)


def _three_track_score():
    score = Score()
    score.track('alpha')
    score.track('beta')
    score.track('gamma')
    score.append(_one_lane_uc(), name='a', track='alpha')
    score.append(_one_lane_uc(), name='b', track='beta')
    score.append(_one_lane_uc(), name='c', track='gamma')
    return score


def _render_score():
    from klotho.semeios.visualization._renderers.svg_score import (
        _svg_score_timeline)
    # figsize is pinned so the derivation below is exact: the default is
    # 0.6 * lanes inches, which lands on a float that int()-truncates.
    return _svg_score_timeline(_three_track_score(), figsize=(12, 3))


# ---------------------------------------------------------------------------
# LAYOUT DERIVATION -- Score (by hand, from svg_score.py's own arithmetic;
# no expected value here was read off a rendered SVG)
#
#   figsize=(12, 3)  ->  width_px = int(12*100) = 1200
#                        height_px = int(3*100) = 300
#   Three bands of one lane each  ->  lanes = 3
#   lane_h = height_px / lanes = 300 / 3 = 100
#
#   Bands stack in track-REGISTRATION order (_score_bands walks
#   ``score._tracks``), so:
#
#       band     lane_start   authored y0 = lane_start * lane_h
#       alpha         0                 0.0
#       beta          1               100.0
#       gamma         2               200.0
#
#   svg_score.py:164 writes each label at ``y0 + 13`` -- 13px BELOW its own
#   band's top edge. That offset only makes sense in a y-DOWN frame, and it
#   is the renderer's own statement of which way is up:
#
#       alpha label authored y =   0 + 13 =  13
#       beta  label authored y = 100 + 13 = 113
#       gamma label authored y = 200 + 13 = 213
#
#   In a y-down frame those numbers ARE the distances from the top of the
#   picture, so first-registered renders nearest the top.
#
#   Under the old math-frame wrap (viewBox "0 -300 1200 300" + scale(1,-1))
#   an authored y maps to -y against a top edge of -300:
#
#       alpha: -13  ->  287px from the top   (the BOTTOM of the picture)
#       beta:  -113 ->  187px from the top
#       gamma: -213 ->   87px from the top   (the TOP of the picture)
#
#   -- exactly reversed, with mirrored glyphs on top of it.
# ---------------------------------------------------------------------------

_EXPECTED_LABEL_DEPTH = {'alpha': 13.0, 'beta': 113.0, 'gamma': 213.0}


class TestScoreRendersRightWayUp:

    def test_first_registered_track_renders_nearest_the_top(self):
        svg = _svg_element(_render_score().svg_str)
        vb, flipped = _viewbox(svg), _is_flipped(svg)
        depths = {name: _depth_from_top(_label_y(svg, name), vb, flipped)
                  for name in ('alpha', 'beta', 'gamma')}
        assert depths['alpha'] < depths['beta'] < depths['gamma'], (
            f"track bands are upside down: {depths}"
        )

    def test_track_label_depths_match_the_hand_derivation(self):
        svg = _svg_element(_render_score().svg_str)
        vb, flipped = _viewbox(svg), _is_flipped(svg)
        for name, expected in _EXPECTED_LABEL_DEPTH.items():
            got = _depth_from_top(_label_y(svg, name), vb, flipped)
            assert got == pytest.approx(expected), (
                f"{name}: label sits {got}px from the top, derived {expected}px"
            )

    def test_no_glyph_is_mirror_imaged(self):
        """A y-down frame needs no inversion anywhere -- neither the wrapper
        group nor a per-text counter-transform. Any ``scale(1,-1)`` left in
        the score SVG mirrors text (or undoes a mirror that should not exist)."""
        svg = _svg_element(_render_score().svg_str)
        assert 'scale(1,-1)' not in svg, (
            "score SVG still contains a y-inverting transform; <text> "
            "elements inside it render as upside-down mirrored glyphs"
        )

    def test_viewbox_is_the_screen_frame(self):
        sd = _render_score()
        vb = _viewbox(_svg_element(sd.svg_str))
        assert vb[1] == pytest.approx(0.0), f"viewBox min_y should be 0: {vb}"
        assert vb[3] == pytest.approx(float(sd.height_px)), vb

    def test_band_separator_rule_sits_between_the_bands(self):
        """The rule drawn at a band's ``lane_start * lane_h`` must land
        between the label above it and the label below it."""
        svg = _svg_element(_render_score().svg_str)
        vb, flipped = _viewbox(svg), _is_flipped(svg)
        rules = [float(m) for m in
                 re.findall(r'<line x1="0" y1="(-?[\d.]+)"', svg)]
        # derived: rules at authored y = 100 and 200 (lane_start 1 and 2;
        # lane_start 0 draws none)
        depths = sorted(_depth_from_top(y, vb, flipped) for y in rules)
        assert depths == pytest.approx([100.0, 200.0]), depths
        alpha = _depth_from_top(_label_y(svg, 'alpha'), vb, flipped)
        beta = _depth_from_top(_label_y(svg, 'beta'), vb, flipped)
        assert alpha < depths[0] < beta


# ---------------------------------------------------------------------------
# LAYOUT DERIVATION -- TemporalBlock timeline (svg_timeline.py)
#
#   BT with two TemporalUnit rows -> _resolve_lanes stacks them:
#   row 0 at lane 0, row 1 at lane 1, lanes = 2.
#
#   figsize=(11, 2)  ->  width_px = 1100, height_px = 200
#   lane_h = 200 / 2 = 100
#
#   A leaf strip's top edge (svg_timeline.py:215) is
#       by0 = lane * lane_h + (1 - bar_h_frac) / 2 * lane_h
#           = lane * 100 + (1 - 0.2) / 2 * 100
#           = lane * 100 + 40
#
#       row 0 (steps 0..) authored y =   0 + 40 =  40
#       row 1 (steps ..N) authored y = 100 + 40 = 140
#
#   Steps are emitted in _resolve_lanes DFS order, so step 0 belongs to
#   row 0 and the LAST step belongs to row 1. Row 0 must render above row 1.
# ---------------------------------------------------------------------------

def _two_row_block():
    # sort_rows=False pins "row 0 is the one passed first" against the
    # duration-sorting default (and its announced change).
    return TemporalBlock([
        TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120),
        TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120),
    ], sort_rows=False)


class TestTimelineRendersRightWayUp:

    def test_block_row_zero_renders_above_row_one(self):
        from klotho.semeios.visualization._renderers.svg_timeline import (
            _svg_timeline_ratios)
        sd = _svg_timeline_ratios(_two_row_block(), figsize=(11, 2))
        svg = _svg_element(sd.svg_str)
        vb, flipped = _viewbox(svg), _is_flipped(svg)

        first = sd.step_element_ids[0][0]
        last = sd.step_element_ids[-1][0]
        d_first = _depth_from_top(_rect_y(svg, first), vb, flipped)
        d_last = _depth_from_top(_rect_y(svg, last), vb, flipped)

        assert d_first == pytest.approx(40.0), (
            f"row 0 strip sits {d_first}px from the top, derived 40px")
        assert d_last == pytest.approx(140.0), (
            f"row 1 strip sits {d_last}px from the top, derived 140px")
        assert d_first < d_last, "TemporalBlock rows are upside down"

    def test_timeline_viewbox_is_the_screen_frame(self):
        from klotho.semeios.visualization._renderers.svg_timeline import (
            _svg_timeline_ratios)
        sd = _svg_timeline_ratios(UTS([
            TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120)]))
        vb = _viewbox(_svg_element(sd.svg_str))
        assert vb[1] == pytest.approx(0.0), f"viewBox min_y should be 0: {vb}"
        assert vb[3] == pytest.approx(float(sd.height_px)), vb


# ---------------------------------------------------------------------------
# The other side of the blast radius: callers that author GENUINE y-up math
# coordinates must keep flipping. Un-flipping svg_rt would break a renderer
# that is currently correct -- and just as silently.
# ---------------------------------------------------------------------------

class TestMathFrameCallersStillFlip:

    def test_svg_wrap_viewbox_still_flips_by_default(self):
        from klotho.semeios.visualization._shared.svg_utils import (
            svg_wrap_viewbox)
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200,
                                y_min=-10, y_max=190)
        assert '<g transform="scale(1,-1)">' in html
        assert _viewbox(_svg_element(html))[1] == pytest.approx(-190.0)

    def test_svg_rt_still_renders_in_the_math_frame(self):
        from klotho.chronos import RhythmTree
        from klotho.semeios.visualization._renderers.svg_rt import _svg_rt_tree
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        svg = _svg_element(_svg_rt_tree(rt).svg_str)
        assert _is_flipped(svg), (
            "svg_rt authors y-up math coordinates and counter-flips its own "
            "text via svg_text(invert_y=True); it must keep the flip"
        )
        assert _viewbox(svg)[1] < 0.0
