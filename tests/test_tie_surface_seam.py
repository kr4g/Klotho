"""The FOURTH id-state event: a leaf that stops (or starts) being a TIE
CONTINUATION, while an overlay is live over it.

``CLAUDE.md`` names three events the id-keyed machinery models -- DEATH (the
node is gone), RELOCATION (ids move, the mapping total over survivors), and a
leaf that stops being a leaf. ``make_rest`` and ``make_sounding`` produce a
fourth that none of them covers: the leaf surface is unchanged and no id
moves, but the TIE surface underneath a live arc does.

Both defects are the same shape as everything SLUR-1 fixed -- the verb
announces nothing, so the heal never runs -- and, measured, both are already
answerable by helpers this file's subjects already own:

* TIE-3: ``_contiguous_slur_segments`` on the post-rest membership returns
  ``[]`` (correctly: two one-note runs, neither a slur).
* TIE-4: ``_snap_to_tie_heads`` on the post-sounding membership returns the
  arc re-headed onto the new tie head, and ``_contiguous_slur_segments``
  accepts it (a continuation of the member just before is a legal gap).

So neither fix invents a rule. What is missing is the announcement.

The raw-handle cases are not decoration. R12 lens 2 (the programmer's lens,
Ryan 2026-08-31) forbids a verb answering one musical question differently
depending on which handle was held; that divergence WAS the whole SLUR-1
finding, and ``RhythmTree.make_rest``/``make_sounding`` are two more doors
into the same room.

"""

import warnings

import pytest

from klotho.thetos import CompositionalUnit as UC


def _tied_arc():
    """4 beats, leaf 3 tied to leaf 2, slur authored over leaves 2..4.

    ``apply_slur`` snaps the continuation onto its head, so the stored arc is
    ``(2, 4)`` -- leaf 3 is in the arc's SPAN but never in its member set.
    That gap is exactly what the rest guard fails to look at.
    """
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'freq': 440})
    leaves = list(uc._rt.leaf_nodes)
    uc._rt.set_node_data(leaves[2], tied=True)
    slur_id = uc.apply_slur([leaves[1], leaves[2], leaves[3]])
    return uc, leaves, slur_id


def _arc_whose_head_can_be_swallowed():
    """Leaf 1 rests; leaf 2 carries ``tied`` but continues nothing while it
    does. Slur over leaves 2..3, so ``_slur_start`` sits on leaf 2.

    Un-resting leaf 1 makes leaf 2 its continuation -- the arc's first member
    stops producing an event at all.
    """
    uc = UC(tempus='4/4', prolatio=(-1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'freq': 440})
    leaves = list(uc._rt.leaf_nodes)
    uc._rt.set_node_data(leaves[1], tied=True)
    slur_id = uc.apply_slur([leaves[1], leaves[2]])
    return uc, leaves, slur_id


def _span_leaves(uc, spec):
    """The leaves lying between the arc's first and last member, inclusive."""
    order = list(uc._rt.leaf_nodes)
    index = {leaf: i for i, leaf in enumerate(order)}
    positions = [index[n] for n in spec['leaf_nodes']]
    return order[min(positions):max(positions) + 1]


def _slur_flags(uc):
    """``(heads, tails)`` counted off the lowering surface."""
    events = uc.events
    heads = sum(1 for _, row in events.iterrows()
                if row.get('_slur_start') == 1.0)
    tails = sum(1 for _, row in events.iterrows()
                if row.get('_slur_end') == 1.0)
    return heads, tails


# --------------------------------------------------------------------------
# TIE-3
# --------------------------------------------------------------------------

