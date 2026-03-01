from klotho.thetos import ParameterTree


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


def _assert_parameter_tree_equivalent(actual, expected):
    a_path_to_node, a_node_to_path = _maps_by_path(actual)
    e_path_to_node, e_node_to_path = _maps_by_path(expected)

    assert set(a_path_to_node.keys()) == set(e_path_to_node.keys())
    assert set(actual.pfields) == set(expected.pfields)
    assert set(actual.mfields) == set(expected.mfields)

    for path in a_path_to_node:
        a_node = a_path_to_node[path]
        e_node = e_path_to_node[path]

        assert dict(actual.nodes[a_node]) == dict(expected.nodes[e_node])
        assert actual.items(a_node) == expected.items(e_node)
        assert actual.get_instrument(a_node) == expected.get_instrument(e_node)

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


def test_parameter_tree_graft_replace_preserves_structure_and_effective_fields():
    source = ParameterTree(1, (11, (12, ("a", "b", "c")), 13))
    source.set_pfields(_node_at_path(source, tuple()), tempo=120, amp=0.5)
    source.set_mfields(_node_at_path(source, (1,)), articulation="tenuto")
    source.set_instrument(_node_at_path(source, (1,)), {"name": "pad", "channel": 2})

    subtree = ParameterTree(9, (31, (32, ("u", "v", "w")), 33))
    subtree.set_pfields(_node_at_path(subtree, tuple()), cutoff=1800)
    subtree.set_pfields(_node_at_path(subtree, (1, 1)), resonance=0.7)
    subtree.set_mfields(_node_at_path(subtree, (1,)), region="upper")
    subtree.set_instrument(_node_at_path(subtree, tuple()), {"name": "lead", "channel": 3})

    source.graft_subtree(_node_at_path(source, (2,)), subtree, mode="replace")

    expected = ParameterTree(1, (11, (12, ("a", "b", "c")), (9, (31, (32, ("u", "v", "w")), 33))))
    expected.set_pfields(_node_at_path(expected, tuple()), tempo=120, amp=0.5)
    expected.set_mfields(_node_at_path(expected, (1,)), articulation="tenuto")
    expected.set_instrument(_node_at_path(expected, (1,)), {"name": "pad", "channel": 2})
    expected.set_pfields(_node_at_path(expected, (2,)), cutoff=1800)
    expected.set_pfields(_node_at_path(expected, (2, 1, 1)), resonance=0.7)
    expected.set_mfields(_node_at_path(expected, (2, 1)), region="upper")
    expected.set_instrument(_node_at_path(expected, (2,)), {"name": "lead", "channel": 3})

    _assert_parameter_tree_equivalent(source, expected)


def test_parameter_tree_graft_adopt_preserves_structure_and_effective_fields():
    source = ParameterTree(10, (1, 2, 3))
    source.set_pfields(_node_at_path(source, tuple()), tempo=98)
    source.set_pfields(_node_at_path(source, (1,)), amp=0.35)
    source.set_mfields(_node_at_path(source, (1,)), role="target")
    source.set_instrument(_node_at_path(source, (1,)), {"name": "bass", "channel": 4})

    subtree = ParameterTree(20, (21, 22, 23))
    subtree.set_pfields(_node_at_path(subtree, tuple()), cutoff=900)
    subtree.set_mfields(_node_at_path(subtree, (0,)), region="low")

    source.graft_subtree(_node_at_path(source, (1,)), subtree, mode="adopt")

    expected = ParameterTree(10, (1, (2, (21, 22, 23)), 3))
    expected.set_pfields(_node_at_path(expected, tuple()), tempo=98)
    expected.set_pfields(_node_at_path(expected, (1,)), amp=0.35)
    expected._meta["pfields"].add("cutoff")
    expected.set_mfields(_node_at_path(expected, (1,)), role="target")
    expected.set_mfields(_node_at_path(expected, (1, 0)), region="low")
    expected.set_instrument(_node_at_path(expected, (1,)), {"name": "bass", "channel": 4})

    _assert_parameter_tree_equivalent(source, expected)


def test_parameter_tree_add_child_invalidates_effective_cache_and_updates_structure():
    source = ParameterTree(1, (11, 12, 13))
    source.set_pfields(_node_at_path(source, tuple()), tempo=120)
    _ = source.get_pfield(_node_at_path(source, (2,)), "tempo")

    target = _node_at_path(source, (1,))
    source.add_child(target, gain=0.8)
    source.add_child(target, pan=0.25)
    children = source.successors(target)
    assert len(children) == 2
    assert source.nodes[children[0]].get("gain") == 0.8
    assert source.nodes[children[1]].get("pan") == 0.25
    assert source.get_pfield(children[0], "tempo") == 120
    assert source.get_pfield(children[1], "tempo") == 120


def test_parameter_tree_replace_node_updates_structure_and_data():
    source = ParameterTree(1, (11, 12, 13))
    source.set_pfields(_node_at_path(source, tuple()), tempo=100)
    source.replace_node(_node_at_path(source, (2,)), pitch=64, velocity=90)

    expected = ParameterTree(1, (11, 12, 13))
    expected.set_pfields(_node_at_path(expected, tuple()), tempo=100)
    expected._graph[_node_at_path(expected, (2,))].update({"pitch": 64, "velocity": 90})

    _assert_parameter_tree_equivalent(source, expected)

