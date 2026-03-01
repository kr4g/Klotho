from klotho.chronos import RhythmTree


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


def _assert_tree_data_equivalent(actual, expected):
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
    assert actual.subdivisions == expected.subdivisions
    assert actual.durations == expected.durations
    assert actual.onsets == expected.onsets


def test_rhythm_tree_graft_replace_matches_expected_structure_and_metrics():
    source = RhythmTree(span=1, meas="4/4", subdivisions=((2, (1, 1, 1)), 3, 4))
    subtree = RhythmTree(span=1, meas="1/1", subdivisions=(5, 6, 7))

    source.graft_subtree(_node_at_path(source, (0, 2)), subtree, mode="replace")

    expected = RhythmTree(
        span=1,
        meas="4/4",
        subdivisions=((2, (1, 1, (1, (5, 6, 7)))), 3, 4),
    )
    _assert_tree_data_equivalent(source, expected)


def test_rhythm_tree_graft_adopt_matches_expected_structure_and_metrics():
    source = RhythmTree(span=1, meas="4/4", subdivisions=((2, (1, 1, 1)), 3, 4))
    subtree = RhythmTree(span=1, meas="1/1", subdivisions=(7, 8, 9))

    source.graft_subtree(_node_at_path(source, (1,)), subtree, mode="adopt")

    expected = RhythmTree(
        span=1,
        meas="4/4",
        subdivisions=((2, (1, 1, 1)), (3, (7, 8, 9)), 4),
    )
    _assert_tree_data_equivalent(source, expected)


def test_rhythm_tree_add_child_recomputes_scoped_metrics():
    source = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 1))
    target = _node_at_path(source, (1,))
    source.add_child(target, proportion=2)
    source.add_child(target, proportion=3)

    expected = RhythmTree(span=1, meas="4/4", subdivisions=(1, (1, (2, 3)), 1))
    _assert_tree_data_equivalent(source, expected)


def test_rhythm_tree_replace_node_recomputes_scoped_metrics():
    source = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 3, 1))
    source.replace_node(_node_at_path(source, (2,)), proportion=5)

    expected = RhythmTree(span=1, meas="4/4", subdivisions=(1, 1, 5, 1))
    _assert_tree_data_equivalent(source, expected)

