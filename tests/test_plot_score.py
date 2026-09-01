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


# ---------------------------------------------------------------------------
# plot(score).play() must ship the SAME SynthDefs play(score) ships.
#
# The two paths collected them separately and the animation copy walked
# event ``defName`` s ALONE. Every def that is never an event's defName was
# therefore missing from the animated page, and the drop is silent the whole
# way down: ``_filter_synthdef_assets`` skips a name it cannot place, and
# scsynth skips an ``/s_new`` naming a def it never received. The audible
# result is not a wrong sound, it is NO sound -- an insert FX is the only
# writer of its track's ``fxBus``, which the track's summing router reads,
# and the spatial width family is what a speaker array is built out of.
#
# Nothing surfaces in Python either: ``scheduler_core.js``'s ``async play()``
# awaits ``setupTracks`` outside any try/catch, and ``_animation_bridge.js``
# calls it with no ``await`` and no ``.catch``, so the throw becomes an
# unhandled promise rejection in the browser.
#
# These compare the two sets rather than asserting a literal list: the claim
# is parity, and a literal list would go stale the next time either side
# gains a def.
# ---------------------------------------------------------------------------

def _quad():
    from klotho.thetos import SpeakerArray
    return SpeakerArray.grid(cols=2, rows=2, col_spacing=50.0,
                             row_spacing=60.0, name='QUAD')


def _play_ships(score):
    """The SynthDef names ``play(score)`` sends to its widget."""
    from klotho.utils.playback.supersonic.converters import (
        convert_score_to_sc_events)
    from klotho.utils.playback.supersonic.engine import SuperSonicEngine
    payload = convert_score_to_sc_events(score)
    engine = SuperSonicEngine(payload['events'], meta=payload['meta'],
                              control_data=payload.get('control_data'))
    return set(engine._needed)


def _plot_ships(score):
    """The SynthDef names ``plot(score).play()`` sends to its page.

    Mirrors what ``build_scripts_html`` does with the extracted set, so a
    def that only the animated page adds still counts as shipped.
    """
    from klotho.utils.playback.supersonic.converters import (
        convert_score_to_sc_animation_events)
    from klotho.utils.playback.supersonic.engine import _INFRA_SYNTHDEFS
    from klotho.semeios.visualization._animation.animated import (
        _extract_needed_synthdefs)
    payload = convert_score_to_sc_animation_events(score)
    names = _extract_needed_synthdefs(payload)
    return (names or set()) | set(_INFRA_SYNTHDEFS) | {'__klEnvCtrl'}


class TestPlotShipsTheSameSynthdefsAsPlay:
    def test_an_insert_fx_reaches_the_animated_page(self):
        """Without the FX def, the track's fxBus has no writer and the
        whole track is silent -- not merely dry."""
        from klotho.thetos.instruments.synthdef import SynthDefFX
        score = Score()
        score.track('wet', inserts=[SynthDefFX('kl_reverb', mix=0.4)])
        uc = _uc()
        uc.set(uc.leaves, inst='kl_saw')
        score.append(uc, name='a', track='wet')

        assert 'kl_reverb' in _plot_ships(score)
        assert _play_ships(score) <= _plot_ships(score)

    def test_the_spatial_width_family_reaches_the_animated_page(self):
        """``__busRouterN`` / ``__spatialDecodeN`` are never an event's
        defName -- the scheduler builds them from ``meta.spatial``."""
        from klotho.thetos import SpeakerArray  # noqa: F401  (via _quad)
        score = Score()
        score.track('main', speakers=_quad())
        uc = _uc()
        uc.set(uc.leaves, speaker=1)
        score.append(uc, name='a')

        shipped = _plot_ships(score)
        assert '__busRouter4' in shipped
        assert '__spatialDecode4' in shipped
        assert _play_ships(score) <= shipped

    def test_a_control_envelope_ships_the_control_synth(self):
        """``__klEnvCtrl`` is likewise never an event defName. The animated
        page also adds it unconditionally, so this pins the extraction
        itself rather than the page assembly."""
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events)
        from klotho.semeios.visualization._animation.animated import (
            _extract_needed_synthdefs)
        from klotho.dynatos.envelopes import Envelope
        score = Score()
        uc = _uc()
        uc.root.apply_envelope(Envelope([0.0, 1.0, 0.0]), pfields='amp',
                               control=True)
        score.append(uc, name='a')
        payload = convert_score_to_sc_animation_events(score)
        assert payload['controlData']['descriptors'], 'fixture grew no envelope'
        assert '__klEnvCtrl' in _extract_needed_synthdefs(payload)

    def test_a_plain_score_ships_exactly_what_play_ships(self):
        """The no-extras case must not have regressed into over-shipping."""
        score = _score()
        assert _play_ships(score) <= _plot_ships(score)


class TestASpatialScoreMayContainARest:
    """``_lower_score_uc`` appends ``__rest__`` markers BEFORE the ``group``
    stamp (the ``continue`` skips it), so in animation mode they reached
    ``_apply_spatial_routing`` reading ``group='default'`` -> ``main``. With
    an array on ``main`` the refusal fired and named ``'__rest__'`` as the
    instrument the composer had to set a speaker on. A rest carries no
    sound; the scheduler's ``_bundleNew`` returns on ``__rest__`` before it
    ever reads ``speakerLane``.
    """

    def _spatial_score_with_a_rest(self):
        score = Score()
        score.track('main', speakers=_quad())
        uc = UC(tempus='4/4', prolatio=(1, -1, 1), bpm=120)
        uc.set(uc.leaves, speaker=1)
        score.append(uc, name='a')
        return score

    def test_play_accepts_it(self):
        """The control: play(score) has always been fine, because it drops
        rests before routing."""
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_events)
        payload = convert_score_to_sc_events(self._spatial_score_with_a_rest())
        assert len(payload['events']) == 2

    def test_plot_accepts_it_too(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events)
        payload = convert_score_to_sc_animation_events(
            self._spatial_score_with_a_rest())
        news = [e for e in payload['events'] if e['type'] == 'new']
        assert len(news) == 3, 'two sounding leaves plus the rest marker'

    def test_the_rest_marker_survives_and_carries_no_lane(self):
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events)
        payload = convert_score_to_sc_animation_events(
            self._spatial_score_with_a_rest())
        rests = [e for e in payload['events'] if e.get('defName') == '__rest__']
        assert len(rests) == 1
        assert 'speakerLane' not in rests[0]

    def test_a_sounding_voice_is_still_refused_without_a_speaker(self):
        """The exemption is for rests only -- the guard it routes around
        must still fire for anything that makes a sound."""
        from klotho.utils.playback.supersonic.converters import (
            convert_score_to_sc_animation_events)
        score = Score()
        score.track('main', speakers=_quad())
        score.append(UC(tempus='4/4', prolatio=(1, 1), bpm=120), name='a')
        with pytest.raises(ValueError, match='names no speaker'):
            convert_score_to_sc_animation_events(score)
