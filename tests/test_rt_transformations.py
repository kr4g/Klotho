"""Haddad's Chapter-2 rhythm-tree transformations (HAD-RT; RT-4, RT-3).

Conformance targets are Haddad's published figures, under the established
pattern this project already uses in ``tests/test_rt_algebra.py``:
behavioural agreement on published examples, never implementation
matching, with every divergence documented and argued.

The fixture chain is thesis pp. 279-280, sect2.3.3-2.3.5, figures
2.12 -> 2.13 -> 2.14, archived with provenance, page renders and the
French prose in English translation at
``projects/klotho-evolution/evidence/haddad-figs-2.12-2.15/``:

- 2.12  (8 ((4 (1 1 1 1 1)) (2 (1 1 1)) (1 (1 1 1 1))
             (5 (1 1)) (5 (1)) (3 (1 1 1 1 1))))
- 2.13  *filtrage* ("filtering") of 2.12 by the source series (5 3 4 2 1 5)
- 2.14  *rythme evide* ("hollowed-out rhythm") of 2.13

Related pins live elsewhere and are cross-referenced by name rather than
duplicated: ``tests/test_tie_groups.py::TestTiedRestsAreIllegal`` owns the
charter sect1 invariant, and
``tests/test_tie_groups.py::TestGroupDerivation`` owns tie-group
derivation. This file only checks that the two transformations respect
them.
"""

from fractions import Fraction

import pytest

from klotho.chronos import RhythmTree
from klotho.chronos.rhythm_trees.algorithms import evide, filtrage


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------

# Figure 2.12: the third circular permutation of fig. 2.11, subdivided by
# the source series (5 3 4 2 1 5). Twenty leaves over six irrational groups.
FIG_2_12 = ((8, ((4, (1, 1, 1, 1, 1)),
                 (2, (1, 1, 1)),
                 (1, (1, 1, 1, 1)),
                 (5, (1, 1)),
                 (5, (1,)),
                 (3, (1, 1, 1, 1, 1)))),)

# Figure 2.13 AS KLOTHO PRODUCES IT -- the 20-leaf mechanical form. Haddad
# prints group 5 as ``(5 (-4 -1))``; see TestFiltrage.test_group_five_is_a
# _documented_divergence for why the one-leaf spelling is the filtering's
# real output and his is a later re-spelling.
FIG_2_13_20_LEAF = "(8 ((4 (-1 1 1 1 1)) (2 (-1 1 1)) (1 (-1 1 1 1)) " \
                   "(5 (-1 1)) (5 (-1)) (3 (-1 1 1 1 1))))"

# Figure 2.13 EXACTLY AS PRINTED, group 5 split. This is evide's published
# input, and feeding it reproduces figure 2.14 character for character.
FIG_2_13_PRINTED = ((8, ((4, (-1, 1, 1, 1, 1)),
                         (2, (-1, 1, 1)),
                         (1, (-1, 1, 1, 1)),
                         (5, (-1, 1)),
                         (5, (-4, -1)),
                         (3, (-1, 1, 1, 1, 1)))),)

# Figure 2.14, as printed. The ``1.0`` markers are genuinely in the thesis
# (confirmed against the 200 dpi page render) and are identical to Klotho's
# own storage convention for a tie continuation.
FIG_2_14 = "(8 ((4 (1 -1 -1 -1 -1)) (2 (1 -1 -1)) (1 (1 -1 -1 -1)) " \
           "(5 (1 -1)) (5 (4 1.0)) (3 (1.0 -1 -1 -1 -1))))"

SERIES = (5, 3, 4, 2, 1, 5)


def _num(v):
    """Render one proportion the way Haddad prints it (``1`` vs ``1.0``)."""
    return repr(v) if isinstance(v, float) else str(int(v))


def _sexp(node):
    """Render a subdivision node as Haddad's printed S-expression."""
    if isinstance(node, (tuple, list)):
        d, s = node
        return f"({_num(d)} ({' '.join(_sexp(x) for x in s)}))"
    return _num(node)


