"""Tests for TemporalUnit."""
import pytest
from fractions import Fraction
from klotho.chronos import TemporalUnit as UT
from tree_helpers import assert_rt_matches_expected
from conftest import get_expected_trees

UT_EXPECTED_KEY = {
    "Test_default_ut": "default_ut",
    "Test_default_ut_120bpm": "default_ut_120bpm",
    "Test_ut_3_4_pulse": "ut_3_4_pulse",
    "Test_ut_6_8_pulse_90bpm": "ut_6_8_pulse_90bpm",
    "Test_ut_4_4_subdivisions": "ut_4_2_1_1",
    "Test_ut_3_4_subdivisions": "ut_complex",
    "Test_ut_5_4_span2": "ut_span2_5_4",
    "Test_ut_7_8_120bpm": "ut_7_8_2_3_2",
    "Test_ut_rest": "ut_rest",
    "Test_ut_duration": "ut_duration",
    "Test_ut_2_4_pulse": "ut_2_4_pulse",
    "Test_ut_3_4_pulse_alt": "ut_3_4_pulse_alt",
    "Test_ut_5_8_pulse": "ut_5_8_pulse",
    "Test_ut_7_8_pulse": "ut_7_8_pulse",
    "Test_ut_6_4_pulse": "ut_6_4_pulse",
    "Test_ut_2_4_60bpm": "ut_2_4_60",
    "Test_ut_2_4_90bpm": "ut_2_4_90",
    "Test_ut_2_4_120bpm": "ut_2_4_120",
    "Test_ut_2_4_200bpm": "ut_2_4_200",
    "Test_ut_3_8_60bpm": "ut_3_8_60",
    "Test_ut_3_8_90bpm": "ut_3_8_90",
    "Test_ut_3_8_120bpm": "ut_3_8_120",
    "Test_ut_3_8_200bpm": "ut_3_8_200",
    "Test_ut_5_4_60bpm": "ut_5_4_60",
    "Test_ut_5_4_90bpm": "ut_5_4_90",
    "Test_ut_5_4_120bpm": "ut_5_4_120",
    "Test_ut_5_4_200bpm": "ut_5_4_200",
    "Test_ut_span1_4_4": "ut_span1",
    "Test_ut_span2_4_4": "ut_span2",
    "Test_ut_span3_4_4": "ut_span3",
    "Test_ut_span4_4_4": "ut_span4",
    "Test_ut_nested_complex": "ut_nested_120",
    "Test_ut_accel_120bpm": "ut_accel",
    "Test_ut_offset": "ut_offset",
}


class Test_default_ut:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 1

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [4.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_rt_pure_no_real_times(self, ut):
        _ = ut.events
        rt_copy = ut.rt
        for node in rt_copy.nodes:
            assert 'real_onset' not in rt_copy[node]
            assert 'real_duration' not in rt_copy[node]

    def test_nodes_view_has_real_times(self, ut):
        _ = ut.events
        for node in ut.nodes:
            assert 'real_onset' in ut.nodes[node]
            assert 'real_duration' in ut.nodes[node]

    def test_nodes_view_has_metric_and_real(self, ut):
        _ = ut.events
        for node in ut.nodes:
            assert ut.nodes[node]['metric_duration'] == ut._rt[node]['metric_duration']
            assert ut.nodes[node]['proportion'] == ut._rt[node]['proportion']
        for i, node in enumerate(ut.leaf_nodes):
            assert ut.nodes[node]['real_onset'] == pytest.approx(float(ut[i].start), abs=1e-10)
            assert ut.nodes[node]['real_duration'] == pytest.approx(float(ut[i].duration), abs=1e-10)


class Test_default_ut_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 1

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [2.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'


class Test_ut_3_4_pulse_alt:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'


class Test_ut_6_8_pulse_90bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='6/8', prolatio='p', bpm=90)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 6

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 90

    def test_tempus(self, ut):
        assert str(ut.tempus) == '6/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.6666666666666666, 1.3333333333333333, 2.0, 2.6666666666666665, 3.333333333333333]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5, 6,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 6

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/8'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/8'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '5/8'


class Test_ut_4_4_subdivisions:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio=(4, 2, 1, 1))

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 2.0, 3.0, 3.5]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [2.0, 1.0, 0.5, 0.5]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 2

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/2'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '3/4'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '7/8'


