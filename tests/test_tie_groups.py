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


# ---------------------------------------------------------------------------
# Lowering (charter sect3-6): one merged event, upstream of voice expansion;
# the precondition and divergence test run at lowering, where the facts
# live; every failure is an attack plus ONE warning naming why.
# ---------------------------------------------------------------------------

import warnings as _warnings

from klotho.utils.playback._sc_assembly import (
    lower_compositional_ir_to_sc_assembly,
    node_event_map,
)


def _tied_uc(inst='kl_tri', prolatio=(1, 1.0, 1, 1)):
    uc = CompositionalUnit(tempus='4/4', prolatio=prolatio, bpm=120)
    uc.set_instrument(uc.root, inst)
    return uc


def _new_events(events):
    return [e for e in events if e.get('type') == 'new'
            and e.get('defName') != '__rest__']


class TestTieLowering:
    def test_group_lowers_to_one_merged_event(self):
        uc = _tied_uc()
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        assert len(news) == 3
        assert news[0]['dur'] == pytest.approx(1.0)
        assert news[0]['releaseAfter'] is True

    def test_continuations_register_in_the_node_map_at_head_start(self):
        # charter sect11: many-nodes-to-one-event, at the head's start —
        # or control envelopes anchored on continuation nodes drop silently
        uc = _tied_uc()
        mapping = node_event_map(uc)
        leaves = uc._rt.leaf_nodes
        head_ids = {e[0] for e in mapping[leaves[0]]}
        cont_ids = {e[0] for e in mapping[leaves[1]]}
        assert head_ids and head_ids == cont_ids
        assert mapping[leaves[1]][0][1] == mapping[leaves[0]][0][1]

    def test_effective_value_divergence_fails_the_tie_with_one_warning(self):
        # charter sect4: the conflict rule is effective-value divergence,
        # not authorship — would the continuation sound different?
        uc = _tied_uc()
        uc.set_pfields(uc._rt.leaf_nodes[1], freq=999.0)
        with pytest.warns(UserWarning, match="divergence on 'freq'"):
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 4  # downgraded to attacks

    def test_instrument_mismatch_fails_the_tie(self):
        uc = _tied_uc()
        uc.set_instrument(uc._rt.leaf_nodes[1], 'kl_saw')
        with pytest.warns(UserWarning, match='instrument mismatch'):
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 4

    def test_group_mismatch_fails_the_tie(self):
        # group is track routing: a cross-group tie would silently move a
        # note between tracks mid-sound (charter sect5)
        uc = _tied_uc()
        uc.set_mfields(uc._rt.leaf_nodes[1], group='solo')
        with pytest.warns(UserWarning, match='group mismatch'):
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 4

    def test_dangling_leading_tie_warns_and_attacks(self):
        uc = _tied_uc(prolatio=(1.0, 1, 1))
        with pytest.warns(UserWarning, match='no predecessor'):
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 3

    def test_identical_tuple_pfields_tie_a_sustained_chord(self):
        # charter sect13: v1 is event-level; identical tuples work today
        uc = _tied_uc()
        for leaf in (uc._rt.leaf_nodes[0], uc._rt.leaf_nodes[1]):
            uc.set_pfields(leaf, freq=(330.0, 415.0))
        with _warnings.catch_warnings():
            _warnings.simplefilter('error')
            events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        # 2 voices for the merged chord event + 1 each for the two plain
        assert len(news) == 4
        merged = [e for e in news if e['dur'] == pytest.approx(1.0)]
        assert len(merged) == 2

    def test_control_envelope_across_the_tie_is_exempt(self):
        # charter sect4: control envelopes ride through via the node map;
        # their baked per-leaf values are NOT divergence
        from klotho.dynatos.envelopes import Envelope
        uc = _tied_uc()
        uc.apply_envelope(Envelope([0.1, 0.9], times=[2.0]), 'amp',
                          uc._rt.root, control=True)
        with _warnings.catch_warnings():
            _warnings.simplefilter('error')
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 3

    def test_pure_bake_divergence_fails_loudly(self):
        # DOCUMENTED DEVIATION from charter sect4's bake clause: a pure
        # bake leaves no descriptor (one-shot write), so its per-leaf
        # values are indistinguishable from authorship. The general
        # divergence rule applies instead — attack + warning naming the
        # key. Never silent. (Charter amendment 2026-08-29; flagged for
        # Ryan.)
        from klotho.dynatos.envelopes import Envelope
        uc = _tied_uc()
        uc.apply_envelope(Envelope([0.1, 0.9], times=[2.0]), 'amp',
                          uc._rt.root, control=False)
        with pytest.warns(UserWarning, match="divergence on 'amp'"):
            events = lower_compositional_ir_to_sc_assembly(uc)
        assert len(_new_events(events)) == 4

    def test_animation_reserves_continuation_steps(self):
        # charter sect3: continuations reserve their step index the way
        # rests do, or every plot downstream of a tie shifts by one
        uc = _tied_uc()
        events = lower_compositional_ir_to_sc_assembly(uc, animation=True)
        steps = {e.get('_stepIndex') for e in events if '_stepIndex' in e}
        assert steps == {0, 1, 2, 3}

    def test_ungated_sustain_control_gets_the_summed_span(self):
        # charter sect3: the sustain poke widens past its slur guard so a
        # tie head's sustain control covers the whole group
        uc = _tied_uc(inst='fd_creep')
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        merged = [e for e in news if e['dur'] == pytest.approx(1.0)]
        assert merged and merged[0]['pfields']['releaseTime'] == pytest.approx(1.0)

    def test_bare_ut_ties_join_on_structure_alone(self):
        # charter sect5: chronos has no instruments
        from klotho.utils.playback.supersonic.converters import (
            temporal_unit_to_sc_events,
        )
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        with _warnings.catch_warnings():
            _warnings.simplefilter('error')
            events = temporal_unit_to_sc_events(ut)
        news = [e for e in events if e.get('type') == 'new']
        assert len(news) == 3


