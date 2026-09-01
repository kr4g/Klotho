"""LAYER-15 -- a memoized Bind draw must not outlive the Bind that produced it.

``CompositionalUnit.set_pfields`` invalidates ``_bind_memo`` before it writes
(``_invalidate_bind_memo_subtree``). The raw door -- ``uc._rt.set_pfields``,
which is ``ParameterApiMixin.set_pfields`` on the fused tree -- reaches the
parameter layer directly and invalidates nothing, so the unit went on serving
the OLD draw while the tree stored the NEW ``Bind``. Measured before the fix:
``uc.events`` said ``0.9664`` and ``uc.copy().events`` said ``999.0`` for the
same node of the same unit -- two handles disagreeing about the music.

The fix stamps each memo entry with the ``Bind`` it was drawn from, so any
door that replaces the ``Bind`` invalidates the draw by construction. These
tests therefore also cover doors nobody has written an override for
(``graft_subtree``, ``clear_fields``).
"""

import random

import pytest

from klotho.thetos import CompositionalUnit as UC, Bind


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)


class TestTheRawPfieldDoorInvalidatesTheDraw:
    def test_two_handles_on_one_unit_agree_after_a_raw_rebind(self):
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=Bind(random.random))
        first = uc.get_pfield(leaf, 'amp')
        assert isinstance(first, float)

        uc._rt.set_pfields(leaf, amp=Bind(lambda ctx: 999.0))

        assert uc.get_pfield(leaf, 'amp') == 999.0
        assert uc.events['amp'][0] == 999.0
        assert uc.copy().events['amp'][0] == uc.events['amp'][0]

    def test_raw_rebind_at_an_ancestor_invalidates_every_descendant(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=Bind(random.random))
        before = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        assert all(isinstance(v, float) for v in before)

        uc._rt.set_pfields(uc._rt.root, amp=Bind(lambda ctx: 999.0))

        after = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        assert after == [999.0] * len(after)

    def test_raw_mfield_door_invalidates_too(self):
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_mfields(leaf, group=Bind(lambda ctx: 'first'))
        assert uc.get_mfield(leaf, 'group') == 'first'

        uc._rt.set_mfields(leaf, group=Bind(lambda ctx: 'second'))

        assert uc.get_mfield(leaf, 'group') == 'second'

    def test_a_plain_value_written_through_the_raw_door_is_seen(self):
        """Regression pin: a non-``Bind`` overwrite never consulted the memo,
        and must keep not consulting it."""
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=Bind(random.random))
        _ = uc.get_pfield(leaf, 'amp')

        uc._rt.set_pfields(leaf, amp=0.25)

        assert uc.get_pfield(leaf, 'amp') == 0.25


class TestTheDrawIsStillMemoizedWhenTheBindIsUnchanged:
    """The point of the memo: a stochastic ``Bind`` is stable across reads and
    across structural edits. The fix must not turn it into a re-roll."""

    def test_repeated_reads_return_one_draw(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=Bind(random.random))
        first = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        second = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]
        assert first == second
        assert len(set(first)) > 1, 'the draws should differ per node'

    def test_a_structural_edit_keeps_the_surviving_draws(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=Bind(random.random))
        leaves = list(uc._rt.leaf_nodes)
        before = {n: uc.get_pfield(n, 'amp') for n in leaves}

        uc.subdivide(leaves[-1], (1, 1))

        for n in leaves[:-1]:
            assert uc.get_pfield(n, 'amp') == before[n]

    def test_deepcopy_carries_the_draws(self):
        """A deep copy must answer exactly what its source answers.

        ``GraphCore.__deepcopy__`` freshens each node's payload dict but
        shares the objects inside it, so the clone's tree holds the very
        same ``Bind`` instance. ``_BindDraw.__deepcopy__`` shares the stamp
        the same way. Deep-copying the stamp instead -- which is what
        happens with no ``__deepcopy__`` -- makes the identity check fail on
        every clone and silently re-rolls every stochastic draw; that was
        measured, and this test is the pin on it.
        """
        import copy as _copy

        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=Bind(random.random))
        before = [uc.get_pfield(n, 'amp') for n in uc._rt.leaf_nodes]

        clone = _copy.deepcopy(uc)

        assert [clone.get_pfield(n, 'amp') for n in clone._rt.leaf_nodes] == before

    def test_public_setter_still_re_rolls(self):
        """Regression pin on the door that was always correct."""
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=Bind(lambda ctx: 1.0))
        assert uc.get_pfield(leaf, 'amp') == 1.0
        uc.set_pfields(leaf, amp=Bind(lambda ctx: 2.0))
        assert uc.get_pfield(leaf, 'amp') == 2.0


class TestDoorsWithNoOverrideOfTheirOwn:
    """Stamping the memo with its ``Bind`` closes doors no wrapper guards."""

    def test_clear_fields_through_the_raw_tree(self):
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=Bind(lambda ctx: 1.0))
        assert uc.get_pfield(leaf, 'amp') == 1.0

        uc._rt.clear_fields()
        uc._rt.set_pfields(leaf, amp=Bind(lambda ctx: 2.0))

        assert uc.get_pfield(leaf, 'amp') == 2.0

    def test_remove_fields_then_rebind_through_the_raw_tree(self):
        uc = _uc()
        leaf = uc._rt.leaf_nodes[0]
        uc.set_pfields(leaf, amp=Bind(lambda ctx: 1.0))
        assert uc.get_pfield(leaf, 'amp') == 1.0

        uc._rt.remove_fields(leaf, ['amp'])
        uc._rt.set_pfields(leaf, amp=Bind(lambda ctx: 2.0))

        assert uc.get_pfield(leaf, 'amp') == 2.0
