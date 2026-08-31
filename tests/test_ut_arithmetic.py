"""OPS-6 — magnitude scaling on `TemporalUnit` (``ut * k``, ``ut / k``).

`Meas` has shipped arithmetic since the beginning; `TemporalUnit` had none.
``ut * Fraction(3, 2)`` now means "make this unit half again as long", and it
does that the only way the doctrine allows: by REWRITING THE TEMPUS, leaving
the bpm untouched.

THE HOMOTHETIA TRAP -- the reason this file exists. There are two ways to
make a unit last 1.5x longer, and they are audibly indistinguishable:

    source          : 4/4 (2 1 2)  beat 1/4  bpm 60   duration 4.0
    bpm-scaled      : 4/4 (2 1 2)  beat 1/4  bpm 40   duration 6.0
    tempus-rewritten: 12/8 (2 1 2) beat 1/4  bpm 60   duration 6.0
    events, both    : [(0.0, 2.4), (2.4, 1.2), (3.6, 2.4)]  <- byte-identical

No listening test can tell them apart; they are different objects on the
page. In a thesis about *l'écriture de la durée* ("the writing of duration")
the notation IS the point, so the standing fence (GEN-1/GEN-5/OPS-6) requires
the tempus rewrite. `test_bpm_is_never_touched` is the test that catches a
regression to the bpm rescale -- without it the item can silently invert
while every audible check still passes.

The tempus is assembled from RAW INTS (TEMPO-5 / ruling R13-D), never through
``Meas.__mul__``, which gcd-reduces even at identity (6/20 -> 3/10; see
tests/test_meas_arithmetic.py). So ``ut * 1`` is a true no-op on spelling,
matching `modulate_tempo`'s identity guarantee.

Not tested here because deliberately not implemented: ``__add__``/``__sub__``
(`fuse` already ships the binary unit-to-unit combiner and PRESERVES both
prolationes; a lossy ``+`` would shadow it) and ``__imul__`` (an in-place
*follows* would mix both halves of TEMPO-1's axis in one operator).
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence
from klotho.chronos.rhythm_trees import Meas
from klotho.thetos.composition.compositional import CompositionalUnit


def src():
    """The trap's exhibit: 4/4 (2 1 2) at quarter = 60, duration 4.0."""
    return TemporalUnit(tempus='4/4', prolatio=(2, 1, 2), beat='1/4', bpm=60)


class TestTheHomothetiaTrap:
    def test_bpm_is_never_touched(self):
        # THE test. A bpm rescale reaches the same sound and the wrong page.
        ut = src()
        out = ut * Fraction(3, 2)
        assert out.bpm == 60
        assert out.bpm == ut.bpm
        assert type(out.bpm) is type(ut.bpm)

    def test_beat_is_never_touched(self):
        ut = src()
        out = ut * Fraction(3, 2)
        assert out.beat == ut.beat == Fraction(1, 4)

    def test_the_tempus_carries_the_scaling(self):
        assert (src() * Fraction(3, 2)).tempus == Meas(12, 8)

    def test_notation_and_duration_both_move(self):
        ut = src()
        out = ut * Fraction(3, 2)
        assert out.tempus != ut.tempus
        assert out.duration == pytest.approx(6.0)
        assert ut.duration == pytest.approx(4.0)

    def test_duration_scales_by_the_factor(self):
        ut = src()
        for k in [Fraction(3, 2), Fraction(1, 3), Fraction(7, 5), Fraction(1, 1)]:
            assert (ut * k).duration == pytest.approx(float(ut.duration * k))


class TestRawIntDiscipline:
    """TEMPO-5: no gcd reduction anywhere in the tempus."""

    def test_identity_is_a_true_no_op_on_spelling(self):
        # `Meas(6, 20) * 1` is 3/10; the unit scaler must not be
        ut = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        assert (ut * Fraction(1, 1)).tempus == Meas(6, 20)

    def test_identity_preserves_duration_bit_for_bit(self):
        ut = TemporalUnit(tempus='6/20', prolatio=(2, 1, 1), beat='1/4', bpm=60)
        assert (ut * Fraction(1, 1)).duration == ut.duration

    def test_four_four_by_a_third_is_written_out(self):
        # `Meas(4, 4) * Fraction(1, 3)` is 1/3; the unit scaler writes 4/12
        assert (src() * Fraction(1, 3)).tempus == Meas(4, 12)

    def test_unreduced_source_stays_unreduced(self):
        ut = TemporalUnit(tempus='6/20', prolatio=(1, 1, 1), beat='1/4', bpm=60)
        assert (ut * Fraction(3, 2)).tempus == Meas(18, 40)


