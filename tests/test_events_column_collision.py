"""``uc.events`` structural columns vs. parameter columns of the same name.

``CompositionalUnit.events`` builds each row by writing the unit's own
structural facts -- ``node_id``, ``start``, ``dur``, ``metric_dur``,
``instrument`` -- and then merging the pfield and mfield dicts on top.
The merge used a plain ``row[k] = ...``, so a field whose NAME matched a
structural column REPLACED that column's value.

That is not a cosmetic ordering nit. It is reachable with no user field
at all: bundled ``kl_kicktone`` declares a SynthDef control named
``dur``, so binding it made ``uc.events['dur']`` report the SynthDef's
0.6 default instead of the note's real one-second duration -- and 0.6 is
not even what plays, because the assembly layer injects the slot
duration into that control (``_duration_inject_key``). The primary
inspection surface disagreed with both the music and the engine.

The rule these tests pin, matching what ``TemporalBlock.events`` shipped
for the same question (BT-12): the structural columns are the guaranteed
contract and always win; a field whose name collides is not appended to
the table, and stays readable on the unit itself.
"""

import warnings

import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.compositional import _UC_EVENT_COLUMNS
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.utils.playback.supersonic.converters import convert_to_sc_events


# The full set, established by reading what ``events`` writes into each row
# before the merge. ``group`` is deliberately NOT here: it is an mfield
# column produced BY the merge, not a structural one, so it has nothing to
# collide with.
STRUCTURAL = ('node_id', 'start', 'dur', 'metric_dur', 'instrument')


def _unit():
    """Four quarter notes at the default 60 bpm: one second each."""
    return UC(span=1, tempus='4/4', prolatio=(1, 1, 1, 1))


def _truth(uc):
    """The structural values the table must report, read from the events."""
    events = list(uc)
    return {
        'node_id': [e.node_id for e in events],
        'start': [e.start for e in events],
        'dur': [e.duration for e in events],
        'metric_dur': [e.metric_duration for e in events],
    }


def test_constant_matches_the_columns_events_actually_writes():
    """The reserved tuple is the table's real structural column list.

    A column added to ``events`` without being added to
    ``_UC_EVENT_COLUMNS`` would reopen the defect for that column alone.
    """
    df = _unit().events
    assert tuple(_UC_EVENT_COLUMNS) == STRUCTURAL
    for name in STRUCTURAL:
        assert name in df.columns
    # and they lead the table, in order
    assert list(df.columns)[:len(STRUCTURAL)] == list(STRUCTURAL)


@pytest.mark.parametrize('name', STRUCTURAL)
def test_pfield_named_after_a_structural_column_does_not_replace_it(name):
    uc = _unit()
    truth = _truth(uc)
    uc.set_pfields(uc._rt.leaf_nodes[1], **{name: 999.0})
    df = uc.events
    if name == 'instrument':
        assert list(df['instrument']) == [None, None, None, None]
    else:
        assert list(df[name]) == truth[name], (
            f"pfield {name!r} overwrote the {name!r} structural column")


@pytest.mark.parametrize('name', STRUCTURAL)
def test_mfield_named_after_a_structural_column_does_not_replace_it(name):
    uc = _unit()
    truth = _truth(uc)
    uc.set_mfields(uc._rt.leaf_nodes[1], **{name: 999.0})
    df = uc.events
    if name == 'instrument':
        assert list(df['instrument']) == [None, None, None, None]
    else:
        assert list(df[name]) == truth[name], (
            f"mfield {name!r} overwrote the {name!r} structural column")


@pytest.mark.parametrize('name', STRUCTURAL)
def test_colliding_field_adds_no_second_column(name):
    """The collision is dropped, not emitted twice or under a mangled name."""
    uc = _unit()
    before = list(uc.events.columns)
    uc.set_pfields(uc._rt.leaf_nodes[1], **{name: 999.0})
    after = list(uc.events.columns)
    assert after == before
    assert after.count(name) == 1


@pytest.mark.parametrize('name', STRUCTURAL)
def test_colliding_field_is_still_readable_on_the_unit(name):
    """Dropped from the table is not dropped from the unit."""
    uc = _unit()
    leaf = uc._rt.leaf_nodes[1]
    uc.set_pfields(leaf, **{name: 999.0})
    assert uc.get_pfield(leaf, name) == 999.0
    assert name in uc.pfields


@pytest.mark.parametrize('name', STRUCTURAL)
def test_colliding_field_warns_and_names_itself(name):
    uc = _unit()
    uc.set_pfields(uc._rt.leaf_nodes[1], **{name: 999.0})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        uc.events
    messages = [str(w.message) for w in caught]
    assert any(name in m and 'events' in m for m in messages), (
        f"no warning named the shadowed field {name!r}; got {messages}")


