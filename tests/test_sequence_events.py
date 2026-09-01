"""``TemporalUnitSequence.events`` -- the missing member of the family.

``TemporalUnit``, ``CompositionalUnit`` and ``TemporalBlock`` all expose an
``.events`` DataFrame; the sequence did not, so the one container Ryan
actually composes into -- the single-voice result of
:func:`~klotho.chronos.temporal_units.algorithms.interleave` -- was the one
he could not tabulate. ``interleave`` mixes whole units untouched, so its
result routinely holds BOTH plain ``TemporalUnit``s and
``CompositionalUnit``s; the parameters of the latter must survive into the
table or it lies by omission the same way ``TemporalBlock.events`` did
before BT-12.

The contract is deliberately ``TemporalBlock.events``' contract with one
substitution: where a block's rows are simultaneous and identified by
``row``/``voice``, a sequence's members are SUCCESSIVE and identified by a
single ``member`` index. ``interleave``'s own docstring calls its result
"one single-voice TemporalUnitSequence", and ``_walk_block_events``
already refuses to extend the voice path through a sequence "because its
members are successive, not simultaneous" -- so there is no voice here to
name.

Everything in this file is greenfield: no test anywhere exercised sequence
events before it.
"""

import warnings

import pytest

import pandas as pd

from klotho.chronos import TemporalUnit, TemporalUnitSequence, TemporalBlock
from klotho.chronos.temporal_units.temporal import _reoffset
from klotho.chronos.temporal_units.algorithms import interleave
from klotho.thetos import CompositionalUnit


EXPECTED_COLUMNS = ['member', 'node_id', 'start', 'duration', 'end',
                    'is_rest', 's', 'metric_onset', 'metric_duration']


def _u(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


def _leaves(uc):
    return [h.id for h in uc.leaves]


def _uc(tempus='4/4', prolatio=(1, 1), bpm=60, instrument='kl_saw', **pf):
    uc = CompositionalUnit(tempus=tempus, prolatio=prolatio, beat='1/4',
                           bpm=bpm)
    if instrument is not None:
        uc.set_instrument(uc._rt.root, instrument)
    if pf:
        for leaf in _leaves(uc):
            uc.set_pfields(leaf, **pf)
    return uc


def _user_warnings(caught):
    return [w for w in caught if issubclass(w.category, UserWarning)]


# ---------------------------------------------------------------------------
# Shape and the guaranteed leading columns.
# ---------------------------------------------------------------------------

class TestShape:

    def test_events_is_a_dataframe_with_the_documented_columns(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1))])
        df = seq.events
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_empty_sequence_gives_an_empty_table_with_the_same_columns(self):
        df = TemporalUnitSequence([]).events
        assert len(df) == 0
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_empty_sequence_built_from_none_is_the_same(self):
        df = TemporalUnitSequence().events
        assert len(df) == 0
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_index_is_a_clean_range(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1))])
        df = seq.events
        assert list(df.index) == list(range(len(df)))

    def test_tail_columns_are_exactly_the_unit_table(self):
        # A sequence table and a unit table read the same way; ``member``
        # is the only identity column the merge adds.
        unit = _u()
        seq = TemporalUnitSequence([unit])
        assert list(seq.events.columns)[1:] == list(unit.events.columns)

    def test_len_and_iter_still_yield_members_not_events(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1))])
        assert len(seq) == 2
        assert len(list(seq)) == 2
        assert len(seq.events) > 2

    def test_one_row_per_event_across_all_members(self):
        a, b = _u('4/4', (1, 1, 2)), _u('2/4', (1, 1))
        seq = TemporalUnitSequence([a, b])
        assert len(seq.events) == len(a.events) + len(b.events)


# ---------------------------------------------------------------------------
# Member identity.
# ---------------------------------------------------------------------------

