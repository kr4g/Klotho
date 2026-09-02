"""AF-1 merge-delta: the refusals that name nothing the caller can act on.

``origin/main`` is the released 10.18.0. This branch is 100+ commits ahead,
and along the way three public spellings that used to work were retired.
Retiring them is fine -- **failing to name the replacement is not.** Every
test here asserts on the MIGRATION TARGET's name, never on the whole message
text, so improving the prose does not turn these into brittle string pins.

The four surfaces, each measured before the fix (the failure output is quoted
on each class):

1. ``segment(ratio)`` -> ``segment_proportions(ratio)``. The name ``segment``
   was taken over by Haddad's segmentation operator in BOTH the
   ``rhythm_trees`` and ``temporal_units`` namespaces. Neither refusal named
   ``segment_proportions``; the RT-level one redirected the caller to the
   TemporalUnit operator, which is a third function that will also refuse
   them. **10.18.0's signature took ONE argument** (``git show
   9c1646c:klotho/chronos/rhythm_trees/algorithms.py``, line 228), so the
   arity path -- not the type guard -- is the door a real old caller walks
   into.
2. ``convolve(x, h, beat=, bpm=)`` -> ``convolve(x, h, reference=(beat, bpm))``.
   Two of the four old spellings died inside ``reference`` with an error that
   named neither ``convolve`` nor ``reference``.
3. ``TemporalUnit(span=...)`` refuses anything that is not ``int`` or
   ``Fraction``, and the message argued only about floats -- while the type
   a composer most often arrives with is a numpy integer, straight out of
   ``np.random.randint``. That message must NOT be pasted onto the
   zero/negative branch, where every clause of it is false.
4. ``autoref``'s tail-list guard told callers that a ``Fraction`` -- this
   library's own exact-arithmetic type for proportions -- "is not a number",
   and then advised a conversion that silently truncates it.

**ONE BEHAVIOUR CHANGE ships with this file**, disclosed in
``TestConvolveReferenceIsNarrowerNow``: three malformed ``reference`` shapes
that used to return a result are now refused.
"""

import numbers
from fractions import Fraction

import numpy as np
import pytest

from klotho.chronos import RhythmTree, TemporalUnit
from klotho.chronos.rhythm_trees.meas import Meas
from klotho.chronos.rhythm_trees.algorithms import (
    segment as rt_segment,
    segment_proportions,
)
from klotho.chronos.temporal_units.algorithms import (
    convolve,
    segment as ut_segment,
)
from klotho.topos.collections.patterns import autoref, autoref_rotmat


# ----------------------------------------------------------------------------
# 1 · segment / segment_proportions
# ----------------------------------------------------------------------------

