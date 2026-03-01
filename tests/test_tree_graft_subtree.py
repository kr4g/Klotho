import pytest
import random

from klotho.topos.graphs.trees import Tree


def _label(tree, node):
    return tree[node]["label"]


def _node_by_label(tree, label):
    matches = [node for node in tree.nodes if _label(tree, node) == label]
    assert len(matches) == 1
    return matches[0]


def _label_structure(tree, node=None):
    if node is None:
        node = tree.root
    children = tree.successors(node)
    value = _label(tree, node)
    if not children:
        return value
    return (value, tuple(_label_structure(tree, child) for child in children))


def _tree_from_structure(structure):
    if isinstance(structure, tuple) and len(structure) == 2:
        return Tree(structure[0], structure[1])
    return Tree(structure, tuple())


def _leaf_labels_from_structure(structure):
    if not (isinstance(structure, tuple) and len(structure) == 2):
        return (structure,)
    leaves = []
    for child in structure[1]:
        leaves.extend(_leaf_labels_from_structure(child))
    return tuple(leaves)


def _replace_leaf_in_structure(source_structure, target_label, replacement_structure):
    found = False

    def walk(node):
        nonlocal found
        if not (isinstance(node, tuple) and len(node) == 2):
            if node == target_label:
                if found:
                    raise AssertionError(f"Duplicate target leaf label: {target_label}")
                found = True
                return replacement_structure
            return node

        label, children = node
        return (label, tuple(walk(child) for child in children))

    result = walk(source_structure)
    if not found:
        raise AssertionError(f"Target leaf label not found: {target_label}")
    return result


def _adopt_leaf_in_structure(source_structure, target_label, subtree_structure):
    if isinstance(subtree_structure, tuple) and len(subtree_structure) == 2:
        adopted_children = subtree_structure[1]
    else:
        adopted_children = tuple()

    found = False

    def walk(node):
        nonlocal found
        if not (isinstance(node, tuple) and len(node) == 2):
            if node == target_label:
                if found:
                    raise AssertionError(f"Duplicate target leaf label: {target_label}")
                found = True
                return (node, adopted_children)
            return node

        label, children = node
        return (label, tuple(walk(child) for child in children))

    result = walk(source_structure)
    if not found:
        raise AssertionError(f"Target leaf label not found: {target_label}")
    return result


def _assert_structurally_equivalent(actual, expected):
    actual_labels = {_label(actual, node) for node in actual.nodes}
    expected_labels = {_label(expected, node) for node in expected.nodes}
    assert actual_labels == expected_labels

    for label in actual_labels:
        a_node = _node_by_label(actual, label)
        e_node = _node_by_label(expected, label)

        a_parent = actual.parent(a_node)
        e_parent = expected.parent(e_node)
        a_parent_label = None if a_parent is None else _label(actual, a_parent)
        e_parent_label = None if e_parent is None else _label(expected, e_parent)
        assert a_parent_label == e_parent_label

        a_successors = tuple(_label(actual, n) for n in actual.successors(a_node))
        e_successors = tuple(_label(expected, n) for n in expected.successors(e_node))
        assert a_successors == e_successors

        a_descendants = {_label(actual, n) for n in actual.descendants(a_node)}
        e_descendants = {_label(expected, n) for n in expected.descendants(e_node)}
        assert a_descendants == e_descendants

        a_subtree_leaves = tuple(_label(actual, n) for n in actual.subtree_leaves(a_node))
        e_subtree_leaves = tuple(_label(expected, n) for n in expected.subtree_leaves(e_node))
        assert a_subtree_leaves == e_subtree_leaves

    a_leaf_nodes = tuple(_label(actual, n) for n in actual.leaf_nodes)
    e_leaf_nodes = tuple(_label(expected, n) for n in expected.leaf_nodes)
    assert a_leaf_nodes == e_leaf_nodes

    assert _label_structure(actual) == _label_structure(expected)


SOURCE_STRUCTURES = [
    ("R", ("A", "B", "C")),
    ("R", (("N1", ("A", "B")), "C", ("N2", ("D", "E", "F")))),
    ("R", (("L", (("L1", ("A", "B")), "C")), ("M", ("D", ("M2", ("E", "F")))), "G")),
    ("R", (("P", (("Q", (("S", ("A", "B")), "C")), "D")), "E", ("T", ("F", "G")))),
    (
        "R0",
        (
            ("R1", ("A0", ("R2", ("A1", "A2")), "A3")),
            ("R3", (("R4", ("A4", "A5")), "A6")),
            "A7",
            ("R5", ("A8", "A9")),
        ),
    ),
    (
        "ROOT",
        (
            ("L0", (("L1", ("LA", "LB", "LC")), ("L2", ("LD", "LE")))),
            "LF",
            ("M0", ("LG", ("M1", ("LH", ("M2", ("LI", "LJ")))))),
            "LK",
        ),
    ),
]


