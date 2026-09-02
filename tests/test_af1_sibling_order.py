"""AF-1 / audit H1 -- sibling order must not depend on rustworkx's free list.

Child order in this codebase is ascending node id and nothing else:
``GraphCore.successors`` returns ``tuple(sorted(...))``, so the sort IS the
ordering model. Three write paths -- ``RhythmTree.subdivide``'s
``add_children``, ``Tree.add_subtree`` and ``Tree.graft_subtree`` -- used to
add a batch of siblings with sequential raw inserts and trust that ALLOCATION
order equals ascending order.

It does not. **The rustworkx free list is LIFO**, so two nodes removed in
ASCENDING id order are handed back DESCENDING by the next allocation batch::

    g.remove_node(1); g.remove_node(3)
    [g.add_node(...) for _ in range(2)]   # -> [3, 1], not [1, 3]

The proportions were therefore written onto the siblings in the wrong order,
and a tie was migrated onto the first-ALLOCATED child rather than the first
child. Nothing raised: the composer got a plausible tree with permuted beat
proportions and a tie binding the wrong note. Reversing the removal order
(remove 2 then 1) gave the CORRECT answer, so the defect was invisible in any
test that happened to free ids descending.

Every expected duration below is derived by hand from the proportions, and
the arithmetic is written into the test so a reader can check it without
running anything.
"""

from fractions import Fraction

import random

from klotho.chronos import RhythmTree
from klotho.topos.graphs.trees import Tree


# ---------------------------------------------------------------------------
# The premise the whole file rests on: LIFO reuse.
# ---------------------------------------------------------------------------

def test_the_free_list_is_lifo_so_ascending_removals_realloc_descending():
    """The mechanism, pinned directly on the graph.

    If rustworkx ever changes this, the three regressions below stop
    exercising anything and this test says so first.
    """
    rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
    assert sorted(rt.nodes) == [0, 1, 2, 3, 4]
    rt.remove_subtree(1)
    rt.remove_subtree(2)
    assert sorted(rt.nodes) == [0, 3, 4]

    # two raw allocations come back 2 then 1 -- descending
    allocated = [rt._add_node_raw() for _ in range(2)]
    assert allocated == [2, 1], (
        f"expected LIFO reuse [2, 1], got {allocated}"
    )
    for n in allocated:
        rt._remove_node_raw(n)


# ---------------------------------------------------------------------------
# subdivide
# ---------------------------------------------------------------------------

def test_subdivide_after_ascending_removals_keeps_the_requested_order():
    """``subdivide(node, (3, 1))`` must produce 3 then 1, not 1 then 3.

    Derivation.  ``4/4`` spans one whole note, so the tree's total duration
    is ``1``.  After removing two of the four beats the root reads ``(1 1)``:
    two children of proportion 1 out of a sum of 2, so each is ``1/2``.
    Subdividing the first with ``(3, 1)`` splits that ``1/2`` over a sum of
    4::

        first  = 1/2 * 3/4 = 3/8
        second = 1/2 * 1/4 = 1/8

    so the leaf surface is ``(3/8, 1/8, 1/2)``.  Before the fix it came back
    ``(1/8, 3/8, 1/2)`` -- the requested ``(3, 1)`` stored as ``(1, 3)``.
    """
    rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
    rt.remove_subtree(1)          # ascending removal order arms the LIFO
    rt.remove_subtree(2)

    rt.subdivide(3, (3, 1))

    assert rt.durations == (Fraction(3, 8), Fraction(1, 8), Fraction(1, 2))
    subdivided, tail = rt.group.S
    assert tuple(subdivided.S) == (3, 1)
    assert tail == 1


def test_subdivide_answers_the_same_whichever_order_the_ids_were_freed():
    """Removing 2-then-1 already worked; removing 1-then-2 must agree.

    This is the property the defect broke: the answer depended on the order
    of an EARLIER, unrelated edit.
    """
    def build(first_removed, second_removed):
        rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.remove_subtree(first_removed)
        rt.remove_subtree(second_removed)
        rt.subdivide(3, (3, 1))
        return rt.durations

    ascending = build(1, 2)
    descending = build(2, 1)
    assert ascending == descending == (
        Fraction(3, 8), Fraction(1, 8), Fraction(1, 2))


