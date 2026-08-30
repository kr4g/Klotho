"""The positional insertion primitive: ``Tree.insert_child``.

Child order in a Klotho tree is ascending rustworkx node index and nothing
else -- ``GraphCore.successors`` returns ``tuple(sorted(...))``, so the sort
IS the ordering model. That makes "insert at rank k" mean exactly "shift the
CONTENT of ranks k..n-1 one slot right, then write the new content into the
vacated slot k". These tests pin that reading, its two visible consequences
(node identity follows POSITION, not content) and the one validation gap
positional insertion opens: a tie at the head of the leaf surface has no
predecessor to continue.
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.topos.graphs.trees import Tree
from klotho.thetos import CompositionalUnit as UC


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