class TestRestingATieContinuationUnderAnArc:
    """TIE-3. Resting a continuation silences music the arc spans, and also
    destroys the tie that made the gap legal. The arc must not survive
    drawn across the resulting rest.

    A player reading the passage afterwards sees: note, rest, note. There is
    no arc there -- both runs are one note long, and one note is not a slur.
    So the correct answer is the same one ``make_rest`` already gives when it
    silences a MEMBER: the arc dissolves, and it says so.
    """

    @pytest.mark.parametrize('handle', ['uc', 'raw'])
    def test_no_arc_is_left_spanning_the_new_rest(self, handle):
        uc, leaves, slur_id = _tied_arc()
        continuation = leaves[2]

        if handle == 'uc':
            uc.make_rest(continuation)
        else:
            uc._rt.make_rest(continuation)

        for spec in uc._slur_specs.values():
            span = _span_leaves(uc, spec)
            rests = [n for n in span
                     if uc._rt[n].get('proportion', 1) < 0]
            assert not rests, (
                f'{handle}: arc {spec["leaf_nodes"]} spans rests {rests}'
            )

    @pytest.mark.parametrize('handle', ['uc', 'raw'])
    def test_the_dissolution_is_announced(self, handle):
        """SLUR-B1's rule, one door further: a slur death is never silent."""
        uc, leaves, slur_id = _tied_arc()
        continuation = leaves[2]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            if handle == 'uc':
                uc.make_rest(continuation)
            else:
                uc._rt.make_rest(continuation)

        assert any('Slur removed' in str(w.message) for w in caught), (
            f'{handle}: silent, caught {[str(w.message) for w in caught]}'
        )

    def test_the_two_handles_agree(self):
        """R12 lens 2: one musical question, one answer, whichever handle."""
        uc_a, leaves_a, _ = _tied_arc()
        uc_b, leaves_b, _ = _tied_arc()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc_a.make_rest(leaves_a[2])
            uc_b._rt.make_rest(leaves_b[2])

        via_uc = {k: tuple(v['leaf_nodes'])
                  for k, v in uc_a._slur_specs.items()}
        via_raw = {k: tuple(v['leaf_nodes'])
                   for k, v in uc_b._slur_specs.items()}
        assert via_uc == via_raw

    def test_resting_a_leaf_outside_the_arc_leaves_it_alone(self):
        """The guard must widen to the SPAN, not to the whole tree."""
        uc, leaves, slur_id = _tied_arc()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            uc.make_rest(leaves[0])

        assert slur_id in uc._slur_specs
        assert tuple(uc._slur_specs[slur_id]['leaf_nodes']) == (leaves[1],
                                                                leaves[3])
        assert not any('Slur removed' in str(w.message) for w in caught)


# --------------------------------------------------------------------------
# TIE-4
# --------------------------------------------------------------------------

class TestUnRestingUnderneathAnArcsFirstMember:
    """TIE-4. Un-resting a leaf can make the following leaf its continuation.
    When that following leaf is the arc's first member it stops producing an
    event, ``_slur_start`` vanishes with it, and every event of the arc takes
    the not-a-start branch -- an arc reaching playback that no note opens.

    Charter §8 already says what a slur does about a tie group: it is atomic,
    and a selection touching a continuation snaps to the head. Applying that
    same rule AFTER the fact re-heads the arc onto the leaf that now carries
    the attack.
    """

    @pytest.mark.parametrize('handle', ['uc', 'raw'])
    def test_the_arc_still_has_a_note_that_opens_it(self, handle):
        uc, leaves, slur_id = _arc_whose_head_can_be_swallowed()

        if handle == 'uc':
            uc.make_sounding(leaves[0])
        else:
            uc._rt.make_sounding(leaves[0])

        heads, tails = _slur_flags(uc)
        assert (heads, tails) == (1, 1), (
            f'{handle}: {heads} heads / {tails} tails'
        )

    @pytest.mark.parametrize('handle', ['uc', 'raw'])
    def test_the_arc_re_heads_onto_the_new_tie_head(self, handle):
        uc, leaves, slur_id = _arc_whose_head_can_be_swallowed()

        if handle == 'uc':
            uc.make_sounding(leaves[0])
        else:
            uc._rt.make_sounding(leaves[0])

        assert slur_id in uc._slur_specs, 'the arc lost its identity'
        assert tuple(uc._slur_specs[slur_id]['leaf_nodes']) == (leaves[0],
                                                                leaves[2])

    def test_the_stored_spec_is_one_apply_slur_would_author(self):
        """R12 lens 2: never store a selection the public constructor
        refuses. The gap is legal only because it is a continuation of the
        member just before it."""
        uc, leaves, _ = _arc_whose_head_can_be_swallowed()
        uc.make_sounding(leaves[0])

        for spec in uc._slur_specs.values():
            members = list(spec['leaf_nodes'])
            assert uc._contiguous_slur_segments(members) == [members]

    def test_the_two_handles_agree(self):
        uc_a, leaves_a, _ = _arc_whose_head_can_be_swallowed()
        uc_b, leaves_b, _ = _arc_whose_head_can_be_swallowed()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc_a.make_sounding(leaves_a[0])
            uc_b._rt.make_sounding(leaves_b[0])

        via_uc = {k: tuple(v['leaf_nodes'])
                  for k, v in uc_a._slur_specs.items()}
        via_raw = {k: tuple(v['leaf_nodes'])
                   for k, v in uc_b._slur_specs.items()}
        assert via_uc == via_raw


