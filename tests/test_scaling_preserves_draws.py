"""Scaling a unit scales the music it already has -- it does not re-roll it.

Ryan's ruling, 2026-08-31: *"we simply scale the ut/uc as it is. No need to
re-eval things."* The three rebuild-from-prolatio recipes -- ``uc * k``
(``TemporalUnit._scaled``), ``modulate_tempo`` and ``modulate_tempus`` --
build a fresh ``CompositionalUnit`` and mirror the source's parameter state
onto it. Every id-keyed overlay was carried across that rebuild EXCEPT
``_bind_memo``, so every stochastic ``Bind`` drew again: measured before the
fix, an amp of 0.3238 came back as 0.1508 through ``uc * Fraction(1, 1)`` --
an identity operation that changed the music.

This is the second half of commit b4b9252, which stopped the same three call
sites pinning UNSET pfields to 0.0. The Bind half was left undone then and is
closed here.

``copy()`` still re-rolls, deliberately. The asymmetry is pinned below
(:class:`TestTheDeliberateAsymmetryWithCopy`) and argued in full in
``CompositionalUnit.copy``'s docstring.
"""

import copy as _copy
import random
from fractions import Fraction

import pytest

from klotho.chronos.temporal_units.algorithms import (
    modulate_tempo, modulate_tempus)
from klotho.chronos.temporal_units.temporal import TemporalUnit as UT
from klotho.thetos import CompositionalUnit as UC, Bind


class _Counter:
    """A Bind callable whose draws are 1.0, 2.0, 3.0 ... -- one per call.

    Distinguishable draws make a re-roll, a rotation and a stale-id
    carry-over three visibly different failures rather than one "the numbers
    moved" blur, and ``n`` makes the CALL itself observable: value equality
    alone would pass a recipe that re-rolled a Bind which happens to be
    deterministic.

    The root resolves alongside the leaves, so a four-leaf unit reads five
    draws. Assertions here are written against ``n`` and against the values
    actually observed, never against an absolute numbering.
    """

    def __init__(self):
        self.n = 0

    def __call__(self, ctx):
        self.n += 1
        return float(self.n)


def _uc(prolatio=(1, 1, 1, 1)):
    return UC(tempus='4/4', prolatio=prolatio, beat='1/4', bpm=120)


def _bound_uc(prolatio=(1, 1, 1, 1), key='amp'):
    """A unit with a counting Bind at the root, its draws already made.

    Returns ``(unit, counter)``.
    """
    uc = _uc(prolatio)
    counter = _Counter()
    uc.set_pfields(uc._rt.root, **{key: Bind(counter)})
    _ = uc.events                      # resolve, so there is a draw to keep
    return uc, counter


def _amps(unit, key='amp'):
    return list(unit.events[key])


SCALINGS = [
    pytest.param(lambda u: u * Fraction(1, 1), id='times-one'),
    pytest.param(lambda u: u * Fraction(2), id='times-two'),
    pytest.param(lambda u: u * Fraction(1, 2), id='times-one-half'),
    pytest.param(lambda u: u * Fraction(5, 7), id='times-five-sevenths'),
    pytest.param(lambda u: modulate_tempo(u, '1/4', 90), id='modulate_tempo'),
    pytest.param(lambda u: modulate_tempus(u, 1, '7/8'), id='modulate_tempus'),
    pytest.param(lambda u: modulate_tempus(u, 3, '4/4'),
                 id='modulate_tempus-new-span'),
]


