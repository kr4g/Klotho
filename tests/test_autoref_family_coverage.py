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
from klotho.topos.collections.patterns import (
    autoref,
    autoref_rotmat,
    pair_adjacent,
    permute_list,
    substitute,
)


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


class TestIteratedAutoreference:
    """RT-6 -- ``autoref(..., depth=n)``, Haddad's figures 2.17-2.20.

    Section 2.3.7, "De l'autoreference" ("On self-reference"), states the
    rule in prose: "Il s'agit de substituer en subdivisant tout le rythme par
    lui-meme en operant une rotation circulaire a chaque iteration" -- "It
    consists of substituting by subdividing the whole rhythm by itself,
    performing a circular rotation at each iteration."

    The expected values below are TRANSCRIBED from the thesis's own printed
    OpenMusic s-expressions, which sit as machine-readable text above each
    engraving (recovered with ``pdftotext``; see
    ``projects/klotho-evolution/evidence/haddad-fig-2.19-2.20/``). They are
    a real oracle, not a snapshot of Klotho's output.
    """

    # Figure 2.17, "Mesure initiale" ("Initial measure"): (? (((4 4) ((4 (2 3))))))
    # He calls it "la graine" -- "the seed".
    SEED = (2, 3)

    # Figure 2.18, "Premiere iteration" ("First iteration"):
    #   (((4 4) ((2 (3 2)) (3 (2 3)))))
    ITER_1 = ((2, (3, 2)), (3, (2, 3)))

    # Figure 2.19, "Deuxieme iteration" ("Second iteration"):
    #   (((4 4) ((2 ((3 (2 3)) (2 (3 2)))) (3 ((2 (3 2)) (3 (2 3)))))))
    ITER_2 = (
        (2, ((3, (2, 3)), (2, (3, 2)))),
        (3, ((2, (3, 2)), (3, (2, 3)))),
    )

    # Figure 2.20, "Troisieme iteration" ("Third iteration"):
    #   (((4 4) ((2 ((3 ((2 (3 2)) (3 (2 3)))) (2 ((3 (2 3)) (2 (3 2))))))
    #            (3 ((2 ((3 (2 3)) (2 (3 2)))) (3 ((2 (3 2)) (3 (2 3)))))))))
    ITER_3 = (
        (2, ((3, ((2, (3, 2)), (3, (2, 3)))),
             (2, ((3, (2, 3)), (2, (3, 2)))))),
        (3, ((2, ((3, (2, 3)), (2, (3, 2)))),
             (3, ((2, (3, 2)), (3, (2, 3)))))),
    )

    def test_depth_one_reproduces_figure_2_18(self):
        assert autoref(self.SEED, depth=1) == self.ITER_1

    def test_depth_two_reproduces_figure_2_19(self):
        assert autoref(self.SEED, depth=2) == self.ITER_2

    def test_depth_three_reproduces_figure_2_20(self):
        assert autoref(self.SEED, depth=3) == self.ITER_3

    def test_depth_one_is_the_default_and_is_unchanged(self):
        """Backward compatibility: the new keyword must not move depth 1."""
        for lst in ((3, 4, 5, 7), (2, 3), (1, 1, 1), (5,)):
            assert autoref(lst, depth=1) == autoref(lst)

    def test_each_head_keeps_its_integer_at_every_depth(self):
        """The head slot stays a D. Applying ``autoref`` to its own output
        instead puts the whole ``(D, S)`` pair in the head slot, which is not
        a rhythm-tree spec at all -- that is the bug ``depth`` exists to fix.
        """
        for depth in (1, 2, 3):
            assert tuple(h for h, _ in autoref((3, 4, 5, 7), depth=depth)) == (3, 4, 5, 7)

    def test_the_recursion_is_on_the_tail(self):
        for depth in (2, 3, 4):
            rows = autoref((3, 4, 5, 7), depth=depth)
            for (head, tail), (shallow_head, shallow_tail) in zip(rows, autoref((3, 4, 5, 7))):
                assert head == shallow_head
                assert tail == autoref(shallow_tail, depth=depth - 1)

    def test_leaf_count_grows_as_n_to_the_depth_plus_one(self):
        def leaves(spec):
            """Leaves of a subdivision spec: a node is an int, or (D, S)."""
            total = 0
            for node in spec:
                if isinstance(node, tuple):
                    total += leaves(node[1]) if node[1] else 1
                else:
                    total += 1
            return total

        for depth in (1, 2, 3):
            assert leaves(autoref((3, 4, 5, 7), depth=depth)) == 4 ** (depth + 1)
        for depth in (1, 2, 3):
            assert leaves(autoref((2, 3), depth=depth)) == 2 ** (depth + 1)

    def test_the_result_builds_a_rhythm_tree(self):
        from klotho.chronos import RhythmTree

        nested = autoref((3, 4, 5, 7), depth=2)
        rt = RhythmTree(meas='19/16', subdivisions=nested)
        assert rt.subdivisions == nested

    @pytest.mark.parametrize('bad', [0, -1, -5])
    def test_a_depth_below_one_raises(self, bad):
        with pytest.raises(ValueError, match='depth'):
            autoref((3, 4, 5), depth=bad)

    @pytest.mark.parametrize('bad', [1.5, '2', None])
    def test_a_non_integer_depth_raises(self, bad):
        with pytest.raises(ValueError, match='depth'):
            autoref((3, 4, 5), depth=bad)

    def test_preserve_signs_is_refused_beyond_depth_one(self):
        """``permute_list`` tests ``x >= 0`` on every element, and at depth 2
        the elements are nested tuples. Rather than invent sign semantics for
        a nested structure -- Haddad publishes no signed iterated example --
        the combination is refused outright.
        """
        with pytest.raises(ValueError, match='preserve_signs'):
            autoref((3, -4, 5), preserve_signs=True, depth=2)

    def test_preserve_signs_still_works_at_depth_one(self):
        assert autoref((3, -4, 5), preserve_signs=True, depth=1) == autoref(
            (3, -4, 5), preserve_signs=True
        )


