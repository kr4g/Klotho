"""
Tests for RT.subdivide: equivalence with (D S) formalism.
rt.subdivide(leaf, S) should match RT built from equivalent nested structure.
Node IDs may differ between direct build and subdivide; compare by structure.
"""
import pytest
from klotho.chronos import RhythmTree as RT
from tree_helpers import assert_rt_structurally_equivalent


class Test_subdivide_4_2_1_1_first_leaf:
    def test_subdivide_matches_built_structure(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[4, 2, 1, 1])
        rt.subdivide(1, [1, 1, 1])
        expected = RT(subdivisions=[[4, [1, 1, 1]], 2, 1, 1])
        assert rt.durations == expected.durations
        assert rt.onsets == expected.onsets
        assert len(rt.leaf_nodes) == len(expected.leaf_nodes)

    def test_subdivide_all_nodes_and_traversals(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[4, 2, 1, 1])
        rt.subdivide(1, [1, 1, 1])
        expected = RT(subdivisions=[[4, [1, 1, 1]], 2, 1, 1])
        assert_rt_structurally_equivalent(rt, expected)


class Test_subdivide_uniform_4_first_leaf:
    def test_subdivide_matches_built_structure(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[1, 1, 1, 1])
        rt.subdivide(1, [1, 1])
        expected = RT(subdivisions=[[1, [1, 1]], 1, 1, 1])
        assert rt.durations == expected.durations
        assert rt.onsets == expected.onsets
        assert len(rt.leaf_nodes) == len(expected.leaf_nodes)

    def test_subdivide_all_nodes_and_traversals(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[1, 1, 1, 1])
        rt.subdivide(1, [1, 1])
        expected = RT(subdivisions=[[1, [1, 1]], 1, 1, 1])
        assert_rt_structurally_equivalent(rt, expected)


class Test_subdivide_nested_inner_leaf:
    def test_subdivide_matches_built_structure(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[[4, [1, 1, 1]], 2, 1, 1])
        rt.subdivide(2, [1, 1])
        expected = RT(subdivisions=[[4, [[1, [1, 1]], 1, 1]], 2, 1, 1])
        assert rt.durations == expected.durations
        assert rt.onsets == expected.onsets
        assert len(rt.leaf_nodes) == len(expected.leaf_nodes)

    def test_subdivide_all_nodes_and_traversals(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=[[4, [1, 1, 1]], 2, 1, 1])
        rt.subdivide(2, [1, 1])
        expected = RT(subdivisions=[[4, [[1, [1, 1]], 1, 1]], 2, 1, 1])
        assert_rt_structurally_equivalent(rt, expected)


class Test_subdivide_leaf_order:
    def test_subdivide_preserves_left_to_right_leaf_order(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=(4, 2, 1, 1))
        leaf1 = rt.leaf_nodes[0]
        rt.subdivide(leaf1, (1, 1, 1))
        expected = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        leaf_durations = tuple(rt[n]["metric_duration"] for n in rt.leaf_nodes)
        expected_durations = tuple(expected[n]["metric_duration"] for n in expected.leaf_nodes)
        assert leaf_durations == expected_durations
        assert rt.onsets == expected.onsets

    def test_subdivide_leaf_order_all_nodes_and_traversals(self):
        if not hasattr(RT, "subdivide"):
            pytest.skip("subdivide not yet implemented")
        rt = RT(subdivisions=(4, 2, 1, 1))
        leaf1 = rt.leaf_nodes[0]
        rt.subdivide(leaf1, (1, 1, 1))
        expected = RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))
        assert_rt_structurally_equivalent(rt, expected)
