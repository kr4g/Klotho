"""OPS-6 — `Meas` arithmetic, pinned.

`Meas` has shipped ``+ - * /`` since the beginning and the docket asserts it
"implements them faithfully". That claim was UNVERIFIED: before this file no
test in the suite performed a single `Meas` arithmetic operation (every other
mention is as an expected value, an argument, or an import).

The behaviour is not uniform, and the difference is load-bearing for every
caller that builds a Tempus:

- ``+`` / ``-`` cancel the DENOMINATORS only (they land on the lcm
  denominator and never cancel the numerator against it), so they preserve
  the unreduced spelling `Meas` exists to protect;
- ``*`` / ``/`` gcd-reduce the whole result, so they respell EVEN AT
  IDENTITY -- ``Meas(6, 20) * 1`` comes back 3/10.

That last line is why the tempus arithmetic in `modulate_tempo`, `fuse` and
`TemporalUnit.__mul__` assembles raw ints instead of routing through
``Meas.__mul__`` (TEMPO-5 / ruling R13-D; reducing a Tempus changes the
unit's *nature*, Haddad sect4.4.2/4.4.5).

These are characterization pins: they record what ships today so that a
future change to either half is caught deliberately rather than silently.
"""

from fractions import Fraction

import pytest

from klotho.chronos.rhythm_trees import Meas


class TestAddPreservesSpelling:
    """``+`` cancels denominators only -- never num against den."""

    def test_like_denominators_do_not_reduce(self):
        assert Meas(3, 4) + Meas(3, 4) == Meas(6, 4)  # not 3/2

    def test_adding_zero_is_a_true_no_op_on_spelling(self):
        assert Meas(6, 20) + Meas(0, 20) == Meas(6, 20)  # not 3/10

    def test_unlike_denominators_land_on_the_lcm(self):
        assert Meas(3, 4) + Meas(1, 8) == Meas(7, 8)

    def test_quarter_plus_quarter_stays_in_quarters(self):
        assert Meas(1, 4) + Meas(1, 4) == Meas(2, 4)  # not 1/2

    def test_fraction_operand(self):
        assert Meas(3, 4) + Fraction(1, 4) == Meas(4, 4)

    def test_int_operand_scales_by_the_denominator(self):
        assert Meas(3, 4) + 1 == Meas(7, 4)

    def test_str_operand(self):
        assert Meas(3, 4) + '1/4' == Meas(4, 4)

    def test_radd_from_int(self):
        assert 1 + Meas(3, 4) == Meas(7, 4)

    def test_unsupported_operand_is_not_implemented(self):
        with pytest.raises(TypeError):
            Meas(3, 4) + object()


class TestSubPreservesSpelling:
    def test_like_denominators_do_not_reduce(self):
        assert Meas(3, 4) - Meas(1, 4) == Meas(2, 4)  # not 1/2

    def test_unlike_denominators_land_on_the_lcm(self):
        assert Meas(3, 4) - Meas(1, 8) == Meas(5, 8)

    def test_int_operand(self):
        assert Meas(7, 4) - 1 == Meas(3, 4)

    def test_rsub_from_int(self):
        assert 2 - Meas(3, 4) == Meas(5, 4)

    def test_result_may_be_negative(self):
        assert Meas(1, 4) - Meas(3, 4) == Meas(-2, 4)


class TestMulReduces:
    """``*`` gcd-reduces. This is the hazard, pinned as a hazard."""

    def test_identity_respells_the_tempus(self):
        # the sharpest demonstration: multiplying by 1 is NOT a no-op
        assert Meas(6, 20) * Fraction(1, 1) == Meas(3, 10)
        assert Meas(6, 20) * Fraction(1, 1) != Meas(6, 20)

    def test_four_four_times_a_third(self):
        assert Meas(4, 4) * Fraction(1, 3) == Meas(1, 3)  # value-right, 4/12 unwritten

    def test_four_four_times_three_halves(self):
        assert Meas(4, 4) * Fraction(3, 2) == Meas(3, 2)  # not 12/8

    def test_int_operand_reduces_too(self):
        assert Meas(4, 4) * 2 == Meas(2, 1)  # not 8/4

    def test_meas_operand(self):
        assert Meas(3, 4) * Meas(2, 3) == Meas(1, 2)

    def test_rmul_matches_mul(self):
        assert 2 * Meas(4, 4) == Meas(4, 4) * 2

    def test_value_is_always_correct_even_though_spelling_is_not(self):
        for m, k in [(Meas(6, 20), Fraction(1, 1)),
                     (Meas(4, 4), Fraction(3, 2)),
                     (Meas(7, 8), Fraction(2, 5))]:
            assert (m * k).to_fraction() == m.to_fraction() * k


class TestTrueDivReduces:
    def test_int_divisor(self):
        assert Meas(4, 4) / 2 == Meas(1, 2)  # not 4/8

    def test_fraction_divisor(self):
        assert Meas(4, 4) / Fraction(3, 2) == Meas(2, 3)  # not 8/12

    def test_identity_respells(self):
        assert Meas(6, 20) / Fraction(1, 1) == Meas(3, 10)

    def test_division_by_zero_int(self):
        with pytest.raises(ZeroDivisionError):
            Meas(4, 4) / 0

    def test_division_by_zero_fraction(self):
        with pytest.raises(ZeroDivisionError):
            Meas(4, 4) / Fraction(0, 1)

    def test_rtruediv_from_int(self):
        assert 1 / Meas(4, 4) == Meas(1, 1)

    def test_rtruediv_into_zero_numerator(self):
        with pytest.raises(ZeroDivisionError):
            1 / Meas(0, 4)

    def test_value_is_always_correct(self):
        assert (Meas(7, 8) / Fraction(2, 5)).to_fraction() == Fraction(7, 8) / Fraction(2, 5)


class TestEqualityAndSpelling:
    def test_eq_is_strict_on_spelling(self):
        assert Meas(4, 4) != Meas(2, 2)

    def test_is_equivalent_compares_value(self):
        assert Meas(4, 4).is_equivalent(Meas(2, 2))
        assert Meas(6, 20).is_equivalent(Meas(3, 10))

    def test_reduced_is_the_explicit_opt_in(self):
        assert Meas(6, 20).reduced() == Meas(3, 10)

    def test_neg_keeps_the_denominator(self):
        assert -Meas(6, 20) == Meas(-6, 20)

    def test_abs_keeps_the_denominator(self):
        assert abs(Meas(-6, 20)) == Meas(6, 20)

    def test_zero_denominator_raises(self):
        with pytest.raises(ValueError):
            Meas(4, 0)
