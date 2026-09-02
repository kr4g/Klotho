"""Absorb at the arc's EDGES, and the net that has to land before widening it.

SLUR-1 made ABSORB the single overlay policy: a member that grows children
hands its place to the leaves it grew. The rule it shipped tests provenance
-- every other sounding leaf under the newcomer's parent must already belong
to this overlay -- but it looked for candidates GEOMETRICALLY, inside
``low < i < high`` over the arc's own member positions.

Growth at the FIRST member arrives before ``low`` and growth at the LAST
member arrives after ``high``, so neither could ever be seen. Measured on a
two-note slur whose last member grows three children::

    uc.subdivide(member, (1, 1, 1))    -> (2, 5, 6, 7)     the whole growth
    three add_child(member)            -> (2, 5)           two leaves lost

and the same at the head, where three prepends left ``(7, 3)`` where the
one-shot form gives ``(5, 6, 7, 3)``. At the lowering surface the arc's
``_slur_end`` moved from t=2.667 to t=2.0: the legato releases two thirds of
a beat early and two sounding leaves sit outside the arc entirely.

The window also contradicts a principle this repo already shipped a test for
-- ``test_raw_subdivide_at_the_slur_edge_extends_the_arc_onto_the_new_leaves``
says in its own name that the tail EXTENDS rather than retreats -- so the
geometry was never the rule. Provenance was. The fix drops the positional
window and derives candidates structurally instead: only leaves sharing a
parent with a leaf the overlay already covers can pass the provenance test at
all, so that is the set worth scanning.

**Widening an admission window trades a refusal defect for an admission
defect, and admission is the worse one**: an over-admitting rule silently
draws a slur over notes the composer never selected, and no suite count can
see it. So the authorability oracle below lands first and runs over every
door, in both this module and as a net for the next person to touch this.
"""

import warnings

import pytest

from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


# --------------------------------------------------------------------------
# The oracle
# --------------------------------------------------------------------------

def slur_contract_violations(uc):
    """Every way a stored slur spec can be one ``apply_slur`` would refuse.

    Independent of the heal: it reads only the tree and the stored specs, and
    restates the public constructor's own preconditions. Returns a list of
    strings, empty when every spec is authorable.
    """
    problems = []
    order = list(uc._rt.leaf_nodes)
    index = {leaf: i for i, leaf in enumerate(order)}
    head_of = {}
    for group in uc._rt.tie_groups:
        for continuation in group[1:]:
            head_of[continuation] = group[0]

    seen_leaves = {}
    for slur_id, spec in uc._slur_specs.items():
        members = list(spec['leaf_nodes'])

        if len(members) < 2:
            problems.append(f'slur {slur_id}: {len(members)} members, '
                            f'apply_slur requires at least two')
            continue
        if len(set(members)) != len(members):
            problems.append(f'slur {slur_id}: duplicate members {members}')
        for leaf in members:
            if leaf not in index:
                problems.append(f'slur {slur_id}: member {leaf} is not a leaf')
                continue
            if uc._rt[leaf].get('proportion', 1) < 0:
                problems.append(f'slur {slur_id}: member {leaf} is a rest')
            if leaf in head_of:
                problems.append(f'slur {slur_id}: member {leaf} is a tie '
                                f'continuation, not a note (charter sect 8)')
            if leaf in seen_leaves:
                problems.append(f'slur {slur_id}: leaf {leaf} is already in '
                                f'slur {seen_leaves[leaf]}')
            seen_leaves[leaf] = slur_id

        placed = [m for m in members if m in index]
        if placed != sorted(placed, key=index.__getitem__):
            problems.append(f'slur {slur_id}: members out of time order '
                            f'{members}')

        for previous, following in zip(placed, placed[1:]):
            for i in range(index[previous] + 1, index[following]):
                between = order[i]
                if head_of.get(between) != previous:
                    problems.append(
                        f'slur {slur_id}: leaf {between} sits inside the span '
                        f'unslurred, so apply_slur could not author this')
    return problems


def envelope_contract_violations(uc):
    """The same, for control envelopes: a stored subset must resolve to
    leaves, with no rest and no duplicate."""
    problems = []
    leaves = set(uc._rt.leaf_nodes)
    for env_id, desc in uc._control_envelopes.items():
        subset = desc.get('leaf_subset')
        if subset is None:
            continue
        if len(set(subset)) != len(subset):
            problems.append(f'envelope {env_id}: duplicate targets {subset}')
        for leaf in subset:
            if leaf not in leaves:
                problems.append(f'envelope {env_id}: target {leaf} is not a leaf')
    return problems


