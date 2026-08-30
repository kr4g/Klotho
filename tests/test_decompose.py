"""Regression tests for decompose truth-preservation.

decompose must never silently lose, add, or reorder musical material:
no dropped branches (WL-45), no lost per-leaf parameters (WL-25a),
no rests turned into sounding units (NEW-02), no empty results from an
out-of-range depth (NEW-01), and depth=0 means the root, not the leaves
(WL-25c). IDs refer to the klotho-evolution triage catalog.
"""
import pytest

from klotho.chronos.temporal_units import TemporalUnit, decompose
from klotho.thetos import CompositionalUnit as UC


ASYM_S = ((3, ((1, (2, 1, 1)), (2, (1, 1)), (1, ()))),
          (2, ((1, (3, 1, 2)), (1, (1, 1, 1)))),
          (1, ()))


@pytest.fixture
def asym_ut():
    return TemporalUnit(tempus='4/4', prolatio=ASYM_S, bpm=120)


def _all_leaf_durations(uts):
    return [d for u in uts for d in u.durations]


class TestLeafBranchTruth:
    def test_cu_leaf_decompose_preserves_per_leaf_pfields(self):
        # WL-25a: without depth=, every authored pfield came back 0.0
        uc = UC(tempus='5/4', prolatio=(1, 1, 1, 1, 1), pfields=['amp'])
        for i, leaf in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(leaf, amp=(i + 1) / 10)
        units = decompose(uc)
        assert [u[0].pfields['amp'] for u in units] == pytest.approx(
            [0.1, 0.2, 0.3, 0.4, 0.5])

    def test_cu_leaf_decompose_with_prolatio_cascades_leaf_pfields(self):
        # WL-25a: an explicit prolatio reshapes each leaf; the source leaf's
        # effective pfields must cascade from the new unit's root
        uc = UC(tempus='3/4', prolatio=(1, 1, 1), pfields=['amp'])
        for i, leaf in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(leaf, amp=(i + 1) / 10)
        units = decompose(uc, prolatio=(1, 1))
        for i, u in enumerate(units):
            sounding = [c for c in u if not c.is_rest]
            assert len(sounding) == 2
            assert [c.pfields['amp'] for c in sounding] == pytest.approx(
                [(i + 1) / 10] * 2)

    def test_cu_leaf_decompose_preserves_rests(self):
        # NEW-02 (CU side): silence must stay silence
        uc = UC(tempus='3/4', prolatio=(1, -1, 1), pfields=['amp'])
        units = decompose(uc)
        assert [[c.is_rest for c in u] for u in units] == [[False], [True], [False]]

    def test_ut_leaf_decompose_preserves_rests(self):
        # NEW-02: leaf branch used abs(ratio) + 'd', so rests became audio
        ut = TemporalUnit(tempus='3/4', prolatio=(1, -1, 1), bpm=120)
        units = decompose(ut)
        assert [[c.is_rest for c in u] for u in units] == [[False], [True], [False]]
        assert [abs(d) for d in _all_leaf_durations(units)] == pytest.approx(
            [0.5, 0.5, 0.5])

    def test_ut_leaf_decompose_rest_with_explicit_prolatio_stays_rest(self):
        # NEW-02: subdividing a rest must not produce attacks
        ut = TemporalUnit(tempus='3/4', prolatio=(1, -1, 1), bpm=120)
        units = decompose(ut, prolatio=(1, 1))
        assert all(not c.is_rest for c in units[0])
        assert all(c.is_rest for c in units[1])
        assert all(not c.is_rest for c in units[2])

    def test_ut_leaf_decompose_sounding_durations_unchanged(self):
        # guard: the leaf branch's timing behavior for sounding leaves stands
        ut = TemporalUnit(tempus='4/4', prolatio=(2, 1, 1), bpm=120)
        units = decompose(ut)
        assert [float(u.duration) for u in units] == pytest.approx([1.0, 0.5, 0.5])


