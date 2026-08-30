"""``segment`` -- Haddad's segmentation operator (perp), docket OPS-5.

Source: Haddad 2020 thesis sect4.5.3.1, pp. 129-131, figs. 4.71-4.74.

    « La segmentation est l'operation qui divise une Unite Temporelle en
    deux par un facteur proportionnel pouvant etre une fraction
    quelconque entre 0 et 1, ou aussi, par un Tempus donne, relatif a
    celui de l'Unite Temporelle en question. »
    -- "Segmentation is the operation that divides a Temporal Unit in two
    by a proportional factor, which may be any fraction between 0 and 1,
    *or else by a given Tempus, relative to that of the Temporal Unit in
    question*."

That second clause is the calling convention the docket omits, and both
are implemented: a plain rational is the factor itself, a ``Meas`` is a
Tempus read relative to the source's (fig. 4.73 converts it by
multiplying by the inverse of the source Tempus, ``25/24 x 2/5 = 5/12``),
and a list of ``Meas``/units is summed first (fig. 4.74's n-th-unit form,
``(15/24 + 20/24) x 2/5 = 7/12``).

CONFORMANCE IS ASSERTED ON DURATION, NEVER ON PRINTED ``Meas`` SPELLING.
The fence's raw-int discipline (TEMPO-5) legitimately gives ``10/6``
where he prints ``5/3``: he reduced, Klotho does not. The two denote the
same duration, and the duration is the claim.

TWO TYPOS IN HIS PRINTED PROSE, both corrected by his own engravings.
Recorded here so nobody "fixes" the code to match the prose -- same class
as the already-recorded corrupt fig. 4.55 impulse:

1. p. 129 prints ``(5/4) perp 1/2 => [(5/2) | (5/2)]``, with source and
   results SWAPPED. Fig. 4.71 engraves the source as ``5/2``, and
   ``5/2 perp 1/2`` gives ``5/4 | 5/4``.
2. p. 131 prints ``5/2 x 7/12 = 25/24``. It is ``35/24``; fig. 4.74(d)
   engraves ``35/24 | 25/24``.

THE TIE VARIANT IS STAGED, NOT SHIPPED. On the prolatio that straddles
the cut, p. 130:

    « On aura ainsi le choix de, soit "scinder" les prolationis se
    trouvant dans le champs de la "coupure" (b), soit les preserver par
    une liaison rythmique (c). »
    -- "We thus have the choice either to *'split'* the prolationes
    falling within the field of the 'cut' (b), or to *preserve them by a
    rhythmic tie* (c)."

Klotho ships (b). Variant (c) would need a UT -> UT cross-container tie,
which is ties charter sect7 and is explicitly not implemented -- ties work
today only unit-locally. ``tie=True`` therefore raises.
"""

from fractions import Fraction

import pytest

from klotho.chronos import (RhythmTree, TemporalUnit, TemporalUnitSequence,
                            TemporalBlock, Meas)
from klotho.chronos.rhythm_trees.algorithms import segment_proportions
from klotho.chronos.temporal_units.algorithms import segment


def _val(m):
    """The reduced value of a ``Meas`` -- NOT ``Fraction(meas)``.

    ``Meas`` is registered as ``numbers.Rational`` and keeps raw,
    unreduced numerator/denominator, so ``Fraction(meas)`` copies them
    verbatim: ``Fraction(Meas('4/4')) != Fraction(1, 1)``. Rebuilding
    from the two ints is what normalises.
    """
    return Fraction(m.numerator, m.denominator)


def _leaf_durations(ut):
    return [ut._rt[n]['metric_duration'] for n in ut._rt.leaf_nodes]


class TestPublishedFixtures:
    """The five worked examples of figs. 4.71-4.74.

    Every assertion is on the tempus VALUE. Row 2 is the one where his
    printed spelling and Klotho's differ (``5/3`` vs ``10/6``) while the
    duration is identical.
    """

    SOURCE = ('5/2', (1,))

    @pytest.mark.parametrize('factor,left,right', [
        ('1/2', '5/4', '5/4'),
        ('2/3', '5/3', '5/6'),     # he prints 5/3; Klotho spells it 10/6
        ('1/8', '5/16', '35/16'),
        ('5/12', '25/24', '35/24'),   # fig. 4.73
        ('7/12', '35/24', '25/24'),   # fig. 4.74 (his prose prints 25/24)
    ])
    def test_published_pair(self, factor, left, right):
        ut = TemporalUnit(tempus=self.SOURCE[0], prolatio=self.SOURCE[1])
        out = segment(ut, factor)
        assert len(out.seq) == 2
        assert [_val(u.tempus) for u in out.seq] == [Fraction(left),
                                                     Fraction(right)]

    def test_the_reduction_difference_is_spelling_only(self):
        """Row 2, stated explicitly: 10/6 is not 5/3 on the page, but it
        is the same duration, and the raw-int spelling is the fence."""
        ut = TemporalUnit(tempus='5/2', prolatio=(1,))
        left = segment(ut, '2/3').seq[0]
        assert str(left.tempus) == '10/6'
        assert _val(left.tempus) == Fraction(5, 3)


