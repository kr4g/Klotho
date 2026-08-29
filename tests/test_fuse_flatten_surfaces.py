"""The lifted fuse/flatten surfaces (LAYER-3 reconciliation; ruling R13).

The conformance spine is the LAYER-1 probe's exhibit
(projects/klotho-evolution/evidence/layer1-probe/): candidate (d) on
mixed-tempo operands — lift, reconcile at the first operand's reference
(exact, unreduced), fuse symbolically, re-temporalise — with every leaf's
real clock duration preserved.
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree, TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.rhythm_trees import Meas
from klotho.chronos.temporal_units.algorithms import fuse, flatten
from klotho.thetos.composition.compositional import CompositionalUnit


class TestFuseSameTempo:
    def test_published_example_lifted(self):
        parts = [TemporalUnit(tempus=m, prolatio='d', beat='1/4', bpm=60)
                 for m in ('6/20', '3/20', '3/20', '3/20')]
        out = fuse(parts)
        assert str(out.tempus) == '15/20'
        assert out.prolationis == (6, 3, 3, 3)
        assert out.beat == Fraction(1, 4) and out.bpm == 60

    def test_identity_reconciliation_is_a_no_op(self):
        a = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        b = TemporalUnit(tempus='3/20', prolatio=(1, 1, 1), beat='1/4', bpm=60)
        out = fuse(a, b)
        assert str(out.tempus) == '9/20'


class TestFuseMixedTempo:
    """The probe's Part 3, as a shipped surface."""

    def _operands(self):
        ut1 = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        ut2 = TemporalUnit(tempus='3/20', prolatio=(1, 1, 1), beat='1/8', bpm=90)
        return ut1, ut2

    def test_reconciles_at_first_operand_reference(self):
        ut1, ut2 = self._operands()
        out = fuse(ut1, ut2)
        assert str(out.tempus) == '30/60'
        assert out.prolationis == ((18, (2, 1, 1)), (12, (1, 1, 1)))
        assert out.beat == ut1.beat and out.bpm == ut1.bpm

    def test_total_real_duration_is_the_sum(self):
        ut1, ut2 = self._operands()
        out = fuse(ut1, ut2)
        assert out.duration == pytest.approx(ut1.duration + ut2.duration,
                                             abs=1e-9)

    def test_every_leaf_real_duration_preserved(self):
        ut1, ut2 = self._operands()
        out = fuse(ut1, ut2)
        orig = [c.duration for c in ut1] + [c.duration for c in ut2]
        assert [c.duration for c in out] == pytest.approx(orig, abs=1e-9)

    def test_explicit_reference_override(self):
        ut1, ut2 = self._operands()
        out = fuse(ut1, ut2, reference=('1/8', 90))
        assert out.beat == Fraction(1, 8) and out.bpm == 90
        assert out.duration == pytest.approx(ut1.duration + ut2.duration,
                                             abs=1e-9)


class TestFuseDispatch:
    def test_all_rhythm_trees_stay_symbolic(self):
        parts = [RhythmTree(span=1, meas='6/20', subdivisions=(1,)),
                 RhythmTree(span=1, meas='3/20', subdivisions=(1,))]
        out = fuse(parts)
        assert isinstance(out, RhythmTree)
        assert str(out.meas) == '9/20'

    def test_reference_refused_for_symbolic_operands(self):
        parts = [RhythmTree(span=1, meas='6/20', subdivisions=(1,))]
        with pytest.raises(ValueError, match='no tempo'):
            fuse(parts, reference=('1/4', 60))

    def test_sequence_fuses_depth_first(self):
        seq = TemporalUnitSequence([
            TemporalUnit(tempus='3/20', prolatio='d', beat='1/4', bpm=60),
            TemporalUnit(tempus='3/20', prolatio='d', beat='1/4', bpm=60),
        ])
        head = TemporalUnit(tempus='6/20', prolatio='d', beat='1/4', bpm=60)
        out = fuse(head, seq)
        assert str(out.tempus) == '12/20'

    def test_block_refuses_loudly_naming_the_row_verb(self):
        bt = TemporalBlock([TemporalUnit(tempus='4/4', prolatio='p'),
                            TemporalUnit(tempus='4/4', prolatio='p')],
                           sort_rows=False)
        with pytest.raises(ValueError, match='row'):
            fuse(TemporalUnit(tempus='4/4', prolatio='p'), bt)

    def test_uc_is_the_staged_surface(self):
        uc = CompositionalUnit(tempus='4/4', prolatio='p')
        with pytest.raises(NotImplementedError, match='staged'):
            fuse(uc, uc)

    def test_untimed_operand_adopts_the_reference(self):
        # p. 97: the relative units' relativity takes precedence; the
        # absolute takes the shared reference verbatim
        ut = TemporalUnit(tempus='6/20', prolatio='d', beat='1/4', bpm=90)
        rt = RhythmTree(span=1, meas='3/20', subdivisions=(1,))
        out = fuse(ut, rt)
        assert str(out.tempus) == '9/20'
        assert out.bpm == 90

    def test_fusion_gives_a_leading_tie_its_predecessor(self):
        a = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        b = TemporalUnit(tempus='2/4', prolatio=(1.0, 1), beat='1/4', bpm=60)
        out = fuse(a, b)
        assert len(out) == 3  # a's last leaf + b's first are now one sound


