"""Regression: shortest_path must not duplicate the start coordinate."""
import pytest

from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.topos.graphs.lattices.algorithms import shortest_path


class TestShortestPathNoDuplicate:
    def test_no_consecutive_duplicates_2d(self):
        tl = ToneLattice(2, resolution=3)
        sp = shortest_path(tl, (0, 0), (3, -2))
        assert len(sp) == 6, f"expected 6 nodes, got {len(sp)}: {sp}"
        for i in range(len(sp) - 1):
            assert sp[i] != sp[i + 1], (
                f"duplicate consecutive coords at idx {i}: {sp}"
            )

    def test_endpoints_correct(self):
        tl = ToneLattice(2, resolution=3)
        sp = shortest_path(tl, (0, 0), (2, 1))
        assert sp[0] == (0, 0)
        assert sp[-1] == (2, 1)
        # 2 + 1 manhattan steps ⇒ 4 nodes
        assert len(sp) == 4

    def test_no_duplicate_start(self):
        tl = ToneLattice(2, resolution=3)
        sp = shortest_path(tl, (0, 0), (1, 0))
        assert sp.count((0, 0)) == 1, f"start coord duplicated: {sp}"

    def test_3d_lattice(self):
        tl = ToneLattice(3, resolution=2)
        sp = shortest_path(tl, (0, 0, 0), (1, 1, 1))
        assert sp[0] == (0, 0, 0)
        assert sp[-1] == (1, 1, 1)
        assert len(sp) == 4
        for i in range(len(sp) - 1):
            assert sp[i] != sp[i + 1]
