"""Tests for `convert_score_to_sc_events` and the universal `play(score)`
dispatch.  Covers event stream correctness, multi-item ordering, track
overrides, and control-envelope collection."""

import pytest

from klotho.chronos import TemporalUnit as UT
from klotho.dynatos import Envelope
from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.score import Score
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
)


def _inst():
    return SynthDefInstrument(
        name='tri', defName='kl_tri',
        pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0},
    )


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
              inst=_inst(), pfields=['amp'])


class TestPayloadShape:
    def test_returns_events_meta_and_control_data(self):
        s = Score()
        s.add(_uc(), name='a')
        payload = convert_score_to_sc_events(s)
        assert set(payload.keys()) >= {'events', 'meta', 'control_data'}
        assert 'buffer' in payload['control_data']
        assert 'blockSize' in payload['control_data']
        assert 'descriptors' in payload['control_data']

    def test_empty_score_produces_empty_event_list(self):
        s = Score()
        payload = convert_score_to_sc_events(s)
        assert payload['events'] == []

    def test_events_sorted_by_start(self):
        s = Score()
        s.add(_uc(), name='b', at=4.0)
        s.add(_uc(), name='a', at=1.0)
        payload = convert_score_to_sc_events(s)
        starts = [e['start'] for e in payload['events']]
        assert starts == sorted(starts)


class TestPlacementReflectedInEvents:
    def test_item_at_offset_pushes_events_forward(self):
        s = Score()
        s.add(_uc(), name='a', at=3.0)
        payload = convert_score_to_sc_events(s)
        new_events = [e for e in payload['events'] if e.get('type') == 'new']
        assert all(e['start'] >= 3.0 - 1e-9 for e in new_events)

    def test_two_items_have_non_overlapping_event_ranges(self):
        s = Score()
        s.add(_uc(), name='a', at=0.0)
        s.add(_uc(), name='b', at=10.0)
        payload = convert_score_to_sc_events(s)
        new_events = [e for e in payload['events'] if e.get('type') == 'new']
        a_events = [e for e in new_events if e['start'] < 5.0]
        b_events = [e for e in new_events if e['start'] >= 10.0]
        assert len(a_events) == 4
        assert len(b_events) == 4


class TestTrackOverride:
    def test_group_mfield_replaced_by_track(self):
        s = Score().track('melody')
        s.add(_uc(), name='a', track='melody')
        payload = convert_score_to_sc_events(s)
        new_events = [e for e in payload['events'] if e.get('type') == 'new']
        assert all(e.get('group') == 'melody' for e in new_events)

    def test_no_track_uses_default_group(self):
        s = Score()
        s.add(_uc(), name='a')
        payload = convert_score_to_sc_events(s)
        new_events = [e for e in payload['events'] if e.get('type') == 'new']
        assert all(e.get('group') == 'default' for e in new_events)


class TestControlEnvelopeCollection:
    def test_envelope_descriptor_appears_in_payload(self):
        uc = _uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        s = Score()
        s.add(uc, name='a')
        payload = convert_score_to_sc_events(s)
        assert len(payload['control_data']['descriptors']) == 1

    def test_envelope_start_reflects_item_placement(self):
        uc = _uc()
        env = Envelope([0.0, 1.0], times=[1.0])
        uc.apply_envelope(
            envelope=env, pfields='amp', node=uc.rt.root, control=True
        )
        s = Score()
        s.add(uc, name='a', at=7.5)
        payload = convert_score_to_sc_events(s)
        desc = payload['control_data']['descriptors'][0]
        assert desc['start'] >= 7.5 - 1e-9


class TestMetaTracksAndInserts:
    def test_registered_tracks_appear_in_meta_groups(self):
        s = Score().track('melody').track('bass')
        s.add(_uc(), name='a', track='melody')
        payload = convert_score_to_sc_events(s)
        assert set(payload['meta'].get('groups', [])) == {'melody', 'bass'}

    def test_main_track_not_included_in_groups(self):
        s = Score()
        s.add(_uc(), name='a', track='main')
        payload = convert_score_to_sc_events(s)
        assert 'main' not in payload['meta'].get('groups', [])


class TestUniversalPlayDispatch:
    def test_play_score_does_not_raise(self):
        """`play(score)` should dispatch through the universal player
        without requiring `Score.play` to exist as a method."""
        from klotho import play
        from klotho.thetos.composition.score import Score as _Score
        assert not hasattr(_Score, 'play'), (
            "Score.play should no longer exist; playback goes through play(score)"
        )
        s = Score()
        s.add(_uc(), name='a')
        play(s)
