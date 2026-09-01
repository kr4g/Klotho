"""The declared ``interval_type`` decides how ``equave`` reads. Its Python
type does not.

Ruling (Ryan, 2026-09-01), superseding the earlier "a float equave means
cents" reading:

    ``Scale``, ``Chord``, ``Voicing`` and ``RelativePitchCollection`` all
    already take an explicit ``interval_type``, validated to be exactly
    ``'ratios'`` or ``'cents'`` and never inferred from the degrees. So the
    selector decides, and nothing is guessed from a type:

    * ``ratios`` mode -- the equave is a RATIO in every spelling. ``2``,
      ``2.0``, ``Fraction(2, 1)`` and ``'2/1'`` are all the octave.
    * ``cents`` mode -- the equave is a CENTS value. ``1901.955`` is the
      Bohlen-Pierce tritave.
    * A FRACTION in cents mode is the one real category error -- a
      ``Fraction`` instance, or a string in fraction format such as
      ``'3/1'``. A ratio written in a field that means cents is a mistake,
      not a second reading, and it is refused with both readings named.

    Ryan's reason: the classes already carry a mode selector, so a
    float-means-cents convention was disambiguating something that is not
    ambiguous here.

WHAT THIS FIXES. Measured on HEAD (ffefa1f), where each branch guessed the
raw argument's type on its own::

    Scale(['1/1','5/4','3/2'], equave=2.0)
        .degrees -> [1, 5/4, 3/2]        # reduced by a hardcoded octave
        .equave  -> 4508805396068249/4503599627370496   ~= 1.001156
                                         # a NEAR-UNISON equave stored on a
                                         # scale whose degrees reach 3/2

    Scale(['1/1','5/4','7/4','9/4'], equave=3.0)
        .degrees -> [1, 9/8, 5/4, 7/4]   # folded into the OCTAVE
                                         # (equave=3 gives [1, 5/4, 7/4, 9/4])

    Scale([0,400,800,1400,1800], 'cents', equave=Fraction(3,1))
        .degrees -> [0, 200, 400, 600, 800]  # reduced by 1200, not by 3
        .equave  -> 3.0                      # ...while storing 3 CENTS

    Scale(['1/1','3/2'], equave=Fraction(10001,10000))
        -> constructs, then repr() raises
           "Exceeds the limit (4300 digits) for integer string conversion"

    AbsolutePitchCollection(['C4','E4','G4'], equave=3).as_voicing().equave
        -> 3.0                           # the tritave stored as 3 CENTS

No exception in any of them except the last-moment repr. Every one is a
wrong number that looks plausible.
"""

from fractions import Fraction

import pytest

from klotho.tonos import Chord, Scale, equave_reduce
from klotho.tonos.chords.chord import Voicing
from klotho.tonos.pitch.pitch_collections import (
    AbsolutePitchCollection,
    PitchCollection,
    RelativePitchCollection,
    _resolve_equave,
)


TRITAVE_CENTS = 1901.9550008653874
JUST_MAJOR = ["1/1", "9/8", "5/4", "4/3", "3/2", "5/3", "15/8"]


class TestResolveEquaveInRatiosMode:
    """Every spelling is a ratio. There is no cents reading here."""

    @pytest.mark.parametrize("spelling", [2, 2.0, Fraction(2, 1), "2/1", "2"])
    def test_every_spelling_of_the_octave_is_the_octave(self, spelling):
        assert _resolve_equave(spelling, "ratios") == Fraction(2, 1)

    @pytest.mark.parametrize("spelling", [3, 3.0, Fraction(3, 1), "3/1", "3"])
    def test_every_spelling_of_the_tritave_is_the_tritave(self, spelling):
        assert _resolve_equave(spelling, "ratios") == Fraction(3, 1)

    def test_a_non_integer_float_is_still_a_ratio(self):
        assert _resolve_equave(1.5, "ratios") == Fraction(3, 2)

    def test_ratios_is_the_default_mode(self):
        assert _resolve_equave(2.0) == Fraction(2, 1)

    @pytest.mark.parametrize("bad", [0, -1, 1, 1.0, "1/1", Fraction(1, 2), 0.5])
    def test_an_equave_at_or_below_the_unison_is_refused(self, bad):
        with pytest.raises(ValueError, match="greater than 1"):
            _resolve_equave(bad, "ratios", "Scale")

    def test_a_float_equave_does_not_become_an_enormous_binary_rational(self):
        """``Fraction(f)`` is exact in binary and therefore huge; reducing by
        such a ratio is what built the numbers that could not be printed."""
        ratio = _resolve_equave(2 ** (1 / 12), "ratios")
        assert ratio.denominator <= 10 ** 6
        assert float(ratio) == pytest.approx(2 ** (1 / 12), rel=1e-9)