class TestSecondPositionalArgumentIsGuarded:
    """A stray positional second argument was silently taken as ``lst2``.

    ``mode`` is keyword-only in the signature, so ``autoref_rotmat(lst, 'G')``
    does not select a mode -- it makes ``('G',)`` the tail list. That happened
    to raise "equal length" for a one-letter mode, but ``'GSDC'`` has four
    letters, so for a four-element list it was ACCEPTED and returned a matrix
    of letters. Silent corruption; the codebase's doctrine is loud failure.
    """

    def test_a_mode_string_is_rejected_by_autoref_rotmat(self):
        with pytest.raises(ValueError, match='mode'):
            autoref_rotmat((3, 4, 5, 7), 'GSDC')

    def test_a_short_mode_string_is_also_rejected_as_a_mode_mistake(self):
        with pytest.raises(ValueError, match='mode'):
            autoref_rotmat((3, 4, 5, 7), 'G')

    def test_a_mode_string_is_rejected_by_autoref(self):
        with pytest.raises(ValueError, match='number'):
            autoref((3, 4, 5, 7), 'GSDC')

    def test_the_message_names_the_offending_element(self):
        with pytest.raises(ValueError, match="'G'"):
            autoref_rotmat((3, 4, 5, 7), 'GSDC')

    def test_a_genuine_numeric_second_list_still_works(self):
        assert autoref((1, 2, 3), (10, 20, 30)) == (
            (1, (20, 30, 10)),
            (2, (30, 10, 20)),
            (3, (10, 20, 30)),
        )

    def test_floats_are_accepted(self):
        assert autoref((1, 2), (1.5, 2.5))[0][1] == (2.5, 1.5)

    @pytest.mark.parametrize('mode', ['G', 'S', 'D', 'C'])
    def test_the_keyword_form_is_untouched(self, mode):
        assert autoref_rotmat((3, 4, 5, 7), mode=mode) is not None


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


