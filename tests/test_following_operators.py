"""The Tempus-FOLLOWING operator family -- augmentation, diminution,
dilatation/contraction (docket OPS-2/3/4, box half).

Source: Haddad 2020 thesis sect4.5.2-4.5.3, pp. 124-128, figs. 4.58-4.69.

THE AXIS. Every add/remove/scale operator comes in two policies, and
Haddad states the difference outright on p. 128:

    « Les prolationis qui en resultent sont identiques. C'est le Tempus
    qui differe. Dans le cas de la << prolation >> stricte, le Tempus est
    identique. Dans le deuxieme cas, le Tempus est la somme des
    prolationis une fois transformes. »
    -- "The resulting prolationis are identical. It is the Tempus that
    differs. In the case of strict 'prolation', the Tempus is identical.
    In the second case, *the Tempus is the sum of the prolationis once
    transformed*."

The second case is this family: the Tempus FOLLOWS. bpm is held, so the
real duration changes and the notation changes with it. His own terms for
the two policies are « prolationnelle stricte » ("strictly prolational")
for the preserved half and « relative » for this one; the English pair
"Tempus-preserving"/"Tempus-following" is Klotho's coinage -- he never
writes it.

    box = follows (here)     circle = preserved (test_preserved_operators)
    augmentation  (+ in a box)   insertion   (+ in a circle)
    diminution    (- in a box)   extraction  (- in a circle)
    dilatation/contraction       expansion/compression
      (x in a box, U+22A0)         (x in a circle, U+2297)

EVERY OPERATOR IS decompose -> operate -> concatenate, sect4.5.2 preamble,
p. 124:

    « Ces operations utilisent l'ajout equivalent a l'addition, le retrait
    a la soustraction, et la substitution (sous forme de multiplication)
    apres decomposition de l'Unite temporelle composee suivi de la
    concatenation de l'ensemble des prolationis. »
    -- "These operations use addition for adding, subtraction for
    removal, and substitution (in the form of multiplication) -- after
    decomposition of the composite Temporal Unit, followed by
    concatenation of the whole set of prolationis."

so all three ship as ``decompose`` + edit + ``fuse``, and the common
denominator that makes an inserted or scaled operand commensurable with
the survivors is ``_fuse_parts``' lcm fold, already shipped.

INDEXING, settled by the source itself, p. 125:

    « ...et position la position de l'ajout par rapport a l'ensemble de la
    sequence decomposee (0 etant la position de tete de sequence). »
    -- "...and position is the position of the addition relative to the
    whole decomposed sequence (0 being the head-of-sequence position)."

0-based into the DECOMPOSED sequence, insert-before, indices naming the
ORIGINAL pre-operation sequence. p. 127 repeats it for the scaling
operator ("0 being the first prolatio").

CONFORMANCE IS ASSERTED ON DURATION AND ON THE PROLATIONIS, NEVER ON HIS
PRINTED ``Meas`` SPELLING. His diminution Tempi are inconsistent even
within one figure pair -- he prints 14/18 as ``7/9`` and 10/18 as ``5/9``
but leaves 15/18 alone. Those reductions are not rule-generated; TEMPO-5
keeps the raw ints. Same duration, his reduction, not a divergence.

TWO CORRUPT FIGURES, recorded so nobody "fixes" the code to match the
print -- same class as the already-recorded corrupt fig. 4.55 impulse:

1. figs. 4.58 and 4.60 print the source subscript as ``(2 1 1)``. The
   correct input is ``(2 1 2)``, proven three ways: the prose says
   « trois prolationis de (2 1 2) » ("three prolationis of (2 1 2)"), the
   engraving is a 5:4 tuplet (5 = 2+1+2), and only ``(2 1 2)`` yields the
   printed result ``(4 2 3 4)``.
2. figs. 4.68 and 4.69 reprint the *expansion* result ``(4 2 9 6 3)`` as
   the contraction's prolationis. Fig. 4.69's Tempus ``16/27`` is correct
   and forces the true answer, ``(12 6 3 2 9)`` on 54.
"""

from fractions import Fraction

import pytest

from klotho.chronos import (RhythmTree, TemporalUnit, TemporalUnitSequence,
                            TemporalBlock, Meas)
from klotho.chronos.rhythm_trees.algorithms import (
    diminish as rt_diminish,
    scale_tempus as rt_scale_tempus,
)
from klotho.chronos.temporal_units.algorithms import diminish, scale_tempus


def _val(m):
    """The reduced value of a ``Meas`` -- NOT ``Fraction(meas)``.

    ``Meas`` is registered as ``numbers.Rational`` and keeps raw,
    unreduced numerator/denominator, so ``Fraction(meas)`` copies them
    verbatim: ``Fraction(Meas('4/4')) != Fraction(1, 1)``. Rebuilding
    from the two ints is what normalises.
    """
    return Fraction(m.numerator, m.denominator)


