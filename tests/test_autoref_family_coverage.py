"""Coverage for the autoref / auto_subdiv / from_tree_mat family (NEW-07).

The family had zero tests until API-1 pinned ``autoref_rotmat`` against
Haddad's published matrices (``test_autoref_rotmat.py``). This file covers
the rest of it: the two algorithms ``autoref_rotmat`` is built from, the
matrix subdivider, and the ``TemporalBlock`` constructor that consumes them.

Two of these tests pin behaviour that is **wrong in the docstring, right in
the code's own terms** -- ``auto_subdiv_matrix`` and ``from_tree_mat`` both
advertise a row-and-column rotation and both collapse to column-only at their
default offset (charter NEW-28; the doc half lands in API-3). They are pinned
here so the doc fix has an oracle and so a future change to either formula is
loud rather than silent.
"""

import warnings

import pytest

from klotho.chronos.rhythm_trees.algorithms import auto_subdiv, auto_subdiv_matrix
from klotho.chronos.temporal_units.temporal import ProlatioTypes, TemporalBlock
from klotho.topos.collections.patterns import autoref, autoref_rotmat, permute_list


class TestPermuteList:
    """Haddad's algorithm 4."""

    def test_it_rotates_left_by_pt(self):
        assert permute_list((3, 4, 5, 7), 1) == (4, 5, 7, 3)

    def test_zero_is_the_identity(self):
        assert permute_list((3, 4, 5, 7), 0) == (3, 4, 5, 7)

    def test_a_full_turn_is_the_identity(self):
        assert permute_list((3, 4, 5, 7), 4) == (3, 4, 5, 7)

    def test_it_wraps_past_the_length(self):
        assert permute_list((3, 4, 5, 7), 5) == permute_list((3, 4, 5, 7), 1)

    def test_a_negative_offset_rotates_right(self):
        assert permute_list((3, 4, 5, 7), -1) == (7, 3, 4, 5)

    def test_signs_travel_with_the_values_by_default(self):
        assert permute_list((3, -4, 5), 1) == (-4, 5, 3)

    def test_preserve_signs_pins_the_sign_pattern_in_place(self):
        """Magnitudes rotate; the sign of each *position* does not move."""
        assert permute_list((3, -4, 5), 1, preserve_signs=True) == (4, -5, 3)


class TestAutoref:
    """Haddad's algorithm 5."""

    def test_each_head_keeps_its_element_and_gains_a_tail(self):
        assert autoref((3, 4, 5)) == (
            (3, (4, 5, 3)),
            (4, (5, 3, 4)),
            (5, (3, 4, 5)),
        )

    def test_row_n_rotates_the_tail_by_n_plus_one(self):
        lst = (3, 4, 5, 7)
        for n, (_, tail) in enumerate(autoref(lst)):
            assert tail == permute_list(lst, n + 1)

    def test_one_argument_doubles_as_both_lists(self):
        assert autoref((3, 4, 5)) == autoref((3, 4, 5), (3, 4, 5))

    def test_heads_come_from_the_first_list_and_tails_from_the_second(self):
        heads = tuple(h for h, _ in autoref((1, 2, 3), (10, 20, 30)))
        tails = tuple(t for _, t in autoref((1, 2, 3), (10, 20, 30)))
        assert heads == (1, 2, 3)
        assert all(set(t) == {10, 20, 30} for t in tails)

    def test_unequal_lengths_raise(self):
        with pytest.raises(ValueError, match="equal length"):
            autoref((1, 2), (1, 2, 3))

    def test_three_arguments_raise(self):
        with pytest.raises(ValueError, match="one or two"):
            autoref((1,), (2,), (3,))


class TestAutoSubdiv:
    def test_each_element_becomes_a_D_S_pair(self):
        assert auto_subdiv((3, 4, 5), 1) == (
            (3, (1, 1, 1, 1)),
            (4, (1, 1, 1, 1, 1)),
            (5, (1, 1, 1)),
        )

    def test_the_subdivision_count_comes_from_the_offset_neighbour(self):
        subdivs = (3, 4, 5, 7)
        for n in range(5):
            for idx, (D, S) in enumerate(auto_subdiv(subdivs, n)):
                assert D == subdivs[idx]
                assert len(S) == subdivs[(idx + n) % len(subdivs)]

    def test_offset_zero_subdivides_each_element_by_itself(self):
        assert auto_subdiv((3, 4), 0) == ((3, (1, 1, 1)), (4, (1, 1, 1, 1)))

    def test_the_offset_wraps(self):
        assert auto_subdiv((3, 4, 5), 4) == auto_subdiv((3, 4, 5), 1)

    def test_a_single_element_subdivides_by_itself_at_any_offset(self):
        assert auto_subdiv((3,), 7) == ((3, (1, 1, 1)),)

    def test_an_empty_subdivision_is_empty(self):
        assert auto_subdiv((), 1) == ()


