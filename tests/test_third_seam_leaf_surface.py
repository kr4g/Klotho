"""The THIRD id-state event: a leaf that STOPS BEING A LEAF -- plus the two
regressions the DEATH/RELOCATION fix wave introduced around it.

b5be431 framed the id-state contract as exactly two events. ``uc._rt.subdivide``
and ``uc._rt.graft_subtree`` are a third: the edited node's id survives IN
PLACE, but it is interior now, and slur specs and control-envelope subsets
that keep naming it inherit their markers onto every note of the new subtree.
The UC's own verbs heal this by absorbing the new leaves; the raw tree verbs
announced nothing at all.

The two regressions:

* ``_remap_slur_specs`` relocated each member independently and never
  re-checked CONTIGUITY -- ``insert_child`` into the middle of a slurred span
  authored a slur the public ``apply_slur`` refuses to create, with the
  inserted note sitting inside the slur unmarked.
* ``_mirror_param_state``'s topology check raised on a bare-root source
  (prune/remove_subtree can strip a unit to its root, RT-26): ``prolationis``
  reports ``(1,)`` and rebuilding from ``(1,)`` gives root + one child, so
  the shapes legitimately differ by that one degenerate step. All three
  rebuild recipes (``uc * k``, ``modulate_tempo``, ``modulate_tempus``) died.
"""

import warnings
from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree
from klotho.chronos.temporal_units.algorithms import modulate_tempo, modulate_tempus
from klotho.dynatos.envelopes import Envelope
from klotho.thetos import CompositionalUnit as UC


def _tagged(prolatio=(1, 1, 1, 1)):
    """A UC whose every beat carries its own freq tag (100, 200, ...)."""
    uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields={'freq': 0})
    for i, node in enumerate(uc._rt.leaf_nodes):
        uc.set_pfields(node, freq=100 * (i + 1))
    return uc


def _marked(uc, column):
    """Freqs of the events carrying flag 1 in *column* ([] when no slur exists)."""
    ev = uc.events
    if column not in ev.columns:
        return []
    return [float(row['freq']) for _, row in ev.iterrows() if row[column] == 1.0]


class TestLeafStopsBeingALeaf:
    """C-1: raw-tree subdivide/graft must announce the leaf-surface change."""

    def test_raw_subdivide_absorbs_the_new_leaves_into_the_slur(self):
        """FLIPPED by Ryan's ruling of 2026-08-30: the policy is ABSORB.

        This test asserted DROP, which is the choice `eb03bd4` shipped and
        the ruling overrules. The subdivided note is interior and so cannot
        itself be a member -- that part never changed -- but the three
        children it grew take its place rather than the slur dissolving.
        """
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.subdivide(L[1], (1, 1, 1))

        (spec,) = uc._slur_specs.values()
        assert L[1] not in spec['leaf_nodes'], 'a non-leaf is never a member'
        assert spec['leaf_nodes'] == tuple(uc._rt.subtree_leaves(L[1])) + (L[2],)
        # the children inherit the ex-leaf's freq, so the head reads as 200
        assert _marked(uc, '_slur_start') == [200.0]
        assert _marked(uc, '_slur_end') == [300.0]

    def test_raw_subdivide_at_the_slur_edge_extends_the_arc_onto_the_new_leaves(self):
        """FLIPPED with the one above. The tail EXTENDS, it does not retreat.

        Growing children under the slur's LAST member used to shorten the
        arc to the survivors; under ABSORB the arc reaches the last child of
        what the member grew.
        """
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        uc._rt.subdivide(L[3], (1, 1))

        (spec,) = uc._slur_specs.values()
        assert spec['leaf_nodes'] == (L[1], L[2]) + tuple(uc._rt.subtree_leaves(L[3]))
        assert _marked(uc, '_slur_start') == [200.0]
        # the tail is now the LAST child of the ex-leaf, which inherited 400
        assert _marked(uc, '_slur_end') == [400.0]

    def test_raw_graft_absorbs_the_grafted_leaves_into_the_slur(self):
        """FLIPPED with the two above -- graft and subdivide are one policy."""
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.graft_subtree(L[1], RhythmTree(meas='1/4', subdivisions=(1, 1)))

        (spec,) = uc._slur_specs.values()
        assert spec['leaf_nodes'] == tuple(uc._rt.subtree_leaves(L[1])) + (L[2],)
        assert _marked(uc, '_slur_start') == [200.0]
        assert _marked(uc, '_slur_end') == [300.0]

    def test_raw_subdivide_absorbs_the_new_leaves_into_envelope_subsets(self):
        """Strengthened, not merely renamed.

        The old assertion was ``L[1] not in desc['leaf_subset']``, which
        DROP and ABSORB both satisfy -- absorption substitutes the new
        leaves for the ex-leaf, so the ex-leaf is absent either way. It
        proved nothing about the policy. The positive form does.
        """
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'freq',
                          node=[L[0], L[1]], control=True)

        uc._rt.subdivide(L[1], (1, 1, 1))

        (desc,) = uc._control_envelopes.values()
        assert L[1] not in desc['leaf_subset'], 'a non-leaf is never a target'
        assert desc['leaf_subset'] == (L[0],) + tuple(uc._rt.subtree_leaves(L[1]))

    def test_uc_verb_still_absorbs_the_new_leaves(self):
        """The owning verb's richer heal must be untouched by the seam."""
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc.subdivide(L[1], (1, 1, 1))

        (spec,) = uc._slur_specs.values()
        assert len(spec['leaf_nodes']) == 4  # three children + L[2]