class TestTieAwareDecompose:
    """ALG-2 at the temporal surface (charter sect9)."""

    def test_ut_decomposes_one_unit_per_group(self):
        from klotho.chronos.temporal_units.algorithms import decompose
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        seq = decompose(ut)
        assert len(seq.seq) == 3
        assert str(seq.seq[0].tempus) == '2/4'  # unreduced group sum
        assert seq.seq[0].duration == pytest.approx(1.0)

    def test_decomposed_sequence_sounds_identical(self):
        from klotho.chronos.temporal_units.algorithms import decompose
        ut = TemporalUnit(tempus='4/4', prolatio=(1, 1.0, -1, 1), bpm=120)
        seq = decompose(ut)
        assert sum(u.duration for u in seq.seq) == pytest.approx(ut.duration)
        assert len(seq.seq) == len(ut)

    def test_dangling_leading_tie_keeps_its_marker(self):
        from klotho.chronos.temporal_units.algorithms import decompose
        ut = TemporalUnit(tempus='3/4', prolatio=(1.0, 1, 1), bpm=120)
        seq = decompose(ut)
        first_rt = seq.seq[0]._rt
        assert first_rt[first_rt.leaf_nodes[0]]['tied'] is True

    def test_cu_group_takes_the_heads_parameters(self):
        from klotho.chronos.temporal_units.algorithms import decompose
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        uc.set_pfields(uc._rt.leaf_nodes[0], freq=333.0)
        seq = decompose(uc)
        assert len(seq.seq) == 3
        grp = seq.seq[0]
        assert str(grp.tempus) == '2/4'
        assert grp.duration == pytest.approx(1.0)
        assert grp[0].pfields.get('freq') == 333.0

    def test_cu_explicit_prolatio_groups_too(self):
        from klotho.chronos.temporal_units.algorithms import decompose
        uc = CompositionalUnit(tempus='4/4', prolatio=(1, 1.0, 1, 1), bpm=120)
        seq = decompose(uc, prolatio=(1, 1))
        assert len(seq.seq) == 3
        assert str(seq.seq[0].tempus) == '2/4'
        assert sum(u.duration for u in seq.seq) == pytest.approx(uc.duration)


class TestSlurOverTie:
    """First coverage of slur x tie (charter sect8 names the gap)."""

    def test_slur_selection_snaps_to_group_heads(self):
        uc = _tied_uc()
        slur_id = uc.apply_slur(uc._rt.leaf_nodes)
        spec = uc._slur_specs[slur_id]
        leaves = uc._rt.leaf_nodes
        assert list(spec['leaf_nodes']) == [leaves[0], leaves[2], leaves[3]]

    def test_tied_group_is_one_slur_member(self):
        uc = _tied_uc()
        uc.apply_slur(uc._rt.leaf_nodes)
        events = lower_compositional_ir_to_sc_assembly(uc)
        news = _new_events(events)
        sets = [e for e in events if e.get('type') == 'set']
        assert len(news) == 1  # one synth for the whole slur
        assert len(sets) == 2  # two continuations of the slur
        assert news[0]['dur'] == pytest.approx(1.0)  # merged head span
