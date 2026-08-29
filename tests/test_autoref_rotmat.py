"""Coverage for the autoref rotation-matrix family.

This family had ZERO test coverage before 10.18 (charter NEW-07), which is
how mode 'C' could sit dead for four months while both the docstring and the
error message advertised it (WL-28).

The expected matrices below are transcribed from the PRIMARY SOURCE: Karim
Haddad, *Vers une temporalite musicale repensee* ("Toward a Rethought
Musical Temporality", 2020), section 2.3.8, "Les modes de rotation sur un
rythme autoreferentiel" ("Rotation modes on a self-referential rhythm"),
figures 2.22-2.25, for the proportions (3 4 5 7). They are NOT captured from Klotho's own output, so
they are a real oracle rather than a snapshot of whatever the code does.
"""

import pytest

from klotho.topos.collections.patterns import autoref, autoref_rotmat, permute_list


LST = (3, 4, 5, 7)


THESIS = {
    # Figure 2.22 -- "La rotation en mode Group" (rotation in Group mode)
    'G': (((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7))),
          ((4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)), (3, (4, 5, 7, 3))),
          ((5, (7, 3, 4, 5)), (7, (3, 4, 5, 7)), (3, (4, 5, 7, 3)), (4, (5, 7, 3, 4))),
          ((7, (3, 4, 5, 7)), (3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)))),
    # Figure 2.23 -- "La rotation en mode S" (rotation in S mode: D fixed, S rotates)
    'S': (((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7))),
          ((3, (5, 7, 3, 4)), (4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3))),
          ((3, (7, 3, 4, 5)), (4, (3, 4, 5, 7)), (5, (4, 5, 7, 3)), (7, (5, 7, 3, 4))),
          ((3, (3, 4, 5, 7)), (4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)), (7, (7, 3, 4, 5)))),
    # Figure 2.24 -- "La rotation en mode D" (rotation in D mode: S fixed, D rotates)
    'D': (((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7))),
          ((4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)), (7, (7, 3, 4, 5)), (3, (3, 4, 5, 7))),
          ((5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)), (3, (7, 3, 4, 5)), (4, (3, 4, 5, 7))),
          ((7, (4, 5, 7, 3)), (3, (5, 7, 3, 4)), (4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)))),
    # Figure 2.25 -- "La rotation en mode circulaire" (rotation in circular mode)
    'C': (((3, (4, 5, 7, 3)), (4, (5, 7, 3, 4)), (5, (7, 3, 4, 5)), (7, (3, 4, 5, 7))),
          ((4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3)), (3, (5, 7, 3, 4))),
          ((5, (4, 5, 7, 3)), (7, (5, 7, 3, 4)), (3, (7, 3, 4, 5)), (4, (3, 4, 5, 7))),
          ((7, (7, 3, 4, 5)), (3, (3, 4, 5, 7)), (4, (4, 5, 7, 3)), (5, (5, 7, 3, 4)))),
}


class TestAgainstTheThesis:
    """Every implemented mode must reproduce Haddad's own published matrix."""

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_mode_matches_the_published_matrix(self, mode):
        assert autoref_rotmat(LST, mode=mode) == THESIS[mode]


class TestModeC:
    """WL-28 — mode 'C' returned None while being advertised as valid."""

    def test_mode_c_is_not_none(self):
        assert autoref_rotmat(LST, mode='C') is not None

    def test_mode_c_is_case_insensitive(self):
        assert autoref_rotmat(LST, mode='c') == autoref_rotmat(LST, mode='C')

    def test_mode_c_differs_from_mode_d(self):
        assert autoref_rotmat(LST, mode='C') != autoref_rotmat(LST, mode='D')

    def test_heads_advance_once_per_row_tails_twice(self):
        """The thesis rule: circular rotation of D, circular permutation of S.

        Pinned at n=5, where it distinguishes the real rule from the n=4
        coincidence -- alternating tails by row parity reproduces the
        published n=4 matrix too, but oscillates instead of permuting.
        """
        lst = (3, 4, 5, 7, 11)
        mat = autoref_rotmat(lst, mode='C')
        base = [t for _, t in autoref(lst)]
        advance = []
        for row in mat:
            tails = [t for _, t in row]
            advance.append(next(k for k in range(len(lst))
                                if tails == base[k:] + base[:k]))
        assert advance == [0, 2, 4, 1, 3]

    def test_heads_advance_by_one_per_row(self):
        lst = (3, 4, 5, 7, 11)
        heads = [row[0][0] for row in autoref_rotmat(lst, mode='C')]
        assert heads == list(lst)


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