class TestRelocationCannotAuthorANonContiguousSlur:
    """C-2: an insertion into a slurred span splits the slur at the intruder,
    exactly as a rest does -- it must never extend over a note that was never
    slurred, and never store a selection ``apply_slur`` refuses."""

    def test_insertion_inside_a_two_note_slur_dissolves_it(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2]])

        uc._rt.insert_child(uc._rt.root, 2, proportion=1)

        # two one-note fragments are not slurs; nothing stays marked and the
        # inserted note is not swallowed by a span it was never part of
        assert uc._slur_specs == {}
        assert _marked(uc, '_slur_start') == []
        assert _marked(uc, '_slur_end') == []

    def test_insertion_splits_a_longer_slur_and_keeps_the_viable_fragment(self):
        uc = _tagged(prolatio=(1, 1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[1], L[2], L[3]])

        uc._rt.insert_child(uc._rt.root, 3, proportion=1)

        # the fragment before the intruder still has two notes and survives;
        # the one-note fragment after it dissolves
        (spec,) = uc._slur_specs.values()
        leaf_order = list(uc._rt.leaf_nodes)
        indices = [leaf_order.index(n) for n in spec['leaf_nodes']]
        assert indices == [1, 2]
        assert spec['index_range'] == (1, 2)
        assert _marked(uc, '_slur_start') == [200.0]
        assert _marked(uc, '_slur_end') == [300.0]

    def test_every_stored_spec_stays_contiguous_after_insertion(self):
        """The invariant over ALL surviving specs, not only the one its
        siblings name.

        The fixture has to be chosen so that specs survive. On the four-note
        fixture the siblings use, the slur dissolves entirely,
        ``_slur_specs`` is ``{}``, and the loop below runs zero times and
        asserts nothing. Here two slurs are drawn and the insertion lands
        inside the first: the fragment after the intruder survives, and the
        untouched second slur relocates whole, so the loop has two specs to
        check.
        """
        uc = _tagged(prolatio=(1, 1, 1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur([L[0], L[1], L[2]])
        uc.apply_slur([L[3], L[4], L[5]])

        uc._rt.insert_child(uc._rt.root, 1, proportion=1)

        # the invariant apply_slur enforces: members occupy consecutive
        # leaf positions (no tie groups in play here)
        assert len(uc._slur_specs) == 2, \
            'the fixture must leave specs behind, or the loop checks nothing'
        leaf_order = list(uc._rt.leaf_nodes)
        for spec in uc._slur_specs.values():
            indices = sorted(leaf_order.index(n) for n in spec['leaf_nodes'])
            assert indices == list(range(indices[0], indices[-1] + 1))


class TestBareRootUnitSurvivesTheRebuildRecipes:
    """C-3: the topology check stays, but the bare-root shape (RT-26) maps
    root-to-root instead of dying."""

    def _bare(self):
        u = UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
               pfields={'amp': 0.3})
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for n in list(u._rt.leaf_nodes):
                u.remove_subtree(n)
        return u

    def test_identity_scale_keeps_the_root_values(self):
        out = self._bare() * Fraction(1, 1)
        assert out.events['amp'].tolist() == [0.3]

    def test_modulate_tempo_keeps_the_root_values(self):
        out = modulate_tempo(self._bare(), '1/4', 120)
        assert out.events['amp'].tolist() == [0.3]

    def test_modulate_tempus_keeps_the_root_values(self):
        out = modulate_tempus(self._bare(), 1, '2/4')
        assert out.events['amp'].tolist() == [0.3]


def _slur_shape(uc):
    """Per slur id on the lowering surface: heads, tails, and positions.

    ``positions`` are indices into the events table, i.e. places in
    left-to-right performance order.
    """
    events = uc.events
    if '_slur_id' not in events.columns:
        return {}
    shape = {}
    for position, (_, row) in enumerate(events.iterrows()):
        slur_id = row['_slur_id']
        if slur_id != slur_id:          # NaN: this event carries no slur
            continue
        entry = shape.setdefault(int(slur_id),
                                 {'heads': 0, 'tails': 0, 'positions': []})
        entry['positions'].append(position)
        if row['_slur_start'] == 1.0:
            entry['heads'] += 1
        if row['_slur_end'] == 1.0:
            entry['tails'] += 1
    return shape


def _non_leaf_members(uc):
    """Overlay members naming a node that is not on the leaf surface."""
    leaves = set(uc._rt.leaf_nodes)
    slurs = {slur_id: [n for n in spec['leaf_nodes'] if n not in leaves]
             for slur_id, spec in uc._slur_specs.items()}
    envelopes = {env_id: [n for n in desc['leaf_subset'] if n not in leaves]
                 for env_id, desc in uc._control_envelopes.items()}
    return ({k: v for k, v in slurs.items() if v},
            {k: v for k, v in envelopes.items() if v})


#: The three doors through which a leaf can stop being a leaf. The first
#: two announce the event (``d5a1b20``); the third had no override at all.
LEAF_GROWTH_DOORS = [
    ('subdivide', lambda uc, node: uc._rt.subdivide(node, (1, 1, 1))),
    ('graft_subtree',
     lambda uc, node: uc._rt.graft_subtree(
         node, RhythmTree(meas='1/4', subdivisions=(1, 1)))),
    ('insert_child',
     lambda uc, node: [uc._rt.insert_child(node, k, proportion=1)
                       for k in range(3)]),
]


class TestNoOverlayNamesANodeThatStoppedBeingALeaf:
    """LAYER-12 -- the rule the code already states, enforced at every door.

    Derivation, from a rule written in this package rather than from what
    the code does. ``_remap_slur_specs`` states it as a comment on the
    line that applies it: "a note that stopped being a leaf is no longer
    slurrable", and ``_remap_control_envelopes`` repeats it for envelope
    subsets. It follows from what a slur IS: ``apply_slur`` selects among
    ``leaf_nodes``, and only leaves become events, so an overlay member
    that is not a leaf denotes no note at all.

    The rule holds at ``subdivide`` and ``graft_subtree`` because
    ``d5a1b20`` gave each an override. ``insert_child`` never got one, and
    neither shipped seam fires for it -- the node is still in the tree, so
    DEATH's test is false, and ``Tree.insert_child`` announces a
    relocation only when a sibling actually shifted, which an insert into
    a CHILDLESS node never does.
    """

    @pytest.mark.parametrize('door, grow', LEAF_GROWTH_DOORS,
                             ids=[d for d, _ in LEAF_GROWTH_DOORS])
    def test_a_slur_member_that_grows_children_leaves_the_spec(self, door, grow):
        uc = _tagged()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[1], leaves[2]])
        assert uc._slur_specs, 'the fixture must draw a slur, or this checks nothing'

        grow(uc, leaves[1])

        stale_slurs, _ = _non_leaf_members(uc)
        assert stale_slurs == {}, f'{door} left a slur naming a non-leaf'

    @pytest.mark.parametrize('door, grow', LEAF_GROWTH_DOORS,
                             ids=[d for d, _ in LEAF_GROWTH_DOORS])
    def test_an_envelope_target_that_grows_children_leaves_the_subset(self, door, grow):
        uc = _tagged()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'freq',
                          node=[leaves[0], leaves[1], leaves[2]], control=True)
        assert uc._control_envelopes, 'the fixture must draw an envelope'

        grow(uc, leaves[1])

        _, stale_envelopes = _non_leaf_members(uc)
        assert stale_envelopes == {}, f'{door} left an envelope naming a non-leaf'