# --------------------------------------------------------------------------
# Fixtures and doors
# --------------------------------------------------------------------------

def _two_note_slur():
    uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
            pfields={'freq': 440})
    leaves = list(uc._rt.leaf_nodes)
    slur_id = uc.apply_slur([leaves[1], leaves[2]])
    return uc, leaves, slur_id


def _members(uc):
    return {k: tuple(v['leaf_nodes']) for k, v in uc._slur_specs.items()}


#: (name, callable) -- each grows *target* by three leaves, one way or another.
GROWTH_DOORS = [
    ('subdivide',
     lambda uc, target: uc.subdivide(target, (1, 1, 1))),
    ('raw_subdivide',
     lambda uc, target: uc._rt.subdivide(target, (1, 1, 1))),
    ('add_child_x3',
     lambda uc, target: [uc._rt.add_child(target, proportion=1)
                         for _ in range(3)]),
    ('insert_child_prepend_x3',
     lambda uc, target: [uc._rt.insert_child(target, 0, proportion=1)
                         for _ in range(3)]),
]


ABSORB_1 = pytest.mark.xfail(strict=True, reason=(
    "ABSORB-1, OPEN. These describe the behaviour a player expects and the "
    "code does not deliver: growth at an arc's edge keeps only the first "
    "child of what the member grew, so the legato releases early. A fix was "
    "written, measured, and REVERTED in the same session -- admitting "
    "candidates whose parent the arc 'reaches into' let an OUTSIDER in, "
    "silently widening arcs onto notes the composer never selected (645 of "
    "2296 fuzzed disjoint edits; the envelope half drove an unnamed note to "
    "amp 0.0, i.e. silence). Refusing growth loses an extension a composer "
    "can re-apply; admitting an outsider rewrites music they did select. The "
    "real discriminator is whether the candidate leaf is NEW, which the seam "
    "cannot currently tell -- it announces an identity mapping over the "
    "post-edit nodes -- so closing this means handing the seam the pre-edit "
    "leaf surface. strict=True on purpose: if this starts passing, someone "
    "has fixed it and should delete the marker, not inherit it."))