class TestSpanCollapse:
    """The span folds into the numerator; the result always has span 1."""

    def test_span_becomes_one(self):
        ut = TemporalUnit(span=2, tempus='6/20', prolatio=(1, 1, 1))
        assert (ut * Fraction(1, 1)).span == 1

    def test_span_two_of_six_twentieths_comes_back_as_twelve(self):
        ut = TemporalUnit(span=2, tempus='6/20', prolatio=(1, 1, 1))
        assert (ut * Fraction(1, 1)).tempus == Meas(12, 20)

    def test_scaled_span_keeps_the_duration_relation(self):
        ut = TemporalUnit(span=2, tempus='6/20', prolatio=(1, 1, 1), beat='1/4', bpm=60)
        out = ut * Fraction(3, 2)
        assert out.duration == pytest.approx(float(ut.duration * Fraction(3, 2)))


class TestProlationesUntouched:
    def test_subdivision_survives_verbatim(self):
        assert (src() * Fraction(3, 2)).prolationis == (2, 1, 2)

    def test_event_count_is_unchanged(self):
        ut = src()
        assert len(ut * Fraction(3, 2)) == len(ut)

    def test_pulse_keeps_its_pulses(self):
        ut = TemporalUnit(tempus='4/4', prolatio='p')
        assert (ut * Fraction(3, 2)).prolationis == (1, 1, 1, 1)

    def test_a_rest_unit_stays_silent(self):
        ut = TemporalUnit(tempus='4/4', prolatio='r', beat='1/4', bpm=60)
        out = ut * Fraction(3, 2)
        assert len(out) == 1
        assert out[0].is_rest
        assert out.duration == pytest.approx(6.0)

    def test_nested_prolatio_survives(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, (2, (1, 1, 1)), 1))
        out = ut * Fraction(5, 4)
        assert out.prolationis == (1, (2, (1, 1, 1)), 1)
        assert len(out) == len(ut)


class TestAcceptedFactors:
    def test_fraction(self):
        assert (src() * Fraction(3, 2)).tempus == Meas(12, 8)

    def test_meas(self):
        assert (src() * Meas(3, 2)).tempus == Meas(12, 8)

    def test_str(self):
        assert (src() * '3/2').tempus == Meas(12, 8)

    def test_float_is_snapped_like_a_float_bpm(self):
        assert (src() * 1.5).tempus == Meas(12, 8)

    def test_float_snapping_recovers_the_intended_rational(self):
        # limit_denominator(10**6), matching TEMPO-5's float bpm treatment:
        # 0.3 is 3/10, not the binary expansion
        assert (src() * 0.3).tempus == Meas(12, 40)

    def test_rmul_is_commutative(self):
        ut = src()
        assert (Fraction(3, 2) * ut).tempus == (ut * Fraction(3, 2)).tempus

    def test_rmul_from_meas(self):
        assert (Meas(3, 2) * src()).tempus == Meas(12, 8)


class TestTheIntCollision:
    """`ut * 3` has two readings; Klotho refuses to guess (W0 doctrine)."""

    def test_bare_int_raises(self):
        with pytest.raises(TypeError):
            src() * 3

    def test_the_message_names_both_readings(self):
        with pytest.raises(TypeError) as exc:
            src() * 3
        msg = str(exc.value)
        assert 'repeat' in msg
        assert 'Fraction' in msg

    def test_rmul_by_a_bare_int_raises_too(self):
        with pytest.raises(TypeError):
            3 * src()

    def test_bool_is_an_int(self):
        with pytest.raises(TypeError):
            src() * True

    def test_repeat_still_means_copies(self):
        out = src().repeat(3)
        assert isinstance(out, TemporalUnitSequence)
        assert len(out) == 3

    def test_the_arithmetic_reading_is_reachable(self):
        assert (src() * Fraction(3)).tempus == Meas(12, 4)


class TestZeroAndNegative:
    def test_zero_raises(self):
        with pytest.raises(ValueError):
            src() * Fraction(0, 1)

    def test_zero_message_explains(self):
        with pytest.raises(ValueError) as exc:
            src() * 0.0
        assert 'zero' in str(exc.value)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            src() * Fraction(-3, 2)

    def test_negative_message_explains(self):
        with pytest.raises(ValueError) as exc:
            src() * Fraction(-1, 1)
        assert 'negative' in str(exc.value).lower()

    def test_the_constructor_would_have_swallowed_the_sign(self):
        # why negatives raise rather than pass through: TemporalUnit.__init__
        # absolutizes the tempus, so `ut * -1` would read back as `ut * 1`
        assert TemporalUnit(tempus=Meas(-4, 4)).tempus == Meas(4, 4)


class TestTrueDiv:
    def test_division_is_multiplication_by_the_inverse(self):
        ut = src()
        assert (ut / Fraction(3, 2)).tempus == (ut * Fraction(2, 3)).tempus

    def test_four_four_over_three_halves(self):
        assert (src() / Fraction(3, 2)).tempus == Meas(8, 12)

    def test_a_bare_int_divisor_is_accepted(self):
        # no collision to protect against: `repeat` has no division reading
        assert (src() / 2).tempus == Meas(4, 8)

    def test_halving_halves_the_duration(self):
        ut = src()
        assert (ut / 2).duration == pytest.approx(ut.duration / 2)

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            src() / 0

    def test_division_leaves_bpm_alone(self):
        assert (src() / 2).bpm == 60


