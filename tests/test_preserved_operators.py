"""Haddad's Tempus-PRESERVING operator family: insert, extract, scale.

The axis (TEMPO-1/R13-A). Haddad's notation is systematic -- a BOX means the
Tempus FOLLOWS the operation, a CIRCLE means the Tempus is PRESERVED:

    add     augmentation  (+ in a box)   insertion             (+ in a circle)
    remove  diminution    (- in a box)   extraction            (- in a circle)
    scale   dilatation    (x in a box)   expansion/compression (x in a circle)

He states the axis outright on p. 128:

    « Les prolationis qui en résultent sont identiques. C'est le Tempus qui
    diffère. Dans le cas de la « prolation » stricte, le Tempus est
    identique. Dans le deuxième cas, le Tempus est la somme des prolationis
    une fois transformés. »

    "The resulting prolationis are identical. It is the Tempus that differs.
    In the case of strict 'prolation', the Tempus is identical. In the second
    case, the Tempus is the sum of the prolationis once transformed."

He never writes "Tempus-preserving" or "Tempus-following"; his own terms are
*« prolationnelle stricte »* ("strictly prolational") for the circle family
and *« relative »* ("relative") for the box family. The English pair is
Klotho's coinage.

This file covers the CIRCLE family only. The box family (augmentation,
diminution, dilatation) builds a new tree with a recomputed Tempus and lives
elsewhere.

Every operator is decompose -> operate -> concatenate (sect4.5.2, p. 124):

    « Ces opérations utilisent l'ajout équivalent à l'addition, le retrait à
    la soustraction, et la substitution (sous forme de multiplication) après
    décomposition de l'Unité temporelle composée suivi de la concaténation de
    l'ensemble des prolationis. »

    "These operations use addition for adding, subtraction for removal, and
    substitution (in the form of multiplication) -- after decomposition of the
    composite Temporal Unit, followed by concatenation of the whole set of
    prolationis."
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import flatten


# ----------------------------------------------------------------------
# insertion -- (+ in a circle)
# ----------------------------------------------------------------------
class TestInsertionFigure460:
    """fig. 4.60. Thesis typo: the figure prints the source subscript as
    ``(2 1 1)``. The correct input is ``(2 1 2)``, proven three ways -- the
    prose says *« trois prolationis de (2 1 2) »* ("three prolationis of
    (2 1 2)"), the engraving is a 5:4 tuplet (5 = 2+1+2), and only ``(2 1 2)``
    yields ``(4 2 3 4)``. The same broken macro repeats from fig. 4.58."""

    def test_the_published_result(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert rt.group.S == (4, 2, 3, 4)

    def test_the_tempus_spelling_survives_verbatim(self):
        """The flatten is an INTERNAL step, never part of the result. Carrying
        the flattened Tempus through gives identical real durations, so no
        arithmetic assertion catches it -- only this one does."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert str(rt.meas) == '2/2'
        assert rt.span == 1

    def test_returns_self_for_chaining(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.insert(2, Fraction(3, 10)) is rt


class TestInsertionIndexing:
    """0-based indices into the DECOMPOSED sequence, insert BEFORE index k
    (p. 125): *« …et position la position de l'ajout par rapport à l'ensemble
    de la séquence décomposée (0 étant la position de tête de séquence). »*
    -- "…and position is the position of the addition relative to the whole
    decomposed sequence (0 being the head-of-sequence position)." """

    def test_head_position_is_zero(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(0, Fraction(1, 5))
        assert rt.group.S == (1, 2, 1, 2)

    def test_tail_position_is_the_length(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(3, Fraction(1, 5))
        assert rt.group.S == (2, 1, 2, 1)

    def test_negative_index_counts_from_the_end(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(-1, Fraction(1, 5))
        assert rt.group.S == (2, 1, 1, 2)

    @pytest.mark.parametrize('index', [4, -5])
    def test_out_of_range_raises(self, index):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(IndexError):
            rt.insert(index, Fraction(1, 5))

    def test_indices_refer_to_the_ORIGINAL_sequence(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert([0, 3], [Fraction(1, 5), Fraction(1, 5)])
        assert rt.group.S == (1, 2, 1, 2, 1)

    def test_two_insertions_at_one_index_keep_argument_order(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert([1, 1], [Fraction(1, 5), Fraction(2, 5)])
        assert rt.group.S == (2, 1, 2, 1, 2)

    def test_mismatched_lengths_raise(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.insert([0, 1], [Fraction(1, 5)])


class TestInsertionSemantics:
    def test_the_bar_does_not_grow(self):
        """Strictly prolational: the inserted value only fixes the new note's
        RELATIVE weight. Everything compresses; the Tempus is untouched."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert sum(abs(d) for d in rt.durations) == Fraction(1)
        assert rt.durations == (Fraction(4, 13), Fraction(2, 13),
                                Fraction(3, 13), Fraction(4, 13))

    def test_a_negative_duration_inserts_a_rest(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(1, Fraction(-1, 5))
        assert rt.group.S == (2, -1, 1, 2)
        assert rt.durations[1] < 0

    def test_zero_is_refused(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.insert(1, 0)

    def test_a_nested_operand_flattens(self):
        """decompose -> operate -> concatenate: the result is one level, by
        construction. Nesting is not preserved by the circle family."""
        rt = RT(meas='1/1', subdivisions=((2, (2, 1)), 1, 2, 1))
        assert flatten(rt).group.S == (4, 2, 3, 6, 3)
        rt.insert(0, Fraction(1, 18))
        assert rt.group.S == (1, 4, 2, 3, 6, 3)

    def test_a_tie_group_decomposes_as_one_event(self):
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1, 1))
        assert rt.tie_groups == ((1, 2), (3,), (4,))
        rt.insert(0, Fraction(1, 4))
        assert rt.group.S == (1, 2, 1, 1)

    def test_a_string_ratio_is_accepted(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, '3/10')
        assert rt.group.S == (4, 2, 3, 4)


# ----------------------------------------------------------------------
# extraction -- (- in a circle)
# ----------------------------------------------------------------------
class TestExtraction:
    """``prune`` was already extraction for LEAVES; ``extract`` is the named
    verb and delegates to ``remove_subtree``, which is correct in general."""

    def test_extracting_a_leaf_holds_the_tempus(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.extract(2)
        assert str(rt.meas) == '2/2'
        assert rt.group.S == (2, 2)
        assert sum(abs(d) for d in rt.durations) == Fraction(1)

    def test_survivors_dilate_to_fill_the_bar(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.durations == (Fraction(2, 5), Fraction(1, 5), Fraction(2, 5))
        rt.extract(2)
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2))

    def test_extracting_a_whole_group(self):
        rt = RT(meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
        group = rt.successors(rt.root)[1]
        rt.extract(group)
        assert rt.group.S == (1, 3)

    def test_several_nodes_at_once(self):
        rt = RT(meas='4/4', subdivisions=(1, 2, 3, 4))
        succ = rt.successors(rt.root)
        rt.extract([succ[0], succ[2]])
        assert rt.group.S == (2, 4)

    def test_extracting_the_root_raises(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.extract(rt.root)

    def test_returns_self_for_chaining(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.extract(2) is rt

    def test_prune_and_extract_agree_on_a_leaf(self):
        a = RT(meas='2/2', subdivisions=(2, 1, 2)).prune(2)
        b = RT(meas='2/2', subdivisions=(2, 1, 2)).extract(2)
        assert a.group == b.group
        assert a.durations == b.durations

    def test_prune_promotes_and_changes_durations_on_an_INTERIOR_node(self):
        """The documented divergence: on an interior node ``prune`` promotes
        the children one level, which is duration-preserving only when
        ``D == sum(S)``. ``extract``/``remove_subtree`` is the general verb."""
        rt = RT(meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
        assert rt.durations == (Fraction(1, 9), Fraction(5, 18),
                                Fraction(5, 18), Fraction(1, 3))
        rt.prune(rt.successors(rt.root)[1])
        assert rt.group.S == (1, 1, 1, 3)
        assert rt.durations == (Fraction(1, 6), Fraction(1, 6),
                                Fraction(1, 6), Fraction(1, 2))


# ----------------------------------------------------------------------
# expansion / compression -- (x in a circle)
# ----------------------------------------------------------------------
class TestScaleFigure465:
    """fig. 4.65 -- expansion of the third prolatio by 3."""

    def test_the_published_result(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 3)
        assert rt.group.S == (4, 2, 9, 6, 3)
        assert str(rt.meas) == '18/18'


class TestScaleFigure468:
    """fig. 4.68, CORRECTED. Never use figs. 4.68/4.69's printed prolationis:
    both reprint the expansion result ``(4 2 9 6 3)``. Fig. 4.69's Tempus
    ``16/27`` is correct and forces the true answer."""

    def test_the_corrected_result(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.group.S == (12, 6, 3, 2, 9)

    def test_the_tempus_is_respelled_on_the_refined_grid(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert str(rt.meas) == '54/54'
        assert rt.meas.to_fraction() == Fraction(1)


class TestScaleSemantics:
    def test_an_authored_tempus_is_left_alone(self):
        """``2/2`` over a five-part prolatio was never the grid, so it says
        something about the bar and is kept verbatim."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.scale(1, 2)
        assert str(rt.meas) == '2/2'
        assert rt.group.S == (2, 2, 2)

    def test_the_tempus_VALUE_never_changes(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        before = rt.meas.to_fraction() * rt.span
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.meas.to_fraction() * rt.span == before

    def test_the_bar_stays_full(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 3)
        assert sum(abs(d) for d in rt.durations) == Fraction(1)

    def test_expansion_makes_the_target_relatively_longer(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        before = rt.durations
        rt.scale(2, 3)
        after = rt.durations
        assert after[2] / after[0] == 3 * (before[2] / before[0])

    def test_a_rest_keeps_its_sign(self):
        rt = RT(meas='4/4', subdivisions=(1, -1, 2))
        rt.scale(1, 2)
        assert rt.group.S == (1, -2, 2)

    def test_negative_ratio_is_refused(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 2))
        with pytest.raises(ValueError):
            rt.scale(1, -2)

    def test_zero_ratio_is_refused(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 2))
        with pytest.raises(ValueError):
            rt.scale(1, 0)

    @pytest.mark.parametrize('index', [5, -6])
    def test_out_of_range_raises(self, index):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        with pytest.raises(IndexError):
            rt.scale(index, 2)

    def test_mismatched_lengths_raise(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        with pytest.raises(ValueError):
            rt.scale([0, 1], [2])

    def test_ratio_one_is_a_no_op(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 1)
        assert rt.group.S == (4, 2, 3, 6, 3)
        assert str(rt.meas) == '18/18'

    def test_returns_self_for_chaining(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        assert rt.scale(2, 3) is rt

    def test_a_nested_operand_flattens(self):
        rt = RT(meas='1/1', subdivisions=((2, (2, 1)), 1, 2, 1))
        rt.scale(2, 3)
        assert rt.group.S == (4, 2, 9, 6, 3)


class TestSpanIsAlwaysPreserved:
    def test_a_multi_measure_tree_keeps_its_span_and_length(self):
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.scale(1, Fraction(1, 3))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'
        assert rt.group.S == (3, 1, 3, 3)
        assert sum(abs(d) for d in rt.durations) == Fraction(2)

    def test_insertion_into_a_multi_measure_tree(self):
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.insert(0, Fraction(1, 2))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'
        assert rt.group.S == (1, 1, 1, 1, 1)
        assert sum(abs(d) for d in rt.durations) == Fraction(2)


class TestPreservedFamilyChains:
    def test_the_family_composes(self):
        rt = (RT(meas='2/2', subdivisions=(2, 1, 2))
              .insert(2, Fraction(3, 10))
              .scale(0, 2))
        assert rt.group.S == (8, 2, 3, 4)
        assert str(rt.meas) == '2/2'
