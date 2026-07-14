"""Tests for standalone score events: `Score.new` / `Score.set` /
`Score.release` and their lowering to SC `new`/`set`/`release` events
(the scsynth /s_new / /n_set node analogy)."""

import json

import numpy as np
import pytest

from klotho.thetos import CompositionalUnit as UC
from klotho.thetos.composition.events import Event
from klotho.thetos.composition.score import EventItem, Score, ScoreItem
from klotho.thetos.instruments.synthdef import SynthDefInstrument
from klotho.tonos import Pitch
from klotho.tonos.chords.chord import Chord
from klotho.utils.playback._sc_validate import validate_sc_events
from klotho.utils.playback.supersonic.converters import (
    convert_score_to_sc_events,
)


def _inst():
    return SynthDefInstrument(
        name='tri', defName='kl_tri',
        pfields={'amp': 0.1, 'freq': 440.0, 'pan': 0.0, 'gate': 1, 'out': 0},
    )


def _ungated_inst():
    return SynthDefInstrument(
        name='perc', defName='kl_tri',
        pfields={'amp': 0.1, 'freq': 440.0, 'duration': 0.5, 'out': 0},
    )


def _uc():
    return UC(tempus='4/4', prolatio=(1, 1, 1, 1), beat='1/4', bpm=60,
              inst=_inst(), pfields=['amp'])


def _lower(score):
    payload = convert_score_to_sc_events(score)
    validate_sc_events(payload['events'])
    return payload['events']


def _by_type(events, etype):
    return [e for e in events if e['type'] == etype]


class TestAuthoring:
    def test_handle_is_the_score_entry(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst(), freq=440.0)
        assert isinstance(h, EventItem)
        assert s['event_0'] is h

    def test_auto_name_prefix_distinguishes_events_from_items(self):
        s = Score()
        s.new(0.0, 1.0, _inst())
        s.add(_uc())
        assert list(s.names()) == ['event_0', 'item_1']

    def test_pitch_name_string_coerced_to_pitch(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst(), freq='A4')
        assert isinstance(h.unit.pfields['freq'], Pitch)

    def test_chord_coerced_to_tuple_of_pitches(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst(),
                  freq=Chord(['1/1', '5/4', '3/2']).root('A4'))
        val = h.unit.pfields['freq']
        assert isinstance(val, tuple) and len(val) == 3
        assert all(isinstance(p, Pitch) for p in val)

    def test_numpy_array_rejected(self):
        s = Score()
        with pytest.raises(TypeError, match='tuple'):
            s.new(0.0, 1.0, _inst(), freq=np.array([440.0, 550.0]))

    def test_strum_and_group_routed_to_mfields(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst(), freq=(220.0, 330.0),
                  strum=0.5, group='pads')
        assert h.unit.mfields == {'strum': 0.5, 'group': 'pads'}
        assert 'strum' not in h.unit.pfields
        assert 'group' not in h.unit.pfields

    def test_unknown_inst_name_raises(self):
        s = Score()
        with pytest.raises(ValueError, match='Unknown SynthDef'):
            s.new(0.0, 1.0, 'no_such_synth')

    def test_unregistered_track_raises(self):
        s = Score()
        with pytest.raises(ValueError, match='not registered'):
            s.new(0.0, 1.0, _inst(), track='nope')

    def test_hold_requires_gated_synth(self):
        s = Score()
        with pytest.raises(ValueError, match='gate'):
            s.new(0.0, dur=None, inst=_ungated_inst())

    def test_add_bare_event_returns_event_item(self):
        s = Score()
        item = s.add(Event(inst=_inst(), dur=1.0, pfields={'freq': 440.0}))
        assert isinstance(item, EventItem)
        assert list(s.names()) == ['event_0']


