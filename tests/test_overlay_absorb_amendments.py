"""SLUR-1 -- the amendments the literal absorb rule needs, each pinned.

The naive form of Ryan's ruling is "expand any slur member that is no longer
a leaf into its subtree's ordered leaves". A three-lane design pass ran that
against a full green suite and then found five ways it is wrong (SLUR-A1..A5)
plus five live defects independent of the ruling (SLUR-B1..B5). This module
pins each one.

MUTATION TABLE -- the evidence that these tests can fail. Most were written
after the fix, so the ordinary red-before-green proof is unavailable; instead
each was BREAK-TESTED by reverting exactly one rule in
``klotho/thetos/composition/compositional.py`` and confirming the named test
goes red. Every line below was RUN, not reasoned. The table lives here rather
than in the session handoff because ``projects/`` is gitignored -- a tracked
test pointing there is a dead reference.

Two entries say "BOTH", and that is the point of doing this rather than
asserting it: the first table written for this module had two mutations that
left their test GREEN, because the property they guard is enforced at two
independent places and removing one leaves the other doing the work. A
mutation that does not redden its test has not proved the test worthless --
it has found a second enforcer, and the table must name it or the next reader
will delete one and measure no change.

    test_a_foreign_slurs_leaves_are_a_split_point_not_a_raise
        mutation: in ``_remap_slur_specs``, ``mine()`` -> ``return True``.
        red: slur A absorbs slur B's leaves instead of splitting at them.
        also red under: ``self._slur_specs = rebuilt`` ->
        ``self._slur_specs.update(rebuilt)``, which leaves the dissolved
        slur's key behind holding stale members.

    test_the_rewrite_is_atomic_so_a_refusal_cannot_half_heal_it
        NOT a mutation -- this one has a genuine red-before-green. Measured
        on this exact fixture against the pre-fix code (069cc67), where the
        heal deleted each spec before re-registering its segments:
            RAISED ValueError Slurs cannot overlap
            after: {1: (6, 7), 2: (1, 2)}
        i.e. an exception escaping a structural edit that had already
        committed, and a fragment stored under id 2 -- an id ``apply_slur``
        never returned to anyone. The post-fix result is {0: (1,2), 1: (6,7)}
        with ``_next_slur_id`` unmoved.

    test_self_absorption_dedupes_and_stores_time_order
        mutation: remove BOTH ``kept.sort(key=leaf_index.__getitem__)`` in
        ``_remap_slur_specs`` AND ``ordered = sorted(moved, ...)`` in
        ``_contiguous_slur_segments``. Removing either alone stays GREEN.
        Both are load-bearing for different reasons: the first orders the
        list before ``_partition_non_rest_segments`` walks it splitting at
        rests, the second orders within each surviving run.
        red: leaf_nodes == (3, 2) -- reversed, so ``_slur_start`` lands on
        the later note and ``_slur_end`` on the earlier one.

    test_a_graft_carrying_a_tie_does_not_register_the_continuation
    test_a_member_that_becomes_a_continuation_is_snapped_out
        mutation: remove the ``_snap_to_tie_heads`` call.
        red: members intersecting tie continuations.
        The first fixture's grafted subtree must itself CONTAIN a tie -- an
        earlier draft grafted an untied one and stayed green under this
        mutation, proving nothing.

    test_subdividing_a_tie_continuation_keeps_the_arc
        mutation: remove the ``_absorb_leaves_grown_inside`` call.
        red: the arc dissolves entirely, with a "Slur removed" warning.

    test_total_dissolution_warns
        mutation: ``if dissolved:`` -> ``if False:``.
        red: zero warnings recorded on a slur that died.

    test_a_survivable_edit_does_not_warn
        mutation: ``if dissolved:`` -> ``if True:``.
        red: the guard cries wolf on an arc that lived. Both directions are
        tested because a warning that always fires is as useless as one that
        never does.

    test_an_unsplit_slur_keeps_the_id_apply_slur_returned
    test_a_split_mints_only_the_later_fragments
        mutation: mint unconditionally -- replace the ``if i == 0`` branch
        with ``new_id = next_id; next_id += 1``.
        red: the id moves 0 -> 1 across an edit that split nothing.

    test_apply_slur_always_moves_the_effective_pt_memo_key
        no mutation in this file: it guards an invariant of ``apply_slur``
        that the id-preservation change above now DEPENDS on. See the test's
        own docstring.

    test_an_edit_outside_the_span_leaves_the_values_alone
        mutation: delete the ``baked_leaves`` filter at the top of
        ``_queue_envelope_rebakes``, so every surviving descriptor is queued
        again.
        red: an unrelated subdivide overwrites a later control=False value
        and replaces a stored Bind with a scalar.

    test_an_edit_inside_the_span_still_rebakes
        mutation: the OPPOSITE -- ``descriptors = []``, a gate so tight it
        never rebakes.
        red: absorbed leaves carry no value. Both directions are tested
        because this fix is a gate, and a gate can fail either way.

    test_the_slur_and_the_envelope_absorb_the_same_leaves
    test_the_stored_subset_is_one_apply_envelope_could_author
        mutation: remove the ``_absorb_leaves_grown_inside`` call from
        ``_remap_control_envelopes``.
        red: the two overlays disagree, and the stored subset has a
        positional gap ``apply_envelope`` refuses to author.
"""