class TestWhatIsDeliberatelyAbsent:
    def test_no_imul_dunder(self):
        assert '__imul__' not in vars(TemporalUnit)

    def test_star_equals_rebinds_through_mul(self):
        ut = src()
        before = ut.tempus
        scaled = ut
        scaled *= Fraction(3, 2)
        assert scaled is not ut
        assert ut.tempus == before          # the source is untouched
        assert scaled.tempus == Meas(12, 8)

    def test_addition_is_not_implemented(self):
        # `fuse` is the binary combiner and it PRESERVES both prolationes
        with pytest.raises(TypeError):
            src() + src()

    def test_subtraction_is_not_implemented(self):
        with pytest.raises(TypeError):
            src() - src()

    def test_sequences_do_not_scale(self):
        # the surface is unit-local; a sequence has no single tempus
        with pytest.raises(TypeError):
            TemporalUnitSequence([src(), src()]) * Fraction(3, 2)


class TestSourceIsUnchanged:
    def test_scaling_returns_a_new_unit(self):
        ut = src()
        out = ut * Fraction(3, 2)
        assert out is not ut
        assert ut.tempus == Meas(4, 4)
        assert ut.duration == pytest.approx(4.0)

    def test_the_rhythm_trees_are_independent(self):
        ut = src()
        out = ut * Fraction(3, 2)
        assert out._rt is not ut._rt


class TestAttribution:
    def test_the_computed_tempus_is_attributed(self):
        assert 'tempus' in (src() * Fraction(3, 2)).attributed

    def test_explicit_tempo_slots_carry_over(self):
        out = src() * Fraction(3, 2)
        assert 'beat' in out.attributed
        assert 'bpm' in out.attributed

    def test_unattributed_tempo_slots_stay_unattributed(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        out = ut * Fraction(3, 2)
        assert out.attributed == frozenset({'tempus'})


class TestCompositionalUnit:
    def test_the_result_is_still_a_compositional_unit(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 2),
                               pfields={'freq': 440, 'amp': 0.5})
        assert isinstance(uc * Fraction(3, 2), CompositionalUnit)

    def test_pfields_survive_the_scaling(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 2),
                               pfields={'freq': 440, 'amp': 0.5})
        out = uc * Fraction(3, 2)
        assert sorted(out.pfields) == ['amp', 'freq']
        assert out[0]['freq'] == 440
        assert out[0]['amp'] == 0.5

    def test_the_tempus_rewrite_is_the_same(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(2, 1, 2), beat='1/4', bpm=60)
        out = uc * Fraction(3, 2)
        assert out.tempus == Meas(12, 8)
        assert out.bpm == 60


class TestTheStrSpellingRefusesByValueNotBySpelling:
    """OPS-15 -- a bad factor gets the refusal its VALUE earns.

    Derivation, from the method's own contract rather than from what it
    currently does: ``__mul__``'s Parameters block declares
    ``other : Fraction, Meas, str, or float`` and says "A ``str`` is read
    as a fraction (``'3/2'``)", i.e. the four spellings name one factor
    type. Its Raises block declares exactly one refusal for a bad value:
    "ValueError -- If *other* is zero or negative." Both statements
    together force the invariant: for a value that is zero or negative,
    every spelling must raise the SAME ValueError. A spelling-dependent
    refusal contradicts the docstring, whichever spelling is the odd one.
    """

    @pytest.mark.parametrize('text, number', [
        ('0', Fraction(0)),
        ('0/5', Fraction(0)),
        ('-2', Fraction(-2)),
        ('-3/2', Fraction(-3, 2)),
    ])
    def test_a_str_factor_refuses_exactly_as_the_same_value_does(self, text, number):
        with pytest.raises(ValueError) as as_fraction:
            src() * number
        with pytest.raises(ValueError) as as_str:
            src() * text
        assert str(as_str.value) == str(as_fraction.value)

    def test_the_zero_refusal_survives_the_str_spelling(self):
        with pytest.raises(ValueError) as exc:
            src() * '0'
        assert 'zero' in str(exc.value)

    def test_the_negative_refusal_survives_the_str_spelling(self):
        with pytest.raises(ValueError) as exc:
            src() * '-2'
        assert 'negative' in str(exc.value).lower()

    @pytest.mark.parametrize('text', ['x', ''])
    def test_an_unparsable_str_names_the_factor_not_string_repetition(self, text):
        """The fallback the old ``NotImplemented`` reached was ``str``'s
        sequence-repeat slot, so the composer was told about multiplying a
        sequence -- a message about string repetition, for an arithmetic
        operation, naming neither the factor nor the real problem."""
        with pytest.raises(TypeError) as exc:
            src() * text
        msg = str(exc.value)
        assert repr(text) in msg, msg
        assert 'sequence' not in msg, msg

    def test_the_reflected_spelling_refuses_the_same_way(self):
        """``__rmul__`` delegates, so ``'0' * ut`` must not reach the
        sequence-repeat slot either."""
        with pytest.raises(ValueError) as exc:
            '0' * src()
        assert 'zero' in str(exc.value)
