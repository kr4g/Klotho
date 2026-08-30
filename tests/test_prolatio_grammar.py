"""Construction-time validation of the prolatio (S) grammar.

WL-24 / NEW-27 / NEW-05. Before this, three malformed shapes built a tree
that ran and played the wrong thing:

  (1, 1.5, 1)  built three EQUAL leaves (the 1.5 was truncated and marked
               tied), so the tree displayed one rhythm and played another;
  (1, 0, 1)    built a 0-duration leaf, breaking strictly-increasing
               onsets, and could not be turned into a rest;
  (1, (2,))    died with a bare ``TypeError: bad operand type for abs()``
               naming no position in the structure.

The validator is deliberately LENIENT where Klotho round-trips its own
output -- see TestAcceptsWhatKlothoRoundTrips. Tightening it to the
stricter ``_validate_s_form`` used by ``subdivide`` would break the
library: 218 internal constructions pass a length-1 S, and tied trees
re-emit whole-valued floats.
"""

import numbers
from fractions import Fraction

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units import TemporalUnit


class TestRejectsSilentCorruption:

    def test_non_whole_float_raises(self):
        with pytest.raises(ValueError, match='whole number'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.5, 1))

    def test_non_whole_float_error_names_the_position(self):
        with pytest.raises(ValueError, match=r'S\[1\]'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.5, 1))

    def test_non_whole_float_error_suggests_the_fix(self):
        with pytest.raises(ValueError, match=r'\(2, 3, 2\)'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.5, 1))

    def test_nested_non_whole_float_raises_with_nested_path(self):
        with pytest.raises(ValueError, match=r'S\[1\]\[1\]\[0\]'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1.5, 1)), 1))

    def test_zero_proportion_raises(self):
        with pytest.raises(ValueError, match='cannot be zero'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, 0, 1))

    def test_zero_D_raises(self):
        with pytest.raises(ValueError, match='cannot be zero'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, (0, (1, 1)), 1))

    def test_malformed_pair_raises_value_error_not_bare_typeerror(self):
        with pytest.raises(ValueError, match='exactly 2 items'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, (2,), 1))

    def test_three_element_nested_raises(self):
        with pytest.raises(ValueError, match='exactly 2 items'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1, 1), 3), 1))

    def test_string_element_raises(self):
        with pytest.raises(ValueError, match='int or a whole-valued float'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, 'x', 1))

    def test_fraction_element_raises(self):
        """Fraction was silently accepted and silently wrong: (1, Fraction(3,2), 1)
        produced durations that do not sum to the measure."""
        with pytest.raises(ValueError, match='int or a whole-valued float'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, Fraction(3, 2), 1))

    def test_none_element_raises(self):
        with pytest.raises(ValueError, match='int or a whole-valued float'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, None, 1))


