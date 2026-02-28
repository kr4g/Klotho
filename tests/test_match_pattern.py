import math
import pytest
from klotho.tonos.systems.combination_product_sets import Hexany, Eikosany, match_pattern


class TestHexanyMatchPattern:
    @pytest.fixture
    def hx(self):
        return Hexany()

    def test_triangle_025(self, hx):
        result = match_pattern(hx, [0, 2, 5])
        actual = {tuple(sorted(m)) for m in result}
        expected = {
            (0, 1, 4), (0, 1, 5), (0, 2, 3), (0, 3, 5), (0, 4, 5),
            (1, 2, 3), (1, 2, 4), (1, 3, 4), (1, 4, 5), (2, 3, 4), (2, 3, 5),
        }
        assert actual == expected

    def test_quad_0315(self, hx):
        result = match_pattern(hx, [0, 3, 1, 5])
        actual = {tuple(sorted(m)) for m in result}
        expected = {
            (0, 1, 2, 3), (0, 1, 3, 4), (0, 2, 4, 5), (1, 2, 4, 5), (2, 3, 4, 5),
        }
        assert actual == expected

    def test_quad_2054(self, hx):
        result = match_pattern(hx, [2, 0, 5, 4])
        actual = {tuple(sorted(m)) for m in result}
        expected = {
            (0, 1, 2, 3), (0, 1, 3, 4), (0, 1, 3, 5), (1, 2, 4, 5), (2, 3, 4, 5),
        }
        assert actual == expected

    def test_triangle_231(self, hx):
        result = match_pattern(hx, [2, 3, 1])
        actual = {tuple(sorted(m)) for m in result}
        expected = {
            (0, 1, 4), (0, 1, 5), (0, 2, 3), (0, 2, 5), (0, 3, 5),
            (0, 4, 5), (1, 2, 4), (1, 3, 4), (1, 4, 5), (2, 3, 4), (2, 3, 5),
        }
        assert actual == expected

    def test_same_target_different_order(self, hx):
        r1 = match_pattern(hx, [0, 2, 5])
        r2 = match_pattern(hx, [5, 0, 2])
        assert {tuple(sorted(m)) for m in r1} == {tuple(sorted(m)) for m in r2}


class TestEikosanyAsteriskMatchPattern:
    @pytest.fixture
    def ek(self):
        return Eikosany(master_set='asterisk')

    def test_6node_pattern(self, ek):
        result = match_pattern(ek, [11, 6, 10, 15, 18, 8])
        assert len(result) == 19

    def test_4node_pattern_11_6_10_14(self, ek):
        result = match_pattern(ek, [11, 6, 10, 14])
        assert len(result) == 19

    def test_4node_pattern_6_14_17_12(self, ek):
        result = match_pattern(ek, [6, 14, 17, 12])
        assert len(result) == 19

    def test_5node_pattern(self, ek):
        result = match_pattern(ek, [11, 6, 10, 8, 1])
        assert len(result) == 19


class TestEikosanyCenteredPentagonMatchPattern:
    @pytest.fixture
    def ek(self):
        return Eikosany(master_set='centered_pentagon')

    def test_quad_12_14_11_13(self, ek):
        result = match_pattern(ek, [12, 14, 11, 13])
        actual = {tuple(sorted(m)) for m in result}
        expected = {
            (0, 1, 6, 8), (1, 2, 4, 5), (1, 2, 8, 9), (2, 3, 5, 6),
            (5, 6, 7, 8), (10, 11, 17, 18), (11, 13, 18, 19),
            (13, 14, 16, 17), (14, 15, 17, 18),
        }
        assert actual == expected

    def test_no_coincident_positions(self, ek):
        positions = ek.positions
        nodes = sorted(positions.keys())
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                d = math.sqrt(sum(
                    (positions[nodes[i]][k] - positions[nodes[j]][k]) ** 2
                    for k in range(len(positions[nodes[i]]))
                ))
                assert d > 1e-6, (
                    f"Nodes {nodes[i]} and {nodes[j]} are coincident"
                )


