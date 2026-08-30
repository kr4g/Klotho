"""LAYER-8 — an integer that cannot be a node index is ABSENT, not an OverflowError.

rustworkx node indices are unsigned machine integers. Handing the PyO3 binding a
negative id (or one wider than the platform's index type) made the *conversion*
fail before any Klotho guard could answer, so seven node-addressed verbs and the
``in`` operator all leaked ``OverflowError: can't convert negative int to
unsigned`` — a foreign binding's frame that names neither the method nor the
argument that was wrong.

The oracle in this file is never a hand-written message. It is a **control call
with a positive-but-absent id** (``999``): whatever ``make_rest(999)`` does,
``make_rest(-1)`` must do, because both name a node the tree does not have. The
tests compare exception type and message shape between the two, so the pair
cannot diverge again without a failure here.

What this does NOT change: a *non-integer* node argument (``"x"``, ``1.5``,
``None``) is a different mistake and still raises ``TypeError``, which is the
right type for an argument of the wrong type.
"""

import sys

import pytest

from klotho.chronos import RhythmTree
from klotho.topos.graphs import Graph
from klotho.topos.graphs.trees import Tree


ABSENT = 999                      # positive, and not in the tree: the control
NEGATIVE = -1                     # was OverflowError from the Rust binding
TOO_BIG = sys.maxsize * 2 + 2     # one past the largest representable index

UNADDRESSABLE = [NEGATIVE, TOO_BIG]


def _rt():
    return RhythmTree(meas='4/4', subdivisions=(1, 1, 1, 1))


# Every node-addressed verb the row names, as (name, call-with-a-node-id).
VERBS = [
    ('make_rest', lambda rt, n: rt.make_rest(n)),
    ('make_sounding', lambda rt, n: rt.make_sounding(n)),
    ('prune', lambda rt, n: rt.prune(n)),
    ('remove_subtree', lambda rt, n: rt.remove_subtree(n)),
    ('subtree', lambda rt, n: rt.subtree(n)),
    ('subdivide', lambda rt, n: rt.subdivide(n, (1, 1))),
    ('insert_child', lambda rt, n: rt.insert_child(n, 0, proportion=1)),
]


def _outcome(call, node):
    """Run ``call`` on a fresh tree and return a comparable outcome.

    Returns ``('raised', ExceptionType, message-with-the-id-blanked)`` or
    ``('returned', None, None)``. The id is blanked out of the message so that
    two different absent ids compare equal on everything except the number.
    """
    rt = _rt()
    try:
        call(rt, node)
    except Exception as exc:  # noqa: BLE001 - the type is the thing under test
        return ('raised', type(exc), str(exc).replace(str(node), '<id>'))
    return ('returned', None, None)


class TestUnaddressableIdMatchesAbsentId:
    """The negative case and the positive-but-absent case must not diverge."""

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    @pytest.mark.parametrize('name,call', VERBS, ids=[v[0] for v in VERBS])
    def test_verb_outcome_matches_the_control(self, name, call, bad):
        assert _outcome(call, bad) == _outcome(call, ABSENT)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    @pytest.mark.parametrize('name,call', VERBS, ids=[v[0] for v in VERBS])
    def test_verb_never_leaks_an_arithmetic_error(self, name, call, bad):
        """OverflowError is an ArithmeticError, so this excludes it by type."""
        kind, exc_type, _ = _outcome(call, bad)
        if kind == 'raised':
            assert not issubclass(exc_type, ArithmeticError), (
                f'{name} leaked {exc_type.__name__} for node id {bad}'
            )


class TestDocumentedValueError:
    """`make_rest`/`make_sounding`/`insert_child` document ValueError. Honour it."""

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_make_rest_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().make_rest(bad)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_make_sounding_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().make_sounding(bad)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_insert_child_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().insert_child(bad, 0, proportion=1)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_remove_subtree_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().remove_subtree(bad)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_subtree_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().subtree(bad)

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_subdivide_raises_value_error(self, bad):
        with pytest.raises(ValueError):
            _rt().subdivide(bad, (1, 1))


class TestMembership:
    """``in`` answers False; it does not raise."""

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_rhythm_tree_contains(self, bad):
        assert (bad in _rt()) is False

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_node_view_contains(self, bad):
        assert (bad in _rt().nodes) is False

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_plain_tree_contains(self, bad):
        assert (bad in Tree(1, (1, 1))) is False

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_graph_contains(self, bad):
        g = Graph()
        g.add_node(label='a')
        assert (bad in g) is False

    def test_real_nodes_are_still_found(self):
        rt = _rt()
        assert rt.root in rt
        assert all(n in rt for n in rt.nodes)
        assert (ABSENT in rt) is False