def _printed(rt):
    """The tree's single top-level group as a printed S-expression."""
    assert len(rt.subdivisions) == 1, "fixture trees have one top group"
    return _sexp(rt.subdivisions[0])


def _signs(rt):
    """True where a leaf sounds, in leaf order."""
    return tuple(rt[n]['proportion'] > 0 for n in rt.leaf_nodes)


# --------------------------------------------------------------------------
# RT-4: filtrage
# --------------------------------------------------------------------------

class TestFiltrage:
    """Haddad sect2.3.4, *Du filtrage* ("On filtering"), thesis p. 279.

    *"Nous filtrons le rythme subdivise (2.12) par la meme serie originelle
    (5 3 4 2 1 (5)) qui donnera par extension des silences aux positions
    (0 5 8 12 14 15 20) qui se trouvent etre la premiere note de chaque
    groupe d'irrationnel"*

    "We filter the subdivided rhythm (2.12) by the same original series
    (5 3 4 2 1 (5)) which will by extension give rests at positions
    (0 5 8 12 14 15 20), which happen to be the first note of each
    irrational group."

    His footnote 5: *"0 etant la premiere position comme il est souvent
    l'usage dans les langages informatiques."* -- "0 being the first
    position, as is often the usage in computing languages." So the
    indexing convention is settled by the source, not chosen by us.
    """

    def test_positions_are_haddads_printed_list(self):
        # The rule is [0] + inclusive prefix sums, which reproduces his
        # printed list character for character.
        from itertools import accumulate
        assert [0] + list(accumulate(SERIES)) == [0, 5, 8, 12, 14, 15, 20]

    def test_published_figure_2_13(self):
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12)
        assert len(rt.leaf_nodes) == 20
        assert _printed(filtrage(rt, SERIES)) == FIG_2_13_20_LEAF

    def test_rests_land_on_the_first_note_of_each_group(self):
        # His own gloss on the figure. Six groups, six rested heads --
        # which holds on the 20-leaf reading and only on that reading.
        rt = filtrage(RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12),
                      SERIES)
        rested = [i for i, s in enumerate(_signs(rt)) if not s]
        assert rested == [0, 5, 8, 12, 14, 15]

    def test_group_five_is_a_documented_divergence(self):
        """Klotho emits ``(5 (-1))``; Haddad prints ``(5 (-4 -1))``.

        The split is genuinely printed (confirmed against the page render)
        and he carries it through figs. 2.14 ``(5 (4 1.0))`` and 2.15
        ``(5 (5))``: he split the rest so the *evide* would have a tie to
        demonstrate there. It is his re-spelling, applied after filtering,
        not the filtering's output. Two independent reasons the one-leaf
        form is the operation's real result:

        1. His printed positions ``(0 5 8 12 14 15 20)`` are the prefix
           sums of a TWENTY-leaf surface, with 20 as the exact wrap. A
           21-leaf tree would have to read ``... 15 16``.
        2. "the first note of each irrational group" holds for exactly six
           positions over six groups only on the 20-leaf reading.

        The two spellings are durationally identical, which is what this
        test pins alongside the divergence.
        """
        ours = filtrage(RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12),
                        SERIES)
        assert "(5 (-1))" in _printed(ours)
        assert "(5 (-4 -1))" not in _printed(ours)
        # Durationally identical: group 5 is one 5-unit rest either way.
        his = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_13_PRINTED)
        ours_g5 = [d for d in ours.durations][14:15]
        his_g5 = [d for d in his.durations][14:16]
        assert sum(abs(Fraction(d)) for d in ours_g5) == \
               sum(abs(Fraction(d)) for d in his_g5)

    def test_returns_a_new_tree_and_leaves_the_input_alone(self):
        # Matches decompose/fuse/flatten: transformations return new trees.
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12)
        before = _printed(rt)
        out = filtrage(rt, SERIES)
        assert out is not rt
        assert _printed(rt) == before

    def test_out_of_range_positions_are_clipped_not_wrapped(self):
        """Klotho's choice, not Haddad's -- his example cannot settle it.

        On his tree ``20 % 20 == 0`` and leaf 0 is already a target, so
        clip and wrap are indistinguishable there. We clip: the position
        list is a prefix-sum WALK over the leaf surface, so running off the
        end means the series overshot the tree.
        """
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        out = filtrage(rt, (3, 3, 3))  # positions 0, 3, 6, 9 -> keep 0, 3
        assert _signs(out) == (False, True, True, False)

    def test_the_trailing_total_is_kept(self):
        """Also Klotho's choice. ``[0] + accumulate(series)`` gives n+1
        positions; ``[0] + accumulate(series[:-1])`` gives n. They coincide
        only when ``sum(series) == len(leaf_nodes)``, which is Haddad's
        case. We keep the trailing total because it is literally what he
        printed, and clipping degrades it to the other form in his case.
        """
        rt = RhythmTree(span=1, meas='30/4', subdivisions=tuple([1] * 30))
        rested = [i for i, s in enumerate(_signs(filtrage(rt, SERIES)))
                  if not s]
        # 20 is in range on a 30-leaf tree, so the two formulations diverge
        # here and this pins which one ships.
        assert rested == [0, 5, 8, 12, 14, 15, 20]

    def test_is_idempotent(self):
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12)
        once = filtrage(rt, SERIES)
        assert _printed(filtrage(once, SERIES)) == _printed(once)

    def test_filtering_a_tie_continuation_clears_its_tie(self):
        # charter sect1: a tied rest is illegal, so the sign flip must not
        # manufacture one. See tests/test_tie_groups.py::
        # TestTiedRestsAreIllegal, which owns the invariant itself.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.set_node_data(rt.leaf_nodes[1], tied=True)
        out = filtrage(rt, (1,))  # positions 0, 1
        for n in out.leaf_nodes:
            assert not (out[n]['proportion'] < 0 and out[n].get('tied'))
        assert _signs(out) == (False, False, True, True)

    def test_rejects_an_empty_series(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError):
            filtrage(rt, ())

    def test_rejects_a_non_positive_step(self):
        # A zero or negative step makes the prefix-sum walk stall or run
        # backwards, which is not a filtering of anything.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError):
            filtrage(rt, (2, 0, 1))
        with pytest.raises(ValueError):
            filtrage(rt, (2, -1))