class Test_ut_3_4_subdivisions:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/4', prolatio=((3, (1, (2, (-1, 1, 1)))), (5, (1, -2, (1, (1, 1)), 1)), (3, (-1, 1, 1)), (5, (2, 1))))

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 14

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.1875, 0.3125, 0.4375, 0.5625, 0.75, 1.125, 1.21875, 1.3125, 1.5, 1.6875, 1.875, 2.0625, 2.6875]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.1875, -0.125, 0.125, 0.125, 0.1875, -0.375, 0.09375, 0.09375, 0.1875, -0.1875, 0.1875, 0.1875, 0.625, 0.3125]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (2, 4, 5, 6, 8, 9, 11, 12, 13, 15, 16, 17, 19, 20,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 3

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '9/64'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '3/64'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '3/32'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '3/64'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == -1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '-1/32'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/64'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/32'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '5/64'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/32'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '7/64'

    def test_node_7_proportion(self, ut):
        _ = ut.events
        assert ut._rt[7].get("proportion") == 5

    def test_node_7_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_duration"]) == '15/64'

    def test_node_7_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_onset"]) == '9/64'

    def test_node_8_proportion(self, ut):
        _ = ut.events
        assert ut._rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_duration"]) == '3/64'

    def test_node_8_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_onset"]) == '9/64'

    def test_node_9_proportion(self, ut):
        _ = ut.events
        assert ut._rt[9].get("proportion") == -2

    def test_node_9_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_duration"]) == '-3/32'

    def test_node_9_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_onset"]) == '3/16'

    def test_node_10_proportion(self, ut):
        _ = ut.events
        assert ut._rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[10]["metric_duration"]) == '3/64'

    def test_node_10_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[10]["metric_onset"]) == '9/32'

    def test_node_11_proportion(self, ut):
        _ = ut.events
        assert ut._rt[11].get("proportion") == 1

    def test_node_11_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[11]["metric_duration"]) == '3/128'

    def test_node_11_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[11]["metric_onset"]) == '9/32'

    def test_node_12_proportion(self, ut):
        _ = ut.events
        assert ut._rt[12].get("proportion") == 1

    def test_node_12_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[12]["metric_duration"]) == '3/128'

    def test_node_12_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[12]["metric_onset"]) == '39/128'

    def test_node_13_proportion(self, ut):
        _ = ut.events
        assert ut._rt[13].get("proportion") == 1

    def test_node_13_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[13]["metric_duration"]) == '3/64'

    def test_node_13_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[13]["metric_onset"]) == '21/64'

    def test_node_14_proportion(self, ut):
        _ = ut.events
        assert ut._rt[14].get("proportion") == 3

    def test_node_14_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[14]["metric_duration"]) == '9/64'

    def test_node_14_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[14]["metric_onset"]) == '3/8'

    def test_node_15_proportion(self, ut):
        _ = ut.events
        assert ut._rt[15].get("proportion") == -1

    def test_node_15_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[15]["metric_duration"]) == '-3/64'

    def test_node_15_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[15]["metric_onset"]) == '3/8'

    def test_node_16_proportion(self, ut):
        _ = ut.events
        assert ut._rt[16].get("proportion") == 1

    def test_node_16_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[16]["metric_duration"]) == '3/64'

    def test_node_16_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[16]["metric_onset"]) == '27/64'

    def test_node_17_proportion(self, ut):
        _ = ut.events
        assert ut._rt[17].get("proportion") == 1

    def test_node_17_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[17]["metric_duration"]) == '3/64'

    def test_node_17_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[17]["metric_onset"]) == '15/32'

    def test_node_18_proportion(self, ut):
        _ = ut.events
        assert ut._rt[18].get("proportion") == 5

    def test_node_18_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[18]["metric_duration"]) == '15/64'

    def test_node_18_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[18]["metric_onset"]) == '33/64'

    def test_node_19_proportion(self, ut):
        _ = ut.events
        assert ut._rt[19].get("proportion") == 2

    def test_node_19_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[19]["metric_duration"]) == '5/32'

    def test_node_19_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[19]["metric_onset"]) == '33/64'

    def test_node_20_proportion(self, ut):
        _ = ut.events
        assert ut._rt[20].get("proportion") == 1

    def test_node_20_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[20]["metric_duration"]) == '5/64'

    def test_node_20_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[20]["metric_onset"]) == '43/64'


