"""Targeted regression guards for surfaces the performance work touches.

Coverage analysis (2026-08-08) showed these behaviors had no test that
would fail if they broke:

- ``UTNodeHandle.real_onset``/``real_duration`` and the Chronon dict-like
  read surface (``get``/``__contains__``/``__getitem__``) — the exact read
  sites the offset-relative timing cache rewrite modifies;
- the offset-INCLUSIVE ``abs()`` semantics of ``Chronon.start``;
- slur and control-envelope healing after ``subdivide``/``make_rest`` —
  invoked through ``_post_mutation``, whose cadence the batch-subdivide
  rework changes;
- ``resolved_control_envelopes`` target/time-span mapping.
"""
import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.chronos import TemporalUnitSequence as UTS
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.instruments.synthdef import SynthDefInstrument


def _inst(name='guard_probe'):
    return SynthDefInstrument(
        name=name, defName='kl_tri',
        pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0})


def _uc(prolatio=(1, 1, 1, 1)):
    return UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
              inst=_inst(), pfields=['amp'])


class TestNodeHandleRealTimes:
    def test_leaf_handle_onsets_and_durations(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        onsets = [h.real_onset for h in ut.leaves]
        durs = [h.real_duration for h in ut.leaves]
        assert onsets == [0.0, 1.0, 2.0, 3.0]
        assert durs == [1.0, 1.0, 1.0, 1.0]

    def test_handle_onset_includes_container_offset(self):
        a = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        b = UT(tempus='4/4', prolatio=(1, 1), beat='1/4', bpm=60)
        uts = UTS([a, b])
        assert uts[1].leaves.first.real_onset == 4.0
        assert [e.start for e in uts[1]] == [4.0, 6.0]

    def test_root_handle_spans_unit(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        root = ut.root.first
        assert root.real_onset == 0.0
        assert root.real_duration == 4.0


class TestChrononReadSurface:
    def test_dict_like_reads(self):
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        ev = ut[1]
        assert ev['real_onset'] == 1.0
        assert ev.get('real_onset') == 1.0
        assert ev.real_onset == 1.0
        assert 'real_onset' in ev
        assert 'real_duration' in ev
        assert ev.get('not_a_key', 42) == 42
        assert 'not_a_key' not in ev
        # non-timing keys still route to node data
        assert 'metric_duration' in ev
        assert ev.get('metric_duration') == ev['metric_duration']

    def test_rest_duration_is_abs_of_negative_real_duration(self):
        ut = UT(tempus='3/4', prolatio=(1, -1, 1), beat='1/4', bpm=60)
        rest = ut[1]
        assert rest['real_duration'] == -1.0
        assert rest.duration == 1.0
        assert rest.end == rest.start + 1.0

    def test_start_abs_wraps_offset_inclusive_value(self):
        """Chronon.start takes abs() of the offset-INCLUSIVE onset — a
        unit shifted to negative time reports positive magnitudes. The
        offset-relative cache rewrite must keep the offset inside the
        abs(), not add it afterwards."""
        from klotho.chronos.temporal_units.temporal import _reoffset
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60)
        _reoffset(ut, -2.0)
        assert ut[0]['real_onset'] == -2.0
        assert ut[0].start == 2.0
        assert ut[1]['real_onset'] == -1.0
        assert ut[1].start == 1.0
        assert ut[2].start == 0.0


class TestTimingCacheInvalidationOnStructuralMutation:
    """UC.add_child/prune/remove_subtree mutate the rhythm tree and must
    invalidate the timing cache explicitly: the cache guard compares node
    counts, so a mutation sequence with a net-zero node-count change
    (prune then add_child) would otherwise serve stale onsets."""

    def test_prune_then_add_child_serves_fresh_timings(self):
        uc = _uc(prolatio=(1, (1, (1, 1)), 1))
        before = uc.durations  # warm the cache
        branch = next(
            n for n in uc._rt.nodes
            if n != uc._rt.root and n not in set(uc._rt.leaf_nodes))
        uc.prune(branch)
        uc.add_child(uc._rt.root, proportion=2)
        # node count is back to its pre-mutation value; only explicit
        # invalidation makes these reads recompute. A fresh structural
        # copy computes its cache from scratch off the same tree data.
        fresh = uc.copy()
        assert uc.durations == fresh.durations
        assert uc.onsets == fresh.onsets
        assert uc.durations != before  # the mutation really moved timings

    def test_add_child_refreshes_timings(self):
        uc = _uc()
        _ = uc.onsets
        uc.add_child(uc._rt.root, proportion=1)
        assert uc.durations == _uc(prolatio=(1, 1, 1, 1, 1)).durations

    def test_remove_subtree_refreshes_timings(self):
        uc = _uc()
        _ = uc.onsets
        uc.remove_subtree(list(uc._rt.leaf_nodes)[-1])
        assert uc.durations == _uc(prolatio=(1, 1, 1)).durations


class TestTraversalCacheSemantics:
    """Per-instance version-keyed traversal caches (formerly process-global
    @lru_cache: any write to any tree cleared every tree's cache and pinned
    instances against GC via the strong self keys)."""

    def test_branch_refreshes_after_structural_mutation(self):
        # the old @lru_cache on Tree.branch was never cache_clear()'d
        uc = _uc()
        leaf = list(uc._rt.leaf_nodes)[0]
        assert uc._rt.branch(leaf) == (uc._rt.root, leaf)
        uc.subdivide(leaf, 2)
        child = uc._rt.successors(leaf)[0]
        assert uc._rt.branch(child) == (uc._rt.root, leaf, child)
        assert uc._rt.branch(leaf) == (uc._rt.root, leaf)

    def test_traversals_refresh_after_mutation(self):
        uc = _uc()
        root = uc._rt.root
        before = uc._rt.descendants(root)
        new = uc.add_child(root, proportion=1)
        after = uc._rt.descendants(root)
        assert new in after and new not in before
        assert uc._rt.parent(new) == root
        assert new in uc._rt.successors(root)
        assert uc._rt.ancestors(new) == (root,)

    def test_instances_do_not_share_cache_state(self):
        a, b = _uc(), _uc()
        a_succ = a._rt.successors(a._rt.root)
        b.add_child(b._rt.root, proportion=1)
        assert a._rt.successors(a._rt.root) == a_succ
        assert len(b._rt.successors(b._rt.root)) == 5

    def test_warm_caches_do_not_pin_trees_against_gc(self):
        import gc
        import weakref
        uc = _uc()
        tree = uc._rt
        _ = tree.descendants(tree.root)
        _ = tree.parent(list(tree.leaf_nodes)[0])
        ref = weakref.ref(tree)
        del uc, tree
        gc.collect()
        assert ref() is None, 'tree kept alive by traversal caches'


class TestSlurHealingAfterMutation:
    def _slurred_leaf_ids(self, uc):
        return {n for spec in uc._slur_specs.values()
                for n in spec['leaf_nodes']}

    def test_subdivide_extends_slur_over_new_leaves(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=leaves[:3])
        assert len(uc._slur_specs) == 1
        uc.subdivide(leaves[1], 2)
        assert len(uc._slur_specs) == 1
        healed = next(iter(uc._slur_specs.values()))
        # old middle leaf replaced by its two children; span now 4 leaves
        assert len(healed['leaf_nodes']) == 4
        assert leaves[1] not in healed['leaf_nodes']
        assert leaves[0] in healed['leaf_nodes']
        assert leaves[2] in healed['leaf_nodes']

    def test_make_rest_splits_slur_and_drops_short_segments(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=leaves)  # slur across all four leaves
        uc.make_rest(leaves[1])
        # segment [l0] is too short to keep; [l2, l3] survives as one slur
        assert len(uc._slur_specs) == 1
        surviving = next(iter(uc._slur_specs.values()))
        assert list(surviving['leaf_nodes']) == leaves[2:]


class TestEnvelopeHealingAfterMutation:
    def test_subdivide_rebakes_root_anchored_envelope(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[4.0]), 'amp',
                          node=uc._rt.root, control=True)
        uc.subdivide(leaves[0], 2)
        resolved = uc.resolved_control_envelopes()
        assert len(resolved) == 1
        new_leaves = list(uc._rt.leaf_nodes)
        assert set(resolved[0]['target_nodes']) == set(new_leaves)

    def test_subdivide_remaps_leaf_subset_envelope(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'amp',
                          node=leaves[:2], control=True)
        uc.subdivide(leaves[1], 3)
        resolved = uc.resolved_control_envelopes()
        assert len(resolved) == 1
        targets = set(resolved[0]['target_nodes'])
        assert leaves[1] not in targets
        assert leaves[0] in targets
        assert len(targets) == 4  # l0 + the three children of l1

    def test_make_rest_of_all_targets_removes_envelope(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[1.0]), 'amp',
                          node=leaves[:2], control=True)
        with pytest.warns(RuntimeWarning, match='Control envelope removed'):
            uc.make_rest(leaves[:2])
        assert uc.resolved_control_envelopes() == []


class TestResolvedControlEnvelopeMapping:
    def test_leaf_subset_targets_and_time_span(self):
        uc = _uc()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'pan',
                          node=leaves[1:3], control=True)
        resolved = uc.resolved_control_envelopes()
        assert len(resolved) == 1
        desc = resolved[0]
        assert desc['pfields'] == ['pan']
        assert list(desc['target_nodes']) == leaves[1:3]
        start, end = desc['time_span']
        assert start == uc[1].start
        assert end == pytest.approx(uc[2].end)
