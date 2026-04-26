"""
Before/After equivalence tests for the UC API Simplification.

These tests verify that the NEW API (callables in set_pfields, Patterns in
set_instrument, sparsify, repeat, __getattr__ delegation, etc.) produces
IDENTICAL musical output to the current "before" code.

Each test has a "before" version using the current API and an "after" version
using the proposed new API. Both use the same random seed and must produce
the same event data.

The "after" tests are marked with @pytest.mark.xfail(reason="new API not yet
implemented") so the test suite passes before implementation. Remove the xfail
markers as each feature is implemented.

Abbreviations (from French musical terminology):
    RT  = RhythmTree
    UT  = TemporalUnit
    UTS = TemporalUnitSequence
    BT  = TemporalBlock
    UC  = CompositionalUnit
    PT  = ParameterTree
"""

import pytest
import numpy as np
from fractions import Fraction

from klotho.chronos import RhythmTree as RT
from klotho.chronos import (
    TemporalUnit as UT,
    TemporalUnitSequence as UTS,
    TemporalBlock as BT,
)
from klotho.thetos import (
    CompositionalUnit as UC,
    ToneInstrument as JsInst,
)
from klotho.topos import Pattern
from klotho.tonos import Scale


FLOAT_TOL = 1e-4


def extract_unit_events(unit):
    events = []
    for e in unit:
        pf = e.pfields
        inst = e._resolve_instrument()
        events.append({
            'node_id': e.node_id,
            'start': e.start,
            'duration': e.duration,
            'is_rest': e.is_rest,
            'instrument_name': inst.name if inst is not None else None,
            'freq': pf.get('freq'),
            'vel': pf.get('vel'),
        })
    return events


def assert_events_equal(events_a, events_b):
    assert len(events_a) == len(events_b), (
        f"Event count mismatch: {len(events_a)} vs {len(events_b)}")
    for i, (a, b) in enumerate(zip(events_a, events_b)):
        assert a['node_id'] == b['node_id'], (
            f"Event {i}: node_id {a['node_id']} != {b['node_id']}")
        assert abs(a['start'] - b['start']) < FLOAT_TOL, (
            f"Event {i}: start {a['start']} != {b['start']}")
        assert abs(a['duration'] - b['duration']) < FLOAT_TOL, (
            f"Event {i}: dur {a['duration']} != {b['duration']}")
        assert a['is_rest'] == b['is_rest'], (
            f"Event {i}: is_rest {a['is_rest']} != {b['is_rest']}")
        assert a['instrument_name'] == b['instrument_name'], (
            f"Event {i}: instrument {a['instrument_name']} != {b['instrument_name']}")
        if a['freq'] is not None and b['freq'] is not None:
            assert abs(a['freq'] - b['freq']) < FLOAT_TOL, (
                f"Event {i}: freq {a['freq']} != {b['freq']}")
        else:
            assert a['freq'] == b['freq'], (
                f"Event {i}: freq {a['freq']} != {b['freq']}")
        if a['vel'] is not None and b['vel'] is not None:
            assert abs(a['vel'] - b['vel']) < FLOAT_TOL, (
                f"Event {i}: vel {a['vel']} != {b['vel']}")
        else:
            assert a['vel'] == b['vel'], (
                f"Event {i}: vel {a['vel']} != {b['vel']}")


# ---------------------------------------------------------------------------
# Example 1: "Chronostasis" — Two voices with instrument Patterns and random vel
# ---------------------------------------------------------------------------

def _build_chronostasis_before():
    tempus = '10/16'
    beat = '1/16'
    bpm = 140
    n_bars = 2
    S1 = ((3, (1,)*4), (4, (1,)*6), (3, (1,)*4))
    S2 = ((5, (1,)*5),)*2

    inst_pat_1 = Pattern([JsInst.HatClosed(), [JsInst.HatClosed(),
        [[JsInst.TomHigh(), JsInst.TomMid()],
         [JsInst.HatOpen(), [JsInst.Ride(decay=0.2), JsInst.HatClosed()]]]]])
    uts1 = UTS()
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1.extend([uc1]*n_bars)
    for unit in uts1:
        for leaf in unit.rt.leaf_nodes:
            unit.set_instrument(leaf, next(inst_pat_1))
            unit.set_pfields(leaf, vel=np.random.uniform(0.001, 0.25))

    inst_pat_2 = Pattern([[[JsInst.Kick('kick_punchy', punch=16),
        JsInst.Kick('kick_pitchy', pitchDecay=0.05, decay=0.9)],
        JsInst.Snare()], JsInst.Kick()])
    uts2 = UTS()
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2.extend([uc2]*n_bars)
    for unit in uts2:
        for leaf in unit.rt.leaf_nodes:
            unit.set_instrument(leaf, next(inst_pat_2))
            unit.set_pfields(leaf, vel=np.random.uniform(0.75, 0.9))

    return BT([uts1, uts2])