class TestSegmentRefusalNamesSegmentProportions:
    """10.18.0's ``segment`` took ONE argument::

        def segment(ratio: Union[Fraction, float, str]) -> tuple[int]:
            ratio = Fraction(ratio)
            if ratio >= 1: raise ValueError("Ratio must be less than 1")
            return (ratio.numerator, ratio.denominator - ratio.numerator)

    So the call a real old caller types is ``segment('5/12')``, and the door
    it hits is the ARITY path, not the type guard. Measured before the fix,
    in both namespaces and for all three documented spellings::

        >>> rt_segment('5/12')
        TypeError: segment() missing 1 required positional argument: 'factor'
        >>> ut_segment(Fraction(2, 5))
        TypeError: segment() missing 1 required positional argument: 'factor'

    Python's own message names ``factor``, a parameter of a function the
    caller has never seen, and nothing else. The type guard -- which the
    two-argument tests below exercise -- is a SECOND door, reached only by
    someone who already knows the new signature and transposed its
    arguments.
    """

    @pytest.mark.parametrize('ratio', ['2/5', 0.4, Fraction(2, 5)])
    def test_the_one_argument_old_call_names_segment_proportions(self, ratio):
        """The call shape an old caller actually wrote. All three spellings
        are from 10.18.0's own annotation, ``Union[Fraction, float, str]``."""
        with pytest.raises(TypeError, match='segment_proportions'):
            rt_segment(ratio)
        with pytest.raises(TypeError, match='segment_proportions'):
            ut_segment(ratio)

    def test_the_one_argument_refusal_still_names_the_missing_parameter(self):
        """The arity message must not lose what Python's own said. A caller
        who simply forgot the factor needs the parameter's name."""
        for call in (rt_segment, ut_segment):
            with pytest.raises(TypeError, match='factor'):
                call('2/5')

    def test_a_lone_tree_is_told_factor_is_missing_and_nothing_else(self):
        """Guard against the fix over-reaching. ``segment(rt)`` is a caller
        who forgot an argument, not a pre-10.19 caller: ``Fraction`` never
        accepted a ``RhythmTree``, so no old call could look like this, and
        the rename breadcrumb would be noise."""
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1))
        with pytest.raises(TypeError) as excinfo:
            rt_segment(rt)
        message = str(excinfo.value)
        assert 'factor' in message
        assert 'segment_proportions' not in message

    def test_transposed_arguments_at_the_type_guard_get_the_breadcrumb(self):
        """The SECOND door: two arguments, the first one ratio-shaped."""
        with pytest.raises(TypeError, match='segment_proportions'):
            rt_segment(Fraction(2, 5), Fraction(1, 2))
        with pytest.raises(TypeError, match='segment_proportions'):
            ut_segment(Fraction(2, 5), Fraction(1, 2))

    def test_the_hint_is_targeted_not_pasted_onto_every_refusal(self):
        """A list is not a ratio, so it is not an old ``segment(ratio)`` call
        and must not be told about ``segment_proportions``."""
        with pytest.raises(TypeError) as excinfo:
            rt_segment([1, 2, 3], Fraction(1, 2))
        assert 'segment_proportions' not in str(excinfo.value)

    def test_the_rt_refusal_still_points_at_the_temporal_unit_operator(self):
        """Regression pin on the sentence that was already there."""
        with pytest.raises(TypeError, match='temporal_units'):
            rt_segment(Fraction(2, 5), Fraction(1, 2))

    def test_segment_proportions_is_the_arithmetic_the_message_promises(self):
        """Derived by hand from the 10.18.0 body quoted in the class
        docstring, ``(numerator, denominator - numerator)``: 2/5 ->
        (2, 5 - 2) = (2, 3); 1/3 -> (1, 3 - 1) = (1, 2)."""
        assert segment_proportions(Fraction(2, 5)) == (2, 3)
        assert segment_proportions(Fraction(1, 3)) == (1, 2)


class TestTheBreadcrumbDoesNotFireOnATempus:
    """A ``Meas`` is a Number, and it is a LEGITIMATE factor spelling.

    ``klotho/chronos/rhythm_trees/meas.py:316`` is ``Rational.register(Meas)``,
    so ``isinstance(Meas('4/4'), numbers.Number)`` is True even though
    ``isinstance(Meas('4/4'), Fraction)`` is False. A predicate that tests
    ``numbers.Number`` therefore catches a Tempus.

    That matters because OPS-5 gives ``segment`` two conventions:

        « La segmentation est l'operation qui divise une Unite Temporelle en
        deux par un facteur proportionnel pouvant etre une fraction
        quelconque entre 0 et 1, ou aussi, par un Tempus donne, relatif a
        celui de l'Unite Temporelle en question. »
        -- "Segmentation is the operation that divides a Temporal Unit in two
        by a proportional factor, which may be any fraction between 0 and 1,
        *or else by a given Tempus, relative to that of the Temporal Unit in
        question*."

    So ``segment(Meas('4/4'), f)`` is a caller who transposed the arguments of
    the CURRENT operator, not a pre-10.19 caller. Measured before the fix, it
    was told to go use ``segment_proportions`` -- advice for a mistake it did
    not make.
    """

    def test_meas_is_a_number_which_is_why_the_old_predicate_fired(self):
        assert isinstance(Meas('4/4'), numbers.Number) is True
        assert isinstance(Meas('4/4'), Fraction) is False

    def test_a_transposed_tempus_is_not_sent_to_segment_proportions(self):
        for call in (rt_segment, ut_segment):
            with pytest.raises(TypeError) as excinfo:
                call(Meas('4/4'), Fraction(1, 2))
            assert 'segment_proportions' not in str(excinfo.value)

    def test_a_lone_tempus_is_not_sent_to_segment_proportions_either(self):
        for call in (rt_segment, ut_segment):
            with pytest.raises(TypeError) as excinfo:
                call(Meas('4/4'))
            assert 'segment_proportions' not in str(excinfo.value)

    def test_a_tempus_really_is_a_legitimate_factor(self):
        """Why the misdirection is wrong advice, shown rather than asserted.

        Hand-derived from ``_resolve_segment_factor`` and TEMPO-5's unreduced
        discipline: a ``Meas`` factor is read relative to the source, so
        ``Meas('1/2')`` against a 4/4 unit gives f = (1/2) / (4/4) = 1/2, and
        g = 1/2. The two Tempi are built raw as
        ``(num * f.numerator) / (den * f.denominator)`` = 4*1 / 4*2 = 4/8
        each.
        """
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1))
        out = ut_segment(ut, Meas('1/2'))
        assert [str(u.tempus) for u in out.seq] == ['4/8', '4/8']