class Test_ut_5_4_span2:
    @pytest.fixture
    def ut(self):
        return UT(span=2, tempus='5/4', prolatio=((1, (1, 1, 1)), 1, 1, (1, (1, 1)), 1))

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 8

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 10.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.6666666666666666, 1.3333333333333333, 2.0, 4.0, 6.0, 7.0, 8.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 2.0, 2.0, 1.0, 1.0, 2.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (2, 3, 4, 5, 6, 8, 9, 10,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 10

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/2'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/2'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '1'

    def test_node_7_proportion(self, ut):
        _ = ut.events
        assert ut._rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_duration"]) == '1/2'

    def test_node_7_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_onset"]) == '3/2'

    def test_node_8_proportion(self, ut):
        _ = ut.events
        assert ut._rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_duration"]) == '1/4'

    def test_node_8_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_onset"]) == '3/2'

    def test_node_9_proportion(self, ut):
        _ = ut.events
        assert ut._rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_duration"]) == '1/4'

    def test_node_9_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_onset"]) == '7/4'

    def test_node_10_proportion(self, ut):
        _ = ut.events
        assert ut._rt[10].get("proportion") == 1

    def test_node_10_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[10]["metric_duration"]) == '1/2'

    def test_node_10_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[10]["metric_onset"]) == '2'


class Test_ut_7_8_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='7/8', prolatio=(2, 3, 2), bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '7/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.5

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.5]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.5, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 7

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '7/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 2

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 3

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '3/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 2

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '5/8'


class Test_ut_rest:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio='r')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 1

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [-4.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == -1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '-1'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'


class Test_ut_duration:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio='d')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 1

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [4.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'


class Test_ut_2_4_pulse:
    @pytest.fixture
    def ut(self):
        return UT(tempus='2/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 2

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '2/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'


class Test_ut_3_4_pulse:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'


class Test_ut_5_8_pulse:
    @pytest.fixture
    def ut(self):
        return UT(tempus='5/8', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 5

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 5.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0, 3.0, 4.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/8'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1/2'


class Test_ut_7_8_pulse:
    @pytest.fixture
    def ut(self):
        return UT(tempus='7/8', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 7

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '7/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 7.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5, 6, 7,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 7

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '7/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/8'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/8'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/8'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1/2'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/8'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '5/8'

    def test_node_7_proportion(self, ut):
        _ = ut.events
        assert ut._rt[7].get("proportion") == 1

    def test_node_7_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_duration"]) == '1/8'

    def test_node_7_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_onset"]) == '3/4'


class Test_ut_6_4_pulse:
    @pytest.fixture
    def ut(self):
        return UT(tempus='6/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 6

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '6/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 6.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5, 6,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 6

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/4'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '5/4'


class Test_ut_2_4_60bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='2/4', prolatio='p', bpm=60)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 2

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '2/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'


class Test_ut_2_4_90bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='2/4', prolatio='p', bpm=90)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 2

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 90

    def test_tempus(self, ut):
        assert str(ut.tempus) == '2/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 1.3333333333333333

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.6666666666666666]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.6666666666666666, 0.6666666666666666]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'


class Test_ut_2_4_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='2/4', prolatio='p', bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 2

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '2/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 1.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.5]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.5, 0.5]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'


class Test_ut_2_4_200bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='2/4', prolatio='p', bpm=200)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 2

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 200

    def test_tempus(self, ut):
        assert str(ut.tempus) == '2/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 0.6

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.3]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.3, 0.3]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 2

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/2'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'


class Test_ut_3_8_60bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/8', prolatio='p', bpm=60)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'


class Test_ut_3_8_90bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/8', prolatio='p', bpm=90)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 90

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.6666666666666666, 1.3333333333333333]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.6666666666666666, 0.6666666666666666, 0.6666666666666666]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'