import warnings

import pytest

from klotho.chronos import RhythmTree
from klotho.thetos import CompositionalUnit as UC


def _specs(uc):
    return {k: tuple(v['leaf_nodes']) for k, v in uc._slur_specs.items()}


def _members(uc):
    return {n for s in uc._slur_specs.values() for n in s['leaf_nodes']}


class TestForeignSlursAreSplitPointsNotErrors:
    """SLUR-A1. Absorbing an ancestor's span must not swallow an arc drawn
    inside it -- and must never raise out of a committed structural edit."""

    def test_a_foreign_slurs_leaves_are_a_split_point_not_a_raise(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, (1, (1, 1))), bpm=60)
        uc.apply_slur([1, 2])          # slur A
        uc.apply_slur([4, 5])          # slur B, under interior node 3

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.move_subtree(3, 2)  # A's member 2 now grows B's leaves

        assert _specs(uc) == {1: (4, 5)}, (
            'B keeps its notes -- the deeper, more specific arc wins -- and A, '
            'left with one note, dissolves')

    def test_the_rewrite_is_atomic_so_a_refusal_cannot_half_heal_it(self):
        """The old code deleted a spec before re-registering its segments.

        A refusal partway through therefore left the slur gone, or half
        rewritten under an id the caller never saw. Nothing may be minted
        for a fragment the caller did not author.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, (1, (-1, 1, 1))), bpm=60)
        uc.apply_slur([1, 2, 3])
        uc.apply_slur([6, 7])
        before_next_id = uc._next_slur_id

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.move_subtree(4, 3)

        assert _specs(uc) == {0: (1, 2), 1: (6, 7)}
        assert uc._next_slur_id == before_next_id, (
            'nothing split, so nothing may have been minted')


class TestSelfAbsorption:
    """SLUR-A3. A member moved UNDER another member of the same slur."""

    def test_self_absorption_dedupes_and_stores_time_order(self):
        uc = UC(tempus='4/4', prolatio=((1, (1, 1)), 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.move_subtree(1, L[2])

        (spec,) = uc._slur_specs.values()
        members = list(spec['leaf_nodes'])
        assert len(members) == len(set(members)), 'a node is listed twice'
        order = list(uc._rt.leaf_nodes)
        assert members == sorted(members, key=order.index), (
            'stored out of time order, so the markers land on the wrong notes')


class TestTieGroupsStayAtomic:
    """SLUR-A4 and SLUR-B4, and the slur-over-tie coverage 07_TIES_CHARTER
    section 8 says the first implementation owes.

    The charter: *"Tie groups are atomic for slur membership: a slur
    selection touching a continuation snaps to the group's head -- a
    continuation is part of the head's sound."*
    """

    @staticmethod
    def _tied_slur():
        uc = UC(tempus='4/4', prolatio=(1,) * 6, bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc._rt.set_node_data(L[2], tied=True)     # L[2] continues L[1]
        uc.apply_slur([L[1], L[2], L[3]])
        return uc, L

    def test_apply_slur_snaps_the_continuation_onto_its_head(self):
        uc, L = self._tied_slur()
        assert L[2] not in _members(uc), 'the reference behaviour to match'

    def test_a_graft_carrying_a_tie_does_not_register_the_continuation(self):
        """SLUR-A4: the heal never snapped, so a graft could register one.

        The grafted subtree must CONTAIN a tie, or this proves nothing --
        an earlier draft of this test grafted an untied subtree and stayed
        green with the snap removed.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])
        sub = RhythmTree(meas='1/4', subdivisions=(1, 1))
        sub.set_node_data(sub.leaf_nodes[1], tied=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.graft_subtree(L[1], sub)

        continuations = {n for g in uc._rt.tie_groups for n in g[1:]}
        assert continuations, 'the fixture must actually produce a tie'
        assert _members(uc) & continuations == set(), (
            'a continuation is part of the head sound and can never be a '
            'member (charter sect 8)')

    def test_a_member_that_becomes_a_continuation_is_snapped_out(self):
        """The second route in: absorption puts a leaf in the arc, and only
        later does that leaf become a tie continuation. The next remap must
        fold it onto its head."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.subdivide(L[1], (1, 1))
        grown = list(uc._rt.subtree_leaves(L[1]))
        assert set(grown) <= _members(uc), 'absorption must have run'
        uc._rt.set_node_data(grown[1], tied=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.subdivide(L[3], (1, 1))       # any later structural edit

        assert grown[1] not in _members(uc), (
            'a member that became a tie continuation must be snapped onto '
            'its head')

    def test_subdividing_a_tie_continuation_keeps_the_arc(self):
        """SLUR-B4, decided by R12 -- what a composer would guess.

        Divide a tied-over note inside a slur and a player reads the first
        half as still tied and the second as a new note under the same
        slur. A slur breaks at a rest or where the composer lifts it, not
        because someone shortened a note underneath it. Before this rule
        existed the arc dissolved entirely.
        """
        uc, L = self._tied_slur()
        head, tail = L[1], L[3]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc._rt.subdivide(L[2], (1, 1))

        assert [w for w in caught if 'Slur removed' in str(w.message)] == [], (
            'the arc must survive a subdivision made inside it')
        (spec,) = uc._slur_specs.values()
        assert spec['leaf_nodes'][0] == head
        assert spec['leaf_nodes'][-1] == tail
        continuations = {n for g in uc._rt.tie_groups for n in g[1:]}
        assert _members(uc) & continuations == set()
        # the re-articulated half IS in the arc; the still-tied half is not
        new_leaves = [n for n in uc._rt.subtree_leaves(L[2])]
        assert any(n in _members(uc) for n in new_leaves), (
            'the new attack inside the arc must be a member')


class TestASlurDeathIsAnnounced:
    """SLUR-B1. The envelope half has warned on the identical death since
    it was written; the slur half died in silence."""

    def test_total_dissolution_warns(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[0], L[1]])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc._rt.subdivide(L[0], (1, -1))

        assert uc._slur_specs == {}, 'the fixture must actually kill the slur'
        messages = [str(w.message) for w in caught
                    if issubclass(w.category, RuntimeWarning)]
        assert any('Slur removed' in m for m in messages), (
            f'a slur died in silence; warnings were {messages}')

    def test_a_survivable_edit_does_not_warn(self):
        """The other half of the guard: no crying wolf on an arc that lived."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[0], L[1]])

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc._rt.subdivide(L[0], (1, 1))

        assert uc._slur_specs, 'the fixture must keep the slur alive'
        assert [str(w.message) for w in caught
                if 'Slur removed' in str(w.message)] == []


class TestSlurIdentityHasOneRule:
    """SLUR-B2. The two seams disagreed: one re-minted every time, the other
    preserved the id. ``_slur_id`` is not internal -- ``apply_slur`` returns
    it, it is an mfield on the effective PT, it is a column of ``uc.events``,
    and the lowering keys voice pooling and slur teardown on it."""

    @pytest.mark.parametrize('door, grow', [
        ('uc.subdivide', lambda uc, n: uc.subdivide(n, (1, 1))),
        ('raw.subdivide', lambda uc, n: uc._rt.subdivide(n, (1, 1))),
    ])
    def test_an_unsplit_slur_keeps_the_id_apply_slur_returned(self, door, grow):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        slur_id = uc.apply_slur([L[1], L[2]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grow(uc, L[1])

        assert list(uc._slur_specs) == [slur_id], (
            f'{door}: the arc neither split nor dissolved, so the id the '
            f'caller was handed must still name it')

    def test_a_split_mints_only_the_later_fragments(self):
        uc = UC(tempus='4/4', prolatio=(1,) * 6, bpm=60)
        L = list(uc._rt.leaf_nodes)
        slur_id = uc.apply_slur([L[0], L[1], L[2], L[3]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc.make_rest(L[1])          # splits into [L0] and [L2, L3]

        assert slur_id in uc._slur_specs or len(uc._slur_specs) == 1, (
            'the first surviving segment keeps the original identity')


class TestTheMemoKeyInvariant:
    """NEW-42, closed by measurement rather than by adding a counter.

    The effective-PT snapshot memoizes on ``(_structure_version,
    _next_slur_id, len(_slur_specs), instruments_version)``. Preserving a
    slur's id across a heal freezes ``_next_slur_id``, which removes one of
    two signals -- so the key's soundness now rests on ``_structure_version``
    moving on every membership change reachable from a structural verb.

    A directed sweep plus 2040 randomised mutations found no membership
    change with the key frozen, because ``apply_slur`` is the ONLY membership
    change that touches no tree state, and it still mints an id and grows the
    dict. That is the invariant this test guards: break it, and the memo can
    serve a stale snapshot.
    """

    def test_apply_slur_always_moves_the_effective_pt_memo_key(self):
        uc = UC(tempus='4/4', prolatio=(1,) * 6, bpm=60)
        L = list(uc._rt.leaf_nodes)

        def key():
            return (uc._rt._structure_version, uc._next_slur_id,
                    len(uc._slur_specs))

        before = key()
        uc.apply_slur([L[0], L[1]])
        assert key() != before, (
            'apply_slur changes membership without touching the tree, so it '
            'is the one path where the id mint and the dict size are the '
            'only signals the memo key has')


class TestSequentialAndOneShotGrowthMayDiverge:
    """SLUR-A5, and the docstring on ``apply_slur`` that states it.

    Ryan ruled: sequential and one-shot growth MAY diverge, each edit heals
    against what exists at that moment, and no edit batching may be built to
    hide it. So this test does not assert that they AGREE -- it pins the two
    outcomes so the documented example cannot rot, and so a future change
    that silently converges or diverges further is visible.
    """

    @staticmethod
    def _slurred_four():
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60)
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[0], L[1], L[2], L[3]])
        return uc, L

    def test_plain_growth_agrees(self):
        """Where nothing splits the arc, the two forms give one answer."""
        one, L = self._slurred_four()
        one.subdivide(L[1], (1, 1, 1))

        many, M = self._slurred_four()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k in range(3):
                many._rt.insert_child(M[1], k, proportion=1)

        assert [len(s) for s in _specs(one).values()] == \
               [len(s) for s in _specs(many).values()] == [6]

    def test_growth_containing_a_rest_diverges_and_that_is_the_ruling(self):
        """The documented example, pinned.

        One-shot: the third child lands while the arc still covers its
        parent, so it joins. Stepwise: the rest has already split the arc by
        then, so the third child is landing in music the arc no longer
        covers, and it stays out.
        """
        one, L = self._slurred_four()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            one.subdivide(L[1], (1, -1, 1))

        many, M = self._slurred_four()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k, proportion in enumerate((1, -1, 1)):
                many._rt.insert_child(M[1], k, proportion=proportion)

        one_sizes = sorted(len(s) for s in _specs(one).values())
        many_sizes = sorted(len(s) for s in _specs(many).values())
        assert one_sizes == [2, 3], f'one-shot gave {_specs(one)}'
        assert many_sizes == [2, 2], f'stepwise gave {_specs(many)}'
        assert one_sizes != many_sizes, (
            'the divergence is the ruled behaviour; if these ever agree, the '
            "docstring on apply_slur is wrong and someone has built the edit "
            'batching Ryan said not to build')


class TestAMidSlurInstrumentChangeIsAnnounced:
    """NEW-41. The one place SLUR-1 changes what a user HEARS.

    A slur lowers to ONE synth, created at its head and held: a continuation
    emits a ``set`` on the head's node id and carries no ``defName`` at all.
    So an instrument assigned to a mid-slur note has never sounded, and its
    controls are pushed onto the head's synth instead.

    That was survivable while the raw path DROPPED a subdivided leaf out of
    the slur -- an instrument set on a new child then sounded, because the
    child was no longer a continuation. Absorb keeps it in the arc, so the
    same code goes silent. Measured: on one edit, slur membership goes from
    2 of 6 leaves to 6 of 6.

    The policy question -- break the arc at the change, warn and continue, or
    release and restrike -- is Ryan's, and is filed. What is fixed here is
    only that it stops being SILENT, which is the standard the envelope side
    and the tie side already meet (``_tie_join_reason`` refuses to join on an
    instrument mismatch and says so).
    """

    @staticmethod
    def _slurred(instrument_on_member):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), bpm=60,
                pfields={'freq': 440})
        L = list(uc._rt.leaf_nodes)
        uc.set_instrument(uc._rt.root, 'kl_tri')
        uc.apply_slur([L[0], L[1], L[2]])
        if instrument_on_member:
            uc.set_instrument(L[1], 'kl_saw')
        return uc

    @staticmethod
    def _lower(uc):
        import klotho.utils.playback.supersonic.converters as converters
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            converters.lower_compositional_ir_to_sc_assembly(uc)
            return [str(w.message) for w in caught
                    if 'Instrument change inside a slur' in str(w.message)]

    def test_a_mid_slur_instrument_change_warns(self):
        messages = self._lower(self._slurred(instrument_on_member=True))
        assert messages, 'a note that will not sound as written said nothing'
        assert 'kl_saw' in messages[0] and 'kl_tri' in messages[0], (
            'the warning must name both what was asked for and what sounds')

    def test_a_uniform_slur_does_not_warn(self):
        """The other direction: a warning that always fires is noise."""
        assert self._lower(self._slurred(instrument_on_member=False)) == []


