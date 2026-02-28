"""Tests for CompositionalUnit."""
import pytest
from fractions import Fraction
from klotho.thetos import CompositionalUnit as UC
from tree_helpers import assert_rt_matches_expected, assert_rt_pt_structurally_matched
from conftest import get_expected_trees

UC_EXPECTED_KEY = {
    "Test_uc_default": "uc_default",
    "Test_uc_4_2_1_1": "uc_4_2_1_1",
    "Test_uc_pulse": "uc_pulse",
    "Test_uc_nested": "uc_nested",
}


class Test_uc_default:
    @pytest.fixture
    def uc(self):
        return UC(tempus='4/4')

    def test_full_structural_equivalence(self, uc):
        _ = uc.events
        key = UC_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["uc"][key]["expected"]
        assert_rt_matches_expected(uc._rt, expected)

    def test_rt_pt_structurally_matched(self, uc):
        _ = uc.events
        assert_rt_pt_structurally_matched(uc._rt, uc._pt)

    def test_num_events(self, uc):
        assert len(uc.events) == 1

    def test_beat(self, uc):
        assert str(uc.beat) == '1/4'

    def test_tempus(self, uc):
        assert str(uc.tempus) == '4/4'

    def test_onsets(self, uc):
        _ = uc.events
        expected = [0.0]
        actual = [float(o) for o in uc.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, uc):
        _ = uc.events
        expected = [4.0]
        actual = [float(d) for d in uc.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, uc):
        _ = uc.events
        expected = (1,)
        assert uc.leaf_nodes == expected

    def test_node_0_proportion(self, uc):
        _ = uc.events
        assert uc._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, uc):
        _ = uc.events
        assert uc._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_onset"]) == '0'


class Test_uc_4_2_1_1:
    @pytest.fixture
    def uc(self):
        return UC(tempus='4/4', prolatio=(4, 2, 1, 1))

    def test_full_structural_equivalence(self, uc):
        _ = uc.events
        key = UC_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["uc"][key]["expected"]
        assert_rt_matches_expected(uc._rt, expected)

    def test_rt_pt_structurally_matched(self, uc):
        _ = uc.events
        assert_rt_pt_structurally_matched(uc._rt, uc._pt)

    def test_num_events(self, uc):
        assert len(uc.events) == 4

    def test_beat(self, uc):
        assert str(uc.beat) == '1/4'

    def test_tempus(self, uc):
        assert str(uc.tempus) == '4/4'

    def test_onsets(self, uc):
        _ = uc.events
        expected = [0.0, 2.0, 3.0, 3.5]
        actual = [float(o) for o in uc.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, uc):
        _ = uc.events
        expected = [2.0, 1.0, 0.5, 0.5]
        actual = [float(d) for d in uc.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, uc):
        _ = uc.events
        expected = (1, 2, 3, 4,)
        assert uc.leaf_nodes == expected

    def test_node_0_proportion(self, uc):
        _ = uc.events
        assert uc._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, uc):
        _ = uc.events
        assert uc._rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, uc):
        _ = uc.events
        assert uc._rt[2].get("proportion") == 2

    def test_node_2_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_onset"]) == '1/2'

    def test_node_3_proportion(self, uc):
        _ = uc.events
        assert uc._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_onset"]) == '3/4'

    def test_node_4_proportion(self, uc):
        _ = uc.events
        assert uc._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_onset"]) == '7/8'


class Test_uc_pulse:
    @pytest.fixture
    def uc(self):
        return UC(tempus='4/4', prolatio='p')

    def test_full_structural_equivalence(self, uc):
        _ = uc.events
        key = UC_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["uc"][key]["expected"]
        assert_rt_matches_expected(uc._rt, expected)

    def test_rt_pt_structurally_matched(self, uc):
        _ = uc.events
        assert_rt_pt_structurally_matched(uc._rt, uc._pt)

    def test_num_events(self, uc):
        assert len(uc.events) == 4

    def test_beat(self, uc):
        assert str(uc.beat) == '1/4'

    def test_tempus(self, uc):
        assert str(uc.tempus) == '4/4'

    def test_onsets(self, uc):
        _ = uc.events
        expected = [0.0, 1.0, 2.0, 3.0]
        actual = [float(o) for o in uc.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, uc):
        _ = uc.events
        expected = [1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in uc.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, uc):
        _ = uc.events
        expected = (1, 2, 3, 4,)
        assert uc.leaf_nodes == expected

    def test_node_0_proportion(self, uc):
        _ = uc.events
        assert uc._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, uc):
        _ = uc.events
        assert uc._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, uc):
        _ = uc.events
        assert uc._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, uc):
        _ = uc.events
        assert uc._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, uc):
        _ = uc.events
        assert uc._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_onset"]) == '3/4'


class Test_uc_nested:
    @pytest.fixture
    def uc(self):
        return UC(tempus='4/4', prolatio=((4, (1, 1, 1)), 2, 1, 1))

    def test_full_structural_equivalence(self, uc):
        _ = uc.events
        key = UC_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["uc"][key]["expected"]
        assert_rt_matches_expected(uc._rt, expected)

    def test_rt_pt_structurally_matched(self, uc):
        _ = uc.events
        assert_rt_pt_structurally_matched(uc._rt, uc._pt)

    def test_num_events(self, uc):
        assert len(uc.events) == 6

    def test_beat(self, uc):
        assert str(uc.beat) == '1/4'

    def test_tempus(self, uc):
        assert str(uc.tempus) == '4/4'

    def test_onsets(self, uc):
        _ = uc.events
        expected = [0.0, 0.6666666666666666, 1.3333333333333333, 2.0, 3.0, 3.5]
        actual = [float(o) for o in uc.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, uc):
        _ = uc.events
        expected = [0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 1.0, 0.5, 0.5]
        actual = [float(d) for d in uc.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, uc):
        _ = uc.events
        expected = (2, 3, 4, 5, 6, 7,)
        assert uc.leaf_nodes == expected

    def test_node_0_proportion(self, uc):
        _ = uc.events
        assert uc._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, uc):
        _ = uc.events
        assert uc._rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, uc):
        _ = uc.events
        assert uc._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, uc):
        _ = uc.events
        assert uc._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, uc):
        _ = uc.events
        assert uc._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, uc):
        _ = uc.events
        assert uc._rt[5].get("proportion") == 2

    def test_node_5_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, uc):
        _ = uc.events
        assert uc._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[6]["metric_duration"]) == '1/8'

    def test_node_6_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[6]["metric_onset"]) == '3/4'

    def test_node_7_proportion(self, uc):
        _ = uc.events
        assert uc._rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, uc):
        _ = uc.events
        assert str(uc._rt[7]["metric_duration"]) == '1/8'

    def test_node_7_metric_onset(self, uc):
        _ = uc.events
        assert str(uc._rt[7]["metric_onset"]) == '7/8'

