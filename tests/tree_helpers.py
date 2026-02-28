"""Shared helpers for tree-oriented tests. Full structural equivalence: all nodes, traversals."""
from fractions import Fraction

from klotho.topos.graphs import Group


def _group_to_json(g):
    if isinstance(g, Group):
        return {"D": g.D, "S": [_group_to_json(x) for x in g.S]}
    return g


def _node_data_tuple(g, node):
    d = g[node]
    return (d.get("proportion"), Fraction(d["metric_duration"]), Fraction(d["metric_onset"]))


def _norm_tuple(x):
    p, md, mo = x[0], x[1], x[2]
    return (p, Fraction(md), Fraction(mo))


def _struct_tuple(exp_struct):
    return _norm_tuple(exp_struct[:3])


def _struct_descendants(exp_struct):
    descendants = []
    for child in exp_struct[3]:
        descendants.append(_struct_tuple(child))
        descendants.extend(_struct_descendants(child))
    return descendants


def _struct_leaves(exp_struct):
    children = exp_struct[3]
    if not children:
        return [_struct_tuple(exp_struct)]
    leaves = []
    for child in children:
        leaves.extend(_struct_leaves(child))
    return leaves


def assert_rt_matches_expected(rt, expected, strict_ids=False):
    """Assert rt matches expected structure captured from remote.
    Uses Fraction for duration/onset comparison so '1/1' and '1' match."""
    exp = expected
    assert len(list(rt.nodes)) == exp["num_nodes"], "Node count mismatch"
    assert rt.depth == exp["depth"], "Depth mismatch"
    assert rt.span == exp["span"], "Span mismatch"
    assert str(rt.meas) == exp["meas"], "Meas mismatch"
    assert [str(d) for d in rt.durations] == exp["durations"], "Durations mismatch"
    assert [str(o) for o in rt.onsets] == exp["onsets"], "Onsets mismatch"

    for d in range(rt.depth + 1):
        actual_vals = {_node_data_tuple(rt, n) for n in rt.at_depth(d)}
        expected_vals = {_norm_tuple(x) for x in exp["at_depth"][d]}
        assert actual_vals == expected_vals, f"at_depth({d}) mismatch"

    def check_structure(node, exp_struct):
        p, md, mo, children = exp_struct[0], exp_struct[1], exp_struct[2], exp_struct[3]
        assert rt[node].get("proportion") == p, f"Structure node {node} proportion"
        assert Fraction(rt[node]["metric_duration"]) == Fraction(md), f"Structure node {node} metric_duration"
        assert Fraction(rt[node]["metric_onset"]) == Fraction(mo), f"Structure node {node} metric_onset"
        actual_desc = sorted(_node_data_tuple(rt, x) for x in rt.descendants(node))
        expected_desc = sorted(_struct_descendants(exp_struct))
        assert actual_desc == expected_desc, f"Structure node {node} descendants"
        actual_leaves = sorted(_node_data_tuple(rt, x) for x in rt.subtree_leaves(node))
        expected_leaves = sorted(_struct_leaves(exp_struct))
        assert actual_leaves == expected_leaves, f"Structure node {node} subtree_leaves"
        succs = list(rt.successors(node))
        assert len(succs) == len(children), f"Structure node {node} children count"
        for c, c_exp in zip(succs, children):
            check_structure(c, c_exp)

    check_structure(rt.root, exp["structure"])

    if strict_ids:
        assert list(rt.leaf_nodes) == exp["leaf_nodes"], "Leaf nodes mismatch"
        for n in rt.nodes:
            nd = exp["node_data"][str(n)]
            assert rt[n].get("proportion") == nd["proportion"], f"Node {n} proportion"
            assert Fraction(rt[n]["metric_duration"]) == Fraction(nd["metric_duration"]), f"Node {n} metric_duration"
            assert Fraction(rt[n]["metric_onset"]) == Fraction(nd["metric_onset"]), f"Node {n} metric_onset"
            assert list(rt.successors(n)) == exp["successors"][str(n)], f"Node {n} successors"
            actual_desc = {_node_data_tuple(rt, x) for x in rt.descendants(n)}
            expected_desc = {_norm_tuple(x) for x in exp["descendants"][str(n)]}
            assert actual_desc == expected_desc, f"Node {n} descendants"
            actual_leaves = {_node_data_tuple(rt, x) for x in rt.subtree_leaves(n)}
            expected_leaves = {_norm_tuple(x) for x in exp["subtree_leaves"][str(n)]}
            assert actual_leaves == expected_leaves, f"Node {n} subtree_leaves"

    actual_group = _group_to_json(rt.group)
    assert actual_group == exp["group"], f"Group mismatch: {actual_group} != {exp['group']}"


def assert_rt_pt_structurally_matched(rt, pt):
    """Assert CompositionalUnit's RT and PT have identical structure (nodes, successors, depth, leaf_nodes, etc.)."""
    assert set(rt.nodes) == set(pt.nodes), "RT/PT node set mismatch"
    assert rt.depth == pt.depth, "RT/PT depth mismatch"
    assert rt.leaf_nodes == pt.leaf_nodes, "RT/PT leaf_nodes mismatch"
    for n in rt.nodes:
        assert list(rt.successors(n)) == list(pt.successors(n)), f"RT/PT successors({n}) mismatch"
        assert set(rt.descendants(n)) == set(pt.descendants(n)), f"RT/PT descendants({n}) mismatch"
        assert rt.subtree_leaves(n) == pt.subtree_leaves(n), f"RT/PT subtree_leaves({n}) mismatch"
    for d in range(rt.depth + 1):
        assert set(rt.at_depth(d)) == set(pt.at_depth(d)), f"RT/PT at_depth({d}) mismatch"


def assert_rt_structurally_equivalent(a, b):
    """Assert two RhythmTrees are structurally identical: nodes, successors, descendants, subtree_leaves, at_depth."""
    assert len(list(a.nodes)) == len(list(b.nodes)), "Node count mismatch"
    assert a.depth == b.depth, "Depth mismatch"
    for d in range(a.depth + 1):
        a_vals = {_node_data_tuple(a, n) for n in a.at_depth(d)}
        b_vals = {_node_data_tuple(b, n) for n in b.at_depth(d)}
        assert a_vals == b_vals, f"at_depth({d}) mismatch"

    def _dfs(ta, tb, na, nb):
        assert _node_data_tuple(ta, na) == _node_data_tuple(tb, nb)
        sa = list(ta.successors(na))
        sb = list(tb.successors(nb))
        assert len(sa) == len(sb)
        for ca, cb in zip(sa, sb):
            _dfs(ta, tb, ca, cb)
        da = {_node_data_tuple(ta, n) for n in ta.descendants(na)}
        db = {_node_data_tuple(tb, n) for n in tb.descendants(nb)}
        assert da == db
        la = {_node_data_tuple(ta, n) for n in ta.subtree_leaves(na)}
        lb = {_node_data_tuple(tb, n) for n in tb.subtree_leaves(nb)}
        assert la == lb

    _dfs(a, b, a.root, b.root)