class TestResolveEquaveInCentsMode:
    """The equave is a cents value; a fraction there is refused."""

    def test_a_float_is_cents(self):
        assert _resolve_equave(1901.955, "cents") == 1901.955

    def test_an_int_is_cents_too(self):
        assert _resolve_equave(3, "cents") == 3.0

    def test_the_octave_in_cents(self):
        assert _resolve_equave(1200.0, "cents") == 1200.0

    @pytest.mark.parametrize("ratio_spelling", [Fraction(3, 1), "3/1", "2/1", Fraction(2, 1)])
    def test_a_fraction_is_refused_as_a_category_error(self, ratio_spelling):
        with pytest.raises(ValueError) as excinfo:
            _resolve_equave(ratio_spelling, "cents", "Scale")
        message = str(excinfo.value)
        assert "written as a RATIO" in message
        assert "interval_type='ratios'" in message, "must name the ratio reading"
        assert "1200.0" in message, "must show the cents spelling"

    def test_the_refusal_names_the_ratios_size_in_cents(self):
        with pytest.raises(ValueError, match="1901.9550"):
            _resolve_equave("3/1", "cents", "Scale")

    @pytest.mark.parametrize("bad", [0, -1, 0.0, -0.5])
    def test_a_non_positive_cents_equave_is_refused(self, bad):
        with pytest.raises(ValueError, match="greater than 1"):
            _resolve_equave(bad, "cents", "Scale")


class TestTheTwoPointZeroTrap:
    """The case that produced the redirect: one character, silently a
    different scale."""

    DEGREES = ["1/1", "5/4", "3/2"]

    def test_two_point_zero_is_the_octave(self):
        assert Scale(self.DEGREES, equave=2.0).equave == Fraction(2, 1)

    def test_it_does_not_collapse_the_scale(self):
        assert Scale(self.DEGREES, equave=2.0).degrees == [
            Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)
        ]

    @pytest.mark.parametrize("spelling", [2, 2.0, Fraction(2, 1), "2/1"])
    def test_all_four_spellings_give_the_identical_scale(self, spelling):
        reference = Scale(self.DEGREES, equave=2)
        other = Scale(self.DEGREES, equave=spelling)
        assert other.degrees == reference.degrees
        assert other.equave == reference.equave

    @pytest.mark.parametrize("spelling", [3, 3.0, Fraction(3, 1), "3/1"])
    def test_all_four_spellings_of_the_tritave_agree_too(self, spelling):
        """HEAD folded ``equave=3.0`` into the octave: ``9/4`` came back as
        ``9/8``, a whole octave flat, with no exception."""
        scale = Scale(["1/1", "5/4", "7/4", "9/4"], equave=spelling)
        assert scale.degrees == [Fraction(n, 4) for n in (4, 5, 7, 9)]
        assert scale.equave == Fraction(3, 1)

    def test_chord_too(self):
        assert Chord(["1/1", "5/3", "7/3"], equave=3.0).degrees == [
            Fraction(1, 1), Fraction(5, 3), Fraction(7, 3)
        ]

    def test_the_stored_equave_actually_contains_the_degrees(self):
        """HEAD stored 1.001156 on a scale whose top degree was 3/2."""
        scale = Scale(self.DEGREES, equave=2.0)
        assert all(1 <= d < scale.equave for d in scale.degrees)