def test_subdivide_of_a_tied_leaf_puts_the_tie_on_the_first_child():
    """The continuation must stay first, or the note re-articulates.

    ``(1, 1, 1, 1.0)`` is four beats whose fourth is TIED to the third.
    Remove the first two beats and the surface is ``beat3, beat4(tied)``.
    Subdividing the tied leaf into ``(1, 1)`` has exactly one lossless
    reading (07_TIES_CHARTER sect1, the OpenMusic resolution): the group's
    FIRST leaf carries "continues my predecessor", and the second leaf is a
    fresh attack.

    So the three leaves must group as ``((leaf0, leaf1), (leaf2,))``.
    Before the fix the tie landed on the first-ALLOCATED child, which the
    LIFO free list had put at rank 1 -- giving ``((leaf0,), (leaf1, leaf2))``,
    i.e. the continuation re-articulated and the fresh attack was swallowed.

    Durations are unaffected here (both proportions are 1), which is exactly
    why this half of the defect was silent even to a duration check.
    """
    rt = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1.0))
    rt.remove_subtree(1)
    rt.remove_subtree(2)

    rt.subdivide(4, (1, 1))

    leaves = rt.leaf_nodes
    assert len(leaves) == 3
    # 1/2 for the surviving whole beat, then 1/2 split evenly in two
    assert rt.durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4))
    assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],))


def test_subdivide_on_a_clean_tree_is_unchanged_ids_included():
    """Control: with no freed ids nothing moves -- not even the node ids.

    Captured from the PRE-FIX implementation, so it pins that the repair
    left the common case byte-identical.  Allocation stays depth-first: the
    group ``(2 (1 1))`` takes id 3 and its two leaves take 4 and 5 BEFORE
    the sibling ``3`` takes id 6.

    Durations by hand: root ``(1 1)`` -> 1/2 each; the first 1/2 split by
    ``((2 (1 1)) 3)``, sum 5, gives ``1/2 * 2/5 = 1/5`` for the group (1/10
    per leaf) and ``1/2 * 3/5 = 3/10`` for its sibling.
    """
    rt = RhythmTree(meas='4/4', subdivisions=(1, 1))
    rt.subdivide(1, ((2, (1, 1)), 3))

    assert sorted(rt.nodes) == [0, 1, 2, 3, 4, 5, 6]
    assert rt.leaf_nodes == (4, 5, 6, 2)
    assert rt.durations == (Fraction(1, 10), Fraction(1, 10),
                            Fraction(3, 10), Fraction(1, 2))


# ---------------------------------------------------------------------------
# graft_subtree
# ---------------------------------------------------------------------------

def test_graft_after_ascending_removals_keeps_the_donor_order():
    """A grafted ``(5, 3, 1)`` must arrive as 5, 3, 1.

    Derivation.  The host ``4/4`` totals ``1``; after two removals the root
    reads ``(1 1)``, so the graft target is worth ``1/2``.  The donor's
    three proportions sum to 9::

        5/9 of 1/2 = 5/18
        3/9 of 1/2 = 1/6
        1/9 of 1/2 = 1/18

    then the untouched sibling at ``1/2``.  Before the fix the first two
    swapped -- ``(1/6, 5/18, 1/18, 1/2)``.
    """
    host = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
    host.remove_subtree(1)
    host.remove_subtree(2)
    donor = RhythmTree(meas='1/4', subdivisions=(5, 3, 1))

    host.graft_subtree(3, donor, mode='replace')

    assert host.durations == (Fraction(5, 18), Fraction(1, 6),
                              Fraction(1, 18), Fraction(1, 2))
    grafted, tail = host.group.S
    assert tuple(grafted.S) == (5, 3, 1)
    assert tail == 1


def test_graft_adopt_after_ascending_removals_keeps_the_donor_order():
    """``mode='adopt'`` runs a different method and needs its own pin.

    Same arithmetic as the ``replace`` case: the target leaf is kept and the
    donor's children hang beneath it, so the ``1/2`` is again split 5:3:1.
    """
    host = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))
    host.remove_subtree(1)
    host.remove_subtree(2)
    donor = RhythmTree(meas='1/4', subdivisions=(5, 3, 1))

    host.graft_subtree(3, donor, mode='adopt')

    assert host.durations == (Fraction(5, 18), Fraction(1, 6),
                              Fraction(1, 18), Fraction(1, 2))


# ---------------------------------------------------------------------------
# add_subtree
# ---------------------------------------------------------------------------

def test_add_subtree_after_ascending_removals_keeps_the_donor_order():
    """Three freed ids are enough to scramble a four-node donor.

    Derivation.  The host ``4/4`` totals ``1``; five beats less three leaves
    two, plus the attached donor root makes three children of proportion 1,
    so each is ``1/3``.  The donor's ``(5, 3, 1)`` sums to 9::

        5/9 of 1/3 = 5/27
        3/9 of 1/3 = 1/9
        1/9 of 1/3 = 1/27

    followed by the two surviving beats at ``1/3`` each.  The donor root
    lands on the smallest freed id, so it sorts FIRST among the root's
    children -- that mid-landing is documented behaviour of ``add_child``
    and is not what this test is about.  Before the fix the first two donor
    proportions swapped: ``(1/9, 5/27, 1/27, 1/3, 1/3)``.
    """
    host = RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1, 1))
    host.remove_subtree(1)
    host.remove_subtree(2)
    host.remove_subtree(3)
    donor = RhythmTree(meas='1/4', subdivisions=(5, 3, 1))

    host.add_subtree(host.root, donor)

    assert host.durations == (Fraction(5, 27), Fraction(1, 9), Fraction(1, 27),
                             Fraction(1, 3), Fraction(1, 3))


