"""Regression: ToneLattice / CPS / MasterSet plot+play family parity.

The three "tone-lattice-like" classes must all support ``nodes``,
``shape``, and ``path`` in both 2D (SVG) and 3D (Three.js), including
animated playback figures. Also covers the generator-based ToneLattice
titles and the ND hover-text cleanup.
"""
import pytest

from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.tonos.systems.combination_product_sets import (
    CombinationProductSet, MasterSet,
)
from klotho.topos.graphs.lattices import Lattice
from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
from klotho.semeios.visualization._dispatch.plot_cps import (
    _plot_cps, _plot_master_set,
)
from klotho.semeios.visualization._animation import (
    AnimatedLattice3dFigure, AnimatedLattice3dShapeFigure,
    AnimatedLatticeShapeFigure, ClickPreviewFigure,
)
from klotho.semeios.visualization._shared.colors import SHAPE_COLORS


@pytest.fixture
def tl_3d():
    return ToneLattice.from_generators(('3/2', '5/4', '7/4'), resolution=1,
                                       equave_reduce=True)


@pytest.fixture
def cps_3d():
    return CombinationProductSet((1, 3, 5, 7), 2, master_set='tetrad_3d')


@pytest.fixture
def ms_3d():
    return MasterSet.octahedron().with_factors((1, 3, 5, 7, 9, 11))


class TestLattice3dShape:
    SHAPE = [(0, 0, 0), (1, 0, 0), (0, 1, 0)]

    def test_static_scene_has_shape_data(self, tl_3d):
        fig = _plot_lattice(tl_3d, figsize=(5, 5), shape=self.SHAPE)
        sd = fig.scene_data
        assert len(sd['shapeGroupNodeIndices']) == 1
        assert all(i >= 0 for i in sd['shapeGroupNodeIndices'][0])
        assert sd['shapeColors'] == [SHAPE_COLORS[0]]
        # (0,0,0)-(1,0,0) and (0,0,0)-(0,1,0) are lattice-adjacent.
        assert len(sd['shapeGroupEdges'][0]) == 2
        # Shape nodes are colored with the group color.
        for i in sd['shapeGroupNodeIndices'][0]:
            assert sd['nodeColors'][i] == SHAPE_COLORS[0]

    def test_static_html_renders_shape(self, tl_3d):
        fig = _plot_lattice(tl_3d, figsize=(5, 5), shape=self.SHAPE)
        html = fig.to_html()
        assert 'shapeEdgeObjs' in html

    def test_animate_returns_3d_shape_figure(self, tl_3d):
        fig = _plot_lattice(tl_3d, figsize=(5, 5), animate=True, shape=self.SHAPE)
        assert isinstance(fig, AnimatedLattice3dShapeFigure)
        html = fig.to_html()
        assert 'revealGroupVisual' in html
        assert '_prev' in html and '_next' in html
        synths = {e['defName'] for e in fig.audio_payload['events']
                  if e.get('type') == 'new'}
        assert synths == {'kl_tri'}

    def test_multi_group_shape(self, tl_3d):
        fig = _plot_lattice(tl_3d, figsize=(5, 5),
                            shape=[[(0, 0, 0), (1, 0, 0)], [(0, 1, 0), (0, 0, 1)]])
        sd = fig.scene_data
        assert len(sd['shapeGroupNodeIndices']) == 2
        assert sd['shapeColors'] == [SHAPE_COLORS[0], SHAPE_COLORS[1]]

    def test_2d_shape_animation_still_works(self):
        tl = ToneLattice.from_generators(('3/2', '5/4'), resolution=2,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(5, 5), animate=True,
                            shape=[(0, 0), (1, 0), (0, 1)])
        assert isinstance(fig, AnimatedLatticeShapeFigure)
        html = fig.to_html()
        # Hook contract of the refactored shape playback.
        assert 'revealGroupVisual' in html
        assert 'dimAllNodes' in html
        assert 'hideAllShapeEdges' in html