SUBTREE_STRUCTURES = [
    ("X", ("Y", "Z")),
    ("X", (("X1", ("Y1", "Y2")), "Z1", ("X2", ("Z2", "Z3")))),
    "Xleaf",
    ("UX", (("UY", ("U1", "U2", "U3")), ("UZ", ("U4", ("U5", "U6"))))),
    ("VX", ("V1", ("V2", ("V3", ("V4", "V5"))))),
]


def _replace_case_params():
    params = []
    for source_structure in SOURCE_STRUCTURES:
        source_leaves = _leaf_labels_from_structure(source_structure)
        for subtree_structure in SUBTREE_STRUCTURES:
            for target_leaf in source_leaves:
                params.append((source_structure, subtree_structure, target_leaf))
    return params


@pytest.mark.parametrize(
    "source_structure,subtree_structure,target_leaf",
    _replace_case_params(),
)
def test_graft_replace_matches_hand_built_expected_structure(source_structure, subtree_structure, target_leaf):
    source = _tree_from_structure(source_structure)
    subtree = _tree_from_structure(subtree_structure)

    source.graft_subtree(_node_by_label(source, target_leaf), subtree, mode="replace")

    expected_structure = _replace_leaf_in_structure(source_structure, target_leaf, subtree_structure)
    expected = _tree_from_structure(expected_structure)
    _assert_structurally_equivalent(source, expected)


@pytest.mark.parametrize(
    "source_structure,subtree_structure,target_leaf",
    _replace_case_params(),
)
def test_graft_adopt_matches_hand_built_expected_structure(source_structure, subtree_structure, target_leaf):
    source = _tree_from_structure(source_structure)
    subtree = _tree_from_structure(subtree_structure)

    source.graft_subtree(_node_by_label(source, target_leaf), subtree, mode="adopt")

    expected_structure = _adopt_leaf_in_structure(source_structure, target_leaf, subtree_structure)
    expected = _tree_from_structure(expected_structure)
    _assert_structurally_equivalent(source, expected)


def test_graft_replace_keeps_leaf_traversal_stable_around_deep_insertion():
    source = Tree("R", ("A", "B", "C"))
    subtree = Tree("X", (("X1", ("Y", "Z")), "W"))

    source.graft_subtree(_node_by_label(source, "B"), subtree, mode="replace")

    leaf_labels = tuple(_label(source, node) for node in source.leaf_nodes)
    assert leaf_labels == ("A", "Y", "Z", "W", "C")


def test_graft_replace_works_when_target_is_root_leaf():
    source = Tree("ROOT", tuple())
    subtree = Tree("X", (("Y", ("Y1", "Y2")), "Z"))

    source.graft_subtree(source.root, subtree, mode="replace")

    expected = Tree("X", (("Y", ("Y1", "Y2")), "Z"))
    _assert_structurally_equivalent(source, expected)


def test_graft_adopt_works_when_target_is_root_leaf():
    source = Tree("ROOT", tuple())
    subtree = Tree("X", (("Y", ("Y1", "Y2")), "Z"))

    source.graft_subtree(source.root, subtree, mode="adopt")

    expected = Tree("ROOT", (("Y", ("Y1", "Y2")), "Z"))
    _assert_structurally_equivalent(source, expected)


def test_graft_adopt_with_leaf_subtree_is_noop_on_structure():
    source_structure = ("R", (("N1", ("A", "B")), "C", ("N2", ("D", "E"))))
    source = _tree_from_structure(source_structure)
    subtree = _tree_from_structure("Sleaf")

    source.graft_subtree(_node_by_label(source, "C"), subtree, mode="adopt")

    expected = _tree_from_structure(source_structure)
    _assert_structurally_equivalent(source, expected)


def test_graft_replace_sequential_operations_match_hand_built_result():
    source = _tree_from_structure(("R", ("A", "B", "C", "D")))
    subtree_one = _tree_from_structure(("X", ("Y", "Z")))
    subtree_two = _tree_from_structure(("M", (("N", ("O", "P")), "Q")))

    source.graft_subtree(_node_by_label(source, "B"), subtree_one, mode="replace")
    source.graft_subtree(_node_by_label(source, "D"), subtree_two, mode="replace")

    expected = _tree_from_structure(("R", ("A", ("X", ("Y", "Z")), "C", ("M", (("N", ("O", "P")), "Q")))))
    _assert_structurally_equivalent(source, expected)


def test_graft_rejects_non_leaf_target():
    source = Tree("R", (("N", ("A", "B")), "C"))
    subtree = Tree("X", ("Y", "Z"))

    with pytest.raises(ValueError, match="not a leaf node"):
        source.graft_subtree(_node_by_label(source, "N"), subtree, mode="replace")