class TestAcceptsWhatKlothoRoundTrips:
    """Every shape here is emitted by Klotho itself. Rejecting any of them
    breaks the library -- this is the NEW-27 constraint, as tests."""

    def test_length_one_s(self):
        """The 'd' prolatio preset builds (1,)."""
        assert RhythmTree(span=1, meas='4/4', subdivisions=(1,)) is not None

    def test_length_one_negative_s(self):
        """The 'r' prolatio preset builds (-1,)."""
        assert RhythmTree(span=1, meas='4/4', subdivisions=(-1,)) is not None

    def test_empty_s(self):
        assert RhythmTree(span=1, meas='4/4', subdivisions=()) is not None

    def test_nested_empty_s(self):
        """Produced by real test data (the asymmetric tree in test_decompose)."""
        assert RhythmTree(span=1, meas='4/4', subdivisions=(1, (1, ()))) is not None

    def test_whole_valued_float_is_a_tie_marker_not_a_typo(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1.0, 1))
        assert rt is not None

    def test_whole_valued_float_D(self):
        """AMENDED 2026-08-29 (HAD-ALG; 07_TIES_CHARTER.md sect1): a float D
        on an interior node is now REFUSED. This pin originally asserted the
        round-trip ("a tied interior node round-trips D as 2.0") — but the
        marker propagated to nothing, and the wake condition's OpenMusic
        check found OM6 and om-sharp both give a float group value no tie
        meaning (fullratio/tree2ratio silently round it). Refusing loudly
        beats OM's silent rounding; tie the group's first leaf instead."""
        with pytest.raises(ValueError, match='leaf'):
            RhythmTree(span=1, meas='4/4',
                       subdivisions=(1, (2.0, (1, 1)), 1))

    def test_negative_proportions_are_rests(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1))
        assert any(d < 0 for d in rt.durations)

    def test_rest_group_authored_with_positive_children(self):
        assert RhythmTree(span=1, meas='1/1',
                          subdivisions=(1, (-1, (1, 1, 1, 1)), 1)) is not None

    def test_list_container_accepted(self):
        assert RhythmTree(span=1, meas='4/4', subdivisions=[1, 1, 1]) is not None

    def test_numpy_integer_accepted(self):
        np = pytest.importorskip('numpy')
        assert isinstance(np.int64(2), numbers.Integral)
        assert RhythmTree(span=1, meas='4/4',
                          subdivisions=(np.int64(2), 1)) is not None

    def test_tied_tree_survives_a_subtree_round_trip(self):
        """subtree() re-feeds floats through the constructor."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, (2, (1.0, 1)), 1))
        sub = rt.subtree(rt.leaf_nodes[1])
        assert sub is not None

    def test_prolatio_presets_still_build(self):
        for prolatio in ('d', 'r', 'p'):
            assert TemporalUnit(tempus='4/4', prolatio=prolatio, bpm=120) is not None


class TestSubdivideKeepsItsStricterRule:
    """The constructor validator must NOT replace _validate_s_form: refusing
    to subdivide into one part is a legitimate subdivide semantic."""

    def test_subdivide_still_rejects_single_element_s(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='at least 2 elements'):
            rt.subdivide(rt.leaf_nodes[0], (1,))

    def test_constructor_still_accepts_single_element_s(self):
        assert RhythmTree(span=1, meas='4/4', subdivisions=(1,)) is not None


class TestZeroCannotArriveByMutation:
    """NEW-05 — make_rest silently no-ops on a zero proportion, because
    ``-abs(0) == 0``. Relaxing that guard is a no-op; zero has to be
    unrepresentable instead."""

    def test_mutating_a_proportion_to_zero_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='cannot be zero'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=0)

    def test_make_rest_still_works_on_a_sounding_node(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        leaf = rt.leaf_nodes[0]
        rt.make_rest(leaf)
        assert rt[leaf]['proportion'] < 0

    def test_onsets_are_strictly_increasing_for_any_buildable_tree(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, -1, 1))
        onsets = list(rt.onsets)
        assert all(b > a for a, b in zip(onsets, onsets[1:]))


class TestNonWholeFloatCannotArriveByMutation:
    """NEW-32 -- the same hole as TestZeroCannotArriveByMutation, one door
    further along. The constructor refused ``(1, 1.5, 1)``, but the write
    path had no whole-number check at all, so ``set_node_data(leaf,
    proportion=1.5)`` was accepted in silence: ``1.5`` stored as ``1.0``
    with ``tied=True``, an event disappeared, and two sounds merged into
    one. A grammar enforced at construction only is not a grammar.
    """

    def test_mutating_a_proportion_to_a_non_whole_float_raises(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=1.5)

    def test_the_error_suggests_scaling_the_whole_s(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match=r'\(2, 3, 2\)'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=1.5)

    def test_update_node_data_is_guarded_too(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.update_node_data(rt.leaf_nodes[0], {'proportion': 2.5})

    def test_explicit_tied_false_does_not_launder_the_float(self):
        """``normalize_attrs`` ran BEFORE ``validate_attrs`` and did
        ``int(proportion)`` whenever ``tied=False`` -- so the truncation the
        guard exists to prevent happened before the guard could see it."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=1.5, tied=False)

    def test_explicit_tied_true_is_guarded_too(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=1.5, tied=True)

    def test_add_child_is_guarded_too(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.add_child(rt.leaf_nodes[0], proportion=1.5)

    def test_the_tree_is_intact_after_the_refusal(self):
        """The corruption this closes: four singleton tie-groups became
        ``((0,1),(2,),(3,))`` -- an event silently gone."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        groups_before = rt.tie_groups
        with pytest.raises(ValueError):
            rt.set_node_data(rt.leaf_nodes[0], proportion=1.5)
        assert rt.tie_groups == groups_before
        assert len(rt.durations) == 4

    def test_a_whole_float_still_authors_a_tie_on_the_write_path(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        leaf = rt.leaf_nodes[1]
        rt.set_node_data(leaf, proportion=2.0)
        assert rt[leaf]['tied'] is True

    def test_fraction_cannot_arrive_by_mutation(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='int or a whole-valued float'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=Fraction(3, 2))

    def test_string_cannot_arrive_by_mutation(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        with pytest.raises(ValueError, match='int or a whole-valued float'):
            rt.set_node_data(rt.leaf_nodes[0], proportion='x')

    def test_numpy_integer_still_accepted_on_the_write_path(self):
        np = pytest.importorskip('numpy')
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.set_node_data(rt.leaf_nodes[0], proportion=np.int64(3))
        assert rt[rt.leaf_nodes[0]]['proportion'] == 3


class TestBoolIsNotAProportion:
    """``bool`` is an ``int`` in Python, so every ``isinstance(x, int)``
    check silently took ``True`` for the proportion ``1``. A boolean is a
    type confusion, not a duration; all three surfaces refuse it."""

    def test_constructor_refuses_bool(self):
        with pytest.raises(ValueError, match='bool'):
            RhythmTree(span=1, meas='4/4', subdivisions=(1, True, 1))

    def test_write_path_refuses_bool(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='bool'):
            rt.set_node_data(rt.leaf_nodes[0], proportion=True)

    def test_subdivide_refuses_bool(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='bool'):
            rt.subdivide(rt.leaf_nodes[0], (1, True))


class TestSubdivideCanAuthorATie:
    """RT-2.2 -- ``subdivide`` could not author a tie at all: its
    ``isinstance(elem, int)`` test rejected the whole-valued float that IS
    Klotho's tie marker, so the one structural mutator for rhythm could
    build every shape the constructor could EXCEPT a tied one."""

    def test_subdivide_accepts_a_whole_float(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        leaf = rt.leaf_nodes[0]
        rt.subdivide(leaf, (1, 2.0))
        children = list(rt.successors(leaf))
        assert rt[children[0]]['tied'] is False
        assert rt[children[1]]['tied'] is True

    def test_tie_groups_reflect_the_authored_tie(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.subdivide(rt.leaf_nodes[0], (1, 2.0))
        leaves = rt.leaf_nodes
        assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],),
                                 (leaves[3],), (leaves[4],))

    def test_subdivide_matches_the_constructor_for_the_same_shape(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        rt.subdivide(rt.leaf_nodes[0], (1, 2.0))
        built = RhythmTree(span=1, meas='4/4',
                           subdivisions=((1, (1, 2.0)), 1, 1, 1))
        assert rt.durations == built.durations
        assert ([rt[n]['tied'] for n in rt.leaf_nodes]
                == [built[n]['tied'] for n in built.leaf_nodes])

    def test_subdivide_still_rejects_a_non_whole_float(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='whole number'):
            rt.subdivide(rt.leaf_nodes[0], (1, 1.5))

    def test_subdivide_still_rejects_a_tied_rest(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='tied rest'):
            rt.subdivide(rt.leaf_nodes[0], (1, -2.0))

    def test_subdivide_still_rejects_zero(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='cannot be zero'):
            rt.subdivide(rt.leaf_nodes[0], (1, 0))

    def test_subdivide_still_refuses_a_float_D(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        with pytest.raises(ValueError, match='leaf'):
            rt.subdivide(rt.leaf_nodes[0], (1, (2.0, (1, 1))))

    def test_subdivide_accepts_a_numpy_integer(self):
        """The old ``isinstance(elem, int)`` rejected numpy scalars that the
        constructor accepted -- the same divergence, opposite direction."""
        np = pytest.importorskip('numpy')
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        leaf = rt.leaf_nodes[0]
        rt.subdivide(leaf, (np.int64(1), np.int64(2)))
        children = list(rt.successors(leaf))
        assert [rt[c]['proportion'] for c in children] == [1, 2]

    def test_a_moved_tie_and_an_authored_tie_coexist(self):
        """Subdividing a TIED leaf moves its tie to the first child. When S
        also authors a tie on a later child, both survive: the group
        continues its predecessor AND its second leaf continues its first.
        Nothing is dropped, so nothing has to be chosen between."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        tied_leaf = rt.leaf_nodes[1]
        rt.subdivide(tied_leaf, (1, 2.0))
        children = list(rt.successors(tied_leaf))
        assert rt[children[0]]['tied'] is True   # moved from the parent
        assert rt[children[1]]['tied'] is True   # authored by S
        leaves = rt.leaf_nodes
        assert rt.tie_groups == ((leaves[0], leaves[1], leaves[2]),
                                 (leaves[3],), (leaves[4],))

    def test_a_moved_tie_onto_an_already_tied_first_child_is_idempotent(self):
        """The collision case: the tie moves onto a child S already tied.
        Both mean the same thing about the same leaf, so the move is a
        no-op rather than a conflict."""
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        tied_leaf = rt.leaf_nodes[1]
        rt.subdivide(tied_leaf, (1.0, 1))
        children = list(rt.successors(tied_leaf))
        assert rt[children[0]]['tied'] is True
        assert rt[children[1]]['tied'] is False
        leaves = rt.leaf_nodes
        assert rt.tie_groups == ((leaves[0], leaves[1]), (leaves[2],),
                                 (leaves[3],), (leaves[4],))

    def test_the_tied_leaf_itself_still_sheds_its_tie(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1.0, 1, 1))
        tied_leaf = rt.leaf_nodes[1]
        rt.subdivide(tied_leaf, (1, 2.0))
        assert rt[tied_leaf]['tied'] is False
        assert isinstance(rt[tied_leaf]['proportion'], int)


