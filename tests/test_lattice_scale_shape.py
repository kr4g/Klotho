"""Tests: ``plot(lattice, nodes=<Scale>)`` — node highlighting + scale-run playback."""

import pytest

from klotho.semeios.visualization._animation.animated import (
    AnimatedLattice3dSelectFigure,
    AnimatedNodeSelectSvgFigure,
)
from klotho.semeios.visualization._dispatch.plot_lattice import (
    _plot_lattice,
    _resolve_scale_nodes,
    _scale_nodes_run,
)
from klotho.tonos import Chord, Scale, ToneLattice


@pytest.fixture
def tl_3x5():
    return ToneLattice.from_generators((3, 5), resolution=2, equave_reduce=True)


class TestResolveScaleNodes:
    def test_non_scale_falls_through(self, tl_3x5):
        assert _resolve_scale_nodes(tl_3x5, None) is None
        assert _resolve_scale_nodes(tl_3x5, [(0, 0), (1, 0)]) is None

    def test_resolves_one_coord_per_degree(self, tl_3x5):
        scale, coords = _resolve_scale_nodes(tl_3x5, Scale())
        assert len(coords) == len(scale.degrees)
        assert coords[0] == (0, 0)
        assert all(c in tl_3x5 for c in coords)

    def test_rooted_scale_resolves(self, tl_3x5):
        scale, coords = _resolve_scale_nodes(tl_3x5, Scale().root('D'))
        assert len(coords) == len(scale.degrees)

    def test_unresolvable_degree_raises(self, tl_3x5):
        with pytest.raises(ValueError, match="do not correspond to nodes"):
            _resolve_scale_nodes(tl_3x5, Scale(['1', '13/8', '3/2']))


class TestScaleNodesRun:
    def test_up_and_down_with_octave_step(self, tl_3x5):
        scale, coords = _resolve_scale_nodes(tl_3x5, Scale())
        n = len(coords)
        freqs, run_coords = _scale_nodes_run(scale, coords, equaves=1)
        assert len(freqs) == len(run_coords) == (n + 1) + n
        assert run_coords[0] == run_coords[-1] == coords[0]
        assert run_coords[n] == coords[0]          # octave selects the root node
        assert freqs[n] == pytest.approx(freqs[0] * 2)
        assert freqs == sorted(freqs[:n + 1]) + sorted(freqs[n + 1:], reverse=True)

    def test_equaves_scales_run_length(self, tl_3x5):
        scale, coords = _resolve_scale_nodes(tl_3x5, Scale())
        n = len(coords)
        freqs, run_coords = _scale_nodes_run(scale, coords, equaves=2)
        assert len(run_coords) == (2 * n + 1) + 2 * n
        assert freqs[2 * n] == pytest.approx(freqs[0] * 4)

    def test_negative_equaves_descends(self, tl_3x5):
        scale, coords = _resolve_scale_nodes(tl_3x5, Scale())
        freqs, _ = _scale_nodes_run(scale, coords, equaves=-1)
        assert freqs[len(coords)] == pytest.approx(freqs[0] / 2)


class TestPlotScaleNodes:
    def test_static_highlights_without_shape_groups(self, tl_3x5):
        fig = _plot_lattice(tl_3x5, nodes=Scale(), figsize=(5, 4), fit=True)
        assert type(fig).__name__ == 'SvgLatticeData'
        assert not fig.shape_group_node_indices

    def test_scale_to_shape_redirects(self, tl_3x5):
        with pytest.raises(TypeError, match="Scale goes to nodes="):
            _plot_lattice(tl_3x5, shape=Scale())

    def test_animate_2d_select_figure(self, tl_3x5):
        fig = _plot_lattice(tl_3x5, nodes=Scale(), animate=True, fit=True)
        assert isinstance(fig, AnimatedNodeSelectSvgFigure)
        n = len(Scale().degrees)
        assert len(fig.select_node_indices) == (n + 1) + n
        assert all(i >= 0 for i in fig.select_node_indices)
        assert fig.select_node_indices[0] == fig.select_node_indices[n]
        assert fig.audio_payload is not None

    def test_animate_keeps_connector_edges(self, tl_3x5):
        static = _plot_lattice(tl_3x5, nodes=Scale(), fit=True)
        anim = _plot_lattice(tl_3x5, nodes=Scale(), animate=True, fit=True)
        marker = 'stroke="white" stroke-width="4"'
        n_edges = static.svg_str.count(marker)
        assert n_edges > 0
        assert anim.svg_data.svg_str.count(marker) == n_edges

    def test_animate_3d_select_figure(self):
        tl = ToneLattice(3, resolution=4, equave_reduce=True)
        fig = _plot_lattice(tl, nodes=Scale.bagpipes(), animate=True, fit=True)
        assert isinstance(fig, AnimatedLattice3dSelectFigure)
        sel = fig.scene_data.scene_data['selectNodeIndices']
        assert sel and all(i >= 0 for i in sel)

    def test_animate_reduced_4d(self):
        tl = ToneLattice(4, resolution=4, equave_reduce=True)
        fig = _plot_lattice(tl, nodes=Scale.janus(), animate=True, fit='tight')
        sel = fig.scene_data.scene_data['selectNodeIndices']
        assert sel and all(i >= 0 for i in sel)

    def test_equaves_kwarg(self, tl_3x5):
        n = len(Scale().degrees)
        fig = _plot_lattice(tl_3x5, nodes=Scale(), animate=True, equaves=2)
        assert len(fig.select_node_indices) == (2 * n + 1) + 2 * n

    def test_coordinate_nodes_unaffected(self, tl_3x5):
        fig = _plot_lattice(tl_3x5, nodes=[(0, 0), (1, 0)], animate=True)
        assert not isinstance(fig, AnimatedNodeSelectSvgFigure)

    def test_chord_shape_unaffected(self, tl_3x5):
        fig = _plot_lattice(tl_3x5, shape=Chord([1, '5/4', '3/2']), animate=True)
        assert not isinstance(fig, AnimatedNodeSelectSvgFigure)

    def test_select_html_renders(self, tl_3x5):
        html = _plot_lattice(tl_3x5, nodes=Scale(), animate=True).to_html()
        assert 'selectIdx' in html and 'allNodeIds' in html