class TestCentsModeRefusesAFraction:
    DEGREES = [0, 400, 800, 1400, 1800]

    @pytest.mark.parametrize("ratio_spelling", [Fraction(3, 1), "3/1"])
    def test_scale_refuses(self, ratio_spelling):
        with pytest.raises(ValueError, match="written as a RATIO"):
            Scale(self.DEGREES, "cents", equave=ratio_spelling)

    @pytest.mark.parametrize("ratio_spelling", [Fraction(3, 1), "3/1"])
    def test_chord_refuses(self, ratio_spelling):
        with pytest.raises(ValueError, match="written as a RATIO"):
            Chord(self.DEGREES, "cents", equave=ratio_spelling)

    def test_voicing_refuses(self):
        with pytest.raises(ValueError, match="written as a RATIO"):
            Voicing(self.DEGREES, "cents", equave="3/1")

    def test_relative_collection_refuses(self):
        with pytest.raises(ValueError, match="written as a RATIO"):
            RelativePitchCollection(self.DEGREES, "cents", equave=Fraction(3, 1))

    def test_the_octave_spelled_as_a_ratio_is_refused_as_well(self):
        """Not only exotic equaves: ``'2/1'`` in cents mode is the same
        mistake, and on HEAD it silently became an equave of 2 cents."""
        with pytest.raises(ValueError, match="written as a RATIO"):
            Scale(self.DEGREES, "cents", equave="2/1")

    def test_the_cents_spelling_is_what_works(self):
        scale = Scale(self.DEGREES, "cents", equave=TRITAVE_CENTS)
        assert scale.equave == TRITAVE_CENTS
        assert scale.degrees == pytest.approx([0.0, 400.0, 800.0, 1400.0, 1800.0])
        assert scale.intervals[-1] > 0

    def test_a_plain_int_in_cents_mode_is_cents(self):
        """``equave=3`` in cents mode is three cents -- absurd as music, but
        it is what the mode says, and the degrees are reduced by that same
        three cents rather than by a hardcoded octave (which is what HEAD
        did while storing 3.0)."""
        scale = Scale([0, 400, 800], "cents", equave=3)
        assert scale.equave == 3.0
        assert all(0 <= d < 3.0 for d in scale.degrees)


class TestEveryConstructibleCollectionCanBePrinted:
    """HEAD could build a Scale whose ``repr()`` raised. Nothing may do that.

    ``repr``/``str``/f-string all go through ``int.__str__``, which CPython
    refuses above ``sys.get_int_max_str_digits()`` (4300 by default).
    ``float()`` does not, which is why the previous pass's "nothing hangs"
    test certified a broken object as safe.
    """

    CASES = [
        ("2/1", ["1/1", "5/4", "3/2"]),
        (2.0, ["1/1", "5/4", "3/2"]),
        (3, JUST_MAJOR),
        (1.01, ["1/1", "5/4", "3/2"]),
        (Fraction(101, 100), ["1/1", "3/2"]),
        (Fraction(51, 50), ["1/1", "4/1"]),
    ]

    @pytest.mark.parametrize("equave,degrees", CASES)
    def test_scale_prints(self, equave, degrees):
        scale = Scale(degrees, equave=equave)
        assert repr(scale)
        assert str(scale)
        assert f"{scale}"

    @pytest.mark.parametrize("equave,degrees", CASES)
    def test_chord_prints(self, equave, degrees):
        chord = Chord(degrees, equave=equave)
        assert repr(chord)
        assert str(chord)
        assert f"{chord}"

    def test_the_case_that_used_to_raise(self):
        """On HEAD this built fine and then ``repr()`` raised
        "Exceeds the limit (4300 digits) for integer string conversion";
        the degree's numerator was 13,815 bits."""
        with pytest.raises(ValueError, match="too close to the unison"):
            Scale(["1/1", "3/2"], equave=Fraction(10001, 10000))

    def test_a_float_equave_no_longer_builds_a_binary_monster(self):
        """The old cents->ratio conversion went through
        ``Fraction.from_float(2 ** (cents / 1200))``, a 53-bit numerator over
        a 52-bit denominator, adding ~105 bits per division."""
        scale = Scale(["1/1", "3/2"], equave=1.01)
        assert max(d.numerator.bit_length() for d in scale.degrees) < 14000
        assert repr(scale)