class TestPlacement:
    def test_duration_from_dur(self):
        s = Score()
        h = s.new(2.0, 3.0, _inst())
        assert h.start == 2.0
        assert h.duration == 3.0
        assert h.end == 5.0

    def test_bare_hold_has_zero_duration(self):
        s = Score()
        h = s.new(2.0, dur=None, inst=_inst())
        assert h.duration == 0.0
        assert h.end == 2.0

    def test_released_hold_duration_is_release_offset(self):
        s = Score()
        h = s.new(2.0, dur=None, inst=_inst())
        s.release(h, at=5.0)
        assert h.duration == 3.0
        assert s.end == 5.0

    def test_sets_do_not_extend_duration(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst())
        s.set(h, at=10.0, amp=0.2)
        assert h.duration == 1.0

    def test_append_after_released_hold(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst())
        s.release(h, at=3.0)
        item = s.append(_uc())
        assert item.start == pytest.approx(3.0)

    def test_prepend_shifts_event(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst())
        s.prepend(_uc())  # 4 seconds at 60 bpm
        assert h.start == pytest.approx(4.0)


class TestSetReleaseTiming:
    def test_at_before_event_start_raises(self):
        s = Score()
        h = s.new(2.0, 1.0, _inst())
        with pytest.raises(ValueError, match='precedes'):
            s.set(h, at=1.0, amp=0.2)
        with pytest.raises(ValueError, match='precedes'):
            s.release(h, at=1.0)

    def test_second_release_raises(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst())
        s.release(h, at=2.0)
        with pytest.raises(ValueError, match='already has a release'):
            s.release(h, at=3.0)

    def test_empty_set_raises(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst())
        with pytest.raises(ValueError, match='at least one pfield'):
            s.set(h, at=0.5)

    def test_engine_mfields_rejected_in_set(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst())
        with pytest.raises(ValueError, match='meta-fields'):
            s.set(h, at=0.5, strum=0.1, amp=0.2)

    def test_set_on_uc_item_raises_type_error(self):
        s = Score()
        s.add(_uc(), name='a')
        with pytest.raises(TypeError, match='standalone events'):
            s.set('a', at=1.0, amp=0.2)

    def test_target_by_name_string(self):
        s = Score()
        s.new(0.0, 1.0, _inst(), name='hit')
        s.set('hit', at=0.5, amp=0.2)
        assert len(s['hit'].unit._sets) == 1

    def test_foreign_item_raises(self):
        s1, s2 = Score(), Score()
        h = s1.new(0.0, 1.0, _inst())
        s2.new(0.0, 1.0, _inst())
        with pytest.raises(ValueError, match='different Score'):
            s2.set(h, at=0.5, amp=0.2)

    def test_at_tracks_event_through_ripple(self):
        """A set authored in absolute time is stored relative, so it
        moves with its event when an earlier item is resized."""
        s = Score()
        s.add(_uc(), name='a')                       # 0..4s
        h = s.new(4.0, dur=None, inst=_inst(), freq=440.0)
        s.set(h, at=6.0, amp=0.2)                    # 2s into the event
        s.release(h, at=8.0)
        s['a'].set_duration(8.0, ripple=True)        # event now at 8s
        events = _lower(s)
        ev_sets = [e for e in _by_type(events, 'set')]
        assert h.start == pytest.approx(8.0)
        assert ev_sets[-1]['start'] == pytest.approx(10.0)
        assert _by_type(events, 'release')[-1]['start'] == pytest.approx(12.0)


