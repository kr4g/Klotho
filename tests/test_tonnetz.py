"""Tonnetz: triangular geometry, D6 symmetries, shape reflections, JI labels.

The neo-Riemannian P/L/R moves are *not* API — they are reflections of a
triangle across its fifth, minor-third, and major-third edges. These tests
pin the general ``reflect`` operation against the published coordinate
formulas (P: U(q,r) <-> D(q,r-1), L: U(q,r) <-> D(q,r), R: U(q,r) <-> D(q-1,r))
and the exact-JI consequences (E minor from L of C major; the I-vi-ii-V-I
syntonic comma pump).
"""
from fractions import Fraction as F

import pytest

from klotho.tonos import Tonnetz, ToneLattice
from klotho.topos.shapes import Shape, rotations, translate


def U(q, r):
    """Up-triangle (major) anchored at (q, r); root vertex (q, r)."""
    return Shape([(q, r), (q + 1, r), (q, r + 1)])


def D(q, r):
    """Down-triangle (minor) anchored at (q, r); root vertex (q, r+1)."""
    return Shape([(q + 1, r), (q, r + 1), (q + 1, r + 1)])


# Oblique metric of the isometric embedding, doubled to stay integer:
# 2G = [[2, 1], [1, 2]].
_2G = ((2, 1), (1, 2))


def _matmul(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2))
        for i in range(2)
    )


def _transpose(a):
    return tuple(zip(*a))


@pytest.fixture(scope='module')
def tz():
    return Tonnetz(resolution=6)


class TestBoard:
    def test_default_generators_and_directions(self, tz):
        assert tz.generators == [F(3, 2), F(5, 4)]
        assert tz.directions == {F(3, 2): (1, 0), F(5, 4): (0, 1), F(6, 5): (1, -1)}

    def test_six_neighbors_interior(self, tz):
        assert len(tz.neighbors((0, 0))) == 6
        assert set(tz.neighbors((0, 0))) == {
            (1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)
        }

    def test_third_direction_edges_exist(self, tz):
        assert tz.has_edge((0, 0), (1, -1))
        assert tz.has_edge((-2, 3), (-1, 2))
        assert not tz.has_edge((0, 0), (1, 1))

    def test_dimensionality_pinned_to_two(self):
        with pytest.raises(ValueError):
            Tonnetz(generators=('3/2', '5/4', '7/4'), resolution=2)

    def test_from_generators_weaves(self):
        tn = Tonnetz.from_generators(('6/5', '5/4'), resolution=3)
        assert isinstance(tn, Tonnetz)
        assert len(tn.neighbors((0, 0))) == 6
        assert tn.directions[F(6, 5)] == (1, 0)
        # derived third direction: (6/5)/(5/4) = 24/25 (inside the
        # bipolar reduction window, so it stays as-is)
        assert tn.directions[F(24, 25)] == (1, -1)

    def test_with_generators_preserves_type_board_reference(self, tz):
        rooted = tz.root('A3')
        tn = rooted.with_generators(('6/5', '5/4'))
        assert isinstance(tn, Tonnetz)
        assert len(tn.neighbors((0, 0))) == 6
        assert tn.resolution == tz.resolution
        assert tn.reference_pitch.freq == rooted.reference_pitch.freq


class TestSymmetries:
    def test_group_sizes(self, tz):
        assert len(tz.symmetries()) == 6
        assert len(tz.symmetries(reflections=True)) == 12
        assert len(set(tz.symmetries(reflections=True))) == 12

    def test_metric_invariance(self, tz):
        for a in tz.symmetries(reflections=True):
            assert _matmul(_matmul(_transpose(a), _2G), a) == _2G

    def test_rotation_order_six(self, tz):
        r60 = tz.symmetries()[1]
        m = ((1, 0), (0, 1))
        seen = []
        for _ in range(6):
            m = _matmul(r60, m)
            seen.append(m)
        assert m == ((1, 0), (0, 1))
        assert len(set(seen)) == 6

    def test_mirrors_are_involutions(self, tz):
        for m in tz.symmetries(reflections=True)[6:]:
            assert _matmul(m, m) == ((1, 0), (0, 1))

    def test_triangle_orbit_closes(self, tz):
        orbit = rotations(U(0, 0), group=tz.symmetries())
        assert set(orbit) == {tuple(U(0, 0)), tuple(D(0, 0))}
        orbit_all = rotations(U(0, 0), group=tz.symmetries(reflections=True))
        assert set(orbit_all) == {tuple(U(0, 0)), tuple(D(0, 0))}