class TestTheCostGuardRefusesInsteadOfAppearingToHang:
    """Measured 2026-09-01 with the guards removed::

        equave_reduce(Fraction(3, 2), Fraction(1000001, 1000000))
            -> no result after 120 s

    The guard is priced, not fixed at an arbitrary cents floor: the cost of a
    reduction is (size of the degree) / (size of the equave) steps, and in
    ratio mode each step adds about one equave's worth of bits.
    """

    @pytest.mark.parametrize("equave", [
        Fraction(1000001, 1000000),
        1.000001,
        Fraction(10001, 10000),
    ])
    def test_a_near_unison_ratio_equave_is_refused(self, equave):
        with pytest.raises(ValueError, match="too close to the unison"):
            Scale(["1/1", "3/2"], equave=equave)

    def test_chord_refuses_it_too(self):
        with pytest.raises(ValueError, match="too close to the unison"):
            Chord(["1/1", "3/2"], equave=Fraction(1000001, 1000000))

    def test_a_sub_millicent_equave_in_cents_mode_is_refused(self):
        with pytest.raises(ValueError, match="too close to the unison"):
            Scale([0.0, 700.0], "cents", equave=1e-9)

    def test_the_refusal_explains_both_readings(self):
        with pytest.raises(ValueError) as excinfo:
            Scale(["1/1", "3/2"], equave=Fraction(1000001, 1000000))
        message = str(excinfo.value)
        assert "ratios mode" in message and "cents mode" in message

    def test_a_musically_small_but_legitimate_equave_still_works(self):
        """The guard prices the work, so a comma-sized equave -- small, real,
        and used in xenharmonic practice -- is not caught by it."""
        for comma in (Fraction(81, 80), Fraction(531441, 524288)):
            scale = Scale(["1/1", "3/2"], equave=comma)
            assert len(scale.degrees) >= 1
            assert repr(scale)

    def test_the_degenerate_equave_guard_from_34f3241_still_fires(self):
        for unison in ("1/1", 1, Fraction(1, 1), 1.0):
            with pytest.raises(ValueError, match="greater than 1"):
                Scale(["1/1", "3/2"], equave=unison)


class TestNEdoDegreesAndStoredEquaveAgree:
    """``n_edo`` builds a cents-mode scale, so its ``equave`` is cents.

    The previous pass divided the raw argument as cents to size the steps and
    then handed the same raw argument to a constructor that read it as a
    ratio: ``n_edo(13, equave=3)`` produced degrees spanning 2.77 cents while
    reporting an equave of 1901.955. Only the default ``n_edo(12)`` was under
    test, so nothing went red.
    """

    @pytest.mark.parametrize("n,equave", [
        (12, 1200.0), (13, 1901.955), (19, 1200.0), (13, 3), (7, 2), (36, 1200.0),
    ])
    def test_the_top_degree_plus_one_step_closes_the_equave(self, n, equave):
        scale = Scale.n_edo(n, equave=equave)
        step = scale.degrees[1] - scale.degrees[0]
        assert scale.equave == pytest.approx(float(equave))
        assert scale.degrees[-1] + step == pytest.approx(float(equave))

    def test_bohlen_pierce_thirteen_equal_divisions_of_the_tritave(self):
        scale = Scale.n_edo(13, equave=TRITAVE_CENTS)
        assert scale.equave == pytest.approx(1901.955, abs=1e-3)
        assert len(scale.degrees) == 13
        assert scale.degrees[1] == pytest.approx(146.3042, abs=1e-3)
        assert scale.degrees[-1] < scale.equave

    def test_the_default_is_still_twelve_tone_equal_temperament(self):
        scale = Scale.n_edo(12)
        assert scale.equave == 1200.0
        assert scale.degrees == pytest.approx([i * 100.0 for i in range(12)])

    def test_a_ratio_spelling_is_refused_rather_than_silently_read_as_cents(self):
        with pytest.raises(ValueError, match="written as a RATIO"):
            Scale.n_edo(13, equave=Fraction(3, 1))