class TestCPS3dParity:
    def test_static_path_renders(self, cps_3d):
        labels = list(cps_3d.nodes)[:4]
        fig = _plot_cps(cps_3d, path=labels)
        assert len(fig.path_steps) == len(labels) - 1
        assert fig.halo_data is not None

    def test_animate_path(self, cps_3d):
        labels = list(cps_3d.nodes)[:4]
        fig = _plot_cps(cps_3d, animate=True, path=labels)
        assert isinstance(fig, AnimatedLattice3dFigure)
        assert len(fig.audio_payload['events']) > 0

    def test_animate_shape(self, cps_3d):
        labels = list(cps_3d.nodes)[:3]
        fig = _plot_cps(cps_3d, animate=True, shape=labels)
        assert isinstance(fig, AnimatedLattice3dShapeFigure)
        sd = fig.scene_data.scene_data
        assert len(sd['shapeGroupNodeIndices']) == 1
        assert sd['shapeColors'] == [SHAPE_COLORS[0]]

    def test_static_shape_renders(self, cps_3d):
        labels = list(cps_3d.nodes)[:3]
        fig = _plot_cps(cps_3d, shape=labels)
        sd = fig.scene_data
        assert len(sd['shapeGroupNodeIndices']) == 1

    def test_bare_animate_is_click_preview(self, cps_3d):
        fig = _plot_cps(cps_3d, animate=True)
        assert isinstance(fig, ClickPreviewFigure)

    def test_bare_static_unchanged(self, cps_3d):
        fig = _plot_cps(cps_3d)
        assert fig.scene_data['nodeFreqs'] is None
        assert fig.scene_data['previewConfig'] is None

    def test_2d_cps_unchanged(self):
        hexany = CombinationProductSet.hexany()
        fig = _plot_cps(hexany)
        assert hasattr(fig, 'svg_str')


class TestMasterSet3dShape:
    def test_animate_shape(self, ms_3d):
        labels = sorted(ms_3d.positions)[:3]
        fig = _plot_master_set(ms_3d, animate=True, shape=labels)
        assert isinstance(fig, AnimatedLattice3dShapeFigure)
        html = fig.to_html()
        assert 'revealGroupVisual' in html

    def test_static_shape_scene_data(self, ms_3d):
        labels = sorted(ms_3d.positions)[:3]
        fig = _plot_master_set(ms_3d, shape=labels)
        sd = fig.scene_data
        assert len(sd['shapeGroupNodeIndices']) == 1
        assert all(i >= 0 for i in sd['shapeGroupNodeIndices'][0])

    def test_bare_animate_is_click_preview(self, ms_3d):
        fig = _plot_master_set(ms_3d, animate=True)
        assert isinstance(fig, ClickPreviewFigure)


class TestToneLatticeTitles:
    def test_fraction_generators(self):
        tl = ToneLattice.from_generators(('3/2', '5/4'), resolution=1,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4))
        assert '3/2 x 5/4 (Octave Reduced)' in fig.svg_str

    def test_prime_generators(self):
        tl = ToneLattice(3, resolution=1, equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4))
        html = fig.to_html()
        assert '3 x 5 x 7 (Octave Reduced)' in html

    def test_non_octave_equave(self):
        tl = ToneLattice.from_generators((2, 5), resolution=1,
                                         equave_reduce=True, equave=3)
        fig = _plot_lattice(tl, figsize=(4, 4))
        assert '2 x 5 (Equave Reduced)' in fig.svg_str

    def test_no_reduction_no_parenthetical(self):
        tl = ToneLattice.from_generators((3, 5), resolution=1,
                                         equave_reduce=False)
        fig = _plot_lattice(tl, figsize=(4, 4))
        assert '3 x 5' in fig.svg_str
        assert 'Reduced' not in fig.svg_str

    def test_explicit_title_wins(self):
        tl = ToneLattice.from_generators((3, 5), resolution=1,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4), title='Custom Title')
        assert 'Custom Title' in fig.svg_str
        assert 'Octave Reduced' not in fig.svg_str

    def test_plain_lattice_title_unchanged(self):
        lat = Lattice(2, resolution=2)
        fig = _plot_lattice(lat, figsize=(4, 4))
        assert '2D Lattice' in fig.svg_str

    def test_nd_tone_lattice_generator_title(self):
        tl = ToneLattice.from_generators((3, 5, 7, 11), resolution=1,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4), target_dims=2,
                            dim_reduction='pca')
        assert '3 x 5 x 7 x 11 (Octave Reduced)' in fig.svg_str


class TestNDHoverText:
    def test_2d_reduced_hover_uses_coord_label(self):
        tl = ToneLattice.from_generators((3, 5, 7, 11), resolution=1,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4), target_dims=2,
                            dim_reduction='pca')
        assert 'Original:' not in fig.svg_str
        assert 'Reduced:' not in fig.svg_str
        assert 'Monzo: (' in fig.svg_str

    def test_3d_reduced_hover_uses_coord_label(self):
        tl = ToneLattice.from_generators((3, 5, 7, 11), resolution=1,
                                         equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4), target_dims=3,
                            dim_reduction='pca')
        html = fig.to_html()
        assert 'Original:' not in html
        assert 'Reduced:' not in html
        assert 'Monzo: (' in html

    def test_non_prime_basis_uses_coordinate_label(self):
        tl = ToneLattice.from_generators(('3/2', '5/4', '7/4', '11/8'),
                                         resolution=1, equave_reduce=True)
        fig = _plot_lattice(tl, figsize=(4, 4), target_dims=2,
                            dim_reduction='pca')
        assert 'Coordinate: (' in fig.svg_str
        assert 'Monzo' not in fig.svg_str