class TestTempusConvention:
    """His second calling convention: a given Tempus, read relative to
    the source's."""

    def test_a_meas_factor_is_relative_fig_4_73(self):
        ut = TemporalUnit(tempus='5/2', prolatio=(1,))
        out = segment(ut, Meas('25/24'))     # 25/24 x 2/5 = 5/12
        assert [_val(u.tempus) for u in out.seq] == [Fraction(25, 24),
                                                     Fraction(35, 24)]

    def test_a_list_of_tempi_is_summed_fig_4_74(self):
        ut = TemporalUnit(tempus='5/2', prolatio=(1,))
        out = segment(ut, [Meas('15/24'), Meas('20/24')])
        # (15/24 + 20/24) x 2/5 = 7/12
        assert [_val(u.tempus) for u in out.seq] == [Fraction(35, 24),
                                                     Fraction(25, 24)]

    def test_a_list_of_units_is_summed_too(self):
        """The workflow of fig. 4.73(b)-(c): decompose, then use the
        resulting fundamental units as segmentation proportions."""
        ut = TemporalUnit(tempus='5/2', prolatio=(1,))
        parts = [TemporalUnit(tempus='15/24', prolatio=(1,)),
                 TemporalUnit(tempus='20/24', prolatio=(1,))]
        out = segment(ut, parts)
        assert [_val(u.tempus) for u in out.seq] == [Fraction(35, 24),
                                                     Fraction(25, 24)]

    def test_a_rational_and_a_meas_of_the_same_text_differ(self):
        """The one real footgun, pinned: '5/12' is the factor itself,
        ``Meas('5/12')`` is a Tempus relative to the source's."""
        ut = TemporalUnit(tempus='5/2', prolatio=(1,))
        by_ratio = segment(ut, '5/12').seq[0]
        by_tempus = segment(ut, Meas('5/12')).seq[0]
        assert _val(by_ratio.tempus) == Fraction(25, 24)
        assert _val(by_tempus.tempus) == Fraction(5, 12) * Fraction(2, 5) \
            * Fraction(5, 2)


class TestShape:
    def test_returns_exactly_two_units_in_a_sequence(self):
        out = segment(TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1)), '1/4')
        assert isinstance(out, TemporalUnitSequence)
        assert len(out.seq) == 2

    def test_total_duration_is_preserved(self):
        ut = TemporalUnit(tempus='5/2', prolatio=(1, 2, 3), beat='1/4', bpm=72)
        for f in ('1/2', '2/3', '1/8', '5/12', '7/12'):
            assert segment(ut, f).duration == pytest.approx(ut.duration)

    def test_tempo_and_span_carry_over(self):
        ut = TemporalUnit(span=2, tempus='4/4', prolatio=(1, 1),
                          beat='1/8', bpm=96)
        out = segment(ut, '1/4')
        for u in out.seq:
            assert u.beat == Fraction(1, 8)
            assert u.bpm == 96
            assert u.span == 2
        assert out.duration == pytest.approx(ut.duration)

    def test_a_rhythm_tree_gives_two_rhythm_trees(self):
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
        left, right = segment(rt, '1/4')
        assert isinstance(left, RhythmTree) and isinstance(right, RhythmTree)
        assert _val(left.meas) == Fraction(1, 4)
        assert _val(right.meas) == Fraction(3, 4)