def _spelling(rt):
    """``(numerator, denominator, subdivisions)`` -- the printed form."""
    return (rt.meas.numerator, rt.meas.denominator, rt.subdivisions)


# B is his running source for figs. 4.62-4.69: the *reduction* of
# ``1/1 ((2 (2 1)) 1 2 1)``, fig. 4.62. Klotho's ``flatten`` already
# reproduces it character for character.
def _B():
    return RhythmTree(meas='18/18', subdivisions=(4, 2, 3, 6, 3))


class TestDiminution:
    """Diminution -- - in a box, sect4.5.2.2, p. 126, figs. 4.62-4.63.

        « Le tempus sera par consequent recalcule a partir de la somme des
        prolationis restants. »
        -- "The tempus will consequently be recomputed from the sum of
        the remaining prolationis."
    """

    def test_fig_4_63_head(self):
        assert _spelling(rt_diminish(_B(), 0)) == (14, 18, (2, 3, 6, 3))

    def test_fig_4_63_tail(self):
        assert _spelling(rt_diminish(_B(), 4)) == (15, 18, (4, 2, 3, 6))

    def test_fig_4_63_multiple(self):
        assert _spelling(rt_diminish(_B(), (1, 3))) == (10, 18, (4, 3, 3))

    def test_his_printed_tempi_are_reductions_not_a_divergence(self):
        # He prints 14/18 as ``7/9`` and 10/18 as ``5/9`` but leaves
        # 15/18 alone -- his spellings are not rule-generated. TEMPO-5
        # keeps the raw ints; the DURATION is the claim.
        assert _val(rt_diminish(_B(), 0).meas) == Fraction(7, 9)
        assert _val(rt_diminish(_B(), (1, 3)).meas) == Fraction(5, 9)
        assert _val(rt_diminish(_B(), 4).meas) == Fraction(5, 6)

    def test_tempus_is_the_sum_of_the_survivors(self):
        out = rt_diminish(_B(), (1, 3))
        assert sum(abs(s) for s in out.subdivisions) == out.meas.numerator

    def test_duration_shrinks_by_exactly_the_removed_prolatio(self):
        # B's third prolatio (index 2) is 3/18 = 1/6.
        assert _val(rt_diminish(_B(), 2).meas) == Fraction(18, 18) - Fraction(1, 6)

    def test_removing_everything_raises(self):
        with pytest.raises(ValueError):
            rt_diminish(_B(), (0, 1, 2, 3, 4))

    def test_out_of_range_position_raises(self):
        with pytest.raises(ValueError):
            rt_diminish(_B(), 5)
        with pytest.raises(ValueError):
            rt_diminish(_B(), -1)

    def test_empty_positions_raises(self):
        with pytest.raises(ValueError):
            rt_diminish(_B(), ())


class TestDilatationContraction:
    """Dilatation/Contraction -- x in a box (U+22A0), sect4.5.2.3,
    pp. 127-128, figs. 4.66-4.69.

    ONE operator: the ratio's size decides the direction, which is
    exactly why the Klotho verb is not called ``dilate`` -- that name is
    accurate above 1 and actively misleading below it. The pair is named
    for the POLICY (``scale_tempus`` here, ``scale`` for the preserved
    sibling), which is the point of the axis.
    """

    def test_fig_4_66_dilatation(self):
        assert _spelling(rt_scale_tempus(_B(), 3, 2)) == (24, 18, (4, 2, 9, 6, 3))

    def test_fig_4_69_contraction(self):
        # NEVER use figs. 4.68/4.69's printed prolationis -- both reprint
        # the preceding EXPANSION result ``(4 2 9 6 3)``. His Tempus
        # 16/27 is correct and forces the true answer; 32/54 is its raw
        # spelling on the grid the contraction actually refines to.
        out = rt_scale_tempus(_B(), ('1/3', '1/9'), (2, 3))
        assert _spelling(out) == (32, 54, (12, 6, 3, 2, 9))
        assert _val(out.meas) == Fraction(16, 27)

    def test_tempus_is_the_sum_of_the_transformed_prolationis(self):
        out = rt_scale_tempus(_B(), 3, 2)
        assert sum(abs(s) for s in out.subdivisions) == out.meas.numerator

    def test_duration_changes_by_exactly_the_scaled_prolatio(self):
        # B's index 2 is 3/18 = 1/6; tripling it adds 2/6.
        assert (_val(rt_scale_tempus(_B(), 3, 2).meas)
                == Fraction(1, 1) + Fraction(2, 6))

    def test_ratio_one_is_a_no_op_in_value(self):
        out = rt_scale_tempus(_B(), 1, 2)
        assert _val(out.meas) == Fraction(1, 1)
        assert out.subdivisions == (4, 2, 3, 6, 3)

    def test_a_rest_keeps_its_sign_under_scaling(self):
        src = RhythmTree(meas='4/4', subdivisions=(1, -1, 1, 1))
        out = rt_scale_tempus(src, 2, 1)
        assert out.subdivisions == (1, -2, 1, 1)

    def test_scalars_broadcast(self):
        assert (_spelling(rt_scale_tempus(_B(), (3,), (2,)))
                == _spelling(rt_scale_tempus(_B(), 3, 2)))

    def test_a_meas_ratio_keeps_its_raw_spelling(self):
        # A Meas ratio is read raw (TEMPO-5); a Fraction/str normalises,
        # which is Fraction's contract, not a policy of this verb.
        assert (rt_scale_tempus(_B(), Meas(2, 6), 2).meas.denominator
                != rt_scale_tempus(_B(), '1/3', 2).meas.denominator)

    def test_zero_ratio_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), 0, 2)

    def test_negative_ratio_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), '-1/3', 2)

    def test_duplicate_position_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), (2, 3), (1, 1))

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), (2, 3), (1,))

    def test_out_of_range_position_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), 2, 5)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            rt_scale_tempus(_B(), (), ())


