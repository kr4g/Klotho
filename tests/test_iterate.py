"""``iterate`` -- Haddad's iteration generators (docket OPS-7).

Source: Haddad 2020 thesis sect4.6, p. 131, figs. 4.76-4.82. He names two
kinds and Klotho ships both as one verb with a ``mode``:

    a) « Iteration simple sur tout ou partie des elements. »
       -- "Simple iteration over all or part of the elements."

    b) « Iteration recursive cumulative sur tout ou partie des elements,
       le resultat etant l'accumulation des resultats de la recursion. »
       -- "Cumulative recursive iteration over all or part of the
       elements, the result being the accumulation of the results of the
       recursion."

and three operator glosses that fix the shape of the result:

    « p := »  -- "at each iteration the operation is performed on the
                 result of the previous one"  (that is ``mode='recursive'``)
    « & »     -- "create a sequence from all the iteration results"
                 (that is why the return is a ``TemporalUnitSequence``)
    « || »    -- "concatenation of all results" (that is ``fuse``, already
                 shipped -- the OTHER thing his notation offers)

NAMING. "Erosion" was the docket's coinage and is NOT Haddad's; under
R13-G his own two terms are accurate, so the English name follows them
and "erosion" stays out of the API entirely.

ASSERT ON DURATION, NOT SPELLING. His printed Tempus spellings in this
section are editorial, not rule-generated -- the same duration 1/2 prints
as ``3/6`` in his sequence A and ``9/18`` in his sequence B. Klotho builds
Tempi raw (TEMPO-5) and does not chase his reductions, so the general
contract here is the VALUE and the real duration. Exact spellings are
pinned only in the rows where they happen to coincide, and marked.

THE ``Meas`` TRAP, third time. ``Fraction(meas)`` does NOT normalise:
``Meas`` is registered as ``numbers.Rational`` but keeps raw ints, so
``Fraction(Meas('4/4')) != Fraction(1, 1)``. ``_val`` below rebuilds from
the two ints, same as ``test_segment.py`` and ``test_interleave.py``.
"""

from fractions import Fraction
from functools import partial

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.temporal_units.algorithms import (
    iterate, diminish, augment, scale_tempus,
)


def _val(m):
    """The reduced value of a ``Meas``.

    NOT ``Fraction(meas)``: ``Meas`` is registered as ``numbers.Rational``
    and keeps raw, unreduced numerator/denominator, so ``Fraction(meas)``
    copies them verbatim and ``Fraction(Meas('4/4')) != Fraction(1, 1)``.
    Rebuilding from the two ints is what normalises.
    """
    return Fraction(m.numerator, m.denominator)


def _tempi(uts):
    return [_val(u.tempus) for u in uts.seq]


def _spellings(uts):
    return [str(u.tempus) for u in uts.seq]


# His running source, fig. 4.62: the nested unit whose `flatten` is the
# five-term surface 18/18 (4 2 3 6 3) that the generators erode.
def _fig_462():
    return TemporalUnit(tempus='1/1', prolatio=((2, (2, 1)), 1, 2, 1))


class TestFig478Conformance:
    """figs. 4.78/4.79 -- ``p := (p |-|(i)) &`` on ``1/1 (4 3 2 1)``.

    His ``i = 0, 2`` is the iteration counter running INCLUSIVELY from 0
    to 2 (three iterations); the position deleted is 0 every step. Read
    the other way -- counter as position -- the second result would be
    ``2/5 (3 1)``, not his ``3/10 (2 1)``, so the counter is not the
    position and ``index`` is its own parameter.
    """

    def test_the_three_published_results(self):
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        out = iterate(src, diminish, 0, 2, include_source=False)
        assert _tempi(out) == [Fraction(3, 5), Fraction(3, 10),
                               Fraction(1, 10)]

    def test_the_published_prolationes(self):
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        out = iterate(src, diminish, 0, 2, include_source=False)
        assert [tuple(u.prolationis) for u in out.seq] == [
            (3, 2, 1), (2, 1), (1,)]

    def test_durations_shrink_monotonically(self):
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        out = iterate(src, diminish, 0, 2)
        durs = [u.duration for u in out.seq]
        assert durs == sorted(durs, reverse=True)


