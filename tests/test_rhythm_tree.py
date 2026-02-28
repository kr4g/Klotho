"""Tests for RhythmTree."""
import pytest
from fractions import Fraction
from klotho import RhythmTree as RT
from tree_helpers import assert_rt_matches_expected
from conftest import get_expected_trees

class Test_single_note:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1,))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 2

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 1

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

class Test_uniform_4:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 1, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 5

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 4

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/4'), Fraction('1/4'), Fraction('1/4'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('1/2'), Fraction('3/4'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/4'

class Test_uniform_4_scaled:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(5, 5, 5, 5))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 5

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 4

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/4'), Fraction('1/4'), Fraction('1/4'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('1/2'), Fraction('3/4'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 5

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 5

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 5

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 5

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/4'

class Test_uniform_3:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 4

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 3

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/3'), Fraction('1/3'), Fraction('1/3'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/3'), Fraction('2/3'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/3'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/3'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/3'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/3'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '2/3'

class Test_uniform_5:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 1, 1, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 6

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 5

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/5'), Fraction('1/5'), Fraction('1/5'), Fraction('1/5'), Fraction('1/5'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/5'), Fraction('2/5'), Fraction('3/5'), Fraction('4/5'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4, 5,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/5'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/5'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/5'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/5'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '2/5'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/5'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/5'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/5'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '4/5'

class Test_uniform_7:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 1, 1, 1, 1, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 8

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 7

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/7'), Fraction('1/7'), Fraction('1/7'), Fraction('1/7'), Fraction('1/7'), Fraction('1/7'), Fraction('1/7'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/7'), Fraction('2/7'), Fraction('3/7'), Fraction('4/7'), Fraction('5/7'), Fraction('6/7'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4, 5, 6, 7,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/7'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/7'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/7'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/7'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '2/7'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/7'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/7'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/7'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '4/7'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/7'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '5/7'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/7'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '6/7'

class Test_uniform_13:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 14

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 13

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'), Fraction('1/13'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/13'), Fraction('2/13'), Fraction('3/13'), Fraction('4/13'), Fraction('5/13'), Fraction('6/13'), Fraction('7/13'), Fraction('8/13'), Fraction('9/13'), Fraction('10/13'), Fraction('11/13'), Fraction('12/13'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/13'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/13'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/13'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/13'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '2/13'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/13'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/13'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/13'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '4/13'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/13'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '5/13'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/13'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '6/13'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/13'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '7/13'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/13'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '8/13'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/13'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '9/13'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/13'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '10/13'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/13'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '11/13'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/13'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '12/13'

class Test_weighted_4_2_1_1:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(4, 2, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 5

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 4

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/2'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 2

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/2'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '3/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '7/8'

class Test_weighted_8_4_2_2:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(8, 4, 2, 2))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 5

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 4

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/2'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 8

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 4

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/2'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '3/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 2

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '7/8'

class Test_weighted_7_2_1_1:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(7, 2, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 5

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 4

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('7/11'), Fraction('2/11'), Fraction('1/11'), Fraction('1/11'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('7/11'), Fraction('9/11'), Fraction('10/11'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 7

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '7/11'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 2

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '2/11'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '7/11'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/11'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '9/11'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/11'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '10/11'

class Test_nested_one_level:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((4, (1, 1, 1)), 2, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 8

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 6

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/6'), Fraction('1/6'), Fraction('1/6'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/6'), Fraction('1/3'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 2

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/8'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '3/4'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/8'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '7/8'

class Test_nested_two_levels:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((4, (1, 1, (1, (1, 1)))), 2, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 10

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 7

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/6'), Fraction('1/6'), Fraction('1/12'), Fraction('1/12'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/6'), Fraction('1/3'), Fraction('5/12'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 5, 6, 7, 8, 9,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/12'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/3'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/12'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '5/12'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/4'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/2'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/8'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/4'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/8'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '7/8'

class Test_nested_two_levels_meas1:
    @pytest.fixture
    def rt(self):
        return RT(meas=1, subdivisions=((4, (1, 1, (1, (1, 1)))), 2, 1, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 10

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 7

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/6'), Fraction('1/6'), Fraction('1/12'), Fraction('1/12'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/6'), Fraction('1/3'), Fraction('5/12'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 5, 6, 7, 8, 9,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/12'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/3'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/12'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '5/12'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/4'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/2'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/8'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/4'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/8'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '7/8'

class Test_rests_basic:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, (1, (1, 1)), (1, (1, 1, -1, 1)), (1, (1, 3))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 13

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 9

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/8'), Fraction('1/8'), Fraction('1/16'), Fraction('1/16'), Fraction('-1/16'), Fraction('1/16'), Fraction('1/16'), Fraction('3/16'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('3/8'), Fraction('1/2'), Fraction('9/16'), Fraction('5/8'), Fraction('11/16'), Fraction('3/4'), Fraction('13/16'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 3, 4, 6, 7, 8, 9, 11, 12,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/16'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/2'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/16'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '9/16'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == -1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '-1/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '5/8'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/16'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '11/16'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/4'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '3/4'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/16'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '3/4'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 3

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/16'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '13/16'

class Test_rests_nested:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, (1, (1, (1, (-1, 1)))), (1, (1, 1, -1, 1)), (1, (-1, 2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 16

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 11

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/8'), Fraction('-1/16'), Fraction('1/16'), Fraction('1/16'), Fraction('1/16'), Fraction('-1/16'), Fraction('1/16'), Fraction('-1/16'), Fraction('1/8'), Fraction('1/16'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('3/8'), Fraction('7/16'), Fraction('1/2'), Fraction('9/16'), Fraction('5/8'), Fraction('11/16'), Fraction('3/4'), Fraction('13/16'), Fraction('15/16'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 3, 5, 6, 8, 9, 10, 11, 13, 14, 15,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == -1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '-1/16'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '3/8'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/16'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/16'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/4'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/2'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '1/2'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/16'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '9/16'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == -1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '-1/16'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '5/8'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/16'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '11/16'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/4'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '3/4'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == -1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '-1/16'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '3/4'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 2

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '1/8'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '13/16'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/16'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '15/16'

class Test_rest_group:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, (1, (1, 1)), (-1, (1, 1, 1, 1)), (1, (1, 3))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 13

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 9

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/8'), Fraction('1/8'), Fraction('-1/16'), Fraction('-1/16'), Fraction('-1/16'), Fraction('-1/16'), Fraction('1/16'), Fraction('3/16'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('3/8'), Fraction('1/2'), Fraction('9/16'), Fraction('5/8'), Fraction('11/16'), Fraction('3/4'), Fraction('13/16'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 3, 4, 6, 7, 8, 9, 11, 12,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == -1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '-1/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == -1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '-1/16'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/2'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == -1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '-1/16'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '9/16'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == -1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '-1/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '5/8'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-1/16'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '11/16'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/4'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '3/4'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/16'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '3/4'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 3

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/16'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '13/16'

class Test_rest_leaf:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, (1, (1, 1)), -1, (1, (1, 3))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 9

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 6

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/8'), Fraction('1/8'), Fraction('-1/4'), Fraction('1/16'), Fraction('3/16'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('3/8'), Fraction('1/2'), Fraction('3/4'), Fraction('13/16'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 3, 4, 5, 7, 8,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == -1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '-1/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/4'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '3/4'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/16'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '3/4'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 3

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '3/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '13/16'

class Test_complex_meas1:
    @pytest.fixture
    def rt(self):
        return RT(meas=1, subdivisions=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 21

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 14

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/16'), Fraction('-1/24'), Fraction('1/24'), Fraction('1/24'), Fraction('1/16'), Fraction('-1/8'), Fraction('1/32'), Fraction('1/32'), Fraction('1/16'), Fraction('-1/16'), Fraction('1/16'), Fraction('1/16'), Fraction('5/24'), Fraction('5/48'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/16'), Fraction('5/48'), Fraction('7/48'), Fraction('3/16'), Fraction('1/4'), Fraction('3/8'), Fraction('13/32'), Fraction('7/16'), Fraction('1/2'), Fraction('9/16'), Fraction('5/8'), Fraction('11/16'), Fraction('43/48'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '3/16'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/16'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/16'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '-1/24'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/16'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/24'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '5/48'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/24'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/48'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '5/16'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '3/16'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/16'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-1/8'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/4'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/16'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '3/8'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/32'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '3/8'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/32'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '13/32'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/16'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '7/16'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '3/16'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '1/2'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '-1/16'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '1/2'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/16'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '9/16'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '1/16'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '5/8'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '5/16'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '11/16'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '5/24'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '11/16'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '5/48'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '43/48'

class Test_complex_meas_3_4:
    @pytest.fixture
    def rt(self):
        return RT(meas='3/4', subdivisions=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 21

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 14

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '3/4'

    def test_durations(self, rt):
        expected = (Fraction('3/64'), Fraction('-1/32'), Fraction('1/32'), Fraction('1/32'), Fraction('3/64'), Fraction('-3/32'), Fraction('3/128'), Fraction('3/128'), Fraction('3/64'), Fraction('-3/64'), Fraction('3/64'), Fraction('3/64'), Fraction('5/32'), Fraction('5/64'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('3/64'), Fraction('5/64'), Fraction('7/64'), Fraction('9/64'), Fraction('3/16'), Fraction('9/32'), Fraction('39/128'), Fraction('21/64'), Fraction('3/8'), Fraction('27/64'), Fraction('15/32'), Fraction('33/64'), Fraction('43/64'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '3/4'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '9/64'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '3/64'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '3/32'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '3/64'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '-1/32'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/64'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/32'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '5/64'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/32'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/64'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '15/64'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '9/64'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '3/64'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '9/64'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-3/32'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '3/16'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/64'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '9/32'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/128'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '9/32'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/128'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '39/128'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '3/64'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '21/64'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '9/64'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '3/8'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '-3/64'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '3/8'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '3/64'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '27/64'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '3/64'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '15/32'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '15/64'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '33/64'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '5/32'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '33/64'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '5/64'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '43/64'

class Test_complex_meas_6_5:
    @pytest.fixture
    def rt(self):
        return RT(meas='6/5', subdivisions=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 21

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 14

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '6/5'

    def test_durations(self, rt):
        expected = (Fraction('3/40'), Fraction('-1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('3/40'), Fraction('-3/20'), Fraction('3/80'), Fraction('3/80'), Fraction('3/40'), Fraction('-3/40'), Fraction('3/40'), Fraction('3/40'), Fraction('1/4'), Fraction('1/8'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('3/40'), Fraction('1/8'), Fraction('7/40'), Fraction('9/40'), Fraction('3/10'), Fraction('9/20'), Fraction('39/80'), Fraction('21/40'), Fraction('3/5'), Fraction('27/40'), Fraction('3/4'), Fraction('33/40'), Fraction('43/40'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 6

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '6/5'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '9/40'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '3/40'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '3/20'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '3/40'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '-1/20'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/40'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/20'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/8'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/20'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/40'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '3/8'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '9/40'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '3/40'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '9/40'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-3/20'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '3/10'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/40'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '9/20'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/80'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '9/20'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/80'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '39/80'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '3/40'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '21/40'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '9/40'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '3/5'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '-3/40'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '3/5'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '3/40'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '27/40'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '3/40'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '3/4'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '3/8'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '33/40'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '1/4'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '33/40'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '1/8'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '43/40'

class Test_complex_meas_2_3:
    @pytest.fixture
    def rt(self):
        return RT(meas='2/3', subdivisions=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 21

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 14

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '2/3'

    def test_durations(self, rt):
        expected = (Fraction('1/24'), Fraction('-1/36'), Fraction('1/36'), Fraction('1/36'), Fraction('1/24'), Fraction('-1/12'), Fraction('1/48'), Fraction('1/48'), Fraction('1/24'), Fraction('-1/24'), Fraction('1/24'), Fraction('1/24'), Fraction('5/36'), Fraction('5/72'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/24'), Fraction('5/72'), Fraction('7/72'), Fraction('1/8'), Fraction('1/6'), Fraction('1/4'), Fraction('13/48'), Fraction('7/24'), Fraction('1/3'), Fraction('3/8'), Fraction('5/12'), Fraction('11/24'), Fraction('43/72'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '2/3'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/24'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/12'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/24'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '-1/36'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/24'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/36'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '5/72'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/36'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/72'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '5/24'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/8'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/24'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '1/8'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-1/12'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/6'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/24'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '1/4'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/48'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '1/4'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/48'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '13/48'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/24'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '7/24'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '1/8'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '1/3'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '-1/24'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '1/3'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/24'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '3/8'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '1/24'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '5/12'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '5/24'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '11/24'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '5/36'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '11/24'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '5/72'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '43/72'

class Test_complex_meas_7_2:
    @pytest.fixture
    def rt(self):
        return RT(meas='7/2', subdivisions=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 21

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 14

    def test_depth(self, rt):
        assert rt.depth == 3

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '7/2'

    def test_durations(self, rt):
        expected = (Fraction('7/32'), Fraction('-7/48'), Fraction('7/48'), Fraction('7/48'), Fraction('7/32'), Fraction('-7/16'), Fraction('7/64'), Fraction('7/64'), Fraction('7/32'), Fraction('-7/32'), Fraction('7/32'), Fraction('7/32'), Fraction('35/48'), Fraction('35/96'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('7/32'), Fraction('35/96'), Fraction('49/96'), Fraction('21/32'), Fraction('7/8'), Fraction('21/16'), Fraction('91/64'), Fraction('49/32'), Fraction('7/4'), Fraction('63/32'), Fraction('35/16'), Fraction('77/32'), Fraction('301/96'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 7

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '7/2'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '21/32'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '7/32'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '7/16'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '7/32'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '-7/48'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '7/32'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '7/48'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '35/96'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '7/48'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '49/96'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '35/32'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '21/32'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '7/32'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '21/32'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '-7/16'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '7/8'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '7/32'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '21/16'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '7/64'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '21/16'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '7/64'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '91/64'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '7/32'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '49/32'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '21/32'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '7/4'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '-7/32'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '7/4'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '7/32'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '63/32'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '7/32'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '35/16'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '35/32'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '77/32'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '35/48'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '77/32'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '35/96'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '301/96'

class Test_span_1_meas_5_4:
    @pytest.fixture
    def rt(self):
        return RT(span=1, meas='5/4', subdivisions=((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 11

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 8

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '5/4'

    def test_durations(self, rt):
        expected = (Fraction('1/12'), Fraction('1/12'), Fraction('1/12'), Fraction('1/4'), Fraction('1/4'), Fraction('1/8'), Fraction('1/8'), Fraction('1/4'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/12'), Fraction('1/6'), Fraction('1/4'), Fraction('1/2'), Fraction('3/4'), Fraction('7/8'), Fraction('1'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 8, 9, 10,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '5/4'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/12'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/12'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/12'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/12'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/6'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/4'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/4'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/2'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/4'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '3/4'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/8'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/4'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/8'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '7/8'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/4'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '1'

class Test_span_2_meas_5_4:
    @pytest.fixture
    def rt(self):
        return RT(span=2, meas='5/4', subdivisions=((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 11

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 8

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 2

    def test_meas(self, rt):
        assert str(rt.meas) == '5/4'

    def test_durations(self, rt):
        expected = (Fraction('1/6'), Fraction('1/6'), Fraction('1/6'), Fraction('1/2'), Fraction('1/2'), Fraction('1/4'), Fraction('1/4'), Fraction('1/2'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/6'), Fraction('1/3'), Fraction('1/2'), Fraction('1'), Fraction('3/2'), Fraction('7/4'), Fraction('2'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 8, 9, 10,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 10

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '5/2'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/2'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/2'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/2'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '3/2'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/4'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/2'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/4'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '7/4'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/2'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '2'

class Test_span_3_meas_5_4:
    @pytest.fixture
    def rt(self):
        return RT(span=3, meas='5/4', subdivisions=((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 11

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 8

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 3

    def test_meas(self, rt):
        assert str(rt.meas) == '5/4'

    def test_durations(self, rt):
        expected = (Fraction('1/4'), Fraction('1/4'), Fraction('1/4'), Fraction('3/4'), Fraction('3/4'), Fraction('3/8'), Fraction('3/8'), Fraction('3/4'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/4'), Fraction('1/2'), Fraction('3/4'), Fraction('3/2'), Fraction('9/4'), Fraction('21/8'), Fraction('3'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 8, 9, 10,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 15

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '15/4'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '3/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/2'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '3/4'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '3/4'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '3/4'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '3/2'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '3/4'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '9/4'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '3/8'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '9/4'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '3/8'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '21/8'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/4'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '3'

class Test_accelerating:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 17

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 16

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('2/17'), Fraction('15/136'), Fraction('7/68'), Fraction('13/136'), Fraction('3/34'), Fraction('11/136'), Fraction('5/68'), Fraction('9/136'), Fraction('1/17'), Fraction('7/136'), Fraction('3/68'), Fraction('5/136'), Fraction('1/34'), Fraction('3/136'), Fraction('1/68'), Fraction('1/136'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('2/17'), Fraction('31/136'), Fraction('45/136'), Fraction('29/68'), Fraction('35/68'), Fraction('81/136'), Fraction('91/136'), Fraction('25/34'), Fraction('27/34'), Fraction('115/136'), Fraction('121/136'), Fraction('63/68'), Fraction('65/68'), Fraction('133/136'), Fraction('135/136'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 16

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '2/17'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 15

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '15/136'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '2/17'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 14

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '7/68'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '31/136'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 13

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '13/136'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '45/136'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 12

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '3/34'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '29/68'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 11

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '11/136'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '35/68'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 10

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '5/68'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '81/136'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 9

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '9/136'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '91/136'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 8

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/17'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '25/34'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 7

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '7/136'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '27/34'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 6

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/68'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '115/136'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 5

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '5/136'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '121/136'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 4

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/34'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '63/68'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '3/136'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '65/68'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 2

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/68'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '133/136'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/136'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '135/136'

class Test_decelerating:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 17

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 16

    def test_depth(self, rt):
        assert rt.depth == 1

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/136'), Fraction('1/68'), Fraction('3/136'), Fraction('1/34'), Fraction('5/136'), Fraction('3/68'), Fraction('7/136'), Fraction('1/17'), Fraction('9/136'), Fraction('5/68'), Fraction('11/136'), Fraction('3/34'), Fraction('13/136'), Fraction('7/68'), Fraction('15/136'), Fraction('2/17'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/136'), Fraction('3/136'), Fraction('3/68'), Fraction('5/68'), Fraction('15/136'), Fraction('21/136'), Fraction('7/34'), Fraction('9/34'), Fraction('45/136'), Fraction('55/136'), Fraction('33/68'), Fraction('39/68'), Fraction('91/136'), Fraction('105/136'), Fraction('15/17'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/136'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 2

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/68'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '1/136'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 3

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '3/136'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '3/136'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 4

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/34'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/68'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 5

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '5/136'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '5/68'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 6

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '3/68'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '15/136'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 7

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '7/136'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '21/136'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 8

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/17'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '7/34'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 9

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '9/136'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '9/34'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 10

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '5/68'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '45/136'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 11

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '11/136'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '55/136'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 12

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/34'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '33/68'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 13

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '13/136'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '39/68'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 14

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '7/68'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '91/136'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 15

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '15/136'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '105/136'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 16

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '2/17'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '15/17'

class Test_pulse_accel:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)), (1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1)), (1, (10, 9, 8, 7, 6, 5, 4, 3, 2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 34

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 30

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('2/33'), Fraction('3/55'), Fraction('8/165'), Fraction('7/165'), Fraction('2/55'), Fraction('1/33'), Fraction('4/165'), Fraction('1/55'), Fraction('2/165'), Fraction('1/165'), Fraction('2/33'), Fraction('3/55'), Fraction('8/165'), Fraction('7/165'), Fraction('2/55'), Fraction('1/33'), Fraction('4/165'), Fraction('1/55'), Fraction('2/165'), Fraction('1/165'), Fraction('2/33'), Fraction('3/55'), Fraction('8/165'), Fraction('7/165'), Fraction('2/55'), Fraction('1/33'), Fraction('4/165'), Fraction('1/55'), Fraction('2/165'), Fraction('1/165'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('2/33'), Fraction('19/165'), Fraction('9/55'), Fraction('34/165'), Fraction('8/33'), Fraction('3/11'), Fraction('49/165'), Fraction('52/165'), Fraction('18/55'), Fraction('1/3'), Fraction('13/33'), Fraction('74/165'), Fraction('82/165'), Fraction('89/165'), Fraction('19/33'), Fraction('20/33'), Fraction('104/165'), Fraction('107/165'), Fraction('109/165'), Fraction('2/3'), Fraction('8/11'), Fraction('43/55'), Fraction('137/165'), Fraction('48/55'), Fraction('10/11'), Fraction('31/33'), Fraction('53/55'), Fraction('54/55'), Fraction('164/165'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/3'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 10

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '2/33'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 9

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '3/55'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '2/33'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 8

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '8/165'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '19/165'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 7

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '7/165'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '9/55'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 6

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '2/55'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '34/165'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/33'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '8/33'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 4

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '4/165'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/11'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 3

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/55'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '49/165'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 2

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '2/165'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '52/165'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/165'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '18/55'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/3'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '1/3'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 10

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '2/33'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '1/3'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 9

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '3/55'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '13/33'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 8

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '8/165'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '74/165'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 7

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '7/165'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '82/165'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 6

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '2/55'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '89/165'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '1/33'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '19/33'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 4

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '4/165'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '20/33'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 3

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '1/55'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '104/165'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 2

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '2/165'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '107/165'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 1

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '1/165'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '109/165'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/3'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '2/3'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 10

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '2/33'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '2/3'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 9

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '3/55'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '8/11'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 8

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '8/165'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '43/55'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 7

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '7/165'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '137/165'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 6

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '2/55'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '48/55'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 5

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '1/33'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '10/11'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 4

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '4/165'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '31/33'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 3

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '1/55'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '53/55'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 2

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '2/165'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '54/55'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 1

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '1/165'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '164/165'

class Test_pulse_decel:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)), (1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)), (1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 34

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 30

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/165'), Fraction('2/165'), Fraction('1/55'), Fraction('4/165'), Fraction('1/33'), Fraction('2/55'), Fraction('7/165'), Fraction('8/165'), Fraction('3/55'), Fraction('2/33'), Fraction('1/165'), Fraction('2/165'), Fraction('1/55'), Fraction('4/165'), Fraction('1/33'), Fraction('2/55'), Fraction('7/165'), Fraction('8/165'), Fraction('3/55'), Fraction('2/33'), Fraction('1/165'), Fraction('2/165'), Fraction('1/55'), Fraction('4/165'), Fraction('1/33'), Fraction('2/55'), Fraction('7/165'), Fraction('8/165'), Fraction('3/55'), Fraction('2/33'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/165'), Fraction('1/55'), Fraction('2/55'), Fraction('2/33'), Fraction('1/11'), Fraction('7/55'), Fraction('28/165'), Fraction('12/55'), Fraction('3/11'), Fraction('1/3'), Fraction('56/165'), Fraction('58/165'), Fraction('61/165'), Fraction('13/33'), Fraction('14/33'), Fraction('76/165'), Fraction('83/165'), Fraction('91/165'), Fraction('20/33'), Fraction('2/3'), Fraction('37/55'), Fraction('113/165'), Fraction('116/165'), Fraction('8/11'), Fraction('25/33'), Fraction('131/165'), Fraction('46/55'), Fraction('146/165'), Fraction('31/33'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/3'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/165'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '2/165'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/165'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 3

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/55'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/55'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 4

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '4/165'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '2/55'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 5

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/33'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '2/33'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 6

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '2/55'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/11'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 7

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '7/165'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '7/55'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 8

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '8/165'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '28/165'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 9

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/55'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '12/55'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 10

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '2/33'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '3/11'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/3'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '1/3'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/165'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '1/3'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 2

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '2/165'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '56/165'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 3

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/55'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '58/165'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 4

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '4/165'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '61/165'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 5

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '1/33'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '13/33'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 6

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '2/55'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '14/33'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 7

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '7/165'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '76/165'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 8

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '8/165'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '83/165'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 9

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '3/55'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '91/165'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 10

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '2/33'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '20/33'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/3'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '2/3'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 1

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '1/165'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '2/3'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 2

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '2/165'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '37/55'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 3

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/55'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '113/165'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 4

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '4/165'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '116/165'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 5

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '1/33'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '8/11'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 6

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '2/55'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '25/33'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 7

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '7/165'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '131/165'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 8

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '8/165'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '46/55'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 9

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '3/55'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '146/165'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 10

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '2/33'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '31/33'

class Test_accel_outer_pulse_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((7, (1, 1, 1, 1, 1)), (6, (1, 1, 1, 1, 1)), (5, (1, 1, 1, 1, 1)), (4, (1, 1, 1, 1, 1)), (3, (1, 1, 1, 1, 1)), (2, (1, 1, 1, 1, 1)), (1, (1, 1, 1, 1, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 43

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 35

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('1/140'), Fraction('1/140'), Fraction('1/140'), Fraction('1/140'), Fraction('1/140'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/20'), Fraction('1/10'), Fraction('3/20'), Fraction('1/5'), Fraction('1/4'), Fraction('41/140'), Fraction('47/140'), Fraction('53/140'), Fraction('59/140'), Fraction('13/28'), Fraction('1/2'), Fraction('15/28'), Fraction('4/7'), Fraction('17/28'), Fraction('9/14'), Fraction('47/70'), Fraction('7/10'), Fraction('51/70'), Fraction('53/70'), Fraction('11/14'), Fraction('113/140'), Fraction('29/35'), Fraction('17/20'), Fraction('61/70'), Fraction('25/28'), Fraction('127/140'), Fraction('129/140'), Fraction('131/140'), Fraction('19/20'), Fraction('27/28'), Fraction('34/35'), Fraction('137/140'), Fraction('69/70'), Fraction('139/140'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 7

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/20'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/20'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/20'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/20'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/10'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/20'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '3/20'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/20'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/5'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 6

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '3/14'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/4'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '3/70'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '1/4'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '3/70'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '41/140'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/70'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '47/140'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/70'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '53/140'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '3/70'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '59/140'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 5

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '5/28'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '13/28'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 1

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '1/28'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '13/28'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/28'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '1/2'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/28'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '15/28'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '1/28'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '4/7'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 1

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '1/28'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '17/28'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 4

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '1/7'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '9/14'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '1/35'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '9/14'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 1

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '1/35'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '47/70'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 1

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '1/35'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '7/10'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/35'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '51/70'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 1

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '1/35'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '53/70'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 3

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '3/28'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '11/14'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 1

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '3/140'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '11/14'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 1

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '3/140'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '113/140'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 1

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '3/140'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '29/35'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 1

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '3/140'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '17/20'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 1

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '3/140'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '61/70'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 2

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '1/14'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '25/28'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 1

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '1/70'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '25/28'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 1

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '1/70'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '127/140'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 1

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '1/70'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '129/140'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 1

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '1/70'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '131/140'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 1

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '1/70'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '19/20'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 1

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '1/28'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '27/28'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 1

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '1/140'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '27/28'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 1

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '1/140'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '34/35'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 1

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '1/140'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '137/140'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 1

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '1/140'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '69/70'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 1

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '1/140'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '139/140'

class Test_decel_outer_pulse_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((1, (1, 1, 1, 1, 1)), (2, (1, 1, 1, 1, 1)), (3, (1, 1, 1, 1, 1)), (4, (1, 1, 1, 1, 1)), (5, (1, 1, 1, 1, 1)), (6, (1, 1, 1, 1, 1)), (7, (1, 1, 1, 1, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 43

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 35

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/140'), Fraction('1/140'), Fraction('1/140'), Fraction('1/140'), Fraction('1/140'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('1/70'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('3/140'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('1/35'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('1/28'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('3/70'), Fraction('1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('1/20'), Fraction('1/20'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/140'), Fraction('1/70'), Fraction('3/140'), Fraction('1/35'), Fraction('1/28'), Fraction('1/20'), Fraction('9/140'), Fraction('11/140'), Fraction('13/140'), Fraction('3/28'), Fraction('9/70'), Fraction('3/20'), Fraction('6/35'), Fraction('27/140'), Fraction('3/14'), Fraction('17/70'), Fraction('19/70'), Fraction('3/10'), Fraction('23/70'), Fraction('5/14'), Fraction('11/28'), Fraction('3/7'), Fraction('13/28'), Fraction('1/2'), Fraction('15/28'), Fraction('81/140'), Fraction('87/140'), Fraction('93/140'), Fraction('99/140'), Fraction('3/4'), Fraction('4/5'), Fraction('17/20'), Fraction('9/10'), Fraction('19/20'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/28'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/140'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/140'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/140'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/140'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/70'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/140'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '3/140'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/140'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/35'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/14'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/28'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/70'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '1/28'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/70'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/20'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/70'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '9/140'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/70'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '11/140'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/70'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '13/140'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 3

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '3/28'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '3/28'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 1

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '3/140'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '3/28'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 1

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '3/140'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '9/70'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '3/140'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '3/20'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '3/140'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '6/35'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 1

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '3/140'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '27/140'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 4

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '1/7'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '3/14'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '1/35'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '3/14'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 1

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '1/35'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '17/70'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 1

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '1/35'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '19/70'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/35'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '3/10'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 1

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '1/35'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '23/70'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 5

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '5/28'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '5/14'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 1

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/28'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '5/14'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 1

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '1/28'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '11/28'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 1

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '1/28'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '3/7'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 1

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '1/28'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '13/28'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 1

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '1/28'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '1/2'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 6

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '3/14'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '15/28'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 1

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '3/70'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '15/28'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 1

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '3/70'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '81/140'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 1

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '3/70'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '87/140'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 1

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '3/70'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '93/140'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 1

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '3/70'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '99/140'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 7

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '1/4'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '3/4'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 1

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '1/20'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '3/4'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 1

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '1/20'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '4/5'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 1

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '1/20'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '17/20'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 1

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '1/20'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '9/10'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 1

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '1/20'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '19/20'

class Test_desc_weights_asc_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((7, (1, 2, 3, 4, 5, 6, 7)), (6, (1, 2, 3, 4, 5, 6, 7)), (5, (1, 2, 3, 4, 5, 6, 7)), (4, (1, 2, 3, 4, 5, 6, 7)), (3, (1, 2, 3, 4, 5, 6, 7)), (2, (1, 2, 3, 4, 5, 6, 7)), (1, (1, 2, 3, 4, 5, 6, 7))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 57

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 49

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/112'), Fraction('1/56'), Fraction('3/112'), Fraction('1/28'), Fraction('5/112'), Fraction('3/56'), Fraction('1/16'), Fraction('3/392'), Fraction('3/196'), Fraction('9/392'), Fraction('3/98'), Fraction('15/392'), Fraction('9/196'), Fraction('3/56'), Fraction('5/784'), Fraction('5/392'), Fraction('15/784'), Fraction('5/196'), Fraction('25/784'), Fraction('15/392'), Fraction('5/112'), Fraction('1/196'), Fraction('1/98'), Fraction('3/196'), Fraction('1/49'), Fraction('5/196'), Fraction('3/98'), Fraction('1/28'), Fraction('3/784'), Fraction('3/392'), Fraction('9/784'), Fraction('3/196'), Fraction('15/784'), Fraction('9/392'), Fraction('3/112'), Fraction('1/392'), Fraction('1/196'), Fraction('3/392'), Fraction('1/98'), Fraction('5/392'), Fraction('3/196'), Fraction('1/56'), Fraction('1/784'), Fraction('1/392'), Fraction('3/784'), Fraction('1/196'), Fraction('5/784'), Fraction('3/392'), Fraction('1/112'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/112'), Fraction('3/112'), Fraction('3/56'), Fraction('5/56'), Fraction('15/112'), Fraction('3/16'), Fraction('1/4'), Fraction('101/392'), Fraction('107/392'), Fraction('29/98'), Fraction('16/49'), Fraction('143/392'), Fraction('23/56'), Fraction('13/28'), Fraction('369/784'), Fraction('379/784'), Fraction('197/392'), Fraction('207/392'), Fraction('439/784'), Fraction('67/112'), Fraction('9/14'), Fraction('127/196'), Fraction('129/196'), Fraction('33/49'), Fraction('34/49'), Fraction('141/196'), Fraction('3/4'), Fraction('11/14'), Fraction('619/784'), Fraction('625/784'), Fraction('317/392'), Fraction('323/392'), Fraction('661/784'), Fraction('97/112'), Fraction('25/28'), Fraction('351/392'), Fraction('353/392'), Fraction('89/98'), Fraction('45/49'), Fraction('365/392'), Fraction('53/56'), Fraction('27/28'), Fraction('757/784'), Fraction('759/784'), Fraction('381/392'), Fraction('383/392'), Fraction('771/784'), Fraction('111/112'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 55, 56,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 7

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/112'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/56'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/112'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 3

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '3/112'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '3/112'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 4

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/28'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '3/56'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 5

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '5/112'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '5/56'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 6

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '3/56'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '15/112'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 7

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/16'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '3/16'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 6

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '3/14'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/4'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '3/392'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '1/4'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 2

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/196'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '101/392'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 3

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '9/392'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '107/392'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 4

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '3/98'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '29/98'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 5

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '15/392'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '16/49'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 6

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '9/196'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '143/392'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 7

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '3/56'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '23/56'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 5

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '5/28'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '13/28'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 1

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '5/784'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '13/28'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '5/392'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '369/784'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 3

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '15/784'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '379/784'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 4

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '5/196'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '197/392'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 5

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '25/784'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '207/392'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 6

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '15/392'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '439/784'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 7

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '5/112'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '67/112'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 4

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '1/7'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '9/14'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 1

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/196'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '9/14'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 2

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '1/98'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '127/196'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 3

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '3/196'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '129/196'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 4

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '1/49'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '33/49'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 5

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '5/196'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '34/49'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 6

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '3/98'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '141/196'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 7

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '1/28'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '3/4'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 3

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '3/28'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '11/14'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 1

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '3/784'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '11/14'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 2

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '3/392'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '619/784'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 3

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '9/784'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '625/784'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 4

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '3/196'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '317/392'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 5

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '15/784'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '323/392'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 6

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '9/392'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '661/784'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 7

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '3/112'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '97/112'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 2

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '1/14'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '25/28'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 1

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '1/392'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '25/28'

    def test_node_43_proportion(self, rt):
        assert rt[43].get("proportion") == 2

    def test_node_43_metric_duration(self, rt):
        assert str(rt[43]["metric_duration"]) == '1/196'

    def test_node_43_metric_onset(self, rt):
        assert str(rt[43]["metric_onset"]) == '351/392'

    def test_node_44_proportion(self, rt):
        assert rt[44].get("proportion") == 3

    def test_node_44_metric_duration(self, rt):
        assert str(rt[44]["metric_duration"]) == '3/392'

    def test_node_44_metric_onset(self, rt):
        assert str(rt[44]["metric_onset"]) == '353/392'

    def test_node_45_proportion(self, rt):
        assert rt[45].get("proportion") == 4

    def test_node_45_metric_duration(self, rt):
        assert str(rt[45]["metric_duration"]) == '1/98'

    def test_node_45_metric_onset(self, rt):
        assert str(rt[45]["metric_onset"]) == '89/98'

    def test_node_46_proportion(self, rt):
        assert rt[46].get("proportion") == 5

    def test_node_46_metric_duration(self, rt):
        assert str(rt[46]["metric_duration"]) == '5/392'

    def test_node_46_metric_onset(self, rt):
        assert str(rt[46]["metric_onset"]) == '45/49'

    def test_node_47_proportion(self, rt):
        assert rt[47].get("proportion") == 6

    def test_node_47_metric_duration(self, rt):
        assert str(rt[47]["metric_duration"]) == '3/196'

    def test_node_47_metric_onset(self, rt):
        assert str(rt[47]["metric_onset"]) == '365/392'

    def test_node_48_proportion(self, rt):
        assert rt[48].get("proportion") == 7

    def test_node_48_metric_duration(self, rt):
        assert str(rt[48]["metric_duration"]) == '1/56'

    def test_node_48_metric_onset(self, rt):
        assert str(rt[48]["metric_onset"]) == '53/56'

    def test_node_49_proportion(self, rt):
        assert rt[49].get("proportion") == 1

    def test_node_49_metric_duration(self, rt):
        assert str(rt[49]["metric_duration"]) == '1/28'

    def test_node_49_metric_onset(self, rt):
        assert str(rt[49]["metric_onset"]) == '27/28'

    def test_node_50_proportion(self, rt):
        assert rt[50].get("proportion") == 1

    def test_node_50_metric_duration(self, rt):
        assert str(rt[50]["metric_duration"]) == '1/784'

    def test_node_50_metric_onset(self, rt):
        assert str(rt[50]["metric_onset"]) == '27/28'

    def test_node_51_proportion(self, rt):
        assert rt[51].get("proportion") == 2

    def test_node_51_metric_duration(self, rt):
        assert str(rt[51]["metric_duration"]) == '1/392'

    def test_node_51_metric_onset(self, rt):
        assert str(rt[51]["metric_onset"]) == '757/784'

    def test_node_52_proportion(self, rt):
        assert rt[52].get("proportion") == 3

    def test_node_52_metric_duration(self, rt):
        assert str(rt[52]["metric_duration"]) == '3/784'

    def test_node_52_metric_onset(self, rt):
        assert str(rt[52]["metric_onset"]) == '759/784'

    def test_node_53_proportion(self, rt):
        assert rt[53].get("proportion") == 4

    def test_node_53_metric_duration(self, rt):
        assert str(rt[53]["metric_duration"]) == '1/196'

    def test_node_53_metric_onset(self, rt):
        assert str(rt[53]["metric_onset"]) == '381/392'

    def test_node_54_proportion(self, rt):
        assert rt[54].get("proportion") == 5

    def test_node_54_metric_duration(self, rt):
        assert str(rt[54]["metric_duration"]) == '5/784'

    def test_node_54_metric_onset(self, rt):
        assert str(rt[54]["metric_onset"]) == '383/392'

    def test_node_55_proportion(self, rt):
        assert rt[55].get("proportion") == 6

    def test_node_55_metric_duration(self, rt):
        assert str(rt[55]["metric_duration"]) == '3/392'

    def test_node_55_metric_onset(self, rt):
        assert str(rt[55]["metric_onset"]) == '771/784'

    def test_node_56_proportion(self, rt):
        assert rt[56].get("proportion") == 7

    def test_node_56_metric_duration(self, rt):
        assert str(rt[56]["metric_duration"]) == '1/112'

    def test_node_56_metric_onset(self, rt):
        assert str(rt[56]["metric_onset"]) == '111/112'

class Test_asc_weights_desc_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((1, (7, 6, 5, 4, 3, 2, 1)), (2, (7, 6, 5, 4, 3, 2, 1)), (3, (7, 6, 5, 4, 3, 2, 1)), (4, (7, 6, 5, 4, 3, 2, 1)), (5, (7, 6, 5, 4, 3, 2, 1)), (6, (7, 6, 5, 4, 3, 2, 1)), (7, (7, 6, 5, 4, 3, 2, 1))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 57

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 49

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/112'), Fraction('3/392'), Fraction('5/784'), Fraction('1/196'), Fraction('3/784'), Fraction('1/392'), Fraction('1/784'), Fraction('1/56'), Fraction('3/196'), Fraction('5/392'), Fraction('1/98'), Fraction('3/392'), Fraction('1/196'), Fraction('1/392'), Fraction('3/112'), Fraction('9/392'), Fraction('15/784'), Fraction('3/196'), Fraction('9/784'), Fraction('3/392'), Fraction('3/784'), Fraction('1/28'), Fraction('3/98'), Fraction('5/196'), Fraction('1/49'), Fraction('3/196'), Fraction('1/98'), Fraction('1/196'), Fraction('5/112'), Fraction('15/392'), Fraction('25/784'), Fraction('5/196'), Fraction('15/784'), Fraction('5/392'), Fraction('5/784'), Fraction('3/56'), Fraction('9/196'), Fraction('15/392'), Fraction('3/98'), Fraction('9/392'), Fraction('3/196'), Fraction('3/392'), Fraction('1/16'), Fraction('3/56'), Fraction('5/112'), Fraction('1/28'), Fraction('3/112'), Fraction('1/56'), Fraction('1/112'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/112'), Fraction('13/784'), Fraction('9/392'), Fraction('11/392'), Fraction('25/784'), Fraction('27/784'), Fraction('1/28'), Fraction('3/56'), Fraction('27/392'), Fraction('4/49'), Fraction('9/98'), Fraction('39/392'), Fraction('41/392'), Fraction('3/28'), Fraction('15/112'), Fraction('123/784'), Fraction('69/392'), Fraction('75/392'), Fraction('159/784'), Fraction('165/784'), Fraction('3/14'), Fraction('1/4'), Fraction('55/196'), Fraction('15/49'), Fraction('16/49'), Fraction('67/196'), Fraction('69/196'), Fraction('5/14'), Fraction('45/112'), Fraction('345/784'), Fraction('185/392'), Fraction('195/392'), Fraction('405/784'), Fraction('415/784'), Fraction('15/28'), Fraction('33/56'), Fraction('249/392'), Fraction('33/49'), Fraction('69/98'), Fraction('285/392'), Fraction('291/392'), Fraction('3/4'), Fraction('13/16'), Fraction('97/112'), Fraction('51/56'), Fraction('53/56'), Fraction('109/112'), Fraction('111/112'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 24, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38, 39, 40, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 53, 54, 55, 56,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/28'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 7

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/112'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 6

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '3/392'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/112'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 5

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '5/784'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '13/784'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 4

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/196'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '9/392'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 3

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '3/784'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '11/392'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/392'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '25/784'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/784'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '27/784'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 2

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/14'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/28'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 7

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/56'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '1/28'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 6

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '3/196'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '3/56'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 5

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '5/392'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '27/392'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 4

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/98'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '4/49'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '3/392'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '9/98'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 2

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/196'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '39/392'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/392'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '41/392'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 3

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '3/28'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '3/28'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 7

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '3/112'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '3/28'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 6

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '9/392'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '15/112'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 5

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '15/784'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '123/784'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 4

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '3/196'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '69/392'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 3

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '9/784'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '75/392'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 2

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '3/392'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '159/784'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 1

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '3/784'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '165/784'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 4

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '1/7'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '3/14'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 7

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/28'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '3/14'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 6

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '3/98'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '1/4'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 5

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '5/196'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '55/196'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 4

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '1/49'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '15/49'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 3

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '3/196'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '16/49'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 2

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '1/98'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '67/196'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 1

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '1/196'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '69/196'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 5

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '5/28'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '5/14'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 7

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '5/112'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '5/14'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 6

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '15/392'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '45/112'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 5

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '25/784'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '345/784'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 4

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '5/196'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '185/392'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 3

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '15/784'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '195/392'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 2

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '5/392'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '405/784'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 1

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '5/784'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '415/784'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 6

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '3/14'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '15/28'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 7

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '3/56'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '15/28'

    def test_node_43_proportion(self, rt):
        assert rt[43].get("proportion") == 6

    def test_node_43_metric_duration(self, rt):
        assert str(rt[43]["metric_duration"]) == '9/196'

    def test_node_43_metric_onset(self, rt):
        assert str(rt[43]["metric_onset"]) == '33/56'

    def test_node_44_proportion(self, rt):
        assert rt[44].get("proportion") == 5

    def test_node_44_metric_duration(self, rt):
        assert str(rt[44]["metric_duration"]) == '15/392'

    def test_node_44_metric_onset(self, rt):
        assert str(rt[44]["metric_onset"]) == '249/392'

    def test_node_45_proportion(self, rt):
        assert rt[45].get("proportion") == 4

    def test_node_45_metric_duration(self, rt):
        assert str(rt[45]["metric_duration"]) == '3/98'

    def test_node_45_metric_onset(self, rt):
        assert str(rt[45]["metric_onset"]) == '33/49'

    def test_node_46_proportion(self, rt):
        assert rt[46].get("proportion") == 3

    def test_node_46_metric_duration(self, rt):
        assert str(rt[46]["metric_duration"]) == '9/392'

    def test_node_46_metric_onset(self, rt):
        assert str(rt[46]["metric_onset"]) == '69/98'

    def test_node_47_proportion(self, rt):
        assert rt[47].get("proportion") == 2

    def test_node_47_metric_duration(self, rt):
        assert str(rt[47]["metric_duration"]) == '3/196'

    def test_node_47_metric_onset(self, rt):
        assert str(rt[47]["metric_onset"]) == '285/392'

    def test_node_48_proportion(self, rt):
        assert rt[48].get("proportion") == 1

    def test_node_48_metric_duration(self, rt):
        assert str(rt[48]["metric_duration"]) == '3/392'

    def test_node_48_metric_onset(self, rt):
        assert str(rt[48]["metric_onset"]) == '291/392'

    def test_node_49_proportion(self, rt):
        assert rt[49].get("proportion") == 7

    def test_node_49_metric_duration(self, rt):
        assert str(rt[49]["metric_duration"]) == '1/4'

    def test_node_49_metric_onset(self, rt):
        assert str(rt[49]["metric_onset"]) == '3/4'

    def test_node_50_proportion(self, rt):
        assert rt[50].get("proportion") == 7

    def test_node_50_metric_duration(self, rt):
        assert str(rt[50]["metric_duration"]) == '1/16'

    def test_node_50_metric_onset(self, rt):
        assert str(rt[50]["metric_onset"]) == '3/4'

    def test_node_51_proportion(self, rt):
        assert rt[51].get("proportion") == 6

    def test_node_51_metric_duration(self, rt):
        assert str(rt[51]["metric_duration"]) == '3/56'

    def test_node_51_metric_onset(self, rt):
        assert str(rt[51]["metric_onset"]) == '13/16'

    def test_node_52_proportion(self, rt):
        assert rt[52].get("proportion") == 5

    def test_node_52_metric_duration(self, rt):
        assert str(rt[52]["metric_duration"]) == '5/112'

    def test_node_52_metric_onset(self, rt):
        assert str(rt[52]["metric_onset"]) == '97/112'

    def test_node_53_proportion(self, rt):
        assert rt[53].get("proportion") == 4

    def test_node_53_metric_duration(self, rt):
        assert str(rt[53]["metric_duration"]) == '1/28'

    def test_node_53_metric_onset(self, rt):
        assert str(rt[53]["metric_onset"]) == '51/56'

    def test_node_54_proportion(self, rt):
        assert rt[54].get("proportion") == 3

    def test_node_54_metric_duration(self, rt):
        assert str(rt[54]["metric_duration"]) == '3/112'

    def test_node_54_metric_onset(self, rt):
        assert str(rt[54]["metric_onset"]) == '53/56'

    def test_node_55_proportion(self, rt):
        assert rt[55].get("proportion") == 2

    def test_node_55_metric_duration(self, rt):
        assert str(rt[55]["metric_duration"]) == '1/56'

    def test_node_55_metric_onset(self, rt):
        assert str(rt[55]["metric_onset"]) == '109/112'

    def test_node_56_proportion(self, rt):
        assert rt[56].get("proportion") == 1

    def test_node_56_metric_duration(self, rt):
        assert str(rt[56]["metric_duration"]) == '1/112'

    def test_node_56_metric_onset(self, rt):
        assert str(rt[56]["metric_onset"]) == '111/112'

class Test_desc_weights_cycle_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((6, (1, 2, 3, 1, 2, 3)), (5, (1, 2, 3, 1, 2, 3)), (4, (1, 2, 3, 1, 2, 3)), (3, (1, 2, 3, 1, 2, 3)), (2, (1, 2, 3, 1, 2, 3)), (1, (1, 2, 3, 1, 2, 3))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 43

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 36

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/42'), Fraction('1/21'), Fraction('1/14'), Fraction('1/42'), Fraction('1/21'), Fraction('1/14'), Fraction('5/252'), Fraction('5/126'), Fraction('5/84'), Fraction('5/252'), Fraction('5/126'), Fraction('5/84'), Fraction('1/63'), Fraction('2/63'), Fraction('1/21'), Fraction('1/63'), Fraction('2/63'), Fraction('1/21'), Fraction('1/84'), Fraction('1/42'), Fraction('1/28'), Fraction('1/84'), Fraction('1/42'), Fraction('1/28'), Fraction('1/126'), Fraction('1/63'), Fraction('1/42'), Fraction('1/126'), Fraction('1/63'), Fraction('1/42'), Fraction('1/252'), Fraction('1/126'), Fraction('1/84'), Fraction('1/252'), Fraction('1/126'), Fraction('1/84'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/42'), Fraction('1/14'), Fraction('1/7'), Fraction('1/6'), Fraction('3/14'), Fraction('2/7'), Fraction('11/36'), Fraction('29/84'), Fraction('17/42'), Fraction('107/252'), Fraction('13/28'), Fraction('11/21'), Fraction('34/63'), Fraction('4/7'), Fraction('13/21'), Fraction('40/63'), Fraction('2/3'), Fraction('5/7'), Fraction('61/84'), Fraction('3/4'), Fraction('11/14'), Fraction('67/84'), Fraction('23/28'), Fraction('6/7'), Fraction('109/126'), Fraction('37/42'), Fraction('19/21'), Fraction('115/126'), Fraction('13/14'), Fraction('20/21'), Fraction('241/252'), Fraction('27/28'), Fraction('41/42'), Fraction('247/252'), Fraction('83/84'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 6

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '2/7'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/42'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/21'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/42'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 3

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/14'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/14'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/42'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/7'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 2

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/21'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '1/6'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 3

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/14'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '3/14'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 5

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '5/21'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '2/7'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '5/252'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '2/7'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 2

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '5/126'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '11/36'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 3

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '5/84'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '29/84'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '5/252'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '17/42'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 2

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '5/126'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '107/252'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '5/84'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '13/28'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 4

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '4/21'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '11/21'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/63'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '11/21'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 2

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '2/63'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '34/63'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 3

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '1/21'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '4/7'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 1

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '1/63'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '13/21'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 2

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '2/63'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '40/63'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 3

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '1/21'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '2/3'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 3

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '1/7'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '5/7'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/84'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '5/7'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 2

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '1/42'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '61/84'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 3

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '1/28'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '3/4'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 1

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/84'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '11/14'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 2

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '1/42'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '67/84'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 3

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '1/28'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '23/28'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 2

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '2/21'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '6/7'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 1

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '1/126'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '6/7'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 2

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '1/63'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '109/126'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 3

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '1/42'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '37/42'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 1

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '1/126'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '19/21'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 2

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '1/63'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '115/126'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 3

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '1/42'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '13/14'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 1

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '1/21'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '20/21'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 1

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '1/252'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '20/21'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 2

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '1/126'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '241/252'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 3

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '1/84'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '27/28'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 1

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '1/252'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '41/42'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 2

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '1/126'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '247/252'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 3

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '1/84'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '83/84'

class Test_asc_weights_cycle_inner:
    @pytest.fixture
    def rt(self):
        return RT(subdivisions=((1, (1, 2, 3, 1, 2, 3)), (2, (1, 2, 3, 1, 2, 3)), (3, (1, 2, 3, 1, 2, 3)), (4, (1, 2, 3, 1, 2, 3)), (5, (1, 2, 3, 1, 2, 3)), (6, (1, 2, 3, 1, 2, 3)), (7, (1, 2, 3, 1, 2, 3)), (8, (1, 2, 3, 1, 2, 3))))

    def test_full_structural_equivalence(self, rt):
        key = self.__class__.__name__.replace("Test_", "")
        expected = get_expected_trees()["rt"][key]["expected"]
        assert_rt_matches_expected(rt, expected)

    def test_num_nodes(self, rt):
        assert len(rt.nodes) == 57

    def test_num_leaves(self, rt):
        assert len(rt.leaf_nodes) == 48

    def test_depth(self, rt):
        assert rt.depth == 2

    def test_span(self, rt):
        assert rt.span == 1

    def test_meas(self, rt):
        assert str(rt.meas) == '1/1'

    def test_durations(self, rt):
        expected = (Fraction('1/432'), Fraction('1/216'), Fraction('1/144'), Fraction('1/432'), Fraction('1/216'), Fraction('1/144'), Fraction('1/216'), Fraction('1/108'), Fraction('1/72'), Fraction('1/216'), Fraction('1/108'), Fraction('1/72'), Fraction('1/144'), Fraction('1/72'), Fraction('1/48'), Fraction('1/144'), Fraction('1/72'), Fraction('1/48'), Fraction('1/108'), Fraction('1/54'), Fraction('1/36'), Fraction('1/108'), Fraction('1/54'), Fraction('1/36'), Fraction('5/432'), Fraction('5/216'), Fraction('5/144'), Fraction('5/432'), Fraction('5/216'), Fraction('5/144'), Fraction('1/72'), Fraction('1/36'), Fraction('1/24'), Fraction('1/72'), Fraction('1/36'), Fraction('1/24'), Fraction('7/432'), Fraction('7/216'), Fraction('7/144'), Fraction('7/432'), Fraction('7/216'), Fraction('7/144'), Fraction('1/54'), Fraction('1/27'), Fraction('1/18'), Fraction('1/54'), Fraction('1/27'), Fraction('1/18'),)
        assert rt.durations == expected

    def test_onsets(self, rt):
        expected = (Fraction('0'), Fraction('1/432'), Fraction('1/144'), Fraction('1/72'), Fraction('7/432'), Fraction('1/48'), Fraction('1/36'), Fraction('7/216'), Fraction('1/24'), Fraction('1/18'), Fraction('13/216'), Fraction('5/72'), Fraction('1/12'), Fraction('13/144'), Fraction('5/48'), Fraction('1/8'), Fraction('19/144'), Fraction('7/48'), Fraction('1/6'), Fraction('19/108'), Fraction('7/36'), Fraction('2/9'), Fraction('25/108'), Fraction('1/4'), Fraction('5/18'), Fraction('125/432'), Fraction('5/16'), Fraction('25/72'), Fraction('155/432'), Fraction('55/144'), Fraction('5/12'), Fraction('31/72'), Fraction('11/24'), Fraction('1/2'), Fraction('37/72'), Fraction('13/24'), Fraction('7/12'), Fraction('259/432'), Fraction('91/144'), Fraction('49/72'), Fraction('301/432'), Fraction('35/48'), Fraction('7/9'), Fraction('43/54'), Fraction('5/6'), Fraction('8/9'), Fraction('49/54'), Fraction('17/18'),)
        assert rt.onsets == expected

    def test_leaf_nodes_order(self, rt):
        expected = (2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 44, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56,)
        assert rt.leaf_nodes == expected

    def test_node_0_proportion(self, rt):
        assert rt[0].get("proportion") == 1

    def test_node_0_metric_duration(self, rt):
        assert str(rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, rt):
        assert str(rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, rt):
        assert rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, rt):
        assert str(rt[1]["metric_duration"]) == '1/36'

    def test_node_1_metric_onset(self, rt):
        assert str(rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, rt):
        assert rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, rt):
        assert str(rt[2]["metric_duration"]) == '1/432'

    def test_node_2_metric_onset(self, rt):
        assert str(rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, rt):
        assert rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, rt):
        assert str(rt[3]["metric_duration"]) == '1/216'

    def test_node_3_metric_onset(self, rt):
        assert str(rt[3]["metric_onset"]) == '1/432'

    def test_node_4_proportion(self, rt):
        assert rt[4].get("proportion") == 3

    def test_node_4_metric_duration(self, rt):
        assert str(rt[4]["metric_duration"]) == '1/144'

    def test_node_4_metric_onset(self, rt):
        assert str(rt[4]["metric_onset"]) == '1/144'

    def test_node_5_proportion(self, rt):
        assert rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, rt):
        assert str(rt[5]["metric_duration"]) == '1/432'

    def test_node_5_metric_onset(self, rt):
        assert str(rt[5]["metric_onset"]) == '1/72'

    def test_node_6_proportion(self, rt):
        assert rt[6].get("proportion") == 2

    def test_node_6_metric_duration(self, rt):
        assert str(rt[6]["metric_duration"]) == '1/216'

    def test_node_6_metric_onset(self, rt):
        assert str(rt[6]["metric_onset"]) == '7/432'

    def test_node_7_proportion(self, rt):
        assert rt[7].get("proportion") == 3

    def test_node_7_metric_duration(self, rt):
        assert str(rt[7]["metric_duration"]) == '1/144'

    def test_node_7_metric_onset(self, rt):
        assert str(rt[7]["metric_onset"]) == '1/48'

    def test_node_8_proportion(self, rt):
        assert rt[8].get("proportion") == 2

    def test_node_8_metric_duration(self, rt):
        assert str(rt[8]["metric_duration"]) == '1/18'

    def test_node_8_metric_onset(self, rt):
        assert str(rt[8]["metric_onset"]) == '1/36'

    def test_node_9_proportion(self, rt):
        assert rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, rt):
        assert str(rt[9]["metric_duration"]) == '1/216'

    def test_node_9_metric_onset(self, rt):
        assert str(rt[9]["metric_onset"]) == '1/36'

    def test_node_10_proportion(self, rt):
        assert rt[10].get("proportion") == 2

    def test_node_10_metric_duration(self, rt):
        assert str(rt[10]["metric_duration"]) == '1/108'

    def test_node_10_metric_onset(self, rt):
        assert str(rt[10]["metric_onset"]) == '7/216'

    def test_node_11_proportion(self, rt):
        assert rt[11].get("proportion") == 3

    def test_node_11_metric_duration(self, rt):
        assert str(rt[11]["metric_duration"]) == '1/72'

    def test_node_11_metric_onset(self, rt):
        assert str(rt[11]["metric_onset"]) == '1/24'

    def test_node_12_proportion(self, rt):
        assert rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, rt):
        assert str(rt[12]["metric_duration"]) == '1/216'

    def test_node_12_metric_onset(self, rt):
        assert str(rt[12]["metric_onset"]) == '1/18'

    def test_node_13_proportion(self, rt):
        assert rt[13].get("proportion") == 2

    def test_node_13_metric_duration(self, rt):
        assert str(rt[13]["metric_duration"]) == '1/108'

    def test_node_13_metric_onset(self, rt):
        assert str(rt[13]["metric_onset"]) == '13/216'

    def test_node_14_proportion(self, rt):
        assert rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, rt):
        assert str(rt[14]["metric_duration"]) == '1/72'

    def test_node_14_metric_onset(self, rt):
        assert str(rt[14]["metric_onset"]) == '5/72'

    def test_node_15_proportion(self, rt):
        assert rt[15].get("proportion") == 3

    def test_node_15_metric_duration(self, rt):
        assert str(rt[15]["metric_duration"]) == '1/12'

    def test_node_15_metric_onset(self, rt):
        assert str(rt[15]["metric_onset"]) == '1/12'

    def test_node_16_proportion(self, rt):
        assert rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, rt):
        assert str(rt[16]["metric_duration"]) == '1/144'

    def test_node_16_metric_onset(self, rt):
        assert str(rt[16]["metric_onset"]) == '1/12'

    def test_node_17_proportion(self, rt):
        assert rt[17].get("proportion") == 2

    def test_node_17_metric_duration(self, rt):
        assert str(rt[17]["metric_duration"]) == '1/72'

    def test_node_17_metric_onset(self, rt):
        assert str(rt[17]["metric_onset"]) == '13/144'

    def test_node_18_proportion(self, rt):
        assert rt[18].get("proportion") == 3

    def test_node_18_metric_duration(self, rt):
        assert str(rt[18]["metric_duration"]) == '1/48'

    def test_node_18_metric_onset(self, rt):
        assert str(rt[18]["metric_onset"]) == '5/48'

    def test_node_19_proportion(self, rt):
        assert rt[19].get("proportion") == 1

    def test_node_19_metric_duration(self, rt):
        assert str(rt[19]["metric_duration"]) == '1/144'

    def test_node_19_metric_onset(self, rt):
        assert str(rt[19]["metric_onset"]) == '1/8'

    def test_node_20_proportion(self, rt):
        assert rt[20].get("proportion") == 2

    def test_node_20_metric_duration(self, rt):
        assert str(rt[20]["metric_duration"]) == '1/72'

    def test_node_20_metric_onset(self, rt):
        assert str(rt[20]["metric_onset"]) == '19/144'

    def test_node_21_proportion(self, rt):
        assert rt[21].get("proportion") == 3

    def test_node_21_metric_duration(self, rt):
        assert str(rt[21]["metric_duration"]) == '1/48'

    def test_node_21_metric_onset(self, rt):
        assert str(rt[21]["metric_onset"]) == '7/48'

    def test_node_22_proportion(self, rt):
        assert rt[22].get("proportion") == 4

    def test_node_22_metric_duration(self, rt):
        assert str(rt[22]["metric_duration"]) == '1/9'

    def test_node_22_metric_onset(self, rt):
        assert str(rt[22]["metric_onset"]) == '1/6'

    def test_node_23_proportion(self, rt):
        assert rt[23].get("proportion") == 1

    def test_node_23_metric_duration(self, rt):
        assert str(rt[23]["metric_duration"]) == '1/108'

    def test_node_23_metric_onset(self, rt):
        assert str(rt[23]["metric_onset"]) == '1/6'

    def test_node_24_proportion(self, rt):
        assert rt[24].get("proportion") == 2

    def test_node_24_metric_duration(self, rt):
        assert str(rt[24]["metric_duration"]) == '1/54'

    def test_node_24_metric_onset(self, rt):
        assert str(rt[24]["metric_onset"]) == '19/108'

    def test_node_25_proportion(self, rt):
        assert rt[25].get("proportion") == 3

    def test_node_25_metric_duration(self, rt):
        assert str(rt[25]["metric_duration"]) == '1/36'

    def test_node_25_metric_onset(self, rt):
        assert str(rt[25]["metric_onset"]) == '7/36'

    def test_node_26_proportion(self, rt):
        assert rt[26].get("proportion") == 1

    def test_node_26_metric_duration(self, rt):
        assert str(rt[26]["metric_duration"]) == '1/108'

    def test_node_26_metric_onset(self, rt):
        assert str(rt[26]["metric_onset"]) == '2/9'

    def test_node_27_proportion(self, rt):
        assert rt[27].get("proportion") == 2

    def test_node_27_metric_duration(self, rt):
        assert str(rt[27]["metric_duration"]) == '1/54'

    def test_node_27_metric_onset(self, rt):
        assert str(rt[27]["metric_onset"]) == '25/108'

    def test_node_28_proportion(self, rt):
        assert rt[28].get("proportion") == 3

    def test_node_28_metric_duration(self, rt):
        assert str(rt[28]["metric_duration"]) == '1/36'

    def test_node_28_metric_onset(self, rt):
        assert str(rt[28]["metric_onset"]) == '1/4'

    def test_node_29_proportion(self, rt):
        assert rt[29].get("proportion") == 5

    def test_node_29_metric_duration(self, rt):
        assert str(rt[29]["metric_duration"]) == '5/36'

    def test_node_29_metric_onset(self, rt):
        assert str(rt[29]["metric_onset"]) == '5/18'

    def test_node_30_proportion(self, rt):
        assert rt[30].get("proportion") == 1

    def test_node_30_metric_duration(self, rt):
        assert str(rt[30]["metric_duration"]) == '5/432'

    def test_node_30_metric_onset(self, rt):
        assert str(rt[30]["metric_onset"]) == '5/18'

    def test_node_31_proportion(self, rt):
        assert rt[31].get("proportion") == 2

    def test_node_31_metric_duration(self, rt):
        assert str(rt[31]["metric_duration"]) == '5/216'

    def test_node_31_metric_onset(self, rt):
        assert str(rt[31]["metric_onset"]) == '125/432'

    def test_node_32_proportion(self, rt):
        assert rt[32].get("proportion") == 3

    def test_node_32_metric_duration(self, rt):
        assert str(rt[32]["metric_duration"]) == '5/144'

    def test_node_32_metric_onset(self, rt):
        assert str(rt[32]["metric_onset"]) == '5/16'

    def test_node_33_proportion(self, rt):
        assert rt[33].get("proportion") == 1

    def test_node_33_metric_duration(self, rt):
        assert str(rt[33]["metric_duration"]) == '5/432'

    def test_node_33_metric_onset(self, rt):
        assert str(rt[33]["metric_onset"]) == '25/72'

    def test_node_34_proportion(self, rt):
        assert rt[34].get("proportion") == 2

    def test_node_34_metric_duration(self, rt):
        assert str(rt[34]["metric_duration"]) == '5/216'

    def test_node_34_metric_onset(self, rt):
        assert str(rt[34]["metric_onset"]) == '155/432'

    def test_node_35_proportion(self, rt):
        assert rt[35].get("proportion") == 3

    def test_node_35_metric_duration(self, rt):
        assert str(rt[35]["metric_duration"]) == '5/144'

    def test_node_35_metric_onset(self, rt):
        assert str(rt[35]["metric_onset"]) == '55/144'

    def test_node_36_proportion(self, rt):
        assert rt[36].get("proportion") == 6

    def test_node_36_metric_duration(self, rt):
        assert str(rt[36]["metric_duration"]) == '1/6'

    def test_node_36_metric_onset(self, rt):
        assert str(rt[36]["metric_onset"]) == '5/12'

    def test_node_37_proportion(self, rt):
        assert rt[37].get("proportion") == 1

    def test_node_37_metric_duration(self, rt):
        assert str(rt[37]["metric_duration"]) == '1/72'

    def test_node_37_metric_onset(self, rt):
        assert str(rt[37]["metric_onset"]) == '5/12'

    def test_node_38_proportion(self, rt):
        assert rt[38].get("proportion") == 2

    def test_node_38_metric_duration(self, rt):
        assert str(rt[38]["metric_duration"]) == '1/36'

    def test_node_38_metric_onset(self, rt):
        assert str(rt[38]["metric_onset"]) == '31/72'

    def test_node_39_proportion(self, rt):
        assert rt[39].get("proportion") == 3

    def test_node_39_metric_duration(self, rt):
        assert str(rt[39]["metric_duration"]) == '1/24'

    def test_node_39_metric_onset(self, rt):
        assert str(rt[39]["metric_onset"]) == '11/24'

    def test_node_40_proportion(self, rt):
        assert rt[40].get("proportion") == 1

    def test_node_40_metric_duration(self, rt):
        assert str(rt[40]["metric_duration"]) == '1/72'

    def test_node_40_metric_onset(self, rt):
        assert str(rt[40]["metric_onset"]) == '1/2'

    def test_node_41_proportion(self, rt):
        assert rt[41].get("proportion") == 2

    def test_node_41_metric_duration(self, rt):
        assert str(rt[41]["metric_duration"]) == '1/36'

    def test_node_41_metric_onset(self, rt):
        assert str(rt[41]["metric_onset"]) == '37/72'

    def test_node_42_proportion(self, rt):
        assert rt[42].get("proportion") == 3

    def test_node_42_metric_duration(self, rt):
        assert str(rt[42]["metric_duration"]) == '1/24'

    def test_node_42_metric_onset(self, rt):
        assert str(rt[42]["metric_onset"]) == '13/24'

    def test_node_43_proportion(self, rt):
        assert rt[43].get("proportion") == 7

    def test_node_43_metric_duration(self, rt):
        assert str(rt[43]["metric_duration"]) == '7/36'

    def test_node_43_metric_onset(self, rt):
        assert str(rt[43]["metric_onset"]) == '7/12'

    def test_node_44_proportion(self, rt):
        assert rt[44].get("proportion") == 1

    def test_node_44_metric_duration(self, rt):
        assert str(rt[44]["metric_duration"]) == '7/432'

    def test_node_44_metric_onset(self, rt):
        assert str(rt[44]["metric_onset"]) == '7/12'

    def test_node_45_proportion(self, rt):
        assert rt[45].get("proportion") == 2

    def test_node_45_metric_duration(self, rt):
        assert str(rt[45]["metric_duration"]) == '7/216'

    def test_node_45_metric_onset(self, rt):
        assert str(rt[45]["metric_onset"]) == '259/432'

    def test_node_46_proportion(self, rt):
        assert rt[46].get("proportion") == 3

    def test_node_46_metric_duration(self, rt):
        assert str(rt[46]["metric_duration"]) == '7/144'

    def test_node_46_metric_onset(self, rt):
        assert str(rt[46]["metric_onset"]) == '91/144'

    def test_node_47_proportion(self, rt):
        assert rt[47].get("proportion") == 1

    def test_node_47_metric_duration(self, rt):
        assert str(rt[47]["metric_duration"]) == '7/432'

    def test_node_47_metric_onset(self, rt):
        assert str(rt[47]["metric_onset"]) == '49/72'

    def test_node_48_proportion(self, rt):
        assert rt[48].get("proportion") == 2

    def test_node_48_metric_duration(self, rt):
        assert str(rt[48]["metric_duration"]) == '7/216'

    def test_node_48_metric_onset(self, rt):
        assert str(rt[48]["metric_onset"]) == '301/432'

    def test_node_49_proportion(self, rt):
        assert rt[49].get("proportion") == 3

    def test_node_49_metric_duration(self, rt):
        assert str(rt[49]["metric_duration"]) == '7/144'

    def test_node_49_metric_onset(self, rt):
        assert str(rt[49]["metric_onset"]) == '35/48'

    def test_node_50_proportion(self, rt):
        assert rt[50].get("proportion") == 8

    def test_node_50_metric_duration(self, rt):
        assert str(rt[50]["metric_duration"]) == '2/9'

    def test_node_50_metric_onset(self, rt):
        assert str(rt[50]["metric_onset"]) == '7/9'

    def test_node_51_proportion(self, rt):
        assert rt[51].get("proportion") == 1

    def test_node_51_metric_duration(self, rt):
        assert str(rt[51]["metric_duration"]) == '1/54'

    def test_node_51_metric_onset(self, rt):
        assert str(rt[51]["metric_onset"]) == '7/9'

    def test_node_52_proportion(self, rt):
        assert rt[52].get("proportion") == 2

    def test_node_52_metric_duration(self, rt):
        assert str(rt[52]["metric_duration"]) == '1/27'

    def test_node_52_metric_onset(self, rt):
        assert str(rt[52]["metric_onset"]) == '43/54'

    def test_node_53_proportion(self, rt):
        assert rt[53].get("proportion") == 3

    def test_node_53_metric_duration(self, rt):
        assert str(rt[53]["metric_duration"]) == '1/18'

    def test_node_53_metric_onset(self, rt):
        assert str(rt[53]["metric_onset"]) == '5/6'

    def test_node_54_proportion(self, rt):
        assert rt[54].get("proportion") == 1

    def test_node_54_metric_duration(self, rt):
        assert str(rt[54]["metric_duration"]) == '1/54'

    def test_node_54_metric_onset(self, rt):
        assert str(rt[54]["metric_onset"]) == '8/9'

    def test_node_55_proportion(self, rt):
        assert rt[55].get("proportion") == 2

    def test_node_55_metric_duration(self, rt):
        assert str(rt[55]["metric_duration"]) == '1/27'

    def test_node_55_metric_onset(self, rt):
        assert str(rt[55]["metric_onset"]) == '49/54'

    def test_node_56_proportion(self, rt):
        assert rt[56].get("proportion") == 3

    def test_node_56_metric_duration(self, rt):
        assert str(rt[56]["metric_duration"]) == '1/18'

    def test_node_56_metric_onset(self, rt):
        assert str(rt[56]["metric_onset"]) == '17/18'

