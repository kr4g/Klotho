"""Coverage for the autoref rotation-matrix family.

This family had ZERO test coverage before 10.18 (charter NEW-07), which is
how mode 'C' could sit dead for four months while both the docstring and the
error message advertised it (WL-28).

The expected matrices below are transcribed from Karim Haddad, *L'Unite
Temporelle : Une approche pour l'ecriture de la duree et de sa
quantification* ("The Temporal Unit: An approach to the writing of duration
and its quantification"), doctoral thesis, Sorbonne Universite, 2020, HAL
tel-03258984; section 2.3.8, "Les modes de rotation sur un rythme
autoreferentiel" ("Rotation modes on a self-referential rhythm"), figures
2.22-2.25, for the proportions (3 4 5 7). They are NOT captured from Klotho's
own output, so they are a real oracle rather than a snapshot of whatever the
code does.

Two citation corrections, made 2026-08-29 (chunk HAD-RT):

* The title *Vers une temporalite musicale repensee* ("Toward a Rethought
  Musical Temporality"), used here before, names a work that does not exist;
  the phrase appears nowhere in the document. See
  ``projects/klotho-evolution/evidence/haddad-sources/README.md``.
* The 2020 thesis was called "the PRIMARY SOURCE" for this material. It is
  the late synthesis, not the primary source: Haddad's 2008 chapter in *The
  OM Composer's Book 2* states the same construction twelve years earlier and
  its Figure 27 uses the very same (3 4 5 7) proportions for the same
  purpose. The thesis is still the source the matrices below are transcribed
  from; it is simply not the earliest one.
"""

import pytest

from klotho.topos.collections.patterns import (
    autoref,
    autoref_rotmat,
    autoref_rotmat_all,
    permute_list,
)


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


class TestTheFifthProcess:
    """RT-8 -- ``autoref_rotmat_all``, Haddad's figure 2.26.

    Section 2.3.8 opens by counting the operations: "Nous avons releve cinq
    processus possibles de l'autoreferencement associe a la rotation" -- "We
    have identified five possible processes of self-referencing associated
    with rotation." Four are the G/S/D/C modes. The fifth is section
    2.3.8.5, "Matrice autoreferentielle" ("Self-referential matrix"): "Tout
    ces modes donnent lieu a une matrice de toutes les transformations
    possibles" -- "All these modes give rise to a matrix of all the possible
    transformations." Figure 2.26 is titled "Matrice de toutes les
    permutations" -- "Matrix of all the permutations."

    Figure 2.26 is engraving-only: unlike figures 2.18-2.25 it prints no
    s-expression, and ``pdftotext`` returns noise for the page. So the row
    ORDER is not transcribed from it -- reading durations off rotated,
    dense notation is the mistake that let mode 'C' sit wrong for months.
    It is settled mechanically instead, by asking which convention puts
    each already-verified mode's matrix on the rows it predicts. See
    ``projects/klotho-evolution/evidence/haddad-fig-2.26/README.md``, which
    prescribes exactly this check.
    """

    def test_it_returns_n_squared_rows(self):
        for lst in ((3, 4), (3, 4, 5), LST, (3, 4, 5, 7, 11)):
            assert len(autoref_rotmat_all(lst)) == len(lst) ** 2

    def test_figure_2_26_has_sixteen_rows_for_these_proportions(self):
        """The render shows rows explicitly numbered 0-15 for (3 4 5 7)."""
        assert len(autoref_rotmat_all(LST)) == 16

    def test_every_row_is_a_full_autoref_row(self):
        for row in autoref_rotmat_all(LST):
            assert len(row) == len(LST)
            assert all(isinstance(D, int) and len(S) == len(LST) for D, S in row)

    def test_row_zero_is_plain_autoref(self):
        assert autoref_rotmat_all(LST)[0] == autoref(LST)

    def test_every_row_is_distinct(self):
        assert len(set(autoref_rotmat_all(LST))) == 16

    # ---- the convention: k = 4p + q, row-major, p = head offset ----

    def test_mode_s_lies_on_rows_zero_to_three(self):
        """S is p = 0: heads fixed, tails shearing. Under row-major that is
        the first n rows. This and mode D are the discriminating pair."""
        rows = autoref_rotmat_all(LST)
        assert tuple(rows[q] for q in range(4)) == THESIS['S']

    def test_mode_d_lies_on_rows_zero_four_eight_twelve(self):
        """D is q = 0: tail table frozen, heads rotating. Under row-major
        that is every fourth row."""
        rows = autoref_rotmat_all(LST)
        assert tuple(rows[4 * p] for p in range(4)) == THESIS['D']

    def test_the_transposed_convention_is_refuted(self):
        """Under k = 4q + p, S and D swap. They do not. G is symmetric under
        transposition and proves nothing, which is why it is not used here."""
        rows = autoref_rotmat_all(LST)
        assert tuple(rows[4 * p] for p in range(4)) != THESIS['S']
        assert tuple(rows[q] for q in range(4)) != THESIS['D']

    def test_mode_g_lies_on_the_diagonal(self):
        rows = autoref_rotmat_all(LST)
        assert tuple(rows[5 * p] for p in range(4)) == THESIS['G']

    def test_mode_c_lies_on_q_equals_twice_p(self):
        rows = autoref_rotmat_all(LST)
        assert tuple(rows[4 * p + (2 * p) % 4] for p in range(4)) == THESIS['C']

    def test_the_four_mode_lines_are_exactly_the_named_modes(self):
        """Haddad's structural claim, made true in the code: each named mode
        is a line through one n-squared family."""
        n = len(LST)
        rows = autoref_rotmat_all(LST)
        lines = {
            'G': [(p, p) for p in range(n)],
            'S': [(0, q) for q in range(n)],
            'D': [(p, 0) for p in range(n)],
            'C': [(p, 2 * p) for p in range(n)],
        }
        for mode, pairs in lines.items():
            assert tuple(rows[n * p + q % n] for p, q in pairs) == autoref_rotmat(
                LST, mode=mode
            )

    def test_the_mode_lines_hold_at_n_equals_five(self):
        """n=4 cannot separate 2p from row parity; n=5 can."""
        lst = (3, 4, 5, 7, 11)
        n = 5
        rows = autoref_rotmat_all(lst)
        for mode, pairs in {
            'G': [(p, p) for p in range(n)],
            'S': [(0, q) for q in range(n)],
            'D': [(p, 0) for p in range(n)],
            'C': [(p, 2 * p) for p in range(n)],
        }.items():
            assert tuple(rows[n * p + q % n] for p, q in pairs) == autoref_rotmat(
                lst, mode=mode
            )

    # ---- argument handling is shared with the four-mode function ----

    def test_one_arg_and_two_identical_args_agree(self):
        assert autoref_rotmat_all(LST) == autoref_rotmat_all(LST, LST)

    def test_unequal_lengths_raise(self):
        with pytest.raises(ValueError, match='equal length'):
            autoref_rotmat_all((1, 2, 3), (1, 2))

    def test_three_args_raise(self):
        with pytest.raises(ValueError, match='one or two'):
            autoref_rotmat_all(LST, LST, LST)

    def test_a_mode_string_is_rejected(self):
        with pytest.raises(ValueError, match='number'):
            autoref_rotmat_all(LST, 'GSDC')