def test_no_warning_when_nothing_collides():
    uc = _unit()
    uc.set_pfields(uc._rt.leaf_nodes[1], amp=0.3, freq=440.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        df = uc.events
    assert [str(w.message) for w in caught] == []
    # pandas coerces the unset rows to NaN in a float column
    assert df['amp'].tolist()[1] == 0.3
    assert df['amp'].isna().tolist() == [True, False, True, True]


# --- the live case: no user field at all, just a bundled instrument -------

def test_bundled_kicktone_dur_column_is_the_notes_duration():
    """``kl_kicktone`` ships a ``dur`` control; binding it must not lie.

    This is the reachable half of the defect. It needs no user pfield --
    ``set_instrument`` registers every control the SynthDef declares.
    """
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    assert list(uc.events['dur']) == [1.0, 1.0, 1.0, 1.0], (
        "the kicktone's 0.6 SynthDef default replaced the real duration")
    assert list(uc.events['start']) == [0.0, 1.0, 2.0, 3.0]


def test_kicktone_events_table_agrees_with_what_is_lowered():
    """The table and the engine must report the same duration.

    Before the fix the table said 0.6 and the lowered event said 1.0 --
    the injected slot duration -- so the inspection surface disagreed with
    the sound for an entirely ordinary bundled instrument.
    """
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    table = list(uc.events['dur'])
    lowered = [e['dur'] for e in convert_to_sc_events(uc)]
    assert table == lowered


def test_kicktone_dur_control_still_reaches_the_synth():
    """Dropping the COLUMN must not drop the CONTROL.

    The point of keeping ``dur`` a legal field name is that the kicktone
    needs it; if this ever goes red the fix has over-reached into a
    refusal.
    """
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    for event in convert_to_sc_events(uc):
        assert 'dur' in event['pfields']


def test_naming_a_field_after_a_structural_column_is_not_refused():
    """No refusal here, on purpose.

    ``dur`` and ``start`` are plausible -- and, for ``dur``, actual --
    SynthDef control names, so the table's column namespace must not
    constrain the field namespace. Pins the decision so a later "just
    reserve the names" pass has to argue with a test.
    """
    uc = _unit()
    leaf = uc._rt.leaf_nodes[0]
    for name in STRUCTURAL:
        uc.set_pfields(leaf, **{name: 1.0})
        uc.set_mfields(leaf, **{f'm_{name}': 1.0})
    uc.set_instrument(
        leaf, SynthDefInstrument(name='w', defName='w',
                                 pfields={'start': 0.25, 'dur': 0.5}))


# --- unaffected neighbours -----------------------------------------------

def test_group_mfield_column_survives():
    """``group`` is an mfield column, not a structural one: it stays."""
    df = _unit().events
    assert list(df['group']) == ['default'] * 4


def test_ordinary_columns_are_unchanged_by_the_guard():
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    df = uc.events
    assert list(df['amp']) == [0.85] * 4
    assert list(df['baseFreq']) == [110.0] * 4
    assert list(df['instrument']) == ['kl_kicktone'] * 4


# --- characterisation, NOT proof of the fix -------------------------------
#
# DEFENCE IN DEPTH. These two pass against the BROKEN code as well: the
# corruption was always confined to the DataFrame, because lowering reads
# ``event.start`` / ``event.duration`` (real ``Chronon`` properties that a
# pfield cannot shadow) rather than the table. They are here to pin that
# containment, so a future change that lets a field reach the timing path
# fails loudly instead of moving a note.
#
# Break-tested honestly: they go red only under refusal-shaped mutations
# (a raise at ``set_pfields`` or ``set_instrument``), which kills their
# setup. No mutation of the table merge itself reddens them, which is the
# point -- they testify about lowering, not about the table.

def test_defence_in_depth_pfield_start_does_not_move_the_note():
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    uc.set_pfields(uc._rt.leaf_nodes[1], start=999.0)
    assert [e['start'] for e in convert_to_sc_events(uc)] == [0.0, 1.0, 2.0, 3.0]


def test_defence_in_depth_pfield_dur_does_not_stretch_the_note():
    uc = _unit()
    uc.set_instrument(list(uc._rt.leaf_nodes),
                      SynthDefInstrument.from_manifest('kl_kicktone'))
    uc.set_pfields(uc._rt.leaf_nodes[1], dur=999.0)
    assert [e['dur'] for e in convert_to_sc_events(uc)] == [1.0, 1.0, 1.0, 1.0]
