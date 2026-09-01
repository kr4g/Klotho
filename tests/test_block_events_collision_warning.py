"""``TemporalBlock.events`` collision disclosure -- matching ``uc.events``.

``TemporalBlock.events`` builds a parameter column for each
:class:`~klotho.thetos.composition.compositional.CompositionalUnit` row by
doing::

    extra = {'instrument': ...}
    extra.update(c.pfields)
    extra.update(c.mfields)

A name registered as BOTH a pfield and an mfield on the same unit (the split
introduced in de7d7a2) collides here exactly as it does in ``uc.events``: the
``mfields`` update runs second, so the mfield value silently wins the single
resulting column. ``uc.events`` discloses this collision with a warning
(de7d7a2); until now, the block table resolved it the same way with NO
disclosure at all -- a user reading ``blk.events`` had no way to learn that
the value shown was the mfield, not the pfield.

This file also pins the OLDER structural-column collision (BT-12, b4b9252):
a parameter named after one of the block table's own ten guaranteed columns
(``row``/``voice``/``node_id``/``start``/``duration``/``end``/``is_rest``/
``s``/``metric_onset``/``metric_duration``) was already dropped rather than
overwriting the timing value, but that fix predates the warning convention
``uc.events`` established (d4dd5dd) and shipped with no warning either.

Both collisions now warn, with wording adapted from ``uc.events``'s own
warnings for the same two situations, and neither resolution changes:
the narrower/structural side still wins, exactly as before.
"""

import warnings

import pytest

from klotho.chronos import TemporalUnit, TemporalBlock
from klotho.thetos import CompositionalUnit


def _plain(tempus='4/4', prolatio=(1, 1), bpm=60):
    return TemporalUnit(tempus=tempus, prolatio=prolatio, bpm=bpm)


def _leaf(uc):
    return [h.id for h in uc.leaves][0]


def _uc_with_namespace_collision():
    """A unit where 'label' is registered as both a pfield and an mfield."""
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
    leaf = _leaf(uc)
    uc.set_pfields(leaf, label='pf-value')
    uc.set_mfields(leaf, label='mf-value')
    return uc


def _uc_with_structural_collision():
    """A unit where pfields shadow the block's own 'start'/'duration' columns."""
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
    leaf = _leaf(uc)
    uc.set_pfields(leaf, duration=99.0, start=7.0)
    return uc


def _clean_uc():
    """An ordinary unit with no collision of either kind."""
    uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
    uc.set_instrument(uc._rt.root, 'kl_saw')
    leaves = [h.id for h in uc.leaves]
    uc.set_pfields(leaves[0], freq=220.0, amp=0.4)
    uc.set_pfields(leaves[1], freq=330.0, amp=0.2)
    return uc


def _user_warnings(caught):
    return [w for w in caught if issubclass(w.category, UserWarning)]


# ---------------------------------------------------------------------------
# Namespace collision (a name registered as both a pfield and an mfield).
# ---------------------------------------------------------------------------

class TestNamespaceCollisionWarning:

    def test_a_collision_warns_and_names_the_field(self):
        uc = _uc_with_namespace_collision()
        blk = TemporalBlock([uc], sort_rows=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        matches = [w for w in _user_warnings(caught) if 'label' in str(w.message)]
        assert matches, "the namespace collision was not disclosed"
        assert matches[0].category is UserWarning

    def test_resolution_is_unchanged_the_mfield_value_appears(self):
        uc = _uc_with_namespace_collision()
        blk = TemporalBlock([uc], sort_rows=False)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            df = blk.events
        row = df[df['node_id'] == _leaf(uc)].iloc[0]
        assert row['label'] == 'mf-value'
        # The column namespace collapses to one, as before: no separate
        # 'label'-for-the-pfield column exists alongside it.
        assert list(df.columns).count('label') == 1

    def test_block_and_uc_events_agree_on_the_resolved_value(self):
        """The two surfaces resolve the same collision the same way.

        This is the drift guard: ``uc.events`` and ``blk.events`` must never
        show different values for the same node's shadowed name.
        """
        uc = _uc_with_namespace_collision()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            uc_df = uc.events
            blk_df = TemporalBlock([uc], sort_rows=False).events
        leaf = _leaf(uc)
        uc_row = uc_df[uc_df['node_id'] == leaf].iloc[0]
        blk_row = blk_df[blk_df['node_id'] == leaf].iloc[0]
        assert uc_row['label'] == blk_row['label'] == 'mf-value'

    def test_two_colliding_rows_still_produce_one_warning_naming_both(self):
        """Aggregated across the whole table, like ``uc.events``'s single warning.

        Not one warning per event or per row -- that would be one warning
        per note in a long block, which is worse than the silence it
        replaces.
        """
        a = _uc_with_namespace_collision()
        b = CompositionalUnit(tempus='4/4', prolatio=(1,), beat='1/4', bpm=60)
        b.set_pfields(_leaf(b), tag='pf2')
        b.set_mfields(_leaf(b), tag='mf2')
        blk = TemporalBlock([a, b], sort_rows=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        namespace_warnings = [
            w for w in _user_warnings(caught)
            if 'pfield and an mfield' in str(w.message)
        ]
        assert len(namespace_warnings) == 1
        assert 'label' in str(namespace_warnings[0].message)
        assert 'tag' in str(namespace_warnings[0].message)


# ---------------------------------------------------------------------------
# Structural collision (a field named after one of the block's own columns).
# ---------------------------------------------------------------------------

class TestStructuralCollisionWarning:

    def test_a_collision_warns_and_names_the_field(self):
        uc = _uc_with_structural_collision()
        blk = TemporalBlock([uc], sort_rows=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        matches = _user_warnings(caught)
        assert matches, "the structural collision was not disclosed"
        message = str(matches[0].message)
        assert 'start' in message and 'duration' in message
        assert matches[0].category is UserWarning

    def test_resolution_is_unchanged_the_timing_column_wins(self):
        uc = _uc_with_structural_collision()
        blk = TemporalBlock([uc], sort_rows=False)
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            df = blk.events
        assert list(df.columns).count('start') == 1
        assert list(df.columns).count('duration') == 1
        assert df['start'].tolist() == pytest.approx([0.0, 2.0])
        assert df['duration'].tolist() == pytest.approx([2.0, 2.0])

    def test_block_and_uc_events_agree_the_field_is_shadowed(self):
        uc = _uc_with_structural_collision()
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            uc_df = uc.events
            blk_df = TemporalBlock([uc], sort_rows=False).events
        # Neither table lets the pfield replace its own 'start' column;
        # both still let the field be read straight off the unit.
        assert uc_df['start'].tolist() == blk_df['start'].tolist()
        leaf = _leaf(uc)
        assert uc.get_pfield(leaf, 'start') == 7.0


# ---------------------------------------------------------------------------
# No false positives: this is the regression that would annoy every user.
# ---------------------------------------------------------------------------

class TestNoFalsePositives:

    def test_a_clean_block_warns_about_neither_collision(self):
        uc = _clean_uc()
        blk = TemporalBlock([uc, _plain()], sort_rows=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        matches = _user_warnings(caught)
        assert not matches, [str(w.message) for w in matches]

    def test_an_empty_block_warns_about_neither_collision(self):
        blk = TemporalBlock([])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        assert not _user_warnings(caught)

    def test_a_block_of_plain_units_warns_about_neither_collision(self):
        blk = TemporalBlock([_plain(), _plain('2/4')], sort_rows=False)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            blk.events
        assert not _user_warnings(caught)