class TestTiesCollapse:
    """A tie group decomposes to ONE fundamental unit (ALG-2), so the
    follows family indexes tie GROUPS, not leaves -- and, like
    ``flatten``, whose machinery it is, it returns a surface with one term
    per sounding event and no ties left."""

    def test_positions_index_tie_groups(self):
        src = RhythmTree(meas='4/4', subdivisions=(1, 1.0, 1, 1))
        # three groups: (1 1.0), (1), (1) -- position 1 is the THIRD leaf
        out = rt_diminish(src, 1)
        assert out.subdivisions == (2, 1)

    def test_rests_survive_a_diminution(self):
        src = RhythmTree(meas='4/4', subdivisions=(1, -1, 1, 1))
        assert rt_diminish(src, 0).subdivisions == (-1, 1, 1)


class TestTemporalUnitSurface:
    """bpm is HELD; the Tempus follows, so the real duration changes."""

    def test_diminish_holds_bpm_and_shrinks_the_duration(self):
        ut = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3),
                          beat='1/4', bpm=60)
        out = diminish(ut, 0)
        assert out.bpm == 60 and out.beat == ut.beat
        assert _val(out.tempus) == Fraction(7, 9)
        assert out.duration == pytest.approx(ut.duration * 14 / 18)

    def test_span_folds_in(self):
        ut = TemporalUnit(span=2, tempus='18/18', prolatio=(4, 2, 3, 6, 3),
                          beat='1/4', bpm=60)
        out = diminish(ut, 0)
        assert out.span == 1
        assert _val(out.tempus) == Fraction(14, 9)

    def test_attribution_marks_the_tempus(self):
        ut = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3),
                          beat='1/4', bpm=60)
        assert 'tempus' in diminish(ut, 0).attributed

    def test_rhythm_tree_in_returns_rhythm_tree(self):
        assert isinstance(diminish(_B(), 0), RhythmTree)

    def test_sequence_refused(self):
        ut = TemporalUnit(tempus='1/4', prolatio=(1, 1))
        with pytest.raises(TypeError):
            diminish(TemporalUnitSequence([ut]), 0)

    def test_block_refused(self):
        ut = TemporalUnit(tempus='1/4', prolatio=(1, 1))
        with pytest.raises(TypeError):
            diminish(TemporalBlock([TemporalUnitSequence([ut])]), 0)


class TestCompositionalUnitRefused:
    """The follows family rebuilds the tree from a decomposition, so leaf
    identity is destroyed and parameter state has nowhere to land -- the
    same ground on which ``flatten`` and ``segment`` refuse (R13-E).
    ``interleave`` accepts a CU because it merges nothing at all."""

    def test_diminish_refuses(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        cu = CompositionalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
        with pytest.raises(NotImplementedError):
            diminish(cu, 0)

    def test_scale_tempus_holds_bpm(self):
        ut = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3),
                          beat='1/4', bpm=60)
        out = scale_tempus(ut, 3, 2)
        assert out.bpm == 60 and out.beat == ut.beat
        assert _val(out.tempus) == Fraction(4, 3)
        assert out.duration == pytest.approx(ut.duration * 24 / 18)

    def test_scale_tempus_refuses_a_compositional_unit(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        cu = CompositionalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
        with pytest.raises(NotImplementedError):
            scale_tempus(cu, 3, 2)

    def test_scale_tempus_refuses_a_sequence(self):
        ut = TemporalUnit(tempus='1/4', prolatio=(1, 1))
        with pytest.raises(TypeError):
            scale_tempus(TemporalUnitSequence([ut]), 2, 0)