def test_plain_tree_add_subtree_keeps_the_donor_label_order():
    """The same repair on a bare ``Tree``, where labels make it readable."""
    host = Tree('H', ('a', 'b', 'c', 'd', 'e'))
    for label in ('a', 'b', 'c'):
        node = next(n for n in host.nodes if host[n].get('label') == label)
        host.remove_subtree(node)
    donor = Tree('D', ('x', 'y', 'z'))

    attached = host.add_subtree(host.root, donor)

    labels = [host[c].get('label') for c in host.successors(attached)]
    assert labels == ['x', 'y', 'z']


def test_plain_tree_graft_subtree_keeps_the_donor_label_order():
    """``graft_subtree`` on a bare ``Tree``, same reasoning."""
    host = Tree('H', ('a', 'b', 'c', 'd'))
    target = None
    for label in ('a', 'b'):
        node = next(n for n in host.nodes if host[n].get('label') == label)
        host.remove_subtree(node)
    target = next(n for n in host.nodes if host[n].get('label') == 'c')
    donor = Tree('D', ('x', 'y', 'z'))

    grafted = host.graft_subtree(target, donor, mode='replace')

    labels = [host[c].get('label') for c in host.successors(grafted)]
    assert labels == ['x', 'y', 'z']


# ---------------------------------------------------------------------------
# The differential property, over randomised shapes.
# ---------------------------------------------------------------------------

def _shape(rt):
    """Structure and proportions, with the node ids factored out."""
    def walk(n):
        kids = rt.successors(n)
        p = rt[n].get('proportion')
        return (p, tuple(walk(c) for c in kids)) if kids else (p,)
    return walk(rt.root)


def test_a_recycled_tree_answers_exactly_as_a_pristine_one():
    """500 random shapes: the dirty tree must equal the clean tree.

    The oracle is DIFFERENTIAL, not hand-computed: the same edit is replayed
    on a pristine tree built directly in the surviving shape, which has no
    freed ids and so cannot hit the LIFO reuse at all.  That clean path is
    itself pinned by hand above
    (``test_subdivide_on_a_clean_tree_is_unchanged_ids_included``), so the
    two together say "the recycled tree is the tree you asked for".

    All four writers are exercised, over nested subdivision specs up to
    three levels deep, with the removals sometimes ascending (which arms the
    LIFO) and sometimes not.  Measured against the pre-fix implementation
    this fails on roughly a QUARTER of the trials -- 999 mismatches in 4000
    -- so the defect was common, not exotic.
    """
    rng = random.Random(20260901)
    mismatches = []

    for _ in range(500):
        width = rng.randint(3, 7)
        rt = RhythmTree(meas='4/4',
                        subdivisions=tuple(rng.randint(1, 5)
                                           for _ in range(width)))

        victims = rng.sample(list(rt.leaf_nodes), rng.randint(0, width - 2))
        if rng.random() < 0.5:
            victims.sort()                     # ascending arms the LIFO
        for v in victims:
            rt.remove_subtree(v)

        survivors = list(rt.leaf_nodes)
        target = rng.choice(survivors)
        rank = survivors.index(target)

        def rand_S(depth=0):
            out = []
            for _ in range(rng.randint(2, 4)):
                if depth < 2 and rng.random() < 0.35:
                    out.append((rng.randint(1, 5), rand_S(depth + 1)))
                else:
                    out.append(rng.randint(1, 5))
            return tuple(out)

        S = rand_S()
        donor_subs = tuple(rng.randint(1, 5) for _ in range(rng.randint(2, 4)))
        op = rng.choice(['subdivide', 'graft_replace', 'graft_adopt',
                         'add_subtree'])

        # the reference: a tree that never had an id freed, in the same shape
        reference = RhythmTree(
            meas='4/4',
            subdivisions=tuple(rt[leaf].get('proportion')
                               for leaf in survivors))
        ref_target = list(reference.leaf_nodes)[rank]

        def apply(tree, node):
            if op == 'subdivide':
                tree.subdivide(node, S)
            elif op == 'add_subtree':
                tree.add_subtree(node, RhythmTree(meas='1/4',
                                                  subdivisions=donor_subs))
            else:
                tree.graft_subtree(
                    node, RhythmTree(meas='1/4', subdivisions=donor_subs),
                    mode='replace' if op == 'graft_replace' else 'adopt')

        apply(rt, target)
        apply(reference, ref_target)

        if _shape(rt) != _shape(reference):
            mismatches.append((op, victims, _shape(rt), _shape(reference)))

    assert not mismatches, (
        f'{len(mismatches)}/500 recycled trees differ from the pristine '
        f'answer; first: {mismatches[0]}')