class TestSplitVariant:
    """Variant (b): the prolatio in the field of the cut is SPLIT."""

    def test_a_boundary_cut_partitions_cleanly(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1))
        left, right = segment(ut, '1/2').seq
        assert left.prolationis == (1, 1)
        assert right.prolationis == (1, 1)

    def test_a_straddled_leaf_becomes_two_attacks(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1))
        left, right = segment(ut, '3/8').seq
        assert _val(left.tempus) == Fraction(3, 8)
        assert _val(right.tempus) == Fraction(5, 8)
        assert _leaf_durations(left) == [Fraction(1, 4), Fraction(1, 8)]
        assert _leaf_durations(right) == [Fraction(1, 8), Fraction(1, 4),
                                          Fraction(1, 4)]

    def test_the_two_halves_reconstruct_the_source_leaves(self):
        """The invariant that holds for every cut: concatenating the
        halves' leaf durations gives the source's, with the straddled
        leaf replaced by its two pieces."""
        ut = TemporalUnit(tempus='4/4', prolatio=(2, (3, (1, 1, 1)), 1))
        for f in ('1/8', '1/3', '3/8', '5/9', '7/8'):
            left, right = segment(ut, f).seq
            pieces = _leaf_durations(left) + _leaf_durations(right)
            assert sum(pieces) == sum(_leaf_durations(ut))
            assert len(pieces) in (len(_leaf_durations(ut)),
                                   len(_leaf_durations(ut)) + 1)

    def test_nesting_survives_a_cut_inside_a_group(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, (3, (1, 1, 1))))
        left, right = segment(ut, '1/2').seq
        # The 3-tuplet is cut after its first third: both halves keep a
        # group rather than being flattened.
        assert any(isinstance(e, tuple) for e in left.prolationis)
        assert any(isinstance(e, tuple) for e in right.prolationis)

    def test_a_rest_stays_a_rest_on_both_sides(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, -2, 1))
        left, right = segment(ut, '1/2').seq
        assert _leaf_durations(left) == [Fraction(1, 4), Fraction(-1, 4)]
        assert _leaf_durations(right) == [Fraction(-1, 4), Fraction(1, 4)]


class TestTies:
    def test_tie_true_is_staged_not_shipped(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1))
        with pytest.raises(NotImplementedError) as exc:
            segment(ut, '3/8', tie=True)
        msg = str(exc.value)
        assert '7' in msg           # charter sect7
        assert 'tie' in msg.lower()

    def test_a_whole_tied_leaf_keeps_its_tie(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1))
        left, right = segment(ut, '1/2').seq
        assert [left._rt[n].get('tied') for n in left._rt.leaf_nodes] \
            == [False, True]

    def test_the_split_variant_does_not_tie_the_two_pieces(self):
        """Variant (b) makes two independent attacks -- that is exactly
        what distinguishes it from variant (c)."""
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1))
        left, right = segment(ut, '3/8').seq
        assert right._rt[right._rt.leaf_nodes[0]].get('tied') is False


class TestRefusals:
    def test_a_factor_of_zero_raises(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1,))
        with pytest.raises(ValueError):
            segment(ut, 0)

    def test_a_factor_of_one_raises(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1,))
        with pytest.raises(ValueError):
            segment(ut, 1)

    def test_a_negative_factor_raises(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1,))
        with pytest.raises(ValueError):
            segment(ut, '-1/2')

    def test_a_sequence_is_not_segmentable(self):
        seq = TemporalUnitSequence([TemporalUnit(tempus='4/4', prolatio=(1,))])
        with pytest.raises(TypeError):
            segment(seq, '1/2')

    def test_a_block_is_not_segmentable(self):
        block = TemporalBlock([
            TemporalUnitSequence([TemporalUnit(tempus='4/4', prolatio=(1,))])
        ])
        with pytest.raises(TypeError):
            segment(block, '1/2')

    def test_a_compositional_unit_is_staged(self):
        from klotho.thetos.composition.compositional import CompositionalUnit
        cu = CompositionalUnit(tempus='4/4', prolatio=(1, 1))
        with pytest.raises(NotImplementedError):
            segment(cu, '1/4')


class TestSegmentProportions:
    """The pair helper, renamed from ``segment`` (the operator took the
    name back) and with two live defects fixed. It had ZERO test coverage
    before this module: every ``segment`` hit under ``tests/`` was a slur
    or envelope segment."""

    def test_the_documented_behaviour(self):
        assert segment_proportions(Fraction(1, 3)) == (1, 2)
        assert segment_proportions('2/5') == (2, 3)

    def test_the_float_path_is_usable(self):
        """DEFECT 1: ``Fraction(1/3)`` with no ``limit_denominator`` gave
        ``(6004799503160661, 12009599006321323)`` -- the documented float
        path was unusable."""
        assert segment_proportions(1 / 3) == (1, 2)
        assert segment_proportions(0.25) == (1, 3)

    def test_zero_raises(self):
        """DEFECT 2: it returned ``(0, 1)``, a zero proportion the rhythm
        tree grammar rejects with 'proportion at S[0] cannot be zero'."""
        with pytest.raises(ValueError):
            segment_proportions(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            segment_proportions('-1/2')

    def test_one_or_more_raises(self):
        with pytest.raises(ValueError):
            segment_proportions(1)
        with pytest.raises(ValueError):
            segment_proportions('3/2')
