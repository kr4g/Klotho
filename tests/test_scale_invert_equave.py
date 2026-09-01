"""
``~scale`` mirrored every ratio about the octave, whatever the scale's equave.

The ratios branch of ``Scale.__invert__`` built each inverted degree as
``Fraction(d.denominator * 2, d.numerator)`` -- that is ``2 / d``, with the 2
written in as a literal. The cents branch of the same method already mirrored
about ``self._equave``, so the two halves of one operator disagreed about what
inversion means, and the disagreement was silent: a Bohlen-Pierce or
tritave-equave scale came back with plausible-looking ratios that were the
wrong notes.

Measured before the fix::

    Scale(["1/1", "5/4", "3/2"], equave="3/1")   equave: 3
    ~scale -> [1/1, 4/3, 8/5]                    # 2/d, then re-housed in 3/1
    expected -> [1/1, 2/1, 12/5]                 # 3/d

The same line assumed every degree was a ``Fraction``. ``_process_scale_degrees``
keeps floats as floats when any input degree is a float, so::

    Scale([1.0, 1.25, 1.5])
    ~scale -> AttributeError: 'float' object has no attribute 'denominator'
"""

import math
from fractions import Fraction

import pytest

from klotho.tonos import Scale


def _cents(ratio):
    return 1200.0 * math.log2(float(ratio))


class TestInvertMirrorsAboutTheScaleEquave:
    def test_octave_scale_is_unchanged_by_the_fix(self):
        # The literal 2 was right for the octave, and must stay right.
        scale = Scale(["1/1", "5/4", "3/2"])
        assert (~scale).degrees == [Fraction(1, 1), Fraction(4, 3), Fraction(8, 5)]

    def test_tritave_scale_mirrors_about_three(self):
        scale = Scale(["1/1", "5/4", "3/2"], equave="3/1")
        assert (~scale).degrees == [Fraction(1, 1), Fraction(2, 1), Fraction(12, 5)]

    def test_every_inverted_degree_is_equave_over_degree(self):
        scale = Scale(["1/1", "9/8", "7/5", "5/3"], equave="3/1")
        expected = sorted(
            [Fraction(1, 1)]
            + [Fraction(3, 1) / d for d in scale.degrees if d != Fraction(1, 1)]
        )
        assert (~scale).degrees == expected

    def test_invert_is_an_involution_under_a_non_octave_equave(self):
        scale = Scale(["1/1", "5/4", "3/2"], equave="3/1")
        assert (~~scale).degrees == scale.degrees

    def test_ratio_inversion_agrees_with_cents_inversion(self):
        # The cents branch was always equave-aware. Mirroring the same scale
        # both ways must now land on the same pitches; before the fix the
        # ratios branch was 700 cents adrift on the tritave.
        tritave_cents = _cents(Fraction(3, 1))
        ratios = Scale(["1/1", "5/4", "3/2"], equave="3/1")
        cents = Scale([_cents(d) for d in ratios.degrees],
                      interval_type="cents", equave=tritave_cents)
        from_ratios = sorted(_cents(d) for d in (~ratios).degrees)
        from_cents = sorted((~cents).degrees)
        assert from_ratios == pytest.approx(from_cents, abs=1e-6)

    def test_neg_follows_invert(self):
        scale = Scale(["1/1", "5/4", "3/2"], equave="3/1")
        assert (-scale).degrees == (~scale).degrees

    def test_inverted_scale_keeps_its_equave_and_reference(self):
        scale = Scale(["1/1", "5/4", "3/2"], equave="3/1", reference_pitch="A4")
        inverted = ~scale
        assert inverted.equave == Fraction(3, 1)
        assert inverted.reference_pitch.freq == pytest.approx(scale.reference_pitch.freq)


class TestInvertHandlesFloatDegrees:
    def test_float_degrees_no_longer_raise(self):
        scale = Scale([1.0, 1.25, 1.5])
        inverted = ~scale
        assert all(isinstance(d, float) for d in inverted.degrees)
        assert inverted.degrees == pytest.approx([1.0, 4 / 3, 1.6])

    def test_float_degrees_under_a_non_octave_equave(self):
        scale = Scale([1.0, 1.25, 1.5], equave=Fraction(3, 1))
        assert (~scale).degrees == pytest.approx([1.0, 2.0, 2.4])

    def test_float_degrees_stay_an_involution(self):
        scale = Scale([1.0, 1.25, 1.5], equave=Fraction(3, 1))
        assert (~~scale).degrees == pytest.approx(scale.degrees)


class TestCentsBranchUnchanged:
    def test_octave_cents_scale(self):
        scale = Scale([0, 100, 400, 700], interval_type="cents")
        assert (~scale).degrees == pytest.approx([0.0, 500.0, 800.0, 1100.0])

    def test_non_octave_cents_scale(self):
        scale = Scale([0, 100, 400, 700], interval_type="cents", equave=1902.0)
        assert (~scale).degrees == pytest.approx([0.0, 1202.0, 1502.0, 1802.0])
