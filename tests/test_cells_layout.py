"""layout='cells' for ToneLattice plotting (2D rect cells / 3D translucent cubes).

The cells layout draws one filled square (2D) or cube (3D) per lattice
coordinate with no grid or connector edges. Highlights, shapes, and node
selections colour the cells; paths keep the standard arrow/bezier overlay
drawn between cell centers. Animation metadata must stay structurally
identical to the default layout so animated figures work unchanged.
"""
import pytest

from klotho.tonos import ToneLattice
from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice


def _fig(result):
    return getattr(result, 'fig', result)


@pytest.fixture
def tl2():
    return ToneLattice.from_generators((3, 5), resolution=3)


@pytest.fixture
def tl3():
    return ToneLattice.from_generators((3, 5, 7), resolution=2)


SHAPE_2D = [[(0, 0), (1, 0), (0, 1), (1, 1)], [(-2, -2), (-1, -2), (0, -2), (0, -1)]]
PATH_2D = [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0), (1, 0)]
SHAPE_3D = [[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]]
PATH_3D = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 1, 1)]


class TestCells2D:

    def test_bare_board(self, tl2):
        fig = _fig(_plot_lattice(tl2, layout='cells', figsize=(6, 6)))
        # one <rect> per coordinate plus the background rect; no circles or grid lines
        assert fig.svg_str.count('<rect') == 50
        assert '<circle' not in fig.svg_str.split('data-tip-uid')[0] or fig.svg_str.count('<circle id=') == 0
        assert 'stroke="#808080"' not in fig.svg_str
        assert len(fig.all_node_ids) == 49

    def test_shape_groups_colour_cells_without_edges(self, tl2):
        fig = _fig(_plot_lattice(tl2, layout='cells', shape=SHAPE_2D, figsize=(6, 6)))
        assert fig.shape_group_edge_ids == [[], []]
        assert len(fig.shape_colors) == 2
        assert all(len(g) == 4 and -1 not in g for g in fig.shape_group_node_indices)
        for color in fig.shape_colors:
            assert f'fill="{color}"' in fig.svg_str

    def test_path_metadata_matches_lattice_layout(self, tl2):
        cells = _fig(_plot_lattice(tl2, layout='cells', path=PATH_2D, figsize=(6, 6)))
        classic = _fig(_plot_lattice(tl2, layout='lattice', path=PATH_2D, figsize=(6, 6)))
        assert len(cells.step_group_ids) == len(classic.step_group_ids)
        assert len(cells.halo_ids) == len(classic.halo_ids) == 2
        assert cells.path_node_indices == classic.path_node_indices
        assert cells.path_node_colors == classic.path_node_colors
        assert '<polygon' in cells.svg_str  # arrowheads

    def test_nodes_highlight_cells(self, tl2):
        fig = _fig(_plot_lattice(tl2, layout='cells', nodes=[(0, 0), (1, 0)], figsize=(6, 6)))
        assert 'fill="white"' in fig.svg_str
        # no white connector edges in cells layout
        assert 'stroke="white" stroke-width="4"' not in fig.svg_str

    def test_mute_background(self, tl2):
        fig = _fig(_plot_lattice(tl2, layout='cells', nodes=[(0, 0), (1, 0)],
                                 mute_background=True, figsize=(6, 6)))
        assert len(fig.all_node_ids) == 2

    def test_animated_shape_figure_renders(self, tl2):
        afig = _plot_lattice(tl2, layout='cells', shape=SHAPE_2D, animate=True)
        html = afig.to_html()
        assert len(html) > 1000
        assert '<rect' in html

    def test_animated_path_figure_renders(self, tl2):
        afig = _plot_lattice(tl2, layout='cells', path=PATH_2D, animate=True)
        html = afig.to_html()
        assert len(html) > 1000

    def test_default_layout_unchanged(self, tl2):
        fig = _fig(_plot_lattice(tl2, figsize=(6, 6)))
        assert fig.svg_str.count('<circle id=') == 49
        assert fig.svg_str.count('<rect') == 1  # background only