# --------------------------------------------------------------------------
# RT-3: evide
# --------------------------------------------------------------------------

class TestEvide:
    """Haddad sect2.3.5, *Du rythme evide*, thesis p. 280.

    *"Nous emprunterons a Pierre Boulez le principe du << rythme evide >>
    [...] comme on peut aussi representer comme un rythme << negatif >>
    d'un autre qui lui est pendant. Il s'agit d'intervertir les silences
    par des notes exprimees et vice et versa"*

    "We will borrow from Pierre Boulez the principle of the 'hollowed-out
    rhythm' [...] which can also be represented as a 'negative' rhythm of
    another that is its counterpart. It is a matter of interchanging the
    rests with expressed notes and vice versa."

    Boulez source as Haddad cites it: Pierre Boulez and Paule Thevenin,
    *Releves d'apprenti* ("Apprentice's Notes"), Editions du Seuil, 1966.
    """

    def test_published_figure_2_14(self):
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_13_PRINTED)
        assert _printed(evide(rt)) == FIG_2_14

    def test_the_tie_group_crosses_a_branch_boundary(self):
        """The re-tie in fig. 2.14 spans leaf ordinals 14/15/16 -- the last
        leaf of group 5 and the first leaf of group 6. Leaf ORDER, not
        subtree containment, is what joins a group (charter sect2), and
        this published figure is the case that proves it.
        """
        out = evide(RhythmTree(span=1, meas='8/2',
                               subdivisions=FIG_2_13_PRINTED))
        leaves = list(out.leaf_nodes)
        multi = [g for g in out.tie_groups if len(g) > 1]
        assert len(multi) == 1
        assert [leaves.index(n) for n in multi[0]] == [14, 15, 16]
        # and it really does straddle two different parents
        parents = {out.parent(n) for n in multi[0]}
        assert len(parents) == 2

    def test_charter_sect10_run_rule(self):
        """charter sect10: for each maximal run of newly-sounding leaves,
        head keeps ``tied=False``, the rest get ``tied=True``.
        """
        rt = RhythmTree(span=1, meas='4/4',
                        subdivisions=(-1, -1, 1, -1, -1, 1, 1, 1))
        out = evide(rt)
        assert _signs(out) == (True, True, False, True, True, False,
                               False, False)
        leaves = list(out.leaf_nodes)
        tied = [out[n].get('tied', False) for n in leaves]
        assert tied == [False, True, False, False, True, False, False, False]

    def test_returns_a_new_tree_and_leaves_the_input_alone(self):
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_13_PRINTED)
        before = _printed(rt)
        out = evide(rt)
        assert out is not rt
        assert _printed(rt) == before

    # -- the three traps ---------------------------------------------------

    def test_trap_one_negative_interior_nodes_are_normalised(self):
        """``_evaluate`` re-negates a positive child of a negative parent,
        so flipping a leaf sounding under a resting BRANCH is silently
        undone. evide normalises negative interior nodes to positive first.

        Without the normalisation ``(1, (-2 (1 1)), 1)`` hollows out to
        ``(-1, (-2 (-1 -1)), -1)`` -- the group stays a rest and nothing
        sounds at all. Shape exercised from the other side by
        ``tests/test_tie_groups.py::
        test_resting_a_branch_clears_descendant_ties``.
        """
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (-2, (1, 1)), 1))
        out = evide(rt)
        assert _printed_flat(out) == "(-1 (2 (1 1.0)) -1)"

    def test_trap_two_the_sound_flip_clears_tied_explicitly(self):
        """Writing an int ``proportion`` does NOT clear ``tied``:
        ``_evaluate`` reads ``isinstance(s, float) or data['tied']``, and
        only a NEGATIVE value forces the flag off. So a leaf flipped from
        rest to sound must be written with an explicit ``tied=False`` or it
        keeps a stale flag and re-floats to ``2.0``.

        Here every leaf sounds after the flip, so charter sect10's run rule
        is the ONLY thing allowed to set a tie -- head untied, rest tied.
        """
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(-1, -2, -1))
        out = evide(rt)
        leaves = list(out.leaf_nodes)
        assert [out[n].get('tied', False) for n in leaves] == \
               [False, True, True]

    def test_trap_three_input_ties_are_destroyed_by_design(self):
        """evide flips every leaf, so every input tie clears and charter
        sect10's run rule re-ties from scratch. So ``evide(evide(x))``
        restores x's SIGN PATTERN exactly, but normalises its ties to the
        MAXIMAL re-tie -- an involution on the signs only, never on the
        whole tree. Both directions of the loss are pinned here.
        """
        # (a) ties are ADDED where the input had none: every adjacent
        #     sounding pair comes back tied.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, -1, 1))
        assert all(len(g) == 1 for g in rt.tie_groups)   # no ties going in
        twice = evide(evide(rt))
        assert _signs(twice) == _signs(rt)               # signs restored
        assert [len(g) for g in twice.tie_groups] == [2, 1, 1]

        # (b) a tie is LOST when it was a dangling continuation -- a tied
        #     leaf whose predecessor is a rest (charter sect6). The run
        #     rule makes it a head instead, because runs are computed after
        #     the flip and a run cannot start mid-rest.
        rt2 = RhythmTree(span=1, meas='4/4', subdivisions=(-1, 1, 1))
        rt2.set_node_data(rt2.leaf_nodes[1], tied=True)
        assert rt2[rt2.leaf_nodes[1]].get('tied') is True
        twice2 = evide(evide(rt2))
        assert _signs(twice2) == _signs(rt2)
        assert twice2[twice2.leaf_nodes[1]].get('tied', False) is False

    # -- edge cases --------------------------------------------------------

    def test_all_rest_input_becomes_one_tie_group_with_an_untied_head(self):
        # charter sect10's second guard: the run head must not end up a
        # dangling continuation. By construction it cannot, because runs
        # are computed AFTER the flip.
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(-1, -1, -1, -1))
        out = evide(rt)
        assert _signs(out) == (True, True, True, True)
        assert len(out.tie_groups) == 1
        assert out[out.leaf_nodes[0]].get('tied', False) is False

    def test_all_sounding_input_becomes_all_rests_no_tied_rest(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        out = evide(rt)
        assert _signs(out) == (False, False, False, False)
        assert all(len(g) == 1 for g in out.tie_groups)
        for n in out.leaf_nodes:
            assert not (out[n]['proportion'] < 0 and out[n].get('tied'))

    def test_never_produces_a_tied_rest(self):
        # The charter sect1 invariant itself is owned by
        # tests/test_tie_groups.py::TestTiedRestsAreIllegal; this only
        # checks that evide respects it across the fixture chain.
        cases = [FIG_2_12, FIG_2_13_PRINTED,
                 (1, (-2, (1, 1)), 1), (-1, -1, 1, -1)]
        for s in cases:
            rt = RhythmTree(span=1, meas='8/2', subdivisions=s)
            for tree in (evide(rt), evide(evide(rt))):
                for n in tree.leaf_nodes:
                    assert not (tree[n]['proportion'] < 0
                                and tree[n].get('tied'))

    def test_total_duration_is_unchanged(self):
        # A hollowing-out is a re-voicing, not a re-timing.
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_13_PRINTED)
        out = evide(rt)
        assert sum(abs(Fraction(d)) for d in out.durations) == \
               sum(abs(Fraction(d)) for d in rt.durations)