# ----------------------------------------------------------------------------
# 2 · convolve's reference
# ----------------------------------------------------------------------------

def _operands():
    x = TemporalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=90)
    h = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1), beat='1/8', bpm=120)
    return x, h


class TestConvolveReferenceRefusal:
    """Measured before the fix, for the four 10.18.0 spellings::

        >>> convolve(x, h, '1/2', 120)         # the real 4-arg spelling
        TypeError: convolve() takes from 2 to 3 positional arguments but 4
                   were given                                  # adequate

        >>> convolve(x, h, beat='1/2', bpm=120)
        TypeError: convolve() got an unexpected keyword argument 'beat'
                                                               # adequate

        >>> convolve(x, h, '1/2')
        ValueError: Invalid literal for Fraction: '/'           # names nothing

        >>> convolve(x, h, 120)
        TypeError: 'int' object is not subscriptable            # names nothing

    The last two reach ``reference[0]`` / ``reference[1]`` and die inside the
    subscript: ``'1/2'[0]`` is ``'1'`` and ``'1/2'[1]`` is ``'/'``.
    """

    def test_a_bare_beat_string_names_the_replacement(self):
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, '1/2')

    def test_a_bare_beat_string_names_the_removed_parameters(self):
        x, h = _operands()
        with pytest.raises(TypeError) as excinfo:
            convolve(x, h, '1/2')
        message = str(excinfo.value)
        assert 'beat' in message and 'bpm' in message

    def test_a_bare_bpm_number_names_the_replacement(self):
        """Passing bpm third is at least as plausible a mistake as passing
        beat third, and it used to die on ``'int' object is not
        subscriptable``."""
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, 120)

    def test_the_correct_new_spelling_still_works(self):
        """``reference=(beat, bpm)`` -- the units come back at the reference
        tempo, which is the documented contract."""
        x, h = _operands()
        out = convolve(x, h, ('1/2', 120))
        assert all(u.beat == Fraction(1, 2) and u.bpm == 120 for u in out.seq)

    def test_a_two_element_list_reference_is_unchanged(self):
        """HEAD subscripted ``reference``, so a list already worked; the
        validation must not narrow that."""
        x, h = _operands()
        as_list = convolve(x, h, ['1/2', 120])
        as_tuple = convolve(x, h, ('1/2', 120))
        assert [str(u.tempus) for u in as_list.seq] == \
               [str(u.tempus) for u in as_tuple.seq]

    def test_the_default_reference_is_untouched(self):
        """Documented contract (R13-B): the reference defaults to the FIRST
        operand's own (beat, bpm) -- so omitting it must equal writing it."""
        x, h = _operands()
        omitted = convolve(x, h)
        written = convolve(x, h, (x.beat, x.bpm))
        assert [str(u.tempus) for u in omitted.seq] == \
               [str(u.tempus) for u in written.seq]
        assert omitted.seq[0].beat == x.beat and omitted.seq[0].bpm == x.bpm


