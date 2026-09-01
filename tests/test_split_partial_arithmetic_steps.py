"""R27. ``split_partial`` divides arithmetically, not by equal ratios.

The docstring promised "a sequence of *n + 1* integers where each adjacent
pair forms the same ratio", and its own worked example refuted that two lines
below: ``split_partial('3/2', 2)`` returns ``[4, 5, 6]``, whose steps are
``5/4`` (386.31 cents) and ``6/5`` (315.64 cents) -- 70.67 cents apart, more
than a third of a semitone. The algorithm is right; the sentence described
equal temperament instead of the harmonic series.

Two things are pinned here. The arithmetic, so the docstring can be checked
against behaviour rather than against itself; and the absence of the refuted
sentence, so the wrong claim cannot come back unnoticed. The prose test is
the one that was red before the wording was fixed.
"""

import inspect
from fractions import Fraction

import pytest

from klotho.tonos.utils.intervals import ratio_to_cents, split_partial


CASES = [
    ("3/2", 2),
    ("3/2", 3),
    ("2/1", 2),
    ("2/1", 4),
    ("5/4", 2),
    ("7/4", 3),
    ("9/8", 2),
    ("5/1", 2),
    ("7/1", 3),
]


class TestTheStepsAreArithmeticallyEqual:
    @pytest.mark.parametrize("interval,n", CASES)
    def test_adjacent_members_differ_by_a_constant_amount(self, interval, n):
        h = split_partial(interval, n).harmonics
        diffs = [h[i + 1] - h[i] for i in range(len(h) - 1)]
        assert len(set(diffs)) == 1, f"{interval} /{n}: additive steps {diffs} are not constant"
        assert diffs[0] >= 1

    @pytest.mark.parametrize("interval,n", CASES)
    def test_the_result_spans_exactly_the_target_interval(self, interval, n):
        h = split_partial(interval, n).harmonics
        assert len(h) == n + 1
        assert Fraction(h[-1], h[0]) == Fraction(interval)

    @pytest.mark.parametrize("interval,n", CASES)
    def test_k_is_the_first_member(self, interval, n):
        result = split_partial(interval, n)
        assert result.k == result.harmonics[0]


class TestTheStepsAreNotEqualRatios:
    """The claim the old docstring made, disproved on every case that has
    room to disagree. ``n == 1`` is excluded only because one step cannot
    differ from itself."""

    @pytest.mark.parametrize("interval,n", CASES)
    def test_adjacent_ratios_are_not_all_the_same(self, interval, n):
        h = split_partial(interval, n).harmonics
        ratios = {Fraction(h[i + 1], h[i]) for i in range(len(h) - 1)}
        assert len(ratios) > 1, (
            f"{interval} /{n}: expected unequal ratio steps, got {ratios}"
        )

    def test_the_worked_example_is_off_by_more_than_a_third_of_a_semitone(self):
        h = split_partial("3/2", 2).harmonics
        assert h == [4, 5, 6]
        first = float(ratio_to_cents(Fraction(5, 4)))
        second = float(ratio_to_cents(Fraction(6, 5)))
        assert first == pytest.approx(386.3137, abs=1e-3)
        assert second == pytest.approx(315.6413, abs=1e-3)
        assert abs(first - second) == pytest.approx(70.6724, abs=1e-3)

    @pytest.mark.parametrize("interval,n", [c for c in CASES if c[1] > 2])
    def test_measured_in_cents_the_steps_shrink_as_the_numbers_rise(self, interval, n):
        h = split_partial(interval, n).harmonics
        cents = [float(ratio_to_cents(Fraction(h[i + 1], h[i]))) for i in range(len(h) - 1)]
        assert cents == sorted(cents, reverse=True)


class TestThePartialsAreNotAlwaysConsecutive:
    """"Consecutive harmonics" is the common case, not the rule: the common
    difference is 1 only when the search finds no smaller start with a larger
    step."""

    def test_a_common_difference_above_one(self):
        assert split_partial("5/1", 2).harmonics == [1, 3, 5]
        assert split_partial("4/1", 2).harmonics == [2, 5, 8]
        assert split_partial("9/1", 2).harmonics == [1, 5, 9]


class TestTheDocstringNoLongerClaimsEqualRatios:
    """The wording is the artifact under test here, so it is read directly."""

    def test_the_refuted_sentence_is_gone(self):
        doc = inspect.getdoc(split_partial)
        assert "forms the same ratio" not in doc
        assert "same ratio" not in doc

    def test_it_says_the_steps_are_arithmetic(self):
        doc = inspect.getdoc(split_partial).lower()
        assert "arithmetic" in doc

    def test_it_does_not_say_bare_equal_steps(self):
        """"n equal steps" was the same lie in shorter form: equal in what?"""
        doc = inspect.getdoc(split_partial).lower()
        assert "equal steps" not in doc
        assert "equal subdivisions" not in doc
