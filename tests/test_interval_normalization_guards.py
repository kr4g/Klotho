"""
Reduction used to HANG on input it cannot reduce, instead of refusing it.

``equave_reduce``, ``reduce_interval``, ``reduce_interval_relative`` and
``reduce_freq`` all walk a value into range with ``while x < bound: x *=
equave``. Zero stays zero however many times you multiply it, and a negative
number never climbs, so the loop spun forever -- no exception, no traceback,
no output. A composer whose generative code produced a ``0`` ratio (an empty
product, a division that collapsed) got a frozen notebook kernel and no clue
why.

A degenerate *equave* is the same defect from the other side: an equave of 1
never moves the value, and an equave of 0 or less never moves it consistently
upward.

Measured before the guards, each aborted by a one-second alarm::

    equave_reduce(0)                  -> HANG
    equave_reduce(-1.5)               -> HANG
    reduce_interval(0)                -> HANG
    reduce_interval_relative(0, 1)    -> HANG
    reduce_interval_relative(1, 0)    -> HANG
    reduce_freq(0.0)                  -> HANG
    equave_reduce(4, equave=1)        -> HANG
    equave_reduce(4, equave=-2)       -> HANG
    reduce_freq(10.0, equave=1)       -> HANG
    Scale(["0/1", "3/2"])             -> HANG
    Scale([0.0, 1.5])                 -> HANG

Every test here asserts a ``ValueError``, which is immediate. None of them
waits on a timeout: a test that waits for a hang would hang the suite.
"""

from fractions import Fraction

import pytest

from klotho.tonos import Scale, Chord
from klotho.tonos.utils.interval_normalization import (
    equave_reduce,
    reduce_freq,
    reduce_interval,
    reduce_interval_relative,
    reduce_sequence_relative,
)


class TestNonPositiveIntervalRefused:
    @pytest.mark.parametrize("bad", [0, "0/1", Fraction(0, 1), -1.5, -2, Fraction(-3, 2)])
    def test_equave_reduce(self, bad):
        with pytest.raises(ValueError):
            equave_reduce(bad)

    @pytest.mark.parametrize("bad", [0, -1.5])
    def test_equave_reduce_non_octave_equave(self, bad):
        # The octave fast path already guarded `interval > 0` and then fell
        # through into the unguarded slow loop, so a non-octave equave hung
        # on exactly the same input.
        with pytest.raises(ValueError):
            equave_reduce(bad, equave=3)

    @pytest.mark.parametrize("bad", [0, "0/1", -1.5])
    def test_reduce_interval(self, bad):
        with pytest.raises(ValueError):
            reduce_interval(bad)

    def test_reduce_interval_relative_target(self):
        with pytest.raises(ValueError):
            reduce_interval_relative(0, 1)

    def test_reduce_interval_relative_source(self):
        with pytest.raises(ValueError):
            reduce_interval_relative(1, 0)

    def test_reduce_sequence_relative_inherits_the_guard(self):
        with pytest.raises(ValueError):
            reduce_sequence_relative([1, 0, 2])

    @pytest.mark.parametrize("bad", [0.0, -100.0])
    def test_reduce_freq(self, bad):
        with pytest.raises(ValueError):
            reduce_freq(bad)

    def test_the_message_names_the_remedy(self):
        with pytest.raises(ValueError) as excinfo:
            equave_reduce(0)
        message = str(excinfo.value)
        assert "0" in message
        assert "positive" in message


class TestDegenerateEquaveRefused:
    @pytest.mark.parametrize("bad", [1, 0, -2, Fraction(1, 2), "1/1"])
    def test_equave_reduce(self, bad):
        with pytest.raises(ValueError):
            equave_reduce(4, equave=bad)

    @pytest.mark.parametrize("bad", [1, 0, Fraction(1, 2)])
    def test_reduce_interval(self, bad):
        with pytest.raises(ValueError):
            reduce_interval(4, equave=bad)

    @pytest.mark.parametrize("bad", [1, 0, Fraction(1, 2)])
    def test_reduce_interval_relative(self, bad):
        with pytest.raises(ValueError):
            reduce_interval_relative(Fraction(1, 4), 1, equave=bad)

    @pytest.mark.parametrize("bad", [1, 0, Fraction(1, 2)])
    def test_reduce_freq(self, bad):
        with pytest.raises(ValueError):
            reduce_freq(10.0, equave=bad)

    def test_the_message_names_the_remedy(self):
        with pytest.raises(ValueError) as excinfo:
            equave_reduce(4, equave=1)
        message = str(excinfo.value)
        assert "greater than 1" in message


class TestScaleAndChordRefuseInsteadOfHanging:
    """The freeze reached users through the collection constructors."""

    def test_scale_zero_ratio_degree(self):
        with pytest.raises(ValueError):
            Scale(["0/1", "3/2"])

    def test_scale_zero_float_degree(self):
        # The float path never calls equave_reduce -- it carries its own copy
        # of the same loop -- so guarding the helpers alone left this frozen.
        with pytest.raises(ValueError):
            Scale([0.0, 1.5])

    def test_scale_negative_float_degree(self):
        with pytest.raises(ValueError):
            Scale([-2.0, 1.5])

    def test_scale_unison_equave(self):
        with pytest.raises(ValueError):
            Scale(["1/1", "3/2"], equave="1/1")

    def test_scale_unison_equave_float_degrees(self):
        with pytest.raises(ValueError):
            Scale([1.0, 1.5], equave=1.0)

    def test_chord_zero_ratio_degree(self):
        with pytest.raises(ValueError):
            Chord(["0/1", "3/2"])

    def test_chord_zero_float_degree(self):
        with pytest.raises(ValueError):
            Chord([0.0, 1.5])


class TestValidInputStillReduces:
    """The guards must refuse only what could not terminate."""

    def test_octave_fast_path(self):
        assert equave_reduce(Fraction(5, 1)) == Fraction(5, 4)
        assert equave_reduce(Fraction(1, 3)) == Fraction(4, 3)
        assert equave_reduce(Fraction(3, 2)) == Fraction(3, 2)

    def test_non_octave_equave(self):
        assert equave_reduce(Fraction(9, 1), equave=3) == Fraction(1, 1)
        assert equave_reduce(Fraction(1, 2), equave=3) == Fraction(3, 2)

    def test_reduce_interval_bipolar_window(self):
        assert reduce_interval(Fraction(5, 1)) == Fraction(5, 4)
        assert reduce_interval(Fraction(1, 3)) == Fraction(2, 3)

    def test_reduce_interval_relative(self):
        assert reduce_interval_relative(Fraction(3, 2), Fraction(6, 1)) == Fraction(6, 1)

    def test_reduce_freq(self):
        assert reduce_freq(10.0) == pytest.approx(40.0)
        assert reduce_freq(440.0) == pytest.approx(440.0)

    def test_scale_and_chord_still_build(self):
        assert Scale(["1/1", "5/4", "3/2"]).degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)
        ]
        assert Scale([1.0, 1.25, 1.5]).degrees == pytest.approx([1.0, 1.25, 1.5])
        assert Chord(["1/1", "5/4", "3/2"]).degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)
        ]
        assert Chord([1.0, 1.25, 1.5]).degrees == pytest.approx([1.0, 1.25, 1.5])
