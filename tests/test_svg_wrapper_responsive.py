"""Regression: svg_wrap and svg_wrap_viewbox render at figsize px with horizontal scroll."""
import re

import pytest

from klotho.semeios.visualization._shared.svg_utils import (
    svg_wrap, svg_wrap_viewbox,
)


def _outer_div(html):
    m = re.search(r'<div[^>]*>', html)
    assert m is not None, f"no outer div in html: {html[:200]}"
    return m.group(0)


def _svg_tag(html):
    m = re.search(r'<svg[^>]*>', html)
    assert m is not None, f"no <svg> tag in html: {html[:200]}"
    return m.group(0)


class TestSvgWrap:
    def test_svg_has_fixed_pixel_dimensions(self):
        html = svg_wrap('<circle r="5"/>', 400, 200)
        svg_tag = _svg_tag(html)
        assert re.search(r'\bwidth="400"', svg_tag), svg_tag
        assert re.search(r'\bheight="200"', svg_tag), svg_tag

    def test_svg_viewbox_present(self):
        html = svg_wrap('<circle r="5"/>', 400, 200)
        assert 'viewBox="0 0 400 200"' in html

    def test_outer_div_scrolls_horizontally(self):
        html = svg_wrap('<circle r="5"/>', 400, 200)
        div_tag = _outer_div(html)
        assert 'overflow-x:auto' in div_tag, (
            f"outer div should enable horizontal scrolling: {div_tag!r}"
        )

    def test_outer_div_respects_container(self):
        html = svg_wrap('<circle r="5"/>', 400, 200)
        div_tag = _outer_div(html)
        assert 'max-width:100%' in div_tag, (
            f"outer div should cap at container width: {div_tag!r}"
        )

    def test_outer_div_has_no_background(self):
        html = svg_wrap('<circle r="5"/>', 400, 200, background='black')
        div_tag = _outer_div(html)
        assert 'background:black' not in div_tag, (
            f"outer div must not paint its background: {div_tag!r}"
        )

    def test_background_applied_to_svg_only(self):
        html = svg_wrap('<circle r="5"/>', 400, 200, background='black')
        svg_tag = _svg_tag(html)
        assert 'background:black' in svg_tag


class TestSvgWrapViewbox:
    def test_viewbox_preserved(self):
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200, y_min=-10, y_max=190)
        assert 'viewBox="0 -190.0000 800 200.0000"' in html

    def test_fixed_pixel_dimensions(self):
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200, y_min=-10, y_max=190)
        svg_tag = _svg_tag(html)
        assert re.search(r'\bwidth="800"', svg_tag), svg_tag
        assert re.search(r'\bheight="200"', svg_tag), svg_tag

    def test_outer_div_scrolls_and_no_background(self):
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200, y_min=-10, y_max=190,
                                 background='black')
        div_tag = _outer_div(html)
        assert 'overflow-x:auto' in div_tag
        assert 'max-width:100%' in div_tag
        assert 'background:black' not in div_tag

    def test_scale_invert_group_preserved(self):
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200, y_min=-10, y_max=190)
        assert '<g transform="scale(1,-1)">' in html

    def test_preserve_aspect_ratio_none(self):
        """Content should fill the display box exactly (no letterboxing)."""
        html = svg_wrap_viewbox('<circle r="5"/>', 800, 200, y_min=-10, y_max=220)
        assert 'preserveAspectRatio="none"' in html