class TestMemberIdentity:

    def test_member_column_disambiguates_a_node_id_that_recurs(self):
        # node_id is NOT unique across members: two structurally identical
        # units both number their leaves 1, 2.
        seq = TemporalUnitSequence([_u(), _u()])
        df = seq.events
        assert df['node_id'].tolist().count(1) == 2
        pairs = set(zip(df['member'], df['node_id']))
        assert len(pairs) == len(df)

    def test_member_is_the_position_in_the_sequence(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1)), _u()])
        assert sorted(set(seq.events['member'])) == [0, 1, 2]

    def test_member_names_the_top_level_member_even_through_nesting(self):
        seq = TemporalUnitSequence([
            TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))]),
            _u(),
        ])
        assert sorted(set(seq.events['member'])) == [0, 1]

    def test_member_is_an_integer_not_a_string(self):
        # ``voice`` in the block table is a dotted STRING path; the
        # sequence's index is an ordinary int, so it can be compared and
        # sorted numerically.
        seq = TemporalUnitSequence([_u(), _u()])
        assert all(isinstance(m, (int,)) and not isinstance(m, bool)
                   for m in seq.events['member'].tolist())


# ---------------------------------------------------------------------------
# Absolute times -- a member's events sit where the member sits.
# ---------------------------------------------------------------------------

class TestAbsoluteTimes:

    def test_second_member_reports_absolute_not_local_starts(self):
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), _u('4/4', (1, 1))])
        df = seq.events
        second = df[df['member'] == 1]
        # Member 1 begins where member 0 ends (4 s at 1/4 = 60).
        assert second['start'].min() == pytest.approx(4.0)
        assert df['start'].max() == pytest.approx(6.0)

    def test_sequence_offset_is_included(self):
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), _u('4/4', (1, 1))])
        _reoffset(seq, 10.0)
        df = seq.events
        assert df['start'].min() == pytest.approx(10.0)
        assert df['end'].max() == pytest.approx(18.0)

    def test_end_is_start_plus_duration(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1))])
        df = seq.events
        assert (df['end'] - df['start'] - df['duration']).abs().max() < 1e-9

    def test_events_are_ordered_by_start(self):
        seq = TemporalUnitSequence([_u(), _u('2/4', (1, 1)), _u()])
        starts = seq.events['start'].tolist()
        assert starts == sorted(starts)

    def test_a_member_mutated_in_place_re_offsets_the_table(self):
        # The sequence hands out LIVE members; ``s[0].append(...)`` moves
        # everything after it without any sequence-level mutator running.
        inner = TemporalUnitSequence([_u('4/4', (1, 1))])
        seq = TemporalUnitSequence([inner, _u('4/4', (1, 1))])
        assert seq.events[seq.events['member'] == 1]['start'].min() == \
            pytest.approx(4.0)
        seq[0].append(_u('4/4', (1, 1)))
        df = seq.events
        assert df[df['member'] == 1]['start'].min() == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# CompositionalUnit parameters -- the point of the task.
# ---------------------------------------------------------------------------