class TestTheRefactorIsByteIdentical:
    """The four mode arms are now lines through one row builder. These
    reference implementations are the arms as they stood before, transcribed
    verbatim; any drift in output is a regression, not a redesign.
    """

    @staticmethod
    def _old(lst1, lst2, mode, ps):
        n = len(lst1)
        if mode == 'G':
            return tuple(autoref(permute_list(lst1, i, ps), permute_list(lst2, i, ps),
                                 preserve_signs=ps) for i in range(n))
        if mode == 'S':
            return tuple(tuple((lst1[j], permute_list(lst2, i + j + 1, ps))
                               for j in range(n)) for i in range(n))
        if mode == 'D':
            return tuple(tuple((elem, autoref(lst2, preserve_signs=ps)[j][1])
                               for j, elem in enumerate(permute_list(lst1, i, ps)))
                         for i in range(n))
        return tuple(tuple((elem, autoref(permute_list(lst2, 2 * i, ps),
                                          preserve_signs=ps)[j][1])
                           for j, elem in enumerate(permute_list(lst1, i, ps)))
                     for i in range(n))

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    @pytest.mark.parametrize('lst', [(3, 4, 5, 7), (3, 4, 5), (3, 4, 5, 7, 11), (2, 3)])
    def test_unsigned_output_is_unchanged(self, mode, lst):
        assert autoref_rotmat(lst, mode=mode) == self._old(lst, lst, mode, False)

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    @pytest.mark.parametrize('lst', [(3, -4, 5, -7), (3, -4, 5, -7, 11), (-1, 2, -3)])
    def test_signed_output_is_unchanged(self, mode, lst):
        """preserve_signs pins each sign to a POSITION, so it survives being
        applied twice -- but the S arm composed two rotations where the old
        code did one, so this is pinned rather than assumed."""
        assert autoref_rotmat(lst, mode=mode, preserve_signs=True) == self._old(
            lst, lst, mode, True
        )

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_the_two_list_extension_is_unchanged(self, mode):
        lst1, lst2 = (3, 4, 5, 7), (10, 20, 30, 40)
        assert autoref_rotmat(lst1, lst2, mode=mode) == self._old(lst1, lst2, mode, False)


class TestPreserveSigns:
    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_preserve_signs_keeps_sign_pattern_fixed(self, mode):
        signed = (3, -4, 5, -7)
        mat = autoref_rotmat(signed, mode=mode, preserve_signs=True)
        heads = [elem for row in mat for elem, _ in row]
        # signs stay pinned to position, magnitudes rotate
        assert all(abs(h) in {3, 4, 5, 7} for h in heads)
        assert any(h < 0 for h in heads)