class TestFig482SequenceA:
    """fig. 4.82's A: delete the FIRST prolatio, recursively.

    Four results; his printed Tempi are 7/9, 2/3, 3/6, 1/6. Klotho prints
    14/18, 4/6, 3/6, 1/6 -- the same four values.
    """

    EXPECTED = [Fraction(7, 9), Fraction(2, 3), Fraction(1, 2),
                Fraction(1, 6)]

    def test_four_results_by_value(self):
        out = iterate(_fig_462(), diminish, include_source=False)
        assert _tempi(out) == self.EXPECTED

    def test_the_floor_stops_it_without_an_explicit_stop(self):
        """``stop=None`` runs to the structural floor: one prolatio left."""
        out = iterate(_fig_462(), diminish, include_source=False)
        assert len(out.seq) == 4
        assert len(out.seq[-1].prolationis) == 1

    def test_the_two_rows_he_prints_unreduced_match_exactly(self):
        out = iterate(_fig_462(), diminish, include_source=False)
        assert _spellings(out)[2:] == ['3/6', '1/6']


class TestFig482SequenceB:
    """fig. 4.82's B: delete the LAST prolatio, recursively.

    The position is ``4 - i``, which is the whole reason ``index`` must
    accept a CALLABLE of the counter: his published B is unreachable with
    an int.
    """

    EXPECTED = [Fraction(5, 6), Fraction(1, 2), Fraction(1, 3),
                Fraction(2, 9)]

    def test_four_results_by_value(self):
        out = iterate(_fig_462(), diminish, include_source=False,
                      index=lambda i: 4 - i)
        assert _tempi(out) == self.EXPECTED

    def test_his_printed_spellings_all_hold_here(self):
        out = iterate(_fig_462(), diminish, include_source=False,
                      index=lambda i: 4 - i)
        assert _spellings(out) == ['15/18', '9/18', '3/9', '2/9']

    def test_a_callable_index_is_required_for_this(self):
        """An int cannot express ``4 - i``; 4 alone runs out of surface."""
        with pytest.raises(ValueError):
            iterate(_fig_462(), diminish, include_source=False, index=4)


class TestIncludeSource:
    """The trap fig. 4.82 sets: the formalism gives 4 units per operand,
    the engravings of fig. 4.80 give 5, because each sequence begins with
    the unit it was eroded from. Default is therefore ``True``.
    """

    def test_default_prepends_the_source(self):
        out = iterate(_fig_462(), diminish)
        assert len(out.seq) == 5
        assert _val(out.seq[0].tempus) == Fraction(1, 1)

    def test_the_source_passes_through_unflattened(self):
        """The head is his fig. 4.80 bar 1, nested, not the flattened
        surface the operator indexes into."""
        out = iterate(_fig_462(), diminish)
        assert str(out.seq[0].prolationis) == str(_fig_462().prolationis)

    def test_the_head_is_a_copy(self):
        src = _fig_462()
        out = iterate(src, diminish)
        assert out.seq[0] is not src

    def test_off_gives_the_formalism_count(self):
        assert len(iterate(_fig_462(), diminish,
                           include_source=False).seq) == 4

    def test_fig_480_upper_stave(self):
        out = iterate(_fig_462(), diminish)
        assert _tempi(out) == [Fraction(1, 1)] + TestFig482SequenceA.EXPECTED

    def test_fig_480_lower_stave(self):
        out = iterate(_fig_462(), diminish, index=lambda i: 4 - i)
        assert _tempi(out) == [Fraction(1, 1)] + TestFig482SequenceB.EXPECTED


class TestModes:
    """His (a) vs his (b). Same source, same positions, different target:
    ``'simple'`` applies to the SOURCE every step, ``'recursive'`` (his
    ``p :=``) to the PREVIOUS RESULT."""

    SRC = ('1/1', (4, 3, 2, 1))

    def _src(self):
        return TemporalUnit(tempus=self.SRC[0], prolatio=self.SRC[1])

    def test_simple_probe(self):
        """Delete one element of the source per step -- nothing accumulates."""
        out = iterate(self._src(), diminish, 0, 2, mode='simple',
                      include_source=False)
        assert _tempi(out) == [Fraction(3, 5), Fraction(7, 10),
                               Fraction(4, 5)]

    def test_recursive_probe(self):
        """Same call, ``p :=``: each step erodes the previous result."""
        out = iterate(self._src(), diminish, 0, 2, mode='recursive',
                      include_source=False)
        assert _tempi(out) == [Fraction(3, 5), Fraction(3, 10),
                               Fraction(1, 10)]

    def test_the_two_modes_differ(self):
        a = _tempi(iterate(self._src(), diminish, 0, 2, mode='simple',
                           include_source=False))
        b = _tempi(iterate(self._src(), diminish, 0, 2, mode='recursive',
                           include_source=False))
        assert a != b

    def test_simple_default_index_is_the_counter(self):
        """Haddad's (a) is "over all the elements", so the default walks
        them; a constant 0 would give identical copies."""
        out = iterate(self._src(), diminish, mode='simple',
                      include_source=False)
        assert _tempi(out) == [Fraction(3, 5), Fraction(7, 10),
                               Fraction(4, 5), Fraction(9, 10)]

    def test_simple_default_stop_is_one_pass_over_the_surface(self):
        out = iterate(self._src(), diminish, mode='simple',
                      include_source=False)
        assert len(out.seq) == 4

    def test_simple_leaves_the_source_intact(self):
        src = self._src()
        iterate(src, diminish, mode='simple')
        assert _val(src.tempus) == Fraction(1, 1)

    def test_an_unknown_mode_is_a_value_error(self):
        with pytest.raises(ValueError) as exc:
            iterate(self._src(), diminish, 0, 1, mode='cumulative')
        assert 'simple' in str(exc.value)
        assert 'recursive' in str(exc.value)