class TestAutoSubdivMatrix:
    MAT = (autoref((3, 4, 5)),) * 3

    def test_it_preserves_the_matrix_shape_and_the_heads(self):
        out = auto_subdiv_matrix(self.MAT)
        assert len(out) == len(self.MAT)
        for row_in, row_out in zip(self.MAT, out):
            assert len(row_out) == len(row_in)
            assert tuple(D for D, _ in row_out) == tuple(D for D, _ in row_in)

    def test_the_effective_offset_is_j_minus_i_plus_rotation_offset_times_i(self):
        for rot in (0, 1, 2, 3):
            out = auto_subdiv_matrix(self.MAT, rotation_offset=rot)
            for i, row in enumerate(self.MAT):
                for j, (_, S) in enumerate(row):
                    assert out[i][j][1] == auto_subdiv(S, j - i + rot * i)

    def test_the_row_index_cancels_at_the_default_offset(self):
        """NEW-28, pinned as-is. ``j - i + 1*i == j``, so identical input rows
        produce identical output rows and the docstring's promise of
        row-and-column variation is false *at the default*. The docstring
        fix is API-3's; the behaviour is deliberately unchanged here."""
        out = auto_subdiv_matrix(self.MAT)
        assert out[0] == out[1] == out[2]

    def test_a_non_default_offset_does_vary_by_row(self):
        out = auto_subdiv_matrix(self.MAT, rotation_offset=2)
        assert out[0] != out[1]


class TestFromTreeMat:
    MAT = autoref_rotmat((3, 4, 5))

    @staticmethod
    def _build(**kw):
        kw.setdefault('sort_rows', False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return TemporalBlock.from_tree_mat(TestFromTreeMat.MAT, **kw)

    def test_the_block_mirrors_the_matrix_shape(self):
        blk = self._build()
        assert blk.height == len(self.MAT)
        assert [len(row) for row in blk.rows] == [len(r) for r in self.MAT]

    def test_each_unit_takes_its_prolatio_from_the_pair(self):
        blk = self._build()
        for row_in, row_out in zip(self.MAT, blk.rows):
            for (D, S), unit in zip(row_in, row_out):
                assert unit.prolationis == S
                assert unit.tempus.numerator == abs(D)

    def test_meas_denom_sets_the_measure_denominator(self):
        blk = self._build(meas_denom=4)
        assert blk.rows[0][0].tempus.denominator == 4

    def test_a_negative_D_becomes_a_rest(self):
        neg = tuple(tuple((-D, S) for D, S in row) for row in self.MAT)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blk = TemporalBlock.from_tree_mat(neg, sort_rows=False)
        assert blk.rows[0][0].type is ProlatioTypes.REST

    def test_subdiv_replaces_each_S_with_an_auto_subdivision(self):
        plain = self._build()
        sub = self._build(subdiv=True)
        assert plain.rows[0][0].prolationis != sub.rows[0][0].prolationis
        assert blk_shape(plain) == blk_shape(sub)

    def test_the_subdiv_offset_is_rotation_offset_times_i_minus_j_minus_i(self):
        """The formula differs from :func:`auto_subdiv_matrix`'s -- it also
        reverses S. Pinned because the two are easy to assume identical."""
        for rot in (1, 2):
            blk = self._build(subdiv=True, rotation_offset=rot)
            for i, row in enumerate(self.MAT):
                for j, (_, S) in enumerate(row):
                    expected = auto_subdiv(S[::-1], rot * i - j - i)
                    assert blk.rows[i][j].prolationis == expected

    def test_the_row_index_cancels_at_the_default_offset(self):
        """The same NEW-28 class as ``auto_subdiv_matrix``, by a different
        formula: ``1*i - j - i == -j``. Identical input rows give identical
        subdivisions. Pinned, not fixed."""
        same = (self.MAT[0],) * 3
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            blk = TemporalBlock.from_tree_mat(same, subdiv=True, sort_rows=False)
        pro = [[u.prolationis for u in row] for row in blk.rows]
        assert pro[0] == pro[1] == pro[2]


def blk_shape(blk):
    return [len(row) for row in blk.rows]
