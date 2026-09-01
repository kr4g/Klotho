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

A near-unison *equave* is the same defect once removed. The degenerate guard
asks only ``equave > 1``, so an equave a hair *above* 1 passes it and then
spins practically forever: reduction divides one equave at a time, and in
exact rational arithmetic each division adds about one equave's worth of bits
to the numbers. Measured 2026-09-01::

    equave_reduce(Fraction(3, 2), equave=Fraction(1000001, 1000000))
                                      -> no result after 120 s

``Scale`` and ``Chord`` now price the reduction before running any of it
(``check_reduction_cost``), so a near-unison equave refuses immediately in
both modes. STILL OPEN: ``equave_reduce``, ``reduce_interval``,
``reduce_interval_relative`` and ``ToneLattice._custom_equave_reduce`` are
reachable directly and still carry only the ``> 1`` guard, so calling them
with a near-unison equave still hangs.

The cost guard also fixes a second symptom that is worse than a hang, because
nothing looks wrong until someone prints the result. On HEAD::

    Scale(["1/1", "3/2"], equave=Fraction(10001, 10000))
        -> constructs; the second degree's numerator is 13,815 bits, and
           repr() then raises "Exceeds the limit (4300 digits) for integer
           string conversion"
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
        """RESTORED 2026-09-01. ``equave=1.0`` IS the unison.

        A previous pass changed this test to expect success, on a convention
        (a float equave means CENTS, so ``1.0`` asks for a one-cent equave)
        that the project owner then superseded: for ``Scale``, ``Chord``,
        ``Voicing`` and ``RelativePitchCollection`` the declared
        ``interval_type`` decides, not the Python type. In the default
        ``ratios`` mode every spelling of the equave is a RATIO, so ``1.0``,
        ``1``, ``'1/1'`` and ``Fraction(1, 1)`` are all the unison and all
        refuse. See tests/test_scale_chord_equave_mode_convention.py.

        The float-degree branch is kept as its own case because it carries a
        separate copy of the reduction loop from the Fraction branch above.
        """
        for unison in (1.0, 1, "1/1", Fraction(1, 1)):
            with pytest.raises(ValueError, match="greater than 1"):
                Scale([1.0, 1.5], equave=unison)

    def test_scale_near_unison_equave_is_refused_before_it_can_appear_to_hang(self):
        """An equave just ABOVE the unison passes the degenerate guard.

        It terminates in principle and is useless in practice. At one cent a
        3/2 takes 701 divisions and lands on a 13,699-bit numerator -- 4,124
        decimal digits, at the edge of what CPython will print; a thousandth
        of a cent takes 700,000 and returned nothing in 120 seconds. Both are
        the symptom this module exists to prevent, so the cost of the
        reduction is priced before any of it runs.
        """
        for equave in (Fraction(1000001, 1000000), 1.000001, Fraction(10001, 10000)):
            with pytest.raises(ValueError, match="too close to the unison"):
                Scale([1.0, 1.5], equave=equave)
            with pytest.raises(ValueError, match="too close to the unison"):
                Scale(["1/1", "3/2"], equave=equave)

    def test_scale_near_unison_equave_in_cents_mode_too(self):
        """Cents mode subtracts rather than divides, so it does not build
        enormous numbers -- but a billion float subtractions per degree still
        freezes the interpreter."""
        with pytest.raises(ValueError, match="too close to the unison"):
            Scale([0.0, 700.0], "cents", equave=1e-9)

    def test_a_real_comma_sized_equave_is_still_allowed(self):
        """The guard prices work; it is not a floor on musical size. The
        syntonic comma (21.5 cents) and the Pythagorean comma (23.5 cents)
        are real intervals people build lattices on, and both pass.
        """
        for comma in (Fraction(81, 80), Fraction(531441, 524288)):
            assert repr(Scale(["1/1", "3/2"], equave=comma))

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