class TestSubstitute:
    """RT-7 -- Haddad's section 2.3.6, "De la substitution" ("On substitution").

    Oracle: the pair list printed in the prose. From the source list
    (5 3 4 2 1 5) he writes ``((5 3) (3 4) (4 2) (2 1) (1 5) (5 5))``,
    glossed as "renvoyant ainsi la proportion en cours avec celle qui lui
    succede" -- "thus returning the current proportion together with the one
    that succeeds it."

    That pair list is the ONLY published oracle: figure 2.16, which should
    show the resulting rhythm tree, prints figure 2.15's tree verbatim -- a
    copy-paste error in the thesis (recorded at
    ``projects/klotho-evolution/evidence/haddad-sources/FINDINGS.md:245-247``).
    """

    HADDAD_SOURCE = (5, 3, 4, 2, 1, 5)
    HADDAD_PAIRS = ((5, 3), (3, 4), (4, 2), (2, 1), (1, 5), (5, 5))

    def test_it_reproduces_haddads_published_pair_list(self):
        flat = tuple((head, tail[0]) for head, tail in substitute(self.HADDAD_SOURCE))
        assert flat == self.HADDAD_PAIRS

    def test_each_tail_holds_exactly_the_successor(self):
        lst = (3, 4, 5, 7)
        assert substitute(lst) == ((3, (4,)), (4, (5,)), (5, (7,)), (7, (3,)))

    def test_the_last_element_wraps_to_the_first(self):
        assert substitute((3, 4, 5))[-1] == (5, (3,))

    def test_every_tail_has_width_one(self):
        assert all(len(tail) == 1 for _, tail in substitute((3, 4, 5, 7, 11)))

    def test_heads_are_the_source_list_in_order(self):
        lst = (5, 3, 4, 2, 1, 5)
        assert tuple(h for h, _ in substitute(lst)) == lst

    def test_it_differs_from_pair_adjacent(self):
        assert substitute((3, 4, 5, 7)) != pair_adjacent((3, 4, 5, 7))

    def test_empty(self):
        assert substitute(()) == ()

    def test_a_singleton_gets_an_empty_tail(self):
        """Matches ``pair_adjacent``, ``nested_chain`` and
        ``alternate_sequence``, which all return ``(e, ())`` for one element:
        a lone proportion has no distinct successor to substitute in.
        """
        assert substitute((7,)) == ((7, ()),)

    def test_two_elements(self):
        assert substitute((3, 4)) == ((3, (4,)), (4, (3,)))

    def test_two_elements_agrees_with_pair_adjacent(self):
        assert substitute((3, 4)) == pair_adjacent((3, 4))

    def test_the_result_builds_a_rhythm_tree(self):
        from klotho.chronos import RhythmTree

        spec = substitute((5, 3, 4, 2, 1, 5))
        assert RhythmTree(meas='20/16', subdivisions=spec).subdivisions == spec


class TestPairAdjacent:
    """``pair_adjacent`` had zero tests and zero call sites. Pinned here
    because RT-7 documents it as NOT Haddad's substitution: its adjacency
    width is two where his is one.
    """

    def test_each_element_pairs_with_the_next_two(self):
        assert pair_adjacent((3, 4, 5, 7)) == (
            (3, (4, 5)),
            (4, (5, 7)),
            (5, (7, 3)),
            (7, (3, 4)),
        )

    def test_it_wraps_circularly(self):
        assert pair_adjacent((1, 2, 3))[-1] == (3, (1, 2))

    def test_every_tail_has_width_two(self):
        assert all(len(tail) == 2 for _, tail in pair_adjacent((1, 2, 3, 4, 5)))

    def test_the_docstring_example_holds(self):
        assert pair_adjacent((1, 2, 3, 4, 5)) == (
            (1, (2, 3)),
            (2, (3, 4)),
            (3, (4, 5)),
            (4, (5, 1)),
            (5, (1, 2)),
        )

    def test_empty(self):
        assert pair_adjacent(()) == ()

    def test_a_singleton_gets_an_empty_tail(self):
        assert pair_adjacent((7,)) == ((7, ()),)

    def test_two_elements_collapse_to_width_one(self):
        """With only two elements the next-two rule would repeat the head, so
        it degrades to the successor -- the one case where it coincides with
        Haddad's substitution."""
        assert pair_adjacent((3, 4)) == ((3, (4,)), (4, (3,)))


def blk_shape(blk):
    return [len(row) for row in blk.rows]