# --------------------------------------------------------------------------
# The two composed: Haddad's own chain
# --------------------------------------------------------------------------

class TestTheHaddadChain:
    """2.12 -> filtrage -> 2.13 -> evide -> 2.14, run end to end."""

    def test_filtrage_then_evide_on_the_twenty_leaf_form(self):
        rt = RhythmTree(span=1, meas='8/2', subdivisions=FIG_2_12)
        out = evide(filtrage(rt, SERIES))
        # Identical to fig. 2.14 except in group 5, where our filtrage kept
        # the one-leaf spelling: his ``(5 (4 1.0))`` becomes ``(5 (1))``,
        # the same 5 units of sound, spelled once instead of twice.
        assert _printed(out) == (
            "(8 ((4 (1 -1 -1 -1 -1)) (2 (1 -1 -1)) (1 (1 -1 -1 -1)) "
            "(5 (1 -1)) (5 (1)) (3 (1.0 -1 -1 -1 -1))))"
        )

    def test_the_cross_branch_tie_survives_the_respelling(self):
        # The tie that fig. 2.14 demonstrates is still there on the 20-leaf
        # form -- two members instead of three, because group 5 has one
        # leaf instead of two, but still crossing the branch boundary.
        out = evide(filtrage(RhythmTree(span=1, meas='8/2',
                                        subdivisions=FIG_2_12), SERIES))
        multi = [g for g in out.tie_groups if len(g) > 1]
        assert len(multi) == 1
        assert len(multi[0]) == 2
        assert len({out.parent(n) for n in multi[0]}) == 2


def _printed_flat(rt):
    """Render a whole S (not a single group) as an S-expression body."""
    return "(" + " ".join(_sexp(x) for x in rt.subdivisions) + ")"