class TestReflect:
    @pytest.mark.parametrize('q,r', [(0, 0), (2, -1), (-3, 4)])
    def test_plr_oracle(self, tz, q, r):
        u = U(q, r)
        fifth_edge = ((q, r), (q + 1, r))
        minor_third_edge = ((q, r + 1), (q + 1, r))
        major_third_edge = ((q, r), (q, r + 1))

        p = tz.reflect(u, edge=fifth_edge)
        l = tz.reflect(u, edge=minor_third_edge)
        r_ = tz.reflect(u, edge=major_third_edge)
        assert p == D(q, r - 1)
        assert l == D(q, r)
        assert r_ == D(q - 1, r)

        # involutions
        assert tz.reflect(p, edge=fifth_edge) == u
        assert tz.reflect(l, edge=minor_third_edge) == u
        assert tz.reflect(r_, edge=major_third_edge) == u

    def test_axis_form_matches_edge_form(self, tz):
        u = U(0, 0)
        assert tz.reflect(u, axis='3/2', through=(0, 0)) == \
            tz.reflect(u, edge=((0, 0), (1, 0)))
        assert tz.reflect(u, axis=(1, 0), through=(0, 0)) == D(0, -1)

    def test_axis_resolves_interval_directions(self, tz):
        u = U(0, 0)
        assert tz.reflect(u, axis=F(6, 5), through=(0, 1)) == \
            tz.reflect(u, edge=((0, 1), (1, 0)))

    def test_bisector_mirror(self, tz):
        # The (1,1) bisector swaps the two generator axes.
        assert tz.reflect(Shape([(1, 0)]), axis=(1, 1)) == Shape([(0, 1)])

    def test_non_mirror_direction_rejected(self, tz):
        with pytest.raises(ValueError, match='mirror direction'):
            tz.reflect(U(0, 0), edge=((0, 0), (2, 1)))

    def test_exactly_one_of_edge_or_axis(self, tz):
        with pytest.raises(ValueError):
            tz.reflect(U(0, 0))
        with pytest.raises(ValueError):
            tz.reflect(U(0, 0), edge=((0, 0), (1, 0)), axis=(1, 0))


class TestRotate:
    def test_identity_periods(self, tz):
        u = U(0, 0)
        assert tz.rotate(u, 6) == u
        assert tz.rotate(u, 0) == u
        assert tz.rotate(tz.rotate(u, 2), -2) == u

    def test_sixty_degrees_flips_orientation(self, tz):
        rotated = tz.rotate(U(0, 0), 1)
        assert rotated == Shape([(0, 0), (0, 1), (-1, 1)])

    def test_about_fixed_vertex(self, tz):
        u = U(2, -1)
        rotated = tz.rotate(u, 3, about=(2, -1))
        assert (2, -1) in rotated


class TestLabels:
    def test_major_triad_ratios(self, tz):
        chord = tz.chord(U(0, 0))
        assert {F(d) for d in chord.degrees} == {F(1), F(5, 4), F(3, 2)}

    def test_l_of_major_is_relative_leittonwechsel_minor(self, tz):
        l = tz.reflect(U(0, 0), edge=((0, 1), (1, 0)))
        chord = tz.chord(l)
        assert {F(d) for d in chord.degrees} == {F(5, 4), F(3, 2), F(15, 8)}

    def test_shape_and_list_equivalent(self, tz):
        assert list(tz.chord(U(0, 0)).degrees) == \
            list(tz.chord(list(U(0, 0))).degrees)

    def test_shape_sequence_yields_chord_sequence(self, tz):
        seq = tz.chord([U(0, 0), D(0, 0)])
        assert len(seq.chords) == 2

    def test_creep_moves(self):
        # Creep (in G): G - B - C - Cm as shape operations from U(0,0),
        # heard against a G reference: I -> III (two flips) -> IV (slide)
        # -> iv (flip over the slid fifth edge).
        tz = Tonnetz(resolution=6).root('G3')
        g = U(0, 0)
        bm = tz.reflect(g, edge=((0, 1), (1, 0)))    # L: B minor
        b = tz.reflect(bm, edge=((0, 1), (1, 1)))    # P: flip over ITS fifth edge
        assert b == U(0, 1)
        c = translate(g, (-1, 0))
        cm = tz.reflect(c, edge=((-1, 0), (0, 0)))
        assert cm == D(-1, -1)
        roots = [tz.get_ratio(x) for x in [(0, 0), (0, 1), (-1, 0), (-1, 0)]]
        assert roots[:3] == [F(1), F(5, 4), F(2, 3)]
        # the G vertex (0,0) is shared by I, IV, and iv exactly
        assert (0, 0) in g and (0, 0) in c and (0, 0) in cm

    def test_syntonic_comma_pump(self, tz):
        # I - vi - ii - V - I: each move exact, the returning tonic root
        # lands one syntonic comma flat (80/81 against the original 1/1).
        c = U(0, 0)
        am = tz.reflect(c, edge=((0, 0), (0, 1)))               # R
        assert am == D(-1, 0)
        dm = translate(am, (-1, 0))                             # down a fifth
        g = tz.reflect(translate(dm, (-1, 1)),
                       edge=((-3, 2), (-2, 1)))                 # slide + L-flip
        assert g == U(-3, 1)
        c2 = translate(g, (-1, 0))                              # V -> I
        assert c2 == U(-4, 1)
        assert tz.get_ratio((-4, 1)) == F(80, 81)


