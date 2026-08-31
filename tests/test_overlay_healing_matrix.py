"""REC-1 lane: the cells the guard file never pinned.

Every assertion here is a PROPERTY -- no literal an implementation could
fake -- derived from a contract stated in the source, never from what the
code was observed to do:

* ``Tree._notify_nodes_relocated``: "an id absent from it was DESTROYED and
  every id-keyed map must drop it -- rustworkx reuses freed indices, so an
  entry left behind does not merely leak, it re-attaches to whatever lands
  in the slot."
* ``CompositionalUnit._remap_control_envelopes``: "the descriptor must not
  keep naming an id the public API could never select".
* ``CompositionalUnit._relocate_id_keyed_state``: "a verb reached THROUGH
  ``uc._rt`` ... heals the same overlays this unit's own deleters heal."
* ``CompositionalTree._announce_leaf_surface_change``: the third event is
  "a leaf that STOPPED BEING A LEAF"; overlays naming it "would inherit
  their markers onto every note of the subtree it grew".
* ``RhythmTree._respell``: the source map "is what carries pfields, mfields
  and instrument bindings across the rebuild -- and, through
  ``_notify_nodes_relocated``, everything else keyed by node id (slurs,
  memoized Bind draws, control-envelope targets)."
"""
import random
import warnings

import pytest

from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC, Bind


def _tagged(prolatio=(1, 1, 1, 1, 1, 1)):
    """A UC whose every leaf carries an mfield naming the event it IS.

    The tag is an mfield, not a pfield, so baking an envelope over the
    pfields cannot overwrite the identity the assertions read.
    """
    uc = UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=60,
            pfields={'amp': 0.1}, mfields={'tag': ''})
    for i, node in enumerate(uc._rt.leaf_nodes):
        uc.set_mfields(node, tag=f'e{i}')
    return uc


def _envelope_on(uc, leaves):
    uc.apply_envelope(Envelope([0.0, 1.0], times=[2.0]), 'amp',
                      node=list(leaves), control=True)


def _tags(uc, nodes):
    return [uc.get_mfield(n, 'tag') for n in nodes]


RAW_DELETERS = [
    ('_rt.prune',          lambda uc, L: uc._rt.prune(L[2])),
    ('_rt.remove_subtree', lambda uc, L: uc._rt.remove_subtree(L[2])),
    ('_rt.prune_leaves',   lambda uc, L: uc._rt.prune_leaves(1)),
    ('_rt.prune_to_depth', lambda uc, L: uc._rt.prune_to_depth(0)),
]


class TestNoOverlayOutlivesTheNodeItNames:
    """DEATH through a RAW TREE verb, which no UC override intercepts."""

    @pytest.mark.parametrize('name, delete', RAW_DELETERS,
                             ids=[n for n, _ in RAW_DELETERS])
    def test_a_control_envelope_names_no_id_the_delete_freed(self, name, delete):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, L[2:4])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            delete(uc, L)
        leaves = set(uc._rt.leaf_nodes)
        nodes = set(uc._rt.nodes)
        for env_id, desc in uc._control_envelopes.items():
            assert desc['anchor_node'] in nodes, (
                f'{name}: envelope {env_id} anchors on a destroyed node')
            if desc['leaf_subset'] is not None:
                dangling = [n for n in desc['leaf_subset'] if n not in leaves]
                assert dangling == [], (
                    f'{name}: envelope {env_id} still targets {dangling}, '
                    f'which the delete freed; leaves are {sorted(leaves)}')

    @pytest.mark.parametrize('name, delete', RAW_DELETERS,
                             ids=[n for n, _ in RAW_DELETERS])
    def test_a_slur_names_no_id_the_delete_freed(self, name, delete):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=L[2:5])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            delete(uc, L)
        leaves = set(uc._rt.leaf_nodes)
        for slur_id, spec in uc._slur_specs.items():
            dangling = [n for n in spec['leaf_nodes'] if n not in leaves]
            assert dangling == [], (
                f'{name}: slur {slur_id} still names {dangling}; '
                f'leaves are {sorted(leaves)}')

    @pytest.mark.parametrize('name, delete', RAW_DELETERS,
                             ids=[n for n, _ in RAW_DELETERS])
    def test_a_memoized_bind_draw_names_no_id_the_delete_freed(self, name, delete):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.set_pfields(uc._rt.root, amp=Bind(lambda ctx: random.random()))
        _ = uc.events                      # warm the memo
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            delete(uc, L)
        nodes = set(uc._rt.nodes)
        dangling = sorted({n for (n, _k) in uc._bind_memo if n not in nodes})
        assert dangling == [], (
            f'{name}: memoized draws survive for destroyed nodes {dangling}')