class TestConvolveReferenceIsNarrowerNow:
    """**BEHAVIOUR CHANGE, deliberate and disclosed.**

    The body only ever reads ``reference[0]`` and ``reference[1]``, so any
    object that answers those two subscripts used to work, however malformed.
    Measured in a guard-free copy of ``temporal_units/algorithms.py`` (the
    validation block deleted, module loaded by path under the package name),
    against the operands ``_operands()`` builds::

        convolve(x, h, ('1/2', 120, 3))                    -> RETURNED
            ['16/9', '32/9', '32/9', '16/9']
        convolve(x, h, {0: '1/2', 1: 120})                 -> RETURNED
            ['16/9', '32/9', '32/9', '16/9']
        convolve(x, h, np.array([Fraction(1, 2), 120], dtype=object))
                                                            -> RETURNED
            ['16/9', '32/9', '32/9', '16/9']

    All three now raise ``TypeError``. **This is a narrowing, and it stays.**
    A third element silently discarded is exactly the class of defect the
    guard was added to stop -- a caller who writes ``('1/2', 120, 3)`` means
    something by the 3 and does not get it. Under R35 correctness wins over
    compatibility. Nothing in ``klotho/``, ``tests/`` or
    ``examples/mat111mc_notebooks/`` passes any of these shapes.

    A 1-tuple is NOT part of the change: ``('1/2',)`` already raised
    ``IndexError: tuple index out of range``. Only the message improves.
    """

    def test_a_longer_tuple_is_now_refused_instead_of_silently_truncated(self):
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, ('1/2', 120, 3))

    def test_a_dict_reference_is_now_refused(self):
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, {0: '1/2', 1: 120})

    def test_a_numpy_object_array_reference_is_now_refused(self):
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, np.array([Fraction(1, 2), 120], dtype=object))

    def test_a_short_tuple_was_already_failing_and_only_the_message_moves(self):
        x, h = _operands()
        with pytest.raises(TypeError, match='reference'):
            convolve(x, h, ('1/2',))


# ----------------------------------------------------------------------------
# 3 · TemporalUnit's span refusal
# ----------------------------------------------------------------------------

class TestSpanRefusalNamesTheNumpyCase:
    """The refusal spends two paragraphs on floats and never mentioned the
    type a composer actually arrives with.

    ``np.random.randint(1, 5)`` returns ``np.int64`` directly, and
    ``isinstance(np.int64(2), (int, Fraction))`` is ``False`` -- so
    ``UT(span=np.random.randint(1, 5))`` is refused by a message arguing
    about floats.
    """

    def test_the_refusal_names_numpy(self):
        with pytest.raises(ValueError, match='numpy'):
            TemporalUnit(span=np.int64(2), tempus='4/4')

    def test_the_refusal_names_the_conversion_that_fixes_it(self):
        with pytest.raises(ValueError, match=r'int\('):
            TemporalUnit(span=np.int64(2), tempus='4/4')

    def test_the_refusal_still_explains_the_float_case(self):
        """Regression pin: the float explanation was correct and stays."""
        with pytest.raises(ValueError, match='float'):
            TemporalUnit(span=2.0, tempus='4/4')

    def test_the_float_message_keeps_what_lane_b_pinned(self):
        """``tests/test_lane_b_ut_constructor_guards.py`` pins these three
        on ``span=0.5``; splitting the raise must not drop them."""
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(span=0.5, tempus='4/4')
        message = str(excinfo.value)
        assert '0.5' in message
        assert 'Fraction' in message
        assert "tempus='2/4'" in message

    def test_rhythmtree_accepts_the_numpy_span_the_message_now_cites(self):
        """The asymmetry the new sentence tells the caller about: numpy ints
        are ``numbers.Integral`` and carry ``.numerator``, so RhythmTree --
        the very object UT builds -- takes the value UT refuses.

        Derived by hand: ``span=2`` over 4/4 covers two whole measures, and
        ``(1, 1)`` halves them, so each leaf is one whole measure -- metric
        durations ``(1/1, 1/1)``, summing to 2.
        """
        rt = RhythmTree(span=np.int64(2), meas='4/4', subdivisions=(1, 1))
        assert rt.durations == (Fraction(1, 1), Fraction(1, 1))
        assert sum(rt.durations) == 2


