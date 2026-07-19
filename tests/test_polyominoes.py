"""Polyomino/polycube generation and placement helpers (klotho.topos.shapes).

Count anchors come from the standard enumerations: 2D n=4 gives 19 fixed /
7 one-sided (Tetris) / 5 free tetrominoes; 3D n=4 gives 8 one-sided
(OEIS A000162) / 7 free (A038119) tetracubes.
"""
import pytest

from klotho.tonos import ToneLattice
from klotho.topos.shapes import (
    Shape, polyominoes, normalize, translate, rotations,
    center, fits, placements, overlap, contact,
)


class TestEnumeration:

    @pytest.mark.parametrize("kind,expected", [
        ('fixed', [1, 2, 6, 19]),
        ('one-sided', [1, 1, 2, 7]),
        ('free', [1, 1, 2, 5]),
    ])
    def test_2d_counts(self, kind, expected):
        assert [len(polyominoes(n, 2, kind)) for n in (1, 2, 3, 4)] == expected

    @pytest.mark.parametrize("kind,expected", [
        ('one-sided', [1, 1, 2, 8]),
        ('free', [1, 1, 2, 7]),
    ])
    def test_3d_counts(self, kind, expected):
        assert [len(polyominoes(n, 3, kind)) for n in (1, 2, 3, 4)] == expected

    def test_game_piece_sets(self):
        # the "Tetris-valid" sets: one-sided = rotations only, mirrors distinct
        assert len(polyominoes(4, 2)) == 7    # classic Tetris tetrominoes
        assert len(polyominoes(4, 3)) == 8    # Blockout tetracubes (A000162)
        assert len(polyominoes(5, 3)) == 29   # Blockout extended pentacubes
        # total distinct rotation forms of the tetracube set
        assert sum(len(rotations(p)) for p in polyominoes(4, 3)) == 86

    def test_shapes_are_normalized_and_sorted(self):
        for shape in polyominoes(4):
            assert shape == normalize(shape)
        assert polyominoes(4) == sorted(polyominoes(4))

    def test_deterministic(self):
        assert polyominoes(4) == polyominoes(4)
        assert polyominoes(4, 3) == polyominoes(4, 3)

    def test_invalid_args(self):
        with pytest.raises(ValueError):
            polyominoes(0)
        with pytest.raises(ValueError):
            polyominoes(4, 0)
        with pytest.raises(ValueError):
            polyominoes(4, kind='chiral')


class TestOrientations:

    def test_rotation_counts(self):
        counts = sorted(len(rotations(p)) for p in polyominoes(4))
        # O=1, I=2, S=2, Z=2, T=4, J=4, L=4
        assert counts == [1, 2, 2, 2, 4, 4, 4]

    def test_reflections_unite_chiral_pairs(self):
        shapes = polyominoes(4)
        s_like = [p for p in shapes if len(rotations(p)) == 2 and p != normalize([(0, i) for i in range(4)])]
        assert len(s_like) == 2  # S and Z
        a, b = s_like
        assert b in rotations(a, reflections=True)
        assert b not in rotations(a)

    def test_3d_rotation_group_size(self):
        # a fully asymmetric tetracube placement can have up to 24 orientations
        assert all(len(rotations(p)) <= 24 for p in polyominoes(4, 3))


class TestTransforms:

    def test_center(self):
        o_piece = ((0, 0), (0, 1), (1, 0), (1, 1))
        centered = center(translate(o_piece, (5, -7)))
        assert centered == ((0, 0), (0, 1), (1, 0), (1, 1)) or all(
            -1 <= c[i] <= 1 for c in centered for i in range(2))
        i_piece = normalize([(0, k) for k in range(4)])
        ci = center(i_piece)
        assert min(c[1] for c in ci) == -1 and max(c[1] for c in ci) == 2
        assert isinstance(ci, Shape)

    def test_normalize_translate_roundtrip(self):
        shape = ((0, 0), (0, 1), (1, 1), (1, 2))
        moved = translate(shape, (-3, 2))
        assert normalize(moved) == shape
        assert moved == tuple(sorted((c[0] - 3, c[1] + 2) for c in shape))

    def test_overlap(self):
        a = ((0, 0), (0, 1), (1, 0), (1, 1))
        b = translate(a, (1, 0))
        assert overlap(a, a) == 4
        assert overlap(a, b) == 2
        assert overlap(a, translate(a, (5, 5))) == 0

    def test_contact(self):
        a = ((0, 0), (0, 1), (1, 0), (1, 1))     # O at origin
        b = translate(a, (2, 0))                  # O touching along one edge
        assert overlap(a, b) == 0
        assert contact(a, b) == 2
        assert contact(a, translate(a, (5, 5))) == 0
        # shared cells are not contacts
        assert contact(a, a) == 0


class TestShapeIdentity:

    def test_functions_return_shapes(self):
        assert all(isinstance(p, Shape) for p in polyominoes(4))
        piece = polyominoes(4)[2]
        assert isinstance(translate(piece, (1, 1)), Shape)
        assert all(isinstance(r, Shape) for r in rotations(piece))
        assert all(isinstance(p, Shape) for p in
                   placements(piece, ToneLattice.from_generators((3, 5), resolution=2)))

    def test_color_invariant_under_rotation_and_translation(self):
        for piece in polyominoes(4):
            expected = piece.color
            for rot in rotations(piece):
                assert rot.color == expected
                assert translate(rot, (5, -3)).color == expected

    def test_colors_distinct_within_piece_set(self):
        assert len({p.color for p in polyominoes(4)}) == 7
        assert len({p.color for p in polyominoes(4, 3)}) == 8
        assert len({p.color for p in polyominoes(5)}) == 18

    def test_mirror_pieces_have_distinct_colors(self):
        s = Shape([(0, 0), (1, 0), (1, 1), (2, 1)])
        z = Shape([(0, 1), (1, 1), (1, 0), (2, 0)])
        assert s.color != z.color

    def test_plain_tuple_equality_preserved(self):
        assert polyominoes(4)[0] == ((0, 0), (0, 1), (0, 2), (0, 3))

    def test_arbitrary_group_gets_fallback_color(self):
        weird = Shape([(0, 0), (5, 5)])
        assert weird.color.startswith('#') and len(weird.color) == 7


class TestLatticePlacement:

    @pytest.fixture
    def board(self):
        return ToneLattice.from_generators((3, 5), resolution=3)

    def test_fits(self, board):
        o_piece = ((0, 0), (0, 1), (1, 0), (1, 1))
        assert fits(o_piece, board)
        assert not fits(translate(o_piece, (3, 3)), board)

    def test_placements_i_piece(self, board):
        i_piece = normalize([(0, i) for i in range(4)])
        opts = placements(i_piece, board)
        # 2 orientations x (4 x 7) in-bounds translations on the 7x7 board
        assert len(opts) == 56
        assert all(fits(p, board) for p in opts)

    def test_placements_dimension_mismatch(self, board):
        with pytest.raises(ValueError):
            placements(((0, 0, 0), (0, 0, 1)), board)

    def test_placements_3d(self):
        board3 = ToneLattice.from_generators((3, 5, 7), resolution=2)
        piece = polyominoes(4, 3)[0]
        opts = placements(piece, board3)
        assert opts
        assert all(fits(p, board3) for p in opts)