class TestLoweringNew:
    def test_tuple_pfield_expands_to_voices(self):
        s = Score()
        s.new(0.0, 1.0, _inst(), freq=(220.0, 330.0, 440.0))
        news = _by_type(_lower(s), 'new')
        assert len(news) == 3
        assert len({e['id'] for e in news}) == 3
        assert len({e['_polyGroupId'] for e in news}) == 1
        assert sorted(e['pfields']['freq'] for e in news) == [220.0, 330.0, 440.0]

    def test_group_from_track(self):
        s = Score().track('pads')
        s.new(0.0, 1.0, _inst(), track='pads')
        assert all(e['group'] == 'pads' for e in _lower(s))

    def test_group_from_mfield_when_no_track(self):
        s = Score()
        s.new(0.0, 1.0, _inst(), group='fx_bus')
        assert all(e['group'] == 'fx_bus' for e in _lower(s))

    def test_group_defaults_to_default(self):
        s = Score()
        s.new(0.0, 1.0, _inst())
        assert all(e['group'] == 'default' for e in _lower(s))

    def test_fixed_dur_contract(self):
        s = Score()
        s.new(0.0, 2.5, _inst(), freq=440.0)
        (new,) = _by_type(_lower(s), 'new')
        assert new['dur'] == pytest.approx(2.5)
        assert new['releaseAfter'] is True

    def test_hold_contract(self):
        s = Score()
        s.new(0.0, dur=None, inst=_inst(), freq=440.0)
        (new,) = _by_type(_lower(s), 'new')
        assert new['dur'] is None
        assert new['releaseAfter'] is False

    def test_release_contract(self):
        s = Score()
        h = s.new(1.0, dur=None, inst=_inst(), freq=440.0)
        s.release(h, at=4.0)
        (new,) = _by_type(_lower(s), 'new')
        assert new['dur'] == pytest.approx(3.0)
        assert new['releaseAfter'] is False

    def test_strum_staggers_voice_starts(self):
        s = Score()
        s.new(0.0, 1.0, _inst(), freq=(220.0, 330.0, 440.0), strum=0.5)
        news = _by_type(_lower(s), 'new')
        starts = sorted(e['start'] for e in news)
        assert starts[0] == pytest.approx(0.0)
        assert starts[1] > starts[0]
        assert starts[2] > starts[1]

    def test_ungated_synth_gets_duration_pfield(self):
        s = Score()
        s.new(0.0, 1.5, _ungated_inst(), freq=440.0)
        (new,) = _by_type(_lower(s), 'new')
        assert new['pfields']['duration'] == pytest.approx(1.5)

    def test_instrument_defaults_below_user_pfields(self):
        s = Score()
        s.new(0.0, 1.0, _inst(), freq=220.0)
        (new,) = _by_type(_lower(s), 'new')
        assert new['pfields']['freq'] == 220.0
        assert new['pfields']['amp'] == 0.1     # instrument default
        assert 'gate' not in new['pfields']
        assert 'out' not in new['pfields']


class TestLoweringSetRelease:
    def _chord_score(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=(220.0, 330.0, 440.0))
        s.set(h, at=2.0, amp=(0.05, 0.1))
        s.release(h, at=5.0)
        return s

    def test_set_and_release_ids_match_new_ids(self):
        events = _lower(self._chord_score())
        new_ids = [e['id'] for e in _by_type(events, 'new')]
        assert [e['id'] for e in _by_type(events, 'set')] == new_ids
        assert [e['id'] for e in _by_type(events, 'release')] == new_ids

    def test_set_tuple_cycles_modulo_over_voices(self):
        events = _lower(self._chord_score())
        amps = [e['pfields']['amp'] for e in _by_type(events, 'set')]
        assert amps == [0.05, 0.1, 0.05]

    def test_set_scalar_broadcasts(self):
        s = Score()
        h = s.new(0.0, 1.0, _inst(), freq=(220.0, 330.0))
        s.set(h, at=0.5, amp=0.3)
        sets = _by_type(_lower(s), 'set')
        assert [e['pfields']['amp'] for e in sets] == [0.3, 0.3]

    def test_set_freq_pitch_name_lowers_to_float(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=440.0)
        s.set(h, at=1.0, freq='A5')
        (set_ev,) = _by_type(_lower(s), 'set')
        assert set_ev['pfields']['freq'] == pytest.approx(880.0)

    def test_same_start_orders_new_set_release(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=440.0)
        s.set(h, at=0.0, amp=0.2)
        s.release(h, at=0.0)
        assert [e['type'] for e in _lower(s)] == ['new', 'set', 'release']

    def test_sets_keep_author_order(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=440.0)
        s.set(h, at=1.0, amp=0.2)
        s.set(h, at=1.0, amp=0.4)
        sets = _by_type(_lower(s), 'set')
        assert [e['pfields']['amp'] for e in sets] == [0.2, 0.4]

    def test_ids_regenerate_across_lowerings(self):
        s = self._chord_score()
        first = {e['id'] for e in _lower(s)}
        second = {e['id'] for e in _lower(s)}
        assert first.isdisjoint(second)

    def test_release_dropped_for_ungated_synth(self):
        s = Score()
        h = s.new(0.0, 1.0, _ungated_inst(), freq=440.0)
        s.release(h, at=0.5)
        events = _lower(s)
        assert _by_type(events, 'release') == []