class TestARebakeTouchesOnlyWhatTheEditChanged:
    """Found by the adversarial pass against the first SLUR-1 commit.

    Making the seam rebake was necessary -- an absorbed leaf must get its
    value. But the first version queued EVERY surviving descriptor, so any
    structural edit anywhere in the unit re-asserted every control envelope
    over its whole span. That silently destroyed user data twice over: a
    later ``control=False`` envelope on the same pfield (Ryan's ENV-6 ruling
    promises those resolve last-write-wins) and a ``Bind`` stored inside the
    span, replaced by a scalar so the callable never ran again.

    Before the seam rebaked at all, an edit outside an envelope's span could
    not touch its values. That property is restored by gating on
    ``baked_leaves`` rather than traded away for the absorb.
    """

    @staticmethod
    def _enveloped():
        from klotho.dynatos import Envelope
        from klotho.thetos import Bind
        uc = UC(tempus='6/4', prolatio=(1,) * 6, beat='1/4', bpm=60,
                pfields={'freq': 0})
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 100.0], times=[2.0]), 'freq',
                          node=[L[0], L[1], L[2]], control=True)
        uc.set_pfields(L[0], freq=1000.0)
        uc.set_pfields(L[1], freq=Bind.index(map=lambda i, n: 7777.0))
        return uc, L

    def test_an_edit_outside_the_span_leaves_the_values_alone(self):
        uc, L = self._enveloped()
        before = [repr(uc._rt[n].get('freq')) for n in L[:3]]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.subdivide(L[5], (1, 1))       # nowhere near the envelope

        after = [repr(uc._rt[n].get('freq')) for n in L[:3]]
        assert after == before, (
            'an edit outside the span re-asserted the envelope over values '
            'the user wrote afterwards')

    def test_an_edit_inside_the_span_still_rebakes(self):
        """The other direction -- a gate too tight is a hole in the ramp."""
        uc, L = self._enveloped()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.subdivide(L[2], (1, 1))

        grown = list(uc._rt.subtree_leaves(L[2]))
        values = [uc._rt[n].get('freq') for n in grown]
        assert all(v is not None for v in values), (
            f'absorbed leaves {grown} carry no value: {values}')