class TestCells3D:

    def test_bare_board(self, tl3):
        fig = _fig(_plot_lattice(tl3, layout='cells', figsize=(7, 7)))
        sd = fig.scene_data
        assert sd['layout'] == 'cells'
        assert sd['gridEdges'] == []
        assert len(sd['nodes']) == 125
        assert sd['nodeOpacities'] is not None
        assert set(sd['nodeOpacities']) == {0.15}
        html = fig.to_html()
        assert 'BoxGeometry' in html and 'nodeMeshes' in html

    def test_shape_lit_cells_no_tubes(self, tl3):
        fig = _fig(_plot_lattice(tl3, layout='cells', shape=SHAPE_3D, figsize=(7, 7)))
        sd = fig.scene_data
        assert sd['shapeGroupEdges'] == [[]]
        assert sum(1 for o in sd['nodeOpacities'] if o == 0.9) == 4
        assert all(-1 not in g for g in sd['shapeGroupNodeIndices'])

    def test_path_steps_and_lit_cells(self, tl3):
        fig = _fig(_plot_lattice(tl3, layout='cells', path=PATH_3D, figsize=(7, 7)))
        sd = fig.scene_data
        assert len(fig.path_steps) == len(PATH_3D) - 1
        assert fig.halo_data is not None
        assert sum(1 for o in sd['nodeOpacities'] if o == 0.9) == len(set(PATH_3D))

    def test_animated_shape_figure_renders(self, tl3):
        afig = _plot_lattice(tl3, layout='cells', shape=SHAPE_3D, animate=True)
        html = afig.to_html()
        assert len(html) > 1000
        assert 'BoxGeometry' in html

    def test_default_layout_unchanged(self, tl3):
        fig = _fig(_plot_lattice(tl3, figsize=(7, 7)))
        sd = fig.scene_data
        assert sd['layout'] == 'lattice'
        assert len(sd['gridEdges']) > 0
        assert sd['nodeOpacities'] is None
        assert 'SphereGeometry' in fig.to_html()


class TestShapeColors:
    """Shape-carrying groups use their identity colors instead of the palette."""

    def test_2d_shape_colors(self, tl2):
        from klotho.topos.shapes import polyominoes, translate
        pieces = polyominoes(4)
        groups = [translate(pieces[0], (-3, -3)), translate(pieces[4], (1, 1))]
        fig = _fig(_plot_lattice(tl2, layout='cells', shape=groups, figsize=(6, 6)))
        assert fig.shape_colors == [g.color for g in groups]

    def test_3d_shape_colors(self, tl3):
        from klotho.topos.shapes import polyominoes, translate
        pieces = polyominoes(4, 3)
        groups = [translate(pieces[0], (-2, -2, -2)), translate(pieces[5], (0, 0, 0))]
        fig = _fig(_plot_lattice(tl3, layout='cells', shape=groups, figsize=(7, 7)))
        assert fig.scene_data['shapeColors'] == [g.color for g in groups]

    def test_plain_groups_still_cycle_palette(self, tl2):
        fig = _fig(_plot_lattice(tl2, layout='cells', shape=SHAPE_2D, figsize=(6, 6)))
        assert fig.shape_colors == ['#90EE90', '#FFD700']


class TestTrail:

    def test_2d_trail_renders_hook(self, tl2):
        html = _plot_lattice(tl2, layout='cells', shape=SHAPE_2D,
                             animate=True, trail=True).to_html()
        assert 'function renderTrail' in html
        assert '"0.3"' in html

    def test_2d_no_trail_by_default(self, tl2):
        html = _plot_lattice(tl2, layout='cells', shape=SHAPE_2D, animate=True).to_html()
        assert 'function renderTrail' not in html

    def test_3d_trail_and_cells_hide(self, tl3):
        html = _plot_lattice(tl3, layout='cells', shape=SHAPE_3D,
                             animate=True, trail=0.4).to_html()
        assert 'function renderTrail' in html
        assert '_shapeCellsMode' in html
        assert 'm.opacity = 0.15' in html  # inactive shapes match background
        assert 'm.opacity = 0.4' in html

    def test_cps_trail(self):
        from klotho.tonos import Hexany
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps
        html = _plot_cps(Hexany(), shape=[[0, 1, 2], [3, 4, 5]],
                         animate=True, trail=True).to_html()
        assert 'function renderTrail' in html


class TestValidation:

    def test_invalid_layout_raises(self, tl2):
        with pytest.raises(ValueError):
            _plot_lattice(tl2, layout='mosaic')

    def test_cells_above_3d_raises(self):
        tl4 = ToneLattice.from_generators((3, 5, 7, 11), resolution=1)
        with pytest.raises(ValueError):
            _plot_lattice(tl4, layout='cells')