class TestTimeScaling:
    def test_stretch_scales_whole_gesture(self):
        s = Score()
        h = s.new(0.0, 2.0, _inst(), freq=440.0)
        s.set(h, at=1.0, amp=0.2)
        h.stretch(2.0)
        events = _lower(s)
        (new,) = _by_type(events, 'new')
        (set_ev,) = _by_type(events, 'set')
        assert new['dur'] == pytest.approx(4.0)
        assert set_ev['start'] == pytest.approx(2.0)

    def test_frozen_blocks_stretch_but_not_set(self):
        s = Score()
        h = s.new(0.0, 2.0, _inst(), freq=440.0)
        h.freeze()
        with pytest.raises(RuntimeError, match='frozen'):
            h.stretch(2.0)
        s.set(h, at=1.0, amp=0.2)  # authoring still allowed
        assert len(h.unit._sets) == 1

    def test_bare_hold_cannot_be_scaled(self):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst())
        with pytest.raises(ValueError, match='zero duration'):
            h.set_duration(2.0)


class TestNegativeTimeline:
    def test_riser_event_before_zero_shifts_everything(self):
        s = Score()
        h = s.new(-2.0, 2.0, _inst(), freq=220.0, name='riser')
        s.set(h, at=-1.0, amp=0.3)
        s.add(_uc(), at=0.0)
        events = _lower(s)  # validates: no negative starts survive
        riser_new = [e for e in _by_type(events, 'new')
                     if e['pfields']['freq'] == 220.0]
        assert riser_new[0]['start'] == pytest.approx(0.0)
        (set_ev,) = _by_type(events, 'set')
        assert set_ev['start'] == pytest.approx(1.0)
        uc_starts = [e['start'] for e in _by_type(events, 'new')
                     if e['pfields']['freq'] != 220.0]
        assert min(uc_starts) == pytest.approx(2.0)

    def test_negative_hold_release_shifts_together(self):
        s = Score()
        h = s.new(-3.0, dur=None, inst=_inst(), freq=440.0)
        s.release(h, at=-1.0)
        events = _lower(s)
        (new,) = _by_type(events, 'new')
        (rel,) = _by_type(events, 'release')
        assert new['start'] == pytest.approx(0.0)
        assert new['dur'] == pytest.approx(2.0)
        assert rel['start'] == pytest.approx(2.0)

    def test_write_normalizes_negative_timeline(self, tmp_path):
        s = Score()
        s.new(-2.0, 1.0, _inst(), freq=440.0)
        path = tmp_path / 'neg.json'
        s.write(str(path))
        data = json.loads(path.read_text())
        assert all(e['start'] >= -1e-9 for e in data['events'])


class TestIsolationAndWrite:
    def test_add_copies_event(self):
        s = Score()
        ev = Event(inst=_inst(), dur=1.0, pfields={'freq': 440.0})
        item = s.add(ev)
        s.set(item, at=0.5, amp=0.2)
        assert ev._sets == []
        assert len(item.unit._sets) == 1

    def test_write_round_trips_hold_and_ids(self, tmp_path):
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=(220.0, 330.0))
        s.release(h, at=5.0)
        s2 = Score()
        s2.new(0.0, dur=None, inst=_inst(), freq=440.0)  # bare hold
        path = tmp_path / 'events.json'
        s2.write(str(path))
        data = json.loads(path.read_text())
        (new,) = [e for e in data['events'] if e['type'] == 'new']
        assert new['dur'] is None

        path2 = tmp_path / 'chord.json'
        s.write(str(path2))
        data2 = json.loads(path2.read_text())
        new_ids = [e['id'] for e in data2['events'] if e['type'] == 'new']
        rel_ids = [e['id'] for e in data2['events'] if e['type'] == 'release']
        assert rel_ids == new_ids


class TestPlayDispatch:
    def test_play_score_with_events_does_not_raise(self):
        from klotho import play
        s = Score()
        h = s.new(0.0, dur=None, inst=_inst(), freq=(220.0, 330.0))
        s.set(h, at=1.0, amp=0.2)
        s.release(h, at=3.0)
        s.add(_uc(), at=1.0)
        play(s)
