"""Barlow measures: indigestibility and harmonicity (MASTER_PLAN Stage A2.1).

Reference values from Barlow, *On the Quantification of Harmony and Metre*.
"""
import pytest

from klotho.tonos import indigestibility, harmonicity


class TestIndigestibility:
    @pytest.mark.parametrize("n, expected", [
        (1, 0.0),
        (2, 1.0),
        (3, 8 / 3),
        (4, 2.0),
        (5, 6.4),
        (6, 1.0 + 8 / 3),
        (9, 16 / 3),
    ])
    def test_published_values(self, n, expected):
        assert indigestibility(n) == pytest.approx(expected)

    def test_multiplicativity_over_factors(self):
        # xi(p^a * q^b) = a*xi(p) + b*xi(q)
        assert indigestibility(12) == pytest.approx(
            2 * indigestibility(2) + indigestibility(3))

    def test_rejects_nonpositive(self):
        with pytest.raises(ValueError):
            indigestibility(0)
        with pytest.raises(ValueError):
            indigestibility(-3)


class TestHarmonicity:
    def test_fifth_magnitude(self):
        assert abs(harmonicity('3/2')) == pytest.approx(0.2727, abs=1e-4)

    def test_unison_is_infinite(self):
        assert harmonicity(1) == float('inf')
        assert harmonicity('2/2') == float('inf')

    def test_polarity(self):
        # Barlow's canonical values: fifth 3/2 is otonal (+0.2727),
        # fourth 4/3 is utonal (-0.2143); inversion flips the sign.
        assert harmonicity('3/2') == pytest.approx(0.2727, abs=1e-4)
        assert harmonicity('4/3') == pytest.approx(-0.2143, abs=1e-4)
        assert harmonicity('3/2') == -harmonicity('2/3')

    def test_simpler_ratios_score_higher(self):
        assert abs(harmonicity('3/2')) > abs(harmonicity('5/4')) > abs(harmonicity('15/8'))

    def test_accepts_fraction_and_str(self):
        from fractions import Fraction
        assert harmonicity(Fraction(3, 2)) == harmonicity('3/2')

    def test_rejects_float(self):
        with pytest.raises(TypeError):
            harmonicity(1.5)
