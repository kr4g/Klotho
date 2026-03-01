from fractions import Fraction

from klotho.tonos import HarmonicTree


def _node_at_path(tree, path):
    node = tree.root
    for idx in path:
        node = tree.successors(node)[idx]
    return node


def _maps_by_path(tree):
    path_to_node = {}
    node_to_path = {}

    def walk(node, path):
        path_to_node[path] = node
        node_to_path[node] = path
        for idx, child in enumerate(tree.successors(node)):
            walk(child, path + (idx,))

    walk(tree.root, tuple())
    return path_to_node, node_to_path


def _assert_harmonic_tree_equivalent(actual, expected):
    a_path_to_node, a_node_to_path = _maps_by_path(actual)
    e_path_to_node, e_node_to_path = _maps_by_path(expected)

    assert set(a_path_to_node.keys()) == set(e_path_to_node.keys())

    for path in a_path_to_node:
        a_node = a_path_to_node[path]
        e_node = e_path_to_node[path]

        assert dict(actual.nodes[a_node]) == dict(expected.nodes[e_node])

        a_parent = actual.parent(a_node)
        e_parent = expected.parent(e_node)
        assert (None if a_parent is None else a_node_to_path[a_parent]) == (
            None if e_parent is None else e_node_to_path[e_parent]
        )

        a_successors = tuple(a_node_to_path[n] for n in actual.successors(a_node))
        e_successors = tuple(e_node_to_path[n] for n in expected.successors(e_node))
        assert a_successors == e_successors

        a_descendants = {a_node_to_path[n] for n in actual.descendants(a_node)}
        e_descendants = {e_node_to_path[n] for n in expected.descendants(e_node)}
        assert a_descendants == e_descendants

        a_subtree_leaves = tuple(a_node_to_path[n] for n in actual.subtree_leaves(a_node))
        e_subtree_leaves = tuple(e_node_to_path[n] for n in expected.subtree_leaves(e_node))
        assert a_subtree_leaves == e_subtree_leaves

    assert tuple(a_node_to_path[n] for n in actual.leaf_nodes) == tuple(e_node_to_path[n] for n in expected.leaf_nodes)
    assert actual.harmonics == expected.harmonics
    assert actual.ratios == expected.ratios


def test_harmonic_tree_graft_replace_recomputes_harmonics_and_ratios():
    source = HarmonicTree(
        root=1,
        children=(3, (5, (7, 9)), 11),
        equave=Fraction(2, 1),
        span=1,
    )
    subtree = HarmonicTree(
        root=13,
        children=(15, 17),
        equave=Fraction(2, 1),
        span=1,
    )

    source.graft_subtree(_node_at_path(source, (1, 1)), subtree, mode="replace")

    expected = HarmonicTree(
        root=1,
        children=(3, (5, (7, (13, (15, 17)))), 11),
        equave=Fraction(2, 1),
        span=1,
    )
    _assert_harmonic_tree_equivalent(source, expected)


def test_harmonic_tree_graft_adopt_recomputes_harmonics_and_ratios():
    source = HarmonicTree(
        root=1,
        children=(3, (5, (7, 9)), 11),
        equave=Fraction(2, 1),
        span=1,
    )
    subtree = HarmonicTree(
        root=13,
        children=(15, 17),
        equave=Fraction(2, 1),
        span=1,
    )

    source.graft_subtree(_node_at_path(source, (0,)), subtree, mode="adopt")

    expected = HarmonicTree(
        root=1,
        children=((3, (15, 17)), (5, (7, 9)), 11),
        equave=Fraction(2, 1),
        span=1,
    )
    _assert_harmonic_tree_equivalent(source, expected)


def test_harmonic_tree_add_child_recomputes_scoped_values():
    source = HarmonicTree(
        root=1,
        children=(3, 5, 7),
        equave=Fraction(2, 1),
        span=1,
    )
    target = _node_at_path(source, (1,))
    source.add_child(target, factor=11)
    source.add_child(target, factor=13)

    expected = HarmonicTree(
        root=1,
        children=(3, (5, (11, 13)), 7),
        equave=Fraction(2, 1),
        span=1,
    )
    _assert_harmonic_tree_equivalent(source, expected)


def test_harmonic_tree_replace_node_recomputes_scoped_values():
    source = HarmonicTree(
        root=1,
        children=(3, (5, (7, 9)), 11),
        equave=Fraction(2, 1),
        span=1,
    )
    source.replace_node(_node_at_path(source, (2,)), factor=13)

    expected = HarmonicTree(
        root=1,
        children=(3, (5, (7, 9)), 13),
        equave=Fraction(2, 1),
        span=1,
    )
    _assert_harmonic_tree_equivalent(source, expected)