class TestEikosanyIrregularHexagonMatchPattern:
    @pytest.fixture
    def ek(self):
        return Eikosany(master_set='irregular_hexagon')

    def test_4node_11_16_4_0(self, ek):
        result = match_pattern(ek, [11, 16, 4, 0])
        actual = {tuple(sorted(m)) for m in result}
        expected = {(0, 5, 12, 18), (1, 7, 14, 19), (3, 8, 15, 19)}
        assert actual == expected

    def test_4node_18_6_8_19(self, ek):
        result = match_pattern(ek, [18, 6, 8, 19])
        actual = {tuple(sorted(m)) for m in result}
        expected = {(0, 1, 11, 13), (0, 3, 5, 9), (10, 14, 16, 19)}
        assert actual == expected

    def test_6node_no_false_positives(self, ek):
        result = match_pattern(ek, [0, 11, 5, 16, 18, 19])
        actual = {tuple(sorted(m)) for m in result}
        expected = {(0, 1, 3, 8, 14, 19)}
        assert actual == expected


class TestStructuralCorrespondence:
    def test_match_ordering_preserves_structure(self):
        hx = Hexany()
        positions = hx.positions
        target = [0, 3, 1, 5]

        ref_matrix = []
        for i in range(len(target)):
            row = []
            for j in range(len(target)):
                pi, pj = positions[target[i]], positions[target[j]]
                row.append(round(math.sqrt(sum((a - b) ** 2 for a, b in zip(pi, pj))), 6))
            ref_matrix.append(row)

        for match in match_pattern(hx, target):
            match_matrix = []
            for i in range(len(match)):
                row = []
                for j in range(len(match)):
                    pi, pj = positions[match[i]], positions[match[j]]
                    row.append(round(math.sqrt(sum((a - b) ** 2 for a, b in zip(pi, pj))), 6))
                match_matrix.append(row)

            for i in range(len(target)):
                for j in range(len(target)):
                    assert abs(ref_matrix[i][j] - match_matrix[i][j]) < 1e-4, (
                        f"Structural mismatch at [{i}][{j}]: "
                        f"target pair ({target[i]},{target[j]}) dist={ref_matrix[i][j]}, "
                        f"match pair ({match[i]},{match[j]}) dist={match_matrix[i][j]}"
                    )

    def test_position_sort_order_invariant_to_target_ordering(self):
        hx = Hexany()
        r1 = match_pattern(hx, [0, 3, 1, 5])
        r2 = match_pattern(hx, [3, 0, 5, 1])

        s1 = [tuple(sorted(m)) for m in r1]
        s2 = [tuple(sorted(m)) for m in r2]
        assert s1 == s2

    def test_reordered_target_changes_internal_node_order(self):
        hx = Hexany()
        r1 = match_pattern(hx, [0, 3, 1, 5])
        r2 = match_pattern(hx, [3, 0, 5, 1])

        assert {tuple(sorted(m)) for m in r1} == {tuple(sorted(m)) for m in r2}
        assert [tuple(m) for m in r1] != [tuple(m) for m in r2]

    def test_rotation_sort_differs_from_position_sort(self):
        hx = Hexany()
        target = [0, 4, 3]
        r_pos = match_pattern(hx, target, sort_by='position')
        r_rot = match_pattern(hx, target, sort_by='rotation')
        assert {tuple(sorted(m)) for m in r_pos} == {tuple(sorted(m)) for m in r_rot}


class TestIncludeTarget:
    def test_include_target_prepends(self):
        hx = Hexany()
        target = [0, 2, 5]
        result = match_pattern(hx, target, include_target=True)
        assert result[0] == tuple(target)
        assert len(result) == 12

    def test_exclude_target_default(self):
        hx = Hexany()
        result = match_pattern(hx, [0, 2, 5])
        assert len(result) == 11

    def test_include_target_with_small_input(self):
        hx = Hexany()
        result = match_pattern(hx, [0, 1], include_target=True)
        assert result == [(0, 1)]

    def test_include_target_preserves_order(self):
        hx = Hexany()
        target = [5, 0, 2]
        result = match_pattern(hx, target, include_target=True)
        assert result[0] == (5, 0, 2)


class TestEdgeCases:
    def test_less_than_3_nodes_returns_empty(self):
        hx = Hexany()
        assert match_pattern(hx, [0, 1]) == []

    def test_positions_exist(self):
        hx = Hexany()
        assert len(hx.positions) == 6

    def test_eikosany_positions_count(self):
        ek = Eikosany(master_set='asterisk')
        assert len(ek.positions) == 20