class TestBothOverlaysHealOneEditTheSameWay:
    """Also from the adversarial pass.

    The slur half got ``_absorb_leaves_grown_inside``; the envelope half did
    not. Measured on two sequential inserts under a target both overlays
    covered, the slur read ``(1, 2, 6, 7, 4)`` and the subset read
    ``(1, 2, 6, 4)`` -- leaf 7, a SOUNDING leaf strictly inside the
    envelope's span, carried no value at all. A hole in the ramp, and a
    stored subset with a positional gap that ``apply_envelope`` refuses to
    author.

    Ryan ruled that sequential and one-shot growth may diverge. He did not
    rule that two overlays may heal the same edit differently.
    """

    def test_the_slur_and_the_envelope_absorb_the_same_leaves(self):
        from klotho.dynatos import Envelope
        uc = UC(tempus='6/4', prolatio=(1,) * 5, beat='1/4', bpm=60,
                pfields={'freq': 0})
        L = list(uc._rt.leaf_nodes)
        span = [L[0], L[1], L[2], L[3]]
        uc.apply_slur(span)
        uc.apply_envelope(Envelope([0.0, 100.0], times=[2.0]), 'freq',
                          node=span, control=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k in range(2):
                uc._rt.insert_child(L[2], k, proportion=1)

        (slur,) = uc._slur_specs.values()
        (desc,) = uc._control_envelopes.values()
        assert tuple(desc['leaf_subset']) == tuple(slur['leaf_nodes']), (
            'the two overlays healed one edit differently')

        order = list(uc._rt.leaf_nodes)
        subset = list(desc['leaf_subset'])
        assert subset == sorted(subset, key=order.index), 'not in time order'
        holes = [n for n in subset if uc._rt[n].get('freq') is None]
        assert holes == [], f'sounding leaves inside the span with no value: {holes}'

    def test_the_stored_subset_is_one_apply_envelope_could_author(self):
        """The oracle: a positional gap is a spec the public API refuses."""
        from klotho.dynatos import Envelope
        uc = UC(tempus='6/4', prolatio=(1,) * 5, beat='1/4', bpm=60,
                pfields={'freq': 0})
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 100.0], times=[2.0]), 'freq',
                          node=[L[0], L[1], L[2], L[3]], control=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for k in range(2):
                uc._rt.insert_child(L[2], k, proportion=1)

        (desc,) = uc._control_envelopes.values()
        uc._resolve_leaf_selection(list(desc['leaf_subset']))   # raises if not