def _build_chronostasis_after():
    tempus = '10/16'
    beat = '1/16'
    bpm = 140
    n_bars = 2
    S1 = ((3, (1,)*4), (4, (1,)*6), (3, (1,)*4))
    S2 = ((5, (1,)*5),)*2

    inst_pat_1 = Pattern([JsInst.HatClosed(), [JsInst.HatClosed(),
        [[JsInst.TomHigh(), JsInst.TomMid()],
         [JsInst.HatOpen(), [JsInst.Ride(decay=0.2), JsInst.HatClosed()]]]]])
    uc1 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    uts1 = uc1.repeat(n_bars)
    for unit in uts1:
        unit.set_instrument(unit.leaves, inst_pat_1)
        unit.set_pfields(unit.leaves, vel=lambda: np.random.uniform(0.001, 0.25))

    inst_pat_2 = Pattern([[[JsInst.Kick('kick_punchy', punch=16),
        JsInst.Kick('kick_pitchy', pitchDecay=0.05, decay=0.9)],
        JsInst.Snare()], JsInst.Kick()])
    uc2 = UC(tempus=tempus, prolatio=S2, beat=beat, bpm=bpm)
    uts2 = uc2.repeat(n_bars)
    for unit in uts2:
        unit.set_instrument(unit.leaves, inst_pat_2)
        unit.set_pfields(unit.leaves, vel=lambda: np.random.uniform(0.75, 0.9))

    return BT([uts1, uts2])


class TestChronostasisEquivalence:

    def test_before_produces_expected(self):
        np.random.seed(42)
        block = _build_chronostasis_before()
        rows = list(block)
        v1_u0 = extract_unit_events(rows[0][0])
        assert len(v1_u0) == 14
        assert v1_u0[0]['instrument_name'] == 'HatClosed'
        assert abs(v1_u0[0]['vel'] - 0.09426) < 0.001
        v2_u0 = extract_unit_events(rows[1][0])
        assert v2_u0[0]['instrument_name'] == 'kick_punchy'
        assert abs(v2_u0[0]['vel'] - 0.838862) < 0.001

    def test_after_matches_before(self):
        np.random.seed(42)
        block_before = _build_chronostasis_before()

        np.random.seed(42)
        block_after = _build_chronostasis_after()

        rows_before = list(block_before)
        rows_after = list(block_after)
        assert len(rows_before) == len(rows_after)

        for row_b, row_a in zip(rows_before, rows_after):
            for unit_b, unit_a in zip(row_b, row_a):
                events_b = extract_unit_events(unit_b)
                events_a = extract_unit_events(unit_a)
                assert_events_equal(events_b, events_a)


# ---------------------------------------------------------------------------
# Example 2: "Entertain Me" — Melody with mfield-driven pitch assignment
# ---------------------------------------------------------------------------

def _build_entertain_me_melody_before():
    tempus = '36/16'
    beat = '1/8'
    bpm = 184
    S1 = ((20, ((5, (1,)*5),)*4), (15, ((3, (1,)*3),)*5))
    scale = Scale.phrygian().root('B3')

    uc_mel = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Kalimba())
    limbs = uc_mel.rt.at_depth(1)
    uc_mel.set_mfields(limbs[0], idx=0, drct=1, offset=0)
    uc_mel.set_mfields(limbs[1], idx=len(scale), drct=-1, offset=0)
    successors = list(uc_mel.rt.successors(limbs[-1]))
    for k, node in enumerate(successors):
        uc_mel.set_mfields(node, offset=len(successors) - k)

    for b, branch in enumerate(uc_mel.rt.at_depth(2)):
        for k, leaf in enumerate(uc_mel.rt.descendants(branch)):
            offset = uc_mel.get_mfield(leaf, 'offset')
            idx = uc_mel.get_mfield(leaf, 'idx')
            drct = uc_mel.get_mfield(leaf, 'drct')
            scl_idx = offset + idx + drct*k
            uc_mel.set_pfields(leaf, freq=scale[scl_idx].freq)

    return uc_mel


