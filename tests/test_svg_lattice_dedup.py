"""Structural regression for the _svg_lattice_2d shared-helper refactor.

The path/shape rendering of the 2D lattice renderer was deduplicated
into ``svg_shared.render_path_edges`` / ``render_shape_groups``. Output
equivalence with the pre-refactor renderer was verified byte-for-byte
(normalized ids) across a 16-case matrix during the refactor; these
tests pin the structural invariants the animated figures rely on.
"""
import re

from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
from klotho.semeios.visualization._shared.colors import SHAPE_COLORS


def _tl(res=2):
    return ToneLattice.from_generators((3, 5), resolution=res, equave_reduce=True)


class TestPathStructure:
    def test_step_groups_match_path_edges(self):
        path = [(0, 0), (1, 0), (1, 1), (0, 1)]
        fig = _plot_lattice(_tl(), figsize=(5, 5), path=path)
        assert len(fig.step_group_ids) == len(path) - 1
        for group in fig.step_group_ids:
            assert len(group) == 3  # glow, edge, arrow
        assert len(fig.halo_ids) == 2
        assert len(fig.path_node_indices) == len(path)
        assert len(fig.path_node_colors) == len(path)

    def test_repeated_edges_arc_as_beziers(self):
        # The same edge traversed repeatedly must curve on alternating
        # sides with growing offsets (drawn as quadratic Beziers).
        path = [(0, 0), (1, 0), (0, 0), (1, 0), (0, 0)]
        fig = _plot_lattice(_tl(), figsize=(5, 5), path=path)
        # traversals 1..3 arc; each arced step draws glow + colored path
        # with the same Q command -> 6 path elements with Q.
        q_count = len(re.findall(r'd="M[^"]*Q', fig.svg_str))
        assert q_count == 6
        # First traversal is a straight line.
        l_count = len(re.findall(r'd="M[^"]*L', fig.svg_str))
        assert l_count == 2

    def test_halo_radius_and_gradient(self):
        fig = _plot_lattice(_tl(), figsize=(5, 5), path=[(0, 0), (1, 0)])
        assert 'radialGradient' in fig.svg_str
        assert 'r="20"' in fig.svg_str

    def test_mute_background_reduces_nodes(self):
        path = [(0, 0), (1, 0), (1, 1)]
        full = _plot_lattice(_tl(), figsize=(5, 5), path=path)
        muted = _plot_lattice(_tl(), figsize=(5, 5), path=path,
                              mute_background=True)
        assert len(muted.all_node_ids) < len(full.all_node_ids)
        assert len(muted.all_node_ids) == 3


class TestShapeStructure:
    def test_group_colors_cycle(self):
        shape = [[(0, 0), (1, 0)], [(0, 1), (1, 1)], [(-1, -1), (0, -1)]]
        fig = _plot_lattice(_tl(), figsize=(5, 5), shape=shape)
        assert fig.shape_colors == [SHAPE_COLORS[0], SHAPE_COLORS[1], SHAPE_COLORS[2]]
        assert len(fig.shape_group_node_indices) == 3
        assert len(fig.shape_group_edge_ids) == 3
        # Each pair above is lattice-adjacent -> one edge per group.
        for gids in fig.shape_group_edge_ids:
            assert len(gids) == 1
        assert len(fig.all_shape_edge_ids) == 3

    def test_shape_edge_attributes(self):
        fig = _plot_lattice(_tl(), figsize=(5, 5), shape=[(0, 0), (1, 0)])
        m = re.search(r'<line id="[^"]+" [^>]*stroke="' + SHAPE_COLORS[0]
                      + r'" stroke-width="3" opacity="0.8"', fig.svg_str)
        assert m is not None

    def test_non_adjacent_members_draw_no_edge(self):
        # (0,0) and (1,1) are diagonal, not lattice-adjacent.
        fig = _plot_lattice(_tl(), figsize=(5, 5), shape=[(0, 0), (1, 1)])
        assert fig.shape_group_edge_ids == [[]]
        # Nodes still colored.
        assert all(i >= 0 for i in fig.shape_group_node_indices[0])


class TestOneDimensional:
    def test_1d_path_renders(self):
        tl1 = ToneLattice.from_generators((3,), resolution=3, equave_reduce=True)
        fig = _plot_lattice(tl1, figsize=(6, 2), path=[(0,), (1,), (2,)])
        assert len(fig.step_group_ids) == 2
        assert len(fig.halo_ids) == 2