class TestStartAndStop:
    """His ``i = d, f`` is an INCLUSIVE counter range; ``start`` shifts
    the value handed to ``index`` and nothing else."""

    def test_stop_is_inclusive(self):
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        assert len(iterate(src, diminish, 0, 2, include_source=False).seq) == 3

    def test_start_only_shifts_the_counter(self):
        """It feeds ``index`` and does nothing else, so a compensating
        shift inside ``index`` cancels it exactly."""
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        base = _tempi(iterate(src, diminish, 0, 2, mode='simple',
                              include_source=False, index=lambda i: i))
        shifted = _tempi(iterate(src, diminish, 1, 3, mode='simple',
                                 include_source=False,
                                 index=lambda i: i - 1))
        assert base == shifted

    def test_start_does_not_skip_iterations(self):
        """``i = d, f`` is inclusive, so the count is ``f - d + 1``."""
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1))
        assert len(iterate(src, diminish, 1, 3, mode='simple',
                           include_source=False).seq) == 3

    def test_stop_below_start_is_zero_iterations(self):
        out = iterate(_fig_462(), diminish, 2, 0, include_source=False)
        assert out.seq == []

    def test_zero_iterations_still_carries_the_source(self):
        out = iterate(_fig_462(), diminish, 2, 0)
        assert len(out.seq) == 1
        assert _val(out.seq[0].tempus) == Fraction(1, 1)


class TestStructuralFloor:
    """Iterating past a single prolatio is empty, and the caller is not
    asked to get it right."""

    def test_an_overlong_stop_truncates_rather_than_raising(self):
        out = iterate(_fig_462(), diminish, 0, 99, include_source=False)
        assert len(out.seq) == 4
        assert _tempi(out) == TestFig482SequenceA.EXPECTED

    def test_a_single_prolatio_source_yields_nothing(self):
        src = TemporalUnit(tempus='1/4', prolatio=(1,))
        assert iterate(src, diminish, include_source=False).seq == []

    def test_a_single_prolatio_source_still_carries_itself(self):
        src = TemporalUnit(tempus='1/4', prolatio=(1,))
        assert len(iterate(src, diminish).seq) == 1

    def test_a_non_shrinking_operator_demands_an_explicit_stop(self):
        """``scale_tempus`` never changes the prolatio count, so the floor
        can never be reached and ``stop=None`` would not terminate."""
        src = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
        with pytest.raises(ValueError) as exc:
            iterate(src, partial(_scale_by, Fraction(3, 2)))
        assert 'stop' in str(exc.value)

    def test_the_same_operator_is_fine_with_an_explicit_stop(self):
        src = TemporalUnit(tempus='18/18', prolatio=(4, 2, 3, 6, 3))
        out = iterate(src, partial(_scale_by, 2), 0, 1,
                      include_source=False)
        assert len(out.seq) == 2
        # 4 -> 8 gives 22/18; 8 -> 16 gives 30/18. Recursive, so the
        # second step doubles what the first step already doubled.
        assert _tempi(out) == [Fraction(22, 18), Fraction(30, 18)]


def _scale_by(ratio, unit, position):
    """Adapter: ``scale_tempus`` is not unary, so it is bound to a ratio.

    This is the documented way to iterate any operator that takes more
    than a position.
    """
    return scale_tempus(unit, ratio, position)


