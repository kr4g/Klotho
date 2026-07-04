"""Smoke tests: plot(obj).play() pipeline runs end-to-end for RT / Lattice / CPS / MasterSet / UTS / BT."""
from unittest.mock import patch

import pytest

from klotho.chronos.rhythm_trees import RhythmTree
from klotho.chronos.temporal_units.temporal import (
    TemporalUnit, TemporalUnitSequence, TemporalBlock,
)
from klotho.thetos.composition.compositional import CompositionalUnit
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
        nodes_list = list(cps.nodes)[:3]
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


def _u1():
    return TemporalUnit(tempus='4/4', prolatio=(1, 2, 1), bpm=120)


def _u2():
    return TemporalUnit(tempus='3/4', prolatio='p', bpm=90)


def _u3():
    return TemporalUnit(tempus='5/8', prolatio=(2, -1, 3), bpm=100)


def _uc():
    return CompositionalUnit(tempus='4/4', prolatio=(1, 1, 2), bpm=100)


def _timeline_cases():
    return {
        'flat_uts': TemporalUnitSequence([_u1(), _u2(), _u3()]),
        'flat_bt': TemporalBlock([_u1(), _u2(), _u3()], sort_rows=False),
        'uts_with_bt': TemporalUnitSequence([_u1(), TemporalBlock([_u2(), _u3()]), _u2()]),
        'bt_with_uts': TemporalBlock([TemporalUnitSequence([_u1(), _u2()]), _u3()], sort_rows=False),
        'nested_bt': TemporalBlock(
            [TemporalBlock([_u1(), _u2()]), TemporalUnitSequence([_u3(), _u1()])],
            sort_rows=False),
        'uts_with_uc': TemporalUnitSequence([_u1(), _uc()]),
        'bt_with_uc': TemporalBlock([_uc(), _u2()], sort_rows=False),
    }


class TestSmokeTimelinePlotPlay:
    """plot() returns a KlothoPlot for UTS/BT and the static SVG renders."""

    @pytest.mark.parametrize('case', sorted(_timeline_cases()))
    def test_static(self, case):
        obj = _timeline_cases()[case]
        p = plot(obj)
        assert isinstance(p, KlothoPlot)
        _assert_renderable(p)

    def test_non_ratios_layout_rejected(self):
        from klotho.semeios.visualization._dispatch import _plot_timeline
        with pytest.raises(ValueError, match='ratios'):
            _plot_timeline(_timeline_cases()['flat_uts'], layout='containers')

    def test_empty_container_rejected(self):
        from klotho.semeios.visualization._dispatch import _plot_timeline
        with pytest.raises(ValueError):
            _plot_timeline(TemporalUnitSequence())


class TestTimelineAnimated:
    """Exercise the animate=True code path for UTS/BT."""

    @pytest.mark.parametrize('case', sorted(_timeline_cases()))
    def test_animate(self, case):
        from klotho.semeios.visualization._dispatch import _plot_timeline
        obj = _timeline_cases()[case]
        fig = _plot_timeline(obj, animate=True)
        html = fig.to_html()
        assert isinstance(html, str) and len(html) > 0


class TestTimelineStepConsistency:
    """Renderer step count == global _stepIndex range in both engines' payloads."""

    @pytest.mark.parametrize('case', sorted(_timeline_cases()))
    def test_step_indices_match(self, case):
        from klotho.semeios.visualization._renderers.svg_timeline import (
            _resolve_lanes, _svg_timeline_ratios,
        )
        from klotho.utils.playback.tonejs.converters import (
            temporal_container_to_animation_events,
        )
        from klotho.utils.playback.supersonic.converters import (
            temporal_container_to_sc_animation_events,
        )

        obj = _timeline_cases()[case]
        placements, _, _ = _resolve_lanes(obj)
        total_steps = sum(len(p.unit._rt.leaf_nodes) for p in placements)

        sd = _svg_timeline_ratios(obj)
        assert len(sd.step_element_ids) == total_steps
        assert len(sd.step_halo_ids) == total_steps
        assert len(sd.step_durations) == total_steps

        tone = temporal_container_to_animation_events(obj)
        tone_steps = {ev['_stepIndex'] for ev in tone['events']
                      if ev.get('_stepIndex') is not None}
        assert tone_steps == set(range(total_steps))
        assert min(ev['start'] for ev in tone['events']) == 0.0

        sc = temporal_container_to_sc_animation_events(obj)
        sc_steps = {ev['_stepIndex'] for ev in sc
                    if ev.get('_stepIndex') is not None}
        assert sc_steps == set(range(total_steps))
        assert min(ev['start'] for ev in sc) >= 0.0


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
        nodes_list = list(cps.nodes)[:3]
        fig = _plot_cps(cps, path=nodes_list, animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)

    def test_master_set_animate_with_path(self):
        from klotho.semeios.visualization._dispatch.plot_cps import _plot_master_set
        ms = MasterSet.hexagon().with_factors((1, 3, 5, 7, 9, 11))
        fig = _plot_master_set(ms, path=['A', 'B', 'C'], animate=True)
        assert hasattr(fig, 'to_html')
        assert isinstance(fig.to_html(), str)