# --------------------------------------------------------------------------
# The invariant the two fixes are FOR
# --------------------------------------------------------------------------

class TestOneMusicalQuestionOneAnswer:
    """R12 lens 2 (Ryan, 2026-08-31): a verb must not answer differently
    depending on which handle the caller held. That divergence was the whole
    SLUR-1 finding, and ``make_rest``/``make_sounding`` were two more doors
    into the same room -- the raw handle healed nothing at all.

    Two comparisons, deliberately asserting different things:

    * **Across HANDLES, everything must agree, ``_next_slur_id`` included.**
      An id is part of the answer -- ``apply_slur`` returns it, ``uc.events``
      carries it as a column, and the lowering keys voice pooling and slur
      teardown on it -- so two paths agreeing about notes while disagreeing
      about ids have still handed the caller two different objects.

    * **One call versus several calls, only the MUSIC must agree.** These may
      legitimately diverge in the counter under SLUR-A5, and measured, they
      do: resting leaves 3, 5 and 7 of a nine-note arc one at a time mints a
      second arc after the first rest that the third rest then kills, so
      ``_next_slur_id`` ends at 2 where the single call leaves it at 1. The
      surviving music is identical either way. Asserting the counter here
      would be asserting that Klotho batches edits, which Ryan ruled it must
      not do -- each edit heals against the music that exists at that moment,
      and a transient arc that genuinely existed is honest bookkeeping.

    MUTATION TABLE -- each line was RUN and the result recorded:
      1. Delete ``CompositionalTree.make_rest``     -> RED on every pattern
         that splits the arc: the raw handle leaves the arc wholly untouched.
      2. Delete ``CompositionalTree.make_sounding`` -> RED: raw keeps
         ``(2, 3)`` where the uc handle re-heads the arc to ``(1, 3)``.
      3. Drop ``_next_slur_id`` from the cross-handle comparison -> stays
         GREEN, which is why it is in it: membership alone cannot see an id
         divergence, and an id divergence is what SLUR-B2 was about.
      4. Assert ``_next_slur_id`` on the one-call/stepwise comparison too ->
         RED on pattern ``(3, 5, 7)``, which is what taught this test the
         difference between the two comparisons rather than a guess about it.
    """

    PATTERNS = [(2,), (4,), (2, 4), (1, 7), (2, 3), (0, 8), (3, 5, 7), (1, 4, 7)]

    @staticmethod
    def _nine_beat_arc():
        uc = UC(tempus='9/4', prolatio=(1,) * 9, beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur(leaves[0:9])
        return uc, leaves

    @staticmethod
    def _music(uc):
        return {k: tuple(v['leaf_nodes']) for k, v in uc._slur_specs.items()}

    @classmethod
    def _answer(cls, uc):
        return cls._music(uc), uc._next_slur_id

    @pytest.mark.parametrize('pattern', PATTERNS)
    def test_the_two_handles_agree_completely(self, pattern):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            via_uc, leaves = self._nine_beat_arc()
            for i in pattern:
                via_uc.make_rest(leaves[i])

            via_raw, leaves = self._nine_beat_arc()
            for i in pattern:
                via_raw._rt.make_rest(leaves[i])

        assert self._answer(via_uc) == self._answer(via_raw)

    @pytest.mark.parametrize('pattern', PATTERNS)
    def test_one_call_and_several_calls_leave_the_same_music(self, pattern):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            one_call, leaves = self._nine_beat_arc()
            one_call.make_rest([leaves[i] for i in pattern])

            stepwise, leaves = self._nine_beat_arc()
            for i in pattern:
                stepwise.make_rest(leaves[i])

        assert self._music(one_call) == self._music(stepwise)

    def test_make_sounding_agrees_across_handles(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            via_uc, leaves, _ = _arc_whose_head_can_be_swallowed()
            via_uc.make_sounding(leaves[0])

            via_raw, leaves, _ = _arc_whose_head_can_be_swallowed()
            via_raw._rt.make_sounding(leaves[0])

        assert self._answer(via_uc) == self._answer(via_raw)


class TestAuthoringATieAnnouncesToo:
    """The door a composer actually uses.

    ``uc._rt.set_node_data(leaf, tied=True)`` is the ONLY way to author a tie
    in this codebase -- there is no ``.tie()`` verb yet -- and it reproduced
    TIE-4 byte for byte after TIE-4 was closed through ``make_rest`` and
    ``make_sounding``. Tying a slurred note back to its predecessor swallows
    the arc's first member into the tie group, the ``_slur_start`` goes with
    it, and the arc reaches playback with an end marker and no start.

    The node-data writers announce only when the write touches ``tied`` or
    ``proportion``. Every pfield and mfield write goes through the same
    writers and ``_bake_envelope`` writes through them in a loop, so
    announcing unconditionally would run the whole overlay heal on the
    hottest path in the library.
    """

    def test_tying_the_arcs_first_member_re_heads_the_arc(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        slur_id = uc.apply_slur([leaves[1], leaves[2]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.set_node_data(leaves[1], tied=True)

        heads, tails = _slur_flags(uc)
        assert (heads, tails) == (1, 1), (
            f'{heads} heads / {tails} tails -- an arc no note opens')
        assert tuple(uc._slur_specs[slur_id]['leaf_nodes']) == (leaves[0],
                                                                leaves[2])

    def test_parameter_writes_stay_off_this_path(self):
        """The other direction, and the reason the gate is a key test rather
        than an unconditional announce.

        ``set_pfields`` -- which ``_bake_envelope`` calls in a loop, the
        hottest write in the library -- must not run the overlay heal, and
        neither must a ``set_node_data`` write carrying no surface key.

        Honest note: mutating the gate to announce UNCONDITIONALLY leaves
        this green, measured. ``set_pfields`` does not route through
        ``set_node_data`` at all -- the RhythmTree layer's validator refuses
        a pfield there -- so the gate is not load-bearing today. It is kept
        because ``_SURFACE_KEYS`` is what the announcement actually means,
        and because the day someone routes a parameter write through these
        writers the gate is the only thing between them and running the whole
        overlay heal per note. Saying so is cheaper than letting a later
        reader assume a mutation stands behind it.
        """
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])

        calls = []
        tree_type = type(uc._rt)
        original = tree_type._announce_leaf_surface_change
        tree_type._announce_leaf_surface_change = lambda self: calls.append(1)
        try:
            uc._rt.set_pfields(leaves[1], freq=880)
        finally:
            tree_type._announce_leaf_surface_change = original

        assert calls == [], (
            'a parameter write ran the whole overlay heal -- this gate sits '
            'on the hottest write path in the library')
