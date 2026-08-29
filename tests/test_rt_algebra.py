"""The Chapter-4 symbolic algebra at RT level (HAD-ALG; ruling R13).

Conformance targets are Haddad's published figures (the established
pattern: behavioural agreement on published examples, never
implementation matching). The fixture spine:

- strict decomposition of 3/4 (2 1 1 1) => 6/20 3/20 3/20 3/20
  (figs 4.33/4.39 rule: numerator p_i * N, common denominator sum|p| * D)
- fuse(6/20, 3/20, 3/20, 3/20) => 15/20 (6 3 3 3) -- his published
  concatenation example, unreduced spelling kept
- flatten (his *reduction*): 3/4 (2 1 1 1) => 15/20 (6 3 3 3), the SAME
  sound (exact Fraction onsets/durations) in canonical one-level spelling
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree
from klotho.chronos.rhythm_trees import Meas
from klotho.chronos.rhythm_trees.algorithms import (
    measure_ratios,
    strict_decomposition,
)


class TestStrictDecomposition:
    """ALG-6: the shipped version did not preserve duration -- 3/4
    (2 1 1 1) returned terms summing to 3/5. The rule from his figs:
    numerator p_i * meas.numerator, common denominator sum|p| *
    meas.denominator; returned as Meas, because Fraction auto-reduces
    the common-denominator form out of existence."""

    def test_published_example_3_4(self):
        ratios = measure_ratios((2, 1, 1, 1))
        parts = strict_decomposition(ratios, Meas('3/4'))
        assert [str(p) for p in parts] == ['6/20', '3/20', '3/20', '3/20']

    def test_returns_meas_not_fraction(self):
        parts = strict_decomposition(measure_ratios((2, 1, 1, 1)), Meas('3/4'))
        assert all(isinstance(p, Meas) for p in parts)

    def test_duration_is_preserved(self):
        for s, meas in (((2, 1, 1, 1), '3/4'), ((1, 1, 1), '7/5'),
                        ((3, 1, 2), '6/8')):
            parts = strict_decomposition(measure_ratios(s), Meas(meas))
            total = sum((p.to_fraction() for p in parts), Fraction(0))
            assert total == Meas(meas).to_fraction()

    def test_common_denominator_form(self):
        parts = strict_decomposition(measure_ratios((2, 1, 1, 1)), Meas('3/4'))
        assert len({p.denominator for p in parts}) == 1

    def test_rests_keep_their_sign(self):
        parts = strict_decomposition(measure_ratios((2, -1, 1)), Meas('4/4'))
        assert parts[1].numerator < 0
        total = sum((abs(p).to_fraction() for p in parts), Fraction(0))
        assert total == Fraction(1)


from klotho.chronos.rhythm_trees.algorithms import (  # noqa: E402
    decompose as rt_decompose,
    fuse as rt_fuse,
    flatten as rt_flatten,
)


class TestRTDecompose:
    """LAYER-2: the RT-level sibling that ALG-1 (signs) and ALG-2 (ties)
    live on. Returns RhythmTrees — nothing temporalised."""

    def test_leaves_become_fundamental_trees(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(2, 1, 1, 1))
        parts = rt_decompose(rt)
        assert [str(p.meas) for p in parts] == ['3/10', '3/20', '3/20', '3/20']
        assert all(isinstance(p, RhythmTree) for p in parts)

    def test_rests_come_back_sign_carrying(self):
        # ALG-1: the sign lives in the S (a negative term is a
        # rest-encoded S at RT level)
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1))
        parts = rt_decompose(rt)
        assert parts[1].subdivisions == (-1,)
        assert parts[1].meas.numerator > 0

    def test_tie_groups_fuse_into_one_part(self):
        # ALG-2 per charter sect9: iterate tie GROUPS; group tempus =
        # unreduced raw-int sum on the common denominator
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        parts = rt_decompose(rt)
        assert len(parts) == 3
        assert str(parts[0].meas) == '2/4'   # 1/4 + 1/4, unreduced

    def test_group_tempus_sum_is_unreduced_across_denominators(self):
        # the sect9 arithmetic shape: 16/21 + 32/35 = 80/105 + 96/105
        # = 176/105 — why Haddad's [x] is 10 units, not 11
        a, b = Fraction(16, 21), Fraction(32, 35)
        rt = RhythmTree.from_ratios((a, b))
        rt.set_node_data(rt.leaf_nodes[1], tied=True)
        parts = rt_decompose(rt)
        assert len(parts) == 1
        assert str(parts[0].meas) == '176/105'

    def test_cross_branch_group(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(1, (2, (1.0, 1)), 1))
        parts = rt_decompose(rt)
        assert len(parts) == 3

    def test_decomposition_preserves_total_duration(self):
        rt = RhythmTree(span=1, meas='7/5', subdivisions=(3, (2, (1, 1.0)), -1))
        parts = rt_decompose(rt)
        total = sum((abs(p.meas).to_fraction() for p in parts), Fraction(0))
        assert total == Fraction(7, 5)


class TestFuse:
    """ALG-3, his ‖ (a fold, not concatenation — R13-G). Conformance:
    the published 6/20 ‖ 3/20 ‖ 3/20 ‖ 3/20 => 15/20 (6 3 3 3)."""

    def test_published_example(self):
        parts = [RhythmTree(span=1, meas=m, subdivisions=(1,))
                 for m in ('6/20', '3/20', '3/20', '3/20')]
        out = rt_fuse(parts)
        assert str(out.meas) == '15/20'
        assert out.subdivisions == (6, 3, 3, 3)

    def test_leaf_durations_exact(self):
        parts = [RhythmTree(span=1, meas=m, subdivisions=(1,))
                 for m in ('6/20', '3/20', '3/20', '3/20')]
        out = rt_fuse(parts)
        assert out.durations == (Fraction(3, 10), Fraction(3, 20),
                                 Fraction(3, 20), Fraction(3, 20))

    def test_mixed_denominators_are_legal(self):
        # sect4.4.6.5: same-denominator is NOT a validity precondition —
        # variable denominators yield a complex composed unit
        parts = [RhythmTree(span=1, meas='12/5', subdivisions=(1,)),
                 RhythmTree(span=1, meas='5/12', subdivisions=(1,))]
        out = rt_fuse(parts)
        assert str(out.meas) == '169/60'  # the 2008 paper's own example

    def test_composed_operands_nest(self):
        parts = [RhythmTree(span=1, meas='6/20', subdivisions=(2, 1)),
                 RhythmTree(span=1, meas='3/20', subdivisions=(1,))]
        out = rt_fuse(parts)
        assert str(out.meas) == '9/20'
        assert out.subdivisions == ((6, (2, 1)), 3)

    def test_rest_operands_keep_their_sign(self):
        parts = [RhythmTree(span=1, meas='1/4', subdivisions=(1,)),
                 RhythmTree(span=1, meas='1/4', subdivisions=(-1,))]
        out = rt_fuse(parts)
        assert out.subdivisions == (1, -1)
        assert str(out.meas) == '2/4'

    def test_span_folds_in(self):
        parts = [RhythmTree(span=2, meas='3/20', subdivisions=(1,)),
                 RhythmTree(span=1, meas='3/20', subdivisions=(1,))]
        out = rt_fuse(parts)
        assert str(out.meas) == '9/20'


class TestFlatten:
    """ALG-4, his *réduction* — a PROJECTION onto canonical one-level
    form (sum(prolatio) = tempus numerator), idempotent, a no-op exactly
    on already-canonical input. NOT gcd-reduction (hence not `reduce`)."""

    def test_published_example(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(2, 1, 1, 1))
        out = rt_flatten(rt)
        assert str(out.meas) == '15/20'
        assert out.subdivisions == (6, 3, 3, 3)

    def test_same_sound(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(2, 1, 1, 1))
        out = rt_flatten(rt)
        assert out.durations == rt.durations
        assert out.onsets == rt.onsets

    def test_idempotent(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(2, 1, 1, 1))
        once = rt_flatten(rt)
        twice = rt_flatten(once)
        assert str(twice.meas) == str(once.meas)
        assert twice.subdivisions == once.subdivisions

    def test_noop_on_canonical_input(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        out = rt_flatten(rt)
        assert str(out.meas) == '4/4'
        assert out.subdivisions == (1, 1, 1, 1)

    def test_ties_flatten_to_one_term(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        out = rt_flatten(rt)
        assert str(out.meas) == '4/4'
        assert out.subdivisions == (2, 1, 1)

    def test_nested_with_rest(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(1, (2, (1, -1)), 1))
        out = rt_flatten(rt)
        total = sum(abs(s) for s in out.subdivisions)
        assert total == out.meas.numerator
        assert out.durations == rt.durations