def _build_entertain_me_melody_after():
    tempus = '36/16'
    beat = '1/8'
    bpm = 184
    S1 = ((20, ((5, (1,)*5),)*4), (15, ((3, (1,)*3),)*5))
    scale = Scale.phrygian().root('B3')

    uc_mel = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Kalimba())
    limbs = uc_mel.at_depth(1)
    uc_mel.set_mfields(limbs[0], idx=0, drct=1, offset=0)
    uc_mel.set_mfields(limbs[1], idx=len(scale), drct=-1, offset=0)
    uc_mel.set_mfields(
        list(uc_mel.successors(limbs.last)),
        offset=lambda c: c.total - c.index)

    for branch in uc_mel.at_depth(2):
        uc_mel.set_pfields(
            uc_mel.leaves_of(branch),
            freq=lambda c: scale[
                c.mfields['offset'] + c.mfields['idx'] + c.mfields['drct'] * c.index
            ].freq)

    return uc_mel


class TestEntertainMeMelodyEquivalence:

    def test_before_produces_expected(self):
        uc = _build_entertain_me_melody_before()
        events = list(uc)
        assert len(events) == 35
        assert all(not e.is_rest for e in events)
        freqs = [e.pfields.get('freq') for e in events]
        assert all(f is not None and f > 0 for f in freqs)

    def test_after_matches_before(self):
        uc_before = _build_entertain_me_melody_before()
        uc_after = _build_entertain_me_melody_after()
        events_before = extract_unit_events(uc_before)
        events_after = extract_unit_events(uc_after)
        assert_events_equal(events_before, events_after)


# ---------------------------------------------------------------------------
# Example 2: "Entertain Me" — Drum voice with subtree instruments
# ---------------------------------------------------------------------------

def _build_entertain_me_drums_before():
    tempus = '36/16'
    beat = '1/8'
    bpm = 184
    S1 = ((20, ((5, (1,)*5),)*4), (15, ((3, (1,)*3),)*5))

    uc_ds = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    limbs = uc_ds.rt.at_depth(1)
    ds_pat = Pattern([[JsInst.Kick(), JsInst.Snare()], JsInst.HatClosed()])

    for k, node in enumerate(uc_ds.rt.subtree_leaves(limbs[0])):
        uc_ds.set_instrument(node, next(ds_pat))
    for k, node in enumerate(uc_ds.rt.subtree_leaves(limbs[-1])):
        uc_ds.set_instrument(node, JsInst.HatOpen(vel=0.1) if k % 2 == 0 else JsInst.HatClosed())

    return uc_ds


def _build_entertain_me_drums_after():
    tempus = '36/16'
    beat = '1/8'
    bpm = 184
    S1 = ((20, ((5, (1,)*5),)*4), (15, ((3, (1,)*3),)*5))

    uc_ds = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm)
    limbs = uc_ds.at_depth(1)

    uc_ds.set_instrument(
        uc_ds.leaves_of(limbs.first),
        Pattern([[JsInst.Kick(), JsInst.Snare()], JsInst.HatClosed()]))
    uc_ds.set_instrument(
        uc_ds.leaves_of(limbs.last),
        lambda c: JsInst.HatOpen(vel=0.1) if c.index % 2 == 0 else JsInst.HatClosed())

    return uc_ds


class TestEntertainMeDrumsEquivalence:

    def test_before_produces_expected(self):
        uc = _build_entertain_me_drums_before()
        events = [e for e in uc if not e.is_rest]
        inst_names = [e._resolve_instrument().name for e in events if e._resolve_instrument() is not None]
        assert 'Kick' in inst_names
        assert 'HatClosed' in inst_names

    def test_after_matches_before(self):
        uc_before = _build_entertain_me_drums_before()
        uc_after = _build_entertain_me_drums_after()
        events_before = extract_unit_events(uc_before)
        events_after = extract_unit_events(uc_after)
        assert_events_equal(events_before, events_after)


# ---------------------------------------------------------------------------
# Example 3: "Polyriddim" — Voice 3 (bass) with sparsify + freq/vel lambdas
# ---------------------------------------------------------------------------