class Test_ut_3_8_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/8', prolatio='p', bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 1.5

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.5, 1.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.5, 0.5, 0.5]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'


class Test_ut_3_8_200bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='3/8', prolatio='p', bpm=200)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 3

    def test_beat(self, ut):
        assert str(ut.beat) == '1/8'

    def test_bpm(self, ut):
        assert ut.bpm == 200

    def test_tempus(self, ut):
        assert str(ut.tempus) == '3/8'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 0.8999999999999999

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.3, 0.6]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.3, 0.3, 0.3]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 3

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/8'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/8'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/8'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/8'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/8'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/4'


class Test_ut_5_4_60bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='5/4', prolatio='p', bpm=60)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 5

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 5.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0, 3.0, 4.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1'


class Test_ut_5_4_90bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='5/4', prolatio='p', bpm=90)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 5

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 90

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 3.333333333333333

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.6666666666666666, 1.3333333333333333, 2.0, 2.6666666666666665]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666, 0.6666666666666666]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1'


class Test_ut_5_4_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='5/4', prolatio='p', bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 5

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.5

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.5, 1.0, 1.5, 2.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.5, 0.5, 0.5, 0.5, 0.5]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1'


class Test_ut_5_4_200bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='5/4', prolatio='p', bpm=200)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 5

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 200

    def test_tempus(self, ut):
        assert str(ut.tempus) == '5/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 1.5

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.3, 0.6, 0.8999999999999999, 1.2]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.3, 0.3, 0.3, 0.3, 0.3]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 5

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '5/4'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/4'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1'


class Test_ut_span1_4_4:
    @pytest.fixture
    def ut(self):
        return UT(span=1, tempus='4/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 1.0, 2.0, 3.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'


class Test_ut_span2_4_4:
    @pytest.fixture
    def ut(self):
        return UT(span=2, tempus='4/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 8.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 2.0, 4.0, 6.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [2.0, 2.0, 2.0, 2.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 8

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '2/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/2'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/2'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/2'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/2'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/2'


class Test_ut_span3_4_4:
    @pytest.fixture
    def ut(self):
        return UT(span=3, tempus='4/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 12.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 3.0, 6.0, 9.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [3.0, 3.0, 3.0, 3.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 12

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '3/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '3/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '3/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '3/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '3/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '3/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '3/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '9/4'


class Test_ut_span4_4_4:
    @pytest.fixture
    def ut(self):
        return UT(span=4, tempus='4/4', prolatio='p')

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 16.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 4.0, 8.0, 12.0]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [4.0, 4.0, 4.0, 4.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 16

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '4/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3'


class Test_ut_nested_complex:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio=((4, (1, 1, (1, (1, 1)))), 2, 1, 1), bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 7

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.3333333333333333, 0.6666666666666666, 0.8333333333333334, 1.0, 1.5, 1.75]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.3333333333333333, 0.3333333333333333, 0.16666666666666666, 0.16666666666666666, 0.5, 0.25, 0.25]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (2, 3, 5, 6, 7, 8, 9,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 4

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/2'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/6'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '0'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/6'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/6'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '1/3'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 1

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/12'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '1/3'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 1

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/12'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '5/12'

    def test_node_7_proportion(self, ut):
        _ = ut.events
        assert ut._rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_duration"]) == '1/4'

    def test_node_7_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_onset"]) == '1/2'

    def test_node_8_proportion(self, ut):
        _ = ut.events
        assert ut._rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_duration"]) == '1/8'

    def test_node_8_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_onset"]) == '3/4'

    def test_node_9_proportion(self, ut):
        _ = ut.events
        assert ut._rt[9].get("proportion") == 1

    def test_node_9_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_duration"]) == '1/8'

    def test_node_9_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[9]["metric_onset"]) == '7/8'


class Test_ut_accel_120bpm:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio=(8, 7, 6, 5, 4, 3, 2, 1), bpm=120)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 8

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 120

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 2.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [0.0, 0.4444444444444444, 0.8333333333333334, 1.1666666666666667, 1.4444444444444444, 1.6666666666666667, 1.8333333333333333, 1.9444444444444444]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [0.4444444444444444, 0.3888888888888889, 0.3333333333333333, 0.2777777777777778, 0.2222222222222222, 0.16666666666666666, 0.1111111111111111, 0.05555555555555555]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4, 5, 6, 7, 8,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 8

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '2/9'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 7

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '7/36'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '2/9'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 6

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/6'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '5/12'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 5

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '5/36'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '7/12'

    def test_node_5_proportion(self, ut):
        _ = ut.events
        assert ut._rt[5].get("proportion") == 4

    def test_node_5_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_duration"]) == '1/9'

    def test_node_5_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[5]["metric_onset"]) == '13/18'

    def test_node_6_proportion(self, ut):
        _ = ut.events
        assert ut._rt[6].get("proportion") == 3

    def test_node_6_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_duration"]) == '1/12'

    def test_node_6_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[6]["metric_onset"]) == '5/6'

    def test_node_7_proportion(self, ut):
        _ = ut.events
        assert ut._rt[7].get("proportion") == 2

    def test_node_7_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_duration"]) == '1/18'

    def test_node_7_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[7]["metric_onset"]) == '11/12'

    def test_node_8_proportion(self, ut):
        _ = ut.events
        assert ut._rt[8].get("proportion") == 1

    def test_node_8_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_duration"]) == '1/36'

    def test_node_8_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[8]["metric_onset"]) == '35/36'