class TestFuseAttribution:
    def test_unattributed_operands_stay_unattributed(self):
        # NEW-39's lift-rule wrinkle: the fused result keeps following
        # the future ambient dial
        a = TemporalUnit(tempus='6/20', prolatio='d')
        b = TemporalUnit(tempus='3/20', prolatio='d')
        out = fuse(a, b)
        assert 'beat' not in out.attributed and 'bpm' not in out.attributed
        assert 'tempus' in out.attributed

    def test_any_attributed_operand_attributes_the_result(self):
        a = TemporalUnit(tempus='6/20', prolatio='d', bpm=60)
        b = TemporalUnit(tempus='3/20', prolatio='d')
        assert 'bpm' in fuse(a, b).attributed

    def test_explicit_reference_attributes_both(self):
        a = TemporalUnit(tempus='6/20', prolatio='d')
        b = TemporalUnit(tempus='3/20', prolatio='d')
        out = fuse(a, b, reference=('1/4', 60))
        assert {'beat', 'bpm'} <= out.attributed


class TestConvolveContract:
    """ALG-5: the hardcoded '1/4' @ 60 reference is repealed (R13-B);
    signs and ties flow from the reworked decompose; zeros delete."""

    def test_reference_defaults_to_first_operand(self):
        from klotho.chronos.temporal_units.algorithms import convolve
        x = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=90)
        h = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=90)
        out = convolve(x, h)
        assert all(u.bpm == 90 and u.beat == Fraction(1, 4)
                   for u in out.seq)

    def test_same_reference_terms_are_raw_products(self):
        # identity reconciliation is a no-op (TEMPO-5), so the terms are
        # the plain metric products: (1/4)*(1/4) etc.
        from klotho.chronos.temporal_units.algorithms import convolve
        x = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        h = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        out = convolve(x, h)
        assert [u.tempus.to_fraction() for u in out.seq] == [
            Fraction(1, 16), Fraction(1, 8), Fraction(1, 16)]

    def test_rests_carry_sign_and_render_as_rests(self):
        from klotho.chronos.temporal_units.algorithms import convolve
        x = TemporalUnit(tempus='2/4', prolatio=(1, -1), beat='1/4', bpm=60)
        h = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        out = convolve(x, h)
        # y = [1/16, 0 (deleted), -1/16]
        assert len(out.seq) == 2
        assert out.seq[0]._rt[out.seq[0]._rt.leaf_nodes[0]]['proportion'] > 0
        assert out.seq[1]._rt[out.seq[1]._rt.leaf_nodes[0]]['proportion'] < 0

    def test_ties_shorten_the_operand(self):
        from klotho.chronos.temporal_units.algorithms import convolve
        x = TemporalUnit(tempus='3/4', prolatio=(1, 1.0, 1), beat='1/4', bpm=60)
        h = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        out = convolve(x, h)
        # x decomposes to 2 terms (the tie merges), so y_len = 2 + 2 - 1
        assert len(out.seq) == 3

    def test_explicit_reference_override(self):
        from klotho.chronos.temporal_units.algorithms import convolve
        x = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        h = TemporalUnit(tempus='2/4', prolatio=(1, 1), beat='1/4', bpm=60)
        out = convolve(x, h, reference=('1/8', 120))
        assert all(u.bpm == 120 and u.beat == Fraction(1, 8)
                   for u in out.seq)


class TestFlattenSurface:
    def test_flatten_ut_published_example(self):
        ut = TemporalUnit(tempus='3/4', prolatio=(2, 1, 1, 1), bpm=120)
        out = flatten(ut)
        assert str(out.tempus) == '15/20'
        assert out.prolationis == (6, 3, 3, 3)

    def test_flatten_sounds_identical(self):
        ut = TemporalUnit(tempus='3/4', prolatio=(2, 1, 1, 1), bpm=120)
        out = flatten(ut)
        assert out.onsets == pytest.approx(ut.onsets, abs=1e-12)
        assert out.durations == pytest.approx(ut.durations, abs=1e-12)

    def test_flatten_merges_ties(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        out = flatten(ut)
        assert out.prolationis == (2, 1, 1)
        assert len(out) == 3

    def test_flatten_rt_returns_rt(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(2, 1, 1, 1))
        assert isinstance(flatten(rt), RhythmTree)

    def test_flatten_uc_is_staged(self):
        with pytest.raises(NotImplementedError, match='staged'):
            flatten(CompositionalUnit(tempus='4/4', prolatio='p'))

    def test_flatten_sequence_points_at_fuse(self):
        seq = TemporalUnitSequence([TemporalUnit(tempus='4/4', prolatio='p')])
        with pytest.raises(TypeError, match='fuse'):
            flatten(seq)
