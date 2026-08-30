"""BT-4 — ``TemporalBlock.events`` and ``TemporalBlock.principal_row``.

The block is the polyphonic container and it exposed no events at all
before this: only geometry (``duration``, ``axis``, ``height``). Two
consumers name BT-4 as a hard prerequisite:

* **WL-42, *épaisseur temporelle*** — French for "temporal thickness"
  (Haddad §5.2.2, p. 174). He measures it *« par les dates des objets
  temporels qui les compose »* — "by the dates of the temporal objects
  that compose them" — and calls the quality of that thickness *« le
  rapport entre événements diachroniques et synchroniques »*, "the ratio
  between diachronic and synchronic events". So the surface must be one
  table, ordered by date, with voice identity surviving the merge and
  with ``end`` as well as ``start`` so overlap is computable.
* **Ties charter §7**, which defines "the last leaf of a TemporalBlock"
  as the last leaf of its *principal row* — the row whose end is latest.

Everything here is greenfield: no test anywhere exercised block events
before this file, so these tests are the whole safety net.
"""

import warnings

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.temporal_units.temporal import _reoffset
from klotho.thetos import CompositionalUnit


EXPECTED_COLUMNS = ['row', 'voice', 'node_id', 'start', 'duration', 'end',
                    'is_rest', 's', 'metric_onset', 'metric_duration']


def _u(tempus='4/4', prolatio=(1, 1, 2), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


class TestEventsShape:

    def test_events_is_a_dataframe_with_the_documented_columns(self):
        blk = TemporalBlock([_u(), _u('2/4', (1, 1))], sort_rows=False)
        df = blk.events
        import pandas as pd
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_empty_block_gives_an_empty_table_with_the_same_columns(self):
        df = TemporalBlock([], sort_rows=False).events
        assert len(df) == 0
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_index_is_a_clean_range(self):
        blk = TemporalBlock([_u(), _u('2/4', (1, 1))], sort_rows=False)
        df = blk.events
        assert list(df.index) == list(range(len(df)))

    def test_events_are_ordered_by_start(self):
        blk = TemporalBlock([_u(), _u('2/4', (1, 1))], sort_rows=False)
        starts = blk.events['start'].tolist()
        assert starts == sorted(starts)

    def test_equal_onsets_break_by_row_index(self):
        # both rows start at 0 under the default axis, so the first two
        # events share a start; the row column decides the order.
        blk = TemporalBlock([_u(), _u()], sort_rows=False)
        df = blk.events
        first = df[df['start'] == 0.0]
        assert first['row'].tolist() == sorted(first['row'].tolist())

    def test_len_and_iter_still_yield_rows_not_events(self):
        rows = [_u(), _u('2/4', (1, 1))]
        blk = TemporalBlock(rows, sort_rows=False)
        assert len(blk) == 2
        assert len(list(blk)) == 2
        assert len(blk.events) > 2
        assert blk[0] is blk.rows[0]


class TestRowIdentity:

    def test_row_column_disambiguates_a_node_id_that_recurs(self):
        # node_id is NOT unique across rows: two structurally identical
        # rows both number their leaves 1, 2, 3.
        blk = TemporalBlock([_u(), _u()], sort_rows=False)
        df = blk.events
        assert df['node_id'].tolist().count(1) == 2
        pairs = set(zip(df['row'], df['node_id']))
        assert len(pairs) == len(df)

    def test_row_names_the_top_level_row_even_through_nesting(self):
        blk = TemporalBlock(
            [TemporalBlock([_u(), _u()], sort_rows=False),
             TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))])],
            sort_rows=False)
        assert set(blk.events['row']) == {0, 1}

    def test_voice_distinguishes_the_subvoices_of_a_nested_block(self):
        # Without a second identity column the two parallel sub-rows of the
        # nested block would be indistinguishable inside row 0, and WL-42's
        # synchronic/diachronic ratio would be uncomputable there.
        inner = TemporalBlock([_u(), _u()], sort_rows=False)
        blk = TemporalBlock([inner, _u('2/4', (1, 1))], sort_rows=False)
        df = blk.events
        assert set(df[df['row'] == 0]['voice']) == {'0.0', '0.1'}
        assert set(df[df['row'] == 1]['voice']) == {'1'}

    def test_voice_of_a_flat_row_is_just_the_row_index(self):
        blk = TemporalBlock([_u(), _u('2/4', (1, 1))], sort_rows=False)
        df = blk.events
        assert set(df['voice']) == {'0', '1'}