class TestAFreedIdIsNotInheritedByItsSuccessor:
    """The consequence the invariants above exist to prevent, end to end."""

    def test_a_brand_new_note_does_not_arrive_already_slurred(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=L[2:5])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.remove_subtree(L[3])    # frees an id in the middle of the slur
        newcomer = uc._rt.add_child(uc._rt.root, proportion=1)
        uc.set_mfields(newcomer, tag='newcomer')
        slurred = {n for spec in uc._slur_specs.values()
                   for n in spec['leaf_nodes']}
        assert newcomer not in slurred, (
            'a note created after the slur was drawn is inside it because it '
            'landed in the freed id')

    def test_a_brand_new_note_is_not_already_a_control_envelope_target(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, L[2:4])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.remove_subtree(L[2])
            uc._rt.remove_subtree(L[3])
        newcomers = [uc._rt.add_child(uc._rt.root, proportion=1)
                     for _ in range(2)]
        targeted = {n for r in uc.resolved_control_envelopes()
                    for n in r['target_nodes']}
        assert not (set(newcomers) & targeted), (
            'notes created after the envelope was drawn are automated by it '
            'because they landed in the freed ids')

    def test_a_brand_new_note_does_not_inherit_a_dead_notes_memoized_draw(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.set_pfields(uc._rt.root, amp=Bind(lambda ctx: random.random()))
        _ = uc.events
        dead_draw = uc._bind_memo[(L[2], 'amp')]
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            uc._rt.remove_subtree(L[2])
        newcomer = uc._rt.add_child(uc._rt.root, proportion=1)
        _ = uc.events
        assert uc.get_pfield(newcomer, 'amp') != dead_draw, (
            'the new note re-used the destroyed note\'s memoized draw')


class TestALeafThatStoppedBeingALeafDropsItsOverlays:
    """The THIRD event, through ``move_subtree``.

    ``CompositionalTree`` announces this for ``subdivide`` and
    ``graft_subtree``. ``move_subtree`` produces the same state -- the
    target keeps its id and stops being a leaf -- and is a supported path
    (``tests/test_timing_cache_staleness.py`` exercises it).
    """

    def test_move_subtree_drops_the_ex_leaf_from_the_slur(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=[L[0], L[1]])
        uc._rt.move_subtree(L[4], L[1])    # L[1] gains a child
        leaves = set(uc._rt.leaf_nodes)
        for slur_id, spec in uc._slur_specs.items():
            interior = [n for n in spec['leaf_nodes'] if n not in leaves]
            assert interior == [], (
                f'slur {slur_id} still names {interior}, which is interior now')

    def test_move_subtree_does_not_slur_the_note_that_moved_in(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        uc.apply_slur(node=[L[0], L[1]])
        moved = L[4]
        uc._rt.move_subtree(moved, L[1])
        events = uc.events
        if '_slur_id' not in events.columns:
            return                          # the slur dissolved entirely
        marked = {row['tag'] for _, row in events.iterrows()
                  if row['_slur_id'] == row['_slur_id']}   # not NaN
        assert 'e4' not in marked, (
            'the note that moved under the ex-leaf is inside a slur it was '
            'never part of')

    def test_move_subtree_drops_the_ex_leaf_from_envelope_subsets(self):
        uc = _tagged()
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, L[0:2])
        uc._rt.move_subtree(L[4], L[1])
        leaves = set(uc._rt.leaf_nodes)
        for env_id, desc in uc._control_envelopes.items():
            if desc['leaf_subset'] is None:
                continue
            interior = [n for n in desc['leaf_subset'] if n not in leaves]
            assert interior == [], (
                f'envelope {env_id} still targets {interior}, interior now')


REBUILD_CASES = [
    # Each verb gets the fixture that actually renumbers under it: a flat
    # tree for the positional insert (which allocates one new id and leaves
    # the rest alone), a NESTED tree for the ``_respell`` family (which
    # flattens, so every non-root id is freed and re-allocated). On a flat
    # tree ``_respell`` happens to hand the survivors back ids that read
    # correctly even with the healer off, so a flat fixture cannot tell a
    # healed descriptor from a stale one.
    ('_rt.insert_child', (1, 1, 1, 1),
     lambda uc, L: uc._rt.insert_child(uc._rt.root, 0, proportion=1)),
    ('_rt.insert', ((1, (1, 1)), (1, (1, 1))),
     lambda uc, L: uc._rt.insert(0, '1/8')),
    ('_rt.extract', ((1, (1, 1)), (1, (1, 1))),
     lambda uc, L: uc._rt.extract(0)),
    ('_rt.scale', ((1, (1, 1)), (1, (1, 1))),
     lambda uc, L: uc._rt.scale(0, 3)),
]


class TestAControlEnvelopeFollowsItsNotesThroughARebuild:
    """RELOCATION. ``tests/test_id_keyed_state.py`` pins this for slurs and
    for the Bind memo; the control envelope was the one overlay left
    unpinned against every verb that rebuilds the leaf surface."""

    @pytest.mark.parametrize('name, prolatio, mutate', REBUILD_CASES,
                             ids=[c[0] for c in REBUILD_CASES])
    def test_the_targets_are_the_same_events_after(self, name, prolatio, mutate):
        uc = _tagged(prolatio)
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, [L[1], L[2]])
        before = _tags(uc, uc.resolved_control_envelopes()[0]['target_nodes'])
        assert before == ['e1', 'e2']       # the fixture, not the claim
        mutate(uc, L)
        resolved = uc.resolved_control_envelopes()
        assert resolved, f'{name}: the envelope vanished'
        assert _tags(uc, resolved[0]['target_nodes']) == before, (
            f'{name}: the envelope moved to different events')
        leaves = set(uc._rt.leaf_nodes)
        desc = next(iter(uc._control_envelopes.values()))
        if desc['leaf_subset'] is not None:
            stale = [n for n in desc['leaf_subset'] if n not in leaves]
            assert stale == [], (
                f'{name}: the descriptor still names {stale}, which is not a '
                f'leaf; leaves are {sorted(leaves)}')

    def test_extracting_every_target_removes_the_envelope_and_says_so(self):
        uc = _tagged((1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, L[2:4])
        with pytest.warns(RuntimeWarning, match='Control envelope removed'):
            uc._rt.extract([2, 3])
        assert uc._control_envelopes == {}
        assert uc.resolved_control_envelopes() == []

    def test_an_inserted_note_is_not_swallowed_by_the_envelope_span(self):
        """``apply_envelope`` records a subset only for an explicit
        selection, so a note nobody selected must not join it. This is the
        envelope's half of ``TestRelocationCannotAuthorANonContiguousSlur``.
        """
        uc = _tagged((1, 1, 1, 1))
        L = list(uc._rt.leaf_nodes)
        _envelope_on(uc, L[1:3])
        uc._rt.insert_child(uc._rt.root, 2, proportion=1)   # lands mid-span
        tags = _tags(uc, uc.resolved_control_envelopes()[0]['target_nodes'])
        assert tags == ['e1', 'e2']