class TestSquareGroupStillDefault:
    def test_rotations_group_param_matches_default(self):
        from klotho.topos.graphs.lattices.lattices import Lattice
        lat = Lattice(dimensionality=2, resolution=2)
        piece = Shape([(0, 0), (1, 0), (2, 0), (2, 1)])
        assert rotations(piece, group=lat.symmetries()) == rotations(piece)
        assert rotations(piece, group=lat.symmetries(reflections=True)) == \
            rotations(piece, reflections=True)

    def test_lattice_symmetries_sizes(self):
        from klotho.topos.graphs.lattices.lattices import Lattice
        lat2 = Lattice(dimensionality=2, resolution=1)
        assert len(lat2.symmetries()) == 4
        assert len(lat2.symmetries(reflections=True)) == 8
        lat3 = Lattice(dimensionality=3, resolution=1)
        assert len(lat3.symmetries()) == 24
        assert len(lat3.symmetries(reflections=True)) == 48


class TestFlip:
    def test_letters_match_reflect_oracle(self, tz):
        g = U(0, 0)
        assert tz.flip(g, 'P') == D(0, -1)
        assert tz.flip(g, 'R') == D(-1, 0)
        assert tz.flip(g, 'L') == D(0, 0)

    def test_axis_forms_equivalent(self, tz):
        g = U(2, -1)
        assert tz.flip(g, (1, 0)) == tz.flip(g, 'P') == tz.flip(g, '3/2')

    @pytest.mark.parametrize('move', ['P', 'R', 'L', 'S'])
    def test_involutions_both_orientations(self, tz, move):
        for t in (U(0, 0), D(2, 1)):
            assert tz.flip(tz.flip(t, move), move) == t

    def test_slide_holds_the_third(self, tz):
        # From major: C -> C#m territory; holds the third vertex exactly,
        # root moves up a chromatic semitone (25/24).
        g = U(0, 0)
        s = tz.flip(g, 'S')
        assert s == D(-1, 1)
        assert set(g) & set(s) == {(0, 1)}
        ratios = {F(str(d)) for d in tz.chord(s).degrees}
        assert F(5, 4) in ratios and F(25, 24) in ratios
        # From minor: Cm -> B territory; root down a chromatic semitone.
        gm = tz.flip(g, 'P')
        b = tz.flip(gm, 'S')
        assert b == U(1, -2)
        assert set(gm) & set(b) == {(1, -1)}
        assert tz.get_ratio(min(b)) == F(24, 25)

    def test_ambiguous_and_missing_edges_rejected(self, tz):
        square = Shape([(0, 0), (1, 0), (0, 1), (1, 1)])
        with pytest.raises(ValueError, match='parallel edges'):
            tz.flip(square, 'P')
        line = Shape([(-2, 0), (-1, 0), (0, 0)])
        with pytest.raises(ValueError, match='no edge'):
            tz.flip(line, 'R')
        with pytest.raises(ValueError):
            tz.flip(square, 'S')   # slide is triangles-only


class TestPerform:
    def test_history_matches_manual_folding(self, tz):
        g = U(0, 0)
        hist = tz.perform(g, ['R', 'P', (0, 1), 'S'])
        assert len(hist) == 5
        assert hist[0] == g
        assert hist[1] == tz.flip(g, 'R')
        assert hist[2] == tz.flip(hist[1], 'P')
        assert hist[3] == translate(hist[2], (0, 1))
        assert hist[4] == tz.flip(hist[3], 'S')

    def test_returns_shapes(self, tz):
        for s in tz.perform(U(0, 0), ['P', (1, 0)]):
            assert isinstance(s, Shape)