class TestTheLengthOneDivergenceIsDeliberate:
    """RT-2.3 -- the constructor accepts ``(1,)`` and ``subdivide`` refuses
    it, and that is not drift. The constructor describes a STRUCTURE, in
    which a one-part group is a real shape Klotho emits 218 times.
    ``subdivide`` describes an ACTION, and "divide this into one part" is a
    no-op the API declines on purpose."""

    def test_constructor_docstring_names_the_divergence(self):
        doc = RhythmTree._validate_s_grammar.__doc__
        assert 'structure' in doc.lower()
        assert 'subdivide' in doc

    def test_subdivide_validator_docstring_names_the_divergence(self):
        doc = RhythmTree._validate_s_form.__doc__
        assert 'action' in doc.lower()
        assert 'constructor' in doc.lower()

    def test_the_shared_scalar_rule_is_single_sourced(self):
        """All three surfaces delegate to one helper; the per-surface rules
        are additions to it, never restatements of it."""
        from klotho.chronos.rhythm_trees import rhythm_tree as rt_mod
        assert callable(rt_mod._check_proportion_scalar)


class TestGraftSubtreeDocstrings:
    """WL-29 — the docstring advertised an 'append' mode that never existed."""

    def test_append_is_not_a_mode(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        sub = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        with pytest.raises(ValueError, match='Invalid mode'):
            rt.graft_subtree(rt.leaf_nodes[0], sub, mode='append')

    def test_docstring_no_longer_advertises_append(self):
        assert 'append' not in RhythmTree.graft_subtree.__doc__

    def test_docstring_advertises_both_real_modes(self):
        doc = RhythmTree.graft_subtree.__doc__
        assert 'replace' in doc and 'adopt' in doc

    def test_canonical_docstring_documents_the_modes(self):
        from klotho.topos.graphs.trees import Tree
        doc = Tree.graft_subtree.__doc__
        assert 'replace' in doc and 'adopt' in doc

    def test_documented_return_type_matches_reality(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        sub = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1))
        result = rt.graft_subtree(rt.leaf_nodes[0], sub, mode='replace')
        assert isinstance(result, int)
        assert 'int' in RhythmTree.graft_subtree.__doc__
