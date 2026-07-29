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


class TestRecordControls:
    """record=True adds the record button/stems checkbox; defaults change nothing."""

    def _score_payload(self):
        from klotho.thetos.composition.score import Score
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )
        s = Score()
        s.track('drums')
        s.new(start=0.0, dur=0.5, inst=SynthDefInstrument.sampler('bb_kick'),
              track='drums', amp=0.7)
        return convert_score_to_sc_events(s)

    def _engine(self, **kwargs):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        payload = self._score_payload()
        return SuperSonicEngine(
            payload["events"], meta=payload.get("meta"),
            control_data=payload.get("control_data"), **kwargs)

    def test_control_bar_defaults_unchanged(self):
        from klotho.utils.playback.supersonic._js_fragments import control_bar_html
        assert control_bar_html('w1') == control_bar_html('w1', record=False,
                                                          stems=False)
        assert '_rec' not in control_bar_html('w1')

    def test_control_bar_record_and_stems_markup(self):
        from klotho.utils.playback.supersonic._js_fragments import control_bar_html
        html = control_bar_html('w1', record=True, stems=True)
        assert 'id="w1_rec"' in html
        assert 'id="w1_stems"' in html
        assert 'id="w1_dl"' in html
        # record button renders disabled/greyed until the gate enables it
        assert html.index('id="w1_toggle"') < html.index('id="w1_rec"') \
            < html.index('id="w1_loop"')
        no_stems = control_bar_html('w1', record=True, stems=False)
        assert 'id="w1_rec"' in no_stems and 'id="w1_stems"' not in no_stems

    def test_record_widget_has_recorder_and_controls(self):
        eng = self._engine(record=True)
        html = eng._generate_html()
        wid = eng.widget_id
        assert f'id="{wid}_rec"' in html
        assert f'id="{wid}_stems"' in html  # score with tracks
        assert 'globalThis.KlothoRecorder = KlothoRecorder' in html
        assert '__klothoPlaybackBridgeV3' in html

    def test_plain_widget_has_no_record_artifacts(self):
        eng = self._engine()
        html = eng._generate_html()
        wid = eng.widget_id
        assert f'id="{wid}_rec"' not in html
        assert 'globalThis.KlothoRecorder = KlothoRecorder' not in html

    def test_record_without_tracks_has_no_stems_checkbox(self):
        from klotho.utils.playback.supersonic.engine import SuperSonicEngine
        events = [{
            "type": "new", "id": "a1", "defName": "kl_tri", "start": 0.0,
            "dur": 0.5, "releaseAfter": True,
            "pfields": {"freq": 440.0, "amp": 0.5},
        }]
        eng = SuperSonicEngine(events, record=True)
        html = eng._generate_html()
        assert f'id="{eng.widget_id}_rec"' in html
        assert f'id="{eng.widget_id}_stems"' not in html

    def test_animated_score_record_assembly(self):
        from klotho.thetos.composition.score import Score
        from klotho.thetos.instruments.synthdef import SynthDefInstrument
        from klotho.semeios.visualization._dispatch.plot_score import _plot_score
        s = Score()
        s.track('drums')
        s.new(start=0.0, dur=0.5, inst=SynthDefInstrument.sampler('bb_kick'),
              track='drums', amp=0.7)
        fig = _plot_score(s, animate=True, record=True)
        html = fig.to_html()
        assert f'id="{fig.widget_id}_rec"' in html
        assert f'id="{fig.widget_id}_stems"' in html
        assert 'globalThis.KlothoRecorder = KlothoRecorder' in html
        plain = _plot_score(s, animate=True)
        html2 = plain.to_html()
        assert f'id="{plain.widget_id}_rec"' not in html2
        assert 'globalThis.KlothoRecorder = KlothoRecorder' not in html2


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