class TestDepthValidation:
    def test_depth_zero_decomposes_at_root(self):
        # WL-25c: `if depth:` treated depth=0 as absent and fell through
        # to the leaf branch
        ut = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))), bpm=120)
        units = decompose(ut, depth=0)
        assert len(units) == 1
        assert len(list(units[0])) == 4
        assert float(units[0].duration) == pytest.approx(float(ut.duration))

    def test_depth_beyond_tree_depth_raises(self, asym_ut):
        # NEW-01: used to return an EMPTY sequence silently (total loss)
        with pytest.raises(ValueError, match="depth"):
            decompose(asym_ut, depth=10)

    def test_negative_depth_raises(self, asym_ut):
        with pytest.raises(ValueError, match="depth"):
            decompose(asym_ut, depth=-1)

    def test_cu_prolatio_with_depth_raises(self):
        # WL-25b: prolatio was silently ignored on a CompositionalUnit with
        # depth=. Honouring it would discard the per-leaf data the depth
        # branch exists to preserve, so the combination refuses loudly.
        uc = UC(tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))), pfields=['amp'])
        with pytest.raises(ValueError, match="prolatio"):
            decompose(uc, prolatio=(1, 1, 1), depth=1)


class TestDepthFrontier:
    def test_frontier_preserves_total_duration_and_leaf_count(self, asym_ut):
        # WL-45: branches shallower than depth were silently dropped
        # (13 leaves / 2.0 s came back as 12 leaves / 1.667 s at depth=2)
        source_durations = list(asym_ut.durations)
        for depth in (1, 2, 3):
            units = decompose(asym_ut, depth=depth)
            total = sum(float(u.duration) for u in units)
            assert total == pytest.approx(float(asym_ut.duration)), depth
            assert len(_all_leaf_durations(units)) == len(source_durations), depth

    def test_frontier_orders_shallow_leaves_by_onset(self, asym_ut):
        # WL-45: a shallow leaf must interleave positionally, not append —
        # the decomposed sequence must sound identical to the source
        source_durations = list(asym_ut.durations)
        units = decompose(asym_ut, depth=2)
        assert _all_leaf_durations(units) == pytest.approx(source_durations)

    def test_frontier_cu_preserves_authored_values(self):
        # WL-45 on a CompositionalUnit: the dropped branch's authored
        # values vanished with it
        uc = UC(tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1)), 1),
                pfields=['amp'])
        for i, leaf in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(leaf, amp=(i + 1) / 10)
        units = decompose(uc, depth=2)
        amps = [c.pfields['amp'] for u in units for c in u if not c.is_rest]
        assert amps == pytest.approx([0.1, 0.2, 0.3, 0.4, 0.5])
        total = sum(float(u.duration) for u in units)
        assert total == pytest.approx(float(uc.duration))

    def test_frontier_rest_leaf_stays_rest(self):
        # NEW-02's class in the depth branch: a rest leaf on the frontier
        # was rebuilt as a sounding unit
        ut = TemporalUnit(tempus='3/4', prolatio=(1, -1, 1), bpm=120)
        units = decompose(ut, depth=1)
        assert [[c.is_rest for c in u] for u in units] == [[False], [True], [False]]

    def test_ut_depth_prolatio_override_still_applies(self):
        # guard: on a plain TemporalUnit, an explicit prolatio re-prolates
        # each depth unit (existing, wanted behavior)
        ut = TemporalUnit(tempus='4/4', prolatio=((1, (1, 1)), (1, (1, 1))), bpm=120)
        units = decompose(ut, prolatio=(1, 1, 1), depth=1)
        assert [u.prolationis for u in units] == [(1, 1, 1), (1, 1, 1)]

    def test_frontier_rest_group_with_prolatio_stays_rest(self):
        # RT-11/NEW-02 in the depth branch: the rest test only looked at
        # nodes in the leaf set, so a rest GROUP -- an interior node with a
        # negative proportion, a shape the grammar accepts and pins -- fell
        # through to the requested prolatio and was rebuilt as sound.
        # Silence became audio at whole-unit granularity.
        ut = TemporalUnit(tempus='1/1', prolatio=((-1, (1, 1)), 1), bpm=60)
        units = decompose(ut, prolatio=(1, 2), depth=1)
        assert [[c.is_rest for c in u] for u in units] == [[True], [False, False]]
        assert sum(abs(float(u.duration)) for u in units) == pytest.approx(
            float(ut.duration))

    def test_frontier_rest_group_without_prolatio_keeps_its_subdivisions(self):
        # guard on the fix above: the DEFAULT arm must keep riding the
        # node's own signed subdivisions, so a rest group comes back with
        # its internal rhythm intact rather than collapsed to one rest.
        ut = TemporalUnit(tempus='1/1', prolatio=((-1, (1, 1)), 1), bpm=60)
        units = decompose(ut, depth=1)
        assert [u.prolationis for u in units] == [(-1, -1), (1,)]
        assert _all_leaf_durations(units) == pytest.approx(list(ut.durations))