class TestScalingKeepsTheDrawsItAlreadyMade:
    @pytest.mark.parametrize('scale', SCALINGS)
    def test_every_drawn_value_survives(self, scale):
        uc, _ = _bound_uc()
        before = _amps(uc)
        assert len(set(before)) == 4        # four distinct draws to lose

        assert _amps(scale(uc)) == before

    @pytest.mark.parametrize('scale', SCALINGS)
    def test_the_callable_is_never_invoked_again(self, scale):
        """Not merely "equal values" -- the Bind is not evaluated at all."""
        uc, counter = _bound_uc()
        calls = counter.n
        assert calls == 5                   # root plus four leaves

        _ = scale(uc).events

        assert counter.n == calls

    def test_identity_scaling_is_a_true_no_op_on_a_random_bind(self):
        """The measured defect, in its original shape."""
        random.seed(20260831)
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=Bind(random.random))
        before = _amps(uc)

        assert _amps(uc * Fraction(1, 1)) == before

    def test_the_source_is_untouched(self):
        uc, _ = _bound_uc()
        before = _amps(uc)

        _ = (uc * Fraction(3, 2)).events

        assert _amps(uc) == before

    def test_a_chain_of_scalings_keeps_the_first_draws(self):
        uc, counter = _bound_uc()
        before = _amps(uc)

        chained = modulate_tempo(uc * Fraction(3, 2), '1/8', 200) * Fraction(1, 4)

        assert _amps(chained) == before
        assert counter.n == 5

    def test_a_bind_stored_at_a_leaf_survives_too(self):
        """Preservation is per (node, field), not a root-only special case."""
        uc = _uc()
        leaf = uc._rt.leaf_nodes[2]
        uc.set_pfields(leaf, amp=Bind(_Counter()))
        drawn = uc.get_pfield(leaf, 'amp')

        scaled = uc * Fraction(2)

        assert scaled.get_pfield(scaled._rt.leaf_nodes[2], 'amp') == drawn

    def test_an_mfield_bind_survives_too(self):
        """``_bind_memo`` is keyed by field name, pfield or mfield alike."""
        uc = _uc()
        counter = _Counter()
        uc.set_mfields(uc._rt.root, group=Bind(lambda ctx: f'g{counter(ctx)}'))
        before = [uc.get_mfield(n, 'group') for n in uc._rt.leaf_nodes]
        assert len(set(before)) == 4

        scaled = uc * Fraction(1, 1)

        assert [scaled.get_mfield(n, 'group')
                for n in scaled._rt.leaf_nodes] == before


class TestPreservationFollowsTheShapeAndNotTheRawIds:
    """The rebuild numbers its nodes differently from a mutated source.

    ``_mirror_param_state`` already documents this for pfields: a
    ``subdivide``d 4/4 carries leaves (5, 6, 2, 3, 4) while its rebuild
    numbers them (2, 3, 4, 5, 6), so copying by raw id ROTATES the music.
    The memo is keyed by node id and rides the same correspondence.
    """

    def test_draws_do_not_rotate_after_a_subdivide(self):
        uc, _ = _bound_uc()
        uc.subdivide(uc._rt.leaf_nodes[0], (1, 1))
        before = _amps(uc)
        assert uc._rt.leaf_nodes == (5, 6, 2, 3, 4)      # source ids, shuffled

        scaled = uc * Fraction(1, 1)

        assert scaled._rt.leaf_nodes == (2, 3, 4, 5, 6)  # rebuild ids, in order
        assert _amps(scaled) == before

    def test_draws_do_not_rotate_after_a_removal(self):
        uc, _ = _bound_uc(prolatio=(1, (1, (1, 1)), 1))
        uc.remove_subtree(uc._rt.leaf_nodes[0])
        before = _amps(uc)

        assert _amps(modulate_tempo(uc, '1/4', 60)) == before


