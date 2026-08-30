"""RT-5 -- ``make_sounding``, the reverse of ``make_rest``.

``make_rest`` shipped with no inverse anywhere in the library: there was no
``unrest``, no ``make_sounding``, no way to take a rest back except to
rebuild the tree. Every other structural edit on a RhythmTree could be
undone by another edit; this one could not.

The name is ``make_sounding`` for symmetry with the vocabulary the tie work
already shipped -- ``tie_groups`` counts SOUNDING groups, ``leaves.sounding``
selects SOUNDING leaves. ``unrest`` reads as the noun for turmoil.

Two things make this more than a sign flip, and both are pinned below.

1. ANCESTORS. ``_evaluate`` re-negates any positive child of a negative
   parent, so writing a positive proportion onto a leaf that sits under a
   rested group is silently undone on the next recompute: the call reports
   success and nothing changes. This is the NEW-05 failure class -- an
   operation that cannot express its own result. ``make_sounding``
   therefore un-rests the ancestor chain too.

2. HONEST ASYMMETRY. ``make_rest`` is LOSSY. It clears ``tied``, and at the
   CompositionalUnit level it splits intersecting slurs and drops control
   envelopes, and none of that records its pre-flip state. So this is not
   an inverse in the strict sense: it restores the RHYTHM and cannot
   restore ties, slurs, or envelopes. The tests below assert that plainly
   rather than pretending otherwise.
"""

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units import TemporalUnit
from klotho.thetos.composition.compositional import CompositionalUnit


class TestRhythmTreeMakeSounding:

    def test_a_rested_leaf_comes_back(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1, 1))
        leaf = rt.leaf_nodes[1]
        rt.make_sounding(leaf)
        assert rt[leaf]['proportion'] > 0
        assert rt[leaf]['metric_duration'] > 0

    def test_make_rest_then_make_sounding_restores_the_durations(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        before = rt.durations
        leaf = rt.leaf_nodes[2]
        rt.make_rest(leaf)
        assert rt.durations != before
        rt.make_sounding(leaf)
        assert rt.durations == before

    def test_a_leaf_under_a_rested_parent_actually_comes_back(self):
        """THE test for this item. Writing a positive proportion onto this
        leaf directly is a silent no-op: ``_evaluate`` re-negates it from
        the parent on the next recompute."""
        rt = RhythmTree(span=1, meas='1/1',
                        subdivisions=(1, (1, (1, 1, 1, 1)), 1))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        rt.make_rest(branch)
        leaf = list(rt.subtree_leaves(branch))[0]
        assert rt[leaf]['metric_duration'] < 0

        rt.make_sounding(leaf)
        assert rt[leaf]['proportion'] > 0
        assert rt[leaf]['metric_duration'] > 0

    def test_the_result_survives_a_recompute(self):
        """A fixpoint check: if ``make_sounding`` left the graph in a state
        ``_evaluate`` disagrees with, the next mutation anywhere in the tree
        would quietly re-rest the leaf."""
        rt = RhythmTree(span=1, meas='1/1',
                        subdivisions=(1, (1, (1, 1, 1, 1)), 1))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        rt.make_rest(branch)
        leaf = list(rt.subtree_leaves(branch))[0]
        rt.make_sounding(leaf)
        rt._evaluate()
        assert rt[leaf]['metric_duration'] > 0

    def test_the_ancestor_is_un_rested_but_the_siblings_are_not(self):
        """Un-resting one leaf must not un-rest the whole group -- the group
        node's sign changes because it is no longer entirely silent, while
        every sibling keeps its own negative proportion."""
        rt = RhythmTree(span=1, meas='1/1',
                        subdivisions=(1, (1, (1, 1, 1, 1)), 1))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        rt.make_rest(branch)
        sub_leaves = list(rt.subtree_leaves(branch))
        rt.make_sounding(sub_leaves[0])
        assert rt[branch]['proportion'] > 0
        assert all(rt[n]['metric_duration'] < 0 for n in sub_leaves[1:])

    def test_it_reaches_descendants_like_make_rest_does(self):
        rt = RhythmTree(span=1, meas='1/1',
                        subdivisions=(1, (1, (1, 1, 1, 1)), 1))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        rt.make_rest(branch)
        rt.make_sounding(branch)
        assert all(rt[n]['metric_duration'] > 0 for n in rt.leaf_nodes)

    def test_a_whole_rested_tree_comes_back(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        before = rt.durations
        rt.make_rest(rt.root)
        rt.make_sounding(rt.root)
        assert rt.durations == before

    def test_it_is_a_no_op_on_an_already_sounding_node(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        before = rt.durations
        rt.make_sounding(rt.leaf_nodes[0])
        assert rt.durations == before

    def test_it_is_idempotent(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1, 1))
        leaf = rt.leaf_nodes[1]
        rt.make_sounding(leaf)
        once = rt.durations
        rt.make_sounding(leaf)
        assert rt.durations == once

    def test_an_unknown_node_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='not found'):
            rt.make_sounding(9999)

    def test_onsets_stay_strictly_increasing(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1, 1))
        rt.make_sounding(rt.leaf_nodes[1])
        onsets = list(rt.onsets)
        assert all(b > a for a, b in zip(onsets, onsets[1:]))


