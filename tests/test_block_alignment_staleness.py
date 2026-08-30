"""BT alignment must not go stale when a row is mutated through ``rows``.

``TemporalBlock._align_rows`` computes each row's alignment offset from the
row durations it sees at that moment, and every *block-level* mutator calls
it. But :attr:`TemporalBlock.rows` hands out the **live** row objects, so a
row mutated through its own public API (``uts.append``, ``ut.bpm = ...``)
changes the geometry alignment was computed from without any block mutator
ever running. The block then reports absolute times that contradict its own
``start``..``end`` window -- which the ``events`` docstring promises are
"directly comparable across voices under any axis".

BT-4 deliberately declined to cache ``events`` *because* ``rows`` is live.
The alignment offsets were the cache that decision missed; these tests pin
the read-time validation that closes it.

Scope note: ``TemporalBlock``'s geometry model (axis-primary vs
offsets-primary, ``from_offsets``, per-row axes) is an open question and is
NOT settled here. Everything below is about staleness only -- the second
class of test pins that a block nobody mutated through a live row aligns
exactly as it always did.
"""

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock


def _u(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


class TestStaleAlignmentAfterLiveRowMutation:

    def test_right_aligned_block_realigns_after_a_row_grows(self):
        # axis=1 right-aligns: every row must END at the block's end.
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                            axis=1, sort_rows=False)
        assert blk.end == pytest.approx(4.0)
        assert [r.start for r in blk.rows] == pytest.approx([2.0, 0.0])

        blk[0].append(_u('4/4'))          # live-row mutation, not blk.append

        assert blk.end == pytest.approx(6.0)
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 2.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)
        assert blk.events['start'].min() == pytest.approx(blk.start)

    def test_every_row_ends_at_the_block_end_at_axis_1(self):
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                            axis=1, sort_rows=False)
        blk[0].append(_u('4/4'))
        for row in blk.rows:
            assert row.end == pytest.approx(blk.end)

    def test_principal_row_follows_the_grown_row(self):
        # axis=0 leaves no tie to break, so the principal row is unambiguously
        # the one that grew. (At axis=1 every row ends together and the
        # documented bottom-most tie-break decides instead -- covered below.)
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                            axis=0, sort_rows=False)
        assert blk.principal_row is blk.rows[1]
        blk[0].append(_u('4/4'))
        assert blk.principal_row is blk.rows[0]
        assert blk.principal_row.duration == pytest.approx(6.0)
        assert blk.principal_row.end == pytest.approx(blk.end)

    def test_principal_row_still_ends_at_the_block_end_at_axis_1(self):
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                            axis=1, sort_rows=False)
        blk[0].append(_u('4/4'))
        assert blk.principal_row.end == pytest.approx(blk.end)

    def test_events_stay_inside_the_block_window_at_every_axis(self):
        for axis in (-1.0, -0.5, 0.0, 0.5, 1.0):
            blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                                axis=axis, sort_rows=False)
            blk[0].append(_u('4/4'))
            events = blk.events
            assert events['start'].min() >= blk.start - 1e-9, axis
            assert events['end'].max() <= blk.end + 1e-9, axis

    def test_nested_block_realigns_through_the_outer_block(self):
        inner = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                              axis=0, sort_rows=False)
        blk = TemporalBlock([inner, _u('4/4')], axis=1, sort_rows=False)
        assert blk.end == pytest.approx(4.0)

        blk[0][0].append(_u('4/4'))       # mutate the nested block's row 0

        assert blk.end == pytest.approx(6.0)
        # inner is now the long row: at axis=1 the outer plain row shifts to 2.0
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 2.0])
        # inner is centred (axis=0): its short 4s row sits (6-4)/2 = 1.0 in
        assert [r.start for r in blk[0].rows] == pytest.approx([0.0, 1.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)

    def test_a_sequence_nested_in_a_row_realigns_through_the_block(self):
        # The grown object is two containers down (BT row -> UTS -> UTS), so
        # the block's realign has to cascade rather than just move row starts.
        blk = TemporalBlock([TemporalUnitSequence([TemporalUnitSequence([_u('2/4')]),
                                                   _u('4/4')]),
                             _u('4/4')], axis=1, sort_rows=False)
        blk[0][0].append(_u('4/4'))

        assert blk.end == pytest.approx(10.0)
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 6.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)

    def test_a_shrinking_row_realigns_too(self):
        # The other direction: the block's own duration goes DOWN, so the
        # stale offset leaves the untouched row hanging past the new end.
        blk = TemporalBlock([TemporalUnitSequence([_u('4/4'), _u('4/4')]),
                             _u('4/4')], axis=1, sort_rows=False)
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 4.0])

        blk[0].remove(1)                  # row 0 shrinks 8s -> 4s

        assert blk.duration == pytest.approx(4.0)
        assert [r.start for r in blk.rows] == pytest.approx([0.0, 0.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)

    def test_sorting_blocks_re_sort_after_a_live_row_grows(self):
        blk = TemporalBlock([TemporalUnitSequence([_u('2/4')]), _u('4/4')],
                            axis=1, sort_rows=True)
        assert [r.duration for r in blk.rows] == pytest.approx([4.0, 2.0])
        blk[1].append(_u('4/4'))          # the short row becomes the longest
        assert [r.duration for r in blk.rows] == pytest.approx([6.0, 4.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)


class TestUnmutatedBlocksAreUnchanged:
    """The fix must be invisible to a block nobody mutated through a row."""

    @pytest.mark.parametrize('axis', [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_construction_offsets_are_untouched(self, axis):
        blk = TemporalBlock([_u('2/4'), _u('4/4')], axis=axis, sort_rows=False)
        expected = 2.0 * (axis + 1) / 2
        assert [r.start for r in blk.rows] == pytest.approx([expected, 0.0])

    def test_reading_repeatedly_is_idempotent(self):
        blk = TemporalBlock([_u('2/4'), _u('4/4')], axis=0, sort_rows=False)
        first = [r.start for r in blk.rows]
        for _ in range(3):
            blk.events, blk.duration, blk.end, blk.principal_row
        assert [r.start for r in blk.rows] == pytest.approx(first)

    def test_block_level_mutator_still_realigns(self):
        blk = TemporalBlock([_u('2/4')], axis=1, sort_rows=False)
        blk.append(_u('4/4'))
        assert [r.start for r in blk.rows] == pytest.approx([2.0, 0.0])
        assert blk.events['end'].max() == pytest.approx(blk.end)

    def test_empty_block_reads_clean(self):
        blk = TemporalBlock([], sort_rows=False)
        assert blk.duration == 0.0
        assert blk.end == 0.0
        assert blk.principal_row is None
        assert len(blk.events) == 0
