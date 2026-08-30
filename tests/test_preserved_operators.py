"""Haddad's Tempus-PRESERVING operator family: insert, extract, scale.

The axis (TEMPO-1/R13-A). Haddad's notation is systematic -- a BOX means the
Tempus FOLLOWS the operation, a CIRCLE means the Tempus is PRESERVED:

    add     augmentation  (+ in a box)   insertion             (+ in a circle)
    remove  diminution    (- in a box)   extraction            (- in a circle)
    scale   dilatation    (x in a box)   expansion/compression (x in a circle)

He states the axis outright on p. 128:

    « Les prolationis qui en résultent sont identiques. C'est le Tempus qui
    diffère. Dans le cas de la « prolation » stricte, le Tempus est
    identique. Dans le deuxième cas, le Tempus est la somme des prolationis
    une fois transformés. »

    "The resulting prolationis are identical. It is the Tempus that differs.
    In the case of strict 'prolation', the Tempus is identical. In the second
    case, the Tempus is the sum of the prolationis once transformed."

He never writes "Tempus-preserving" or "Tempus-following"; his own terms are
*« prolationnelle stricte »* ("strictly prolational") for the circle family
and *« relative »* ("relative") for the box family. The English pair is
Klotho's coinage.

This file covers the CIRCLE family only. The box family (augmentation,
diminution, dilatation) builds a new tree with a recomputed Tempus and lives
elsewhere.

Every operator is decompose -> operate -> concatenate (sect4.5.2, p. 124):

    « Ces opérations utilisent l'ajout équivalent à l'addition, le retrait à
    la soustraction, et la substitution (sous forme de multiplication) après
    décomposition de l'Unité temporelle composée suivi de la concaténation de
    l'ensemble des prolationis. »

    "These operations use addition for adding, subtraction for removal, and
    substitution (in the form of multiplication) -- after decomposition of the
    composite Temporal Unit, followed by concatenation of the whole set of
    prolationis."
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree as RT
from klotho.chronos.rhythm_trees.algorithms import flatten


# ----------------------------------------------------------------------
# insertion -- (+ in a circle)
# ----------------------------------------------------------------------
class TestInsertionFigure460:
    """fig. 4.60. Thesis typo: the figure prints the source subscript as
    ``(2 1 1)``. The correct input is ``(2 1 2)``, proven three ways -- the
    prose says *« trois prolationis de (2 1 2) »* ("three prolationis of
    (2 1 2)"), the engraving is a 5:4 tuplet (5 = 2+1+2), and only ``(2 1 2)``
    yields ``(4 2 3 4)``. The same broken macro repeats from fig. 4.58."""

    def test_the_published_result(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert rt.group.S == (4, 2, 3, 4)

    def test_the_tempus_spelling_survives_verbatim(self):
        """The flatten is an INTERNAL step, never part of the result. Carrying
        the flattened Tempus through gives identical real durations, so no
        arithmetic assertion catches it -- only this one does."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert str(rt.meas) == '2/2'
        assert rt.span == 1

    def test_returns_self_for_chaining(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.insert(2, Fraction(3, 10)) is rt


class TestInsertionIndexing:
    """0-based indices into the DECOMPOSED sequence, insert BEFORE index k
    (p. 125): *« …et position la position de l'ajout par rapport à l'ensemble
    de la séquence décomposée (0 étant la position de tête de séquence). »*
    -- "…and position is the position of the addition relative to the whole
    decomposed sequence (0 being the head-of-sequence position)." """

    def test_head_position_is_zero(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(0, Fraction(1, 5))
        assert rt.group.S == (1, 2, 1, 2)

    def test_tail_position_is_the_length(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(3, Fraction(1, 5))
        assert rt.group.S == (2, 1, 2, 1)

    def test_negative_index_counts_from_the_end(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(-1, Fraction(1, 5))
        assert rt.group.S == (2, 1, 1, 2)

    @pytest.mark.parametrize('index', [4, -5])
    def test_out_of_range_raises(self, index):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(IndexError):
            rt.insert(index, Fraction(1, 5))

    def test_indices_refer_to_the_ORIGINAL_sequence(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert([0, 3], [Fraction(1, 5), Fraction(1, 5)])
        assert rt.group.S == (1, 2, 1, 2, 1)

    def test_two_insertions_at_one_index_keep_argument_order(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert([1, 1], [Fraction(1, 5), Fraction(2, 5)])
        assert rt.group.S == (2, 1, 2, 1, 2)

    def test_mismatched_lengths_raise(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.insert([0, 1], [Fraction(1, 5)])


class TestInsertionSemantics:
    def test_the_bar_does_not_grow(self):
        """Strictly prolational: the inserted value only fixes the new note's
        RELATIVE weight. Everything compresses; the Tempus is untouched."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, Fraction(3, 10))
        assert sum(abs(d) for d in rt.durations) == Fraction(1)
        assert rt.durations == (Fraction(4, 13), Fraction(2, 13),
                                Fraction(3, 13), Fraction(4, 13))

    def test_a_negative_duration_inserts_a_rest(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(1, Fraction(-1, 5))
        assert rt.group.S == (2, -1, 1, 2)
        assert rt.durations[1] < 0

    def test_zero_is_refused(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.insert(1, 0)

    def test_a_nested_operand_flattens(self):
        """decompose -> operate -> concatenate: the result is one level, by
        construction. Nesting is not preserved by the circle family."""
        rt = RT(meas='1/1', subdivisions=((2, (2, 1)), 1, 2, 1))
        assert flatten(rt).group.S == (4, 2, 3, 6, 3)
        rt.insert(0, Fraction(1, 18))
        assert rt.group.S == (1, 4, 2, 3, 6, 3)

    def test_a_tie_group_decomposes_as_one_event(self):
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1, 1))
        assert rt.tie_groups == ((1, 2), (3,), (4,))
        rt.insert(0, Fraction(1, 4))
        assert rt.group.S == (1, 2, 1, 1)

    def test_a_string_ratio_is_accepted(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.insert(2, '3/10')
        assert rt.group.S == (4, 2, 3, 4)


# ----------------------------------------------------------------------
# extraction -- (- in a circle)
# ----------------------------------------------------------------------
class TestExtraction:
    """``prune`` was already extraction for LEAVES; ``extract`` is the named
    verb and delegates to ``remove_subtree``, which is correct in general."""

    def test_extracting_a_leaf_holds_the_tempus(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.extract(2)
        assert str(rt.meas) == '2/2'
        assert rt.group.S == (2, 2)
        assert sum(abs(d) for d in rt.durations) == Fraction(1)

    def test_survivors_dilate_to_fill_the_bar(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.durations == (Fraction(2, 5), Fraction(1, 5), Fraction(2, 5))
        rt.extract(2)
        assert rt.durations == (Fraction(1, 2), Fraction(1, 2))

    def test_extracting_a_whole_group(self):
        rt = RT(meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
        group = rt.successors(rt.root)[1]
        rt.extract(group)
        assert rt.group.S == (1, 3)

    def test_several_nodes_at_once(self):
        rt = RT(meas='4/4', subdivisions=(1, 2, 3, 4))
        succ = rt.successors(rt.root)
        rt.extract([succ[0], succ[2]])
        assert rt.group.S == (2, 4)

    def test_extracting_the_root_raises(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(ValueError):
            rt.extract(rt.root)

    def test_returns_self_for_chaining(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        assert rt.extract(2) is rt

    def test_prune_and_extract_agree_on_a_leaf(self):
        a = RT(meas='2/2', subdivisions=(2, 1, 2)).prune(2)
        b = RT(meas='2/2', subdivisions=(2, 1, 2)).extract(2)
        assert a.group == b.group
        assert a.durations == b.durations

    def test_prune_promotes_and_changes_durations_on_an_INTERIOR_node(self):
        """The documented divergence: on an interior node ``prune`` promotes
        the children one level, which is duration-preserving only when
        ``D == sum(S)``. ``extract``/``remove_subtree`` is the general verb."""
        rt = RT(meas='4/4', subdivisions=(1, (5, (1, 1)), 3))
        assert rt.durations == (Fraction(1, 9), Fraction(5, 18),
                                Fraction(5, 18), Fraction(1, 3))
        rt.prune(rt.successors(rt.root)[1])
        assert rt.group.S == (1, 1, 1, 3)
        assert rt.durations == (Fraction(1, 6), Fraction(1, 6),
                                Fraction(1, 6), Fraction(1, 2))


# ----------------------------------------------------------------------
# expansion / compression -- (x in a circle)
# ----------------------------------------------------------------------
class TestScaleFigure465:
    """fig. 4.65 -- expansion of the third prolatio by 3."""

    def test_the_published_result(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 3)
        assert rt.group.S == (4, 2, 9, 6, 3)
        assert str(rt.meas) == '18/18'


class TestScaleFigure468:
    """fig. 4.68, CORRECTED. Never use figs. 4.68/4.69's printed prolationis:
    both reprint the expansion result ``(4 2 9 6 3)``. Fig. 4.69's Tempus
    ``16/27`` is correct and forces the true answer.

    **Spelling divergence, deliberate.** Haddad prints
    ``54/54 (12 6 3 2 9)``; Klotho gives ``18/18 (12 6 3 2 9)``. Same Tempus
    VALUE, same durations, same proportions -- counted in eighteenths rather
    than fifty-fourths, because the preserved family never moves the
    authored spelling. Three reasons:

    1. Re-spelling is never forced. Timing is ``meas * span`` distributed
       over integer proportions, so the denominator is a display choice
       (pinned in ``test_a_finer_grid_needs_no_finer_denominator``).
    2. The rest of this operator work already asserts on DURATION, not on
       printed spelling, because his spellings are demonstrably not
       rule-generated: the same duration is ``3/6`` in one sequence and
       ``9/18`` in another, and ``14/18`` is reduced to ``7/9`` while
       ``15/18`` is left alone. ``test_following_operators.py`` pins his
       reduced spellings as values for the same reason.
    3. The rule that produced ``54/54`` cannot tell a GRID from a METER.
       ``18/18`` is a normalized ratio nobody engraves; ``3/4`` is a meter,
       and it has the same arithmetic shape -- so the rule rewrote ``3/4``
       to ``6/8``. See ``TestTheAuthoredSpellingIsNeverMoved``.

    Flagged to Ryan as a reversible ruling: his printed spelling can return
    as an opt-in argument."""

    def test_the_corrected_result(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.group.S == (12, 6, 3, 2, 9)

    def test_the_tempus_VALUE_matches_the_figure_and_the_spelling_stands(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.meas.to_fraction() == Fraction(1)          # his 54/54
        assert str(rt.meas) == '18/18'                       # as authored

    def test_the_durations_are_the_figures_durations(self):
        """The assertion that would catch a real error, since the spelling
        no longer can: proportions on a Tempus of value 1."""
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.durations == (Fraction(12, 32), Fraction(6, 32),
                                Fraction(3, 32), Fraction(2, 32),
                                Fraction(9, 32))


class TestScaleSemantics:
    def test_an_authored_tempus_is_left_alone(self):
        """``2/2`` over a five-part prolatio was never the grid, so it says
        something about the bar and is kept verbatim."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        rt.scale(1, 2)
        assert str(rt.meas) == '2/2'
        assert rt.group.S == (2, 2, 2)

    def test_the_tempus_VALUE_never_changes(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        before = rt.meas.to_fraction() * rt.span
        rt.scale([2, 3], [Fraction(1, 3), Fraction(1, 9)])
        assert rt.meas.to_fraction() * rt.span == before

    def test_the_bar_stays_full(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 3)
        assert sum(abs(d) for d in rt.durations) == Fraction(1)

    def test_expansion_makes_the_target_relatively_longer(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        before = rt.durations
        rt.scale(2, 3)
        after = rt.durations
        assert after[2] / after[0] == 3 * (before[2] / before[0])

    def test_a_rest_keeps_its_sign(self):
        rt = RT(meas='4/4', subdivisions=(1, -1, 2))
        rt.scale(1, 2)
        assert rt.group.S == (1, -2, 2)

    def test_negative_ratio_is_refused(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 2))
        with pytest.raises(ValueError):
            rt.scale(1, -2)

    def test_zero_ratio_is_refused(self):
        rt = RT(meas='4/4', subdivisions=(1, 1, 2))
        with pytest.raises(ValueError):
            rt.scale(1, 0)

    @pytest.mark.parametrize('index', [5, -6])
    def test_out_of_range_raises(self, index):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        with pytest.raises(IndexError):
            rt.scale(index, 2)

    def test_mismatched_lengths_raise(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        with pytest.raises(ValueError):
            rt.scale([0, 1], [2])

    def test_ratio_one_is_a_no_op(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        rt.scale(2, 1)
        assert rt.group.S == (4, 2, 3, 6, 3)
        assert str(rt.meas) == '18/18'

    def test_returns_self_for_chaining(self):
        rt = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        assert rt.scale(2, 3) is rt

    def test_a_nested_operand_flattens(self):
        rt = RT(meas='1/1', subdivisions=((2, (2, 1)), 1, 2, 1))
        rt.scale(2, 3)
        assert rt.group.S == (4, 2, 9, 6, 3)


class TestSpanIsAlwaysPreserved:
    """``span`` multiplies the Tempus, so every duration here is out of TWO
    whole notes, not one -- which is what makes these worth asserting
    separately. The exact per-event durations are pinned, not just their
    sum: a total of 2 survives any redistribution, so on its own it cannot
    tell a correct result from a scrambled one."""

    def test_a_multi_measure_tree_keeps_its_span_and_length(self):
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.scale(1, Fraction(1, 3))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'
        assert rt.group.S == (3, 1, 3, 3)
        assert rt.durations == (Fraction(3, 5), Fraction(1, 5),
                                Fraction(3, 5), Fraction(3, 5))
        assert sum(abs(d) for d in rt.durations) == Fraction(2)

    def test_insertion_into_a_multi_measure_tree(self):
        """The inserted ``1/2`` equals what each event already weighed, so
        the five come out equal -- a result that pins the compression but
        says nothing about POSITION. See the asymmetric case below."""
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.insert(0, Fraction(1, 2))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'
        assert rt.group.S == (1, 1, 1, 1, 1)
        assert rt.durations == (Fraction(2, 5),) * 5
        assert sum(abs(d) for d in rt.durations) == Fraction(2)

    def test_an_asymmetric_insertion_lands_where_it_was_asked_to(self):
        rt = RT(span=2, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.insert(1, Fraction(1, 4))
        assert rt.group.S == (2, 1, 2, 2, 2)
        assert rt.durations == (Fraction(4, 9), Fraction(2, 9),
                                Fraction(4, 9), Fraction(4, 9),
                                Fraction(4, 9))
        assert rt.span == 2
        assert str(rt.meas) == '4/4'


class TestPreservedFamilyChains:
    def test_the_family_composes(self):
        rt = (RT(meas='2/2', subdivisions=(2, 1, 2))
              .insert(2, Fraction(3, 10))
              .scale(0, 2))
        assert rt.group.S == (8, 2, 3, 4)
        assert str(rt.meas) == '2/2'


# ----------------------------------------------------------------------
# what a rebuilt leaf carries
# ----------------------------------------------------------------------
class TestPayloadsSurviveTheRebuild:
    """A preserved-family verb re-spells the leaf surface. What it must NOT
    do is throw away everything the surviving events were carrying.

    ``CompositionalTree(ParameterApiMixin, RhythmTree)`` inherits this whole
    family, and its pfields, mfields and instrument bindings live in NODE
    DATA -- so a rebuild that deletes every non-root node deletes them too,
    silently. ``extract`` is the oracle: it never rebuilt, and survivors kept
    their payloads. All three verbs must now agree with it."""

    @staticmethod
    def _tree(subdivisions=(1, 1, 1, 1)):
        from klotho.thetos.composition.compositional import CompositionalTree
        ct = CompositionalTree(meas='4/4', subdivisions=subdivisions)
        return ct

    def test_scale_keeps_per_event_pfields(self):
        ct = self._tree()
        for n, amp in zip(ct.leaf_nodes, (0.125, 0.25, 0.5, 0.75)):
            ct.set_pfields(n, amp=amp)
        ct.scale(0, 3)
        assert [ct.get_pfield(n, 'amp') for n in ct.leaf_nodes] == \
            [0.125, 0.25, 0.5, 0.75]

    def test_scale_keeps_per_event_mfields(self):
        ct = self._tree()
        for n, name in zip(ct.leaf_nodes, ('m0', 'm1', 'm2', 'm3')):
            ct.set_mfields(n, articulation=name)
        ct.scale(0, 3)
        assert [ct.get_mfield(n, 'articulation') for n in ct.leaf_nodes] == \
            ['m0', 'm1', 'm2', 'm3']

    def test_insert_keeps_pfields_and_the_new_event_takes_the_default(self):
        ct = self._tree()
        ct.set_pfields(ct.root, amp=0.5)
        for n, amp in zip(ct.leaf_nodes, (0.125, 0.25, 0.5, 0.75)):
            ct.set_pfields(n, amp=amp)
        ct.insert(2, Fraction(1, 8))
        assert [ct.get_pfield(n, 'amp') for n in ct.leaf_nodes] == \
            [0.125, 0.25, 0.5, 0.5, 0.75]

    def test_a_pfield_on_a_DELETED_interior_node_survives_the_flatten(self):
        """The rebuild deletes the group node, so an override that only ever
        lived there has to be pushed down onto the events that inherited it
        -- otherwise flattening silently un-sets it."""
        ct = self._tree((1, (2, (1, 1)), 1))
        group = ct.successors(ct.root)[1]
        ct.set_pfields(group, amp=0.9)
        ct.scale(0, 2)
        assert [ct.get_pfield(n, 'amp') for n in ct.leaf_nodes] == \
            [None, 0.9, 0.9, None]

    def test_the_root_keeps_inheriting_after_the_rebuild(self):
        """Only the ancestors that were DELETED are pushed down. The root
        survives, so a value set there still cascades -- and still cascades
        to events written later."""
        ct = self._tree()
        ct.scale(0, 3)
        ct.set_pfields(ct.root, amp=0.4)
        assert [ct.get_pfield(n, 'amp') for n in ct.leaf_nodes] == \
            [0.4, 0.4, 0.4, 0.4]

    def test_an_instrument_bound_on_a_leaf_follows_its_event(self):
        ct = self._tree()
        ct.set_instrument(ct.leaf_nodes[2], 'marimba')
        ct.scale(0, 3)
        assert [ct.get_instrument(n) for n in ct.leaf_nodes] == \
            [None, None, 'marimba', None]

    def test_no_binding_is_left_on_a_node_that_no_longer_exists(self):
        """Freed node indices are REUSED, so a binding left behind on a
        deleted node does not merely leak -- it re-attaches itself to
        whatever event lands in that slot."""
        ct = self._tree((1, (2, (1, 1)), 1))
        group = ct.successors(ct.root)[1]
        ct.set_instrument(group, 'marimba')
        ct.scale(0, 2)
        assert set(ct.node_instruments) <= set(ct.nodes)
        assert [ct.get_instrument(n) for n in ct.leaf_nodes] == \
            [None, 'marimba', 'marimba', None]

    def test_a_tie_group_carries_its_HEADs_payload(self):
        """A tie group decomposes to ONE event, so it has one payload: the
        head's. The continuation's own overrides go with the continuation."""
        ct = self._tree((1, 1.0, 1, 1))
        heads = [g[0] for g in ct.tie_groups]
        for n, amp in zip(heads, (0.125, 0.25, 0.5)):
            ct.set_pfields(n, amp=amp)
        ct.set_pfields(ct.tie_groups[0][1], amp=0.99)
        ct.scale(0, 2)
        assert [ct.get_pfield(n, 'amp') for n in ct.leaf_nodes] == \
            [0.125, 0.25, 0.5]

    def test_a_plain_RhythmTree_is_unaffected(self):
        rt = RT(meas='4/4', subdivisions=(1, 2, 3, 4))
        rt.scale(0, 2)
        assert rt.group.S == (2, 2, 3, 4)
        assert all('proportion' in rt[n] for n in rt.nodes)


# ----------------------------------------------------------------------
# the authored Tempus spelling
# ----------------------------------------------------------------------
class TestTheAuthoredSpellingIsNeverMoved:
    """A preserved-family verb never moves the Tempus -- not its value and
    not its spelling.

    The earlier rule re-spelled onto the refined grid whenever the authored
    denominator happened to equal the old grid. That is an arithmetic
    accident of every EQUAL-BEAT bar, so it rewrote ordinary meters:
    ``3/4`` became ``6/8`` (the one pair a musician must not have
    interchanged), ``4/4`` became ``8/8``, and ``3/4`` compressed by ``1/5``
    became ``15/20``, which is not a time signature at all. It also moved
    the beat: ``TemporalUnit`` derives its default beat from the Tempus
    denominator.

    Re-spelling is never FORCED -- see
    ``test_a_finer_grid_needs_no_finer_denominator``. ``18/18`` is a GRID,
    a normalized ratio nobody engraves; ``3/4`` is a METER. No rule can tell
    them apart from the arithmetic, and the misfire class is the common
    case, so the authored spelling stands.

    RULING flagged to Ryan as reversible: if Haddad's printed spelling is
    wanted, it returns as an opt-in argument, not as the default."""

    def test_a_finer_grid_needs_no_finer_denominator(self):
        """The claim the ruling rests on. A tree's timing is ``meas * span``
        distributed over integer proportions, so the denominator is a free
        display choice: the SAME durations are expressible under the
        authored Tempus and under the refined one. If this ever failed, the
        ruling would be overturned -- re-spelling would be forced."""
        authored = RT(meas='3/4', subdivisions=(1, 1, 1))
        authored.insert(1, Fraction(1, 8))
        refined = RT(meas='6/8', subdivisions=(2, 1, 2, 2))
        assert authored.durations == refined.durations
        assert authored.meas.to_fraction() == refined.meas.to_fraction()
        assert all(isinstance(p, int) for p in authored.group.S)

    @pytest.mark.parametrize('meas,subdivisions,index,duration,expected', [
        ('3/4', (1, 1, 1), 1, '1/8', (2, 1, 2, 2)),
        ('4/4', (1, 1, 1, 1), 2, '1/8', (2, 2, 1, 2, 2)),
        ('6/8', (1,) * 6, 1, '1/16', (2, 1, 2, 2, 2, 2, 2)),
        ('12/8', (1,) * 12, 1, '1/16', (2, 1) + (2,) * 11),
        ('7/8', (1,) * 7, 1, '1/16', (2, 1, 2, 2, 2, 2, 2, 2)),
    ])
    def test_insert_keeps_the_meter(self, meas, subdivisions, index,
                                    duration, expected):
        rt = RT(meas=meas, subdivisions=subdivisions)
        total = sum(abs(d) for d in rt.durations)
        rt.insert(index, duration)
        assert str(rt.meas) == meas
        assert rt.group.S == expected
        assert sum(abs(d) for d in rt.durations) == total

    @pytest.mark.parametrize('meas,subdivisions,index,ratio,expected', [
        ('3/4', (1, 1, 1), 0, '1/5', (1, 5, 5)),
        ('4/4', (1, 1, 1, 1), 0, '1/3', (1, 3, 3, 3)),
        ('6/8', (1,) * 6, 0, '1/4', (1, 4, 4, 4, 4, 4)),
        ('7/8', (1,) * 7, 0, '1/3', (1, 3, 3, 3, 3, 3, 3)),
    ])
    def test_scale_keeps_the_meter(self, meas, subdivisions, index, ratio,
                                   expected):
        rt = RT(meas=meas, subdivisions=subdivisions)
        total = sum(abs(d) for d in rt.durations)
        rt.scale(index, ratio)
        assert str(rt.meas) == meas
        assert rt.group.S == expected
        assert sum(abs(d) for d in rt.durations) == total

    def test_a_span_2_tree_whose_denominator_IS_the_grid(self):
        """The case ``TestSpanIsAlwaysPreserved`` could not reach: with
        ``span=2, meas='4/4'`` the grid is 2 and the denominator is 4, so
        the re-spell branch never ran. Here they coincide."""
        rt = RT(span=2, meas='2/4', subdivisions=(1, 1, 1, 1))
        rt.scale(0, Fraction(1, 3))
        assert str(rt.meas) == '2/4'
        assert rt.span == 2
        assert rt.group.S == (1, 3, 3, 3)
        assert sum(abs(d) for d in rt.durations) == Fraction(1)

    def test_the_beat_does_not_move_under_the_operator(self):
        """The live consequence: ``TemporalUnit`` derives its default beat
        from the Tempus denominator, so re-spelling ``3/4`` as ``6/8``
        turned a quarter-note beat into an eighth-note beat."""
        from klotho.chronos import TemporalUnit
        rt = RT(meas='3/4', subdivisions=(1, 1, 1))
        assert TemporalUnit.from_rt(rt).beat == Fraction(1, 4)
        rt.insert(1, Fraction(1, 8))
        assert TemporalUnit.from_rt(rt).beat == Fraction(1, 4)


class TestTheArgumentOrderHazard:
    """``(index, value)`` REVERSES Haddad's printed ``⊗((ratios),
    (positions))``. The order is deliberate -- it matches ``list.insert``,
    ``TemporalUnitSequence.insert`` and ``TemporalBlock.insert`` -- but a
    reversed pair of two integers is indistinguishable and runs silently."""

    def test_haddads_printed_order_gives_a_different_answer(self):
        published = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        published.scale(2, 3)
        reversed_pair = RT(meas='18/18', subdivisions=(4, 2, 3, 6, 3))
        reversed_pair.scale(3, 2)
        assert published.group.S == (4, 2, 9, 6, 3)     # fig. 4.65
        assert reversed_pair.group.S == (4, 2, 3, 12, 3)
        assert published.group.S != reversed_pair.group.S

    @pytest.mark.parametrize('index', [Fraction(3, 10), '1/8', 1.0, None])
    def test_a_non_integer_index_raises_instead_of_being_dropped(self, index):
        """A Fraction index used to pass the range test and then match no
        position, so the operation was dropped in silence."""
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(TypeError):
            rt.insert(index, 2)
        with pytest.raises(TypeError):
            rt.scale(index, 2)

    def test_the_message_names_the_argument_order(self):
        rt = RT(meas='2/2', subdivisions=(2, 1, 2))
        with pytest.raises(TypeError, match='index, value'):
            rt.insert(Fraction(3, 10), 2)


class TestScaleFlattensTiesToo:
    """``insert``'s docstring said so and ``scale``'s did not, though they
    destroy ties identically: both decompose first, and a tie group
    decomposes to ONE event."""

    def test_a_tie_group_comes_back_as_one_leaf(self):
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1, 1))
        assert rt.tie_groups == ((1, 2), (3,), (4,))
        rt.scale(0, 2)
        assert rt.group.S == (4, 1, 1)
        assert not any(rt[n].get('tied') for n in rt.nodes)

    def test_the_attack_count_is_unchanged(self):
        """A tie group was never more than one attack, so flattening it
        loses notation, not events."""
        rt = RT(meas='4/4', subdivisions=(1, 1.0, 1, 1))
        before = len(rt.tie_groups)
        rt.scale(0, 2)
        assert len(rt.tie_groups) == before == 3
