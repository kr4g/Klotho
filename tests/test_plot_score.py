"""plot(score): track-lane SVG renderer + animated SC payload consistency."""
import pytest

from klotho.thetos import Score, CompositionalUnit as UC
from klotho.chronos import TemporalUnitSequence as UTS
from klotho.chronos.temporal_units.temporal import TemporalUnit
from klotho.semeios.visualization._dispatch import KlothoPlot


@pytest.fixture(autouse=True)
def _mute_display(monkeypatch):
    import IPython.display
    monkeypatch.setattr(IPython.display, 'display', lambda *a, **k: None)


def _uc(prolatio=(1, 1, 2), bpm=120):
    return UC(tempus='4/4', prolatio=prolatio, bpm=bpm)


def _score():
    score = Score()
    score.track('drums')
    score.track('keys')
    score.append(_uc(), name='intro', track='drums')
    score.add(UTS([TemporalUnit(tempus='3/4', prolatio=(1, 1, 1), bpm=90),
                   TemporalUnit(tempus='4/4', prolatio=(1, -1, 1, 1), bpm=120)]),
              name='groove', track='keys', after='intro')
    score.new(0.5, 1.5, 'kl_tri', name='hit', track='drums',
              freq=660.0, amp=0.4)
    return score


def _leaf_count(score):
    from klotho.utils.playback.supersonic.converters import _iter_ucs
    from klotho.thetos.composition.events import Event
    total = 0
    for item in score.items():
        if isinstance(item.unit, Event):
            total += 1
        else:
            for uc in _iter_ucs(item.unit):
                total += len(uc._rt.leaf_nodes)
    return total


class TestScoreRenderer:
    def test_step_count_matches_leaves_plus_loose_events(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        score = _score()
        sd = _svg_score_timeline(score)
        expected = _leaf_count(score)
        assert len(sd.step_element_ids) == expected
        assert len(sd.step_halo_ids) == expected
        assert len(sd.step_durations) == expected

    def test_track_bands_in_registration_order(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        sd = _svg_score_timeline(_score())
        assert sd.track_names == ['drums', 'keys']

    def test_trackless_items_get_default_band(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        score = Score()
        score.append(_uc(), name='solo')
        sd = _svg_score_timeline(score)
        assert sd.track_names == ['default']

    def test_held_event_draws_to_score_end(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        score = Score()
        score.append(_uc(), name='bed')
        score.new(0.0, None, 'kl_tri', name='drone', freq=110.0)
        sd = _svg_score_timeline(score)
        # the held event's step duration spans to the score end
        assert sd.step_durations[-1] == pytest.approx(score.end - 0.0)

    def test_empty_score_rejected(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        with pytest.raises(ValueError, match='empty'):
            _svg_score_timeline(Score())


class TestScoreAnimationPayload:
    def test_step_indices_dense_and_matching(self):
        from klotho.semeios.visualization._renderers.svg_score import _svg_score_timeline
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        score = _score()
        sd = _svg_score_timeline(score)
        payload = convert_score_to_sc_animation_events(score)
        steps = {ev['_stepIndex'] for ev in payload['events']
                 if ev.get('_stepIndex') is not None}
        assert steps == set(range(len(sd.step_element_ids)))

    def test_payload_carries_meta_and_control_data(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        payload = convert_score_to_sc_animation_events(_score())
        assert payload['meta'].get('groups') == ['drums', 'keys']
        assert set(payload['controlData']) == {
            'blockSize', 'descriptors', 'bufferB64', 'numFrames'}
        assert isinstance(payload['sampleAssets'], dict)

    def test_negative_start_pre_shifted(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events,
        )
        score = Score()
        score.append(_uc(), name='body')
        score.new(-1.0, 0.5, 'kl_tri', name='riser', freq=880.0)
        payload = convert_score_to_sc_animation_events(score)
        assert min(ev['start'] for ev in payload['events']) >= 0.0
        # the score itself is not mutated
        assert score['riser'].start == pytest.approx(-1.0)

    def test_play_score_payload_unchanged_by_animation_support(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events,
        )
        payload = convert_score_to_sc_events(_score())
        assert all('_stepIndex' not in ev for ev in payload['events'])
        assert all(ev.get('defName') != '__rest__' for ev in payload['events']
                   if ev['type'] == 'new')


class TestScorePlotDispatch:
    def test_plot_returns_klotho_plot(self):
        from klotho import plot
        p = plot(_score())
        assert isinstance(p, KlothoPlot)
        static = p._build_static()
        assert static is not None
        assert len(static.svg_str) > 0

    def test_animate_html_builds_with_bridge(self):
        from klotho.semeios.visualization._dispatch.plot_score import _plot_score
        fig = _plot_score(_score(), animate=True)
        html = fig.to_html()
        assert 'KlothoPlaybackBridge' in html
        assert 'KlothoGateToggle' in html

    def test_unknown_kwarg_rejected(self):
        from klotho.semeios.visualization._dispatch.plot_score import _plot_score
        with pytest.raises(TypeError, match='score plot'):
            _plot_score(_score(), layout='tree')

    def test_registry_routes_score(self):
        from klotho.semeios.visualization.plots import _PLOT_REGISTRY
        handler = _PLOT_REGISTRY.lookup(_score())
        assert handler is not None
        assert handler.__name__ == '_dispatch_score'