class TestIndexParameter:
    def test_an_int_is_a_constant_position(self):
        out = iterate(_fig_462(), diminish, include_source=False, index=0)
        assert _tempi(out) == TestFig482SequenceA.EXPECTED

    def test_the_recursive_default_is_zero(self):
        explicit = _tempi(iterate(_fig_462(), diminish,
                                  include_source=False, index=0))
        default = _tempi(iterate(_fig_462(), diminish, include_source=False))
        assert explicit == default

    def test_a_callable_receives_the_counter(self):
        seen = []

        def spy(i):
            seen.append(i)
            return 0

        iterate(_fig_462(), diminish, 0, 2, include_source=False, index=spy)
        assert seen == [0, 1, 2]

    def test_a_nonsense_index_is_a_type_error(self):
        with pytest.raises(TypeError) as exc:
            iterate(_fig_462(), diminish, 0, 1, index='first')
        assert 'index' in str(exc.value)


class TestReturnShape:
    def test_returns_a_sequence_because_his_operator_says_sequence(self):
        out = iterate(_fig_462(), diminish)
        assert isinstance(out, TemporalUnitSequence)

    def test_members_are_temporal_units(self):
        out = iterate(_fig_462(), diminish)
        assert all(isinstance(u, TemporalUnit) for u in out.seq)

    def test_duration_is_the_sum_of_the_members(self):
        out = iterate(_fig_462(), diminish)
        assert out.duration == pytest.approx(
            sum(u.duration for u in out.seq))

    def test_beat_and_bpm_ride_through(self):
        src = TemporalUnit(tempus='1/1', prolatio=(4, 3, 2, 1),
                           beat='1/8', bpm=90)
        out = iterate(src, diminish, include_source=False)
        assert all(u.bpm == 90 for u in out.seq)
        assert all(u.beat == Fraction(1, 8) for u in out.seq)


class TestNotAutoref:
    """``autoref`` GROWS a tree by self-referential subdivision;
    ``iterate`` SHRINKS a unit into a sequence. Opposite direction,
    different return type -- pinned so the two are never conflated."""

    def test_autoref_grows_leaves(self):
        from klotho.topos.collections.patterns import autoref
        assert len(autoref((2, 3))) == 2
        assert sum(len(x[1]) for x in autoref((2, 3))) == 4

    def test_iterate_shrinks_leaves(self):
        out = iterate(_fig_462(), diminish, include_source=False)
        counts = [len(u.prolationis) for u in out.seq]
        assert counts == [4, 3, 2, 1]

    def test_the_return_types_differ(self):
        from klotho.topos.collections.patterns import autoref
        assert isinstance(autoref((2, 3)), tuple)
        assert isinstance(iterate(_fig_462(), diminish),
                          TemporalUnitSequence)


class TestRefusals:
    def test_a_compositional_unit_hits_the_operators_own_refusal(self):
        """``iterate`` delegates, so ``diminish``'s refusal fires rather
        than a second, possibly contradictory check of its own."""
        from klotho.thetos.composition.compositional import CompositionalUnit
        cu = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1))
        with pytest.raises(NotImplementedError) as exc:
            iterate(cu, diminish, 0, 1)
        msg = str(exc.value)
        assert 'diminish' in msg
        assert 'CompositionalUnit' in msg

    def test_a_sequence_is_not_a_unit(self):
        seq = TemporalUnitSequence([TemporalUnit(tempus='1/4',
                                                 prolatio=(1, 1))])
        with pytest.raises(TypeError) as exc:
            iterate(seq, diminish, 0, 1)
        assert 'TemporalUnit' in str(exc.value)

    def test_a_block_is_not_a_unit(self):
        block = TemporalBlock([TemporalUnit(tempus='1/4', prolatio=(1, 1))])
        with pytest.raises(TypeError):
            iterate(block, diminish, 0, 1)

    def test_a_non_callable_operator_is_a_type_error(self):
        with pytest.raises(TypeError) as exc:
            iterate(_fig_462(), 'diminish', 0, 1)
        assert 'op' in str(exc.value)


class TestGeneralOperator:
    """``op`` is any unary operator, not hardcoded diminution -- which is
    why the parameter exists at all."""

    def test_augment_grows_and_needs_a_stop(self):
        src = TemporalUnit(tempus='2/2', prolatio=(2, 1, 2))
        out = iterate(src, partial(_add, '1/5'), 0, 1,
                      include_source=False)
        assert len(out.seq) == 2
        assert out.seq[1].duration > out.seq[0].duration > src.duration


def _add(prolatio, unit, position):
    return augment(unit, prolatio, position)