class TestTheFreedIdSlotHazard:
    """rustworkx reuses freed node ids, so a dropped entry is not enough.

    A draw belonging to a destroyed node must not travel through the rebuild
    and land on whatever later occupies that id. The counter makes the dead
    node's value unique, so its reappearance anywhere is unambiguous.
    """

    def test_a_dead_nodes_draw_never_reaches_the_rebuild(self):
        uc, _ = _bound_uc()
        dead = uc._rt.leaf_nodes[-1]
        dead_draw = uc.get_pfield(dead, 'amp')

        uc.remove_subtree(dead)                      # frees id 4
        uc.subdivide(uc._rt.leaf_nodes[0], (1, 1))   # id 4 comes back, new node
        assert 4 in uc._rt._rx.node_indices()
        live = _amps(uc)
        assert dead_draw not in live

        scaled = uc * Fraction(1, 1)

        assert _amps(scaled) == live
        assert dead_draw not in _amps(scaled)

    def test_a_memo_entry_with_no_target_is_dropped_not_carried(self):
        """The guard itself, planted by hand because nothing else can reach it.

        Every upstream door already purges a destroyed node's draw
        (``_invalidate_bind_memo`` on removal, ``_remap_bind_memo`` on
        relocation), so a stale entry cannot arise through the public API --
        which is exactly why the guard in ``_copy_bind_memo`` needs its own
        test rather than a scenario. Removing a MIDDLE leaf leaves the source
        holding ids (0, 1, 3, 4) while the rebuild numbers (0, 1, 2, 3), so
        id 2 is dead in the source and alive in the destination: carrying an
        unmapped entry verbatim re-attaches its draw to a node that has
        nothing to do with it. The planted draw carries the root's real Bind,
        so the ``_BindDraw`` identity stamp would NOT catch it.
        """
        from klotho.thetos.composition.compositional import _BindDraw

        uc, _ = _bound_uc()
        uc.remove_subtree(uc._rt.leaf_nodes[1])
        assert 2 not in uc._rt._rx.node_indices()
        before = _amps(uc)
        root_bind = uc._rt._rx[uc._rt.root]['amp']
        uc._bind_memo[(2, 'amp')] = _BindDraw(root_bind, 999.0)

        scaled = uc * Fraction(1, 1)

        assert 2 in scaled._rt._rx.node_indices()
        assert _amps(scaled) == before
        assert 999.0 not in _amps(scaled)

    def test_a_node_that_outlived_a_reused_id_keeps_its_own_draw(self):
        """The complement: the survivors' draws are still theirs.

        A fix that dropped too much would pass the test above by preserving
        nothing at all.
        """
        uc, _ = _bound_uc()
        uc.remove_subtree(uc._rt.leaf_nodes[-1])
        uc.subdivide(uc._rt.leaf_nodes[0], (1, 1))
        before = _amps(uc)
        assert len(set(before)) == len(before)       # every draw distinct

        assert _amps(uc * Fraction(1, 1)) == before


class TestNewlyCreatedLeavesDrawFresh:
    """A leaf with no prior draw has nothing to preserve, and draws its own.

    Scaling never creates one -- ``*`` and both modulations rewrite the
    TEMPUS and carry ``prolationis`` verbatim, so the event count is
    invariant (``uc * 2`` is refused outright as ambiguous; ``ut.repeat(2)``
    is the verb that makes more music). The one shape where the rebuild does
    add a node is the degenerate root-only source, and even there the single
    draw is carried rather than re-rolled.
    """

    @pytest.mark.parametrize('scale', SCALINGS)
    def test_scaling_never_changes_the_event_count(self, scale):
        uc, _ = _bound_uc(prolatio=(1, (1, (1, 1, 1)), 2))

        assert len(scale(uc).events) == len(uc.events)

    def test_a_bare_int_factor_is_still_refused(self):
        """``uc * 2`` cannot mean "twice the music" -- it is not a door here."""
        uc, _ = _bound_uc()
        with pytest.raises(TypeError, match='ambiguous'):
            _ = uc * 2

    def test_a_leaf_created_after_the_scaling_draws_its_own_value(self):
        uc, counter = _bound_uc()
        scaled = uc * Fraction(2)
        carried = _amps(scaled)
        assert counter.n == 5

        scaled.subdivide(scaled._rt.leaf_nodes[0], (1, 1))

        fresh = _amps(scaled)
        assert counter.n == 7                # exactly the two new leaves drew
        assert fresh[:2] == [6.0, 7.0]       # their own values, not inherited
        assert fresh[2:] == carried[1:]      # the survivors, unchanged

    def test_the_degenerate_root_only_source_keeps_its_one_draw(self):
        """``prolationis`` reports ``(1,)`` for a stripped unit, so the
        rebuild has root + one leaf against the source's single node. The
        draw is carried to both ends of that divergence rather than
        re-rolled -- see ``_mirror_param_state``."""
        uc = _uc()
        for leaf in list(uc._rt.leaf_nodes):
            uc.remove_subtree(leaf)
        assert uc._rt.leaf_nodes == (uc._rt.root,)
        counter = _Counter()
        uc.set_pfields(uc._rt.root, amp=Bind(counter))
        drawn = uc.get_pfield(uc._rt.root, 'amp')
        assert counter.n == 1

        scaled = uc * Fraction(3, 2)

        assert scaled._rt.leaf_nodes != (scaled._rt.root,)
        assert _amps(scaled) == [drawn]
        assert scaled.get_pfield(scaled._rt.root, 'amp') == drawn
        assert counter.n == 1