class TestTheNonPositiveSpanBranchIsNotTheNumpyBranch:
    """One raise covered two unrelated refusals, and the numpy sentence was
    false on the second one -- twice over.

    Measured before the fix, ``UT(span=np.int64(0))``, ``UT(span=np.int64(-3))``,
    ``UT(span=0)`` and ``UT(span=-3)`` ALL received:

        "...the value itself is fine and RhythmTree accepts it; only this
        check is narrow, so wrap it: span=int(np.random.randint(1, 5))."

    Both clauses are false there. ``int(np.int64(0))`` is ``0``, which this
    same guard refuses again -- so the prescribed wrap cannot work. And
    "RhythmTree accepts it" is true in the worst possible sense: RhythmTree
    does not validate ``span`` at all, so the message walks a composer
    straight into SPAN-1's silent-corruption door.
    """

    NON_POSITIVE = [0, -3, Fraction(-1, 2), np.int64(0), np.int64(-3)]

    @pytest.mark.parametrize('bad', NON_POSITIVE)
    def test_it_is_still_refused(self, bad):
        with pytest.raises(ValueError, match='span'):
            TemporalUnit(span=bad, tempus='4/4')

    @pytest.mark.parametrize('bad', NON_POSITIVE)
    def test_it_is_not_offered_the_numpy_wrap_that_cannot_help(self, bad):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(span=bad, tempus='4/4')
        assert 'np.random.randint' not in str(excinfo.value)

    @pytest.mark.parametrize('bad', NON_POSITIVE)
    def test_it_is_not_told_that_rhythmtree_would_accept_it(self, bad):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(span=bad, tempus='4/4')
        assert 'RhythmTree accepts' not in str(excinfo.value)

    @pytest.mark.parametrize('bad', NON_POSITIVE)
    def test_it_names_the_silent_corruption_it_is_standing_in_front_of(self, bad):
        with pytest.raises(ValueError) as excinfo:
            TemporalUnit(span=bad, tempus='4/4')
        assert 'SPAN-1' in str(excinfo.value)

    def test_the_wrap_the_old_message_prescribed_really_does_not_work(self):
        """``int(np.int64(0))`` is ``0``: the advice returns the caller to the
        same refusal. Language fact, derived not measured."""
        assert int(np.int64(0)) == 0
        with pytest.raises(ValueError):
            TemporalUnit(span=int(np.int64(0)), tempus='4/4')

    def test_rhythmtree_really_does_build_the_zero_and_backwards_trees(self):
        """SPAN-1, pinned here because the message now cites it.

        Hand-derived: ``RhythmTree`` scales its metric total by ``span``, so
        4/4 subdivided ``(1, 1)`` gives leaves of ``span/2`` each --
        ``(1/2, 1/2)`` at span 1, and therefore ``(0, 0)`` at span 0 and
        ``(-3/2, -3/2)`` at span -3. Neither raises.
        """
        zero = RhythmTree(span=0, meas='4/4', subdivisions=(1, 1))
        assert zero.durations == (Fraction(0), Fraction(0))
        back = RhythmTree(span=-3, meas='4/4', subdivisions=(1, 1))
        assert back.durations == (Fraction(-3, 2), Fraction(-3, 2))


# ----------------------------------------------------------------------------
# 4 · autoref's tail-list guard
# ----------------------------------------------------------------------------

class TestAutorefTailGuardStopsCallingNumbersNotNumbers:
    """Measured before any of this work::

        >>> autoref((2, 3), (Fraction(1, 2), Fraction(1, 3)))
        ValueError: The second positional argument is the tail list and must
        contain only numbers, but element 0 is Fraction(1, 2) (Fraction).

    ``Fraction`` is this library's exact-arithmetic type for every duration,
    and numpy integers come out of every generator in ``sequences.py``. The
    guard tests ``isinstance(x, (int, float))``, so both are refused -- with
    a message that tells the composer they are not numbers.

    What the guard exists to catch (docket RT-9) is a bare **string** second
    argument: ``mode`` is keyword-only, so ``autoref_rotmat(lst, 'GSDC')``
    used to make ``('G', 'S', 'D', 'C')`` the tail list and return a matrix
    of letters. That mistake is still refused -- pinned below.
    """

    def test_the_message_no_longer_says_a_fraction_is_not_a_number(self):
        with pytest.raises(ValueError) as excinfo:
            autoref((2, 3), (Fraction(1, 2), Fraction(1, 3)))
        assert 'must contain only numbers' not in str(excinfo.value)

    def test_a_numpy_tail_is_told_what_it_actually_is(self):
        with pytest.raises(ValueError, match='numpy'):
            autoref((2, 3), (np.int64(2), np.int64(3)))

    # -- RT-9's closure must not be re-opened --------------------------------

    def test_a_mode_string_is_still_refused_by_autoref(self):
        with pytest.raises(ValueError, match='number'):
            autoref((3, 4, 5, 7), 'GSDC')

    def test_a_mode_string_is_still_refused_by_autoref_rotmat(self):
        with pytest.raises(ValueError, match='mode'):
            autoref_rotmat((3, 4, 5, 7), 'GSDC')

    def test_the_offending_element_is_still_named(self):
        with pytest.raises(ValueError, match="'G'"):
            autoref_rotmat((3, 4, 5, 7), 'GSDC')

    def test_a_genuine_numeric_tail_still_works(self):
        """Rotation by the row index, Algorithm 5: row n takes the tail list
        rotated n+1 places. (1,2,3) x (10,20,30) -> row 0 tail (20,30,10)."""
        assert autoref((1, 2, 3), (10, 20, 30)) == (
            (1, (20, 30, 10)),
            (2, (30, 10, 20)),
            (3, (10, 20, 30)),
        )


