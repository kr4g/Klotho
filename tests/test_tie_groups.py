"""RT ties, chronos side — the event/leaf split (07_TIES_CHARTER.md).

A tie is ONE sound (charter §0): a tied group — head + leaf-order
continuations — is a single sounding event on the EVENT surfaces
(``len(ut)``, iteration, indexing, ``onsets``, ``durations``), while the
leaf surface (``leaves``, selectors, per-leaf node data) stays per-leaf
everywhere. Groups are derived lazily from the RT flags; nothing stores
or materializes them (charter §2).

The first class is the charter §15 pin, written before any implementation:
everything else in the tie design is this fusion pushed through one
surface.

Grammar edges pinned here (charter §1): tied rests are illegal on every
surface; sign-flips clear ``tied``; a float D on an interior node is
REFUSED (resolved against OpenMusic 2026-08-29 — OM6 and om-sharp both
give a float group value no tie meaning and silently round it; Klotho
refuses instead of corrupting silently); a first-leaf tie is legal and
dangles (renders as its own attack).
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree, TemporalUnit
from klotho.thetos.composition.compositional import CompositionalUnit


class TestTheThreeLinePin:
    """Charter §15 item 1 — the pin that defines the whole feature."""

    def test_len_counts_sounding_events(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        assert len(ut) == 3

    def test_leaves_stay_per_leaf(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        assert len(ut.leaves) == 4

    def test_durations_count_groups(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        assert ut.durations == (1.0, 0.5, 0.5)


class TestEventSurfaces:
    def _ut(self):
        return TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)

    def test_iteration_yields_one_event_per_group(self):
        events = list(self._ut())
        assert len(events) == 3
        assert [e.duration for e in events] == [1.0, 0.5, 0.5]

    def test_indexing_is_event_indexed(self):
        ut = self._ut()
        assert ut[0].duration == 1.0
        assert ut[1].start == 1.0

    def test_onsets_are_event_onsets(self):
        assert self._ut().onsets == (0.0, 1.0, 1.5)

    def test_group_event_metric_duration_is_the_sum(self):
        ut = self._ut()
        assert ut[0].metric_duration == Fraction(1, 2)
        assert ut[1].metric_duration == Fraction(1, 4)

    def test_group_event_is_anchored_at_its_head(self):
        ut = self._ut()
        head = ut._rt.leaf_nodes[0]
        assert ut[0].node_id == head
        assert ut[0].tie_group == (ut._rt.leaf_nodes[0], ut._rt.leaf_nodes[1])
        assert ut[1].tie_group == (ut._rt.leaf_nodes[2],)

    def test_tie_free_unit_is_unchanged(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=120)
        assert len(ut) == len(ut.leaves) == 4
        assert ut.durations == (0.5, 0.5, 0.5, 0.5)

    def test_rest_durations_stay_signed(self):
        # WL-19's pinned choice: the durations tuple stays signed.
        ut = TemporalUnit(tempus='4/4', prolatio=(1, -1, 1.0, 1), bpm=120)
        assert ut.durations[1] < 0

    def test_events_dataframe_counts_events(self):
        assert len(self._ut().events) == 3


class TestGroupDerivation:
    def test_cross_branch_group(self):
        # Charter §1: groups are leaf-order runs, NOT subtree containment —
        # the tie here reaches back across a branch boundary.
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(1, (2, (1.0, 1)), 1))
        leaves = rt.leaf_nodes
        assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],), (leaves[3],))

    def test_rests_are_singleton_groups_and_break_runs(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1.0, 1.0))
        leaves = rt.leaf_nodes
        # the tied leaf after the rest dangles (heads its own group); the
        # following tied leaf joins IT, not the rest
        assert rt.tie_groups == ((leaves[0],), (leaves[1],),
                                 (leaves[2], leaves[3]))

    def test_first_leaf_tie_dangles(self):
        # Charter T-C: legal to construct, a leading tie awaiting a
        # predecessor; standalone it is its own (attacking) event.
        ut = TemporalUnit(tempus='3/4', prolatio=(1.0, 1, 1), bpm=120)
        assert len(ut) == 3

    def test_groups_are_derived_not_stored(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        assert len(rt.tie_groups) == 3
        # a mutation that clears the flag changes the derived read — no
        # stored spec to heal
        rt.set_node_data(rt.leaf_nodes[1], tied=False)
        assert len(rt.tie_groups) == 4


class TestAttacksSelector:
    def test_attacks_are_group_heads(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, -1, 1), bpm=120)
        leaves = ut._rt.leaf_nodes
        assert ut.attacks.ids == (leaves[0], leaves[3])

    def test_sounding_still_includes_continuations(self):
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, -1, 1), bpm=120)
        assert len(ut.leaves.sounding) == 3


class TestTiedRestsAreIllegal:
    def test_negative_float_refused_at_construction(self):
        with pytest.raises(ValueError, match='[Tt]ied rest|rest cannot'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, -1.0, 1))

    def test_tying_a_rest_refused_on_the_write_path(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1))
        with pytest.raises(ValueError, match='rest'):
            rt.set_node_data(rt.leaf_nodes[1], tied=True)

    def test_negative_float_refused_on_the_write_path(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='rest'):
            rt.set_node_data(rt.leaf_nodes[1], proportion=-2.0)

    def test_make_rest_clears_the_tie(self):
        # Charter §1: sign-flip operations clear ``tied`` — otherwise they
        # manufacture the illegal state mechanically.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        tied_leaf = rt.leaf_nodes[1]
        rt.make_rest(tied_leaf)
        assert rt[tied_leaf]['tied'] is False
        assert isinstance(rt[tied_leaf]['proportion'], int)
        assert rt[tied_leaf]['proportion'] < 0

    def test_resting_a_branch_clears_descendant_ties(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(1, (2, (1, 1.0)), 1))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        rt.make_rest(branch)
        assert all(rt[l]['tied'] is False for l in rt.leaf_nodes)


class TestTiesAreLeafOnly:
    def test_interior_float_D_refused_at_construction(self):
        # Resolved against OpenMusic (charter §1, 2026-08-29): OM gives a
        # float group value NO tie meaning — it silently rounds. Refuse.
        with pytest.raises(ValueError, match='leaf'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, (2.0, (1, 1)), 1))

    def test_tying_an_interior_node_refused_on_the_write_path(self):
        rt = RhythmTree(span=1, meas='3/4', subdivisions=(1, (2, (1, 1))))
        branch = next(n for n in rt.nodes
                      if rt.out_degree(n) > 0 and n != rt.root)
        with pytest.raises(ValueError, match='leaf'):
            rt.set_node_data(branch, tied=True)

    def test_subdividing_a_tied_leaf_moves_the_tie_to_its_first_child(self):
        # The one operation that would otherwise create an interior float:
        # the leaf's "continues my predecessor" meaning has exactly one
        # lossless landing spot — the first sub-leaf.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        tied_leaf = rt.leaf_nodes[1]
        rt.subdivide(tied_leaf, (1, 1))
        assert rt[tied_leaf]['tied'] is False
        assert isinstance(rt[tied_leaf]['proportion'], int)
        first_child = list(rt.successors(tied_leaf))[0]
        assert rt[first_child]['tied'] is True
        leaves = rt.leaf_nodes
        # groups: (l0 + first sub-leaf), second sub-leaf, l2, l3
        assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],),
                                 (leaves[3],), (leaves[4],))


class TestCompositionalUnitSurfaces:
    def test_uc_len_counts_events(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        assert len(uc) == 3
        assert len(uc.leaves) == 4

    def test_uc_group_event_duration_is_the_sum(self):
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        assert uc[0].duration == 1.0