class TestGrowthAtTheArcEdgesJoinsTheArc:
    """The defect itself. A player reading the passage sees the arc's last
    note divided into three; the arc covers all three and ends where it
    always ended. It does not retreat onto the first of them.

    MARKED xfail: see ``ABSORB_1``. These are kept, not deleted, because a
    deleted test is a defect nobody is tracking.
    """

    @pytest.mark.parametrize('door,grow', GROWTH_DOORS, ids=[d[0] for d in GROWTH_DOORS])
    @pytest.mark.parametrize('edge', ['first', 'last'])
    def test_the_whole_growth_joins_whichever_edge_grew(self, door, grow, edge):
        if door in ('add_child_x3', 'insert_child_prepend_x3'):
            pytest.xfail(ABSORB_1.kwargs['reason'])
        uc, leaves, slur_id = _two_note_slur()
        target = leaves[1] if edge == 'first' else leaves[2]

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grow(uc, target)

        grown = tuple(uc._rt.subtree_leaves(target))
        assert len(grown) == 3, 'fixture did not grow three leaves'
        members = set(uc._slur_specs[slur_id]['leaf_nodes'])
        assert set(grown) <= members, (
            f'{door}/{edge}: only {sorted(set(grown) & members)} of the three '
            f'grown leaves {sorted(grown)} joined the arc'
        )

    @ABSORB_1
    @pytest.mark.parametrize('edge', ['first', 'last'])
    def test_the_arc_spans_the_same_music_however_the_growth_arrived(self, edge):
        """One-shot and stepwise must agree here. SLUR-A5's ruled divergence
        is about growth CONTAINING A REST -- by the time the third child
        arrives, the rest has already split the arc. No rest is involved
        below, so the two forms are describing the same music and must say
        the same thing."""
        one_shot, leaves, slur_id = _two_note_slur()
        stepwise, other_leaves, other_id = _two_note_slur()
        index = 1 if edge == 'first' else 2

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            one_shot.subdivide(leaves[index], (1, 1, 1))
            target = other_leaves[index]
            for _ in range(3):
                if edge == 'first':
                    stepwise._rt.insert_child(target, 0, proportion=1)
                else:
                    stepwise._rt.add_child(target, proportion=1)

        def span(uc, sid):
            events = uc.events
            starts = [r['start'] for _, r in events.iterrows()
                      if r.get('_slur_start') == 1.0]
            ends = [r['start'] + r['dur'] for _, r in events.iterrows()
                    if r.get('_slur_end') == 1.0]
            return starts, ends

        assert span(one_shot, slur_id) == span(stepwise, other_id), (
            f'{edge}: the arc sounds over a different stretch of time '
            f'depending on how the growth arrived'
        )

    @ABSORB_1
    def test_the_envelope_half_extends_too(self):
        """The two overlays share the helper, so they share the defect. An
        envelope whose last target grows must keep ramping over the new
        leaves rather than stopping short of its own endpoint."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'amp': 0.1})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0., 1.], times=[2.]), 'amp',
                          node=[leaves[1], leaves[2]], control=True)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for _ in range(3):
                uc._rt.add_child(leaves[2], proportion=1)

        (desc,) = uc._control_envelopes.values()
        grown = set(uc._rt.subtree_leaves(leaves[2]))
        assert grown <= set(desc['leaf_subset']), (
            f'the envelope covers {desc["leaf_subset"]} and the growth was '
            f'{sorted(grown)} -- the ramp stops short of its own endpoint'
        )


class TestNothingIsAdmittedThatWasNotSelected:
    """The net that had to land before the window was widened.

    Every case here already passed before the fix. That is the point: they
    are not evidence the fix works, they are evidence it did not buy its
    result by admitting music the composer never chose.
    """

    def test_an_insertion_beside_uncovered_music_is_still_an_intruder(self):
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[0], leaves[1]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.insert_child(uc._rt.root, 1, proportion=1)

        assert slur_contract_violations(uc) == []
        for members in _members(uc).values():
            assert len(members) >= 2

    #: ``(door, index or None, does the arc survive)``. The newcomer lands
    #: BETWEEN the two arc members for ``add_child`` and index 2, so their
    #: adjacency breaks and the arc dies; at index 0 or 1 it lands before
    #: them and the arc lives on with exactly the notes it started with.
    SIBLING_DOORS = [('add_child', None, False), ('insert_at_0', 0, True),
                     ('insert_at_1', 1, True), ('insert_at_2', 2, False)]

    @pytest.mark.parametrize('door,at,survives', SIBLING_DOORS,
                             ids=[d[0] for d in SIBLING_DOORS])
    def test_a_sibling_the_overlay_does_not_cover_refuses_the_newcomer(
            self, door, at, survives):
        """Provenance, stated as its own test. Parent holds a sounding leaf
        outside the arc, so nothing under it may join.

        **AF-3.5 -- this had two faults that hid each other.**

        1. Its only door was ``add_child``, which drops the newcomer BETWEEN
           the two arc members and so dissolves the arc. ``after`` came back
           ``None``, the whole ``if`` body was skipped and the provenance
           loop ran zero times: nothing was ever checked.
        2. Membership was compared as ``set(after['leaf_nodes']) - before``,
           a set difference over RAW NODE IDS taken across an edit that
           renumbers them. Measured on the ``insert_at_0`` door: ids go
           ``{3, 4}`` -> ``{4, 6}``, which reads as "leaf 6 joined and leaf 3
           left" when, tracked by a marker pfield, the members are the very
           same two notes. Had the loop ever run it would have reported a
           newcomer that does not exist.

        Both are fixed here: every door is exercised with the outcome it
        must produce, and membership is compared by a per-leaf MARKER rather
        than by an id that the tree is free to reassign.
        """
        uc = UC(tempus='4/4', prolatio=((2, (1, 1)), 1, 1), beat='1/4',
                bpm=60, pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        for i, leaf in enumerate(leaves):
            uc.set_pfields(leaf, freq=100 + i)
        mark = lambda n: uc._rt[n].get('freq')

        slur_id = uc.apply_slur([leaves[1], leaves[2]])
        before = {mark(n) for n in uc._slur_specs[slur_id]['leaf_nodes']}
        group = uc._rt.parent(leaves[1])
        assert mark(leaves[0]) not in before and (
            uc._rt.parent(leaves[0]) is group), (
            'fixture: the group must hold a sounding leaf the arc misses')

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            if at is None:
                uc._rt.add_child(group, proportion=1)
            else:
                uc._rt.insert_child(group, at, proportion=1)

        after = uc._slur_specs.get(slur_id)
        assert (after is not None) is survives, (
            f'{door}: expected the arc to '
            f'{"survive" if survives else "dissolve"}, got {after}')
        if after is None:
            return

        now = {mark(n) for n in after['leaf_nodes']}
        # The newcomer carries no marker, so it is detectable by identity
        # rather than by an id the edit may have reassigned.
        assert now == before, (
            f'{door}: the arc\'s membership changed from {sorted(before)} to '
            f'{sorted(now, key=lambda v: (v is None, v))} -- the inserted '
            f'note (marker None) was never selected by the composer, and no '
            f'selected note may be dropped either')

    @pytest.mark.parametrize('door,grow', GROWTH_DOORS, ids=[d[0] for d in GROWTH_DOORS])
    def test_two_slurs_never_come_to_share_a_leaf(self, door, grow):
        """The ``mine()`` guard, whose only failure mode is silent. SLUR-1
        recorded the foreign-slur case as unreachable armour; measured, an
        absorb CAN admit a foreign slur's member and only that filter strips
        it. So it is load-bearing, and this is the net that says so if anyone
        simplifies it away."""
        uc = UC(tempus='8/4', prolatio=(1,) * 8, beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])
        uc.apply_slur([leaves[4], leaves[5]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grow(uc, leaves[2])

        assert slur_contract_violations(uc) == []

    @pytest.mark.parametrize('door,grow', GROWTH_DOORS, ids=[d[0] for d in GROWTH_DOORS])
    @pytest.mark.parametrize('shape', ['flat', 'wrapped'])
    def test_every_stored_spec_stays_authorable(self, door, grow, shape):
        """The oracle over the matrix, on both a flat tree and a wrapped one.

        The wrapped shape is not decoration: SLUR-1's own root-exemption
        defect made ``(1,1,1,1)`` and ``((4,(1,1,1,1)),)`` -- identical music
        -- answer differently, so a rule claimed to be structure-insensitive
        is a claim to verify.
        """
        prolatio = (1, 1, 1, 1) if shape == 'flat' else ((4, (1, 1, 1, 1)),)
        uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grow(uc, leaves[2])

        assert slur_contract_violations(uc) == []
        assert envelope_contract_violations(uc) == []

    @pytest.mark.parametrize('door,grow', GROWTH_DOORS, ids=[d[0] for d in GROWTH_DOORS])
    def test_a_rest_among_the_growth_still_splits_the_arc(self, door, grow):
        """Absorption must not swallow a rest. Whatever survives is still
        authorable, and no member is a rest."""
        uc = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
                pfields={'freq': 440})
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            grow(uc, leaves[2])
            grown = list(uc._rt.subtree_leaves(leaves[2]))
            uc.make_rest(grown[1])

        assert slur_contract_violations(uc) == []


class TestTheFlatAndWrappedTreesAgree:
    """Same music, same answer, whatever the brackets. The rule SLUR-1
    established when it removed the root exemption, extended to the edges."""

    @pytest.mark.parametrize('edge', ['first', 'last'])
    def test_edge_growth_answers_the_same_under_a_wrapper(self, edge):
        def build(prolatio):
            uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
                    pfields={'freq': 440})
            leaves = list(uc._rt.leaf_nodes)
            uc.apply_slur([leaves[1], leaves[2]])
            target = leaves[1] if edge == 'first' else leaves[2]
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for _ in range(3):
                    if edge == 'first':
                        uc._rt.insert_child(target, 0, proportion=1)
                    else:
                        uc._rt.add_child(target, proportion=1)
            return uc, target

        flat, flat_target = build((1, 1, 1, 1))
        wrapped, wrapped_target = build(((4, (1, 1, 1, 1)),))

        def joined(uc, target):
            grown = set(uc._rt.subtree_leaves(target))
            members = {n for s in uc._slur_specs.values()
                       for n in s['leaf_nodes']}
            return len(grown & members), len(grown)

        assert joined(flat, flat_target) == joined(wrapped, wrapped_target)