class TestSubscriptAndTraversalMatchTheControl:
    """The readers a caller reaches next answer the same for both absent ids."""

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_getitem_raises_key_error_like_the_control(self, bad):
        rt = _rt()
        with pytest.raises(KeyError):
            rt[ABSENT]
        with pytest.raises(KeyError):
            rt[bad]

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_node_view_getitem_raises_index_error_like_the_control(self, bad):
        rt = _rt()
        with pytest.raises(IndexError):
            rt.nodes[ABSENT]
        with pytest.raises(IndexError):
            rt.nodes[bad]

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    @pytest.mark.parametrize('reader', [
        'parent', 'successors', 'predecessors', 'neighbors',
        'out_degree', 'in_degree',
    ])
    def test_reader_matches_the_control(self, reader, bad):
        rt = _rt()
        assert getattr(rt, reader)(bad) == getattr(rt, reader)(ABSENT)


class TestNonIntegersStillRaiseTypeError:
    """Scope guard: this fix is about integers, and only about integers."""

    @pytest.mark.parametrize('bad', ['x', 1.5, None])
    def test_wrong_type_is_a_type_error(self, bad):
        with pytest.raises(TypeError):
            bad in _rt()
        with pytest.raises(TypeError):
            _rt().make_rest(bad)

    def test_bool_is_an_int_and_still_addresses_node_one(self):
        rt = _rt()
        assert (True in rt) is True
        assert rt[True] == rt[1]


class TestSubclassAddressSpaceIsNotHijacked:
    """The internal guard is index-level, not ``in self``.

    A :class:`Lattice` redefines ``__contains__`` over COORDINATE TUPLES, then
    resolves a coordinate to an integer node id and forwards it to
    ``GraphCore.__getitem__``. Writing that guard as ``node not in self`` sends
    the integer back through the coordinate test, which answers False for every
    real node -- so lattice lookup raises ``KeyError`` for data that is present.
    The guard therefore calls ``_has_node``, which always means "a live
    rustworkx index".
    """

    def test_coordinate_lookup_still_reaches_node_data(self):
        from klotho.tonos import ToneLattice

        lat = ToneLattice(dimensionality=2, resolution=[2, 2])
        coord = lat.coords[0]
        assert 'ratio' in lat[coord]

    def test_the_two_address_spaces_disagree_on_purpose(self):
        from klotho.tonos import ToneLattice

        lat = ToneLattice(dimensionality=2, resolution=[2, 2])
        node_id = lat.get_node(lat.coords[0])
        assert lat._has_node(node_id) is True      # index-level: present
        assert (node_id in lat) is False           # coordinate-level: not a coord

    def test_unaddressable_index_is_still_absent_at_index_level(self):
        from klotho.tonos import ToneLattice

        lat = ToneLattice(dimensionality=2, resolution=[2, 2])
        for bad in UNADDRESSABLE:
            assert lat._has_node(bad) is False


class TestEdgeEndpointsLeakTheSameWay:
    """Same defect, edge-addressed: an unaddressable ENDPOINT names no edge.

    Not among the seven node-addressed verbs the row lists, but it is the same
    binding, the same conversion, and the same one-line predicate. Controls
    again: ``has_edge(999, 0)`` is False and ``remove_edge(999, 0)`` raises
    rustworkx's ``NoEdgeBetweenNodes``.
    """

    @staticmethod
    def _g():
        g = Graph()
        a = g.add_node(label='a')
        b = g.add_node(label='b')
        g.add_edge(a, b)
        return g

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_has_edge_is_false_not_overflow(self, bad):
        g = self._g()
        assert g.has_edge(bad, 0) is False
        assert g.has_edge(0, bad) is False
        assert g.has_edge(ABSENT, 0) is False

    @pytest.mark.parametrize('bad', UNADDRESSABLE)
    def test_remove_edge_matches_the_control(self, bad):
        import rustworkx as rx

        for endpoints in [(bad, 0), (0, bad), (ABSENT, 0)]:
            with pytest.raises(rx.NoEdgeBetweenNodes):
                self._g().remove_edge(*endpoints)