def _build_polyriddim_bass_before():
    S1 = ((1, ((6, (1,)*7), (8, (1,)*11))),
          (1, ((6, ((3, (1,)*4), 1, (2, (1,)*3))),
               (8, ((3, (1,)*4), (3, (1,)*4), (5, (1,)*5))))),
          (1, ((6, (2, (3, (1,)*4), (2, (1,)*4))),
               (8, ((2, (1,)*3), (2, (1,)*4), (2, (1,)*5), (2, (1,)*5))))),
          (1, ((6, ((2, (1,)*3), (2, (1,)*3), (2, (1,)*3))),
               (8, (5, (6, (1,)*11))))))
    tempus = '28/16'
    beat = '1/16'
    bpm = 122.5
    n_bars = 2
    scale = Scale.locrian().root('Eb2')
    scl_pat = Pattern([[0, -1, [0, -3]], [1, [3, 4]]])

    uts3 = UTS()
    uc3 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Bassy())
    uts3.extend([uc3]*n_bars)
    for unit in uts3:
        for k, node in enumerate(unit.rt.leaf_nodes):
            if np.random.uniform() < 0.67:
                unit.make_rest(node)
                continue
            unit.set_pfields(node, freq=scale[next(scl_pat)].freq,
                             vel=np.random.uniform(0.1, 0.5))
    return uts3


def _build_polyriddim_bass_after():
    S1 = ((1, ((6, (1,)*7), (8, (1,)*11))),
          (1, ((6, ((3, (1,)*4), 1, (2, (1,)*3))),
               (8, ((3, (1,)*4), (3, (1,)*4), (5, (1,)*5))))),
          (1, ((6, (2, (3, (1,)*4), (2, (1,)*4))),
               (8, ((2, (1,)*3), (2, (1,)*4), (2, (1,)*5), (2, (1,)*5))))),
          (1, ((6, ((2, (1,)*3), (2, (1,)*3), (2, (1,)*3))),
               (8, (5, (6, (1,)*11))))))
    tempus = '28/16'
    beat = '1/16'
    bpm = 122.5
    n_bars = 2
    scale = Scale.locrian().root('Eb2')
    scl_pat = Pattern([[0, -1, [0, -3]], [1, [3, 4]]])

    uc3 = UC(tempus=tempus, prolatio=S1, beat=beat, bpm=bpm, inst=JsInst.Bassy())
    uts3 = uc3.repeat(n_bars)
    for unit in uts3:
        unit.sparsify(0.67)
        unit.set_pfields(unit.leaves,
                         freq=lambda: scale[next(scl_pat)].freq,
                         vel=lambda: np.random.uniform(0.1, 0.5))
    return uts3


class TestPolyriddimBassEquivalence:

    def test_before_produces_expected(self):
        np.random.seed(42)
        uts = _build_polyriddim_bass_before()
        unit0_nonrest = [e for e in uts[0] if not e.is_rest]
        assert len(unit0_nonrest) == 24
        assert abs(unit0_nonrest[0].pfields.get('freq') - 77.7817) < 0.01

    def test_after_structural_equivalence(self):
        np.random.seed(42)
        uts_before = _build_polyriddim_bass_before()
        before_rest_counts = []
        before_nonrest_counts = []
        for unit in uts_before:
            events = list(unit)
            before_rest_counts.append(sum(1 for e in events if e.is_rest))
            before_nonrest_counts.append(sum(1 for e in events if not e.is_rest))

        np.random.seed(42)
        uts_after = _build_polyriddim_bass_after()
        after_rest_counts = []
        after_nonrest_counts = []
        for unit in uts_after:
            events = list(unit)
            after_rest_counts.append(sum(1 for e in events if e.is_rest))
            after_nonrest_counts.append(sum(1 for e in events if not e.is_rest))

        assert len(list(uts_before)) == len(list(uts_after))
        for i in range(len(before_rest_counts)):
            total_b = before_rest_counts[i] + before_nonrest_counts[i]
            total_a = after_rest_counts[i] + after_nonrest_counts[i]
            assert total_b == total_a

        for unit in uts_after:
            for e in unit:
                if not e.is_rest:
                    pf = e.pfields
                    assert pf.get('freq') is not None and pf.get('freq') > 0
                    assert pf.get('vel') is not None and 0.1 <= pf.get('vel') <= 0.5