class TestShapeColor:
    def _groups(self):
        up = U(0, 0)
        return up, translate(up, (2, -1)), D(0, 0)

    def test_fixed_mode_translations_share_rotations_differ(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _shape_group_colors
        up, up_moved, down = self._groups()
        c = _shape_group_colors([up, up_moved, down], 'fixed')
        assert c[0] == c[1] != c[2]

    def test_one_sided_mode_matches_shape_color(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _shape_group_colors
        up, up_moved, down = self._groups()
        c = _shape_group_colors([up, up_moved, down], 'one-sided')
        assert c[0] == c[1] == c[2]           # U == D under a 180-degree turn
        assert c[0] == Shape(up).color

    def test_default_mode_unchanged(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _shape_group_colors
        up, _, down = self._groups()
        assert _shape_group_colors([list(up), list(down)], None) is None
        c = _shape_group_colors([up, down], None)
        assert c == [up.color, down.color]

    def test_single_group_not_split(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _shape_group_colors
        assert len(_shape_group_colors(list(U(0, 0)), 'fixed')) == 1

    def test_invalid_mode_rejected(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _shape_group_colors
        with pytest.raises(ValueError):
            _shape_group_colors([U(0, 0)], 'sideways')

    def test_shape_color_reaches_figure(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tz = Tonnetz(resolution=3)
        up, up_moved, down = self._groups()
        fig = _plot_lattice(tz, figsize=(4, 4), shape=[up, up_moved, down],
                            shape_color='fixed')
        assert fig.shape_colors[0] == fig.shape_colors[1] != fig.shape_colors[2]

    def test_tonnetz_defaults_to_fixed(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tz = Tonnetz(resolution=3)
        fig = _plot_lattice(tz, figsize=(4, 4), shape=[U(0, 0), D(0, 0)])
        assert fig.shape_colors[0] != fig.shape_colors[1]

    def test_tone_lattice_default_unchanged(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tl = ToneLattice.from_generators((3, 5), resolution=3)
        fig = _plot_lattice(tl, figsize=(4, 4), shape=[U(0, 0), D(0, 0)])
        # legacy: Shape.color (one-sided identity) -- U and D share
        assert fig.shape_colors[0] == fig.shape_colors[1]


class TestTrailEdges:
    def test_trail_js_persists_edges_2d(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        from klotho.semeios.visualization._animation.animated import _AnimatedShapeFigureBase
        tz = Tonnetz(resolution=3)
        fig = _plot_lattice(tz, figsize=(4, 4), shape=[U(0, 0), D(0, 0)])
        html = _AnimatedShapeFigureBase(fig, dur=0.5, trail=True).to_html()
        start = html.index('function renderTrail')
        end = html.index('function ', start + 1)
        trail_src = html[start:end]
        assert 'groupEdgeIds[gi]' in trail_src
        assert 'style.opacity' in trail_src
        reveal_src = html[html.index('function revealGroupVisual'):][:900]
        assert 'style.opacity = ""' in reveal_src

    def test_trail_js_persists_edges_3d(self):
        import inspect
        from klotho.semeios.visualization._animation.animated import (
            AnimatedLattice3dShapeFigure)
        src = inspect.getsource(AnimatedLattice3dShapeFigure._controller_js)
        trail_src = src.split('function renderTrail')[1].split("'''")[0]
        assert 'shapeEdgeObjs[gi]' in trail_src
        assert 'klBaseOpacity' in trail_src


class TestPlot:
    def test_tonnetz_layout_default(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        import re
        tz = Tonnetz(resolution=2)
        fig = _plot_lattice(tz, figsize=(5, 5))
        svg = fig.svg_str
        n_nodes = len(re.findall(r'<circle ', svg))
        n_edges = len(re.findall(r'<line ', svg))
        assert n_nodes == 25
        # triangular grid: 4*5 + 5*4 + 16 diagonals
        assert n_edges == 4 * 5 + 5 * 4 + 16
        assert 'Ratio: 3/2' in svg

    def test_shape_and_path_render(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tz = Tonnetz(resolution=3)
        fig = _plot_lattice(tz, figsize=(5, 5), shape=list(U(0, 0)))
        assert len(fig.shape_group_node_indices) == 1
        assert all(i >= 0 for i in fig.shape_group_node_indices[0])
        fig2 = _plot_lattice(tz, figsize=(5, 5),
                             path=[(0, 0), (1, 0), (1, -1)])
        assert all(i >= 0 for i in fig2.path_node_indices)

    def test_explicit_layouts_still_work(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tz = Tonnetz(resolution=2)
        _plot_lattice(tz, figsize=(4, 4), layout='lattice')
        with pytest.raises(ValueError):
            _plot_lattice(ToneLattice.from_generators((3, 5, 7), resolution=1),
                          layout='tonnetz')
