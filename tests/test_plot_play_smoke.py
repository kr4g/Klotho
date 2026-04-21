"""Smoke tests: plot(obj).play() pipeline runs end-to-end for RT / Lattice / CPS / MasterSet."""
from unittest.mock import patch

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.tonos.systems.tone_lattices.tone_lattices import ToneLattice
from klotho.tonos.systems.combination_product_sets import (
    CombinationProductSet, MasterSet,
)
from klotho.topos.graphs.lattices.algorithms import shortest_path
from klotho.semeios.visualization.plots import plot
from klotho.semeios.visualization._dispatch import KlothoPlot


@pytest.fixture(autouse=True)
def _mute_display(monkeypatch):
    """Swallow IPython.display calls so tests can run headless."""
    import IPython.display
    monkeypatch.setattr(IPython.display, 'display', lambda *a, **k: None)


def _assert_renderable(fig):
    assert fig is not None
    assert callable(getattr(fig, 'play', None))
    # Accessing .play requires session boot; invoke the static build instead.
    static = fig._build_static()
    assert static is not None
    if hasattr(static, 'to_html'):
        html = static.to_html()
        assert isinstance(html, str) and len(html) > 0


class TestSmokePlotPlay:
    def test_rhythm_tree(self):
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 2, 1))
        p = plot(rt)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_tone_lattice_2d_plain(self):
        tl = ToneLattice(2, resolution=2)
        p = plot(tl)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_tone_lattice_2d_with_shortest_path(self):
        tl = ToneLattice(2, resolution=3)
        sp = shortest_path(tl, (0, 0), (2, 1))
        p = plot(tl, path=sp)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_cps_plain(self):
        cps = CombinationProductSet.hexany()
        p = plot(cps)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_cps_with_path(self):
        cps = CombinationProductSet.hexany()
        nodes_list = list(cps.graph.nodes)[:3]
        p = plot(cps, path=nodes_list)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_master_set_2d_plain(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        p = plot(ms)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_master_set_2d_with_path(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        p = plot(ms, path=['A', 'B', 'C'])
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_master_set_2d_with_shape(self):
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        p = plot(ms, shape=['A', 'B', 'C'])
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_master_set_3d(self):
        ms = MasterSet.octahedron().with_factors((1, 3, 5, 7, 9, 11))
        p = plot(ms)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)


class TestAnimatedPath:
    """Exercise the animate=True code path, which is what .play() triggers."""

    def test_rt_animate(self):
        from klotho.semeios.visualization._dispatch.plot_rt import _plot_rt
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1, 1))
        fig = _plot_rt(rt, animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)

    def test_lattice_animate_with_path(self):
        from klotho.semeios.visualization._dispatch.plot_lattice import _plot_lattice
        tl = ToneLattice(2, resolution=3)
        fig = _plot_lattice(tl, path=[(0, 0), (1, 0), (1, 1)], animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)

    def test_cps_animate_with_path(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_cps
        cps = CombinationProductSet.hexany()
        nodes_list = list(cps.graph.nodes)[:3]
        fig = _plot_cps(cps, path=nodes_list, animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)

    def test_master_set_animate_with_path(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_master_set
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, path=['A', 'B', 'C'], animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)