class TestParameterColumns:

    def test_a_sequence_of_plain_units_reports_the_nine_columns_alone(self):
        seq = TemporalUnitSequence([_u(), _u()])
        assert list(seq.events.columns) == EXPECTED_COLUMNS

    def test_a_compositional_member_contributes_instrument_then_pfields(self):
        seq = TemporalUnitSequence([_uc(freq=220.0, amp=0.4)])
        cols = list(seq.events.columns)
        assert cols[:len(EXPECTED_COLUMNS)] == EXPECTED_COLUMNS
        tail = cols[len(EXPECTED_COLUMNS):]
        assert tail[0] == 'instrument'
        assert 'freq' in tail and 'amp' in tail

    def test_instrument_is_the_display_name(self):
        seq = TemporalUnitSequence([_uc(instrument='kl_saw')])
        assert set(seq.events['instrument']) == {'kl_saw'}

    def test_mfields_come_after_pfields(self):
        uc = _uc(freq=220.0)
        for leaf in _leaves(uc):
            uc.set_mfields(leaf, track='a')
        cols = list(TemporalUnitSequence([uc]).events.columns)
        assert cols.index('freq') < cols.index('track')

    def test_mixed_sequence_shows_parameters_and_nan_fills_plain_units(self):
        # THE interleave case: plain units and CompositionalUnits in one
        # single-voice sequence.
        seq = TemporalUnitSequence([_u(), _uc(freq=220.0)])
        df = seq.events
        assert 'freq' in df.columns
        assert df[df['member'] == 0]['freq'].isna().all()
        assert not df[df['member'] == 1]['freq'].isna().any()
        assert df[df['member'] == 0]['instrument'].isna().all()

    def test_pfield_columns_are_the_union_across_members(self):
        seq = TemporalUnitSequence([_uc(freq=220.0), _uc(cutoff=800.0)])
        df = seq.events
        assert 'freq' in df.columns and 'cutoff' in df.columns
        assert df[df['member'] == 0]['cutoff'].isna().all()
        assert df[df['member'] == 1]['freq'].isna().all()

    def test_union_keeps_first_seen_order(self):
        seq = TemporalUnitSequence([_uc(freq=220.0), _uc(cutoff=800.0)])
        cols = list(seq.events.columns)
        assert cols.index('freq') < cols.index('cutoff')

    def test_interleave_result_is_tabulatable_with_parameters(self):
        a = TemporalUnitSequence([_uc(freq=220.0), _uc(freq=330.0)])
        b = TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))])
        seq = interleave(a, b)
        df = seq.events
        assert isinstance(df, pd.DataFrame)
        assert 'freq' in df.columns
        assert sorted(set(df['member'])) == [0, 1, 2, 3]
        assert df['freq'].isna().any() and df['freq'].notna().any()


# ---------------------------------------------------------------------------
# Collisions -- resolved exactly as ``uc.events`` and ``blk.events`` do,
# and DISCLOSED (99c3fd4).
# ---------------------------------------------------------------------------

class TestStructuralCollision:

    def test_a_pfield_named_duration_does_not_overwrite_the_timing_column(self):
        uc = _uc()
        for leaf in _leaves(uc):
            uc.set_pfields(leaf, duration=99.0)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            df = TemporalUnitSequence([uc]).events
        assert (df['duration'] != 99.0).all()
        assert df['duration'].tolist() == [2.0, 2.0]

    def test_a_pfield_named_member_does_not_overwrite_the_identity_column(self):
        uc = _uc()
        for leaf in _leaves(uc):
            uc.set_pfields(leaf, member=99)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            df = TemporalUnitSequence([uc]).events
        assert set(df['member']) == {0}

    def test_the_structural_collision_is_disclosed(self):
        uc = _uc()
        for leaf in _leaves(uc):
            uc.set_pfields(leaf, duration=99.0)
        seq = TemporalUnitSequence([uc])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            seq.events
        msgs = [str(w.message) for w in _user_warnings(caught)]
        assert any('duration' in m for m in msgs), msgs
        assert any('TemporalUnitSequence.events' in m for m in msgs), msgs

    def test_the_shadowed_field_is_still_readable_on_the_unit(self):
        uc = _uc()
        leaf = _leaves(uc)[0]
        uc.set_pfields(leaf, duration=99.0)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            TemporalUnitSequence([uc]).events
        assert uc.get_pfield(leaf, 'duration') == 99.0

    def test_a_clean_sequence_warns_about_nothing(self):
        seq = TemporalUnitSequence([_u(), _uc(freq=220.0)])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            seq.events
        assert _user_warnings(caught) == []


