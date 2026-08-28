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
        """A tied interior node round-trips D as 2.0."""
        assert RhythmTree(span=1, meas='4/4',
                          subdivisions=(1, (2.0, (1, 1)), 1)) is not None

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