class Test_ut_offset:
    @pytest.fixture
    def ut(self):
        return UT(tempus='4/4', prolatio='p', bpm=60, offset=2.5)

    def test_full_structural_equivalence(self, ut):
        _ = ut.events
        key = UT_EXPECTED_KEY[self.__class__.__name__]
        expected = get_expected_trees()["ut"][key]["expected"]
        assert_rt_matches_expected(ut._rt, expected)

    def test_num_events(self, ut):
        assert len(ut.events) == 4

    def test_beat(self, ut):
        assert str(ut.beat) == '1/4'

    def test_bpm(self, ut):
        assert ut.bpm == 60

    def test_tempus(self, ut):
        assert str(ut.tempus) == '4/4'

    def test_total_duration(self, ut):
        assert pytest.approx(float(ut.duration), abs=1e-10) == 4.0

    def test_onsets(self, ut):
        _ = ut.events
        expected = [2.5, 3.5, 4.5, 5.5]
        actual = [float(o) for o in ut.onsets]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_durations(self, ut):
        _ = ut.events
        expected = [1.0, 1.0, 1.0, 1.0]
        actual = [float(d) for d in ut.durations]
        assert actual == pytest.approx(expected, abs=1e-10)

    def test_leaf_nodes_order(self, ut):
        _ = ut.events
        expected = (1, 2, 3, 4,)
        assert ut.leaf_nodes == expected

    def test_node_0_proportion(self, ut):
        _ = ut.events
        assert ut._rt[0].get("proportion") == 4

    def test_node_0_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_duration"]) == '1/1'

    def test_node_0_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[0]["metric_onset"]) == '0'

    def test_node_1_proportion(self, ut):
        _ = ut.events
        assert ut._rt[1].get("proportion") == 1

    def test_node_1_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_duration"]) == '1/4'

    def test_node_1_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[1]["metric_onset"]) == '0'

    def test_node_2_proportion(self, ut):
        _ = ut.events
        assert ut._rt[2].get("proportion") == 1

    def test_node_2_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_duration"]) == '1/4'

    def test_node_2_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[2]["metric_onset"]) == '1/4'

    def test_node_3_proportion(self, ut):
        _ = ut.events
        assert ut._rt[3].get("proportion") == 1

    def test_node_3_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_duration"]) == '1/4'

    def test_node_3_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[3]["metric_onset"]) == '1/2'

    def test_node_4_proportion(self, ut):
        _ = ut.events
        assert ut._rt[4].get("proportion") == 1

    def test_node_4_metric_duration(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_duration"]) == '1/4'

    def test_node_4_metric_onset(self, ut):
        _ = ut.events
        assert str(ut._rt[4]["metric_onset"]) == '3/4'