class TestNamespaceCollision:

    def test_the_mfield_wins_the_column(self):
        uc = _uc()
        leaf = _leaves(uc)[0]
        uc.set_pfields(leaf, label='pf-value')
        uc.set_mfields(leaf, label='mf-value')
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            df = TemporalUnitSequence([uc]).events
        assert 'mf-value' in df['label'].tolist()
        assert 'pf-value' not in df['label'].tolist()

    def test_the_namespace_collision_is_disclosed(self):
        uc = _uc()
        leaf = _leaves(uc)[0]
        uc.set_pfields(leaf, label='pf-value')
        uc.set_mfields(leaf, label='mf-value')
        seq = TemporalUnitSequence([uc])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            seq.events
        msgs = [str(w.message) for w in _user_warnings(caught)]
        assert any('label' in m and 'mfield' in m for m in msgs), msgs


# ---------------------------------------------------------------------------
# Nesting.
# ---------------------------------------------------------------------------

class TestNesting:

    def test_a_nested_sequence_is_flattened(self):
        inner = TemporalUnitSequence([_u('2/4', (1, 1)), _u('2/4', (1, 1))])
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), inner])
        df = seq.events
        assert len(df) == 2 + 4
        assert sorted(set(df['member'])) == [0, 1]
        assert df[df['member'] == 1]['start'].min() == pytest.approx(4.0)

    def test_a_nested_sequence_keeps_its_parameters(self):
        inner = TemporalUnitSequence([_uc(freq=440.0)])
        seq = TemporalUnitSequence([_u(), inner])
        df = seq.events
        assert 'freq' in df.columns
        assert set(df[df['member'] == 1]['freq'].dropna()) == {440.0}

    def test_a_nested_block_is_flattened(self):
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('4/4', (1, 1))],
                            sort_rows=False)
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), blk])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            df = seq.events
        assert len(df) == 2 + 4
        assert df[df['member'] == 1]['start'].min() == pytest.approx(4.0)

    def test_a_nested_blocks_parallel_voices_are_disclosed(self):
        # The sequence table has no ``voice`` column, so the two parallel
        # rows of a nested block land under the same ``member`` and are
        # not distinguished. Resolve it the project's way: say so.
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('4/4', (1, 1))],
                            sort_rows=False)
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), blk])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            seq.events
        msgs = [str(w.message) for w in _user_warnings(caught)]
        assert any('TemporalBlock' in m for m in msgs), msgs

    def test_a_nested_blocks_rows_are_ordered_by_date_not_by_discovery(self):
        # The walker finishes the block's row 0 before it starts row 1, so
        # discovery order is 4, 6, 4, 6. The documented order is by
        # ``start``, and this is the ONLY shape in which the two differ --
        # a flat sequence discovers its events in date order already.
        blk = TemporalBlock([_u('4/4', (1, 1)), _u('4/4', (1, 1))],
                            sort_rows=False)
        seq = TemporalUnitSequence([_u('4/4', (1, 1)), blk])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            starts = seq.events['start'].tolist()
        assert starts == [0.0, 2.0, 4.0, 4.0, 6.0, 6.0]

    def test_a_sequence_with_no_block_does_not_warn_about_voices(self):
        seq = TemporalUnitSequence([
            _u(), TemporalUnitSequence([_u('2/4', (1, 1))])])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            seq.events
        assert _user_warnings(caught) == []


# ---------------------------------------------------------------------------
# Parity with the rest of the family.
# ---------------------------------------------------------------------------

class TestFamilyParity:

    def test_a_one_member_sequence_matches_that_units_own_table(self):
        unit = _u('4/4', (1, 1, 2))
        seq = TemporalUnitSequence([unit])
        left = seq.events.drop(columns=['member'])
        right = seq[0].events
        pd.testing.assert_frame_equal(left, right)

    def test_the_table_is_not_a_live_view(self):
        seq = TemporalUnitSequence([_u()])
        df = seq.events
        df.loc[0, 'start'] = 999.0
        assert seq.events.loc[0, 'start'] == 0.0

    def test_rests_are_present_with_is_rest_true(self):
        seq = TemporalUnitSequence([_u('4/4', (1, -1))])
        df = seq.events
        assert df['is_rest'].any()
        assert (df['duration'] > 0).all()
