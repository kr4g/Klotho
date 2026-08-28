"""Coverage for the autoref rotation-matrix family.

This family had ZERO test coverage before 10.18 (charter NEW-07), which is
how mode 'C' could sit dead for four months while both the docstring and the
error message advertised it (WL-28).

The mode 'C' expectations here are not invented: they are the matrix written
by hand in the function's own 2024 docstring (commit 17a9996), which is an
independent oracle for the restored implementation.
"""

import pytest

from klotho.topos.collections.patterns import autoref, autoref_rotmat, permute_list


LST = (3, 4, 5, 7)


class TestModeC:
    """WL-28 — mode 'C' returned None while being advertised as valid."""

    def test_mode_c_is_not_none(self):
        assert autoref_rotmat(LST, mode='C') is not None

    def test_mode_c_matches_the_original_docstring_matrix(self):
        # verbatim from the pre-generalization docstring (commit 17a9996)
        expected = (
            ((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7))),
            ((4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3)), (3, (5, 7, 3, 4))),
            ((5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)), (3, (7, 3, 4, 5)), (4, (3, 4, 5, 7))),
            ((7, (7, 3, 4, 5)), (3, (3, 4, 5, 7)), (4, (4, 5, 7, 3)), (5, (5, 7, 3, 4))),
        )
        assert autoref_rotmat(LST, mode='C') == expected

    def test_mode_c_alternates_tail_table_by_row_parity(self):
        """The defining property of 'C' vs 'D': tails oscillate, heads sweep."""
        mat = autoref_rotmat(LST, mode='C')
        even_tails = [row[j][1] for row in mat[0::2] for j in range(len(LST))]
        odd_tails = [row[j][1] for row in mat[1::2] for j in range(len(LST))]
        # even rows all draw from autoref(lst); odd rows from the phase-2 table
        assert even_tails[:4] == [t for _, t in autoref(LST)]
        assert odd_tails[:4] == [t for _, t in autoref(permute_list(LST, 2))]
        assert even_tails[:4] != odd_tails[:4]

    def test_mode_c_is_case_insensitive(self):
        assert autoref_rotmat(LST, mode='c') == autoref_rotmat(LST, mode='C')

    def test_mode_c_differs_from_mode_d(self):
        assert autoref_rotmat(LST, mode='C') != autoref_rotmat(LST, mode='D')


class TestModeShapeParity:
    """Pin G/S/D too — nothing else in the suite touches them."""

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_every_advertised_mode_returns_a_square_matrix(self, mode):
        mat = autoref_rotmat(LST, mode=mode)
        assert mat is not None, f"mode {mode!r} is advertised but returned None"
        assert len(mat) == len(LST)
        assert all(len(row) == len(LST) for row in mat)

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_one_arg_and_two_identical_args_agree(self, mode):
        assert autoref_rotmat(LST, mode=mode) == autoref_rotmat(LST, LST, mode=mode)

    def test_invalid_mode_still_raises(self):
        with pytest.raises(ValueError, match='Invalid mode'):
            autoref_rotmat(LST, mode='X')

    def test_error_message_advertises_only_implemented_modes(self):
        """The message may not name a mode that returns None."""
        try:
            autoref_rotmat(LST, mode='X')
        except ValueError as exc:
            advertised = [m for m in ('G', 'S', 'D', 'C') if m in str(exc)]
        for mode in advertised:
            assert autoref_rotmat(LST, mode=mode) is not None

    def test_unequal_lengths_raise(self):
        with pytest.raises(ValueError, match='equal length'):
            autoref_rotmat((1, 2, 3), (1, 2), mode='C')

    def test_three_args_raise(self):
        with pytest.raises(ValueError, match='one or two'):
            autoref_rotmat(LST, LST, LST, mode='C')


class TestPreserveSigns:
    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_preserve_signs_keeps_sign_pattern_fixed(self, mode):
        signed = (3, -4, 5, -7)
        mat = autoref_rotmat(signed, mode=mode, preserve_signs=True)
        heads = [elem for row in mat for elem, _ in row]
        # signs stay pinned to position, magnitudes rotate
        assert all(abs(h) in {3, 4, 5, 7} for h in heads)
        assert any(h < 0 for h in heads)