class TestSlurRegression:
    # A slur spanning a frontier that mixes deep subtrees with a bare leaf
    # backfilled from above the frontier depth. `_snip_slur_into_sub_uc`
    # would mis-map if it ever received a bare leaf as `depth_node`
    # (`_path_sig` returns (), and the wrapper root comes back instead of a
    # leaf) -- unreachable today, because a bare leaf's subtree_leaves is
    # itself, so the `len(sounding) < 2` guard short-circuits first. The
    # code is safe by construction, not by luck; these pin the construction.
    SNIP_P = ((1, ((1, (1, 1)), 1)), 1, (1, (1, 1)))   # leaf depths 3,3,2,1,2,2

    @staticmethod
    def _slurred_uc():
        uc = UC(tempus='3/4', prolatio=TestSlurRegression.SNIP_P, bpm=120,
                pfields=['freq'])
        uc.apply_slur(node=list(uc._rt.leaf_nodes))
        return uc

    @pytest.mark.parametrize('depth,n_units', [(1, 3), (2, 5), (3, 6)])
    def test_slur_across_mixed_depth_frontier_conserves_material(self, depth, n_units):
        uc = self._slurred_uc()
        units = decompose(uc, depth=depth)
        assert len(units) == n_units
        assert sum(float(u.duration) for u in units) == pytest.approx(
            float(uc.duration))
        assert _all_leaf_durations(units) == pytest.approx(list(uc.durations))

    def test_slur_across_mixed_depth_frontier_snips_per_unit(self):
        # one source slur becomes two partial slurs in two units; the bare
        # leaf backfilled from above the frontier gets none, and stays in
        # its ordinal position between them
        uc = self._slurred_uc()
        assert [len(u._slur_specs) for u in decompose(uc, depth=1)] == [1, 0, 1]
        assert [len(u._slur_specs) for u in decompose(uc, depth=2)] == [1, 0, 0, 0, 0]
        assert [len(u._slur_specs) for u in decompose(uc, depth=3)] == [0] * 6

    def test_slur_mixed_size_group_max_expansion(self):
        # RUL-01: mixed single/chord/single under one slur expands to the
        # group max at the slur head (unison duplicates), then pure sets —
        # no mid-slur attacks. This pins shipped 10.13 behavior.
        from klotho.utils.playback.supersonic.converters import (
            compositional_unit_to_sc_events,
        )
        uc = UC(tempus='3/4', prolatio=(1, 1, 1), bpm=120, pfields=['freq'])
        leaves = uc.leaves
        uc.set_pfields(leaves[0], freq=440.0)
        uc.set_pfields(leaves[1], freq=(440.0, 550.0, 660.0))
        uc.set_pfields(leaves[2], freq=330.0)
        uc.apply_slur(leaves)
        events = compositional_unit_to_sc_events(uc)

        news = [e for e in events if e['type'] == 'new' and e['defName'] != '__rest__']
        sets = [e for e in events if e['type'] == 'set']
        assert len(news) == 3
        assert all(e['start'] == pytest.approx(0.0) for e in news)
        assert [e['pfields']['freq'] for e in news] == pytest.approx([440.0] * 3)
        assert sorted({round(e['start'], 6) for e in sets}) == [0.5, 1.0]
        assert sorted(e['pfields']['freq'] for e in sets if e['start'] == pytest.approx(0.5)) == \
            pytest.approx([440.0, 550.0, 660.0])
        assert all(e['start'] == pytest.approx(0.0) for e in events
                   if e['type'] == 'new' and e.get('defName') != '__rest__')