class TestTheAsymmetryIsStated:
    """``make_rest`` is lossy, so ``make_sounding`` cannot be a true
    inverse. The docstring must say so instead of implying otherwise."""

    def test_the_tie_is_not_restored(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        leaf = rt.leaf_nodes[1]
        assert rt[leaf]['tied'] is True
        rt.make_rest(leaf)
        rt.make_sounding(leaf)
        assert rt[leaf]['tied'] is False

    def test_the_un_rested_leaf_is_never_left_tied(self):
        """A tied rest is illegal (07_TIES_CHARTER.md sect1); the flip back
        must not manufacture one on the way through either."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        rt.make_rest(rt.leaf_nodes[1])
        rt.make_sounding(rt.leaf_nodes[1])
        assert all(rt[n]['tied'] is False or rt[n]['proportion'] > 0
                   for n in rt.leaf_nodes)

    def test_the_docstring_admits_it_is_not_a_strict_inverse(self):
        doc = RhythmTree.make_sounding.__doc__
        assert 'tie' in doc.lower()
        assert 'not' in doc.lower()

    def test_the_docstring_names_the_ancestor_rule(self):
        doc = RhythmTree.make_sounding.__doc__
        assert 'ancestor' in doc.lower()


class TestTemporalUnitMakeSounding:

    def test_it_accepts_a_single_node(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        node = ut.rt.leaf_nodes[1]
        ut.make_rest(node)
        assert ut.events.loc[1, 'is_rest']
        ut.make_sounding(node)
        assert not ut.events.loc[1, 'is_rest']

    def test_it_accepts_an_iterable(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        nodes = list(ut.rt.leaf_nodes[:2])
        ut.make_rest(nodes)
        ut.make_sounding(nodes)
        assert not ut.events['is_rest'].any()

    def test_the_timing_cache_is_invalidated(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        node = ut.rt.leaf_nodes[1]
        ut.make_rest(node)
        _ = ut.events
        ut.make_sounding(node)
        assert not ut.events.loc[1, 'is_rest']

    def test_the_total_duration_is_unchanged(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        before = ut.duration
        node = ut.rt.leaf_nodes[1]
        ut.make_rest(node)
        ut.make_sounding(node)
        assert ut.duration == pytest.approx(before)


class TestFluentSurfaces:

    def test_node_handle_make_sounding(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        ut.leaves.first.make_rest()
        assert ut.events.loc[0, 'is_rest']
        ut.leaves.first.make_sounding()
        assert not ut.events.loc[0, 'is_rest']

    def test_selector_make_sounding(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        ut.leaves.make_rest()
        assert ut.events['is_rest'].all()
        ut.leaves.make_sounding()
        assert not ut.events['is_rest'].any()


class TestCompositionalUnitMakeSounding:

    def test_it_brings_an_event_back(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        node = uc.rt.leaf_nodes[1]
        assert len(uc.leaves.sounding) == 4
        uc.make_rest(node)
        assert len(uc.leaves.sounding) == 3
        uc.make_sounding(node)
        assert len(uc.leaves.sounding) == 4
        assert uc.rt[node]['metric_duration'] > 0

    def test_the_docstring_states_what_it_cannot_restore(self):
        doc = CompositionalUnit.make_sounding.__doc__
        assert 'slur' in doc.lower()
        assert 'envelope' in doc.lower()

    def test_a_split_slur_does_not_come_back(self):
        """Behavioural proof of the asymmetry at the CU level: resting a
        leaf inside a slur splits the slur into segments, and un-resting it
        does not stitch them back -- nothing recorded the original span."""
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        def covered(unit):
            return {n for spec in unit._slur_specs.values()
                    for n in spec['leaf_nodes']}

        uc.leaves.apply_slur()
        assert len(covered(uc)) == 4
        leaf = uc.rt.leaf_nodes[1]
        uc.make_rest(leaf)
        after_rest = covered(uc)
        assert len(after_rest) < 4
        uc.make_sounding(leaf)
        assert covered(uc) == after_rest
        assert uc.rt[leaf]['metric_duration'] > 0