class TestTheModelessSurfacesAreUnchanged:
    """``equave_reduce``, ``ToneLattice`` and ``Tonnetz`` take a bare equave
    with no ``interval_type``. There a bare equave stays a RATIO, exactly as
    before this change."""

    def test_equave_reduce_reads_every_spelling_as_a_ratio(self):
        assert equave_reduce(3, 2) == Fraction(3, 2)
        assert equave_reduce(3, 2.0) == Fraction(3, 2)
        assert equave_reduce(3, "2/1") == Fraction(3, 2)
        assert equave_reduce(Fraction(7, 1), "3/1") == Fraction(7, 3)

    def test_tone_lattice_equave_is_a_ratio(self):
        from klotho.tonos import ToneLattice
        lattice = ToneLattice(dimensionality=1, resolution=1, equave=3)
        assert lattice.equave == Fraction(3, 1)

    def test_absolute_pitch_collection_equave_is_a_ratio(self):
        assert AbsolutePitchCollection(["C4", "E4"], equave=3).equave == Fraction(3, 1)
        assert AbsolutePitchCollection(["C4", "E4"], equave=2.0).equave == Fraction(2, 1)


class TestAsVoicingCrossesTheSeamInTheRightUnit:
    """``AbsolutePitchCollection`` stores a RATIO equave and builds a
    CENTS-mode Voicing. On HEAD the ratio went straight across, so a tritave
    arrived as an equave of 3 cents with no exception."""

    def test_the_tritave_survives_the_conversion(self):
        apc = AbsolutePitchCollection(["C4", "E4", "G4"], equave=3)
        assert apc.equave == Fraction(3, 1)
        assert apc.as_voicing().equave == pytest.approx(1901.955, abs=1e-3)

    def test_the_octave_default_survives_it(self):
        apc = AbsolutePitchCollection(["C4", "E4", "G4"])
        assert apc.as_voicing().equave == pytest.approx(1200.0)

    def test_an_empty_collection_takes_the_same_path(self):
        apc = AbsolutePitchCollection([], equave=3)
        assert apc.as_voicing().equave == pytest.approx(1901.955, abs=1e-3)

    def test_the_relative_collections_own_as_voicing_is_mode_consistent(self):
        chord = Chord(["1/1", "5/4", "3/2"], equave="3/1")
        assert chord.as_voicing().equave == Fraction(3, 1)
        cents_chord = Chord([0.0, 400.0, 800.0], "cents", equave=TRITAVE_CENTS)
        assert cents_chord.as_voicing().equave == pytest.approx(TRITAVE_CENTS)


class TestTheCommonPathIsUntouched:
    """The overwhelmingly common calls must be byte-identical, including the
    exactness of ``Fraction(2, 1)``."""

    def test_the_default_just_major_scale(self):
        scale = Scale()
        assert scale.equave == Fraction(2, 1)
        assert scale.degrees == [Fraction(1, 1), Fraction(9, 8), Fraction(5, 4),
                                 Fraction(4, 3), Fraction(3, 2), Fraction(5, 3),
                                 Fraction(15, 8)]

    def test_the_default_chord(self):
        chord = Chord()
        assert chord.equave == Fraction(2, 1)
        assert chord.degrees == [Fraction(1, 1), Fraction(5, 4), Fraction(3, 2)]

    def test_the_default_voicing(self):
        assert Voicing().equave == Fraction(2, 1)

    def test_a_cents_scale_with_no_equave_given(self):
        """The class default used to be the string ``"2/1"``, which the new
        rule would refuse in cents mode -- the class would have been refused
        by its own rule. It is now spelled per mode."""
        scale = Scale([0, 100, 400, 700], "cents")
        assert scale.equave == 1200.0
        assert scale.degrees == pytest.approx([0.0, 100.0, 400.0, 700.0])

    def test_a_cents_chord_with_no_equave_given(self):
        assert Chord([0, 400, 700], "cents").equave == 1200.0

    def test_a_cents_voicing_with_no_equave_given(self):
        assert Voicing([0, 400, 700], "cents").equave == 1200.0

    def test_a_pitch_collection_factory_call(self):
        coll = PitchCollection.from_degrees(["1/1", "5/4", "3/2"], equave="2/1")
        assert coll.equave == Fraction(2, 1)

    def test_from_setclass_still_defaults_to_the_octave_in_cents(self):
        coll = RelativePitchCollection.from_setclass([0, 4, 7])
        assert coll.equave == 1200.0


