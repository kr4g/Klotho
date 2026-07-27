"""Widget HTML assembly: unified bridge, disabled-until-ready buttons.

Automated coverage of what pytest can see (the assembled HTML/JS); the
click-behavior itself is verified manually in Jupyter.
"""
import pytest


class TestControlBar:
    def test_no_status_span_and_disabled_toggle(self):
        from klotho.utils.playback.supersonic._js_fragments import control_bar_html
        html = control_bar_html('w1')
        assert '_status' not in html
        assert 'ready</span>' not in html
        assert 'disabled' in html
        assert 'not-allowed' in html
        assert 'opacity: 0.3' in html


class TestEngineWidgetAssembly:
    def _html(self, **kwargs):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        events = [{
            "type": "new", "id": "a1", "defName": "kl_tri", "start": 0.0,
            "dur": 0.5, "releaseAfter": True,
            "pfields": {"freq": 440.0, "amp": 0.5},
        }]
        return SuperSonicEngine(events, **kwargs)._generate_html()

    def test_widget_uses_shared_bridge_and_lifecycle(self):
        html = self._html()
        assert 'KlothoEngineLifecycle' in html
        assert 'KlothoPlaybackBridge' in html
        assert 'KlothoGateToggle' in html
        assert '_status' not in html

    def test_lifecycle_installed_guarded_once(self):
        html = self._html()
        # the module is guard-wrapped, so double injection is harmless,
        # but a single widget bundle should carry it exactly once
        assert html.count('globalThis.KlothoEngineLifecycle = {') == 1

    def test_play_button_renders_disabled(self):
        html = self._html()
        assert 'disabled' in html


class TestAnimatedFigureAssembly:
    def test_rt_animated_html_gates_toggle(self):
        from klotho.semeios.visualization._dispatch.plot_rt import _plot_rt
        from klotho.chronos.rhythm_trees import RhythmTree
        rt = RhythmTree(span=1, meas='4/4', subdivisions=(1, 1, 1))
        html = _plot_rt(rt, animate=True).to_html()
        assert 'KlothoGateToggle' in html
        assert 'KlothoEngineLifecycle' in html
        assert 'disabled' in html
        assert '_status' not in html

    def test_timeline_animated_html_gates_toggle(self):
        from klotho.semeios.visualization._dispatch.plot_timeline import _plot_timeline
        from klotho.chronos.temporal_units.temporal import (
            TemporalUnit, TemporalUnitSequence,
        )
        uts = TemporalUnitSequence([
            TemporalUnit(tempus='4/4', prolatio=(1, 1), bpm=120),
        ])
        html = _plot_timeline(uts, animate=True).to_html()
        assert 'KlothoGateToggle' in html
        assert 'disabled' in html
