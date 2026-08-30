"""``extend`` must iterate a snapshot, so a container can extend by itself.

``TemporalUnitSequence.extend`` and ``TemporalBlock.extend`` append to the very
list they are iterating. Both classes hand that list out live -- ``seq.seq``
and ``blk.rows`` are the internal lists, and ``__iter__`` returns an iterator
over them -- so ``seq.extend(seq)``, ``seq.extend(seq.seq)``,
``blk.extend(blk)`` and ``blk.extend(blk.rows)`` all appended forever. There
was no exception and no warning: the process just grew (measured at ~640,000
rows and 1.19 GB after four seconds) until something outside Python killed it.

Non-termination is the one failure the project's loud-failure doctrine cannot
shape into an error, because nothing ever gets to raise.

The fix is a snapshot of the operand, NOT a refusal of self-reference, and the
alias forms are why: ``other is self`` is only one of the ways the operand can
be the list being appended to, and an aliasing guard cannot enumerate the rest.
Both classes already accept ``x.append(x)`` -- every mutator copies on entry --
so refusing ``x.extend(x)`` would also contradict the sibling method. Snapshot
semantics match ``list.extend``, where ``lst.extend(lst)`` doubles.

These tests deliberately do NOT pin anything about *aliasing of the appended
members*: ``extend`` copies each one, as it always did.
"""

import signal
import threading
from contextlib import contextmanager

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock


def _u(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


class _Runaway(Exception):
    """Raised by the watchdog when a call under test failed to return."""


@contextmanager
def must_return_within(seconds=0.25):
    """Fail -- rather than hang the suite -- if the body does not finish.

    A non-terminating call cannot be asserted against directly; the only
    observable is that control never comes back. ``ITIMER_REAL`` interrupts the
    pure-Python append loop, which turns the hang into an ordinary red test.
    The budget is small on purpose: the runaway allocates roughly 150,000 unit
    copies per second, so a generous timeout would trade a hang for an
    out-of-memory kill. Once ``extend`` snapshots, these calls return in
    microseconds and the timer is cancelled before it can ever fire.
    """
    if not hasattr(signal, 'setitimer') or threading.current_thread() is not threading.main_thread():
        pytest.skip('ITIMER_REAL watchdog needs POSIX signals on the main thread')

    def _fire(signum, frame):
        raise _Runaway

    previous = signal.signal(signal.SIGALRM, _fire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except _Runaway:
        pytest.fail(f'call did not return within {seconds}s -- extend is iterating the list it appends to')
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class TestSelfExtendTerminates:
    """The four spellings that reach the same list, all of which hung."""

    def test_sequence_extends_by_itself(self):
        seq = TemporalUnitSequence([_u('2/4'), _u('4/4')])
        with must_return_within():
            seq.extend(seq)
        # list.extend semantics: the operand is the pre-call contents, so the
        # sequence doubles. Durations (2, 4) become (2, 4, 2, 4).
        assert len(seq) == 4
        assert seq.durations == pytest.approx((2.0, 4.0, 2.0, 4.0))
        assert seq.onsets == pytest.approx((0.0, 2.0, 6.0, 8.0))
        assert seq.duration == pytest.approx(12.0)

    def test_sequence_extends_by_its_own_live_list(self):
        # ``seq.seq`` IS the internal list, so this hangs for the same reason
        # and an ``other is self`` guard would not have caught it.
        seq = TemporalUnitSequence([_u('2/4'), _u('4/4')])
        with must_return_within():
            seq.extend(seq.seq)
        assert len(seq) == 4
        assert seq.durations == pytest.approx((2.0, 4.0, 2.0, 4.0))

    def test_block_extends_by_itself(self):
        blk = TemporalBlock([_u('2/4'), _u('4/4')], axis=-1, sort_rows=False)
        with must_return_within():
            blk.extend(blk)
        assert len(blk) == 4
        assert [r.duration for r in blk.rows] == pytest.approx([2.0, 4.0, 2.0, 4.0])
        # Left-aligned: every row still starts at the block's start, and the
        # block is still as long as its longest row -- doubling adds no length.
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 0.0, 0.0, 0.0])
        assert blk.duration == pytest.approx(4.0)

    def test_block_extends_by_its_own_live_rows(self):
        # ``blk.rows`` IS the internal list; same hang, same reason.
        blk = TemporalBlock([_u('2/4'), _u('4/4')], axis=-1, sort_rows=False)
        with must_return_within():
            blk.extend(blk.rows)
        assert len(blk) == 4
        assert [r.duration for r in blk.rows] == pytest.approx([2.0, 4.0, 2.0, 4.0])


class TestSelfExtendSnapshotsOnce:
    """``repeat`` repeats the *pre-call* contents, matching ``append(ut, repeat=n)``."""

    def test_sequence_self_extend_honours_repeat(self):
        seq = TemporalUnitSequence([_u('2/4')])
        with must_return_within():
            seq.extend(seq, repeat=3)
        # 1 + 3 x 1, not 1 x 2^3: the operand is snapshotted once, so each
        # repetition appends the same original contents.
        assert len(seq) == 4
        assert seq.durations == pytest.approx((2.0, 2.0, 2.0, 2.0))


class TestSelfExtendedMembersAreIndependentCopies:
    """Snapshotting the operand changes nothing about copy-on-entry.

    ``TemporalUnit`` has no settable attribute at all, so independence is shown
    through a nested container member, which does have public mutators.
    """

    def test_appended_units_are_copies_not_the_originals(self):
        seq = TemporalUnitSequence([TemporalUnitSequence([_u('2/4')])])
        original = seq[0]
        with must_return_within():
            seq.extend(seq)
        assert seq[1] is not original
        seq[1].append(_u('4/4'))
        assert seq[1].duration == pytest.approx(6.0)
        assert seq[0].duration == pytest.approx(2.0)

    def test_appended_rows_are_copies_not_the_originals(self):
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')])], axis=-1, sort_rows=False)
        original = blk.rows[0]
        with must_return_within():
            blk.extend(blk)
        assert blk.rows[1] is not original
        blk.rows[1].append(_u('4/4'))
        assert blk.rows[1].duration == pytest.approx(6.0)
        assert blk.rows[0].duration == pytest.approx(2.0)


class TestOperandIsConsumedOnlyOnce:
    """A one-shot iterable now honours ``repeat``, because it is materialised."""

    def test_generator_operand_repeats_as_documented(self):
        seq = TemporalUnitSequence([_u('4/4')])
        # A generator was exhausted by the first repetition, so repeat=3 quietly
        # appended one round instead of three -- the docstring says ``repeat`` is
        # the "number of times to repeat the extension".
        seq.extend((_u('2/4') for _ in range(2)), repeat=3)
        assert len(seq) == 7
        assert seq.durations == pytest.approx((4.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0))


class TestExtendFromADifferentContainerIsUnchanged:
    """Control: the ordinary case must behave exactly as it always did."""

    def test_sequence_extends_from_another_sequence(self):
        target = TemporalUnitSequence([_u('2/4')])
        source = TemporalUnitSequence([_u('4/4'), _u('4/4')])
        target.extend(source)
        assert len(target) == 3
        assert len(source) == 2
        assert target.durations == pytest.approx((2.0, 4.0, 4.0))

    def test_block_extends_from_another_block(self):
        target = TemporalBlock([_u('2/4')], axis=-1, sort_rows=False)
        source = TemporalBlock([_u('4/4'), _u('4/4')], axis=-1, sort_rows=False)
        target.extend(source)
        assert len(target) == 3
        assert len(source) == 2
        assert target.duration == pytest.approx(4.0)
