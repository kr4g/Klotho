"""Regression: MasterSet plot/play has parity with CPS."""
import re
from unittest.mock import patch

import pytest

from klotho.tonos.systems.combination_product_sets import MasterSet
from klotho.semeios.visualization.plots import plot
from klotho.semeios.visualization._dispatch import KlothoPlot
from klotho.semeios.visualization._dispatch.plot_cps import _plot_master_set
from klotho.semeios.visualization._animation import (
    AnimatedCPSSvgFigure, AnimatedCPSShapeFigure, AnimatedLattice3dFigure,
)


@pytest.fixture
def ms_2d_with_factors():
    return MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))


@pytest.fixture
def ms_3d_with_factors():
    return MasterSet.octahedron().with_factors((1, 3, 5, 7, 9, 11))


class TestPlotDispatch:
    def test_plot_returns_klotho_plot(self, ms_2d_with_factors):
        with patch('IPython.display.display'):
            p = plot(ms_2d_with_factors)
        assert isinstance(p, KlothoPlot), f"expected KlothoPlot, got {type(p).__name__}"

    def test_plot_has_play_method(self, ms_2d_with_factors):
        with patch('IPython.display.display'):
            p = plot(ms_2d_with_factors)
        assert callable(getattr(p, 'play', None)), ".play must be callable"


class TestPathSupport2D:
    def test_static_2d_path(self, ms_2d_with_factors):
        fig = _plot_master_set(ms_2d_with_factors, path=['A', 'B', 'C'])
        assert 'svg_str' in dir(fig)
        assert fig.path_node_indices == [0, 1, 2]
        assert len(fig.path_node_colors) == 3

    def test_animated_2d_path(self, ms_2d_with_factors):
        fig = _plot_master_set(
            ms_2d_with_factors, path=['A', 'B', 'C'], animate=True)
        assert isinstance(fig, AnimatedCPSSvgFigure)
        assert fig.audio_payload is not None


class TestShapeSupport2D:
    def test_static_2d_shape(self, ms_2d_with_factors):
        fig = _plot_master_set(ms_2d_with_factors, shape=['A', 'B', 'C'])
        assert len(fig.shape_group_node_indices) == 1
        assert fig.shape_group_node_indices[0] == [0, 1, 2]

    def test_animated_2d_shape(self, ms_2d_with_factors):
        fig = _plot_master_set(
            ms_2d_with_factors, shape=['A', 'B', 'C'], animate=True)
        assert isinstance(fig, AnimatedCPSShapeFigure)


class TestNodesSupport2D:
    def test_static_2d_nodes_highlight(self, ms_2d_with_factors):
        fig = _plot_master_set(ms_2d_with_factors, nodes=['A'])
        # Highlighted node should appear active → light tooltip styling
        # should be available via is_active_list in tooltip HTML.
        assert 'active=' in fig.svg_str

    def test_mute_background_with_nodes(self, ms_2d_with_factors):
        fig = _plot_master_set(
            ms_2d_with_factors, nodes=['A'], mute_background=True)
        # Mute background should still render; ensure no exception.
        assert fig.svg_str


class TestPathSupport3D:
    def test_static_3d_path(self, ms_3d_with_factors):
        fig = _plot_master_set(ms_3d_with_factors, path=['A', 'B', 'C'])
        scene = fig.scene_data
        assert scene['pathNodeIndices']
        # Static mode: click-to-play disabled even when a path is shown.
        assert scene['nodeFreqs'] is None

    def test_animated_3d_path(self, ms_3d_with_factors):
        fig = _plot_master_set(
            ms_3d_with_factors, path=['A', 'B', 'C'], animate=True)
        assert isinstance(fig, AnimatedLattice3dFigure)
        assert fig.audio_payload is not None


class TestClickToPlayOnlyWhenAnimate:
    """Click-to-play is reserved for the ``.play()`` path (animate=True)."""

    def test_static_2d_has_no_freqs(self, ms_2d_with_factors):
        fig = _plot_master_set(ms_2d_with_factors)
        freqs_match = re.search(r'var freqs=([^;]+);', fig.svg_str)
        assert freqs_match and freqs_match.group(1).strip() == 'null'

    def test_animated_2d_has_freqs_without_selection(self, ms_2d_with_factors):
        fig = _plot_master_set(ms_2d_with_factors, animate=True)
        html = fig.to_html()
        assert '_playFreq' in html
        freqs_match = re.search(r'var freqs=(\[[^\]]*\])', html)
        assert freqs_match and freqs_match.group(1) not in ('[]', 'null')

    def test_static_3d_has_no_freqs(self, ms_3d_with_factors):
        fig = _plot_master_set(ms_3d_with_factors)
        html = fig.to_html()
        assert '"nodeFreqs": null' in html or '"nodeFreqs":null' in html

    def test_animated_3d_has_freqs_without_selection(self, ms_3d_with_factors):
        fig = _plot_master_set(ms_3d_with_factors, animate=True)
        html = fig.to_html()
        assert '"nodeFreqs":' in html
        assert '"nodeFreqs": null' not in html and '"nodeFreqs":null' not in html


class TestPathFromShortestPath:
    def test_no_duplicate_first_note_in_payload(self, ms_2d_with_factors):
        # Provide a path where the first two nodes are distinct (equivalent
        # of a dedup'd shortest_path output).  Make sure the generated audio
        # payload's first two events target distinct frequencies.
        path = ['A', 'B', 'C']
        fig = _plot_master_set(ms_2d_with_factors, path=path, animate=True)
        events = fig.audio_payload if isinstance(fig.audio_payload, list) \
            else fig.audio_payload.get('events', [])
        # Extract 'freq' pfield from the first two 'new' events.
        freqs_in_order = []
        for ev in events:
            if isinstance(ev, dict) and ev.get('type') == 'new':
                freq = None
                if 'pfields' in ev and 'freq' in ev.get('pfields', {}):
                    freq = ev['pfields']['freq']
                elif 'freq' in ev:
                    freq = ev['freq']
                if freq is not None:
                    freqs_in_order.append(freq)
            if len(freqs_in_order) >= 2:
                break
        assert len(freqs_in_order) >= 2
        assert freqs_in_order[0] != freqs_in_order[1], (
            f"first two payload freqs are duplicated: {freqs_in_order}"
        )
