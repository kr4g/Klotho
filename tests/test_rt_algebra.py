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