class TestEverySlurOnTheSurfaceIsOneArc:
    """LAYER-12 -- what ``apply_slur`` refuses to author, no edit may create.

    Derivation, from the authoring contract rather than from behaviour. A
    slur is one arc from one note to one note: ``apply_slur`` enforces
    contiguity (``_validate_slur_selection`` raises "Selection must be
    contiguous in left-to-right tree order") and dissolves fragments below
    two notes, and ``_remap_slur_specs``' own comment names contiguity as
    "the property that DEFINED the slur". So on the lowering surface every
    slur id must carry exactly ONE ``_slur_start``, exactly ONE
    ``_slur_end``, and a contiguous run of events between them.

    This invariant is POLICY-AGNOSTIC. Whether a leaf that grows children
    has its slur DROPPED (what ``subdivide`` chose) or ABSORBED onto the
    new leaves (what ``uc.subdivide`` chose), the result is one arc either
    way. It fails only on the third state -- an overlay left naming a node
    the surface no longer has.
    """

    @staticmethod
    def _two_slurs():
        """Six notes, two slurs: 0-1 untouched, 3-4 the one that is edited.

        The untouched slur is what keeps the check non-vacuous: under a
        DROP policy the edited slur dissolves, and a fixture with only
        that slur would assert nothing at all.
        """
        uc = UC(tempus='6/4', prolatio=(1,) * 6, beat='1/4', bpm=60,
                pfields={'freq': 0})
        leaves = list(uc._rt.leaf_nodes)
        for i, node in enumerate(leaves):
            uc.set_pfields(node, freq=100 * (i + 1))
        uc.apply_slur([leaves[0], leaves[1]])
        uc.apply_slur([leaves[3], leaves[4]])
        return uc, leaves

    @pytest.mark.parametrize('door, grow', LEAF_GROWTH_DOORS,
                             ids=[d for d, _ in LEAF_GROWTH_DOORS])
    def test_growing_children_under_a_slurred_note_leaves_one_arc(self, door, grow):
        uc, leaves = self._two_slurs()

        grow(uc, leaves[3])

        shape = _slur_shape(uc)
        assert shape, 'the untouched slur must survive, or this checks nothing'
        for slur_id, entry in shape.items():
            assert entry['heads'] == 1, f'{door}: slur {slur_id} has {entry["heads"]} heads'
            assert entry['tails'] == 1, f'{door}: slur {slur_id} has {entry["tails"]} tails'
            positions = entry['positions']
            assert positions == list(range(positions[0], positions[-1] + 1)), \
                f'{door}: slur {slur_id} is not contiguous: {positions}'

    def test_an_insert_cannot_author_a_slur_apply_slur_would_refuse(self):
        """Consequence (b): the stale spec defeated the overlap check.

        ``_validate_slur_selection`` tests intersection against the stored
        ``leaf_set``. While that set named a node the surface no longer
        had, a second ``apply_slur`` over the hidden children was accepted
        -- and the first slur was left with a head and no tail anywhere on
        the surface.
        """
        uc = _tagged()
        leaves = list(uc._rt.leaf_nodes)
        uc.apply_slur([leaves[0], leaves[1]])

        uc._rt.insert_child(leaves[1], 0, proportion=1)
        uc._rt.insert_child(leaves[1], 1, proportion=1)

        current = list(uc._rt.leaf_nodes)
        try:
            uc.apply_slur([current[1], current[2]])
        except ValueError:
            pass                        # refusing is a correct answer too

        for slur_id, entry in _slur_shape(uc).items():
            assert entry['heads'] == 1, f'slur {slur_id}: {entry}'
            assert entry['tails'] == 1, f'slur {slur_id}: {entry}'