class TestTheDeliberateAsymmetryWithCopy:
    """``copy()`` re-rolls and scaling does not. Both are intended."""

    def test_copy_still_re_rolls(self):
        uc, counter = _bound_uc()
        before = _amps(uc)
        calls = counter.n

        after = _amps(uc.copy())

        assert after != before
        assert counter.n > calls
        assert not set(after) & set(before)

    def test_scaling_by_one_is_the_copy_that_keeps_the_draws(self):
        uc, _ = _bound_uc()

        assert _amps(uc * Fraction(1, 1)) == _amps(uc)

    def test_scaling_then_copying_re_rolls(self):
        uc, _ = _bound_uc()
        before = _amps(uc)

        assert _amps((uc * Fraction(2)).copy()) != before

    def test_a_deep_copy_still_carries_the_draws(self):
        """``__deepcopy__`` is the id-preserving route and is untouched."""
        uc, counter = _bound_uc()
        calls = counter.n

        assert _amps(_copy.deepcopy(uc)) == _amps(uc)
        assert counter.n == calls


class TestNothingElseMoved:
    def test_a_plain_pfield_is_unaffected(self):
        uc = _uc()
        uc.set_pfields(uc._rt.root, amp=0.25)

        assert _amps(uc * Fraction(4, 3)) == [0.25] * 4

    def test_a_selection_reading_bind_still_recomputes(self):
        """``Bind.index`` is never memoized (``reads_selection``), so it is
        resolved against the destination's own structure. Same shape, same
        answer -- defence in depth against the memo swallowing it."""
        uc = _uc()
        uc.set_pfields(uc._rt.root,
                       amp=Bind.index(map=lambda i, n: i / max(n - 1, 1)))
        before = _amps(uc)
        assert before == [0.0, 1 / 3, 2 / 3, 1.0]

        assert _amps(uc * Fraction(1, 1)) == before

    def test_a_rebind_after_scaling_retires_the_carried_draw(self):
        """The ``_BindDraw`` identity stamp still governs the copied memo."""
        uc, _ = _bound_uc()
        scaled = uc * Fraction(1, 1)
        assert _amps(scaled) == _amps(uc)

        scaled._rt.set_pfields(scaled._rt.root, amp=Bind(lambda ctx: 999.0))

        assert _amps(scaled) == [999.0] * 4

    def test_a_plain_temporal_unit_still_scales(self):
        """The non-CompositionalUnit arm has no memo and must not grow one."""
        ut = UT(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=120)

        scaled = ut * Fraction(3, 2)

        assert scaled.tempus == '12/8'
        assert not hasattr(scaled, '_bind_memo')
