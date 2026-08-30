"""``TemporalUnit``'s real-time cache must not survive a rhythm mutation.

``TemporalUnit._real_times`` is an id-keyed map of onsets and durations in
seconds. Its freshness guard used to be a node COUNT:
``len(self._real_times) != self._rt._rx.num_nodes()``. Every mutator that
rewrites the rhythm without adding or removing a node therefore left the
cache in place, and a unit whose events had been read ONCE before the
mutation kept reporting its pre-mutation timings forever.

This is docket row RT-27. Three mutators reach the tree without going
through a ``TemporalUnit``/``CompositionalUnit`` method (which invalidate
explicitly) and preserve the node count:

* ``rt.scale``        -- reweights events, same leaves
* ``rt.replace_node`` -- rewrites one node's proportion
* ``rt.move_subtree`` -- re-parents a subtree, same nodes

The oracle here is the tree itself: real duration is
``(60/bpm) * metric_duration * (beat.denominator/beat.numerator)`` (see
``TemporalUnit._compute_timing_cache``), so ``rt.durations`` -- which no
cache stands in front of -- says what the unit must report. The
warm/cold pairs say the same thing a second way: reading a cache is not a
mutation, so read-then-mutate and mutate-then-read must agree.

That oracle is independent of the cache, and of nothing else.
``rt.durations`` reads ``metric_duration`` straight off the graph with no
memo in front of it, so a stale ``_real_times`` cannot poison it -- but the
seconds CONVERSION in ``_expected_seconds`` is copied from the
implementation, so it would follow the implementation into a wrong formula.
What pins the formula is ``TestFreshUnitsStillCacheAndStillAgree``, whose
values (``[1.0] * 4`` at 4/4, bpm 60, beat 1/4, and ``[2.0] * 4`` after
halving the bpm) are hand-computed. Do not delete that class as redundant.
"""

from fractions import Fraction

import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.thetos import CompositionalUnit as UC


def _ut(prolatio=(1, 1, 1, 1)):
    return UT(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60)


def _uc(prolatio=(1, 1, 1, 1)):
    return UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
              pfields={'freq': 440})


def _expected_seconds(unit):
    """Real durations/onsets straight off the tree, bypassing the cache."""
    beat = Fraction(unit.beat)
    factor = (60 / unit.bpm) * (beat.denominator / beat.numerator)
    durations = [float(d) * factor for d in unit._rt.durations]
    onsets, running = [], 0.0
    for d in durations:
        onsets.append(running)
        running += abs(d)
    return durations, onsets


class TestScaleInvalidatesTiming:

    def test_durations_follow_a_scaled_tree(self):
        warm = _ut()
        warm.durations                      # warm the cache, change nothing
        warm._rt.scale(0, 2)
        expected, _ = _expected_seconds(warm)
        assert list(warm.durations) == pytest.approx(expected)

    def test_onsets_follow_a_scaled_tree(self):
        warm = _ut()
        warm.onsets
        warm._rt.scale(0, 2)
        _, expected = _expected_seconds(warm)
        assert list(warm.onsets) == pytest.approx(expected)

    def test_reading_first_does_not_change_the_answer(self):
        warm, cold = _ut(), _ut()
        warm.durations
        warm._rt.scale(0, 2)
        cold._rt.scale(0, 2)
        assert list(warm.durations) == pytest.approx(list(cold.durations))
        assert list(warm.onsets) == pytest.approx(list(cold.onsets))

    def test_chronon_handles_follow_a_scaled_tree(self):
        # The per-node accessors read _real_times directly; they must not
        # be able to disagree with the unit-level tuples.
        warm = _ut()
        warm[0].real_duration
        warm._rt.scale(0, 2)
        expected, onsets = _expected_seconds(warm)
        assert warm[0].real_duration == pytest.approx(expected[0])
        assert warm[1].real_onset == pytest.approx(onsets[1])


class TestReplaceNodeInvalidatesTiming:

    def test_durations_follow_a_replaced_proportion(self):
        warm = _ut()
        warm.durations
        warm._rt.replace_node(list(warm._rt.leaf_nodes)[0], proportion=3)
        expected, _ = _expected_seconds(warm)
        assert list(warm.durations) == pytest.approx(expected)

    def test_reading_first_does_not_change_the_answer(self):
        warm, cold = _ut(), _ut()
        warm.durations
        warm._rt.replace_node(list(warm._rt.leaf_nodes)[0], proportion=3)
        cold._rt.replace_node(list(cold._rt.leaf_nodes)[0], proportion=3)
        assert list(warm.durations) == pytest.approx(list(cold.durations))
        assert list(warm.onsets) == pytest.approx(list(cold.onsets))


class TestMoveSubtreeInvalidatesTiming:

    def test_durations_follow_a_moved_subtree(self):
        warm = UT(tempus='4/4', prolatio=((1, (1, 1)), 1, 1),
                  beat='1/4', bpm=60)
        warm.durations
        warm._rt.move_subtree(3, 0)         # re-parent one leaf to the root
        expected, _ = _expected_seconds(warm)
        assert list(warm.durations) == pytest.approx(expected)

    def test_reading_first_does_not_change_the_answer(self):
        def mk():
            return UT(tempus='4/4', prolatio=((1, (1, 1)), 1, 1),
                      beat='1/4', bpm=60)
        warm, cold = mk(), mk()
        warm.durations
        warm._rt.move_subtree(3, 0)
        cold._rt.move_subtree(3, 0)
        assert list(warm.durations) == pytest.approx(list(cold.durations))
        assert list(warm.onsets) == pytest.approx(list(cold.onsets))


class TestCompositionalUnitEventsFollowTheTree:
    """The ``uc._rt`` path is blessed in ``CompositionalUnit``'s docstring;
    the events DataFrame is the surface that reaches the audio engine."""

    def test_events_follow_a_scaled_tree(self):
        warm = _uc()
        warm.events
        warm._rt.scale(0, 2)
        expected, onsets = _expected_seconds(warm)
        assert list(warm.events['dur']) == pytest.approx(
            [abs(d) for d in expected])
        assert list(warm.events['start']) == pytest.approx(onsets)

    def test_reading_first_does_not_change_the_answer(self):
        warm, cold = _uc(), _uc()
        warm.events
        warm._rt.scale(0, 2)
        cold._rt.scale(0, 2)
        assert list(warm.events['dur']) == pytest.approx(
            list(cold.events['dur']))
        assert list(warm.events['start']) == pytest.approx(
            list(cold.events['start']))


class TestFreshUnitsStillCacheAndStillAgree:
    """The guard must stay a guard: an untouched unit still serves the
    timings it always did, and bpm/beat changes (which no tree version
    tracks) must keep working through ``_timing_dirty``."""

    def test_untouched_unit_reads_the_same_twice(self):
        ut = _ut()
        assert list(ut.durations) == pytest.approx([1.0, 1.0, 1.0, 1.0])
        assert list(ut.durations) == pytest.approx([1.0, 1.0, 1.0, 1.0])
        assert list(ut.onsets) == pytest.approx([0.0, 1.0, 2.0, 3.0])

    def test_tempo_change_still_refreshes(self):
        # _scale_bpm touches no node, so no tree version moves: this is the
        # _timing_dirty half of the guard, and it must survive the fix.
        ut = _ut()
        ut.durations
        ut._scale_bpm(0.5)              # half the bpm, twice the duration
        assert list(ut.durations) == pytest.approx([2.0, 2.0, 2.0, 2.0])
        assert list(ut.onsets) == pytest.approx([0.0, 2.0, 4.0, 6.0])
