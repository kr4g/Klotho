"""Regression: Contour(Pattern) construction and Contour plotting."""
import os

import matplotlib
matplotlib.use('Agg')

import pytest

from klotho.tonos import Contour
from klotho.topos import Pattern


class TestContourFromPattern:
    def test_matches_manual_iteration(self):
        pattern = Pattern([0, [[[1, -4], [4, [5, [-3, -2]], 6]], [3, -1]]])
        expected = [next(pattern) for _ in range(len(pattern))]
        pattern.reset()
        contour = Contour(pattern)
        assert contour.values == expected

    def test_pattern_state_unchanged(self):
        pattern = Pattern([0, [1, 2]])
        first = next(pattern)
        pos_before = pattern.position
        Contour(pattern)
        assert pattern.position == pos_before
        # Iteration continues where it left off.
        second = next(pattern)
        pattern.reset()
        full = [next(pattern) for _ in range(len(pattern))]
        assert [first, second] == full[:2]

    def test_simple_pattern(self):
        assert Contour(Pattern([0, [1, 2]])).values == [0, 1, 0, 2]

    def test_plain_sequences_still_work(self):
        assert Contour([1, 2, 3]).values == [1, 2, 3]
        assert Contour(Contour([4, 5])).values == [4, 5]

    def test_arithmetic_unchanged(self):
        c = Contour([0, 2, 4])
        assert (c + 5).values == [5, 7, 9]
        assert (c * 2).values == [0, 4, 8]
        assert (-c).values == [0, -2, -4]
        assert Contour.outer([0, 1], [10, 20]).values == [10, 20, 11, 21]


class TestContourPlot:
    def test_plot_smoke(self, tmp_path):
        from klotho.semeios.visualization.plots import _plot_contour
        out = tmp_path / 'contour.png'
        _plot_contour(Contour([0, 2, 4, -1, 3]), output_file=str(out))
        assert out.exists()
        assert out.stat().st_size > 0

    def test_plot_from_pattern(self, tmp_path):
        from klotho.semeios.visualization.plots import _plot_contour
        out = tmp_path / 'contour_pattern.png'
        _plot_contour(Contour(Pattern([0, [1, 2]])), output_file=str(out))
        assert out.exists()

    def test_dispatch_case_exists(self):
        # plot() must dispatch Contour without raising TypeError.
        import inspect
        from klotho.semeios.visualization import plots
        src = inspect.getsource(plots.plot)
        assert 'Contour()' in src

    def test_plot_single_value(self, tmp_path):
        from klotho.semeios.visualization.plots import _plot_contour
        out = tmp_path / 'contour_single.png'
        _plot_contour(Contour([3]), output_file=str(out))
        assert out.exists()