class TestAbsoluteTimes:

    @pytest.mark.parametrize('axis', [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_starts_are_absolute_under_every_axis(self, axis):
        long_row = _u('4/4', (1, 1), bpm=60)      # 4 s
        short_row = _u('2/4', (1, 1), bpm=60)     # 2 s
        blk = TemporalBlock([long_row, short_row], sort_rows=False, axis=axis)
        df = blk.events
        for i, row in enumerate(blk.rows):
            got = df[df['row'] == i]['start'].tolist()
            assert min(got) == pytest.approx(row.start)
            assert max(got) < row.end

    @pytest.mark.parametrize('axis', [-1.0, 0.0, 1.0])
    def test_starts_include_the_blocks_own_offset(self, axis):
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('2/4', (1, 1))],
                            sort_rows=False, axis=axis)
        base = blk.events['start'].tolist()
        _reoffset(blk, 7.5)
        shifted = blk.events['start'].tolist()
        assert shifted == pytest.approx([s + 7.5 for s in base])
        assert min(shifted) == pytest.approx(7.5)

    def test_end_is_start_plus_duration(self):
        blk = TemporalBlock([_u(), _u('2/4', (1, 1))], sort_rows=False, axis=0)
        df = blk.events
        assert df['end'].tolist() == pytest.approx(
            (df['start'] + df['duration']).tolist())

    def test_last_event_end_matches_the_block_end(self):
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('2/4', (1, 1))],
                            sort_rows=False, axis=0)
        assert max(blk.events['end']) == pytest.approx(blk.end)

    def test_offset_blind_uts_onsets_do_not_corrupt_the_table(self):
        # TemporalUnitSequence.onsets IGNORES the sequence's own _offset
        # (a real, unfiled defect). This is the exact shape that exposes
        # it: a shifted UTS row whose onsets read (0, ...) while its member
        # units correctly report the shifted times. The block table must
        # follow the units, not UTS.onsets.
        uts = TemporalUnitSequence([_u('1/4', (1, 1)), _u('1/4', (1, 1))])
        blk = TemporalBlock([_u('4/4', (1, 1)), uts], sort_rows=False, axis=1)
        placed = blk.rows[1]
        assert placed.start > 0                      # it really is shifted
        assert placed.onsets[0] == 0                 # and UTS.onsets is blind
        got = blk.events[blk.events['row'] == 1]['start'].tolist()
        assert min(got) == pytest.approx(placed.start)
        # each member unit contributes events beginning at its own absolute
        # start -- which is UTS.onsets shifted by the row's own offset.
        member_starts = [m.start for m in placed.seq]
        assert member_starts == pytest.approx(
            [placed.start + o for o in placed.onsets])
        for ms in member_starts:
            assert any(g == pytest.approx(ms) for g in got)
        # the blind reading would have placed the row's first event at 0.
        assert placed.onsets[0] not in got


class TestTiesAndRests:

    def test_a_tied_group_counts_as_one_event(self):
        tied = _u('4/4', (1, 1.0, 2))       # leaves 1 and 2 are one event
        untied = _u('4/4', (1, 1, 2))
        assert len(tied.events) == 2 and len(untied.events) == 3
        blk = TemporalBlock([tied, untied], sort_rows=False)
        df = blk.events
        assert len(df[df['row'] == 0]) == 2
        assert len(df[df['row'] == 1]) == 3

    def test_a_tied_groups_duration_is_the_sum_of_its_members(self):
        blk = TemporalBlock([_u('4/4', (1, 1.0, 2))], sort_rows=False)
        df = blk.events
        assert df['duration'].tolist() == pytest.approx([2.0, 2.0])

    def test_rests_appear_with_is_rest_true(self):
        blk = TemporalBlock([_u('4/4', (1, -1, 2))], sort_rows=False)
        df = blk.events
        assert df['is_rest'].tolist() == [False, True, False]
        assert all(d > 0 for d in df['duration'])