def test_graft_rejects_invalid_mode():
    source = Tree("R", ("A", "B"))
    subtree = Tree("X", ("Y",))

    with pytest.raises(ValueError, match="Invalid mode"):
        source.graft_subtree(_node_by_label(source, "A"), subtree, mode="append")


def test_graft_rejects_non_tree_subtree():
    source = Tree("R", ("A", "B"))

    with pytest.raises(TypeError, match="subtree must be a Tree instance"):
        source.graft_subtree(_node_by_label(source, "A"), {"root": "X"}, mode="replace")


def test_add_child_updates_structure_and_group():
    source = Tree("R", ("A", "B"))
    source.add_child(_node_by_label(source, "A"), label="X")

    expected = Tree("R", (("A", ("X",)), "B"))
    _assert_structurally_equivalent(source, expected)


def test_replace_node_updates_structure_and_group():
    source = Tree("R", ("A", "B"))
    source.replace_node(_node_by_label(source, "B"), label="X")

    expected = Tree("R", ("A", "X"))
    _assert_structurally_equivalent(source, expected)


def test_move_subtree_updates_structure():
    source = Tree("R", (("A", ("B", "C")), "D"))
    source.move_subtree(_node_by_label(source, "C"), _node_by_label(source, "D"))

    expected = Tree("R", (("A", ("B",)), ("D", ("C",))))
    _assert_structurally_equivalent(source, expected)


def _generate_random_structure(rng, prefix, max_depth=4, max_branching=4, force_internal=False):
    counter = {"value": 0}

    def new_label():
        label = f"{prefix}_{counter['value']}"
        counter["value"] += 1
        return label

    def build(depth, must_internal):
        label = new_label()
        if depth >= max_depth:
            return label

        if must_internal:
            child_count = rng.randint(2, max_branching)
        else:
            child_count = 0 if rng.random() < 0.35 else rng.randint(2, max_branching)

        if child_count == 0:
            return label

        children = tuple(build(depth + 1, False) for _ in range(child_count))
        return (label, children)

    return build(0, force_internal)


def _count_nodes(structure):
    if not (isinstance(structure, tuple) and len(structure) == 2):
        return 1
    return 1 + sum(_count_nodes(child) for child in structure[1])


@pytest.mark.parametrize("seed", list(range(20)))
def test_graft_replace_random_oracle_equivalence(seed):
    rng = random.Random(seed)
    source_structure = _generate_random_structure(rng, "S", max_depth=4, max_branching=4, force_internal=True)
    subtree_structure = _generate_random_structure(rng, "T", max_depth=3, max_branching=4, force_internal=False)
    target_leaf = rng.choice(_leaf_labels_from_structure(source_structure))

    source = _tree_from_structure(source_structure)
    subtree = _tree_from_structure(subtree_structure)
    source_before_nodes = source.number_of_nodes()
    subtree_nodes = subtree.number_of_nodes()

    source.graft_subtree(_node_by_label(source, target_leaf), subtree, mode="replace")

    expected_structure = _replace_leaf_in_structure(source_structure, target_leaf, subtree_structure)
    expected = _tree_from_structure(expected_structure)
    _assert_structurally_equivalent(source, expected)

    assert source.number_of_nodes() == source_before_nodes + subtree_nodes - 1
    assert source.number_of_edges() == source.number_of_nodes() - 1

    if isinstance(subtree_structure, tuple) and len(subtree_structure) == 2:
        subtree_root_label = subtree_structure[0]
        if subtree_root_label != target_leaf:
            result_labels = {_label(source, node) for node in source.nodes}
            assert target_leaf not in result_labels


@pytest.mark.parametrize("seed", list(range(20)))
def test_graft_adopt_random_oracle_equivalence(seed):
    rng = random.Random(1000 + seed)
    source_structure = _generate_random_structure(rng, "S", max_depth=4, max_branching=4, force_internal=True)
    subtree_structure = _generate_random_structure(rng, "T", max_depth=3, max_branching=4, force_internal=False)
    target_leaf = rng.choice(_leaf_labels_from_structure(source_structure))

    source = _tree_from_structure(source_structure)
    subtree = _tree_from_structure(subtree_structure)
    source_before_nodes = source.number_of_nodes()
    subtree_nodes = subtree.number_of_nodes()

    source.graft_subtree(_node_by_label(source, target_leaf), subtree, mode="adopt")

    expected_structure = _adopt_leaf_in_structure(source_structure, target_leaf, subtree_structure)
    expected = _tree_from_structure(expected_structure)
    _assert_structurally_equivalent(source, expected)

    assert source.number_of_nodes() == source_before_nodes + subtree_nodes - 1
    assert source.number_of_edges() == source.number_of_nodes() - 1
    result_labels = {_label(source, node) for node in source.nodes}
    assert target_leaf in result_labels