# ---------------------------------------------------------------------------
# __getattr__ delegation tests (Change 1)
# ---------------------------------------------------------------------------

class TestUCTraversalSurface:
    """UC traversal returns selectors bound to the UC; raw tree access remains
    available via ``uc._rt`` / ``uc.rt`` for dropped methods."""

    def test_leaves_selector_matches_rt_leaf_nodes(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc.leaves == uc.rt.leaf_nodes

    def test_at_depth_selector_matches_rt_at_depth(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc.at_depth(1) == uc.rt.at_depth(1)

    def test_leaves_of_selector_matches_rt_subtree_leaves(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc.leaves_of(1) == uc.rt.subtree_leaves(1)

    def test_successors_selector_matches_rt_successors(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert list(uc.successors(0)) == list(uc.rt.successors(0))

    def test_descendants_via_rt_escape_hatch(self):
        # Descendants dropped from UC surface; still reachable via uc._rt
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert list(uc._rt.descendants(1)) == list(uc.rt.descendants(1))
        with pytest.raises(AttributeError):
            uc.descendants(1)

    def test_ancestors_via_rt_escape_hatch(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc._rt.ancestors(4) == uc.rt.ancestors(4)
        with pytest.raises(AttributeError):
            uc.ancestors(4)

    def test_parent_via_rt_escape_hatch(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc._rt.parent(2) == uc.rt.parent(2)
        with pytest.raises(AttributeError):
            uc.parent(2)

    def test_depth_scalar_forward(self):
        uc = UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1), beat='1/4', bpm=120)
        assert uc.depth == uc.rt.depth

    def test_nodes_property(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        assert uc.nodes[1]['proportion'] == 1

    def test_nonexistent_attr_raises(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        with pytest.raises(AttributeError):
            _ = uc.nonexistent_method


# ---------------------------------------------------------------------------
# repeat method tests (Change 7)
# ---------------------------------------------------------------------------

class TestRepeatMethod:

    def test_repeat_returns_uts(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)
        uts = uc.repeat(3)
        assert isinstance(uts, UTS)
        assert len(uts.seq) == 3

    def test_repeat_copies_are_independent(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.set_pfields(1, freq=100)
        uts = uc.repeat(2)
        uts[0].set_pfields(1, freq=999)
        assert uts[0].get_pfield(1, 'freq') == 999
        assert uts[1].get_pfield(1, 'freq') == 100

    def test_repeat_preserves_state(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.set_pfields(1, freq=100)
        uc.make_rest(3)
        uts = uc.repeat(2)
        for unit in uts:
            events = list(unit)
            assert events[0].pfields.get('freq') == 100
            assert events[2].is_rest is True


# ---------------------------------------------------------------------------
# sparsify method tests (Change 5)
# ---------------------------------------------------------------------------

class TestSparsifyMethod:

    def test_sparsify_basic(self):
        np.random.seed(42)
        uc = UC(tempus='4/4', prolatio=(1,)*8, beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.sparsify(0.5)
        rest_count = sum(1 for e in uc if e.is_rest)
        assert 0 < rest_count < 8

    def test_sparsify_zero_prob(self):
        uc = UC(tempus='4/4', prolatio=(1,)*8, beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.sparsify(0.0)
        rest_count = sum(1 for e in uc if e.is_rest)
        assert rest_count == 0

    def test_sparsify_one_prob(self):
        uc = UC(tempus='4/4', prolatio=(1,)*8, beat='1/4', bpm=120, inst=JsInst.Kick())
        uc.sparsify(1.0)
        rest_count = sum(1 for e in uc if e.is_rest)
        assert rest_count == 8

    def test_sparsify_scoped_to_subtree(self):
        uc = UC(tempus='4/4', prolatio=((3, (1,)*3), (2, (1,)*2)),
                beat='1/4', bpm=120, inst=JsInst.Kick())
        limbs = uc.rt.at_depth(1)
        uc.sparsify(1.0, node=limbs[0])
        events = list(uc)
        limb0_leaves = set(uc.rt.subtree_leaves(limbs[0]))
        limb1_leaves = set(uc.rt.subtree_leaves(limbs[1]))
        for e in events:
            if e.node_id in limb0_leaves:
                assert e.is_rest is True
            if e.node_id in limb1_leaves:
                assert e.is_rest is False