class TestAutorefAdviceMustNotTruncateTheTypeItNames:
    """The advice a refusal gives is part of the refusal, and this one lost
    data.

    The message named ``Fraction`` first and then said "pass them through
    ``int()`` or ``float()`` to get past it". ``autoref``'s tail list is
    PROPORTIONS. ``Fraction.__int__`` truncates toward zero, so every proper
    fraction becomes ``0``: a composer who followed the advice got a tuple of
    zeros, no exception, and a rhythm tree of zero-valued terms.
    """

    def test_int_really_does_truncate_every_proper_fraction(self):
        """Language fact, derived from ``Fraction.__int__``'s
        truncate-toward-zero contract -- not measured from klotho."""
        assert int(Fraction(1, 2)) == 0
        assert int(Fraction(2, 3)) == 0
        assert int(Fraction(-1, 2)) == 0
        assert float(Fraction(1, 2)) == 0.5

    def test_the_message_recommends_float_not_int(self):
        with pytest.raises(ValueError) as excinfo:
            autoref((2, 3), (Fraction(1, 2), Fraction(1, 3)))
        assert 'float()' in str(excinfo.value)

    def test_the_message_discloses_what_int_would_have_done(self):
        """The exact worked example, so the reader cannot miss it."""
        with pytest.raises(ValueError) as excinfo:
            autoref((2, 3), (Fraction(1, 2), Fraction(1, 3)))
        assert 'int(Fraction(1, 2)) is 0' in str(excinfo.value)

    def test_following_the_int_advice_would_have_been_silent(self):
        """What made it dangerous rather than merely wrong: the truncated
        tail passes the guard and returns a matrix of zeros, with nothing
        raised. Hand-derived from Algorithm 5 -- row n takes the tail rotated
        n+1 places, and every rotation of (0, 0) is (0, 0)."""
        truncated = tuple(int(f) for f in (Fraction(1, 2), Fraction(1, 3)))
        assert truncated == (0, 0)
        assert autoref((2, 3), truncated) == ((2, (0, 0)), (3, (0, 0)))


class TestAutorefMessageDoesNotOvergeneraliseNumpy:
    """"numpy scalars ARE numbers and are refused here" is false for the
    numpy scalar a composer is most likely to hold.

    The guard is ``isinstance(x, (int, float))``. ``np.float64`` subclasses
    Python ``float``, so it is ACCEPTED; ``np.int64``, ``np.int32`` and
    ``np.float32`` do not, so they are refused. The message must say which.
    """

    def test_np_float64_passes_the_guard_and_np_int64_does_not(self):
        """Measured against the guard's own predicate, not against klotho."""
        assert isinstance(np.float64(1.5), (int, float)) is True
        assert isinstance(np.int64(2), (int, float)) is False
        assert isinstance(np.int32(2), (int, float)) is False
        assert isinstance(np.float32(1.5), (int, float)) is False

    def test_a_float64_tail_really_is_accepted_today(self):
        """Behaviour pin behind the wording. Algorithm 5 on a two-element
        list: row 0 takes the tail rotated 1 place, row 1 rotated 2."""
        out = autoref((1, 2), (np.float64(10.0), np.float64(20.0)))
        assert out == ((1, (20.0, 10.0)), (2, (10.0, 20.0)))

    def test_the_message_does_not_say_numpy_scalars_are_refused(self):
        with pytest.raises(ValueError) as excinfo:
            autoref((2, 3), (np.int64(2), np.int64(3)))
        assert 'numpy scalars' not in str(excinfo.value)

    def test_the_message_names_numpy_integers_specifically(self):
        with pytest.raises(ValueError) as excinfo:
            autoref((2, 3), (np.int64(2), np.int64(3)))
        assert 'numpy integer' in str(excinfo.value)