class TestNesting:

    def test_a_uts_row_flattens_in_sequence_order(self):
        uts = TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))])
        blk = TemporalBlock([uts], sort_rows=False)
        df = blk.events
        assert len(df) == 4
        assert df['start'].tolist() == pytest.approx([0.0, 1.0, 2.0, 3.0])

    def test_a_nested_block_row_flattens(self):
        inner = TemporalBlock([_u('2/4', (1, 1)), _u('2/4', (1, 1))],
                              sort_rows=False)
        blk = TemporalBlock([inner], sort_rows=False)
        df = blk.events
        assert len(df) == 4
        assert df['start'].tolist() == pytest.approx([0.0, 0.0, 1.0, 1.0])

    def test_a_block_nested_inside_a_uts_row_flattens(self):
        inner = TemporalBlock([_u('2/4', (1, 1)), _u('2/4', (1, 1))],
                              sort_rows=False)
        uts = TemporalUnitSequence([_u('2/4', (1, 1)), inner])
        blk = TemporalBlock([uts], sort_rows=False)
        df = blk.events
        assert len(df) == 6
        assert min(df[df['voice'] == '0.0']['start']) == pytest.approx(2.0)

    def test_a_compositional_unit_row_yields_the_same_columns(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 2), bpm=100)
        blk = TemporalBlock([uc, _u('2/4', (1, 1))], sort_rows=False)
        df = blk.events
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df[df['row'] == 0]) == len(uc)


class TestEventCount:

    @pytest.mark.parametrize('sort_rows', [True, False])
    def test_event_count_equals_the_sum_over_members(self, sort_rows):
        rows = [_u('4/4', (1, 1, 2)),
                TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))]),
                TemporalBlock([_u('1/4', (1, 1)), _u('1/4', (1, 1))],
                              sort_rows=False)]
        blk = TemporalBlock(rows, sort_rows=sort_rows)

        def count(obj):
            if isinstance(obj, TemporalBlock):
                return sum(count(r) for r in obj.rows)
            if isinstance(obj, TemporalUnitSequence):
                return obj.size
            return len(obj)

        assert len(blk.events) == sum(count(r) for r in blk.rows)

    def test_the_table_tracks_a_mutation(self):
        blk = TemporalBlock([_u('4/4', (1, 1, 2))], sort_rows=False)
        before = len(blk.events)
        blk.append(_u('2/4', (1, 1)))
        assert len(blk.events) == before + 2


class TestPrincipalRow:

    @pytest.mark.parametrize('axis', [-1.0, -0.5, 0.0, 0.5, 1.0])
    def test_principal_row_is_the_row_ending_latest(self, axis):
        long_row = _u('4/4', (1, 1))
        short_row = _u('2/4', (1, 1))
        blk = TemporalBlock([short_row, long_row], sort_rows=False, axis=axis)
        principal = blk.principal_row
        assert principal.end == pytest.approx(blk.end)
        assert principal.end == pytest.approx(max(r.end for r in blk.rows))

    @pytest.mark.parametrize('sort_rows', [True, False])
    def test_principal_row_is_independent_of_sort_rows(self, sort_rows):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', FutureWarning)
            blk = TemporalBlock([_u('2/4', (1, 1)), _u('4/4', (1, 1))],
                                sort_rows=sort_rows)
        assert blk.principal_row.duration == pytest.approx(4.0)

    def test_tie_break_picks_the_bottom_most_row(self):
        # axis=1 aligns every row's end, so all rows tie; the bottom-most
        # (highest index) wins.
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('2/4', (1, 1)),
                             _u('1/4', (1, 1))], sort_rows=False, axis=1)
        assert blk.principal_row is blk.rows[-1]

    def test_equal_length_rows_tie_break_to_the_bottom_most(self):
        blk = TemporalBlock([_u(), _u(), _u()], sort_rows=False)
        assert blk.principal_row is blk.rows[-1]

    def test_empty_block_has_no_principal_row(self):
        assert TemporalBlock([], sort_rows=False).principal_row is None

    def test_principal_row_is_a_live_row_not_a_copy(self):
        blk = TemporalBlock([_u('2/4', (1, 1)), _u('4/4', (1, 1))],
                            sort_rows=False)
        assert any(blk.principal_row is r for r in blk.rows)
