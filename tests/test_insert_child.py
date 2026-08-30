"""The positional insertion primitive: ``Tree.insert_child``.

Child order in a Klotho tree is ascending rustworkx node index and nothing
else -- ``GraphCore.successors`` returns ``tuple(sorted(...))``, so the sort
IS the ordering model. That makes "insert at rank k" mean exactly "shift the
CONTENT of ranks k..n-1 one slot right, then write the new content into the
vacated slot k". These tests pin that reading, its two visible consequences
(node identity follows POSITION, not content) and the one validation gap
positional insertion opens: a tie at the head of the leaf surface has no
predecessor to continue.

Two later classes pin what the primitive does NOT do: it does not read a
node through ``self[...]`` (which broke it on every ``ParameterTree``), and
it does not write anything before it has finished checking its arguments (a
non-int rank used to mutate first and refuse afterwards, leaving the tree's
timings unreadable and saying nothing about it).
"""

from decimal import Decimal
from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.topos.graphs.trees import Tree
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos import ParameterTree as PT


class TestInsertChildOrdering:
    """Rank k means rank k in ``successors`` order, at every position."""

    def test_interior_insert_lands_at_the_requested_rank(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 1, proportion=7)
        assert rt.group.S == (2, 7, 1, 2)

    def test_head_insert(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 0, proportion=7)
        assert rt.group.S == (7, 2, 1, 2)

    def test_tail_index_appends(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 3, proportion=7)
        assert rt.group.S == (2, 1, 2, 7)

    def test_negative_index_counts_from_the_end(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, -1, proportion=7)
        assert rt.group.S == (2, 1, 7, 2)

    @pytest.mark.parametrize('index', [4, -5, 99])
    def test_out_of_range_raises(self, index):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(IndexError):
            rt.insert_child(rt.root, index, proportion=7)

    def test_unknown_parent_raises(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.insert_child(99, 0, proportion=7)

    def test_insert_onto_a_leaf_makes_it_a_parent(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        leaf = rt.leaf_nodes[1]
        rt.insert_child(leaf, 0, proportion=3)
        assert rt.group.S == (2, (1, (3,)), 2)


class TestInsertChildShiftsWholeSubtrees:
    """The moving content is (payload, child list) -- a shifted sibling takes
    its entire subtree with it."""

    def test_a_whole_group_shifts_right(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        rt.insert_child(rt.root, 1, proportion=5)
        assert rt.group.S == (1, 5, (2, (1, 1)), 3)

    def test_inserting_before_a_group_keeps_its_durations(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        rt.insert_child(rt.root, 0, proportion=6)
        assert rt.group.S == (6, 1, (2, (1, 1)), 3)
        # 6 + 1 + 2 + 3 = 12 units of the bar; the group's two leaves split 2.
        assert rt.durations == (
            Fraction(1, 2), Fraction(1, 12),
            Fraction(1, 12), Fraction(1, 12),
            Fraction(1, 4),
        )

    def test_insert_into_an_interior_parent(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        group = rt.successors(rt.root)[1]
        rt.insert_child(group, 1, proportion=4)
        assert rt.group.S == (1, (2, (1, 4, 1)), 3)


class TestInsertChildIdentityFollowsPosition:
    """Slot k keeps its id and receives new content, so an external handle to
    a shifted sibling now denotes a different note. Inherent to rank == index;
    documented, not engineered around."""

    def test_the_returned_id_is_the_slot_not_the_new_node(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        before = list(rt.successors(rt.root))
        new_id = rt.insert_child(rt.root, 0, proportion=7)
        assert new_id == before[0]
        assert rt[new_id]['proportion'] == 7

    def test_a_stale_handle_now_names_the_shifted_neighbour(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        handle = rt.successors(rt.root)[1]   # the leaf sounding "1"
        assert rt[handle]['proportion'] == 1
        rt.insert_child(rt.root, 0, proportion=7)
        # content moved right into the NEXT slot; the id kept its position
        assert rt[handle]['proportion'] == 2

    def test_successors_stay_sorted(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        rt.insert_child(rt.root, 1, proportion=5)
        for n in rt.nodes:
            succ = list(rt.successors(n))
            assert succ == sorted(succ)


class TestInsertChildRecomputesTimings:
    def test_durations_and_onsets_are_fresh(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 1, proportion=5)
        assert rt.group.S == (2, 5, 1, 2)
        assert rt.durations == (Fraction(1, 5), Fraction(1, 2),
                                Fraction(1, 10), Fraction(1, 5))
        assert rt.onsets == (Fraction(0), Fraction(1, 5),
                             Fraction(7, 10), Fraction(4, 5))

    def test_a_rest_can_be_inserted(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 1, proportion=-3)
        assert rt.group.S == (2, -3, 1, 2)
        assert rt.durations[1] < 0

    def test_a_composed_operand_needs_no_second_primitive(self):
        """insert_child then subdivide composes -- there is no insert_subtree."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        new_id = rt.insert_child(rt.root, 1, proportion=3)
        rt.subdivide(new_id, (1, 2))
        assert rt.group.S == (2, (3, (1, 2)), 1, 2)

    def test_default_proportion_is_one(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, 0)
        assert rt.group.S == (1, 2, 1, 2)


class TestInsertChildRefusesADanglingLeadingTie:
    """A tie continues a sound. Inserted at the head of the leaf surface there
    is nothing to continue, and the flag was previously accepted in silence and
    then ignored. ``insert_child`` knows the index, so it is the only surface
    that can refuse this."""

    def test_tie_at_the_head_of_the_tree_raises(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError, match='continues'):
            rt.insert_child(rt.root, 0, tied=True, proportion=3)

    def test_tie_at_the_head_of_the_leftmost_group_raises(self):
        rt = RT(meas='4/4', subdivisions=((2, (1, 1)), 1, 2))
        group = rt.successors(rt.root)[0]
        with pytest.raises(ValueError, match='continues'):
            rt.insert_child(group, 0, tied=True, proportion=3)

    def test_tie_at_the_head_of_a_LATER_group_is_legal(self):
        """Rank 0 is not the test -- having no predecessor is. A group that
        is not leftmost has a leaf before it, so the tie binds."""
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 2))
        group = rt.successors(rt.root)[1]
        rt.insert_child(group, 0, tied=True, proportion=3)
        leaves = rt.leaf_nodes
        assert rt[leaves[1]]['tied'] is True
        assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],),
                                 (leaves[3],), (leaves[4],))

    def test_a_tie_at_rank_k_rebinds_to_the_inserted_note(self):
        rt = RT(meas='2/2', subdivisions=(2, 1.0, 2))
        assert rt.tie_groups == ((1, 2), (3,))
        rt.insert_child(rt.root, 1, proportion=3)
        assert rt.group.S == (2, 3, 1.0, 2)
        assert rt.tie_groups == ((1,), (2, 3), (4,))


class TestInsertChildOnAPlainTree:
    def test_base_tree_labels_shift(self):
        t = Tree('r', ('a', 'b', 'c'))
        t.insert_child(t.root, 1, label='x')
        assert t.group.S == ('a', 'x', 'b', 'c')


class TestInsertChildOnAFusedCompositionalUnit:
    """The UC is ONE fused tree; pfields ride with the content."""

    def test_pfields_shift_with_their_events(self):
        uc = UC(span=1, tempus='2/2', prolatio=(2, 1, 2))
        for i, leaf in enumerate(uc._rt.leaf_nodes):
            uc.set_pfields(leaf, freq=200 + i)
        uc._rt.insert_child(uc._rt.root, 1)
        assert len(uc.events) == 4
        assert [uc.pt[n].get('freq') for n in uc._rt.leaf_nodes] == \
               [200, None, 201, 202]


class TestAddChildAppendIsNotGuaranteedAfterADeletion:
    """PRE-EXISTING, not caused by positional insertion: rustworkx reuses freed
    node indices, so ``add_child`` lands wherever the free list puts it. Pinned
    so the docstring stays honest -- ``insert_child`` is the way to say where."""

    def test_add_child_lands_in_the_freed_slot(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        rt.remove_subtree(4)
        assert rt.group.S == (1, (2, (1,)), 3)
        rt.add_child(rt.root, proportion=9)
        assert rt.group.S == (1, (2, (1,)), 9, 3)

    def test_insert_child_says_where_instead(self):
        rt = RT(meas='4/4', subdivisions=(1, (2, (1, 1)), 3))
        rt.remove_subtree(4)
        rt.insert_child(rt.root, 3, proportion=9)
        assert rt.group.S == (1, (2, (1,)), 3, 9)


class TestInsertChildIntoATiedLeafMigratesTheTie:
    """Inserting into a tied LEAF turns it interior, and ``tied`` has no
    meaning there -- ``tie_groups`` reads the leaf surface, so a flag left on
    the new parent is invisible and the tie is silently destroyed, adding an
    attack that was not there. ``subdivide`` already resolved this
    (07_TIES_CHARTER.md sect1, the OpenMusic resolution): the tie moves to the
    group's first leaf. ``insert_child`` is the same event and takes the same
    answer.

    Both verbs call ONE helper, ``RhythmTree._migrate_tie_to_first_child``, and
    both inherit ``_evaluate``'s tied-rest rule. So the two ``agree`` tests
    below cannot see a defect that lives in either: sabotage the helper and
    they stay green together. Each of them therefore also asserts the absolute
    post-condition, and that is the half that fails."""

    def test_the_tie_survives_and_moves_onto_the_inserted_leaf(self):
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        tied = rt.leaf_nodes[1]
        assert rt.tie_groups == ((1, 2), (3,))
        new = rt.insert_child(tied, 0, proportion=1)
        assert rt[new]['tied'] is True
        assert rt.tie_groups == ((1, new), (3,))

    def test_the_new_interior_node_sheds_the_tie(self):
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        tied = rt.leaf_nodes[1]
        rt.insert_child(tied, 0, proportion=1)
        assert rt[tied]['tied'] is False
        assert isinstance(rt[tied]['proportion'], int)
        assert rt.group.S == (1, (1, (1.0,)), 1)

    def test_the_attack_count_is_unchanged(self):
        """The whole point: an inserted subdivision must not re-articulate a
        note that was tied over."""
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        before = len(rt.tie_groups)
        rt.insert_child(rt.leaf_nodes[1], 0, proportion=1)
        assert len(rt.tie_groups) == before

    def test_insert_child_and_subdivide_agree_on_the_tie_structure(self):
        """Two inserts build what one ``subdivide`` builds -- so they must
        leave the same tie, on the same leaf. (``subdivide`` declines a
        one-part S, which is why this compares a two-part group.)"""
        inserted = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        target = inserted.leaf_nodes[1]
        inserted.insert_child(target, 0, proportion=1)
        inserted.insert_child(target, 1, proportion=1)
        divided = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        divided.subdivide(divided.leaf_nodes[1], (1, 1))
        assert inserted.group.S == divided.group.S
        assert inserted.tie_groups == divided.tie_groups
        assert inserted[target]['tied'] is False
        assert [inserted[n].get('tied') for n in inserted.leaf_nodes] == \
               [divided[n].get('tied') for n in divided.leaf_nodes]
        # The absolute half. Agreement is blind to the shared helper, so say
        # what the shape IS: four leaves, three tie groups, and the tie binds
        # the second leaf back to the first. ``group.S`` alone would not do
        # it -- ``1.0 == 1``, so a tuple comparison cannot see a tie at all.
        assert inserted.group.S == (1, (1, (1.0, 1)), 1)
        assert len(inserted.tie_groups) == 3
        assert inserted.tie_groups[0] == inserted.leaf_nodes[:2]
        assert [inserted[n].get('tied') for n in inserted.leaf_nodes] == \
               [False, True, False, False]

    def test_they_agree_when_the_new_first_leaf_is_a_REST(self):
        """A tie cannot land on a rest (charter sect1), so it dies. Both verbs
        must kill it the same way rather than one leaving a tied rest."""
        inserted = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        target = inserted.leaf_nodes[1]
        inserted.insert_child(target, 0, proportion=-1)
        inserted.insert_child(target, 1, proportion=1)
        divided = RT(meas='4/4', subdivisions=(1, 1.0, 1))
        divided.subdivide(divided.leaf_nodes[1], (-1, 1))
        assert inserted.group.S == divided.group.S
        assert inserted.tie_groups == divided.tie_groups
        # the tie is gone from BOTH ends, not merely invisible: a flag left on
        # the new interior node still reaches `Group` as a float D.
        assert inserted[target]['tied'] is False
        assert isinstance(inserted[target]['proportion'], int)
        assert [inserted[n].get('tied') for n in inserted.leaf_nodes] == \
               [divided[n].get('tied') for n in divided.leaf_nodes]
        # The absolute half. Both verbs inherit `_evaluate`'s tied-rest rule,
        # so they would agree on a tied rest too; say instead that no tie is
        # left anywhere -- four leaves, four single-leaf groups, no flag.
        # The flag list is the assertion that bites: `tie_groups` already
        # refuses to open a group on a rest, so it stays four groups even
        # when the flag survives, and `group.S` cannot see a tie (1.0 == 1).
        assert inserted.group.S == (1, (1, (-1, 1)), 1)
        assert len(inserted.tie_groups) == 4
        assert all(len(g) == 1 for g in inserted.tie_groups)
        assert [inserted[n].get('tied') for n in inserted.leaf_nodes] == \
               [False, False, False, False]

    def test_an_untied_leaf_is_untouched(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        new = rt.insert_child(rt.leaf_nodes[1], 0, proportion=1)
        assert rt[new].get('tied') is False
        assert rt.group.S == (1, (1, (1,)), 1)

    def test_the_tie_reaches_the_event_surface(self):
        """End to end: the defect was audible -- two attacks became three,
        with nothing warning about it."""
        uc = UC(span=1, tempus='4/4', prolatio=(1, 1.0, 1))
        assert len(uc.events) == 2
        uc._rt.insert_child(uc._rt.leaf_nodes[1], 0, proportion=1)
        assert len(uc.events) == 2


class TestInsertChildOnAStandaloneParameterTree:
    """LAYER-6. ``Tree.insert_child`` captured sibling content with
    ``dict(self[s])``, and ``ParameterTree.__getitem__`` does not return the
    payload -- it returns a ``ParameterNode`` proxy that accepts string keys
    only. ``dict()`` on a proxy with no ``keys()`` falls back to the sequence
    protocol and asks for key ``0``, so the proxy raised ``TypeError("Key must
    be a string")`` and the whole positional-insertion primitive was unusable
    on this MRO -- the one Tree mutator that was.

    ``CompositionalUnit`` was never affected: ``CompositionalTree`` does not
    override ``__getitem__``. The blast radius is exactly the standalone
    ``ParameterTree`` that ``klotho.thetos`` exports.

    Content is read through ``self.nodes[s]`` now, which is the raw payload
    view and is what the neighbouring ``add_subtree`` already used.
    """

    def test_insert_child_runs_at_all(self):
        pt = PT(1, (1, 1, 1))
        new_id = pt.insert_child(pt.root, 1)
        assert len(pt.successors(pt.root)) == 4
        assert new_id == pt.successors(pt.root)[1]

    def test_pfields_shift_with_their_slots(self):
        """Identity follows POSITION here too: the content of ranks 1.. moves
        one slot right, so the values must land in the new order."""
        pt = PT(1, (1, 1, 1))
        for i, n in enumerate(pt.successors(pt.root)):
            pt.set_pfields(n, freq=200 + i)
        pt.insert_child(pt.root, 1)
        assert [pt.get_pfield(n, 'freq') for n in pt.successors(pt.root)] == \
               [200, None, 201, 202]

    def test_instrument_bindings_ride_with_the_content(self):
        """An instrument is id-keyed state held OUTSIDE the graph, so it only
        moves because ``_notify_nodes_relocated`` moves it."""
        pt = PT(1, (1, 1, 1))
        second = pt.successors(pt.root)[1]
        pt.set_instrument(second, 'flute')
        pt.insert_child(pt.root, 0)
        slots = pt.successors(pt.root)
        assert pt.get_instrument(slots[2]) == 'flute'
        assert pt.get_instrument(slots[1]) is None

    def test_the_head_insert_leaves_the_head_content_intact(self):
        pt = PT(1, (1, 1, 1))
        for i, n in enumerate(pt.successors(pt.root)):
            pt.set_pfields(n, freq=200 + i)
        pt.insert_child(pt.root, 0)
        assert [pt.get_pfield(n, 'freq') for n in pt.successors(pt.root)] == \
               [None, 200, 201, 202]

    def test_a_nested_parameter_tree_shifts_whole_subtrees(self):
        pt = PT(1, (1, (2, (1, 1)), 1))
        group = pt.successors(pt.root)[1]
        for i, leaf in enumerate(pt.successors(group)):
            pt.set_pfields(leaf, freq=300 + i)
        pt.insert_child(pt.root, 0)
        moved = pt.successors(pt.root)[2]
        assert [pt.get_pfield(n, 'freq') for n in pt.successors(moved)] == \
               [300, 301]


class TestInsertChildRefusesANonIntegerIndexWITHOUTWriting:
    """LAYER-7. The refusal used to come AFTER the write. ``index < 0`` and
    ``0 <= index <= n`` are both legal float comparisons, so a float sailed
    through both guards, ``_add_child_raw`` mutated, and only then did
    ``contents[:index]`` raise ``TypeError: slice indices must be integers``.
    ``_post_mutation`` never ran, so the layer pipeline never recomputed and
    ``rt.durations`` raised ``KeyError: 'metric_duration'`` from then on --
    while ``rt.group.S`` still reported a plausible ``(1, 1, 1, 7)``. A
    refused call announced nothing and left the tree unreadable.

    So these tests do not merely assert that it raises. They assert the tree
    is IDENTICAL afterwards -- payloads, edges, group and timings -- because
    "it raised" was already true when the tree was being corrupted.
    """

    @staticmethod
    def _snapshot(rt):
        return (
            {n: dict(rt.nodes[n]) for n in rt.nodes},
            sorted(rt.edges),
            rt.group.S,
            rt.durations,
            rt.onsets,
        )

    # 1.0, Fraction(1, 1) and Decimal(1) all survived both comparisons and
    # mutated; '1' and None died at the `<` with a leaked comparison message.
    # One shaped refusal now covers all five.
    @pytest.mark.parametrize('index', [1.0, 0.5, Fraction(1, 1), Decimal(1),
                                       '1', None, [1]])
    def test_the_refusal_is_shaped_and_atomic(self, index):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        before = self._snapshot(rt)
        with pytest.raises(TypeError, match='index must be an integer'):
            rt.insert_child(rt.root, index, proportion=7)
        assert rt.group.S == (1, 1, 1)
        assert rt.durations == (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3))
        assert self._snapshot(rt) == before

    def test_the_write_never_happens_WHATEVER_the_error_shape(self):
        """The atomicity half said without reference to the message, because
        the message is the other half and would otherwise hide this one. The
        old call DID raise -- it raised AFTER mutating -- so ``pytest.raises``
        alone proves nothing here. Catch anything, then look at the tree."""
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        payloads = {n: dict(rt.nodes[n]) for n in rt.nodes}
        with pytest.raises(Exception):
            rt.insert_child(rt.root, 1.0, proportion=7)
        assert {n: dict(rt.nodes[n]) for n in rt.nodes} == payloads
        assert rt.group.S == (1, 1, 1)
        assert rt.durations == (Fraction(1, 3), Fraction(1, 3), Fraction(1, 3))

    def test_the_message_names_the_offending_type(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(TypeError) as exc:
            rt.insert_child(rt.root, Fraction(1, 1), proportion=7)
        assert 'Fraction' in str(exc.value)
        assert 'list.insert' in str(exc.value)

    def test_the_tie_path_refuses_the_same_way(self):
        """``RhythmTree.insert_child`` reads ``index`` itself before it
        delegates -- to decide whether a requested tie sits at rank 0 -- so
        the guard has to be reached from there too."""
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        before = self._snapshot(rt)
        with pytest.raises(TypeError, match='index must be an integer'):
            rt.insert_child(rt.root, 1.0, tied=True, proportion=3)
        assert self._snapshot(rt) == before

    def test_a_string_index_in_the_tie_path_refuses_the_same_way(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(TypeError, match='index must be an integer'):
            rt.insert_child(rt.root, '1', tied=True, proportion=3)

    def test_a_parameter_tree_refuses_it_too(self):
        pt = PT(1, (1, 1, 1))
        payloads = {n: dict(pt.nodes[n]) for n in pt.nodes}
        with pytest.raises(TypeError, match='index must be an integer'):
            pt.insert_child(pt.root, 1.0)
        assert {n: dict(pt.nodes[n]) for n in pt.nodes} == payloads
        assert len(pt.successors(pt.root)) == 3

    def test_bool_is_still_an_index(self):
        """Guard on the fix, not on the defect: ``True`` IS an int and worked
        before, so the new check must not start refusing it. Green before the
        fix and after."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert_child(rt.root, True, proportion=7)
        assert rt.group.S == (2, 7, 1, 2)

    @pytest.mark.parametrize('index', [4, -5])
    def test_an_out_of_range_refusal_is_atomic_too(self, index):
        """Also a guard, not a defect: the range check already ran before the
        write. Pinned so reordering the new guard cannot move it after."""
        rt = RT(meas='4/4', subdivisions=(1, 1, 1))
        before = self._snapshot(rt)
        with pytest.raises(IndexError):
            rt.insert_child(rt.root, index, proportion=7)
        assert self._snapshot(rt) == before