class TestTheStoredEquaveRoundTripsThroughEveryDerivedObject:
    """``root``, ``transpose``, inversion, slicing and ``from_collection`` all
    feed the stored equave back through a constructor. Under the new rule that
    round trip has to be a fixed point in both modes."""

    RATIO_SCALE = ["1/1", "5/4", "3/2"]

    def test_ratio_mode_round_trips(self):
        scale = Scale(self.RATIO_SCALE, equave="3/1")
        assert scale.root("A4").equave == Fraction(3, 1)
        assert scale.transpose("3/2").equave == Fraction(3, 1)
        assert (~scale).equave == Fraction(3, 1)
        assert scale[0:5].equave == Fraction(3, 1)

    def test_cents_mode_round_trips(self):
        scale = Scale([0.0, 400.0, 800.0], "cents", equave=TRITAVE_CENTS)
        assert scale.root("A4").equave == pytest.approx(TRITAVE_CENTS)
        assert scale[0:5].equave == pytest.approx(TRITAVE_CENTS)

    def test_from_collection_round_trips_in_cents_mode(self):
        chord = Chord([0, 400, 1400], "cents", equave=TRITAVE_CENTS)
        assert Chord.from_collection(chord).equave == pytest.approx(TRITAVE_CENTS)
        assert Voicing.from_collection(chord).equave == pytest.approx(TRITAVE_CENTS)

    def test_root_and_transpose_agree_with_the_base_scale(self):
        """Recorded here because a previous report claimed they disagreed on
        HEAD under a float equave. Re-measured 2026-09-01 on HEAD: they did
        not -- base, ``root`` and ``transpose`` all returned
        ``[1, 9/8, 5/4, 11/8, 7/4]``. The claim did not reproduce."""
        scale = Scale(["1/1", "5/4", "7/4", "9/4", "11/4"], equave=TRITAVE_CENTS)
        assert scale.root("A4").degrees == scale.degrees
        assert scale.transpose("3/2").degrees == scale.degrees


class TestInvertStillHonoursTheScalesOwnEquave:
    """34f3241 made ``~scale`` mirror within the scale's own equave. Every
    spelling of that equave must give the same inversion -- and now it stays
    exact, because a float equave is no longer routed through a binary
    rational."""

    DEGREES = ["1/1", "5/4", "3/2"]

    @pytest.mark.parametrize("spelling", [3, 3.0, Fraction(3, 1), "3/1"])
    def test_the_inversion_is_the_same_in_every_spelling(self, spelling):
        assert (~Scale(self.DEGREES, equave=spelling)).degrees == [
            Fraction(1, 1), Fraction(2, 1), Fraction(12, 5)
        ]

    def test_it_is_still_an_involution(self):
        scale = Scale(self.DEGREES, equave=3.0)
        assert (~~scale).degrees == scale.degrees

    def test_the_cents_spelling_inverts_within_its_own_equave(self):
        scale = Scale([0.0, 400.0, 700.0], "cents", equave=TRITAVE_CENTS)
        assert all(0 <= d < TRITAVE_CENTS for d in (~scale).degrees)
