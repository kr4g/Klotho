"""BT-12 — ``TemporalBlock.events`` dropped every parameter a ``CompositionalUnit``
row carried.

``blk.events`` built each row from a FIXED dict of ten timing keys and
materialised the frame against the hard-coded ``_BLOCK_EVENT_COLUMNS``, so a
``CompositionalUnit`` row's instrument, freq, amp and group were simply never
read. ``uc.events`` showed them; the same events inside a block did not.

**The sound was never wrong** — ``convert_to_sc_events`` reads the units, not
this table, and lowers the parameters correctly. What lied was the inspection
surface, and it lied by OMISSION, which is why there was no value to refuse
and no warning to raise: the fix is to show the data.

The ten timing columns keep their names, order and dtypes, so nothing
downstream shifts. Parameter columns are APPENDED, and only where there is
something to append: a block of plain units, or of bare ``CompositionalUnit``
rows carrying nothing, still reports exactly the ten documented columns.
"""

import pytest

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.thetos import CompositionalUnit


TIMING_COLUMNS = ['row', 'voice', 'node_id', 'start', 'duration', 'end',
                  'is_rest', 's', 'metric_onset', 'metric_duration']


def _u(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


def _uc(inst='kl_saw'):
    """A UC with an instrument at the root and parameters on its leaves."""
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
    uc.set_instrument(uc._rt.root, inst)
    leaves = [h.id for h in uc.leaves]
    uc.set_pfields(leaves[0], freq=220.0, amp=0.4)
    uc.set_pfields(leaves[1], freq=330.0, amp=0.2)
    return uc


class TestParametersReachTheTable:

    def test_a_uc_row_contributes_its_instrument_and_pfields(self):
        blk = TemporalBlock([_uc(), _u()], sort_rows=False)
        df = blk.events
        assert list(df.columns)[:len(TIMING_COLUMNS)] == TIMING_COLUMNS
        for column in ('instrument', 'freq', 'amp'):
            assert column in df.columns, f'{column} missing from blk.events'

    def test_the_values_match_the_units_own_table(self):
        uc = _uc()
        blk = TemporalBlock([uc, _u()], sort_rows=False)
        df = blk.events
        rows = df[df['row'] == 0].sort_values('node_id')
        own = uc.events.sort_values('node_id')
        assert rows['freq'].tolist() == own['freq'].tolist()
        assert rows['amp'].tolist() == own['amp'].tolist()
        assert rows['instrument'].tolist() == own['instrument'].tolist()

    def test_a_plain_unit_row_is_nan_filled_not_dropped(self):
        blk = TemporalBlock([_uc(), _u()], sort_rows=False)
        df = blk.events
        plain = df[df['row'] == 1]
        assert len(plain) == 2
        assert plain['freq'].isna().all()
        assert plain['instrument'].isna().all()

    def test_a_uc_nested_in_a_sequence_row_still_contributes(self):
        uts = TemporalUnitSequence([_u('2/4'), _uc()])
        blk = TemporalBlock([uts], sort_rows=False)
        df = blk.events
        assert 'freq' in df.columns
        assert sorted(v for v in df['freq'] if v == v) == [220.0, 330.0]

    def test_a_uc_nested_in_a_block_row_still_contributes(self):
        inner = TemporalBlock([_uc(), _u()], sort_rows=False)
        blk = TemporalBlock([inner], sort_rows=False)
        assert 'amp' in blk.events.columns

    def test_two_uc_rows_union_their_keys(self):
        a = CompositionalUnit(tempus='4/4', prolatio=(1,), bpm=60)
        a.set_pfields([h.id for h in a.leaves][0], cutoff=1200.0)
        b = CompositionalUnit(tempus='4/4', prolatio=(1,), bpm=60)
        b.set_pfields([h.id for h in b.leaves][0], pan=-1.0)
        df = TemporalBlock([a, b], sort_rows=False).events
        assert 'cutoff' in df.columns and 'pan' in df.columns
        assert df[df['row'] == 0]['pan'].isna().all()
        assert df[df['row'] == 1]['cutoff'].isna().all()

    def test_mfields_reach_the_table_too(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1,), bpm=60)
        uc.set_mfields([h.id for h in uc.leaves][0], label='ping')
        df = TemporalBlock([uc], sort_rows=False).events
        assert df['label'].tolist() == ['ping']


class TestTimingSurfaceIsUnchanged:
    """The ten timing columns are the guaranteed contract and must not move."""

    def test_a_block_of_plain_units_reports_exactly_the_ten_columns(self):
        df = TemporalBlock([_u(), _u('2/4')], sort_rows=False).events
        assert list(df.columns) == TIMING_COLUMNS

    def test_a_bare_uc_row_adds_only_what_its_own_table_shows(self):
        """The rule is `uc.events`' columns minus the timing ones -- no more.

        A CompositionalUnit is never truly bare: it registers ``group`` as
        an mfield at construction, and its own ``events`` always carries an
        ``instrument`` column. So those two, and nothing else.
        """
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 2), bpm=100)
        df = TemporalBlock([uc, _u('2/4')], sort_rows=False).events
        assert list(df.columns) == TIMING_COLUMNS + ['instrument', 'group']
        assert set(uc.events.columns) - {'node_id', 'start', 'dur',
                                         'metric_dur'} == {'instrument',
                                                           'group'}

    def test_an_empty_block_still_reports_the_ten_columns(self):
        assert list(TemporalBlock([]).events.columns) == TIMING_COLUMNS

    def test_a_pfield_named_like_a_timing_column_does_not_overwrite_it(self):
        """The timing columns win the name; the parameter is dropped, not merged.

        ``duration`` is a real pfield name (the duration-injection control),
        and ``start`` is trivially claimable. Letting either through would
        replace a timing value with a parameter value in the one table whose
        whole job is timing.
        """
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1),
                               beat='1/4', bpm=60)
        uc.set_pfields([h.id for h in uc.leaves][0], duration=99.0, start=7.0)
        df = TemporalBlock([uc], sort_rows=False).events
        assert list(df.columns).count('duration') == 1
        assert list(df.columns).count('start') == 1
        assert df['duration'].tolist() == pytest.approx([2.0, 2.0])
        assert df['start'].tolist() == pytest.approx([0.0, 2.0])

    def test_ordering_and_timing_values_are_untouched(self):
        rows = [_uc(), _u('2/4', (1, 1))]
        df = TemporalBlock(rows, sort_rows=False).events
        assert df['start'].tolist() == sorted(df['start'].tolist())
        assert df[TIMING_COLUMNS].notna().all().all()
        assert df['duration'].tolist() == pytest.approx([2.0, 1.0, 1.0, 2.0])
